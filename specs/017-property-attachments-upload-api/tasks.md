# Tasks: Property Attachments Upload API (017) — Gap Alignment & Missing Artifacts

**Input**: Design documents from `specs/017-property-attachments-upload-api/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅
**Branch**: `017-property-attachments-upload-api`

**Context**: Controller (`property_attachments_controller.py`, 420 lines) and unit tests (`test_property_attachments_unit.py`, 49 tests) are already implemented. This tasks.md covers the **12 gaps** between the existing implementation and the finalized spec (see `research.md`). The previous implementation sprint is complete; this sprint covers gap alignment + missing artifacts.

**Organization**: Tasks grouped by User Story. Phase 2 (gap-06 constants) is foundational and must complete before US1/US2 upload tests can pass. Tests NOT generated as separate tasks — follow test strategy embedded within each phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files or independent code sections)
- **[Story]**: User story from spec.md (US1–US6)
- Paths relative to repository root

---

## Phase 1: Setup

> ✅ **Completed in previous sprint** — `libmagic1` in Dockerfile, controller registered in `__init__.py`, all 4 endpoint methods implemented (420 lines), 49 unit tests created.

No new setup tasks.

---

## Phase 2: Foundational — gap-06 Quantity Limits Constants

**Purpose**: Replace `ir.config_parameter` lookup for **quantity** limits with hardcoded constants. Blocking for all US1/US2 tests that assert `422 attachment_limit_exceeded`.

**⚠️ CRITICAL**: US1/US2 quantity-limit assertions fail until this phase is complete.

- [X] T001 ~~Remove helpers; replace with hardcoded constants~~ → **Revised**: helpers kept, now read from `ir.config_parameter` (seeded via `system_parameters.xml`); `_DEFAULT_*` constants removed; limits 100% from DB (gap-06, D005)
- [X] T002 [P] Unit tests updated: `TestQuantityLimitConstants` tests `CONFIG_PARAM_MAX_IMAGES/DOCUMENTS` keys, `_get_max_images/documents_per_property()` helpers, and asserts `_DEFAULT_*` constants do NOT exist (gap-06)

**Checkpoint**: `_get_max_images_per_property()` and `_get_max_documents_per_property()` removed; unit tests pass with hardcoded constants

---

## Phase 3: US1 + US2 — Upload Error Code Alignment (Priority: P1) 🎯 MVP

**User Stories**: US1 (imagens), US2 (documentos)
**Goal**: All 400/413/415/422 error bodies exactly match the spec error envelope (FR1.1a, FR1.3, FR1.4, FR6.7, FR6.9); zero-byte validation added (FR1.5a)

**Independent Test**:
```bash
# 413 must include received_size field
curl -X POST http://localhost:8069/api/v1/properties/1/attachments \
  -H "Authorization: Bearer $JWT" -H "Cookie: session_id=$SID" \
  -F "file=@/tmp/large.bin" -F "attachment_type=image"
# → {"error": "file_too_large", "detail": "...", "max_size_bytes": 134217728, "received_size": <N>}

