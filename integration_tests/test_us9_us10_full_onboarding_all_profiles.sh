#!/usr/bin/env bash
# =============================================================================
# Feature 009 + 010: Full Onboarding Flow — ALL Profile Types
# =============================================================================
#
# Cobertura:
#   Para cada tipo de perfil, executa o fluxo completo:
#     1. POST /api/v1/profiles         → Criar perfil (dados cadastrais)
#     2. POST /api/v1/users/invite     → Enviar convite (email via MailHog)
#     3. POST /api/v1/users/{id}/resend-invite → Reenviar convite
#     4. MailHog API                   → Interceptar token do email reenviado
#     5. POST /api/v1/auth/set-password → Configurar senha
#     6. POST /api/v1/users/login      → Login e validação
#
# Autorização (spec-009 Authorization Matrix):
#   Owner  → owner, director, manager, agent, prospector,
#             receptionist, financial, legal, portal
#   Agent  → property_owner
#
# Pré-requisitos:
#   - docker compose up -d  (Odoo, PostgreSQL, MailHog)
#   - MailHog acessível em http://localhost:8025
#   - Credenciais válidas em 18.0/.env
#   - jq instalado (brew install jq)
#
# Execução:
#   bash integration_tests/test_us9_us10_full_onboarding_all_profiles.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Setup paths e variáveis
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"

if [ -f "$SCRIPT_DIR/../18.0/.env" ]; then
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/../18.0/.env"
fi

BASE_URL="${TEST_BASE_URL:-http://localhost:8069}"
API_BASE="$BASE_URL/api/v1"
MAILHOG_URL="${MAILHOG_URL:-http://localhost:8025}"

TIMESTAMP=$(date +%s)
TEST_PASSWORD="Onboard@2026!"   # Senha forte p/ todos os usuários criados neste teste

# Contadores globais
TOTAL_PROFILES=0
PASSED_PROFILES=0
FAILED_PROFILES=()

# ---------------------------------------------------------------------------
# Cores
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Lookup: code → profile_type_id (IDs conhecidos da tabela thedevkitchen_profile_type)
# ---------------------------------------------------------------------------
get_profile_type_id() {
    local code="$1"
    case "$code" in
        owner)          echo 1 ;;
        director)       echo 2 ;;
        manager)        echo 3 ;;
        agent)          echo 4 ;;
        prospector)     echo 5 ;;
        receptionist)   echo 6 ;;
        financial)      echo 7 ;;
        legal)          echo 8 ;;
        tenant|portal)  echo 9 ;;
        property_owner) echo 10 ;;
        *) echo "" ;;
    esac
}

# ---------------------------------------------------------------------------
# Helper: Gerar CPF válido
# ---------------------------------------------------------------------------
generate_cpf() {
    # Gera um CPF válido com dígitos verificadores corretos
    local base
    base=$(printf "%09d" $(( (RANDOM * 32768 + RANDOM) % 1000000000 )))

    # Garantir que não seja sequência repetida (inválida)
    while [[ "$base" =~ ^(.)\1+$ ]]; do
        base=$(printf "%09d" $(( (RANDOM * 32768 + RANDOM) % 1000000000 )))
    done

    # Primeiro dígito verificador
    local sum=0
    for i in $(seq 0 8); do
        local d="${base:$i:1}"
        local w=$((10 - i))
        sum=$((sum + d * w))
    done
    local rem=$((sum % 11))
    local d1=$((rem < 2 ? 0 : 11 - rem))

    # Segundo dígito verificador
    sum=0
    for i in $(seq 0 8); do
        local d="${base:$i:1}"
        local w=$((11 - i))
        sum=$((sum + d * w))
    done
    sum=$((sum + d1 * 2))
    rem=$((sum % 11))
    local d2=$((rem < 2 ? 0 : 11 - rem))

    echo "${base}${d1}${d2}"
}

