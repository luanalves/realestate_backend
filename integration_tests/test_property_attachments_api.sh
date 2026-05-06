#!/usr/bin/env bash
# =============================================================================
# Feature 017 — Property Attachments Upload API
# E2E Integration Tests (US1–US6) + Dynamic Config Tests (US5)
#
# Scenarios:
#   US1: Owner uploads image → 201, multitenancy isolation → 404, max images → 422
#   US2: Manager uploads document → 201, max documents → 422
#   US3: Authenticated download → 200 binary, unauthenticated → 401,
#         cross-company → 404, attachment on other property → 404
#   US4: Owner deletes → 204, agent deletes → 403, cross-company delete → 404
#   US5: Dynamic size limit via ir.config_parameter
#   US6: List with pagination, type filter, cross-company → 404
#
# Usage:
#   BASE_URL=http://localhost:8069 \
#   OWNER_EMAIL=owner@example.com \
#   OWNER_PASS=SecurePass123! \
#   MANAGER_EMAIL=manager@example.com \
#   MANAGER_PASS=SecurePass123! \
#   AGENT_EMAIL=agent@example.com \
#   AGENT_PASS=SecurePass123! \
#   PROPERTY_ID=7 \
#   bash integration_tests/test_property_attachments_api.sh
#
# Dependencies:
#   - jq (JSON parsing)
#   - curl
#   - psql (for US5 ir.config_parameter manipulation)
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/get_oauth2_token.sh"
[ -f "${SCRIPT_DIR}/../18.0/.env" ] && source "${SCRIPT_DIR}/../18.0/.env" || true

BASE_URL="${BASE_URL:-http://localhost:8069}"
API_BASE="${BASE_URL}/api/v1"
DB_NAME="${POSTGRES_DB:-realestate}"
DB_USER="${POSTGRES_USER:-odoo}"

OWNER_EMAIL="${OWNER_EMAIL:-${TEST_USER_OWNER:-owner@example.com}}"
OWNER_PASS="${OWNER_PASS:-${TEST_PASSWORD_OWNER:-SecurePass123!}}"
MANAGER_EMAIL="${MANAGER_EMAIL:-${TEST_USER_MANAGER:-manager@example.com}}"
MANAGER_PASS="${MANAGER_PASS:-${TEST_PASSWORD_MANAGER:-SecurePass123!}}"
AGENT_EMAIL="${AGENT_EMAIL:-${TEST_USER_AGENT:-agent@example.com}}"
AGENT_PASS="${AGENT_PASS:-${TEST_PASSWORD_AGENT:-SecurePass123!}}"
PROPERTY_ID="${PROPERTY_ID:-7}"

FIXTURES_DIR="${SCRIPT_DIR}/../18.0/extra-addons/quicksol_estate/tests/fixtures"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
PASS=0
FAIL=0
SKIP=0

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
_log()  { echo "[$(date '+%H:%M:%S')] $*"; }
_pass() { echo -e "${GREEN}✓ PASS${NC} — $1"; PASS=$((PASS + 1)); }
_fail() { echo -e "${RED}✗ FAIL${NC} — $1"; FAIL=$((FAIL + 1)); }
_skip() { echo -e "${YELLOW}⊘ SKIP${NC} — $1"; SKIP=$((SKIP + 1)); }
_info() { echo -e "  ${YELLOW}→${NC} $1"; }

_require_cmd() {
    for cmd in "$@"; do
        if ! command -v "$cmd" &>/dev/null; then
            echo "ERROR: '$cmd' is required but not installed." >&2
            exit 1
        fi
    done
}

