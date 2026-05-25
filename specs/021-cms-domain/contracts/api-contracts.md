# API Contracts: CMS Domain (021)

**Date**: 2026-05-24 | **Branch**: `021-cms-domain`
**Auth**: All authenticated routes use `@require_jwt` + `@require_session` + `@require_company` (triple decorator, ADR-011), except the public route which uses `@require_jwt` only.

---

## Base URL: `/api/v1/cms`

---

## Pages

### POST /api/v1/cms/pages
**Auth**: Triple decorator | **Roles**: owner, director, manager

**Request**:
```json
{
  "name": "string (required)",
  "slug": "string (required) — ^[a-z0-9]+(?:-[a-z0-9]+)*$",
  "content": "string (optional) — JSON Puck, max 512KB",
  "template_id": "integer (optional) — copia content do template",
  "title": "string (optional) — SEO title",
  "meta_description": "string (optional)",
  "og_title": "string (optional)",
  "og_description": "string (optional)",
  "og_image_id": "integer (optional) — id de cms.media da mesma imobiliária",
  "canonical_url": "string (optional)",
  "robots_meta": "string (optional) — enum: index,follow | noindex,follow | noindex,nofollow | noindex",
  "structured_data": "string (optional) — JSON-LD válido"
}
```

**Response 201**:
```json
{
  "id": 42,
  "name": "Home",
  "slug": "home",
  "status": "draft",
  "created_at": "2026-05-24T10:00:00Z",
  "updated_at": "2026-05-24T10:00:00Z",
  "links": {
    "self": "/api/v1/cms/pages/42",
    "update": "/api/v1/cms/pages/42",
    "delete": "/api/v1/cms/pages/42"
  }
}
```

**Errors**:
- `422 slug_invalid` — slug com caracteres inválidos
- `422 content_too_large` + `max_size_bytes`, `received_size`
- `422 content_invalid_json`
- `422 structured_data_invalid_json`
- `422 template_not_found` — template_id de outra imobiliária
- `409 slug_conflict` + `field: "slug"`
- `403 forbidden` — role sem permissão

---

### GET /api/v1/cms/pages
**Auth**: Triple decorator | **Roles**: owner, director, manager (todos os status); agent (somente published)

**Query params**: `?page=1&limit=20&status=draft|pending_review|published|archived`

