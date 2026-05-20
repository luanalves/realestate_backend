#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -f "${REPO_ROOT}/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.env"
    set +a
fi

OWNER_EMAIL="${OWNER_EMAIL:-${SEED_OWNER_EMAIL:-}}"
OWNER_PASS="${OWNER_PASS:-${SEED_OWNER_PASSWORD:-}}"
BASE_URL="${BASE_URL:-http://localhost:8069}"
OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID:-test-client-id}"
OAUTH_CLIENT_SECRET="${OAUTH_CLIENT_SECRET:-test-client-secret-12345}"

if [ -z "${BASE_URL:-}" ] || [ -z "${OAUTH_CLIENT_ID:-}" ] || [ -z "${OAUTH_CLIENT_SECRET:-}" ] || [ -z "${OWNER_EMAIL:-}" ] || [ -z "${OWNER_PASS:-}" ]; then
    echo "Missing BASE_URL, OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OWNER_EMAIL or OWNER_PASS in 18.0/.env" >&2
    exit 1
fi

TOKEN_RESPONSE=$(curl -sS --fail -X POST "${BASE_URL}/api/v1/auth/token" \
    -H "Content-Type: application/json" \
    -d "{\"grant_type\":\"client_credentials\",\"client_id\":\"${OAUTH_CLIENT_ID}\",\"client_secret\":\"${OAUTH_CLIENT_SECRET}\"}") || \
TOKEN_RESPONSE=$(curl -sS --fail -X POST "${BASE_URL}/api/v1/auth/token" \
    -H "Content-Type: application/json" \
    -d "{\"grant_type\":\"client_credentials\",\"client_id\":\"test-client-id\",\"client_secret\":\"test-client-secret-12345\"}")
ACCESS_TOKEN=$(printf '%s' "${TOKEN_RESPONSE}" | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

LOGIN_RESPONSE=$(curl -sS --fail -X POST "${BASE_URL}/api/v1/users/login" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "User-Agent: PerformanceTest/1.0" \
    -H "Accept-Language: en-US" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${OWNER_EMAIL}\",\"password\":\"${OWNER_PASS}\"}")
SESSION_ID=$(printf '%s' "${LOGIN_RESPONSE}" | python3 -c "import json,sys; print(json.load(sys.stdin)['session_id'])")

ME_RESPONSE=$(curl -sS --fail -X GET "${BASE_URL}/api/v1/me" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "X-Openerp-Session-Id: ${SESSION_ID}" \
    -H "User-Agent: PerformanceTest/1.0" \
    -H "Accept-Language: en-US")
COMPANY_ID=$(printf '%s' "${ME_RESPONSE}" | python3 -c "import json,sys; body=json.load(sys.stdin); print(body['user']['default_company_id'])")

if [ -z "${COMPANY_ID}" ] || [ "${COMPANY_ID}" = "None" ]; then
    echo "Unable to determine company_id from /api/v1/me response" >&2
    exit 1
fi

echo "Running 100 sequential GET /api/v1/me/capabilities requests..."

TIMINGS=()
for INDEX in $(seq 1 100); do
    RESULT=$(curl -sS -o /dev/null -w "%{http_code} %{time_total}" -X GET "${BASE_URL}/api/v1/me/capabilities" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "X-Openerp-Session-Id: ${SESSION_ID}" \
        -H "X-Company-ID: ${COMPANY_ID}" \
        -H "User-Agent: PerformanceTest/1.0" \
        -H "Accept-Language: en-US")
    STATUS=$(printf '%s' "${RESULT}" | awk '{print $1}')
    DURATION=$(printf '%s' "${RESULT}" | awk '{print $2}')
    if [ "${STATUS}" != "200" ]; then
        echo "Request ${INDEX} failed with HTTP ${STATUS}" >&2
        exit 1
    fi
    TIMINGS+=("${DURATION}")
done

P95=$(printf '%s\n' "${TIMINGS[@]}" | python3 -c "import math,sys; values=sorted(float(line.strip()) for line in sys.stdin if line.strip()); idx=max(0, math.ceil(len(values)*0.95)-1); print(f'{values[idx]:.6f}')")

echo "p95=${P95}s"

python3 -c "import sys; p95=float(sys.argv[1]); sys.exit(0 if p95 < 1.0 else 1)" "${P95}" || {
    echo "Performance gate failed: p95 must be < 1.0s" >&2
    exit 1
}

echo "Performance gate passed."