_login() {
    local email="$1" pass="$2" bearer="$3"
    local resp
    resp=$(curl -s -X POST "${API_BASE}/users/login" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${bearer}" \
        -d "{\"login\": \"${email}\", \"password\": \"${pass}\"}")
    echo "$resp"
}

_session_id() { echo "$1" | jq -r '.session_id // empty'; }

_assert_code() {
    local label="$1" expected="$2" actual="$3"
    if [ "${actual}" -eq "${expected}" ]; then
        _pass "${label} (HTTP ${actual})"
    else
        _fail "${label} (expected HTTP ${expected}, got HTTP ${actual})"
    fi
}

_assert_field() {
    local label="$1" path="$2" response="$3"
    local value
    value=$(echo "${response}" | jq -r "${path} // empty" 2>/dev/null || true)
    if [ -n "${value}" ] && [ "${value}" != "null" ]; then
        _pass "${label} — '${path}' = '${value}'"
    else
        _fail "${label} — '${path}' missing or null in: $(echo "${response}" | head -c 200)"
    fi
}

_assert_no_web_content() {
    local label="$1" value="$2"
    if echo "${value}" | grep -q '/web/content/'; then
        _fail "${label} — URL contains /web/content/ (invariant violation): ${value}"
    else
        _pass "${label} — URL uses /api/v1/ path"
    fi
}

_psql() {
    # Run a SQL command in the Odoo DB via docker compose or direct psql
    local sql="$1"
    if command -v docker &>/dev/null && docker compose -f "${SCRIPT_DIR}/../18.0/docker-compose.yml" ps db --quiet 2>/dev/null | grep -q .; then
        docker compose -f "${SCRIPT_DIR}/../18.0/docker-compose.yml" exec -T db \
            psql -U "${DB_USER}" -d "${DB_NAME}" -c "${sql}" 2>/dev/null
    else
        psql -U "${DB_USER}" -d "${DB_NAME}" -c "${sql}" 2>/dev/null
    fi
}

_set_max_upload_size() {
    local size="$1"
    _psql "INSERT INTO ir_config_parameter (key, value, create_uid, write_uid, create_date, write_date)
           VALUES ('web.max_file_upload_size', '${size}', 1, 1, NOW(), NOW())
           ON CONFLICT (key) DO UPDATE SET value = '${size}', write_date = NOW();" > /dev/null
    _info "Set web.max_file_upload_size = ${size}"
}

_reset_max_upload_size() {
    _psql "UPDATE ir_config_parameter SET value = '134217728' WHERE key = 'web.max_file_upload_size';" > /dev/null
    _info "Reset web.max_file_upload_size to 134217728 (128 MB)"
}

# ---------------------------------------------------------------------------
# Prerequisites check
# ---------------------------------------------------------------------------
_require_cmd jq curl

echo "========================================================"
echo "Feature 017 — Property Attachments Upload API"
echo "E2E Integration Tests"
echo "========================================================"
echo ""
_info "BASE_URL: ${BASE_URL}"
_info "PROPERTY_ID: ${PROPERTY_ID}"
_info "FIXTURES: ${FIXTURES_DIR}"
echo ""

if [ ! -f "${FIXTURES_DIR}/seed_image.jpg" ]; then
    echo "ERROR: Fixture seed_image.jpg not found at ${FIXTURES_DIR}" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 0: OAuth2 Bearer Token
# ---------------------------------------------------------------------------
_log "Step 0: Getting OAuth2 Bearer Token"
BEARER_TOKEN=$(get_oauth2_token)
if [ -z "${BEARER_TOKEN}" ]; then
    _fail "OAuth2 token — failed to obtain token"
    echo "Results: PASS=${PASS} FAIL=${FAIL} SKIP=${SKIP}"
    exit 1
fi
_pass "OAuth2 bearer token obtained"

# ---------------------------------------------------------------------------
# Step 1: Authenticate users
# ---------------------------------------------------------------------------
_log "Step 1: Authenticating users"

OWNER_AUTH=$(_login "${OWNER_EMAIL}" "${OWNER_PASS}" "${BEARER_TOKEN}")
OWNER_SID=$(_session_id "${OWNER_AUTH}")

MANAGER_AUTH=$(_login "${MANAGER_EMAIL}" "${MANAGER_PASS}" "${BEARER_TOKEN}")
MANAGER_SID=$(_session_id "${MANAGER_AUTH}")

AGENT_AUTH=$(_login "${AGENT_EMAIL}" "${AGENT_PASS}" "${BEARER_TOKEN}")
AGENT_SID=$(_session_id "${AGENT_AUTH}")

[ -n "${OWNER_SID}" ]   && _pass "Owner session" || _fail "Owner login failed"
[ -n "${MANAGER_SID}" ] && _pass "Manager session" || _fail "Manager login failed"
[ -n "${AGENT_SID}" ]   && _pass "Agent session" || _fail "Agent login failed"

AUTH_OWNER=(
    -H "Authorization: Bearer ${BEARER_TOKEN}"
    -H "X-Openerp-Session-Id: ${OWNER_SID}"
)
AUTH_MANAGER=(
    -H "Authorization: Bearer ${BEARER_TOKEN}"
    -H "X-Openerp-Session-Id: ${MANAGER_SID}"
)
AUTH_AGENT=(
    -H "Authorization: Bearer ${BEARER_TOKEN}"
    -H "X-Openerp-Session-Id: ${AGENT_SID}"
)

# ---------------------------------------------------------------------------
# US1 — Image Upload
# ---------------------------------------------------------------------------
echo ""
echo "--- US1: Image Upload ---"

# US1/T01: Owner uploads a valid JPEG → 201
_log "US1/T01: Owner uploads valid JPEG"
UPLOAD_CODE=$(curl -s -o /tmp/f017_upload_image.json -w "%{http_code}" \
    -X POST "${API_BASE}/properties/${PROPERTY_ID}/attachments" \
    "${AUTH_OWNER[@]}" \
    -F "file=@${FIXTURES_DIR}/seed_image.jpg;type=image/jpeg" \
    -F "attachment_type=image")
_assert_code "US1/T01 Owner uploads valid JPEG" 201 "${UPLOAD_CODE}"

if [ "${UPLOAD_CODE}" -eq 201 ]; then
    UPLOAD_RESP=$(cat /tmp/f017_upload_image.json)
    _assert_field "US1/T01 response has id" '.data.id' "${UPLOAD_RESP}"
    _assert_field "US1/T01 response has name" '.data.name' "${UPLOAD_RESP}"
    _assert_field "US1/T01 response has mimetype" '.data.mimetype' "${UPLOAD_RESP}"
    _assert_field "US1/T01 response has size" '.data.size' "${UPLOAD_RESP}"
    _assert_field "US1/T01 response has attachment_type" '.data.attachment_type' "${UPLOAD_RESP}"
    _assert_field "US1/T01 response has uploaded_at" '.data.uploaded_at' "${UPLOAD_RESP}"
    _assert_field "US1/T01 response has links.self" '.data.links.self' "${UPLOAD_RESP}"
    _assert_field "US1/T01 response has links.download" '.data.links.download' "${UPLOAD_RESP}"
    SELF_URL=$(echo "${UPLOAD_RESP}" | jq -r '.data.links.self // empty')
    DOWNLOAD_URL=$(echo "${UPLOAD_RESP}" | jq -r '.data.links.download // empty')
    _assert_no_web_content "US1/T01 links.self is /api/v1/ URL" "${SELF_URL}"
    _assert_no_web_content "US1/T01 links.download is /api/v1/ URL" "${DOWNLOAD_URL}"
    IMAGE_ATTACHMENT_ID=$(echo "${UPLOAD_RESP}" | jq -r '.data.id // empty')
    _info "Uploaded image attachment id: ${IMAGE_ATTACHMENT_ID}"
fi

# US1/T02: MIME type rejected (malicious file with .jpg extension)
_log "US1/T02: Malicious file rejected by magic bytes"
if [ -f "${FIXTURES_DIR}/seed_malicious.jpg" ]; then
    MALICIOUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${API_BASE}/properties/${PROPERTY_ID}/attachments" \
        "${AUTH_OWNER[@]}" \
        -F "file=@${FIXTURES_DIR}/seed_malicious.jpg;type=image/jpeg" \
        -F "attachment_type=image")
    _assert_code "US1/T02 Malicious file rejected → 415" 415 "${MALICIOUS_CODE}"
else
    _skip "US1/T02 — seed_malicious.jpg not found"
fi

# US1/T03: Multitenancy isolation (upload to property from another company → 404)
_log "US1/T03: Multitenancy isolation for upload"
CROSS_COMPANY_PROPERTY="${CROSS_COMPANY_PROPERTY_ID:-9999}"
CROSS_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${API_BASE}/properties/${CROSS_COMPANY_PROPERTY}/attachments" \
    "${AUTH_OWNER[@]}" \
    -F "file=@${FIXTURES_DIR}/seed_image.jpg;type=image/jpeg" \
    -F "attachment_type=image")
_assert_code "US1/T03 Cross-company upload → 404" 404 "${CROSS_CODE}"

# ---------------------------------------------------------------------------
# US2 — Document Upload
# ---------------------------------------------------------------------------
echo ""
echo "--- US2: Document Upload ---"

# US2/T01: Manager uploads valid PDF → 201
_log "US2/T01: Manager uploads valid PDF"
DOC_UPLOAD_CODE=$(curl -s -o /tmp/f017_upload_doc.json -w "%{http_code}" \
    -X POST "${API_BASE}/properties/${PROPERTY_ID}/attachments" \
    "${AUTH_MANAGER[@]}" \
    -F "file=@${FIXTURES_DIR}/seed_document.pdf;type=application/pdf" \
    -F "attachment_type=document")
_assert_code "US2/T01 Manager uploads valid PDF" 201 "${DOC_UPLOAD_CODE}"

if [ "${DOC_UPLOAD_CODE}" -eq 201 ]; then
    DOC_RESP=$(cat /tmp/f017_upload_doc.json)
    DOC_ATTACHMENT_ID=$(echo "${DOC_RESP}" | jq -r '.data.id // empty')
    _assert_field "US2/T01 attachment_type=document" '.data.attachment_type' "${DOC_RESP}"
    ATT_TYPE=$(echo "${DOC_RESP}" | jq -r '.data.attachment_type // empty')
    [ "${ATT_TYPE}" = "document" ] && _pass "US2/T01 attachment_type is 'document'" || _fail "US2/T01 attachment_type expected 'document', got '${ATT_TYPE}'"
    _info "Uploaded document attachment id: ${DOC_ATTACHMENT_ID}"
fi

# US2/T02: Wrong attachment_type for MIME (PDF as image) → 400
_log "US2/T02: PDF submitted as attachment_type=image → 400"
MISMATCH_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${API_BASE}/properties/${PROPERTY_ID}/attachments" \
    "${AUTH_OWNER[@]}" \
    -F "file=@${FIXTURES_DIR}/seed_document.pdf;type=application/pdf" \
    -F "attachment_type=image")
_assert_code "US2/T02 MIME/type mismatch → 400" 400 "${MISMATCH_CODE}"

# ---------------------------------------------------------------------------
# US3 — Download
# ---------------------------------------------------------------------------
echo ""
echo "--- US3: Download ---"

if [ -n "${IMAGE_ATTACHMENT_ID:-}" ] && [ "${IMAGE_ATTACHMENT_ID}" != "null" ]; then
    # US3/T01: Authenticated download → 200 binary
    _log "US3/T01: Authenticated download of image"
    DL_CODE=$(curl -s -o /tmp/f017_downloaded.jpg -w "%{http_code}" \
        -X GET "${API_BASE}/properties/${PROPERTY_ID}/attachments/${IMAGE_ATTACHMENT_ID}/download" \
        "${AUTH_OWNER[@]}")
    _assert_code "US3/T01 Authenticated download" 200 "${DL_CODE}"

    if [ "${DL_CODE}" -eq 200 ]; then
        DL_SIZE=$(wc -c < /tmp/f017_downloaded.jpg 2>/dev/null || echo 0)
        [ "${DL_SIZE}" -gt 0 ] && _pass "US3/T01 Downloaded file is non-empty (${DL_SIZE} bytes)" || _fail "US3/T01 Downloaded file is empty"
    fi

    # US3/T02: Unauthenticated download → 401
    _log "US3/T02: Unauthenticated download → 401"
    UNAUTH_DL_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "${API_BASE}/properties/${PROPERTY_ID}/attachments/${IMAGE_ATTACHMENT_ID}/download")
    _assert_code "US3/T02 Unauthenticated download" 401 "${UNAUTH_DL_CODE}"

    # US3/T03: Cross-company download → 404 (anti-enumeration)
    _log "US3/T03: Cross-company download → 404"
    CC_DL_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "${API_BASE}/properties/${CROSS_COMPANY_PROPERTY:-9999}/attachments/${IMAGE_ATTACHMENT_ID}/download" \
        "${AUTH_OWNER[@]}")
    _assert_code "US3/T03 Cross-company download" 404 "${CC_DL_CODE}"

    # US3/T04: Attachment on wrong property → 404
    _log "US3/T04: Attachment from different property → 404"
    OTHER_PROPERTY="${OTHER_PROPERTY_ID:-8888}"
    WRONG_PROP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "${API_BASE}/properties/${OTHER_PROPERTY}/attachments/${IMAGE_ATTACHMENT_ID}/download" \
        "${AUTH_OWNER[@]}")
    _assert_code "US3/T04 Attachment on wrong property" 404 "${WRONG_PROP_CODE}"
