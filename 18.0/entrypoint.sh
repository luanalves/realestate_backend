#!/bin/bash

set -e

# Logging helper
log() {
    echo "[entrypoint.sh] $1"
}

log_error() {
    echo "[entrypoint.sh] ❌ ERROR: $1" >&2
}

log_warning() {
    echo "[entrypoint.sh] ⚠️  WARNING: $1" >&2
}

# Fix volume permissions: when a Docker named volume is created on a new host,
# the directory is owned by root. The odoo process runs as the 'odoo' user,
# so we chown here (while still root) and then drop privileges via gosu.
if [ "$(id -u)" = '0' ]; then
    chown -R odoo:odoo /var/lib/odoo /mnt/extra-addons 2>/dev/null || true
    exec gosu odoo "$0" "$@"
fi

if [ -v PASSWORD_FILE ]; then
    PASSWORD="$(< $PASSWORD_FILE)"
fi

# set the postgres database host, port, user and password according to the environment
# and pass them as arguments to the odoo process if not present in the config file
: ${HOST:=${DB_PORT_5432_TCP_ADDR:=${DB_HOST:='db'}}}
: ${PORT:=${DB_PORT_5432_TCP_PORT:=${DB_PORT:=5432}}}
# Note: using DB_USER instead of USER to avoid collision with Linux shell variable $USER
: ${DB_USER:=${DB_ENV_POSTGRES_USER:=${POSTGRES_USER:-}}}
: ${PASSWORD:=${DB_ENV_POSTGRES_PASSWORD:=${POSTGRES_PASSWORD:-}}}

# Validate critical environment variables
log "Validating database configuration..."

if [ -z "$DB_USER" ]; then
    log_error "Database user not configured. Set POSTGRES_USER environment variable."
    log_error "Example: POSTGRES_USER=odoo_prod_user"
    exit 1
fi

if [ -z "$PASSWORD" ]; then
    log_error "Database password not configured. Set POSTGRES_PASSWORD environment variable."
    log_error "Example: POSTGRES_PASSWORD=\$(openssl rand -base64 32)"
    exit 1
fi

