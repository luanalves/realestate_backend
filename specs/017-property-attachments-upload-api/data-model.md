# Data Model: Property Attachments Upload API

**Feature**: 017 — Property Attachments Upload API
**Date**: 2026-05-08

---

## Storage Entity: `ir.attachment` (Odoo native)

No new database model is created. All attachments are stored as `ir.attachment` records linked to `real.estate.property` via the standard `res_model` / `res_id` pattern.

### Field Reference

| Field | Odoo type | Source on write | API read name | Notes |
|-------|-----------|----------------|---------------|-------|
| `id` | Integer (PK) | ORM auto-increment | `id` | Exposed in response |
| `name` | Char | `secure_filename(upload.filename)` ∥ `'untitled'` | `name` | Sanitized; path traversal stripped |
| `datas` | Binary | `base64.b64encode(raw_bytes)` | (hidden) | ORM stores base64; not exposed in API |
| `raw` | bytes (computed) | ORM reads filestore on demand | (streaming) | Used by download endpoint only |
| `res_model` | Char | Hard-coded `'real.estate.property'` | (hidden) | Binds to property model |
| `res_id` | Integer | `property_id` from URL path | (hidden) | FK to `real.estate.property.id` |
| `mimetype` | Char | `magic.from_buffer(content[:2048], mime=True)` | `mimetype` | Magic bytes result — never client-declared |
| `description` | Char | `'image'` or `'document'` (enum) | `attachment_type` | Internal discriminator; field name differs from API key |
| `company_id` | Many2one → `res.company` | `request.env.company.id` | (hidden) | Multi-tenancy isolation |
| `file_size` | Integer (computed) | ORM (byte count) | `size` | Read from ORM after write |
| `create_date` | Datetime | ORM auto | `uploaded_at` | Serialized as `YYYY-MM-DDTHH:MM:SSZ` |

### IR Attachment Domain Filter

All queries use this base domain to scope to Feature 017 attachments only (excluding Odoo chatter attachments, profile photos, etc.):

```python
[
    ('res_model', '=', 'real.estate.property'),
    ('res_id', '=', property_id),
    ('description', 'in', ['image', 'document']),
]
```

Legacy attachment handling (Feature 016 compatible): `_fetch_attachment()` also checks `res_model in ('real.estate.property.photo', 'real.estate.property.document')` and resolves the `property_id` foreign key for backward compatibility.

---

## Module Constants

Defined at module level in `controllers/property_attachments_controller.py`:

```python
# Quantity limits (hardcoded — spec D005)
MAX_IMAGES_PER_PROPERTY    = 50
MAX_DOCUMENTS_PER_PROPERTY = 20

# Size limit
DEFAULT_MAX_FILE_BYTES = 134_217_728   # 128 MB fallback
CONFIG_PARAM_MAX_SIZE  = 'web.max_file_upload_size'  # ir.config_parameter key

# Type discriminator values
TYPE_IMAGE    = 'image'
TYPE_DOCUMENT = 'document'

# MIME whitelists (magic bytes result)
ALLOWED_IMAGE_MIMETYPES = frozenset({
    'image/jpeg',
    'image/png',
    'image/webp',
})

ALLOWED_DOCUMENT_MIMETYPES = frozenset({
    'application/pdf',
    'application/msword',                                                          # .doc
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',    # .docx
    'application/vnd.ms-excel',                                                    # .xls
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',           # .xlsx
})

ALLOWED_MIMETYPES = ALLOWED_IMAGE_MIMETYPES | ALLOWED_DOCUMENT_MIMETYPES
```

> **Note (gap-06)**: Current controller uses `ir.config_parameter` for quantity limits. After owner decision, replace with the hardcoded constants above and remove `_get_max_images_per_property()` / `_get_max_documents_per_property()` helpers.

---

## API Serialization Format

### Single Attachment Object

