# Implementation Plan: Property Attachments Upload API

**Branch**: `017-property-attachments-upload-api` | **Date**: 2026-05-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-property-attachments-upload-api/spec.md`

---

## Summary

Expose four REST endpoints under `/api/v1/properties/{id}/attachments` for uploading, listing, downloading and deleting files attached to a real-estate property. Files are stored as `ir.attachment` records linked to `real.estate.property`. Content validation uses `python-magic` (magic bytes), filename sanitization uses `werkzeug.utils.secure_filename`, and the size limit is read from the Odoo native parameter `web.max_file_upload_size`. All endpoints are guarded by the triple-decorator security pattern (`@require_jwt + @require_session + @require_company`). Downloads are served by a dedicated JWT-authenticated streaming endpoint — never via `/web/content/`.

**Implementation state (discovered during planning)**:

| Artifact | Status |
|---|---|
| Controller `property_attachments_controller.py` (420 lines) | ✅ Implemented — has spec deviations (see Phase 0) |
| Unit tests `test_property_attachments_unit.py` (49 tests) | ✅ Implemented |
| `libmagic1` + `python3-magic` in Dockerfile | ✅ Done (lines 21/25) |
| API / HTTP integration tests | ❌ Missing |
| Swagger via `thedevkitchen_api_endpoint` | ❌ Missing |
| Postman collection (ADR-016) | ❌ Missing |
| `serialize_property()` updated for `download_url` | ❌ Missing (Phase 4) |
| Constitution v1.7.0 update | ❌ Missing (Phase 5) |

---

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: Odoo 18.0 ORM, `python-magic` (system: `libmagic1`), `werkzeug.utils.secure_filename`
**Storage**: PostgreSQL via `ir.attachment` ORM; Odoo filestore on disk (`attachment.raw` for reads, `base64.b64encode(content)` for writes)
**Testing**: Odoo `TransactionCase` (unit) + Python `unittest.mock` (controller isolation); E2E via bash scripts (pattern from Feature 013/015)
**Target Platform**: Linux Docker container — Odoo 18.0 (`odoo/odoo:18.0`)
**Project Type**: Single Odoo module (`quicksol_estate`)
**Performance Goals**: ≤128 MB per file (configurable via `ir.config_parameter`); in-memory `attachment.raw` read acceptable for configured size ceiling; list endpoint ≤100ms for typical paginated responses
**Constraints**:
- `libmagic1` MUST be in Dockerfile — already confirmed at lines 21/25 of `18.0/Dockerfile`
- No new database models — `ir.attachment` is the sole storage entity
- No custom settings model — `ir.config_parameter` is the configuration mechanism
- `download_url` INVARIANT: NEVER contains `/web/content/`; always `/api/v1/...`

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Check | Status | Notes |
|-----------|-------|--------|-------|
| I — Security | Triple decorators on all 4 endpoints | ✅ PASS | `@require_jwt + @require_session + @require_company` confirmed in controller |
| I — Security | Magic bytes validation | ✅ PASS | `python-magic` with `libmagic1` in Dockerfile, no fallback |
| I — Security | Secure download (no redirect to `/web/content/`) | ✅ PASS | `Response(content, ...)` streaming, invariant enforced in unit tests |
| I — Security | Anti-enumeration (404 before 403) | ✅ PASS | `_fetch_property_for_company` resolves company-scoped domain first |
| II — Test Coverage | Unit tests for security validations | ✅ PASS | 49 unit tests already implemented |
| II — Test Coverage | API/E2E tests for all endpoints | ⚠️ GAP | No HTTP integration tests — see Phase 0: gap-07, gap-08 |
| III — API-First | 4 REST endpoints via `/api/v1/...` | ✅ PASS | All 4 routes implemented with correct HTTP methods |
| III — API-First | OpenAPI documentation | ⚠️ GAP | Not in `thedevkitchen_api_endpoint` table — see Phase 0: gap-09 |
| IV — Multi-Tenancy | `company_id` on every `ir.attachment` | ✅ PASS | `create()` includes `company_id: request.env.company.id` |
| IV — Multi-Tenancy | Cross-company returns 404 | ✅ PASS | `_fetch_property_for_company` applies `request.company_domain` |
| V — ADR Governance | ADR-005, ADR-011, ADR-016 compliance | ⚠️ GAP | Swagger (ADR-005) and Postman (ADR-016) missing — see gap-09, gap-10 |
| VI — Headless | All routes via Gateway (`/api/v1/...`) | ✅ PASS | No bypass to Odoo native routes |

**Constitution Violations**: None. All deviations are implementation gaps (missing artifacts), not architectural violations. No complexity exceptions required.

---

## Project Structure

### Documentation (this feature)

```
specs/017-property-attachments-upload-api/
├── spec.md              ✅ Complete (42/42 security checklist items closed)
├── checklists/
│   └── security.md      ✅ 42/42 CLOSED
├── plan.md              ✅ This file
├── research.md          ✅ Phase 0 output
├── data-model.md        ✅ Phase 1 output
├── contracts/           ✅ Phase 1 output
│   ├── upload.yaml
│   ├── list.yaml
│   ├── download.yaml
│   └── delete.yaml
├── quickstart.md        ✅ Phase 1 output
└── tasks.md             (speckit.tasks — NOT created by speckit.plan)
```

### Source Code (Odoo module)

```
18.0/extra-addons/quicksol_estate/
├── controllers/
│   └── property_attachments_controller.py   ✅ Implemented (420 lines) — needs gap alignment
├── tests/
│   ├── unit/
│   │   └── test_property_attachments_unit.py ✅ Implemented (49 tests)
│   └── api/
│       └── test_property_attachments_api.py  ❌ Missing — Phase 2
│   └── fixtures/
│       ├── seed_image.jpg       (verify in Phase 2)
│       ├── seed_document.pdf    (verify in Phase 2)
│       ├── seed_malicious.jpg   (verify in Phase 2)
│       └── seed_large.jpg       (verify in Phase 2)
integration_tests/
└── test_us17_*.sh                            ❌ Missing — Phase 2
```

---

## Phase 0: Research

> All technical unknowns were resolved during spec refinement (security checklist, 42/42 items closed). Key decisions are documented as D001–D007 in `spec.md`. This phase documents only the implementation gaps between the existing controller and the finalized spec.

Full findings in [research.md](research.md).

### Gap Inventory

| ID | Category | Description | Phase |
|----|----------|-------------|-------|
| gap-01 | Error format | 413 body: missing `received_size`; error code `PAYLOAD_TOO_LARGE` → `file_too_large` | 2 |
| gap-02 | Error format | 422 body: error code `UNPROCESSABLE_ENTITY` → `attachment_limit_exceeded`; missing `detail`, `attachment_type`, `limit`, `current` | 2 |
| gap-03 | Error format | 400 bodies: generic `VALIDATION_ERROR` → specific codes `missing_file`, `missing_attachment_type`, `invalid_attachment_type` | 2 |
| gap-04 | Error format | 415 bodies: `UNSUPPORTED_MEDIA_TYPE` → `unsupported_mime` (global) and `mime_mismatch` (wrong type) | 2 |
| gap-05 | Validation | FR1.5a missing: no zero-byte file validation → 400 `empty_file` | 2 |
| gap-06 | Constants | Quantity limits read from `ir.config_parameter` instead of hardcoded constants | 2* |
| gap-07 | Tests | No API/HTTP integration tests (`tests/api/test_property_attachments_api.py`) | 2 |
| gap-08 | Tests | No E2E bash scripts (`integration_tests/test_us17_*.sh`) | 2 |
| gap-09 | Swagger | No records in `thedevkitchen_api_endpoint` for 4 endpoints (ADR-005) | 3 |
| gap-10 | Postman | No collection for Feature 017 (ADR-016) | 3 |
| gap-11 | Spec 016 | `serialize_property()` not updated for `download_url` via `/api/v1/...` | 4 |
| gap-12 | Constitution | v1.6.0 → v1.7.0 with 5 new patterns from Feature 017 | 5 |

*gap-06 requires owner decision before implementation (see Decision record below).

### Decision Record: gap-06 — Quantity Limits

**Current implementation**: reads `ir.config_parameter` keys `quicksol_estate.max_images_per_property` / `quicksol_estate.max_documents_per_property`, raising `ValueError` if missing.

**Spec requirement** (FR1.4, D005): hardcoded constants `MAX_IMAGES_PER_PROPERTY = 50`, `MAX_DOCUMENTS_PER_PROPERTY = 20`.

**Analysis**:
- Configurable approach (current): more flexible but contradicts spec, adds hidden bootstrap risk (missing param → `ValueError` + 500)
- Hardcoded constants (spec): simpler, no hidden dependencies, no custom admin config required
- The spec explicitly rejected a custom settings model (D005 decision rationale)

**Recommendation**: Align with spec. Convert to hardcoded constants. Remove `_get_max_images_per_property()` and `_get_max_documents_per_property()` helpers. Update unit tests that reference these config param keys.

**Owner action required**: Confirm before speckit.tasks generates the implementation task for gap-06.

---

## Phase 1: Design Artifacts

### data-model.md → [data-model.md](data-model.md)

**Entity**: `ir.attachment` (Odoo native — no new model created)

| Field | Type | Source / Value | API exposure |
|-------|------|---------------|--------------|
| `id` | Integer (PK) | ORM auto | `id` in response |
| `name` | Char | `secure_filename(upload.filename)` ∥ `'untitled'` | `name` in response |
| `datas` | Binary | `base64.b64encode(content)` | Write-only (ORM internal) |
| `raw` | bytes (computed) | ORM reads filestore | Used for download streaming |
| `res_model` | Char | Hard-coded `'real.estate.property'` | Not exposed |
| `res_id` | Integer | `property_id` from URL | Not exposed |
| `mimetype` | Char | `_detect_mime(content)` — magic bytes result | `mimetype` in response |
| `description` | Char | `'image'` or `'document'` | `attachment_type` in response |
| `company_id` | Many2one → `res.company` | `request.env.company.id` | Not exposed |
| `file_size` | Integer (computed) | ORM | `size` in response |
| `create_date` | Datetime | ORM auto | `uploaded_at` (ISO 8601 Z) |

**Module constants** (after gap-06 fix):
```python
MAX_IMAGES_PER_PROPERTY    = 50
MAX_DOCUMENTS_PER_PROPERTY = 20
DEFAULT_MAX_FILE_BYTES     = 134_217_728  # 128 MB
CONFIG_PARAM_MAX_SIZE      = 'web.max_file_upload_size'

