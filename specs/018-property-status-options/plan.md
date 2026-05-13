# Implementation Plan: Property Status and Situation Options

**Branch**: `018-property-status-options`
**Date**: 2026-05-11
**Spec**: [spec.md](./spec.md)
**Flowcharts**: [flowcharts.md](./flowcharts.md)
**Status**: Implemented

## Goal

Expose property availability, status, owner relationship, commercial condition, and FGTS eligibility fields consistently across API responses, Odoo UI, selectable options, Swagger/OpenAPI, and Postman.

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

### Phase 8 - FGTS Eligibility Summary

Decision source: CAIXA/FGTS Moradia Propria rules. For acquisition/construction, the relevant property-side constraint is whether the **property** was object of FGTS use in a previous acquisition/construction transaction less than 3 years ago, counted from the real estate registry date. The API should model a single current summary for the property, not a multi-item history, unless a future audit feature requires full transaction history.

ADR alignment:

| ADR | Application |
|---|---|
| ADR-001 | Add fields to the existing `quicksol_estate` flat module structure and Odoo 18 view; no `attrs`, no `<tree>`. |
| ADR-002 | Use Cypress for Odoo UI E2E and curl-based API E2E for REST behavior. |
| ADR-003 | Cover model/serializer normalization with unit tests and end-to-end API/UI flows. |
| ADR-005 | Update `quicksol_estate/data/api_endpoints.xml`; Swagger is generated from DB records after module upgrade. |
| ADR-016 | Keep Postman collection maintenance in the main versioned collection when endpoint examples change. |
| ADR-018 | Validate typed API fields and reject wrong JSON types with structured `400` errors. |
| ADR-022 | Run Python compile, XML/JSON checks, Cypress verification when possible, and `git diff --check`. |

Fields:

| API field | Odoo field | Type | Purpose |
|---|---|---|---|
| `fgts.accepts_fgts` | `accepts_fgts` | boolean | Property accepts FGTS as a negotiation/payment option. |
| `fgts.used_fgts` | `used_fgts` | boolean | Known previous FGTS use exists for this property. |
| `fgts.last_usage_date` | `fgts_last_usage_date` | date | Registry/reference date of the last known FGTS use on this property. |
| `fgts.eligible_from` | `fgts_eligible_from` | computed date | First date when FGTS may be used again, 3 years after `fgts.last_usage_date`. |
| `fgts.eligible_now` | `fgts_eligible_now` | computed boolean | Whether the property is currently outside the 3-year restriction window. |
| `fgts.usage_notes` | `fgts_usage_notes` | text | Optional notes from registration/certificate review. |

Implementation steps:

- Add model fields and compute methods in `real.estate.property`.
- Add fields to the Odoo property form under Financial Options.
- Return the FGTS fields only inside a single `fgts` object in property serializers.
- Accept `fgts.accepts_fgts`, `fgts.used_fgts`, `fgts.last_usage_date`, and `fgts.usage_notes` in `POST`/`PUT`.
- Validate `fgts.used_fgts` as boolean and `fgts.last_usage_date` as ISO date string through the existing mapping validator.
- Update OpenAPI request/response schemas and examples.
- Update data model and flow documentation.
- Extend unit, curl API E2E, and Cypress UI E2E tests.

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