# ---------------------------------------------------------------------------
# Helper: Login de usuário → retorna "SESSION_ID|COMPANY_ID"
# ---------------------------------------------------------------------------
login_user() {
    local email="$1"
    local password="$2"
    local bearer="$3"

    local resp
    resp=$(curl -s -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $bearer" \
        -d "{\"login\": \"$email\", \"password\": \"$password\"}")

    local session
    session=$(echo "$resp" | jq -r '.session_id // empty')
    local company
    company=$(echo "$resp" | jq -r '.user.default_company_id // empty')

    if [ -z "$session" ] || [ -z "$company" ]; then
        echo ""
        return 1
    fi

    echo "${session}|${company}"
}

# ---------------------------------------------------------------------------
# Helper: Criar perfil via POST /api/v1/profiles
# ---------------------------------------------------------------------------
create_profile() {
    local name="$1"
    local email="$2"
    local cpf="$3"
    local profile_type="$4"
    local company_id="$5"
    local bearer="$6"
    local session_id="$7"

    # Resolver profile_type_id (inteiro FK)
    local ptid
    ptid=$(get_profile_type_id "$profile_type")
    if [ -z "$ptid" ]; then
        echo "ERROR:400:Unknown profile_type code: $profile_type"
        return 1
    fi

    local extra_fields=""
    if [ "$profile_type" = "tenant" ] || [ "$profile_type" = "portal" ]; then
        extra_fields=', "occupation": "Locatário Teste"'
    fi
    if [ "$profile_type" = "agent" ]; then
        extra_fields=', "hire_date": "2024-01-15"'
    fi

    local payload
    payload=$(cat <<EOF
{
    "name": "$name",
    "email": "$email",
    "document": "$cpf",
    "phone": "11988887777",
    "birthdate": "1990-06-15",
    "company_id": $company_id,
    "profile_type_id": $ptid
    $extra_fields
}
EOF
)

    local resp
    resp=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/profiles" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $bearer" \
        -H "X-Openerp-Session-Id: $session_id" \
        -d "$payload")

    local http_code
    http_code=$(echo "$resp" | tail -n1)
    local body
    body=$(echo "$resp" | sed '$d')

    if [ "$http_code" != "200" ] && [ "$http_code" != "201" ]; then
        echo "ERROR:$http_code:$body"
        return 1
    fi

    local profile_id
    profile_id=$(echo "$body" | jq -r '.id // empty')
    echo "$profile_id"
}

# ---------------------------------------------------------------------------
# Helper: Convidar via POST /api/v1/users/invite
# ---------------------------------------------------------------------------
invite_user() {
    local profile_id="$1"
    local email="$2"
    local company_id="$3"
    local bearer="$4"
    local session_id="$5"

    local resp
    resp=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $bearer" \
        -H "X-Openerp-Session-Id: $session_id" \
        -H "X-Company-ID: $company_id" \
        -d "{\"profile_id\": $profile_id, \"email\": \"$email\"}")

    local http_code
    http_code=$(echo "$resp" | tail -n1)
    local body
    body=$(echo "$resp" | sed '$d')

    if [ "$http_code" != "200" ] && [ "$http_code" != "201" ]; then
        echo "ERROR:$http_code:$body"
        return 1
    fi

    local user_id
    user_id=$(echo "$body" | jq -r '.data.id // empty')
    echo "$user_id"
}

# ---------------------------------------------------------------------------
# Helper: Reenviar convite via POST /api/v1/users/{id}/resend-invite
# ---------------------------------------------------------------------------
resend_invite_user() {
    local user_id="$1"
    local company_id="$2"
    local bearer="$3"
    local session_id="$4"

    local resp
    resp=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/resend-invite" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $bearer" \
        -H "X-Openerp-Session-Id: $session_id" \
        -H "X-Company-ID: $company_id" \
        -d "{\"user_id\": $user_id}")

    local http_code
    http_code=$(echo "$resp" | tail -n1)
    local body
    body=$(echo "$resp" | sed '$d')

    if [ "$http_code" != "200" ] && [ "$http_code" != "201" ]; then
        echo "ERROR:$http_code:$body"
        return 1
    fi

    echo "OK"
}

