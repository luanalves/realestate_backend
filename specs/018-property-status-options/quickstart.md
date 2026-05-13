# Quickstart: Property Status and Situation Options

## Prerequisites

- Odoo stack running from `18.0/docker-compose.yml`.
- Module `quicksol_estate` installed.
- Valid OAuth client credentials and API user credentials in `18.0/.env`.

## 1. Run Unit Tests

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/codex-pycache \
  python3 18.0/extra-addons/quicksol_estate/tests/unit/test_property_mapping_fields_unit.py
```

Expected:

```text
Ran 10 tests
OK
```

## 2. Compile Changed Python Files

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/codex-pycache \
  python3 -m py_compile \
  18.0/extra-addons/quicksol_estate/models/property.py \
  18.0/extra-addons/quicksol_estate/controllers/utils/property_options.py \
  18.0/extra-addons/quicksol_estate/controllers/utils/serializers.py \
  18.0/extra-addons/quicksol_estate/tests/unit/test_property_mapping_fields_unit.py
```

Expected: no output and exit code `0`.

## 3. Upgrade Module for Swagger Sync

From `18.0/`:

```bash
docker compose exec -T odoo odoo -d realestate -u quicksol_estate --stop-after-init
```

Expected:

- Exit code `0`.
- Logs show `loading quicksol_estate/data/api_endpoints.xml`.
- Logs show `Module quicksol_estate loaded`.

Warnings about OpenTelemetry export to `tempo:4317` do not block this spec.

## 4. Validate Options API

Use a valid JWT and session, then call:

```bash
curl -s http://localhost:8069/api/v1/properties/options \
  -H "Authorization: Bearer $JWT" \
  -H "X-Openerp-Session-Id: $SID" \
  -H "Content-Type: application/json"
```

Expected fields:

- `property_status`
- `property_situation`

Expected `property_situation` options:

```json
[
  {"value": "Não Informado", "label": "Não Informado"},
  {"value": "Desocupado", "label": "Desocupado"},
  {"value": "Ocupado", "label": "Ocupado"},
  {"value": "Reservado", "label": "Reservado"},
  {"value": "Em construção", "label": "Em construção"},
  {"value": "Lançamento", "label": "Lançamento"},
  {"value": "Novo", "label": "Novo"}
]
```

## 5. Validate Property Detail

```bash
curl -s http://localhost:8069/api/v1/properties/4 \
  -H "Authorization: Bearer $JWT" \
  -H "X-Openerp-Session-Id: $SID" \
  -H "Content-Type: application/json"
```

Expected relevant fields:

```json
{
  "id": 4,
  "status": "available",
  "property_status": "available",
  "property_situation": "Desocupado",
  "for_sale": true,
  "for_rent": false
}
```

## 6. Validate Generated OpenAPI

```bash
curl -s http://localhost:8069/api/v1/openapi.json > /tmp/openapi.json

python3 - <<'PY'
import json
spec = json.load(open('/tmp/openapi.json'))
opts = spec['paths']['/api/v1/properties/options']['get']['responses']['200']['content']['application/json']['schema']['properties']
detail = spec['paths']['/api/v1/properties/{id}']['get']['responses']['200']['content']['application/json']['schema']['properties']
assert 'property_situation' in opts
assert 'property_status' in detail
assert detail['property_situation']['enum'] == [
    'Não Informado',
    'Desocupado',
    'Ocupado',
    'Reservado',
    'Em construção',
    'Lançamento',
    'Novo',
]
print('openapi ok')
PY
```

## 7. Validate Postman Collection JSON

```bash
python3 -m json.tool docs/postman/quicksol_api_v1.30_postman_collection.json >/tmp/postman_v130.json
```

Expected: exit code `0`.

## 8. Whitespace Check

```bash
git diff --check
```

Expected: no output and exit code `0`.

