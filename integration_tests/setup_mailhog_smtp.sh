#!/bin/bash
# =============================================================================
# setup_mailhog_smtp.sh
# Configures MailHog as Odoo's outgoing SMTP server for integration testing.
# 
# Must be run ONCE after each fresh database setup (e.g., reset_db.sh).
# Without this, Odoo does not send emails, causing test_us9_us10 to hang.
#
# Dependencies:
#   - Docker Compose running in 18.0/ (db + odoo + mailhog containers)
#   - MailHog accessible at mailhog:1025 (internal Docker network)
#
# Usage:
#   cd integration_tests
#   bash setup_mailhog_smtp.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_DIR="$REPO_ROOT/18.0"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

echo "================================================================"
echo "  Setup: MailHog SMTP para Odoo (ambiente de testes)"
echo "================================================================"

# 1. Verify MailHog is reachable
echo ""
echo "[1/3] Verificando MailHog..."
if ! curl -sf "http://localhost:8025/api/v2/messages" > /dev/null 2>&1; then
    fail "MailHog não está acessível em localhost:8025. Verifique se os containers estão rodando: cd 18.0 && docker compose up -d"
fi
log "MailHog acessível em localhost:8025"

# 2. Test SMTP connection from Odoo container
echo ""
echo "[2/3] Testando conexão SMTP Odoo → mailhog:1025..."
if ! docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T odoo python3 -c \
    "import smtplib; s=smtplib.SMTP('mailhog',1025); s.quit(); print('OK')" 2>/dev/null | grep -q OK; then
    fail "Odoo container não consegue conectar a mailhog:1025. Verifique a rede Docker."
fi
log "Conexão SMTP OK (mailhog:1025 acessível do container odoo)"

# 3. Check and insert ir_mail_server
echo ""
echo "[3/3] Configurando ir_mail_server no banco Odoo..."

EXISTING=$(docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T db \
    psql -U odoo -d realestate -tAc \
    "SELECT COUNT(*) FROM ir_mail_server WHERE smtp_host='mailhog' AND smtp_port=1025;" 2>/dev/null || echo "0")

if [ "$EXISTING" -gt "0" ]; then
    warn "MailHog já está configurado em ir_mail_server (${EXISTING} registro(s)). Nada a fazer."
else
    docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T db \
        psql -U odoo -d realestate -c \
        "INSERT INTO ir_mail_server (name, smtp_host, smtp_port, smtp_encryption, smtp_authentication, active, sequence, create_uid, write_uid, create_date, write_date) VALUES ('MailHog (Test)', 'mailhog', 1025, 'none', 'login', TRUE, 1, 1, 1, NOW(), NOW()) RETURNING id, name, smtp_host, smtp_port;" 2>/dev/null

    log "Servidor SMTP 'MailHog (Test)' inserido com sucesso"
fi

echo ""
echo "================================================================"
echo "  SMTP configurado! Odoo agora envia emails via MailHog."
echo "  UI: http://localhost:8025"
echo "================================================================"
echo ""
echo "  Próximo passo: execute os testes de onboarding:"
echo "    cd integration_tests"
echo "    bash test_us9_us10_full_onboarding_all_profiles.sh"
echo ""