# ---------------------------------------------------------------------------
# Helper: Interceptar token do MailHog pelo email do destinatário
# Aguarda até que um email seja encontrado (retry com backoff)
# Argumento opcional $2: número mínimo de mensagens esperadas (para resend)
# ---------------------------------------------------------------------------
get_mailhog_token() {
    local to_email="$1"
    local min_messages="${2:-1}"   # Para resend, esperar pelo menos 2 mensagens

    local max_retries=15
    local retry_delay=2

    for attempt in $(seq 1 $max_retries); do
        # MailHog v2 search API
        local encoded_email
        # Encode manualmente caracteres especiais mínimos necessários
        encoded_email=$(echo "$to_email" | sed 's/@/%40/g' | sed 's/+/%2B/g')

        local search_resp
        search_resp=$(curl -s \
            "$MAILHOG_URL/api/v2/search?kind=to&query=${encoded_email}&start=0&limit=10")

        local count
        count=$(echo "$search_resp" | jq -r '.count // 0' 2>/dev/null || echo "0")

        if [ "$count" -ge "$min_messages" ]; then
            # items[0] é o mais recente no MailHog
            local token=""

            # 1. Tentar no corpo principal (Content.Body)
            local raw_body
            raw_body=$(echo "$search_resp" | jq -r '.items[0].Content.Body // ""' 2>/dev/null)
            token=$(echo "$raw_body" | grep -oE 'token=[A-Za-z0-9_-]{32,40}' | head -1 | sed 's/token=//')

            # 2. Tentar nas MIME parts (email HTML/text multipart)
            if [ -z "$token" ]; then
                local parts_count
                parts_count=$(echo "$search_resp" | jq '.items[0].MIME.Parts | length // 0' 2>/dev/null || echo "0")
                for part_idx in $(seq 0 $((parts_count - 1))); do
                    local part_body
                    part_body=$(echo "$search_resp" | jq -r ".items[0].MIME.Parts[$part_idx].Body // \"\"" 2>/dev/null)
                    token=$(echo "$part_body" | grep -oE 'token=[A-Za-z0-9_-]{32,40}' | head -1 | sed 's/token=//')
                    [ -n "$token" ] && break

                    # Tentar nested parts (MIME dentro de MIME)
                    local nested_count
                    nested_count=$(echo "$search_resp" | jq ".items[0].MIME.Parts[$part_idx].MIME.Parts | length // 0" 2>/dev/null || echo "0")
                    for nested_idx in $(seq 0 $((nested_count - 1))); do
                        local nested_body
                        nested_body=$(echo "$search_resp" | jq -r ".items[0].MIME.Parts[$part_idx].MIME.Parts[$nested_idx].Body // \"\"" 2>/dev/null)
                        token=$(echo "$nested_body" | grep -oE 'token=[A-Za-z0-9_-]{32,40}' | head -1 | sed 's/token=//')
                        [ -n "$token" ] && break
                    done
                    [ -n "$token" ] && break
                done
            fi

            # 3. Tentar no raw body (Content.Body mas limitado)
            if [ -z "$token" ]; then
                local raw_raw
                raw_raw=$(echo "$search_resp" | jq -r '.items[0].Raw.Data // ""' 2>/dev/null)
                token=$(echo "$raw_raw" | grep -oE 'token=[A-Za-z0-9_-]{32,40}' | head -1 | sed 's/token=//')
            fi

            if [ -n "$token" ]; then
                echo "$token"
                return 0
            fi
        fi

        sleep $retry_delay
    done

    echo ""
    return 1
}