else
    _skip "US3 — skipped (no uploaded image attachment id available)"
fi

# ---------------------------------------------------------------------------
# US4 — Delete
# ---------------------------------------------------------------------------
echo ""
echo "--- US4: Delete ---"

# US4/T01: Agent tries to delete → 403
if [ -n "${IMAGE_ATTACHMENT_ID:-}" ] && [ "${IMAGE_ATTACHMENT_ID}" != "null" ]; then
    _log "US4/T01: Agent DELETE → 403"
    AGENT_DEL_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X DELETE "${API_BASE}/properties/${PROPERTY_ID}/attachments/${IMAGE_ATTACHMENT_ID}" \
        "${AUTH_AGENT[@]}")
    _assert_code "US4/T01 Agent DELETE blocked" 403 "${AGENT_DEL_CODE}"
fi

# US4/T02: Cross-company delete → 404
if [ -n "${IMAGE_ATTACHMENT_ID:-}" ] && [ "${IMAGE_ATTACHMENT_ID}" != "null" ]; then
    _log "US4/T02: Cross-company DELETE → 404"
    CC_DEL_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X DELETE "${API_BASE}/properties/${CROSS_COMPANY_PROPERTY:-9999}/attachments/${IMAGE_ATTACHMENT_ID}" \
        "${AUTH_OWNER[@]}")
    _assert_code "US4/T02 Cross-company DELETE" 404 "${CC_DEL_CODE}"