# Validate password strength (minimum 16 characters for production)
if [ ${#PASSWORD} -lt 16 ]; then
    log_warning "Database password is weak (${#PASSWORD} chars). Recommended: 32+ characters."
    log_warning "Generate strong password: openssl rand -base64 32"
fi

log "✅ Database configuration validated (host=$HOST, port=$PORT, user=$DB_USER)"

DB_ARGS=()
function check_config() {
    param="$1"
    value="$2"
    # Env var takes priority; only fall back to odoo.conf if env var is empty
    if [ -z "$value" ] && grep -q -E "^\s*\b${param}\b\s*=" "$ODOO_RC" ; then
        value=$(grep -E "^\s*\b${param}\b\s*=" "$ODOO_RC" |cut -d " " -f3|sed 's/["\n\r]//g')
    fi;
    DB_ARGS+=("--${param}")
    DB_ARGS+=("${value}")
}
check_config "db_host" "$HOST"
check_config "db_port" "$PORT"
check_config "db_user" "$DB_USER"
check_config "db_password" "$PASSWORD"

# PSQL_WAIT_ARGS: connection-only args accepted by wait-for-psql.py (no --database)
PSQL_WAIT_ARGS=("--db_host" "$HOST" "--db_port" "$PORT" "--db_user" "$DB_USER" "--db_password" "$PASSWORD")

# Support DB_NAME env var to override the db_name setting in odoo.conf.
# In production, DB_NAME (e.g. odoo_production) differs from the dev default
# (realestate) that is hardcoded in odoo.conf.
# NOTE: Odoo CLI uses --database/-d, NOT --db_name (which is the conf file key).
: ${DB_NAME:=${POSTGRES_DB:-}}
if [ -n "${DB_NAME:-}" ]; then
    DB_ARGS+=("--database")
    DB_ARGS+=("$DB_NAME")
fi

# ---------------------------------------------------------------------------
# Generate a runtime Odoo config with production overrides from env vars.
# This lets ODOO_ADMIN_PASSWD, ODOO_WORKERS, REDIS_PASSWORD, list_db, etc.
# be applied without modifying the read-only odoo.conf volume mount.
# ---------------------------------------------------------------------------
_rt_needed=false
for _v in ODOO_ADMIN_PASSWD ODOO_LIST_DB ODOO_DB_FILTER ODOO_WORKERS \
          ODOO_MAX_CRON_THREADS ODOO_PROXY_MODE ODOO_LOG_LEVEL \
          ODOO_LIMIT_TIME_CPU ODOO_LIMIT_TIME_REAL \
          ODOO_LIMIT_MEMORY_HARD ODOO_LIMIT_MEMORY_SOFT \
          REDIS_PASSWORD REDIS_HOST REDIS_PORT REDIS_DBINDEX; do
    if [ -n "${!_v}" ]; then _rt_needed=true; break; fi
done
if [ "$_rt_needed" = "true" ]; then
    _rc=$(mktemp /tmp/odoo-XXXXXX.conf)
    chmod 600 "$_rc"
    cp "$ODOO_RC" "$_rc"
    # _cfg: remove any existing (commented or active) key, then append the new value
    _cfg() { local k="$1" v="$2"; sed -i "/^\s*;*\s*${k}\s*=/d" "$_rc"; printf '%s = %s\n' "$k" "$v" >> "$_rc"; }
    [ -n "${ODOO_ADMIN_PASSWD}" ]      && _cfg "admin_passwd"      "$ODOO_ADMIN_PASSWD"
    [ -n "${ODOO_LIST_DB}" ]           && _cfg "list_db"            "$ODOO_LIST_DB"
    [ -n "${ODOO_DB_FILTER}" ]         && _cfg "dbfilter"           "$ODOO_DB_FILTER"
    [ -n "${ODOO_WORKERS}" ]           && _cfg "workers"            "$ODOO_WORKERS"
    [ -n "${ODOO_MAX_CRON_THREADS}" ]  && _cfg "max_cron_threads"   "$ODOO_MAX_CRON_THREADS"
    [ -n "${ODOO_PROXY_MODE}" ]        && _cfg "proxy_mode"         "$ODOO_PROXY_MODE"
    [ -n "${ODOO_LOG_LEVEL}" ]         && _cfg "log_level"          "$ODOO_LOG_LEVEL"
    [ -n "${ODOO_LIMIT_TIME_CPU}" ]    && _cfg "limit_time_cpu"     "$ODOO_LIMIT_TIME_CPU"
    [ -n "${ODOO_LIMIT_TIME_REAL}" ]   && _cfg "limit_time_real"    "$ODOO_LIMIT_TIME_REAL"
    [ -n "${ODOO_LIMIT_MEMORY_HARD}" ] && _cfg "limit_memory_hard"  "$ODOO_LIMIT_MEMORY_HARD"
    [ -n "${ODOO_LIMIT_MEMORY_SOFT}" ] && _cfg "limit_memory_soft"  "$ODOO_LIMIT_MEMORY_SOFT"
    [ -n "${REDIS_PASSWORD}" ]         && _cfg "redis_pass"         "$REDIS_PASSWORD"
    [ -n "${REDIS_HOST}" ]             && _cfg "redis_host"         "$REDIS_HOST"
    [ -n "${REDIS_PORT}" ]             && _cfg "redis_port"         "$REDIS_PORT"
    [ -n "${REDIS_DBINDEX}" ]          && _cfg "redis_dbindex"      "$REDIS_DBINDEX"
    export ODOO_RC="$_rc"
    log "Runtime config generated with env overrides"
fi

case "$1" in
    -- | odoo)
        shift
        if [[ "$1" == "scaffold" ]] ; then
            log "Starting Odoo scaffold command..."
            exec odoo "$@"
        else
            log "Waiting for PostgreSQL to be ready..."
            wait-for-psql.py ${PSQL_WAIT_ARGS[@]} --timeout=30
            log "✅ PostgreSQL is ready. Starting Odoo..."
            exec odoo "$@" "${DB_ARGS[@]}"
        fi
        ;;
    -*)
        log "Waiting for PostgreSQL to be ready..."
        wait-for-psql.py ${PSQL_WAIT_ARGS[@]} --timeout=30
        log "✅ PostgreSQL is ready. Starting Odoo..."
        exec odoo "$@" "${DB_ARGS[@]}"
        ;;
    *)
        log "Executing custom command: $@"
        exec "$@"
esac

log_error "Failed to execute command. This line should never be reached."
exit 1
