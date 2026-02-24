#!/usr/bin/env bash
# ===========================================================================
# reset_db.sh — Reseta a base de dados e reinstala os módulos com seed
# ===========================================================================
# Uso: ./reset_db.sh [--no-workers]
#
# O que este script faz:
#   1. Para o Odoo e os workers Celery (mantém db, redis, rabbitmq rodando)
#   2. Dropa e recria o banco 'realestate'
#   3. Instala os módulos com --without-demo=all (carrega apenas seeds)
#   4. Sobe todos os serviços normalmente
#
# Resultado: banco limpo com Imobiliária Seed + todos os perfis RBAC.
#
# Usuário admin Odoo: admin / admin (inalterado)
# Usuários seed:
#   owner@seed.com.br       / seed123  (Owner)
#   director@seed.com.br    / seed123  (Director)
#   manager@seed.com.br     / seed123  (Manager)
#   agent@seed.com.br       / seed123  (Agent)
#   prospector@seed.com.br  / seed123  (Prospector)
#   receptionist@seed.com.br/ seed123  (Receptionist)
#   financial@seed.com.br   / seed123  (Financial)
#   legal@seed.com.br        / seed123  (Legal)
#   tenant@seed.com.br       / seed123  (Tenant/Portal)
#   propowner@seed.com.br    / seed123  (Property Owner/Portal)
# ===========================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Garante execução a partir do diretório 18.0
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DB_NAME="realestate"
DB_USER="odoo"

# Módulos a instalar (ordem importa: dependências primeiro)
MODULES="quicksol_estate,thedevkitchen_branding,thedevkitchen_apigateway,thedevkitchen_user_onboarding"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()    { echo -e "\033[0;34m[INFO]\033[0m  $*"; }
success() { echo -e "\033[0;32m[OK]\033[0m    $*"; }
warn()    { echo -e "\033[0;33m[WARN]\033[0m  $*"; }
error()   { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Verificações iniciais
# ---------------------------------------------------------------------------
command -v docker >/dev/null 2>&1 || error "Docker não encontrado. Instale o Docker."
docker compose version >/dev/null 2>&1 || error "Docker Compose não encontrado."

# Confirma que os serviços de infra estão rodando
if ! docker compose ps db | grep -q "running"; then
    warn "Serviço 'db' não está rodando. Subindo infraestrutura..."
    docker compose up -d db redis rabbitmq
    info "Aguardando PostgreSQL estar pronto..."
    sleep 8
fi

# ---------------------------------------------------------------------------
# 1. Para Odoo e workers Celery
# ---------------------------------------------------------------------------
info "Parando Odoo e workers Celery..."
docker compose stop odoo \
    celery_commission_worker \
    celery_audit_worker \
    celery_notification_worker \
    flower 2>/dev/null || true
success "Serviços de aplicação parados."

# ---------------------------------------------------------------------------
# 2. Dropa e recria o banco de dados
# ---------------------------------------------------------------------------
info "Dropando banco '$DB_NAME'..."
docker compose exec -T db psql -U "$DB_USER" postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();" \
    >/dev/null 2>&1 || true

docker compose exec -T db psql -U "$DB_USER" postgres \
    -c "DROP DATABASE IF EXISTS $DB_NAME;"
success "Banco '$DB_NAME' removido."

info "Criando banco '$DB_NAME'..."
docker compose exec -T db psql -U "$DB_USER" postgres \
    -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
success "Banco '$DB_NAME' criado."

# ---------------------------------------------------------------------------
# 3. Instala módulos (carrega seeds, sem demo data do Odoo core)
# ---------------------------------------------------------------------------
info "Instalando módulos: $MODULES"
info "Este processo pode levar de 3 a 8 minutos..."

docker compose run --rm \
    -e CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672/ \
    -e CELERY_RESULT_BACKEND=redis://redis:6379/2 \
    odoo \
    odoo \
        -d "$DB_NAME" \
        -i "$MODULES" \
        --without-demo=all \
        --stop-after-init \
        --log-level=warn

success "Módulos instalados e seeds carregados."

# ---------------------------------------------------------------------------
# 4. Sobe todos os serviços
# ---------------------------------------------------------------------------
info "Subindo todos os serviços..."
docker compose up -d
success "Todos os serviços iniciados."

# ---------------------------------------------------------------------------
# Resumo
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
success "Reset concluído com sucesso!"
echo "============================================================"
echo ""
echo "  Odoo UI:              http://localhost:8069"
echo "  Admin Odoo:           admin / admin"
echo ""
echo "  Usuários Seed (todos com senha 'seed123'):"
echo "    owner@seed.com.br         → Owner"
echo "    director@seed.com.br      → Director"
echo "    manager@seed.com.br       → Manager"
echo "    agent@seed.com.br         → Agent"
echo "    prospector@seed.com.br    → Prospector"
echo "    receptionist@seed.com.br  → Receptionist"
echo "    financial@seed.com.br     → Financial"
echo "    legal@seed.com.br         → Legal"
echo "    tenant@seed.com.br        → Tenant (Portal)"
echo "    propowner@seed.com.br     → Property Owner (Portal)"
echo ""
echo "  Empresa Seed: Imobiliária Seed (CNPJ 55.444.333/0001-00)"
echo "  Flower (Celery):      http://localhost:5555"
echo "============================================================"
