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
: ${HOST:=${DB_PORT_5432_TCP_ADDR:='db'}}
: ${PORT:=${DB_PORT_5432_TCP_PORT:=5432}}
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
    if grep -q -E "^\s*\b${param}\b\s*=" "$ODOO_RC" ; then       
        value=$(grep -E "^\s*\b${param}\b\s*=" "$ODOO_RC" |cut -d " " -f3|sed 's/["\n\r]//g')
    fi;
    DB_ARGS+=("--${param}")
    DB_ARGS+=("${value}")
}
check_config "db_host" "$HOST"
check_config "db_port" "$PORT"
check_config "db_user" "$DB_USER"
check_config "db_password" "$PASSWORD"

case "$1" in
    -- | odoo)
        shift
        if [[ "$1" == "scaffold" ]] ; then
            log "Starting Odoo scaffold command..."
            exec odoo "$@"
        else
            log "Waiting for PostgreSQL to be ready..."
            wait-for-psql.py ${DB_ARGS[@]} --timeout=30
            log "✅ PostgreSQL is ready. Starting Odoo..."
            exec odoo "$@" "${DB_ARGS[@]}"
        fi
        ;;
    -*)
        log "Waiting for PostgreSQL to be ready..."
        wait-for-psql.py ${DB_ARGS[@]} --timeout=30
        log "✅ PostgreSQL is ready. Starting Odoo..."
        exec odoo "$@" "${DB_ARGS[@]}"
        ;;
    *)
        log "Executing custom command: $@"
        exec "$@"
esac

log_error "Failed to execute command. This line should never be reached."
exit 1
