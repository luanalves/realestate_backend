# Quickstart: Property Attachments Upload API

**Feature**: 017 — Property Attachments Upload API
**Module**: `quicksol_estate`
**Working directory**: `18.0/extra-addons/quicksol_estate/`

---

## Prerequisites

### 1. Verify `libmagic1` is in the Dockerfile

Open `18.0/Dockerfile` and confirm these lines exist (lines 21 and 25):

```dockerfile
RUN apt-get update && apt-get install -y \
    libmagic1 \
    ...
    python3-magic \
    ...
```

These are already confirmed present. No action required.

### 2. Obtain an auth token

Use the OAuth2 endpoint to get a `Bearer` token and a `session_id` cookie:

```bash
# Login and capture token + session cookie
RESPONSE=$(curl -s -c /tmp/cookies.txt -X POST http://localhost:8069/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"login": "owner@realestate.test", "password": "admin"}')

TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "TOKEN=$TOKEN"
```

Or use `integration_tests/test_us1_s1_owner_login.sh` as a reference.

---

## Running Unit Tests (no Odoo container required)

Unit tests load the controller module in isolation using `unittest.mock`. They run locally without Docker:

```bash
cd 18.0/extra-addons/quicksol_estate/tests/unit

# Run all attachment unit tests
python3 -m pytest test_property_attachments_unit.py -v

# Or with standard unittest
python3 -m unittest test_property_attachments_unit -v
```

Expected: **49 tests, all passing**.

> If `werkzeug` is not installed locally, install it:
> ```bash
> pip install werkzeug python-magic
> ```
> (On macOS, also: `brew install libmagic`)

---

## Running API Integration Tests (requires live container)

After implementing `tests/api/test_property_attachments_api.py` (gap-07):

```bash
cd /opt/homebrew/var/www/realestate/odoo-docker/18.0

# Start the Odoo stack
docker compose up -d

# Run attachment API tests
docker compose exec odoo python3 -m pytest \
  /opt/odoo/addons/quicksol_estate/tests/api/test_property_attachments_api.py -v
```

---

## Running E2E Bash Tests (requires live container)

After implementing `integration_tests/test_us17_*.sh` (gap-08):

```bash
cd /opt/homebrew/var/www/realestate/odoo-docker/integration_tests

# Full feature journey
bash test_us17_s1_upload_journey.sh
bash test_us17_s2_download_journey.sh
bash test_us17_s3_delete_rbac.sh
bash test_us17_s4_list_pagination.sh
bash test_us17_s5_multitenancy_isolation.sh
bash test_us17_s6_rbac_matrix.sh
```

---

## Configuring Size Limit for Tests

The file size limit is read from `ir.config_parameter` key `web.max_file_upload_size` (value in bytes).

### Option A: Odoo UI

1. Go to `Settings → Technical → Parameters → System Parameters`
2. Search for `web.max_file_upload_size`
3. Set value in bytes (e.g., `10485760` for 10 MB)

### Option B: Python (in setUp / tearDown of integration tests)

```python
# setUp: set limit to 10 MB for test
self.env['ir.config_parameter'].sudo().set_param('web.max_file_upload_size', '10485760')

# tearDown: restore default
self.env['ir.config_parameter'].sudo().set_param('web.max_file_upload_size', '134217728')
```

### Option C: psql (for E2E bash tests)

```bash
# Set limit to 10 MB
docker compose exec db psql -U odoo -d realestate -c \
  "INSERT INTO ir_config_parameter (key, value) VALUES ('web.max_file_upload_size', '10485760')
   ON CONFLICT (key) DO UPDATE SET value = '10485760';"

# Restore after test
docker compose exec db psql -U odoo -d realestate -c \
  "UPDATE ir_config_parameter SET value = '134217728' WHERE key = 'web.max_file_upload_size';"
```

---

## Manual API Testing (curl)

### Upload an image

```bash
PROPERTY_ID=1
BASE_URL=http://localhost:8069

curl -X POST "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments" \
  -H "Authorization: Bearer $TOKEN" \
  -b /tmp/cookies.txt \
  -F "file=@/path/to/image.jpg" \
  -F "attachment_type=image"
```

Expected response (201):
```json
{
  "status": "success",
  "data": {
    "id": 42,
    "name": "image.jpg",
    "mimetype": "image/jpeg",
    "size": 204800,
    "attachment_type": "image",
    "uploaded_at": "2026-05-08T14:30:00Z",
    "links": {
      "download": "/api/v1/properties/1/attachments/42/download",
      "self": "/api/v1/properties/1/attachments/42"
    }
  }
}
```

### List attachments

```bash
curl -X GET "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments?attachment_type=image&limit=10" \
  -H "Authorization: Bearer $TOKEN" \
  -b /tmp/cookies.txt
```

### Download an attachment

```bash
ATTACHMENT_ID=42

curl -X GET "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments/$ATTACHMENT_ID/download" \
  -H "Authorization: Bearer $TOKEN" \
  -b /tmp/cookies.txt \
  --output downloaded_file.jpg
```

Verify headers contain:
- `Content-Security-Policy: default-src 'none'`
- `X-Content-Type-Options: nosniff`
- `Content-Disposition: attachment; filename="image.jpg"`

### Delete an attachment

```bash
curl -X DELETE "$BASE_URL/api/v1/properties/$PROPERTY_ID/attachments/$ATTACHMENT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -b /tmp/cookies.txt \
  -w "%{http_code}"
```

Expected: `204` with empty body.

---

## Test Fixtures

Fixtures are located at `18.0/extra-addons/quicksol_estate/tests/fixtures/`.

| File | Size | Purpose |
|------|------|---------|
| `seed_image.jpg` | < 2 MB | Valid JPEG for upload tests |
| `seed_document.pdf` | < 2 MB | Valid PDF for upload tests |
| `seed_malicious.jpg` | small | PHP script with `.jpg` extension — must be rejected (415) |
| `seed_large.jpg` | > 10 MB | Oversized file — use with size limit set to 10 MB |

Verify fixtures exist before running tests:

```bash
ls -lh 18.0/extra-addons/quicksol_estate/tests/fixtures/
```

---

## Linting

```bash
cd /opt/homebrew/var/www/realestate/odoo-docker/18.0
bash lint.sh
```

The controller must pass `pylint ≥ 8.0`, `black`, and `isort` checks (ADR-022).
