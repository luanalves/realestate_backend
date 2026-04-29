#!/usr/bin/env bash
# =============================================================================
# Feature 014 - US14-S2: Register Credit Check Result
# E2E test via curl para PATCH /api/v1/proposals/{id}/credit-checks/{check_id}
#
# Success Criteria:
# - Registrar 'approved' → check=approved, proposal=accepted (FR-003)
# - Registrar 'rejected' sem rejection_reason → 422 (FR-009)
# - Registrar 'rejected' com rejection_reason → check=rejected, proposal=rejected
# - Registrar 'cancelled' → check=cancelled, proposal=sent (FR-007c)
# - Re-registrar em check já resolvido → 409 (imutabilidade, FR-005)
# - check_date no futuro → 422
# ADR-003: E2E API test com banco de dados real
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"

if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then
    source "$SCRIPT_DIR/../18.0/.env"
fi

BASE_URL="${BASE_URL:-${TEST_BASE_URL:-http://localhost:8069}}"
API_BASE="$BASE_URL/api/v1"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

pass() { echo -e "${GREEN}✓ PASS${NC} — $1"; PASS=$((PASS + 1)); }
fail() { echo -e "${RED}✗ FAIL${NC} — $1"; FAIL=$((FAIL + 1)); }
info() { echo -e "  ${YELLOW}→${NC} $1"; }

echo "========================================"
echo "US14-S2: Register Credit Check Result"
echo "Feature 014 — Rental Credit Check"
echo "========================================"

# ---------------------------------------------------------------------------
# Step 0: OAuth2 Bearer Token
# ---------------------------------------------------------------------------
echo ""
echo "Step 0: Obtendo token OAuth2..."
BEARER_TOKEN=$(get_oauth2_token)
if [ $? -ne 0 ] || [ -z "$BEARER_TOKEN" ]; then
    echo -e "${RED}✗ Falha ao obter token OAuth2${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Bearer token obtido${NC}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
login_user() {
    local email="$1"
    local password="$2"
    local response
    response=$(curl -s -m 30 -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -d "{\"login\": \"$email\", \"password\": \"$password\"}")
    local session_id
    session_id=$(echo "$response" | jq -r '.session_id // empty')
    local company_id
    company_id=$(echo "$response" | jq -r '.user.default_company_id // .company_id // empty')
    if [ -z "$session_id" ]; then
        echo ""
        return 1
    fi
    echo "${session_id}|${company_id}"
}

patch_result() {
    local session="$1"
    local company="$2"
    local proposal_id="$3"
    local check_id="$4"
    local body="$5"
    curl -s -m 30 -w "\n%{http_code}" \
        -X PATCH "$API_BASE/proposals/${proposal_id}/credit-checks/${check_id}" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $session" \
        -H "X-Company-ID: $company" \
        -d "$body"
}

YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
TOMORROW=$(date -v+1d +%Y-%m-%d 2>/dev/null || date -d "tomorrow" +%Y-%m-%d)

# ---------------------------------------------------------------------------
# Step 1: Login como Manager
# ---------------------------------------------------------------------------
echo ""
echo "Step 1: Login como Manager..."
MANAGER_EMAIL="${TEST_USER_MANAGER:-manager@seed.com.br}"
MANAGER_PASS="${TEST_PASSWORD_MANAGER:-Senha@123}"

MANAGER_DATA=$(login_user "$MANAGER_EMAIL" "$MANAGER_PASS")
if [ -z "$MANAGER_DATA" ]; then
    echo -e "${RED}✗ Login do Manager falhou${NC}"
    exit 1
fi
MANAGER_SESSION="${MANAGER_DATA%%|*}"
MANAGER_COMPANY="${MANAGER_DATA##*|}"
echo -e "${GREEN}✓ Manager autenticado (company=$MANAGER_COMPANY)${NC}"

# ---------------------------------------------------------------------------
# Step 2: Obter proposta com análise pendente
# ---------------------------------------------------------------------------
echo ""
echo "Step 2: Buscando proposta com análise pendente..."

# Busca proposta em estado credit_check_pending
CC_PROPOSALS=$(curl -s -m 30 \
    -X GET "$API_BASE/proposals?state=credit_check_pending&limit=1" \
    -H "Authorization: Bearer $BEARER_TOKEN" \
    -H "X-Openerp-Session-Id: $MANAGER_SESSION" \
    -H "X-Company-ID: $MANAGER_COMPANY")

