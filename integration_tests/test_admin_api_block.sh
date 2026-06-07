#!/usr/bin/env bash
# =============================================================================
# test_admin_api_block.sh — Feature 022 / ADR-029
# =============================================================================
# Verifica que o endpoint de login da REST API bloqueia usuários do grupo
# base.group_system com HTTP 401 (anti-enumeração) e cria entrada no audit log.
#
# SC-004: 100% das tentativas de login Admin via REST API retornam 401
# SC-005: Cada tentativa bloqueada gera entrada no log de segurança
#
# Fluxo de autenticação (direto no Odoo, sem Kong):
#   1. POST /api/v1/auth/token  (client_credentials) → JWT de aplicação
#   2. POST /api/v1/users/login (com Bearer JWT)      → bloqueado com 401
#
# Credenciais lidas de 18.0/.env automaticamente.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "${SCRIPT_DIR}/../18.0/.env" ] && source "${SCRIPT_DIR}/../18.0/.env" || true

BASE_URL="${BASE_URL:-${ODOO_BASE_URL:-http://localhost:8069}}"
ADMIN_EMAIL="${ADMIN_EMAIL:-${TEST_USER_ADMIN:?'TEST_USER_ADMIN não definido em 18.0/.env'}}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-${TEST_PASSWORD_ADMIN:?'TEST_PASSWORD_ADMIN não definido em 18.0/.env'}}"
BUSINESS_EMAIL="${BUSINESS_EMAIL:-${TEST_USER_OWNER:-}}"
BUSINESS_PASSWORD="${BUSINESS_PASSWORD:-${TEST_PASSWORD_OWNER:-}}"
OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID:?'OAUTH_CLIENT_ID não encontrado — verifique 18.0/.env'}"
OAUTH_CLIENT_SECRET="${OAUTH_CLIENT_SECRET:?'OAUTH_CLIENT_SECRET não encontrado — verifique 18.0/.env'}"
COMPOSE_FILE_DIR="${COMPOSE_FILE_DIR:-${SCRIPT_DIR}/../18.0}"
POSTGRES_DB="${POSTGRES_DB:-realestate}"
POSTGRES_USER="${POSTGRES_USER:-odoo}"

PASS=0
FAIL=0
APP_JWT=""

# --- helpers ------------------------------------------------------------------

green()  { printf "\033[0;32m%s\033[0m\n" "$*"; }
red()    { printf "\033[0;31m%s\033[0m\n" "$*"; }
yellow() { printf "\033[0;33m%s\033[0m\n" "$*"; }

assert_eq() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$actual" == "$expected" ]]; then green "  ✓ $label"; PASS=$((PASS+1))
    else red "  ✗ $label  (esperado='$expected'  atual='$actual')"; FAIL=$((FAIL+1)); fi
}
assert_contains() {
    local label="$1" needle="$2" haystack="$3"
    if echo "$haystack" | grep -q "$needle"; then green "  ✓ $label"; PASS=$((PASS+1))
    else red "  ✗ $label  (esperava '$needle' na resposta)"; FAIL=$((FAIL+1)); fi
}
assert_not_contains() {
    local label="$1" needle="$2" haystack="$3"
    if ! echo "$haystack" | grep -q "$needle"; then green "  ✓ $label"; PASS=$((PASS+1))
    else red "  ✗ $label  ('$needle' não deveria estar na resposta)"; FAIL=$((FAIL+1)); fi
}

# --- step 0: obter JWT de aplicação via client_credentials -------------------

