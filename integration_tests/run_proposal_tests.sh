#!/usr/bin/env bash
# Run all Feature 013 (Property Proposals) integration tests
# Usage: bash integration_tests/run_proposal_tests.sh
#
# Overrides OAuth credentials with test-specific values (test-client-id)
# so that integration tests are isolated from production credentials in .env

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd "$SCRIPT_DIR/../18.0" && pwd)"

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BOLD='\033[1m'; NC='\033[0m'

# ── Test credentials (override .env production values) ───────────────────────
# _PROPOSAL_TEST_ENV=1 prevents test scripts from sourcing 18.0/.env (which has
# production OAuth credentials that would overwrite these test credentials).
export _PROPOSAL_TEST_ENV=1
export BASE_URL="${BASE_URL:-http://localhost:8069}"
export OAUTH_CLIENT_ID="test-client-id"
export OAUTH_CLIENT_SECRET="test-client-secret-12345"
export TEST_USER_OWNER="${TEST_USER_OWNER:-owner@seed.com.br}"
export TEST_PASSWORD_OWNER="${TEST_PASSWORD_OWNER:-seed123}"
export TEST_AGENT_ID="${TEST_AGENT_ID:-8}"
# Use property 117 (Sala Comercial Seed) which starts with only a rejected
# proposal — ensures new proposals begin in 'draft' state (not 'queued').
export PROPOSAL_TEST_PROPERTY_ID="${PROPOSAL_TEST_PROPERTY_ID:-117}"

# ── Test data cleanup ─────────────────────────────────────────────────────────
# Delete all non-seed proposals for company 5 before each test so tests are
# independent. Seed proposals (defined in seed_proposals.xml) are preserved by
# querying their IDs from ir.model.data.
cleanup_proposals() {
  docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T db \
    psql -U odoo -d realestate -c "
DELETE FROM real_estate_proposal
WHERE company_id = 5
  AND id NOT IN (
    SELECT res_id FROM ir_model_data
    WHERE module = 'quicksol_estate'
      AND name LIKE 'seed_proposal%'
      AND model = 'real.estate.proposal'
  );" > /dev/null 2>&1 && true
}

PASS_TOTAL=0; FAIL_TOTAL=0
RESULTS=()

run_test() {
  local name="$1" file="$2"
  echo -e "\n${BOLD}━━━ $name ━━━${NC}"
  cleanup_proposals
  local output
  output=$(bash "$file" 2>&1) || true
  echo "$output"

  local p f
  p=$(echo "$output" | grep -c "PASSED:" || true)
  f=$(echo "$output" | grep -c "FAILED:" || true)
  # Extract actual numbers from "PASSED: N, FAILED: M"
  local pass_count fail_count
  pass_count=$(echo "$output" | grep -o 'PASSED: [0-9]*' | grep -o '[0-9]*' | tail -1 || echo 0)
  fail_count=$(echo "$output" | grep -o 'FAILED: [0-9]*' | grep -o '[0-9]*' | tail -1 || echo 0)
  pass_count=${pass_count:-0}; fail_count=${fail_count:-0}
  PASS_TOTAL=$((PASS_TOTAL + pass_count))
  FAIL_TOTAL=$((FAIL_TOTAL + fail_count))

  if [ "$fail_count" -eq 0 ] && [ "$pass_count" -gt 0 ]; then
    RESULTS+=("${GREEN}✓ PASS${NC}  $name ($pass_count passed)")
  else
    RESULTS+=("${RED}✗ FAIL${NC}  $name ($pass_count passed, $fail_count failed)")
  fi
}

# ── Run tests ─────────────────────────────────────────────────────────────────
echo -e "${BOLD}Feature 013 — Property Proposals Integration Tests${NC}"
echo -e "Base URL: $BASE_URL | User: $TEST_USER_OWNER | Agent: $TEST_AGENT_ID\n"

run_test "T044 Accept & Reject"       "$SCRIPT_DIR/test_us4_proposal_accept_reject.sh"
run_test "T032 FIFO Queue"            "$SCRIPT_DIR/test_us2_proposal_fifo_queue.sh"
run_test "T033 Counter Proposal"      "$SCRIPT_DIR/test_us3_proposal_counter.sh"
run_test "T055 Lead Capture"          "$SCRIPT_DIR/test_us5_proposal_lead_capture.sh"
run_test "T056 List/Filters/Metrics"  "$SCRIPT_DIR/test_us6_proposal_list_filters_metrics.sh"
run_test "T057 Attachments"           "$SCRIPT_DIR/test_us7_proposal_attachments.sh"
run_test "T058 Expiration"            "$SCRIPT_DIR/test_us8_proposal_expiration.sh"
run_test "T032b Concurrent Creation"  "$SCRIPT_DIR/test_us_proposal_concurrent_creation.sh"

# ── Summary ───────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}══════════════════ SUMMARY ══════════════════${NC}"
for r in "${RESULTS[@]}"; do echo -e "  $r"; done
echo ""
if [ "$FAIL_TOTAL" -eq 0 ]; then
  echo -e "${GREEN}${BOLD}ALL TESTS PASSED${NC} — $PASS_TOTAL assertions passed"
  exit 0
else
  echo -e "${RED}${BOLD}FAILURES DETECTED${NC} — $PASS_TOTAL passed, $FAIL_TOTAL failed"
  exit 1
fi