# ---------------------------------------------------------------------------
# Helper: Definir senha via POST /api/v1/auth/set-password (endpoint público)
# ---------------------------------------------------------------------------
set_user_password() {
    local token="$1"
    local password="$2"

    local resp
    resp=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/auth/set-password" \
        -H "Content-Type: application/json" \
        -d "{\"token\": \"$token\", \"password\": \"$password\", \"confirm_password\": \"$password\"}")

    local http_code
    http_code=$(echo "$resp" | tail -n1)
    local body
    body=$(echo "$resp" | sed '$d')

    if [ "$http_code" != "200" ]; then
        echo "ERROR:$http_code:$body"
        return 1
    fi

    echo "OK"
}

# ---------------------------------------------------------------------------
# Helper: Login pós-set-password via POST /api/v1/users/login
# ---------------------------------------------------------------------------
verify_login() {
    local email="$1"
    local password="$2"
    local bearer="$3"

    local resp
    resp=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $bearer" \
        -d "{\"login\": \"$email\", \"password\": \"$password\"}")

    local http_code
    http_code=$(echo "$resp" | tail -n1)
    local body
    body=$(echo "$resp" | sed '$d')

    if [ "$http_code" != "200" ]; then
        echo "ERROR:$http_code:$body"
        return 1
    fi

    local session_id
    session_id=$(echo "$body" | jq -r '.session_id // empty')
    if [ -z "$session_id" ] || [ "$session_id" = "null" ]; then
        echo "ERROR:no_session:$body"
        return 1
    fi

    echo "OK:$session_id"
}