get_app_jwt() {
    echo ""
    yellow "=== Step 0: Obter JWT de aplicação (client_credentials → /api/v1/auth/token) ==="

    APP_JWT=$(curl -s -X POST "${BASE_URL}/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "{\"grant_type\":\"client_credentials\",\"client_id\":\"${OAUTH_CLIENT_ID}\",\"client_secret\":\"${OAUTH_CLIENT_SECRET}\"}" \
        2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

    if [[ -z "$APP_JWT" ]]; then
        red "  ✗ Falha ao obter JWT de aplicação. Verifique OAUTH_CLIENT_ID/SECRET e se o Odoo está rodando."
        exit 1
    fi
    green "  ✓ JWT de aplicação obtido"
}

# --- testes ------------------------------------------------------------------

test_admin_bloqueado() {
    echo ""
    yellow "=== Teste 1: Login do Admin via REST API → 401 (SC-004) ==="

    HTTP_STATUS=$(curl -s -o /tmp/f022_t1.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${APP_JWT}" \
        -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" 2>/dev/null)
    BODY=$(cat /tmp/f022_t1.json 2>/dev/null || echo "")

    assert_eq       "HTTP 401"                                 "401"               "$HTTP_STATUS"
    assert_contains "Resposta contém chave 'error'"            '"error"'           "$BODY"
    assert_contains "Mensagem é 'Invalid credentials' (anti-enumeração)" '"Invalid credentials"' "$BODY"
    assert_not_contains "Sem 'session_id' na resposta"         '"session_id"'      "$BODY"
    assert_not_contains "Sem 'token' na resposta"              '"token"'           "$BODY"
    assert_not_contains "Sem 'Admin' na resposta (anti-enum)"  '"Admin'            "$BODY"
}

test_anti_enumeracao() {
    echo ""
    yellow "=== Teste 2: Resposta idêntica à de credenciais inválidas (anti-enumeração) ==="

    ADM_STATUS=$(curl -s -o /tmp/f022_adm.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${APP_JWT}" \
        -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" 2>/dev/null)

    BAD_STATUS=$(curl -s -o /tmp/f022_bad.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${APP_JWT}" \
        -d '{"email":"usuario-inexistente-f022@example.com","password":"senhaErrada123"}' 2>/dev/null)

    ADM_BODY=$(cat /tmp/f022_adm.json 2>/dev/null || echo "")
    BAD_BODY=$(cat /tmp/f022_bad.json 2>/dev/null || echo "")

    assert_eq "HTTP status idêntico (anti-enumeração)" "$BAD_STATUS" "$ADM_STATUS"
    assert_eq "Body idêntico (anti-enumeração)"        "$BAD_BODY"   "$ADM_BODY"
}

test_audit_log() {
    echo ""
    yellow "=== Teste 3: Tentativa bloqueada gera entrada no audit log (SC-005) ==="

    BEFORE_TS=$(date -u +"%Y-%m-%d %H:%M:%S")

    curl -s -o /dev/null \
        -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${APP_JWT}" \
        -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" 2>/dev/null

    CNT=$(docker compose -f "${COMPOSE_FILE_DIR}/docker-compose.yml" exec -T db \
        psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t -c \
        "SELECT COUNT(*) FROM ir_logging
         WHERE name='auth.login.failed'
           AND message LIKE '%${ADMIN_EMAIL}%'
           AND message LIKE '%Admin API login blocked%'
           AND create_date>='${BEFORE_TS}';" 2>/dev/null | tr -d ' \n' || echo "0")

    assert_eq "Audit log contém entrada para login Admin bloqueado" "1" \
        "$([ "${CNT:-0}" -ge 1 ] 2>/dev/null && echo 1 || echo 0)"
}

test_usuario_negocio_nao_afetado() {
    echo ""
    yellow "=== Teste 4: Login de usuário de negócio funciona normalmente (regressão) ==="

    if [[ -z "$BUSINESS_EMAIL" || -z "$BUSINESS_PASSWORD" ]]; then
        yellow "  ⚠ Ignorado: BUSINESS_EMAIL/BUSINESS_PASSWORD não definidos."
        yellow "    Defina TEST_USER_OWNER e TEST_PASSWORD_OWNER no .env para rodar este teste."
        return
    fi

    HTTP_STATUS=$(curl -s -o /tmp/f022_biz.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${APP_JWT}" \
        -d "{\"email\":\"${BUSINESS_EMAIL}\",\"password\":\"${BUSINESS_PASSWORD}\"}" 2>/dev/null)
    BODY=$(cat /tmp/f022_biz.json 2>/dev/null || echo "")

    assert_eq       "Usuário de negócio retorna HTTP 200" "200"          "$HTTP_STATUS"
    assert_contains "Resposta contém session_id"          '"session_id"' "$BODY"
}

# --- summary ------------------------------------------------------------------

print_summary() {
    echo ""
    echo "========================================"
    echo " Feature 022 — Admin API Block Results  "
    echo "========================================"
    green " PASS: $PASS"
    [[ $FAIL -gt 0 ]] && red " FAIL: $FAIL" || echo " FAIL: $FAIL"
    echo "========================================"
    [[ $FAIL -gt 0 ]] && exit 1 || exit 0
}

# --- main --------------------------------------------------------------------

echo "Feature 022 — Admin API Block Integration Tests"
echo "Base URL : ${BASE_URL}"
echo "Admin    : ${ADMIN_EMAIL}"
echo "Negócio  : ${BUSINESS_EMAIL:-'(não definido — teste 4 será ignorado)'}"

get_app_jwt
test_admin_bloqueado
test_anti_enumeracao
test_audit_log
test_usuario_negocio_nao_afetado
print_summary