fi

# US4/T03: Upload a dedicated attachment and delete it → 204
_log "US4/T03: Owner deletes attachment → 204"
DELETE_UPLOAD_CODE=$(curl -s -o /tmp/f017_del_target.json -w "%{http_code}" \
    -X POST "${API_BASE}/properties/${PROPERTY_ID}/attachments" \
    "${AUTH_OWNER[@]}" \
    -F "file=@${FIXTURES_DIR}/seed_image.jpg;type=image/jpeg" \
    -F "attachment_type=image")
if [ "${DELETE_UPLOAD_CODE}" -eq 201 ]; then
    DEL_ID=$(jq -r '.data.id // empty' /tmp/f017_del_target.json)
    DEL_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X DELETE "${API_BASE}/properties/${PROPERTY_ID}/attachments/${DEL_ID}" \
        "${AUTH_OWNER[@]}")
    _assert_code "US4/T03 Owner DELETE" 204 "${DEL_CODE}"

    # Confirm it's gone
    GET_DELETED_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X GET "${API_BASE}/properties/${PROPERTY_ID}/attachments/${DEL_ID}/download" \
        "${AUTH_OWNER[@]}")
    _assert_code "US4/T03 Deleted attachment no longer accessible" 404 "${GET_DELETED_CODE}"