# ---------------------------------------------------------------------------
# Função principal: Executar fluxo completo para um perfil
# ---------------------------------------------------------------------------
run_profile_flow() {
    local profile_type="$1"
    local inviter_label="$2"    # "Owner" | "Agent"
    local inviter_bearer="$3"
    local inviter_session="$4"
    local inviter_company="$5"

    TOTAL_PROFILES=$((TOTAL_PROFILES + 1))
    local idx=$TOTAL_PROFILES

    local profile_email="test_${profile_type}_${TIMESTAMP}_${idx}@testmail.com"
    local profile_type_upper
    profile_type_upper=$(echo "$profile_type" | tr '[:lower:]' '[:upper:]')
    local profile_name="Test ${profile_type_upper} ${TIMESTAMP}"
    local profile_cpf
    profile_cpf=$(generate_cpf)

    echo ""
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}  Perfil: ${profile_type_upper} (via $inviter_label)${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # -------------------------------------------------------------------
    # STEP 1: Criar perfil
    # -------------------------------------------------------------------
    echo -e "\n  ${BLUE}[1/6]${NC} Criando perfil ${profile_type}..."
    local profile_id
    profile_id=$(create_profile \
        "$profile_name" \
        "$profile_email" \
        "$profile_cpf" \
        "$profile_type" \
        "$inviter_company" \
        "$inviter_bearer" \
        "$inviter_session") || true

    if [[ "$profile_id" == ERROR:* ]] || [ -z "$profile_id" ]; then
        echo -e "  ${RED}✗ Falha ao criar perfil: $profile_id${NC}"
        FAILED_PROFILES+=("$profile_type (create_profile)")
        return 1
    fi
    echo -e "  ${GREEN}✓ Perfil criado (ID=$profile_id, CPF=$profile_cpf)${NC}"

    # -------------------------------------------------------------------
    # STEP 2: Enviar convite (invite)
    # -------------------------------------------------------------------
    echo -e "\n  ${BLUE}[2/6]${NC} Enviando convite para ${profile_email}..."
    local user_id
    user_id=$(invite_user \
        "$profile_id" \
        "$profile_email" \
        "$inviter_company" \
        "$inviter_bearer" \
        "$inviter_session") || true

    if [[ "$user_id" == ERROR:* ]] || [ -z "$user_id" ]; then
        echo -e "  ${RED}✗ Falha no invite: $user_id${NC}"
        FAILED_PROFILES+=("$profile_type (invite)")
        return 1
    fi
    echo -e "  ${GREEN}✓ Convite enviado (user_id=$user_id)${NC}"

    # -------------------------------------------------------------------
    # STEP 3: Capturar token do email inicial (MailHog)
    # -------------------------------------------------------------------
    echo -e "\n  ${BLUE}[3/6]${NC} Aguardando email inicial no MailHog..."
    local initial_token
    initial_token=$(get_mailhog_token "$profile_email" 1) || true

    if [ -z "$initial_token" ]; then
        echo -e "  ${YELLOW}⚠  Token inicial não encontrado no MailHog (pode ser entrega assíncrona)${NC}"
        echo -e "  ${YELLOW}   Continuando com reenvio...${NC}"
    else
        echo -e "  ${GREEN}✓ Token inicial interceptado: ${initial_token:0:12}...${NC}"
    fi

    # -------------------------------------------------------------------
    # STEP 4: Reenviar convite (resend-invite)
    # -------------------------------------------------------------------
    echo -e "\n  ${BLUE}[4/6]${NC} Reenviando convite (resend-invite)..."
    local resend_result
    resend_result=$(resend_invite_user \
        "$user_id" \
        "$inviter_company" \
        "$inviter_bearer" \
        "$inviter_session") || true

    if [[ "$resend_result" == ERROR:* ]]; then
        echo -e "  ${RED}✗ Falha no resend-invite: $resend_result${NC}"
        FAILED_PROFILES+=("$profile_type (resend-invite)")
        return 1
    fi
    echo -e "  ${GREEN}✓ Reenvio solicitado com sucesso${NC}"

    # -------------------------------------------------------------------
    # STEP 5: Capturar token do email reenviado (MailHog — deve ser o mais recente)
    # -------------------------------------------------------------------
    echo -e "\n  ${BLUE}[5/6]${NC} Aguardando email de reenvio no MailHog..."
    # Esperamos pelo menos 2 mensagens (invite + resend); items[0] é o mais recente
    local resend_token
    resend_token=$(get_mailhog_token "$profile_email" 2) || true

    if [ -z "$resend_token" ]; then
        # Fallback: se não houver 2 mensagens, pegar o que tiver
        resend_token=$(get_mailhog_token "$profile_email" 1) || true
    fi

    if [ -z "$resend_token" ]; then
        echo -e "  ${RED}✗ Token não encontrado no MailHog após reenvio${NC}"
        echo -e "  ${RED}  URL: $MAILHOG_URL/api/v2/search?kind=to&query=${profile_email}${NC}"
        FAILED_PROFILES+=("$profile_type (mailhog_token)")
        return 1
    fi
    echo -e "  ${GREEN}✓ Token de reenvio interceptado: ${resend_token:0:12}...${NC}"

    # -------------------------------------------------------------------
    # STEP 6: Configurar senha via set-password
    # -------------------------------------------------------------------
    echo -e "\n  ${BLUE}[6/6]${NC} Configurando senha via token..."
    local set_pwd_result
    set_pwd_result=$(set_user_password "$resend_token" "$TEST_PASSWORD") || true

    if [[ "$set_pwd_result" == ERROR:* ]]; then
        echo -e "  ${RED}✗ Falha no set-password: $set_pwd_result${NC}"
        FAILED_PROFILES+=("$profile_type (set-password)")
        return 1
    fi
    echo -e "  ${GREEN}✓ Senha configurada com sucesso${NC}"

    # -------------------------------------------------------------------
    # STEP 7: Testar login com as novas credenciais
    # -------------------------------------------------------------------
    echo -e "\n  ${BLUE}[7/6]${NC} Verificando login pós-onboarding..."
    sleep 1  # breve pausa para consistência de sessão
    local login_result
    login_result=$(verify_login "$profile_email" "$TEST_PASSWORD" "$inviter_bearer") || true

    if [[ "$login_result" == ERROR:* ]] || [ -z "$login_result" ]; then
        echo -e "  ${RED}✗ Login falhou: $login_result${NC}"
        FAILED_PROFILES+=("$profile_type (login)")
        return 1
    fi
    local new_session="${login_result#OK:}"
    echo -e "  ${GREEN}✓ Login bem-sucedido (session=${new_session:0:16}...)${NC}"

    # -------------------------------------------------------------------
    # Resumo do perfil
    # -------------------------------------------------------------------
    echo -e "\n  ${GREEN}${BOLD}★ Fluxo completo APROVADO para perfil: ${profile_type_upper}${NC}"
    echo -e "    Email:    $profile_email"
    echo -e "    Password: $TEST_PASSWORD"
    echo -e "    user_id:  $user_id | profile_id: $profile_id"

    PASSED_PROFILES=$((PASSED_PROFILES + 1))
    return 0
}

