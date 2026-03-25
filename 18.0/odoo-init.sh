#!/bin/bash
# =============================================================================
# odoo-init.sh — Database init (fresh install) or module upgrade (redeploy)
# =============================================================================
# Called by the docker-compose 'odoo-init' service via:
#   ENTRYPOINT ["/entrypoint.sh"]  +  command: ["bash", "/odoo-init.sh"]
#
# The entrypoint.sh drops privileges to user 'odoo' via gosu before exec'ing
# this script, so all operations here run as the 'odoo' user.
#
# Behaviour:
#   Fresh DB  → installs all modules, loads seed data, sets admin password
#   Existing DB → upgrades modules (--update), re-applies admin password
# =============================================================================

set -e

log()      { echo "[odoo-init] $1"; }
log_ok()   { echo "[odoo-init] ✅ $1"; }
log_warn() { echo "[odoo-init] ⚠️  $1" >&2; }
log_error(){ echo "[odoo-init] ❌ $1" >&2; }

# ---------------------------------------------------------------------------
# Connection config — entrypoint.sh resolves HOST/PORT from DB_HOST/DB_PORT;
# here we resolve the same way for the psql availability check.
# ---------------------------------------------------------------------------
_HOST="${HOST:-${DB_HOST:-db}}"
_PORT="${PORT:-${DB_PORT:-5432}}"
_USER="${POSTGRES_USER:-odoo}"
_PASS="${POSTGRES_PASSWORD:-odoo}"
_DB="${DB_NAME:-realestate}"

# Modules to install/upgrade (comma-separated; dependency order matters)
MODULES="${ODOO_INIT_MODULES:-quicksol_estate,thedevkitchen_branding,thedevkitchen_apigateway,thedevkitchen_user_onboarding}"

# ---------------------------------------------------------------------------
# 1. Wait for PostgreSQL
# ---------------------------------------------------------------------------
log "Waiting for PostgreSQL at $_HOST:$_PORT (db=$_DB, user=$_USER)..."
wait-for-psql.py \
    --db_host="$_HOST" --db_port="$_PORT" \
    --db_user="$_USER" --db_password="$_PASS" \
    --timeout=60
log_ok "PostgreSQL is ready"

# ---------------------------------------------------------------------------
# 2. Detect fresh vs existing database
# ---------------------------------------------------------------------------
# A non-empty result means the 'ir_module_module' table exists → Odoo is
# already initialised. An empty result (or psql failure when the DB doesn't
# exist yet) means we need a fresh install.
_has_odoo=$(PGPASSWORD="$_PASS" psql \
    -h "$_HOST" -p "$_PORT" -U "$_USER" -d "$_DB" \
    -tAc "SELECT 1 FROM information_schema.tables \
          WHERE table_name='ir_module_module' LIMIT 1" \
    2>/dev/null || echo "")

_ODOO_BASE_ARGS=(
    "--db_host=$_HOST" "--db_port=$_PORT"
    "--db_user=$_USER" "--db_password=$_PASS"
    "-d" "$_DB"
    "--without-demo=all"
    "--stop-after-init"
)

# ---------------------------------------------------------------------------
# 3. Block external HTTP/HTTPS during init to prevent partner_autocomplete
#    (and any other IAP module) from spawning threads that call iap.odoo.com.
#    --stop-after-init waits for ALL threads; an unfinished IAP HTTP call
#    causes an infinite hang. Routing through 127.0.0.1:1 guarantees an
#    immediate ConnectionRefused — Odoo's IAP code catches the exception,
#    logs a warning, and the thread exits cleanly.
# ---------------------------------------------------------------------------
export http_proxy="http://127.0.0.1:1/"
export https_proxy="http://127.0.0.1:1/"
export HTTP_PROXY="http://127.0.0.1:1/"
export HTTPS_PROXY="http://127.0.0.1:1/"
# Keep internal services reachable (DB/Redis/RabbitMQ use their own protocols,
# but keep localhost and container names in no_proxy for safety)
export no_proxy="localhost,127.0.0.1,db,redis,rabbitmq,mailhog"
export NO_PROXY="localhost,127.0.0.1,db,redis,rabbitmq,mailhog"
log "External HTTP blocked during init (proxy → 127.0.0.1:1) to prevent IAP hang"

# ---------------------------------------------------------------------------
# 3a. FRESH INSTALL — init all modules and load seed data
# ---------------------------------------------------------------------------
if [ -z "$_has_odoo" ]; then
    log "Fresh database — installing modules: $MODULES"
    odoo "${_ODOO_BASE_ARGS[@]}" --init="$MODULES"
    log_ok "Modules installed: $MODULES"

# ---------------------------------------------------------------------------
# 3b. EXISTING DB — upgrade modules (picks up code/data changes on redeploy)
# ---------------------------------------------------------------------------
else
    log "Existing database — upgrading modules: $MODULES"
    odoo "${_ODOO_BASE_ARGS[@]}" --update="$MODULES"
    log_ok "Modules upgraded: $MODULES"
fi

# Restore normal network access for subsequent steps (e.g. set_admin_password)
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY no_proxy NO_PROXY

# ---------------------------------------------------------------------------
# 4. Set admin user login password (idempotent — safe on every deploy)
# ---------------------------------------------------------------------------
if [ -n "${ODOO_NEW_ADMIN_PASSWORD:-}" ]; then
    log "Applying admin user password from ODOO_NEW_ADMIN_PASSWORD..."
    python3 /usr/local/bin/set_admin_password.py \
        "$_DB" "$_HOST" "$_PORT" "$_USER" "$_PASS" \
        "$ODOO_NEW_ADMIN_PASSWORD"
else
    log_warn "ODOO_NEW_ADMIN_PASSWORD is not set — admin login password remains 'admin'"
fi

log_ok "odoo-init completed successfully"