# 422 must include full body
# (upload 51st image)
# → {"error": "attachment_limit_exceeded", "detail": "...", "attachment_type": "image", "limit": 50, "current": 50}
```

### Implementation

- [X] T003 [US1] Fix 413 error body in `upload_attachment()` in `18.0/extra-addons/quicksol_estate/controllers/property_attachments_controller.py`: change error code from `PAYLOAD_TOO_LARGE` to `file_too_large`; add `received_size=len(content)` and a `detail` message to the error_response call (gap-01, FR1.3)
- [X] T004 [US1] Fix 422 error body in `upload_attachment()` in `property_attachments_controller.py`: change error code from `UNPROCESSABLE_ENTITY` to `attachment_limit_exceeded`; add extra fields `detail`, `attachment_type`, `limit`, `current` to the error_response call (gap-02, FR1.4)
- [X] T005 [P] [US1] Fix 400 missing-file error code in `upload_attachment()` in `property_attachments_controller.py`: replace generic `VALIDATION_ERROR` with `missing_file` (gap-03a, FR1.1a)
- [X] T006 [P] [US1] Fix 400 missing-attachment_type error code in `upload_attachment()` in `property_attachments_controller.py`: replace `VALIDATION_ERROR` with `missing_attachment_type` (gap-03b, FR1.1a)
- [X] T007 [P] [US1] Fix 400 invalid-attachment_type error in `upload_attachment()` in `property_attachments_controller.py`: replace `VALIDATION_ERROR` with `invalid_attachment_type` and add `received=attachment_type` as extra field (gap-03c, FR1.1a)
- [X] T008 [P] [US1] Fix 415 MIME error bodies in `upload_attachment()` in `property_attachments_controller.py`: split single 415 path into two — `unsupported_mime` (MIME not in any whitelist) and `mime_mismatch` (MIME valid globally but wrong for declared `attachment_type`); both return HTTP 415 and include detected MIME in `detail` (gap-04, FR6.7)
- [X] T009 [US1] Add zero-byte file validation (FR1.5a) in `upload_attachment()` in `property_attachments_controller.py`: immediately after `content = upload.read()`, if `len(content) == 0` return `400 Bad Request` with `{"error": "empty_file", "detail": "File content cannot be empty."}` (gap-05)
- [X] T010 [P] [US1] Add unit tests to `18.0/extra-addons/quicksol_estate/tests/unit/test_property_attachments_unit.py` covering all fixed error codes: `test_413_body_includes_received_size()`, `test_422_body_has_all_fields()`, `test_400_missing_file_code()`, `test_400_missing_type_code()`, `test_400_invalid_type_includes_received()`, `test_415_unsupported_mime_code()`, `test_415_mime_mismatch_code()`, `test_400_empty_file_rejected()`

**Checkpoint**: All upload error bodies match spec FR1.1a/FR1.3/FR1.4/FR6.7/FR6.9; 8 new unit tests pass

---

## Phase 4: US6 — List Endpoint Verification (Priority: P1) 🎯 MVP

**User Story**: US6
**Goal**: Confirm existing list handler matches `contracts/list.yaml` — especially FR7.4 (company-scoped `total`), pagination defaults, and `attachment_type` query-param validation

**Independent Test**:
```bash
curl -X GET "http://localhost:8069/api/v1/properties/1/attachments?limit=5&offset=0" \
  -H "Authorization: Bearer $JWT" -H "Cookie: session_id=$SID"
# → {"items": [...], "pagination": {"total": N, "limit": 5, "offset": 0}}
# total = company-scoped count (not global)
```

- [X] T011 [US6] Read list handler in `18.0/extra-addons/quicksol_estate/controllers/property_attachments_controller.py` and verify: `total` is computed by `search_count()` on the same company-scoped domain (FR7.4); default `limit=50`, max `limit=100`, `offset=0`; `attachment_type` query param validated against `{TYPE_IMAGE, TYPE_DOCUMENT}` before filtering; each item's `links` contains only `download` (no `self`)

**Checkpoint**: List handler verified correct — no code change expected

---

## Phase 5: US3 — Download Endpoint Verification (Priority: P1) 🎯 MVP

**User Story**: US3
**Goal**: Confirm download handler reads `att.raw`, sets required security headers, and never redirects to `/web/content/`

**Independent Test**:
```bash
curl -sI "http://localhost:8069/api/v1/properties/1/attachments/42/download" \
  -H "Authorization: Bearer $JWT" -H "Cookie: session_id=$SID" | grep -E "CSP|X-Content|Disposition"
# → Content-Security-Policy: default-src 'none'
# → X-Content-Type-Options: nosniff
# → Content-Disposition: attachment; filename="..."
```

- [X] T012 [US3] Read download handler in `18.0/extra-addons/quicksol_estate/controllers/property_attachments_controller.py` and verify: `attachment.raw` used for bytes (not `datas`); `werkzeug.wrappers.Response` constructed with `Content-Security-Policy: default-src 'none'`, `X-Content-Type-Options: nosniff`, `Content-Disposition: attachment; filename="..."` headers; no redirect to `/web/content/` (FR2.3, FR2.4)

**Checkpoint**: Download handler verified correct — no code change expected

---

## Phase 6: US4 — Delete Endpoint Verification (Priority: P2)

**User Story**: US4
**Goal**: Confirm delete handler enforces Owner/Manager RBAC, calls `unlink()` (hard delete), returns HTTP 204 with empty body

**Independent Test**:
```bash
# Agent must receive 403
curl -X DELETE "http://localhost:8069/api/v1/properties/1/attachments/42" \
  -H "Authorization: Bearer $AGENT_JWT" -H "Cookie: session_id=$SID" -w "%{http_code}"