```json
{
  "id": 42,
  "name": "floor-plan.pdf",
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

Fields:
- `id` ← `ir.attachment.id`
- `name` ← `ir.attachment.name`
- `mimetype` ← `ir.attachment.mimetype` (magic bytes result)
- `size` ← `ir.attachment.file_size` (integer, bytes)
- `attachment_type` ← `ir.attachment.description` (`'image'` or `'document'`)
- `uploaded_at` ← `ir.attachment.create_date` formatted as ISO 8601 UTC
- `links.download` ← always `/api/v1/properties/{property_id}/attachments/{id}/download` — NEVER `/web/content/`
- `links.self` ← present only in upload 201 response (`include_self_link=True`)

### Upload 201 Response

```json
{
  "status": "success",
  "data": {
    "id": 42,
    "name": "floor-plan.pdf",
    "mimetype": "application/pdf",
    "size": 204800,
    "attachment_type": "document",
    "uploaded_at": "2026-05-08T14:30:00Z",
    "links": {
      "download": "/api/v1/properties/5/attachments/42/download",
      "self": "/api/v1/properties/5/attachments/42"
    }
  }
}
```

### List 200 Response

```json
{
  "status": "success",
  "data": {
    "items": [
      { "id": 42, "name": "floor-plan.pdf", "mimetype": "application/pdf",
        "size": 204800, "attachment_type": "document",
        "uploaded_at": "2026-05-08T14:30:00Z",
        "links": { "download": "/api/v1/properties/5/attachments/42/download" }
      }
    ],
    "pagination": {
      "total": 1,
      "limit": 50,
      "offset": 0
    }
  }
}
```

Note: `links.self` is omitted from list items (only present in upload response).
`pagination.total` reflects only attachments visible to the current company (CHK019 / FR7.4).

---

## RBAC Authorization Matrix

| Endpoint | Owner | Manager | Agent | Receptionist | Portal / External |
|----------|-------|---------|-------|-------------|-------------------|
| POST (upload) | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |
| GET (list) | ✅ | ✅ | ✅ | ✅ | ❌ 401 |
| GET (download) | ✅ | ✅ | ✅ | ✅ | ❌ 401 |
| DELETE | ✅ | ✅ | ❌ 403 | ❌ 403 | ❌ 401 |

Authorization precedence (anti-enumeration):
1. `@require_company` → 403 `no_company` if no RE company
2. `_fetch_property_for_company()` → 404 if property not in company scope (before role check)
3. `_is_agent_only()` → 403 `forbidden` if role insufficient

---

## Error Codes Reference (FR6.9 — Unified Envelope)

```json
{"error": "<snake_case>", "detail": "<string>"}
```

| HTTP | `error` | Condition | Extra fields |
|------|---------|-----------|-------------|
| 400 | `missing_file` | No `file` field in multipart | — |
| 400 | `missing_attachment_type` | No `attachment_type` field | — |
| 400 | `invalid_attachment_type` | Value not `image` or `document` | `"received": "<value>"` |
| 400 | `empty_file` | File is 0 bytes (FR1.5a) | — |
| 400 | `missing_filename` | `secure_filename()` returns `''` AND fallback not applied | — (fallback `'untitled'` is applied; this code is reserved) |
| 413 | `file_too_large` | `len(content) > max_bytes` | `"max_size_bytes": N, "received_size": N` |
| 415 | `unsupported_mime` | Detected MIME not in global whitelist | — |
| 415 | `mime_mismatch` | Detected MIME valid globally but not for declared `attachment_type` | — |
| 422 | `attachment_limit_exceeded` | `current_count >= max_count` for type | `"attachment_type": "image\|document", "limit": N, "current": N` |
| 500 | `internal_error` | Unhandled exception | — |

---

## Lifecycle / Cascade Notes

- **Create**: after all validations pass → `ir.attachment.create({...})`
- **Read**: `att.raw` (bytes, from filestore) for download; `_serialize_attachment()` for JSON responses
- **Delete**: `att.unlink()` — **hard delete**. Documented exception to ADR-015 (`ir.attachment` is infrastructure, not a domain entity with audit history requirements)
- **Property soft-delete**: Odoo does NOT auto-cascade `ir.attachment` when a property's `active` field is set to `False`. FR3.4 was removed from spec as out-of-scope. Cleanup of orphaned attachments after property archive is a separate operational concern.