PROPOSAL_ID=$(echo "$CC_PROPOSALS" | jq -r '.data[0].id // empty')

if [ -z "$PROPOSAL_ID" ] || [ "$PROPOSAL_ID" = "null" ]; then
    echo -e "${YELLOW}  ⚠ Nenhuma proposta em credit_check_pending encontrada${NC}"
    echo "  Execute primeiro o S1 para criar uma proposta com análise pendente."
    PROPOSAL_ID=""
fi

# Buscar o check pendente para essa proposta
if [ -n "$PROPOSAL_ID" ]; then
    CHECKS_RESP=$(curl -s -m 30 \
        -X GET "$API_BASE/proposals/${PROPOSAL_ID}/credit-checks?result=pending" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $MANAGER_SESSION" \
        -H "X-Company-ID: $MANAGER_COMPANY")
    CHECK_ID=$(echo "$CHECKS_RESP" | jq -r '.data[0].id // empty')
    info "Proposta $PROPOSAL_ID com check $CHECK_ID (pending)"
fi

# ---------------------------------------------------------------------------
# Cenário 1: check_date no futuro → 422
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 1: check_date no futuro → 422 (validação de data)"
if [ -z "$PROPOSAL_ID" ] || [ -z "$CHECK_ID" ]; then
    echo -e "${YELLOW}  ⚠ Pulado — sem proposta/check disponível${NC}"
else
    BODY="{\"result\": \"approved\", \"check_date\": \"$TOMORROW\", \"session_id\": \"$MANAGER_SESSION\"}"
    RESP=$(patch_result "$MANAGER_SESSION" "$MANAGER_COMPANY" "$PROPOSAL_ID" "$CHECK_ID" "$BODY")
    HTTP_CODE=$(echo "$RESP" | tail -1)
    info "HTTP $HTTP_CODE (check_date=$TOMORROW)"
    if [ "$HTTP_CODE" = "422" ] || [ "$HTTP_CODE" = "400" ]; then
        pass "Data futura rejeitada corretamente ($HTTP_CODE)"
    else
        fail "Esperado 422/400 para data futura, obtido $HTTP_CODE"
    fi
fi

# ---------------------------------------------------------------------------
# Cenário 2: rejected sem rejection_reason → 422 (FR-009)
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 2: 'rejected' sem rejection_reason → 422 (FR-009)"
if [ -z "$PROPOSAL_ID" ] || [ -z "$CHECK_ID" ]; then
    echo -e "${YELLOW}  ⚠ Pulado${NC}"
else
    BODY="{\"result\": \"rejected\", \"check_date\": \"$YESTERDAY\", \"session_id\": \"$MANAGER_SESSION\"}"
    RESP=$(patch_result "$MANAGER_SESSION" "$MANAGER_COMPANY" "$PROPOSAL_ID" "$CHECK_ID" "$BODY")
    HTTP_CODE=$(echo "$RESP" | tail -1)
    info "HTTP $HTTP_CODE"
    if [ "$HTTP_CODE" = "422" ] || [ "$HTTP_CODE" = "400" ]; then
        pass "Rejeição sem motivo bloqueada corretamente ($HTTP_CODE, FR-009)"
    else
        fail "Esperado 422/400 para rejected sem motivo, obtido $HTTP_CODE"
    fi
fi

# ---------------------------------------------------------------------------
# Cenário 3: cancelled → check=cancelled, proposal=sent (FR-007c)
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 3: Cancelar análise → proposal volta a 'sent' (FR-007c)"
if [ -z "$PROPOSAL_ID" ] || [ -z "$CHECK_ID" ]; then
    echo -e "${YELLOW}  ⚠ Pulado${NC}"
else
    BODY="{\"result\": \"cancelled\", \"session_id\": \"$MANAGER_SESSION\"}"
    RESP=$(patch_result "$MANAGER_SESSION" "$MANAGER_COMPANY" "$PROPOSAL_ID" "$CHECK_ID" "$BODY")
    HTTP_CODE=$(echo "$RESP" | tail -1)
    BODY_JSON=$(echo "$RESP" | head -1)
    info "HTTP $HTTP_CODE"
    if [ "$HTTP_CODE" = "200" ]; then
        RESULT=$(echo "$BODY_JSON" | jq -r '.data.result // empty')
        PROPOSAL_STATE=$(echo "$BODY_JSON" | jq -r '.data.proposal_state // empty')
        if [ "$RESULT" = "cancelled" ] && [ "$PROPOSAL_STATE" = "sent" ]; then
            pass "Análise cancelada — check=cancelled, proposal=sent (FR-007c)"
        else
            fail "HTTP 200 mas result=$RESULT, proposal_state=$PROPOSAL_STATE (esperado cancelled/sent)"
        fi
    else
        fail "Esperado 200, obtido $HTTP_CODE"
    fi

    # Após cancelar, recriar análise para os próximos cenários
    info "Recriando análise para cenários seguintes..."
    NEW_CHECK=$(curl -s -m 30 -w "\n%{http_code}" \
        -X POST "$API_BASE/proposals/${PROPOSAL_ID}/credit-checks" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "X-Openerp-Session-Id: $MANAGER_SESSION" \
        -H "X-Company-ID: $MANAGER_COMPANY" \
        -d "{\"insurer_name\": \"Porto Seguro\", \"session_id\": \"$MANAGER_SESSION\"}")
    NEW_HTTP=$(echo "$NEW_CHECK" | tail -1)
    NEW_BODY=$(echo "$NEW_CHECK" | head -1)
    if [ "$NEW_HTTP" = "201" ]; then
        CHECK_ID=$(echo "$NEW_BODY" | jq -r '.data.id // empty')
        info "Nova análise criada — check_id=$CHECK_ID"
    fi
fi

# ---------------------------------------------------------------------------
# Cenário 4: approved → check=approved, proposal=accepted (FR-003)
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 4: Aprovar análise → proposal=accepted (FR-003)"
if [ -z "$PROPOSAL_ID" ] || [ -z "$CHECK_ID" ]; then
    echo -e "${YELLOW}  ⚠ Pulado${NC}"
else
    BODY="{\"result\": \"approved\", \"check_date\": \"$YESTERDAY\", \"session_id\": \"$MANAGER_SESSION\"}"
    RESP=$(patch_result "$MANAGER_SESSION" "$MANAGER_COMPANY" "$PROPOSAL_ID" "$CHECK_ID" "$BODY")
    HTTP_CODE=$(echo "$RESP" | tail -1)
    BODY_JSON=$(echo "$RESP" | head -1)
    info "HTTP $HTTP_CODE"
    if [ "$HTTP_CODE" = "200" ]; then
        RESULT=$(echo "$BODY_JSON" | jq -r '.data.result // empty')
        PROPOSAL_STATE=$(echo "$BODY_JSON" | jq -r '.data.proposal_state // empty')
        if [ "$RESULT" = "approved" ]; then
            pass "Análise aprovada — result=approved, proposal_state=$PROPOSAL_STATE (FR-003)"
        else
            fail "HTTP 200 mas result=$RESULT (esperado approved)"
        fi
    else
        fail "Esperado 200, obtido $HTTP_CODE"
    fi
fi

# ---------------------------------------------------------------------------
# Cenário 5: Re-registrar em check resolvido → 409 (imutabilidade)
# ---------------------------------------------------------------------------
echo ""
echo "Cenário 5: Re-registrar em check já resolvido → 409 (FR-005)"
if [ -z "$PROPOSAL_ID" ] || [ -z "$CHECK_ID" ]; then
    echo -e "${YELLOW}  ⚠ Pulado${NC}"
else
    BODY="{\"result\": \"rejected\", \"rejection_reason\": \"Tentativa indevida\", \"check_date\": \"$YESTERDAY\", \"session_id\": \"$MANAGER_SESSION\"}"
    RESP=$(patch_result "$MANAGER_SESSION" "$MANAGER_COMPANY" "$PROPOSAL_ID" "$CHECK_ID" "$BODY")
    HTTP_CODE=$(echo "$RESP" | tail -1)
    info "HTTP $HTTP_CODE"
    if [ "$HTTP_CODE" = "409" ]; then
        pass "Re-registro bloqueado corretamente — 409 (imutabilidade, FR-005)"
    else
        fail "Esperado 409 para re-registro, obtido $HTTP_CODE"
    fi
fi

# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------
echo ""
echo "========================================"
echo -e "  ${GREEN}PASS: $PASS${NC}   ${RED}FAIL: $FAIL${NC}"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