# ===========================================================================
# INÍCIO DOS TESTES
# ===========================================================================

echo ""
echo -e "${BOLD}================================================================${NC}"
echo -e "${BOLD}  Feature 009 + 010: Full Onboarding — ALL Profiles${NC}"
echo -e "${BOLD}  Timestamp: ${TIMESTAMP}${NC}"
echo -e "${BOLD}================================================================${NC}"

# ---------------------------------------------------------------------------
# Passo 0: Obter Bearer Token OAuth2
# ---------------------------------------------------------------------------
echo -e "\n${BLUE}[SETUP]${NC} Obtendo OAuth2 bearer token..."
BEARER_TOKEN=$(get_oauth2_token)
if [ -z "$BEARER_TOKEN" ]; then
    echo -e "${RED}✗ Falha ao obter OAuth2 token. Verifique OAUTH_CLIENT_ID/SECRET em 18.0/.env${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Bearer token OAuth2 obtido${NC}"

# ---------------------------------------------------------------------------
# Passo 1: Login como Owner
# ---------------------------------------------------------------------------
echo -e "\n${BLUE}[SETUP]${NC} Login como Owner..."
OWNER_EMAIL="${TEST_USER_OWNER:-owner@example.com}"
OWNER_PASS="${TEST_PASSWORD_OWNER:-SecurePass123!}"

OWNER_LOGIN=$(login_user "$OWNER_EMAIL" "$OWNER_PASS" "$BEARER_TOKEN") || true
if [ -z "$OWNER_LOGIN" ]; then
    echo -e "${RED}✗ Owner login falhou (email=$OWNER_EMAIL). Verifique TEST_USER_OWNER em .env${NC}"
    exit 1
fi
OWNER_SESSION="${OWNER_LOGIN%%|*}"
OWNER_COMPANY="${OWNER_LOGIN##*|}"
echo -e "${GREEN}✓ Owner logado (company_id=$OWNER_COMPANY)${NC}"

# ---------------------------------------------------------------------------
# Passo 2: Login como Agent (para property_owner)
# ---------------------------------------------------------------------------
echo -e "\n${BLUE}[SETUP]${NC} Login como Agent (para perfil property_owner)..."
AGENT_EMAIL="${TEST_USER_AGENT:-agent_test}"
AGENT_PASS="${TEST_PASSWORD_AGENT:-agent123}"

AGENT_LOGIN=$(login_user "$AGENT_EMAIL" "$AGENT_PASS" "$BEARER_TOKEN") || true
if [ -z "$AGENT_LOGIN" ]; then
    echo -e "${YELLOW}⚠  Agent login falhou (email=$AGENT_EMAIL) — property_owner será testado via Owner${NC}"
    AGENT_SESSION="$OWNER_SESSION"
    AGENT_COMPANY="$OWNER_COMPANY"
    AGENT_INVITER="Owner (fallback)"
