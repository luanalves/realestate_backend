#!/usr/bin/env bash
# =============================================================================
# test_kong_token_refresh.sh
#
# Testa o mecanismo reativo de refresh de token do Kong:
#   1. Baseline   — verifica que o Kong proxy está respondendo
#   2. Flag manual — simula sinal direto no volume compartilhado e confirma
#                    que o token-refresher detecta e renova o token
#   3. End-to-end  — invalida o token no banco do Odoo, faz uma requisição
#                    real via Kong e verifica o ciclo completo:
#                    Kong 401 → Lua escreve flag → refresher reage
#
# Uso:
#   ./test_kong_token_refresh.sh
#
# Variáveis de ambiente (opcionais):
#   BASE_URL        URL base do Kong  (default: produção)
#   REMOTE_HOST     Host SSH          (default: root@148.230.76.211)
#   DB_NAME         Banco Odoo        (default: odoo_production)
#   DB_USER         Usuário psql      (default: odoo_prod_user)
#   DB_CONTAINER    Container psql    (default: imobiliaria-backoffice-hsxgpe-db-1)
# =============================================================================
set -euo pipefail

BASE_URL="${BASE_URL:-https://api.torque-backoffice.thedevkitchen.com.br}"
REMOTE_HOST="${REMOTE_HOST:-root@148.230.76.211}"
DB_NAME="${DB_NAME:-odoo_production}"
DB_USER="${DB_USER:-odoo_prod_user}"
DB_CONTAINER="${DB_CONTAINER:-imobiliaria-backoffice-hsxgpe-db-1}"
FLAG_FILE="/tmp/kong-signals/needs_refresh"

PASS=0
FAIL=0

pass()    { echo "  ✓ $1"; PASS=$((PASS + 1)); }
fail()    { echo "  ✗ $1"; FAIL=$((FAIL + 1)); }
section() { echo ""; echo "━━━ $1"; }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
remote() { ssh -o ConnectTimeout=10 -o BatchMode=yes "$REMOTE_HOST" "$@"; }

# Retorna o Bearer token atualmente injetado pelo Kong no request-transformer.
get_current_token() {
  remote "curl -s http://localhost:8001/plugins" | \
    python3 -c "
import sys, json
plugins = json.load(sys.stdin)['data']
rt = next((p for p in plugins if p['name'] == 'request-transformer'), None)
if not rt:
    sys.exit(1)
cfg = rt['config']
for section in ('replace', 'add'):
    headers = cfg.get(section, {}).get('headers', []) or []
    for h in headers:
        if 'Authorization' in h and 'Bearer' in h:
            print(h.split('Bearer ')[-1].strip())
            sys.exit(0)
" 2>/dev/null
}

# Conta linhas de log do token-refresher (âncora temporal).
log_anchor() {
  remote "docker logs kong-token-refresher 2>&1 | wc -l" 2>/dev/null | tr -d '[:space:]'
}

# Aguarda PATTERN aparecer em linhas de log APÓS a âncora, por até MAX_SECS.
wait_for_log_after() {
  local pattern="$1"
  local anchor="$2"
  local max_secs="${3:-20}"
  local i=0
  while [ "$i" -lt "$max_secs" ]; do
    sleep 1
    i=$((i + 1))
    local count
    count=$(remote "docker logs kong-token-refresher 2>&1 | tail -n +$((anchor + 1)) | grep -c '$pattern' || true" \
      2>/dev/null | tr -d '[:space:]')
    if echo "$count" | grep -qE '^[1-9][0-9]*$'; then
      return 0
    fi
  done
  return 1
}

# ---------------------------------------------------------------------------
# TEST 1 — Baseline
# ---------------------------------------------------------------------------
section "TEST 1 — Baseline"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
  -X POST "${BASE_URL}/api/v1/auth/token" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials&client_id=probe&client_secret=probe' \
  2>/dev/null || echo "000")

if [ "$HTTP" != "000" ] && [ "$HTTP" != "502" ] && [ "$HTTP" != "504" ]; then
  pass "Kong proxy respondendo (HTTP $HTTP)"
else
  fail "Kong proxy com problema (HTTP $HTTP)"
fi

# ---------------------------------------------------------------------------
# TEST 2 — Flag manual
# ---------------------------------------------------------------------------
section "TEST 2 — Sinal via flag manual"

TOKEN_BEFORE=$(get_current_token)
if [ -z "$TOKEN_BEFORE" ]; then
  fail "Não foi possível obter o token atual do Kong"
else
  pass "Token atual obtido: ${TOKEN_BEFORE:0:25}..."
fi

ANCHOR_2=$(log_anchor)
echo "  → Escrevendo flag no volume compartilhado (como root)..."
remote "docker exec --user root kong-gateway sh -c \
  'mkdir -p /tmp/kong-signals && chmod 777 /tmp/kong-signals && echo 1 > $FLAG_FILE'" 2>&1

echo "  → Aguardando token-refresher detectar o sinal (≤ 15s)..."
if wait_for_log_after "Sinal de token inv" "$ANCHOR_2" 15; then
  pass "Sinal detectado pelo token-refresher"
