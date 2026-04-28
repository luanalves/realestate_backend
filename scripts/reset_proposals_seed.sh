#!/usr/bin/env bash
# reset_proposals_seed.sh
# Resets proposal seed data to cover all 8 FSM states.
# Safe to run multiple times.
#
# Usage:
#   ./scripts/reset_proposals_seed.sh
#
# Must be run from the repo root.

set -euo pipefail

COMPOSE="docker compose -f 18.0/docker-compose.yml"
DB_CMD="$COMPOSE exec -T db psql -U odoo -d realestate"

echo "=== Phase 0: Clean existing seed proposals ==="
$DB_CMD <<'SQL'
DELETE FROM real_estate_proposal;
DELETE FROM real_estate_agent_property_assignment
  WHERE id IN (
    SELECT res_id FROM ir_model_data
    WHERE module = 'quicksol_estate'
      AND name LIKE 'assignment_%'
  );
DELETE FROM ir_model_data
  WHERE module = 'quicksol_estate'
    AND name LIKE 'proposal_%';
DELETE FROM ir_model_data
  WHERE module = 'quicksol_estate'
    AND name LIKE 'assignment_%';
SQL
echo "   Cleaned."

echo ""
echo "=== Phase 1: Upgrade module (creates proposals via FSM) ==="
docker exec odoo18 odoo \
  --config=/etc/odoo/odoo.conf \
  -u quicksol_estate \
  --stop-after-init \
  --log-level=warn 2>&1 | grep -v opentelemetry | grep -v "View error context" || true
echo "   Upgrade done."

echo ""
echo "=== Phase 2: Fix FSM states via SQL ==="
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

SELECT proposal_code, state, proposal_value FROM real_estate_proposal ORDER BY id;
SQL

echo ""
echo "=== Done. Proposals reset with all 8 FSM states. ==="
