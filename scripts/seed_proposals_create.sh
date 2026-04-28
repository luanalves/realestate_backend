#!/usr/bin/env bash
# seed_proposals_create.sh
# Phase 1: limpa e recria os registros de seed de propostas via upgrade do módulo.
# Os estados ficam como draft/queued (comportamento padrão do FSM).
# Rode seed_proposals_fix_states.sh em seguida para corrigir os estados.
#
# Uso (a partir da raiz do repositório):
#   ./scripts/seed_proposals_create.sh

set -euo pipefail

COMPOSE="docker compose -f 18.0/docker-compose.yml"
DB_CMD="$COMPOSE exec -T db psql -U odoo -d realestate"

echo "==> Limpando proposals e assignments de seed anteriores..."
$DB_CMD <<'SQL'
DELETE FROM real_estate_proposal;
DELETE FROM real_estate_agent_property_assignment
  WHERE id IN (
    SELECT res_id FROM ir_model_data
    WHERE module = 'quicksol_estate' AND name LIKE 'assignment_%'
  );
DELETE FROM ir_model_data
  WHERE module = 'quicksol_estate' AND name LIKE 'proposal_%';
DELETE FROM ir_model_data
  WHERE module = 'quicksol_estate' AND name LIKE 'assignment_%';
SQL
echo "   Limpeza concluída."

echo ""
echo "==> Executando upgrade do módulo (cria registros via FSM)..."
docker exec odoo18 odoo \
  --config=/etc/odoo/odoo.conf \
  -u quicksol_estate \
  --stop-after-init \
  --log-level=warn 2>&1 | grep -v opentelemetry | grep -v "View error context" || true
echo "   Upgrade concluído."

echo ""
echo "==> Proposals criadas:"
$DB_CMD -c "SELECT proposal_code, state FROM real_estate_proposal ORDER BY id;"

echo ""
echo "Execute ./scripts/seed_proposals_fix_states.sh para ajustar os estados FSM."
