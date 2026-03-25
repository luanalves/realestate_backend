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