**Response 200**:
```json
{
  "data": [
    {
      "id": 42,
      "name": "Home",
      "slug": "home",
      "status": "draft",
      "title": "Minha Imobiliária | Home",
      "published_at": null,
      "created_at": "2026-05-24T10:00:00Z",
      "updated_at": "2026-05-24T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

> **Nota**: `content` NÃO é retornado na listagem (performance).

---

### GET /api/v1/cms/pages/:id
**Auth**: Triple decorator | **Roles**: owner, director, manager (qualquer status); agent (somente published)

**Response 200**:
```json
{
  "id": 42,
  "name": "Home",
  "slug": "home",
  "status": "published",
  "content": "{...puck json...}",
  "title": "Minha Imobiliária | Home",
  "meta_description": "...",
  "og_title": "...",
  "og_description": "...",
  "og_image_url": "/api/v1/cms/media/5/file",
  "canonical_url": "https://minha-agencia.com/home",
  "robots_meta": "index,follow",
  "structured_data": "{\"@context\":\"https://schema.org\",...}",
  "published_at": "2026-05-24T12:00:00Z",
  "created_at": "2026-05-24T10:00:00Z",
  "updated_at": "2026-05-24T12:00:00Z",
  "links": {
    "self": "/api/v1/cms/pages/42",
    "update": "/api/v1/cms/pages/42",
    "delete": "/api/v1/cms/pages/42"
  }
}
```

**Errors**: `404 not_found`; `403 forbidden` (agent tentando ver draft)

---

### PUT /api/v1/cms/pages/:id
**Auth**: Triple decorator | **Roles**: owner, director, manager (escrita + status); agent (403 para mudança de status)

**Request** (todos os campos são opcionais individualmente):
```json
{
  "name": "string",
  "slug": "string",
  "status": "string — draft|pending_review|published|archived",
  "content": "string — JSON Puck, max 512KB",
  "title": "string",
  "meta_description": "string",
  "og_title": "string",
  "og_description": "string",
  "og_image_id": "integer",
  "canonical_url": "string",
  "robots_meta": "string",
  "structured_data": "string"
}
```

**Response 200**:
```json
{
  "id": 42,
  "status": "published",
  "updated_at": "2026-05-24T12:00:00Z",
  "published_at": "2026-05-24T12:00:00Z",
  "links": { "self": "/api/v1/cms/pages/42" }
}
```

**Errors**:
- `422 invalid_status_transition` + `from`, `to`, `allowed: []`
- `422 invalid_status_value` + `allowed: ["draft","pending_review","published","archived"]`
- `422 slug_invalid` | `409 slug_conflict`
- `422 content_too_large` | `422 content_invalid_json`
- `403 forbidden` — agent tentando mudar status

---

### DELETE /api/v1/cms/pages/:id
**Auth**: Triple decorator | **Roles**: owner, director, manager

Soft delete — seta `active=False`. Conteúdo preservado.

**Response 200**: `{"success": true}`

---

### POST /api/v1/cms/pages/:id/duplicate
**Auth**: Triple decorator | **Roles**: owner, director, manager

Cria nova página com `name + " (Cópia)"`, slug com sufixo `-copy` (incrementado se conflito), `status=draft`.

**Response 201**:
```json
{
  "id": 99,
  "name": "Home (Cópia)",
  "slug": "home-copy",
  "status": "draft",
  "created_at": "2026-05-24T15:00:00Z"
}
```

---

## Templates

### POST /api/v1/cms/templates
**Auth**: Triple decorator | **Roles**: owner, director, manager

**Request**:
```json
{
  "name": "string (required)",
  "category": "string (required) — landing|property|about",
  "content": "string (optional) — JSON Puck"
}
```
**Response 201**: `{ "id": 1, "name": "...", "category": "...", "created_at": "..." }`

---

### GET /api/v1/cms/templates
**Auth**: Triple decorator | **Roles**: owner, director, manager (403 para agent)

**Response 200**: `{ "data": [{"id": 1, "name": "...", "category": "..."}], "pagination": {...} }`
> `content` não retornado na listagem.

---

### GET /api/v1/cms/templates/:id
**Auth**: Triple decorator | **Roles**: owner, director, manager

**Response 200**: `{ "id": 1, "name": "...", "category": "...", "content": "{...}" }`

---

### PUT /api/v1/cms/templates/:id
**Auth**: Triple decorator | **Roles**: owner, director, manager

**Request**: `{ "name": "...", "category": "...", "content": "..." }` (todos opcionais)
**Response 200**: `{ "id": 1, "updated_at": "..." }`

---

### DELETE /api/v1/cms/templates/:id
**Auth**: Triple decorator | **Roles**: owner, director, manager

Soft delete. **Response 200**: `{"success": true}`

---

## Media

### POST /api/v1/cms/media/upload
**Auth**: Triple decorator | **Roles**: owner, director, manager
**Content-Type**: `multipart/form-data`

**Form fields**: `file` (binary, required), `name` (string, optional)

**Response 201**:
```json
{
  "id": 5,
  "name": "banner-home.jpg",
  "mime_type": "image/jpeg",
  "media_type": "image",
  "file_size": 204800,
  "url": "/api/v1/cms/media/5/file",
  "created_at": "2026-05-24T10:00:00Z"
}
```

**Errors**:
- `415 unsupported_mime` + `received: "text/html"`
- `415 mime_mismatch` — extensão ≠ conteúdo real
- `413 file_too_large` + `max_size_bytes`, `received_size`

---

### GET /api/v1/cms/media
**Auth**: Triple decorator | **Roles**: owner, director, manager, agent

**Response 200**: `{ "data": [...], "pagination": {...} }`

---

### GET /api/v1/cms/media/:id
**Auth**: Triple decorator | **Roles**: owner, director, manager, agent

**Response 200**: `{ "id": 5, "name": "...", "mime_type": "...", "url": "...", ... }`

---

### GET /api/v1/cms/media/:id/file
**Auth**: Triple decorator | **Roles**: owner, director, manager, agent

Retorna o binário do arquivo com `Content-Type` correto.

---

### DELETE /api/v1/cms/media/:id
**Auth**: Triple decorator | **Roles**: owner, director, manager

Hard delete — remove `cms.media` + `ir.attachment`. ADR-015 exception.

**Response 200**: `{"success": true}`

---

## Settings

### GET /api/v1/cms/settings
**Auth**: Triple decorator | **Roles**: owner, director, manager

Auto-cria singleton se não existe. Campo `custom_js` omitido para director/manager.

**Response 200**:
```json
{
  "id": 1,
  "company_slug": "minha-agencia",
  "og_default_title": "Minha Imobiliária",
  "og_default_description": "...",
  "custom_css": "...",
  "custom_js": "...",
  "custom_js_last_modified_by": "João Silva",
  "custom_js_last_modified_at": "2026-05-24T10:00:00Z"
}
```

---

### PUT /api/v1/cms/settings
**Auth**: Triple decorator | **Roles**: owner, director, manager

**Request**: `{ "company_slug": "...", "og_default_title": "...", "custom_css": "...", "custom_js": "..." }`

- `custom_js`: somente owner pode enviar (403 para director/manager)
- `custom_css`: validado contra injection antes de persistir

**Response 200**: `{ "id": 1, "company_slug": "...", "updated_at": "..." }`

**Errors**:
- `422 company_slug_invalid`
- `409 company_slug_conflict`
- `422 css_injection_detected` + `field: "custom_css"`
- `422 css_too_large` — custom_css > 64KB
- `403 forbidden` + `detail: "custom_js can only be modified by owner"`

---

## Public Route

### GET /api/v1/public/cms/:company_slug/pages/:page_slug
**Auth**: `@require_jwt` apenas (sem session/company) — `# public endpoint`
**Roles**: qualquer JWT válido da plataforma

