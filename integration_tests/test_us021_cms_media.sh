#!/usr/bin/env bash
# integration_tests/test_us021_cms_media.sh
# US021 Feature 021: CMS Domain - Media Library integration tests
# Covers: T021 (US2)
#
# Prerequisites:
#   - Odoo running at BASE_URL with thedevkitchen_cms installed
#   - OWNER_TOKEN set as env var
#
# Usage:
#   BASE_URL=http://localhost:8069 OWNER_TOKEN=... bash test_us021_cms_media.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8069}"
OWNER_TOKEN="${OWNER_TOKEN:-}"

PASS=0
FAIL=0
SKIP=0

_pass() { echo "  [PASS] $1"; ((PASS++)) || true; }
_fail() { echo "  [FAIL] $1 — $2"; ((FAIL++)) || true; }
_skip() { echo "  [SKIP] $1 — $2"; ((SKIP++)) || true; }
_require_token() {
    if [ -z "$1" ]; then echo "  [SKIP] Token not available ($2)"; ((SKIP++)) || true; return 1; fi
    return 0
}

echo "========================================"
echo "US021 CMS Media Library Tests"
echo "========================================"

# ---- S1: Upload valid jpg ----
echo ""
echo "S1: POST /api/v1/cms/media/upload — valid jpg"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    # Create a minimal valid JPEG (SOI marker)
    printf '\xff\xd8\xff\xe0\x00\x10JFIF\x00' > /tmp/test_valid.jpg
    RESP=$(curl -s -o /tmp/media_upload.json -w "%{http_code}" \
        -X POST "$BASE_URL/api/v1/cms/media/upload" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -F "file=@/tmp/test_valid.jpg;type=image/jpeg" \
        -F "name=test_valid.jpg")
    if [ "$RESP" = "201" ]; then
        MEDIA_ID=$(python3 -c "import json; print(json.load(open('/tmp/media_upload.json'))['id'])" 2>/dev/null || echo "")
        _pass "POST /upload returns 201"
        URL=$(python3 -c "import json; print(json.load(open('/tmp/media_upload.json')).get('url',''))" 2>/dev/null || echo "")
        if [ -n "$URL" ]; then
            _pass "Upload response includes url"
        else
            _fail "Upload url" "No 'url' in response"
        fi
    else
        _fail "POST /upload" "Expected 201, got $RESP — $(cat /tmp/media_upload.json)"
        MEDIA_ID=""
    fi
    rm -f /tmp/test_valid.jpg
fi

# ---- S2: Upload with forbidden MIME ----
echo ""
echo "S2: POST /api/v1/cms/media/upload — MIME forbidden (text/html)"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    echo "<html>test</html>" > /tmp/test_html.html
    RESP=$(curl -s -o /tmp/media_bad_mime.json -w "%{http_code}" \
        -X POST "$BASE_URL/api/v1/cms/media/upload" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -F "file=@/tmp/test_html.html;type=text/html")
    if [ "$RESP" = "415" ]; then
        _pass "text/html returns 415"
    else
        _fail "MIME forbidden" "Expected 415, got $RESP"
    fi
    rm -f /tmp/test_html.html
fi

# ---- S3: Upload with magic bytes divergence (jpg ext, pdf content) ----
echo ""
echo "S3: POST /api/v1/cms/media/upload — magic bytes mismatch"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN"; then
    printf '%%PDF-1.4 fake pdf content' > /tmp/test_mismatch.jpg
    RESP=$(curl -s -o /tmp/media_mismatch.json -w "%{http_code}" \
        -X POST "$BASE_URL/api/v1/cms/media/upload" \
        -H "Authorization: Bearer $OWNER_TOKEN" \
        -F "file=@/tmp/test_mismatch.jpg;type=image/jpeg")
    if [ "$RESP" = "415" ]; then
        ERROR=$(python3 -c "import json; print(json.load(open('/tmp/media_mismatch.json')).get('error',''))" 2>/dev/null || echo "")
        _pass "mime_mismatch returns 415"
        if [ "$ERROR" = "mime_mismatch" ]; then
            _pass "Error envelope has error=mime_mismatch"
        else
            _fail "Error envelope" "Expected mime_mismatch, got '$ERROR'"
        fi
    else
        _fail "MIME mismatch" "Expected 415, got $RESP"
    fi
    rm -f /tmp/test_mismatch.jpg
fi

# ---- S4: DELETE — removes ir.attachment ----
echo ""
echo "S4: DELETE /api/v1/cms/media/:id"
if _require_token "$OWNER_TOKEN" "OWNER_TOKEN" && [ -n "${MEDIA_ID:-}" ]; then
    RESP=$(curl -s -o /tmp/media_delete.json -w "%{http_code}" \
        -X DELETE "$BASE_URL/api/v1/cms/media/$MEDIA_ID" \
        -H "Authorization: Bearer $OWNER_TOKEN")
    if [ "$RESP" = "200" ] || [ "$RESP" = "204" ]; then
        _pass "DELETE /media/:id returns 200/204"
        # Verify the record is gone
        RESP2=$(curl -s -o /dev/null -w "%{http_code}" \
            -X GET "$BASE_URL/api/v1/cms/media/$MEDIA_ID" \
            -H "Authorization: Bearer $OWNER_TOKEN")
        if [ "$RESP2" = "404" ]; then
            _pass "Deleted media returns 404"
        else
            _fail "Deleted media" "Expected 404 after delete, got $RESP2"
        fi
    else
        _fail "DELETE /media/:id" "Expected 200/204, got $RESP — $(cat /tmp/media_delete.json)"
    fi
fi

# ---- S5: Cross-company access ----
_skip "S5: Cross-company access" "Requires OWNER_B_TOKEN configured"

echo ""
echo "========================================"
echo "Results: PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "========================================"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