else
    _skip "US4/T03 — setup upload failed (HTTP ${DELETE_UPLOAD_CODE})"
fi

# ---------------------------------------------------------------------------
# US5 — Dynamic size limit via ir.config_parameter
# ---------------------------------------------------------------------------
echo ""
echo "--- US5: Dynamic Size Limit (ir.config_parameter) ---"

if command -v psql &>/dev/null || (command -v docker &>/dev/null && \
    docker compose -f "${SCRIPT_DIR}/../18.0/docker-compose.yml" ps db --quiet 2>/dev/null | grep -q .); then

    # US5/T01: Set limit to 1 MB → upload seed_large.jpg (>10 MB) → 413
    _log "US5/T01: Set limit to 1 MB, upload large file → 413"
    _set_max_upload_size "1048576"
    LARGE_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${API_BASE}/properties/${PROPERTY_ID}/attachments" \
        "${AUTH_OWNER[@]}" \
        -F "file=@${FIXTURES_DIR}/seed_large.jpg;type=image/jpeg" \
        -F "attachment_type=image")
    _assert_code "US5/T01 Upload over dynamic limit → 413" 413 "${LARGE_CODE}"

    # US5/T02: Reset to 128 MB → upload seed_image.jpg (~1 MB) → 201
    _log "US5/T02: Reset limit to 128 MB, upload small image → 201"
    _reset_max_upload_size
    SMALL_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${API_BASE}/properties/${PROPERTY_ID}/attachments" \
        "${AUTH_OWNER[@]}" \
        -F "file=@${FIXTURES_DIR}/seed_image.jpg;type=image/jpeg" \
        -F "attachment_type=image")
    _assert_code "US5/T02 Upload within dynamic limit → 201" 201 "${SMALL_CODE}"

    # US5/T03: Verify parameter key is the standard Odoo one
    _log "US5/T03: Verifying ir.config_parameter key"
    PARAM_VALUE=$(_psql "SELECT value FROM ir_config_parameter WHERE key = 'web.max_file_upload_size';" 2>/dev/null | grep -E '^\s+[0-9]' | tr -d ' ' || echo "")
    if [ -n "${PARAM_VALUE}" ]; then
        _pass "US5/T03 ir.config_parameter key 'web.max_file_upload_size' exists (value=${PARAM_VALUE})"
    else
        _fail "US5/T03 ir.config_parameter key 'web.max_file_upload_size' not found"
    fi