Retorna página publicada da imobiliária identificada por `company_slug`. Campos operacionais omitidos.

**Response 200**:
```json
{
  "slug": "home",
  "content": "{...puck json...}",
  "title": "Minha Imobiliária | Home",
  "meta_description": "...",
  "og_title": "...",
  "og_description": "...",
  "og_image_url": "https://...",
  "canonical_url": "https://minha-agencia.com/home",
  "robots_meta": "index,follow",
  "structured_data": "{\"@context\":\"https://schema.org\",...}"
}
```

> **Campos NUNCA retornados**: `status`, `created_at`, `updated_at`, `custom_js`, `custom_css`, `id`, `company_id`

**Errors**:
- `401 unauthorized` — JWT ausente ou inválido
- `404 not_found` — company_slug não existe, página não existe, página não está published, página soft-deleted

---

## Error Envelope Pattern (FR6.9)

Todos os erros usam o envelope FR6.9 (Constitution v1.7.0):

```json
{ "error": "snake_case_code", "detail": "human readable", ...campos_extras }
```

Implementado via helper `_cms_error(http_status, error_code, detail=None, **extra)` em `services/cms_error_helpers.py`.

---

## RBAC Matrix

| Endpoint | owner | director | manager | agent | outros |
|----------|-------|----------|---------|-------|--------|
| POST /pages | ✅ | ✅ | ✅ | ❌ | ❌ |
| GET /pages (todos status) | ✅ | ✅ | ✅ | ❌ | ❌ |
| GET /pages (somente published) | — | — | — | ✅ | ❌ |
| GET /pages/:id | ✅ | ✅ | ✅ | ✅ (published) | ❌ |
| PUT /pages/:id (metadados) | ✅ | ✅ | ✅ | ❌ | ❌ |
| PUT /pages/:id (status) | ✅ | ✅ | ✅ | ❌ | ❌ |
| DELETE /pages/:id | ✅ | ✅ | ✅ | ❌ | ❌ |
| POST /pages/:id/duplicate | ✅ | ✅ | ✅ | ❌ | ❌ |
| POST /templates | ✅ | ✅ | ✅ | ❌ | ❌ |
| GET /templates | ✅ | ✅ | ✅ | ❌ | ❌ |
| PUT /templates/:id | ✅ | ✅ | ✅ | ❌ | ❌ |
| DELETE /templates/:id | ✅ | ✅ | ✅ | ❌ | ❌ |
| POST /media/upload | ✅ | ✅ | ✅ | ❌ | ❌ |
| GET /media | ✅ | ✅ | ✅ | ✅ | ❌ |
| DELETE /media/:id | ✅ | ✅ | ✅ | ❌ | ❌ |
| GET /settings | ✅ | ✅ | ✅ | ❌ | ❌ |
| PUT /settings (sem custom_js) | ✅ | ✅ | ✅ | ❌ | ❌ |
| PUT /settings (custom_js) | ✅ | ❌ | ❌ | ❌ | ❌ |
| GET /public/... | JWT ✅ | JWT ✅ | JWT ✅ | JWT ✅ | ❌ |
