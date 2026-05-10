# Phase 0 Research: Property Attachments Upload API

**Date**: 2026-05-08 | **Branch**: `017-property-attachments-upload-api`
**Status**: Complete — all unknowns resolved

---

## Summary

No technical unknowns remain. All architectural decisions were resolved during the security checklist review (42/42 items closed across 8 categories). This document records the confirmed decisions and the implementation gaps discovered when comparing the existing controller against the finalized spec.

---

## Confirmed Decisions

### D001 — `ir.attachment` as storage (no custom model)

- **Decision**: Use Odoo native `ir.attachment` with `res_model='real.estate.property'` and `res_id=property_id`.
- **Rationale**: Standard Odoo pattern. Already used for proposals (`res_model='real.estate.proposal'`). Natively displayed in chatter and attachment panel without custom views.
- **Alternatives rejected**: Custom `real.estate.property.attachment` model — unnecessary complexity, no functional advantage.

### D002 — `ir.attachment.description` as type discriminator

- **Decision**: `description='image'` or `description='document'` — internal discriminator only.
- **Rationale**: No model extension needed. `description` is a free-text field with no Odoo-internal semantic — safe for custom use as a type discriminator.
- **Security**: `description` is NOT exposed as free-text in API requests. `attachment_type` form field is validated against enum `{'image', 'document'}` before being written to `description`.

### D003 — `python-magic` for content validation (no fallback)

- **Decision**: `magic.from_buffer(content[:2048], mime=True)` — detect actual MIME type from file bytes.
- **Rationale**: Prevents script-as-image attacks (PHP, Python, JS disguised as JPEG). `libmagic1` is guaranteed via Dockerfile (lines 21/25 of `18.0/Dockerfile`). Explicit failure (ImportError, MagicException) is safer than silent weak validation.
- **Confirmed**: `libmagic1` present in `18.0/Dockerfile` lines 21 (`libmagic1`) and 25 (`python3-magic`).
- **Alternative rejected**: `mimetypes.guess_type()` — based on filename extension, trivially spoofable.

### D004 — Secure download endpoint (no redirect to `/web/content/`)

- **Decision**: Controller reads `att.raw` (bytes) and returns `werkzeug.wrappers.Response` directly with security headers.
- **Rationale**: `/web/content/{id}` is not behind the API Gateway → no JWT validation → unauthenticated access. Any URL containing `/web/content/` in `download_url` would be a security vulnerability.
- **Headers required**: `Content-Security-Policy: default-src 'none'`, `X-Content-Type-Options: nosniff`.
- **Invariant enforced**: Unit tests T013/T015 assert `download_url` never contains `/web/content/`.

### D005 — `web.max_file_upload_size` for size limit; hardcoded quantity constants

- **Decision**: File size limit from `ir.config_parameter` key `web.max_file_upload_size` (Odoo native, value in bytes). Default 128 MB if absent. Quantity limits hardcoded: `MAX_IMAGES_PER_PROPERTY = 50`, `MAX_DOCUMENTS_PER_PROPERTY = 20`.
- **Rationale**: Reuses Odoo's built-in file upload parameter (admin-configurable via UI without custom code). Hardcoded quantity constants avoid a custom settings model, consistent with spec decision to minimize infrastructure.
- **Gap discovered**: Current controller uses `ir.config_parameter` for quantity limits too (keys `quicksol_estate.max_images_per_property`, `quicksol_estate.max_documents_per_property`). This deviates from spec. See gap-06.

### D006 — No Odoo UI changes

- **Decision**: No custom views, menus, or actions for this feature.
- **Rationale**: `ir.attachment` records with `res_model + res_id` appear automatically in the Odoo chatter and attachment panel. No view code needed.

### D007 — Upload flow: multipart/form-data → bytes → base64 → filestore

- **Decision**: Client sends binary multipart (not base64). Controller reads bytes, validates, then encodes to base64 for `ir.attachment.datas`. Download reverses via `att.raw`.
- **Rationale**: Standard HTTP file upload pattern. Base64 encoding is an ORM implementation detail — not the API contract.

---

## Technology Research

### `python-magic` (resolved)

- **Version**: installed as `python3-magic` in Dockerfile
- **Usage**: `magic.from_buffer(content[:2048], mime=True)` — only first 2048 bytes needed for magic number detection
- **Error handling**: No try/except around `_detect_mime()` — if `libmagic1` is missing, the container is misconfigured; an unhandled ImportError is the correct failure signal

### `werkzeug.utils.secure_filename` (resolved)

- **Already available**: Werkzeug is bundled with Odoo
- **Behavior**: Removes path traversal sequences, strips non-ASCII, replaces spaces with underscores
- **Empty result**: When `secure_filename()` returns `''` (e.g., all-non-ASCII filename), controller falls back to `'untitled'` (FR1.5 spec requirement)

### `ir.attachment.raw` (resolved)

- **Odoo 18.0**: `.raw` property returns `bytes` directly from filestore without loading the full `datas` base64 field. Efficient for streaming large files.
- **No intermediate copy**: filestore is the final destination; no temporary directories involved