# → 403
```

- [X] T013 [US4] Read delete handler in `18.0/extra-addons/quicksol_estate/controllers/property_attachments_controller.py` and verify: RBAC check blocks Agent profile (403) before calling `_fetch_attachment()`; `attachment.unlink()` called (not `active=False`); returns `Response('', status=204)` with empty body (FR3.1, FR3.2, FR3.3)

**Checkpoint**: Delete handler verified correct — no code change expected

---

## Phase 7: US5 — Config Dynamic Behavior Verification (Priority: P2)

**User Story**: US5
**Goal**: Confirm `_get_max_upload_bytes()` reads `ir.config_parameter` dynamically per-request (no module-level caching that would require restart to pick up config changes)

- [X] T014 [US5] Read `_get_max_upload_bytes()` in `18.0/extra-addons/quicksol_estate/controllers/property_attachments_controller.py` and verify: calls `env['ir.config_parameter'].sudo().get_param(CONFIG_PARAM_MAX_SIZE, default=DEFAULT_MAX_FILE_BYTES)` inside the method body (not at import time or module level); returns `int` cast of result; default is `134_217_728` (128 MB)

**Checkpoint**: Size limit is dynamically read; no restart needed after config change

---

## Phase 8: API Integration Tests (gap-07)

**Purpose**: HTTP-level tests (Odoo `TransactionCase`) covering all 4 endpoints, multi-tenancy, and RBAC

- [X] T015 Create `18.0/extra-addons/quicksol_estate/tests/api/test_property_attachments_api.py` as `TransactionCase` subclass; `setUp` loads fixtures from `tests/fixtures/` and configures `web.max_file_upload_size=10485760` for size tests; test methods:
  - [US1] `test_owner_uploads_image_returns_201_with_metadata()` — verify all serialized fields + download_url format
  - [US1] `test_upload_size_exceeded_returns_413_with_received_size()` — exact body match
  - [US1] `test_upload_unsupported_mime_returns_415_unsupported_mime_code()` — `error` == `unsupported_mime`
  - [US1] `test_upload_mime_mismatch_returns_415_mime_mismatch_code()` — image bytes with attachment_type=document
  - [US1] `test_upload_51_images_returns_422_attachment_limit_exceeded_full_body()` — all 4 extra fields present
  - [US1] `test_upload_empty_file_returns_400_empty_file()` — FR1.5a
  - [US1] `test_upload_cross_company_property_returns_404()` — anti-enumeration
  - [US2] `test_manager_uploads_pdf_returns_201()` — document MIME whitelist
  - [US2] `test_max_documents_exceeded_returns_422()` — 21st document
  - [US3] `test_download_returns_binary_with_csp_header()` — `Content-Security-Policy: default-src 'none'`
  - [US3] `test_download_without_jwt_returns_401()` — no auth
  - [US3] `test_download_cross_company_returns_404()` — cross-company isolation
  - [US3] `test_download_wrong_property_attachment_returns_404()` — attachment_id from other property
  - [US4] `test_owner_deletes_returns_204_attachment_gone()` — 204 + verify removed from list response
  - [US4] `test_agent_delete_returns_403()` — RBAC enforcement
  - [US6] `test_list_returns_paginated_items_with_pagination_metadata()` — items[], pagination{total/limit/offset}
  - [US6] `test_list_filter_attachment_type_image_only()` — only images returned, documents excluded
  - [US6] `test_list_total_is_company_scoped_not_global()` — total excludes other-company count (FR7.4)
  - [US5] `test_dynamic_size_limit_via_config_param()` — change `web.max_file_upload_size` → verify 413/201 without restart

**Checkpoint**: Full API test suite covering 19 scenarios; run with `docker compose exec odoo python -m pytest tests/api/test_property_attachments_api.py -v`

---

## Phase 9: E2E Bash Scripts (gap-08)

**Purpose**: End-to-end bash scripts following Feature 015 pattern (`integration_tests/test_us15_*.sh`)

- [X] T016 [P] Create `integration_tests/test_us17_s1_upload_journey.sh` — Owner uploads image and document; assert 201 responses; verify `download_url` begins with `/api/v1/` (not `/web/content/`); verify `mimetype` and `size` fields present (US1, US2)
- [X] T017 [P] Create `integration_tests/test_us17_s2_download_journey.sh` — upload → download via returned `download_url` → assert response headers: `Content-Security-Policy: default-src 'none'`, `X-Content-Type-Options: nosniff`, `Content-Disposition: attachment` (US3)
- [X] T018 [P] Create `integration_tests/test_us17_s3_delete_rbac.sh` — Owner deletes attachment (204); subsequent download returns 404; Agent delete attempt returns 403 (US4)
- [X] T019 [P] Create `integration_tests/test_us17_s4_list_pagination.sh` — upload 6 items; GET with `limit=2&offset=0` returns 2 items with `total=6`; GET with `limit=2&offset=4` returns 2 items; verify `pagination` object structure (US6)
- [X] T020 [P] Create `integration_tests/test_us17_s5_multitenancy_isolation.sh` — upload in company_a; assert company_b user receives 404 on upload/list/download/delete for same property_id (US1–US4, FR5)
- [X] T021 [P] Create `integration_tests/test_us17_s6_rbac_matrix.sh` — 3 roles (Owner, Manager, Agent) × 4 endpoints: assert Owner ✅✅✅✅, Manager ✅✅✅✅, Agent ❌(403)✅✅❌(403) per RBAC authorization matrix in spec.md

**Checkpoint**: 6 E2E scripts executable from `integration_tests/` directory; follow same pattern as `test_us15_s1_agent_creates_service_lifecycle.sh`

---

## Phase 10: Swagger (gap-09, ADR-005)

**Purpose**: Register 4 endpoints in `thedevkitchen_api_endpoint` table via XML data file → module upgrade

> ⚠️ Swagger is generated **dynamically from the database**. Never edit static files.
> Use the **swagger-updater** skill for this phase.

- [X] T022 Add 4 records to the `thedevkitchen_api_endpoint` XML data file in `18.0/extra-addons/quicksol_estate/data/` (verify exact filename by checking existing files in that directory): `POST /api/v1/properties/{property_id}/attachments`, `GET /api/v1/properties/{property_id}/attachments`, `GET /api/v1/properties/{property_id}/attachments/{attachment_id}/download`, `DELETE /api/v1/properties/{property_id}/attachments/{attachment_id}` — use `contracts/upload.yaml`, `contracts/list.yaml`, `contracts/download.yaml`, `contracts/delete.yaml` as schema sources
- [X] T023 *(depends on T022)* Upgrade `quicksol_estate` module to sync Swagger records into DB: `docker compose exec odoo odoo -u quicksol_estate --stop-after-init` from `18.0/` directory; verify 4 new endpoints visible in Swagger UI at `/api/docs`

**Checkpoint**: 4 endpoints documented in Swagger UI; no orphan records in DB

---

## Phase 11: Postman Collection (gap-10, ADR-016)

**Purpose**: Create Feature 017 collection following ADR-016 standards

> Use the **postman-collection-manager** skill for implementation.

- [X] T024 Create `docs/postman/feature017_property_attachments_v1.0_postman_collection.json` → **Note**: Added as folder "23. Property Attachments (Feature 017)" inside the main `quicksol_api_v1.28_postman_collection.json` per ADR-016 (no separate collection per feature) following ADR-016: collection variables `base_url`, `jwt_token`, `session_id`, `property_id`, `attachment_id`; 4 request folders (Upload, List, Download, Delete); `Content-Type: multipart/form-data` on Upload request; auto-save token script on OAuth endpoint; GET requests with query param examples

**Checkpoint**: Collection importable in Postman; all 4 requests executable with configured variables

---

## Phase 12: Polish & Cross-Cutting Concerns

- [ ] T025 ⛔ **BLOCKED** (excluded by user — awaits PM decision) (breaking change — awaits PM decision + mobile team alignment) Update `serialize_property_mapping_fields()` in `18.0/extra-addons/quicksol_estate/controllers/utils/serializers.py`: replace `/web/content/real.estate.property.photo/{photo.id}/image` and `/web/content/real.estate.property.document/{document.id}/file` with `/api/v1/properties/{property_id}/attachments/{aid}/download` — requires PM confirmation that `property_images[].url` and `property_files[].url` breaking change is approved and mobile team is notified (gap-11)
- [X] T026 [P] Update Constitution in `.specify/memory/constitution.md` from v1.6.0 → v1.7.0: add 5 new patterns from Feature 017 — File Upload Sub-resource pattern, Magic Bytes Validation, Secure Download Endpoint (never `/web/content/`), Gateway-Aware URL Generation, Global File Size via `ir.config_parameter` (gap-12)
- [X] T027 [P] Audit logging review: read `property_attachments_controller.py` and verify all rejection paths (MIME invalid, size exceeded, 403, 404 cross-company) emit `_logger.warning()` with minimum required fields per FR6.5: `user_id`, `company_id`, `property_id`, `rejection_code`, `attachment_type`, `file_size_bytes`
- [X] T028 [P] Lint: run `cd 18.0 && bash lint.sh` from repository root and fix any ruff/black/isort errors introduced in `property_attachments_controller.py` by gap-alignment changes (T003–T009)

---

## Dependencies

```
Phase 2 (T001–T002: gap-06 constants)
  → Phase 3 (T003–T010: US1+US2 error alignment)
    → Phase 4 (T011: US6 verify)
    → Phase 5 (T012: US3 verify)
    → Phase 6 (T013: US4 verify)
    → Phase 7 (T014: US5 verify)
      → Phase 8 (T015: API integration tests)
        → Phase 9 (T016–T021: E2E bash scripts)
          → Phase 10 (T022–T023: Swagger)
            → Phase 11 (T024: Postman)
              → Phase 12 (T025–T028: Polish)