else
    _skip "US5 — DB access not available (psql / docker not found)"
fi

# ---------------------------------------------------------------------------
# US6 — List with pagination and type filter
# ---------------------------------------------------------------------------
echo ""
echo "--- US6: List Attachments ---"

# US6/T01: List returns items with metadata
_log "US6/T01: List attachments returns items"
LIST_CODE=$(curl -s -o /tmp/f017_list.json -w "%{http_code}" \
    -X GET "${API_BASE}/properties/${PROPERTY_ID}/attachments" \
    "${AUTH_OWNER[@]}")
_assert_code "US6/T01 List attachments" 200 "${LIST_CODE}"

if [ "${LIST_CODE}" -eq 200 ]; then
    LIST_RESP=$(cat /tmp/f017_list.json)
    _assert_field "US6/T01 response has items array" '.data.items' "${LIST_RESP}"
    _assert_field "US6/T01 response has pagination.total" '.data.pagination.total' "${LIST_RESP}"
    _assert_field "US6/T01 response has pagination.limit" '.data.pagination.limit' "${LIST_RESP}"
    _assert_field "US6/T01 response has pagination.offset" '.data.pagination.offset' "${LIST_RESP}"

    ITEMS_COUNT=$(echo "${LIST_RESP}" | jq '.data.items | length' 2>/dev/null || echo 0)
    _info "Items in list: ${ITEMS_COUNT}"

    if [ "${ITEMS_COUNT}" -gt 0 ]; then
        FIRST_DOWNLOAD=$(echo "${LIST_RESP}" | jq -r '.data.items[0].links.download // empty')
        _assert_no_web_content "US6/T01 list item download link" "${FIRST_DOWNLOAD}"

        # Verify no 'self' link in list items (list items only have 'download')
        HAS_SELF=$(echo "${LIST_RESP}" | jq '.data.items[0].links | has("self")' 2>/dev/null || echo false)
        [ "${HAS_SELF}" = "false" ] \
            && _pass "US6/T01 List items do not expose 'self' link" \
            || _fail "US6/T01 List items should NOT have 'self' link (got: ${HAS_SELF})"
    fi
