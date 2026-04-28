#!/usr/bin/env bash
# seed_proposals_fix_states.sh
# Phase 2: corrige os estados FSM das proposals de seed via SQL direto.
# Deve ser executado APÓS seed_proposals_create.sh.
#
# Uso (a partir da raiz do repositório):
#   ./scripts/seed_proposals_fix_states.sh

set -euo pipefail

COMPOSE="docker compose -f 18.0/docker-compose.yml"
DB_CMD="$COMPOSE exec -T db psql -U odoo -d realestate"

echo "==> Ajustando estados FSM das proposals de seed..."
$DB_CMD <<'SQL'
UPDATE real_estate_proposal SET
    state = 'sent',
    sent_date = NOW() - INTERVAL '2 hours'
WHERE id = (SELECT res_id FROM ir_model_data
            WHERE module = 'quicksol_estate' AND name = 'proposal_sent_1');

UPDATE real_estate_proposal SET
    state = 'negotiation',
    sent_date = NOW() - INTERVAL '3 days'
WHERE id = (SELECT res_id FROM ir_model_data
            WHERE module = 'quicksol_estate' AND name = 'proposal_negotiation_1');

UPDATE real_estate_proposal SET
    state = 'accepted',
    sent_date = NOW() - INTERVAL '7 days',
    accepted_date = NOW() - INTERVAL '2 days'
WHERE id = (SELECT res_id FROM ir_model_data
            WHERE module = 'quicksol_estate' AND name = 'proposal_accepted_1');

UPDATE real_estate_proposal SET
    state = 'rejected',
    sent_date = NOW() - INTERVAL '10 days',
    rejected_date = NOW() - INTERVAL '5 days'
WHERE id = (SELECT res_id FROM ir_model_data
            WHERE module = 'quicksol_estate' AND name = 'proposal_rejected_1');

UPDATE real_estate_proposal SET
    state = 'cancelled'
WHERE id = (SELECT res_id FROM ir_model_data
            WHERE module = 'quicksol_estate' AND name = 'proposal_cancelled_1');

UPDATE real_estate_proposal SET
    state = 'expired',
    sent_date = NOW() - INTERVAL '20 days'
WHERE id = (SELECT res_id FROM ir_model_data
            WHERE module = 'quicksol_estate' AND name = 'proposal_expired_1');
SQL

echo "   Estados ajustados."
echo ""
echo "==> Estado final das proposals:"
$DB_CMD -c "SELECT proposal_code, state, proposal_value FROM real_estate_proposal ORDER BY id;"