### `request.company_domain` (resolved)

- **Source**: `require_company` decorator (ADR-011) sets `request.company_domain` after validating the user has at least one real-estate company. Domain is a list of conditions for filtering by `company_id`.
- **Anti-enumeration**: property not found in company domain → 404 (not 403). This hides existence of cross-company records.

---

## Implementation Gaps (vs Finalized Spec)

### gap-01: 413 error body

| | Current | Spec (FR1.3) |
|---|---|---|
| Error code | `PAYLOAD_TOO_LARGE` | `file_too_large` |
| `received_size` field | Missing | Required |
| `detail` field | Missing | Required |

**Fix**: Update `upload_attachment` handler. Pass `received_size=len(content)` in error extras.

### gap-02: 422 error body

| | Current | Spec (FR1.4) |
|---|---|---|
| Error code | `UNPROCESSABLE_ENTITY` | `attachment_limit_exceeded` |
| `detail` field | Missing | Required |
| `attachment_type` field | Missing | Required |
| `limit` field | Missing | Required |
| `current` field | Missing | Required |

**Fix**: Update 422 `error_response()` call with all required fields.

### gap-03: 400 error bodies (FR1.1a)

| Condition | Current code | Spec code |
|-----------|-------------|-----------|
| No `file` field | `VALIDATION_ERROR` | `missing_file` |
| No `attachment_type` field | `VALIDATION_ERROR` | `missing_attachment_type` |
| Invalid `attachment_type` value | `VALIDATION_ERROR` | `invalid_attachment_type` (+ `received` extra) |

**Fix**: Use specific error codes in `upload_attachment`. Add `"received": attachment_type` extra for `invalid_attachment_type`.

### gap-04: 415 error bodies (FR6.7)

| Condition | Current code | Spec code |
|-----------|-------------|-----------|
| MIME not in global whitelist | `UNSUPPORTED_MEDIA_TYPE` | `unsupported_mime` |
| MIME valid globally but wrong type | `VALIDATION_ERROR` | `mime_mismatch` (HTTP 415) |

**Fix**: Both cases should return 415. Use `unsupported_mime` for global whitelist rejection, `mime_mismatch` for type mismatch.

### gap-05: Empty file validation (FR1.5a)

- **Missing**: No check for `len(content) == 0`
- **Fix**: Add check after `content = upload.read()`. Return 400 `empty_file` if `len(content) == 0`.

### gap-06: Quantity limits source

- **Current**: `ir.config_parameter` (`quicksol_estate.max_images_per_property`, `quicksol_estate.max_documents_per_property`)
- **Spec**: Hardcoded constants `MAX_IMAGES_PER_PROPERTY = 50`, `MAX_DOCUMENTS_PER_PROPERTY = 20`
- **Risk of current approach**: `ValueError` → unhandled → 500 if params are not seeded
- **Fix (pending owner decision)**: Replace `_get_max_images_per_property()` / `_get_max_documents_per_property()` with constant references. Remove the two helper functions.

### gap-07: API integration tests

- **Missing**: `18.0/extra-addons/quicksol_estate/tests/api/test_property_attachments_api.py`
- **Coverage needed**: upload success (image + document), upload failures (all 400/413/415/422 codes), list with pagination + type filter, download (streaming headers), delete (RBAC), cross-company 404

### gap-08: E2E bash scripts

- **Missing**: `integration_tests/test_us17_*.sh`
- **Pattern**: Follow Feature 013/015 E2E test structure (see `integration_tests/test_us15_*.sh`)
- **Scenarios**: US1 upload journey, US3 download journey, US4 delete journey, US6 list journey

### gap-09: Swagger

- **Missing**: 4 records in `thedevkitchen_api_endpoint` table
- **Method**: XML data file → module upgrade → DB → Swagger UI (swagger-updater skill, ADR-005)

### gap-10: Postman collection

- **Missing**: `docs/postman/feature017_property_attachments_v1.0_postman_collection.json`
- **Pattern**: Follow ADR-016 and existing collections in `docs/postman/`

### gap-11: `serialize_property()` integration

- **Missing**: `download_url` field in `property_images` and `property_files` in serializer response
- **Target file**: `18.0/extra-addons/quicksol_estate/controllers/utils/serializers.py`
- **Invariant**: Generated URLs must use `/api/v1/properties/{id}/attachments/{aid}/download` — never `/web/content/{id}`

### gap-12: Constitution v1.7.0

- **Missing**: 5 new patterns from Feature 017 not yet documented
- **Patterns**: File Upload Sub-resource, Magic Bytes Validation, Secure Download Endpoint, Gateway-Aware URL Generation, Global File Size via `ir.config_parameter`
- **Version bump**: MINOR (1.6.0 → 1.7.0)

---

## Summary: No Unknowns Remain

All 7 architectural decisions (D001–D007) are confirmed. All 12 gaps are catalogued with concrete fix descriptions. Phase 1 design can proceed immediately.