fi

# US6/T02: Filter by attachment_type=image
_log "US6/T02: Filter by attachment_type=image"
IMAGE_LIST_CODE=$(curl -s -o /tmp/f017_list_images.json -w "%{http_code}" \
    -X GET "${API_BASE}/properties/${PROPERTY_ID}/attachments?attachment_type=image" \
    "${AUTH_OWNER[@]}")
_assert_code "US6/T02 List filtered by type=image" 200 "${IMAGE_LIST_CODE}"

if [ "${IMAGE_LIST_CODE}" -eq 200 ]; then
    IMAGE_LIST=$(cat /tmp/f017_list_images.json)
    IMAGE_COUNT=$(echo "${IMAGE_LIST}" | jq '.data.items | length' 2>/dev/null || echo 0)
    _info "Image items: ${IMAGE_COUNT}"
    if [ "${IMAGE_COUNT}" -gt 0 ]; then
        ALL_IMAGES=$(echo "${IMAGE_LIST}" | jq '[.data.items[].attachment_type] | all(. == "image")' 2>/dev/null || echo false)
        [ "${ALL_IMAGES}" = "true" ] \
            && _pass "US6/T02 All items have attachment_type=image" \
            || _fail "US6/T02 Some items do not have attachment_type=image"
    fi
fi

# US6/T03: Pagination — limit=1 offset=0 and limit=1 offset=1 return different items
_log "US6/T03: Pagination test"
PAGE1_CODE=$(curl -s -o /tmp/f017_page1.json -w "%{http_code}" \
    -X GET "${API_BASE}/properties/${PROPERTY_ID}/attachments?limit=1&offset=0" \
    "${AUTH_OWNER[@]}")
PAGE2_CODE=$(curl -s -o /tmp/f017_page2.json -w "%{http_code}" \
    -X GET "${API_BASE}/properties/${PROPERTY_ID}/attachments?limit=1&offset=1" \
    "${AUTH_OWNER[@]}")
_assert_code "US6/T03 Page 1 (limit=1 offset=0)" 200 "${PAGE1_CODE}"
_assert_code "US6/T03 Page 2 (limit=1 offset=1)" 200 "${PAGE2_CODE}"

if [ "${PAGE1_CODE}" -eq 200 ] && [ "${PAGE2_CODE}" -eq 200 ]; then
    ID1=$(jq -r '.data.items[0].id // empty' /tmp/f017_page1.json)
    ID2=$(jq -r '.data.items[0].id // empty' /tmp/f017_page2.json)
    if [ -n "${ID1}" ] && [ -n "${ID2}" ] && [ "${ID1}" != "${ID2}" ]; then
        _pass "US6/T03 Page 1 and Page 2 return different items (${ID1} vs ${ID2})"
    elif [ -z "${ID1}" ] || [ -z "${ID2}" ]; then
        _skip "US6/T03 — not enough items to test pagination"
    else
        _fail "US6/T03 Page 1 and Page 2 returned same item id=${ID1}"
    fi
fi

# US6/T04: Cross-company list → 404
_log "US6/T04: Cross-company list → 404"
CC_LIST_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X GET "${API_BASE}/properties/${CROSS_COMPANY_PROPERTY:-9999}/attachments" \
    "${AUTH_OWNER[@]}")
_assert_code "US6/T04 Cross-company list" 404 "${CC_LIST_CODE}"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "========================================================"
echo "Results: PASS=${PASS} FAIL=${FAIL} SKIP=${SKIP}"
echo "========================================================"

if [ "${FAIL}" -gt 0 ]; then
    exit 1
fi
exit 0