else
  fail "token-refresher não detectou o sinal em 15s"
fi

FLAG_EXISTS=$(remote "docker exec kong-token-refresher sh -c '[ -f $FLAG_FILE ] && echo yes || echo no'" 2>/dev/null || echo "unknown")
if [ "$FLAG_EXISTS" = "no" ]; then
  pass "Flag file removido após consumo"
else
  fail "Flag file ainda existe (esperado: removido)"
fi

echo "  → Aguardando novo token ser aplicado (≤ 15s)..."
sleep 8
TOKEN_AFTER=$(get_current_token)
if [ -n "$TOKEN_AFTER" ] && [ "$TOKEN_AFTER" != "$TOKEN_BEFORE" ]; then
  pass "Novo token aplicado: ${TOKEN_AFTER:0:25}..."
elif [ "$TOKEN_AFTER" = "$TOKEN_BEFORE" ]; then
  fail "Token não foi atualizado (igual ao anterior)"
else
  fail "Não foi possível ler o token após refresh"
fi

# ---------------------------------------------------------------------------
# TEST 3 — End-to-end
# ---------------------------------------------------------------------------
section "TEST 3 — End-to-end (invalidação real no DB)"

TOKEN_E2E=$(get_current_token)
if [ -z "$TOKEN_E2E" ]; then
  fail "Token atual não disponível — pulando teste E2E"
else
  pass "Token E2E obtido: ${TOKEN_E2E:0:25}..."

  echo "  → Revogando token no banco do Odoo ($DB_CONTAINER)..."
  DB_PASS=$(remote "grep '^DB_PASSWORD=' \
    /etc/dokploy/compose/imobiliaria-backoffice-hsxgpe/code/18.0/.env \
    2>/dev/null | cut -d= -f2" 2>/dev/null || echo "")

  REVOKE_OUT=$(remote "docker exec \
    -e PGPASSWORD='${DB_PASS}' \
    $DB_CONTAINER \
    psql -U $DB_USER -d $DB_NAME \
    -c \"UPDATE thedevkitchen_oauth_token SET revoked = true WHERE access_token = '${TOKEN_E2E}';\" \
    2>&1" || echo "EXEC_ERROR")

  if echo "$REVOKE_OUT" | grep -q "UPDATE 1"; then
    pass "Token revogado no banco (UPDATE 1)"
  elif echo "$REVOKE_OUT" | grep -q "UPDATE 0"; then
    fail "Token não encontrado no banco (UPDATE 0)"
  else
    fail "Falha ao revogar: $REVOKE_OUT"
  fi

  echo "  → Fazendo requisição via Kong (deve retornar 401 do Odoo)..."
  ANCHOR_3=$(log_anchor)
  # Requisição direta ao Kong via SSH (localhost:8000) para garantir
  # que passa pelo Kong (que injeta o token revogado) sem depender de proxy externo
  HTTP_E2E=$(remote "curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
    'http://localhost:8000/api/v1/test/protected'" 2>/dev/null || true)
  [ -z "$HTTP_E2E" ] && HTTP_E2E="000"

  if [ "$HTTP_E2E" = "401" ]; then
    pass "Kong retornou 401 (token revogado detectado pelo Odoo)"
  else
    fail "Esperado 401, obtido HTTP $HTTP_E2E"
  fi

  echo "  → Aguardando Kong → Lua → flag → refresher (≤ 20s)..."
  if wait_for_log_after "Sinal de token inv" "$ANCHOR_3" 20; then
    pass "Token-refresher reagiu ao 401 do Odoo (ciclo completo)"
  else
    fail "Token-refresher não reagiu em 20s — verifique: docker logs kong-token-refresher"
  fi

  echo "  → Aguardando novo token ser aplicado (≤ 15s)..."
  sleep 8
  TOKEN_E2E_AFTER=$(get_current_token)
  if [ -n "$TOKEN_E2E_AFTER" ] && [ "$TOKEN_E2E_AFTER" != "$TOKEN_E2E" ]; then
    pass "Novo token aplicado após invalidação E2E"
  else
    fail "Token não foi renovado após invalidação E2E"
  fi

  echo "  → Verificando que requisição volta a funcionar..."
  HTTP_FINAL=$(remote "curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
    'http://localhost:8000/api/v1/test/protected'" 2>/dev/null || true)
  [ -z "$HTTP_FINAL" ] && HTTP_FINAL="000"
  if [ "$HTTP_FINAL" != "000" ] && [ "$HTTP_FINAL" != "500" ] && [ "$HTTP_FINAL" != "502" ]; then
    pass "Requisição restaurada após refresh (HTTP $HTTP_FINAL)"
  else
    fail "Requisição ainda falha após refresh (HTTP $HTTP_FINAL)"
  fi
fi

# ---------------------------------------------------------------------------
# Resultado final
# ---------------------------------------------------------------------------
section "RESULTADO"
echo ""
echo "  Passou : $PASS"
echo "  Falhou : $FAIL"
echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "  ✓ Todos os testes passaram."
  exit 0
else
  echo "  ✗ $FAIL teste(s) falharam."
  exit 1
fi