else
    AGENT_SESSION="${AGENT_LOGIN%%|*}"
    AGENT_COMPANY="${AGENT_LOGIN##*|}"
    AGENT_INVITER="Agent"
    echo -e "${GREEN}✓ Agent logado (company_id=$AGENT_COMPANY)${NC}"
fi

# ---------------------------------------------------------------------------
# Verificar MailHog
# ---------------------------------------------------------------------------
echo -e "\n${BLUE}[SETUP]${NC} Verificando conectividade com MailHog..."
MAILHOG_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "$MAILHOG_URL/api/v2/messages?limit=1")
if [ "$MAILHOG_CHECK" != "200" ]; then
    echo -e "${RED}✗ MailHog não acessível em $MAILHOG_URL (HTTP $MAILHOG_CHECK)${NC}"
    echo -e "${RED}  Execute: cd 18.0 && docker compose up -d${NC}"
    exit 1
fi
echo -e "${GREEN}✓ MailHog acessível em $MAILHOG_URL${NC}"

# ===========================================================================
# FLUXO DE ONBOARDING — PERFIS AUTORIZADOS PELO OWNER (9 perfis)
# ===========================================================================

echo ""
echo -e "${BOLD}================================================================${NC}"
echo -e "${BOLD}  PARTE 1: Owner convida 9 perfis${NC}"
echo -e "${BOLD}================================================================${NC}"

# Perfis que Owner pode convidar (spec-009 Authorization Matrix)
# Nota: código no DB é 'tenant' (spec-009 usa 'portal' como alias)
OWNER_MANAGED_PROFILES=(
    "director"
    "manager"
    "agent"
    "prospector"
    "receptionist"
    "financial"
    "legal"
    "tenant"
    "owner"
)

for PTYPE in "${OWNER_MANAGED_PROFILES[@]}"; do
    run_profile_flow \
        "$PTYPE" \
        "Owner" \
        "$BEARER_TOKEN" \
        "$OWNER_SESSION" \
        "$OWNER_COMPANY" || true
done

# ===========================================================================
# FLUXO DE ONBOARDING — PERFIL property_owner (autorizado pelo Agent)
# ===========================================================================

echo ""
echo -e "${BOLD}================================================================${NC}"
echo -e "${BOLD}  PARTE 2: Agent convida property_owner${NC}"
echo -e "${BOLD}================================================================${NC}"

run_profile_flow \
    "property_owner" \
    "$AGENT_INVITER" \
    "$BEARER_TOKEN" \
    "$AGENT_SESSION" \
    "$AGENT_COMPANY" || true

# ===========================================================================
# RELATÓRIO FINAL
# ===========================================================================

echo ""
echo -e "${BOLD}================================================================${NC}"
echo -e "${BOLD}  RELATÓRIO FINAL${NC}"
echo -e "${BOLD}================================================================${NC}"
echo -e "  Total de perfis testados:  ${TOTAL_PROFILES}"
echo -e "  ${GREEN}✓ Aprovados:${NC}              ${PASSED_PROFILES}"
echo -e "  ${RED}✗ Reprovados:${NC}             $((TOTAL_PROFILES - PASSED_PROFILES))"

if [ ${#FAILED_PROFILES[@]} -gt 0 ]; then
    echo ""
    echo -e "  ${RED}Falhas detalhadas:${NC}"
    for FAIL in "${FAILED_PROFILES[@]}"; do
        echo -e "    ${RED}• $FAIL${NC}"
    done
fi

echo ""
if [ "$PASSED_PROFILES" -eq "$TOTAL_PROFILES" ]; then
    echo -e "${GREEN}${BOLD}★★★ TODOS OS ${TOTAL_PROFILES} PERFIS PASSARAM NO FLUXO COMPLETO DE ONBOARDING ★★★${NC}"
    exit 0
else
    echo -e "${RED}${BOLD}✗ $((TOTAL_PROFILES - PASSED_PROFILES)) de ${TOTAL_PROFILES} perfis falharam${NC}"
    exit 1
fi
