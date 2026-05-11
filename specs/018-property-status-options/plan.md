# Implementation Plan: Property Status and Situation Options

**Branch**: `018-property-status-options`
**Date**: 2026-05-11
**Spec**: [spec.md](./spec.md)
**Flowcharts**: [flowcharts.md](./flowcharts.md)
**Status**: Implemented

## Goal

Expose property availability and status fields consistently across API responses, selectable options, Swagger/OpenAPI, and Postman.

## Technical Context

- Odoo module: `quicksol_estate`
- Model: `real.estate.property`
- API controllers:
  - `property_api.py`
  - `master_data_api.py`
- Shared helpers:
  - `controllers/utils/serializers.py`
  - `controllers/utils/property_options.py`
- Swagger source: `quicksol_estate/data/api_endpoints.xml`
- Generated Swagger endpoint: `GET /api/v1/openapi.json`
- Postman collection: `docs/postman/quicksol_api_v1.30_postman_collection.json`

## Implementation Steps

### Phase 1 - Serializer Contract

- Add `for_sale` and `for_rent` to `serialize_property()`.
- Add canonical `property_status` to `serialize_property()`.
- Keep `status` as a legacy alias.
- Add fallback mapping from `property_status` to `property_situation` when stored value is empty.

### Phase 2 - Model Options

- Convert `property_situation` from `fields.Char` to `fields.Selection`.
- Use the exact accepted values:
  - `Não Informado`
  - `Desocupado`
  - `Ocupado`
  - `Reservado`
  - `Em construção`
  - `Lançamento`
  - `Novo`

### Phase 3 - Options API

- Add `property_situation` to `PROPERTY_SELECTION_FIELDS`.
- Ensure `GET /api/v1/properties/options` returns both `property_status` and `property_situation`.

### Phase 4 - Swagger/OpenAPI

- Update `quicksol_estate/data/api_endpoints.xml`.
- Document `property_status`.
- Document `property_situation` enum.
- Run module upgrade:

```bash
docker compose exec -T odoo odoo -d realestate -u quicksol_estate --stop-after-init
```

- Validate generated OpenAPI:

```bash
curl -s http://localhost:8069/api/v1/openapi.json
```

### Phase 5 - Postman

- Create `docs/postman/quicksol_api_v1.30_postman_collection.json` from v1.29.
- Update collection metadata to version `1.30`.
- Update examples so `property_situation` uses valid values.
- Update `docs/postman/README.md` to mark v1.30 as recommended.

### Phase 6 - Tests

- Extend `test_property_mapping_fields_unit.py`.
- Cover:
  - `property_status` in serializer response.
  - `property_situation` options returned by property options helper.
  - fallback from `property_status=available` to `property_situation=Desocupado`.
  - explicit `property_situation` is preserved.

### Phase 7 - Flow Documentation

- Add `flowcharts.md` with endpoint journeys for:
  - loading selectable options;
  - creating properties for sale or rent;
  - updating `property_status` and `property_situation`;
  - interpreting `property_situation` fallback;
  - listing/filtering properties by availability and status;
  - validating Swagger/OpenAPI after module upgrade.

## Verification Plan

Run:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/codex-pycache \
  python3 18.0/extra-addons/quicksol_estate/tests/unit/test_property_mapping_fields_unit.py

env PYTHONPYCACHEPREFIX=/private/tmp/codex-pycache \
  python3 -m py_compile \
  18.0/extra-addons/quicksol_estate/models/property.py \
  18.0/extra-addons/quicksol_estate/controllers/utils/property_options.py \
  18.0/extra-addons/quicksol_estate/controllers/utils/serializers.py \
  18.0/extra-addons/quicksol_estate/tests/unit/test_property_mapping_fields_unit.py

python3 -m json.tool docs/postman/quicksol_api_v1.30_postman_collection.json >/tmp/postman_v130.json

python3 -c "import json,xml.etree.ElementTree as ET; fields=[f for f in ET.parse('18.0/extra-addons/quicksol_estate/data/api_endpoints.xml').getroot().iter('field') if f.attrib.get('name') in ('request_schema','response_schema') and f.text and f.text.strip()]; [json.loads(f.text) for f in fields]; print(len(fields))"

git diff --check
```

Runtime validation:

- `GET /api/v1/properties/options`
- `GET /api/v1/properties/4`
- `GET /api/v1/openapi.json`

## Risks

- Existing database rows may contain arbitrary `property_situation` strings from the previous `fields.Char` model.
- Clients that send lowercase English values like `occupied` or `vacant` for `property_situation` must switch to the documented selectable values.
- `status` remains as a legacy alias, so clients may confuse it with a separate field. New clients should use `property_status`.

## Rollback Notes

If the selection conversion causes data incompatibility:

1. Inspect distinct existing values in `real_estate_property.property_situation`.
2. Map invalid values into the seven accepted values.
3. Re-run module upgrade.
