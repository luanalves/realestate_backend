# Implementation Plan: Property Mapping Fields API Completion

**Branch**: `016-property-mapping-fields` | **Date**: 2026-05-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/016-property-mapping-fields/spec.md`

## Summary

Update the existing property REST endpoints to accept, persist, serialize, and document only the fields marked `❌ Faltando` in the `Mapping_Property` spreadsheet. The implementation stays inside the property domain: `GET /api/v1/properties`, `GET /api/v1/properties/{id}`, `POST /api/v1/properties`, and `PUT /api/v1/properties/{id}`. It must not modify proposal, rental credit check, lead, lease, sale, service, or unrelated endpoints.

The technical approach is to reuse existing `real.estate.property` fields when the semantics already match the spreadsheet field, add only truly missing model fields, centralize mapping/validation/serialization helpers for the new API field set, update the property endpoint Swagger records through XML/DB, and cover the change with unit tests plus curl-based API E2E tests.

## Technical Context

**Language/Version**: Python 3.11, Odoo 18.0
**Primary Dependencies**: Odoo ORM, `quicksol_estate`, `thedevkitchen_apigateway`, JWT/session/company middleware, JSON Schema validation helpers where already used
**Storage**: PostgreSQL 15 for business data and attachments; Redis DB1 for sessions/cache
**Testing**: Python `unittest` + mocks for unit tests; shell/curl API E2E tests in `integration_tests/`; no Odoo `HttpCase` for API flows per ADR-003
**Target Platform**: Dockerized Odoo 18.0, database `realestate`
**Project Type**: Existing Odoo addon change in `18.0/extra-addons/quicksol_estate`
**Performance Goals**: Property list/detail must avoid N+1 reads for tags, images, files, owner/contact metadata, and preserve existing pagination limits
**Constraints**: Preserve triple decorators on private endpoints, company isolation, RBAC, HATEOAS pagination links, ignore-unknown behavior if that is the current documented API policy, and no binary attachment content in JSON
**Scale/Scope**: 4 property endpoints, 39 missing API fields, attachment metadata serialization for image/file arrays

## Applicable Rules

| Source | Rule Applied |
|---|---|
| Constitution | Security first, mandatory tests, API-first, multi-tenancy, ADR governance, headless architecture |
| AGENTS.md from prompt | The provided AGENTS content appears to describe Homebrew/brew, not this Odoo repo. Treat it as non-applicable where it conflicts with project files; use this repository's `.github` instructions and ADRs for actual implementation. |
| `.github/copilot-instructions.md` | Work from `18.0` for Docker/Odoo commands; keep authenticated endpoints protected with JWT + session + company context |
| `.github/instructions/controllers.instructions.md` | Keep `@require_jwt`, `@require_session`, `@require_company` on all private property endpoints |
| `.github/instructions/test-strategy.instructions.md` + ADR-003 | Unit tests use Python `unittest`/mocks without DB; API E2E uses curl against real Odoo and `.env`; no JSON-RPC wrapper for new REST tests |
| ADR-005 + `swagger-updater` skill | Swagger/OpenAPI is generated from `thedevkitchen_api_endpoint` DB records; update XML data and upgrade module, never edit static Swagger output |
| ADR-008 / ADR-011 / ADR-017 | Preserve auth, anti-enumeration/company isolation, session fingerprint behavior, and avoid sensitive data in logs |
| ADR-015 | Keep active/soft-delete behavior in list/detail unchanged |
| ADR-016 + `postman-collection-manager` skill | If Postman is updated, update the main collection in `docs/postman/`, increment minor version, and do not create a feature-only collection |
| ADR-018 | Validate typed known fields and return structured errors; unknown fields remain ignored only if existing API behavior already documents/allows it |
| ADR-019 | Preserve existing RBAC matrix for create/update/read operations |
| ADR-022 | Run available lint/static checks and at minimum `py_compile`/`git diff --check` for touched Python/XML/JSON |
| `development-best-practices` skill | Prefer existing module/model/controller patterns, minimize new abstractions, avoid N+1 queries, do not introduce unnecessary `sudo()` expansion |

## Constitution Check

*GATE: Must pass before implementation and be re-checked before tasks are generated.*

| Principle | Check | Status | Notes |
|---|---|---|---|
| I - Security First | No public endpoints are introduced; existing property endpoint decorators stay unchanged. | PASS | `@require_jwt` + `@require_session` + `@require_company` remain mandatory. |
| II - Test Coverage | Unit tests and curl E2E tests are part of this plan before implementation is accepted. | PASS | Cypress is not planned because this feature has no UI scope. |
| III - API-First | REST contract is updated for list/detail/create/update property endpoints. | PASS | Runtime Swagger update goes through XML data records and module upgrade. |
| IV - Multi-Tenancy | Existing `company_id`, `company_ids` validation, RBAC, and anti-enumeration behavior are preserved. | PASS | Tests include cross-company read/write denial. |
| V - ADR Governance | ADR-003, 005, 008, 011, 015, 016, 018, 019, 022 are explicitly applied. | PASS | Any conflict must be documented in `research.md` before implementation. |
| VI - Headless | Backend/API only; no frontend UI implementation. | PASS | Postman/docs may be updated, but no browser UI. |

## Project Structure

### Documentation (this feature)

```text
specs/016-property-mapping-fields/
├── spec.md              # Requirements and field set
├── plan.md              # This file
├── research.md          # Phase 0 findings and decisions
├── data-model.md        # Phase 1 field/storage mapping
├── quickstart.md        # Phase 1 local verification guide
├── contracts/
│   └── openapi.yaml     # Planning contract only; runtime Swagger remains XML/DB
└── tasks.md             # Phase 2 output from speckit.tasks
```

### Source Code (repository root)

```text
18.0/extra-addons/quicksol_estate/
├── models/
│   ├── property.py                  # Add only missing `real.estate.property` fields
│   └── property_auxiliary.py         # Reuse existing tag/photo/document/key models if applicable
├── controllers/
│   ├── property_api.py              # Accept/update property mapping fields, preserve auth/RBAC
│   └── utils/
│       ├── serializers.py           # Serialize stable mapping field block
│       └── schema.py                # Reuse/extend validation helpers if current pattern supports it
├── data/
│   └── api_endpoints.xml            # Update property endpoint Swagger records
├── schemas/
│   ├── property_create.json         # Add only if schema-file pattern is adopted for properties
│   └── property_update.json         # Add only if schema-file pattern is adopted for properties
└── tests/
    └── unit/
        └── test_property_mapping_fields.py