T022 → T023 (must generate XML before upgrading module)
T025 independently BLOCKED regardless of phase order
```

## Parallel Execution Opportunities

| Phase | Parallel Tasks |
|-------|---------------|
| Phase 2 | T002 can be written while T001 is being implemented (unit tests alongside code) |
| Phase 3 | T005, T006, T007, T008 (independent conditions in `upload_attachment`) + T010 (unit tests) all parallelizable |
| Phase 9 | T016–T021 (each bash script is an independent file) |
| Phase 12 | T026, T027, T028 (Constitution, audit review, lint — independent files) |

## Implementation Strategy

**MVP scope (Phases 2–5)** — estimated ~2h:
1. Fix gap-06 constants (T001–T002) — ~20 min
2. Fix upload error codes (T003–T009) — ~45 min
3. Update unit tests for new error codes (T010) — ~30 min
4. Verify list/download handlers (T011–T012) — ~15 min

**MVP outcome**: All upload error bodies match spec; unit tests green; list/download verified.

**Phase 2 increment (Phases 6–9)** — estimated ~3h:
- Verify delete + config (T013–T014) — ~15 min
- API integration test file T015 (19 test methods) — ~2h
- E2E bash scripts T016–T021 — ~45 min

**Phase 3 increment (Phases 10–11)** — estimated ~45 min:
- Swagger (T022–T023) — ~20 min
- Postman (T024) — ~25 min

**Phase 4 increment (Phase 12)** — estimated ~30 min:
- Audit + lint (T027–T028) — ~20 min
- Constitution (T026) — ~10 min
- T025 BLOCKED until PM decision

---

## Task Count Summary

| Phase | Tasks | Stories | Notes |
|-------|-------|---------|-------|
| 1 — Setup | 0 | — | ✅ All done in previous sprint |
| 2 — Foundational (gap-06) | 2 | — | Blocking for upload tests |
| 3 — US1+US2 (Upload alignment) | 8 | US1, US2 | Gaps 01–05 |
| 4 — US6 (List verify) | 1 | US6 | No code change expected |
| 5 — US3 (Download verify) | 1 | US3 | No code change expected |
| 6 — US4 (Delete verify) | 1 | US4 | No code change expected |
| 7 — US5 (Config verify) | 1 | US5 | No code change expected |
| 8 — API Integration Tests | 1 | All | gap-07 — 19 test methods in one file |
| 9 — E2E Bash Scripts | 6 | All | gap-08 — 6 script files |
| 10 — Swagger | 2 | — | gap-09, ADR-005 |
| 11 — Postman | 1 | — | gap-10, ADR-016 |
| 12 — Polish | 4 | — | gap-11 BLOCKED, gap-12, lint, audit |
| **Total** | **28** | **6 user stories** | |

**Parallel opportunities**: 10 tasks marked `[P]`
**MVP tasks (Phases 2–5)**: T001–T012 (12 tasks)
