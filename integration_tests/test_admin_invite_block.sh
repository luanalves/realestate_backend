#!/usr/bin/env bash
# =============================================================================
# test_admin_invite_block.sh — Feature 022 / ADR-029 / FR-007
# =============================================================================
# Verifica que o endpoint de convite da REST API NÃO aceita convidar um usuário
# com perfil base.group_system. Isso é garantido pela matriz de autorização da
# Feature 009 — sem novo código de guard na Feature 022.
#
# FR-007: Admin não pode ser convidado via API (satisfeito pela Feature 009)
#
# Fluxo: client_credentials → JWT → login como Owner → POST /api/v1/users/invite
# Credenciais lidas de 18.0/.env automaticamente.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "${SCRIPT_DIR}/../18.0/.env" ] && source "${SCRIPT_DIR}/../18.0/.env" || true

BASE_URL="${BASE_URL:-${ODOO_BASE_URL:-http://localhost:8069}}"
OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID:?'OAUTH_CLIENT_ID não encontrado — verifique 18.0/.env'}"
OAUTH_CLIENT_SECRET="${OAUTH_CLIENT_SECRET:?'OAUTH_CLIENT_SECRET não encontrado — verifique 18.0/.env'}"
OWNER_EMAIL="${OWNER_EMAIL:-${TEST_USER_OWNER:-}}"
OWNER_PASSWORD="${OWNER_PASSWORD:-${TEST_PASSWORD_OWNER:-}}"
COMPANY_ID="${TEST_COMPANY_ID:-1}"

PASS=0
FAIL=0
APP_JWT=""
OWNER_SESSION=""

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

check_prerequisites() {
    if [[ -z "$OWNER_EMAIL" || -z "$OWNER_PASSWORD" ]]; then
        yellow ""
        yellow "⚠ TEST_USER_OWNER ou TEST_PASSWORD_OWNER não definidos no .env"
        yellow "  Este teste requer um usuário Owner autenticado para chamar /api/v1/users/invite."
        yellow "  Ignorando teste."
        exit 0
    fi
}

# --- autenticação -------------------------------------------------------------

get_app_jwt() {
    APP_JWT=$(curl -s -X POST "${BASE_URL}/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "{\"grant_type\":\"client_credentials\",\"client_id\":\"${OAUTH_CLIENT_ID}\",\"client_secret\":\"${OAUTH_CLIENT_SECRET}\"}" \
        2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

    if [[ -z "$APP_JWT" ]]; then
        red "  ✗ Falha ao obter JWT de aplicação."
        exit 1
    fi
    green "  ✓ JWT de aplicação obtido"
}

login_owner() {
    OWNER_SESSION=$(curl -s -X POST "${BASE_URL}/api/v1/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${APP_JWT}" \
        -d "{\"email\":\"${OWNER_EMAIL}\",\"password\":\"${OWNER_PASSWORD}\"}" \
        2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")

    if [[ -z "$OWNER_SESSION" ]]; then
        red "  ✗ Login do Owner falhou. Verifique TEST_USER_OWNER e TEST_PASSWORD_OWNER no .env."
        exit 1
    fi
    green "  ✓ Owner autenticado (session_id obtido)"
}

# --- testes ------------------------------------------------------------------

test_admin_nao_convidavel() {
    echo ""
    yellow "=== Teste 1: Convidar perfil system_admin é rejeitado (FR-007) ==="

    HTTP_STATUS=$(curl -s -o /tmp/f022_inv.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${APP_JWT}" \
        -H "X-Openerp-Session-Id: ${OWNER_SESSION}" \
        -d "{
            \"email\": \"fake_admin_$(date +%s)@f022test.invalid\",
            \"name\": \"Fake Admin Feature022\",
            \"profile_type\": \"system_admin\",
            \"company_id\": ${COMPANY_ID}
        }" 2>/dev/null)
    BODY=$(cat /tmp/f022_inv.json 2>/dev/null || echo "")

    assert_eq       "Perfil system_admin é rejeitado (não 200)" "1" \
        "$([ "$HTTP_STATUS" != "200" ] && echo 1 || echo 0)"
    assert_contains "Resposta contém 'error'"  '"error"' "$BODY"
    echo "    HTTP status recebido: ${HTTP_STATUS}"
}

test_agente_ainda_convidavel() {
    echo ""
    yellow "=== Teste 2: Convidar perfil 'agent' ainda funciona (regressão FR-007) ==="

    HTTP_STATUS=$(curl -s -o /tmp/f022_inv_agent.json -w "%{http_code}" \
        -X POST "${BASE_URL}/api/v1/users/invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${APP_JWT}" \
        -H "X-Openerp-Session-Id: ${OWNER_SESSION}" \
        -d "{
            \"email\": \"test_agent_f022_$(date +%s)@f022test.invalid\",
            \"name\": \"Test Agent Feature022\",
            \"profile_type\": \"agent\",
            \"company_id\": ${COMPANY_ID}
        }" 2>/dev/null)

    # Deve ser 200 (criado) ou 400 (validação — ex: domínio .invalid).
    # NÃO deve ser 403 (que indicaria que a matriz de auth bloqueou o perfil 'agent').
    assert_eq "Perfil 'agent' NÃO retorna 403 (não bloqueado pela matriz)" "1" \
        "$([ "$HTTP_STATUS" != "403" ] && echo 1 || echo 0)"
    echo "    HTTP status recebido: ${HTTP_STATUS}"
}

# --- summary ------------------------------------------------------------------

print_summary() {
    echo ""
    echo "========================================"
    echo " Feature 022 — FR-007 Invite Block      "
    echo "========================================"
    green " PASS: $PASS"
    [[ $FAIL -gt 0 ]] && red " FAIL: $FAIL" || echo " FAIL: $FAIL"
    echo "========================================"
    [[ $FAIL -gt 0 ]] && exit 1 || exit 0
}

# --- main --------------------------------------------------------------------

echo "Feature 022 — FR-007: Admin Invite Block Integration Tests"
echo "Base URL : ${BASE_URL}"
echo "Owner    : ${OWNER_EMAIL}"

check_prerequisites

echo ""
yellow "=== Step 0: Autenticação ==="
get_app_jwt
login_owner

test_admin_nao_convidavel
test_agente_ainda_convidavel
print_summary