TYPE_IMAGE    = 'image'
TYPE_DOCUMENT = 'document'

ALLOWED_IMAGE_MIMETYPES = frozenset({'image/jpeg', 'image/png', 'image/webp'})
ALLOWED_DOCUMENT_MIMETYPES = frozenset({
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
})
```

**Lifecycle**:
- Create: `ir.attachment.create(...)` called after all validations pass
- Read: `att.raw` (bytes) for download; `_serialize_attachment()` for list/upload response
- Delete: `att.unlink()` — hard delete, documented exception to ADR-015 (`ir.attachment` is infrastructure, not a domain entity)
- Cascade: Odoo does NOT cascade `ir.attachment` on property soft-delete (`active=False`). FR3.4 was removed from spec as out-of-scope.

**Serialized API representation** (per attachment):
```json
{
  "id": 42,
  "name": "contract.pdf",
  "mimetype": "application/pdf",
  "size": 204800,
  "attachment_type": "document",
  "uploaded_at": "2026-05-08T14:30:00Z",
  "links": {
    "download": "/api/v1/properties/5/attachments/42/download",
    "self": "/api/v1/properties/5/attachments/42"
  }
}
```

### contracts/ → [contracts/](contracts/)

Full OpenAPI 3.0 schemas in individual files. Summary:

| Contract | Method | Path | Auth | RBAC |
|----------|--------|------|------|------|
| `upload.yaml` | POST | `/api/v1/properties/{property_id}/attachments` | Triple | Owner / Manager |
| `list.yaml` | GET | `/api/v1/properties/{property_id}/attachments` | Triple | All RE roles |
| `download.yaml` | GET | `/api/v1/properties/{property_id}/attachments/{attachment_id}/download` | Triple | All RE roles |
| `delete.yaml` | DELETE | `/api/v1/properties/{property_id}/attachments/{attachment_id}` | Triple | Owner / Manager |

**Unified error envelope** (FR6.9):
```json
{"error": "<snake_case>", "detail": "<human-readable string>"}
```
Extended fields per error code:

| Code | Extra fields |
|------|-------------|
| `file_too_large` | `"max_size_bytes": N, "received_size": N` |
| `attachment_limit_exceeded` | `"attachment_type": "image\|document", "limit": N, "current": N` |
| `invalid_attachment_type` | `"received": "<value>"` |

### quickstart.md → [quickstart.md](quickstart.md)

Developer onboarding steps for Feature 017. Key sections:
1. Verify `libmagic1` in Dockerfile (already at lines 21/25 of `18.0/Dockerfile`)
2. Run unit tests without Odoo container
3. Run API integration tests against live `odoo18` container
4. Configure `web.max_file_upload_size` via Odoo UI or `ir.config_parameter` for test scenarios
5. E2E bash test invocation pattern

---

## Post-Design Constitution Re-Check

*After Phase 1, all gates still pass. No new violations introduced by design decisions.*

| New Pattern | Constitution Impact | Action |
|---|---|---|
| File Upload Sub-resource | New architectural pattern | Add to Constitution v1.7.0 (Phase 5) |
| Magic Bytes Validation | New security requirement | Add to Constitution v1.7.0 (Phase 5) |
| Secure Download Endpoint + Gateway bypass risk | New security constraint | Add to Constitution v1.7.0 (Phase 5) |
| Gateway-Aware URL Generation | `download_url` invariant | Add to Constitution v1.7.0 (Phase 5) |
| Global File Size via `ir.config_parameter` | Existing Odoo pattern | Add to Constitution v1.7.0 (Phase 5) |

---

## Next Steps

1. **Owner decision** on gap-06 (hardcoded constants vs configurable via `ir.config_parameter`)
2. Run `speckit.tasks` to generate `tasks.md` with dependency-ordered implementation tasks
3. Implementation order: Phase 2 (gap alignment + tests) → Phase 3 (Swagger + Postman) → Phase 4 (serialize_property) → Phase 5 (Constitution)