integration_tests/
├── test_us16_property_mapping_fields.sh
└── lib/                             # Reuse auth/session helpers

docs/postman/
└── quicksol_api_vX.Y_postman_collection.json  # Update main collection only if Postman is in scope
```

**Structure Decision**: Implement in the existing `quicksol_estate` addon because the affected endpoints and model already live there. Do not create a new module and do not touch proposal/credit-check modules.

## Execution Phases

### Phase 0 - Discovery and Research

1. Compare every `❌ Faltando` field from `spec.md` against `real.estate.property`, auxiliary property models, and current serializers.
2. Classify each field as one of: existing direct field, existing field with API alias, existing auxiliary relation, truly missing field, or unsupported until clarified.
3. Inspect `property_api.py` create/update/detail/list behavior, especially required fields, optional fields, `sudo()`, RBAC, company filters, and current unknown-field behavior.
4. Inspect `api_endpoints.xml` property records and decide exact schema names following ADR-005: `PropertyCreate`, `PropertyUpdate`, `PropertyResponse`, `PropertyListResponse`, `AttachmentMetadata`, `ErrorResponse`.
5. Record findings and decisions in `research.md`, including any field where spreadsheet meaning does not safely match an existing Odoo field.

### Phase 1 - Data and Contract Design

1. Create `data-model.md` with a table mapping: form field, API field, Odoo storage field/model, type, default, writable/read-only behavior, validation, and serializer output.
2. Reuse existing fields where semantics match, for example publication/video/tour/sign/tag/photo/document style fields, without duplicating data.
3. Add new fields only for unmatched business concepts, such as owner contact aliases, commission metadata, documentation flags, or key location if no existing equivalent exists.
4. Define attachment payload rules:
   - API responses return metadata only: `id`, `name`, `mimetype`, `size`, `download_url`.
   - API requests accept only the format already supported or explicitly designed in this phase.
   - Binary content is never returned inline.
5. Draft `contracts/openapi.yaml` as a planning artifact, then ensure implementation updates `data/api_endpoints.xml` because Swagger runtime is DB-generated.
6. Create `quickstart.md` with local Docker/module-upgrade/test commands.

### Phase 2 - Test-First Tasks

1. Add unit tests before implementation for field conversion, defaults, serializer output, attachment metadata shape, validation errors, and partial-update non-destructive behavior.
2. Add curl E2E tests before implementation for:
   - `POST /api/v1/properties` accepts valid missing-field payload.
   - `GET /api/v1/properties/{id}` returns every missing field with persisted values.
   - `PUT /api/v1/properties/{id}` updates only submitted mapping fields.
   - `GET /api/v1/properties` returns the same mapping schema per item and keeps pagination links.
   - Invalid email/date/boolean/array inputs return structured errors.
   - Unauthorized profile and cross-company access remain denied.
3. Run the new tests once to confirm they fail for the missing behavior before implementation.
4. Generate `tasks.md` with small, independently verifiable tasks after `research.md`, `data-model.md`, `contracts/`, and `quickstart.md` exist.

### Phase 3 - Implementation

1. Add missing model fields in `property.py`, using Odoo field types that match API semantics and existing naming style.
2. Implement or extend mapping helpers so create/update code is not a larger hand-written optional-fields dictionary with duplicated conversion logic.
3. Update serializers to include all missing mapping fields with stable defaults:
   - `None` for omitted string/date values.
   - `False` for omitted boolean values.
   - `[]` for omitted collections.
4. Update create/update endpoint handling for writable fields without changing existing required fields or unrelated payload keys.
5. Preserve all existing auth decorators, RBAC gates, company validation, and active/soft-delete behavior.
6. Update `api_endpoints.xml` property records through the `swagger-updater` workflow and ensure `noupdate="0"` records are upgrade-safe.
7. Update the main Postman collection only if the feature scope includes collection maintenance; use `postman-collection-manager` and increment minor version.

### Phase 4 - Verification

Run checks in this order, adapting exact paths after tasks are generated:

```bash
git diff --check
PYTHONPYCACHEPREFIX=/private/tmp/odoo_pycache python3 -m py_compile 18.0/extra-addons/quicksol_estate/models/property.py 18.0/extra-addons/quicksol_estate/controllers/property_api.py 18.0/extra-addons/quicksol_estate/controllers/utils/serializers.py
cd 18.0
docker compose exec odoo python3 /mnt/extra-addons/quicksol_estate/tests/unit/test_property_mapping_fields.py
cd ..
integration_tests/test_us16_property_mapping_fields.sh
```

When Swagger XML changes are made, also run:

```bash
cd 18.0
docker compose exec odoo odoo -d realestate -u quicksol_estate --stop-after-init
```

If project lint tooling is available and stable in the checkout, include ADR-022 checks before completion. Cypress is intentionally omitted unless a UI change is later added.

## Field Implementation Policy

1. **Only `❌ Faltando` rows**: Do not add or alter fields marked mapped, needs mapping, needs adjustment, or partial.
2. **No proposal scope**: Do not edit proposal, rental credit check, lead, lease, sale, or service endpoints.
3. **Reuse before create**: Existing fields with matching semantics must be serialized under the new API name instead of creating duplicate columns.
4. **Alias intentionally**: If an API field aliases an existing storage field, document that alias in `data-model.md`.
5. **Collections are explicit**: Tags/images/files must have deterministic create/update semantics; omitted arrays do not clear existing values.
6. **No binary JSON**: Image/file responses expose metadata and download links only.
7. **Company and RBAC remain authoritative**: Payload cannot override protected company/security fields outside existing allowed behavior.

## Suggested Agent and Skill Flow

| Step | Local repo capability |
|---|---|
| Planning | `.github/agents/speckit.plan.agent.md` conventions are reflected in this plan |
| Test design | Use `.github/agents/speckit.tests.agent.md` guidance when expanding test cases |
| Task generation | Use `.github/agents/speckit.tasks.agent.md` after Phase 1 docs are complete |
| API docs | Use `.github/skills/swagger-updater/SKILL.md`; update XML/DB, never static Swagger output |
| Postman | Use `.github/skills/postman-collection-manager/SKILL.md` only for main collection updates |
| Implementation review | Use `.github/skills/development-best-practices/SKILL.md` for model/controller/security/performance checks |

## Risks and Open Decisions

| Risk / Decision | Handling |
|---|---|
| Spreadsheet field names may not map 1:1 to current model fields | Resolve in `research.md`; do not duplicate fields when existing semantics match. |
| `property_images` and `property_files` request formats may not be currently supported | Define accepted format in Phase 1 before coding; response metadata is mandatory. |
| `owner_email` and owner phone fields may overlap with `owner_id`, `email_ids`, and `phone_ids` | Decide whether API aliases existing contact relations or adds denormalized convenience fields; document tradeoff. |
| Current create/update behavior appears to ignore unknown optional fields | Align implementation with ADR-018 and FR-016 by documenting and preserving the existing policy unless schema validation is already stricter. |
| Swagger runtime can drift if XML is changed without module upgrade | Include module upgrade and `/api/v1/openapi.json` verification in quickstart/verification tasks. |

## Complexity Tracking

No constitution violations are planned. No complexity exception is required.

## Acceptance Gates

- All fields listed in `spec.md` under "Property Mapping Field Set" are traceable in `data-model.md`.
- Existing property endpoints keep their authentication decorators and company isolation.
- New unit tests and curl E2E tests pass.
- API responses return stable defaults and never inline binary attachment data.
- Swagger records are updated through XML/DB and match the implemented request/response behavior.
- No files under proposal, credit-check, lead, lease, sale, or service endpoints are modified unless a pre-existing shared helper requires a narrowly scoped update.
