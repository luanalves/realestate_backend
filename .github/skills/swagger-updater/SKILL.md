---
name: swagger-updater
description: 'Create, update, or remove Swagger/OpenAPI documentation for this project. TRIGGER KEYWORDS: swagger, openapi, api docs, endpoint documentation, api_endpoint, thedevkitchen_api_endpoint, /api/docs, openapi.json, documenting endpoint, add endpoint swagger, remove endpoint swagger, update swagger, atualizar swagger, documentar endpoint, adicionar endpoint, remover endpoint swagger. COVERS: (1) How Swagger is generated dynamically from the database table `thedevkitchen_api_endpoint`, (2) How to add/update/remove endpoints via XML data files, (3) Upgrading the Odoo module to sync DB, (4) Manual DB cleanup for orphan records, (5) OpenAPI 3.0 field standards (ADR-005). RULE: Swagger is updated via database — never by editing static files.'
---

# Swagger Updater

## Core Rule — DB is the Source of Truth

> **Swagger is NEVER updated by editing static files.**
> The Swagger UI (`/api/docs`) and spec (`/api/v1/openapi.json`) are generated dynamically by `swagger_controller.py`, which reads the `thedevkitchen_api_endpoint` table from the database.

The correct workflow is:

```
XML data file → module upgrade → DB table → Swagger UI
```

---

## Architecture

| Component | Location |
|-----------|----------|
| Dynamic generator | `thedevkitchen_apigateway/controllers/swagger_controller.py` |
| DB model | `thedevkitchen.api.endpoint` (table: `thedevkitchen_api_endpoint`) |
| Data files (per module) | `<module>/data/api_endpoints.xml` |
| Swagger UI | `http://localhost:8069/api/docs` |
| OpenAPI JSON spec | `http://localhost:8069/api/v1/openapi.json` |

---

## Model Fields (thedevkitchen.api.endpoint)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | Char | ✅ | Human-readable name (e.g., `List Agents`) |
| `path` | Char | ✅ | API path starting with `/` (e.g., `/api/v1/agents`) |
| `method` | Selection | ✅ | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `module_name` | Char | ✅ | Odoo module that owns the endpoint |
| `summary` | Char | ✅ | Short one-line summary for Swagger UI |
| `description` | Text | ✅ | Full Markdown description with examples |
| `tags` | Char | ✅ | Comma-separated tags for grouping (e.g., `Agents`) |
| `protected` | Boolean | ✅ | `True` = requires JWT auth; `False` = public |
| `active` | Boolean | ✅ | `True` = visible in Swagger UI |
| `request_schema` | Text | — | JSON Schema for request body (POST/PUT/PATCH) |
| `response_schema` | Text | — | JSON Schema for response documentation |

---

## Procedure 1 — Add a New Endpoint

### Step 1 — Add record to the XML data file

Create or update `<module>/data/api_endpoints.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="0">

        <record id="api_endpoint_agents_list" model="thedevkitchen.api.endpoint">
            <field name="name">List Agents</field>
            <field name="path">/api/v1/agents</field>
            <field name="method">GET</field>
            <field name="module_name">thedevkitchen_agents</field>
            <field name="protected" eval="True"/>
            <field name="tags">Agents</field>
            <field name="summary">List all agents</field>
            <field name="description">Returns paginated list of agents for the authenticated company.

**Required Headers:**
- `Authorization: Bearer {access_token}`
- `X-Session-Id: {session_id}`

**Query Parameters:**
- `limit` (int, optional): Max results. Default: 20
- `offset` (int, optional): Pagination offset. Default: 0

**Response Example (200 OK):**
```json
{
  "data": [
    {"id": 1, "name": "João Silva", "creci": "12345-F"}
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

**Error Responses:**
- **401 Unauthorized**: Missing or invalid JWT token
- **403 Forbidden**: Insufficient permissions
</field>
            <field name="active" eval="True"/>
        </record>

    </data>
</odoo>
```

### Step 2 — Declare the data file in `__manifest__.py`

```python
'data': [
    'data/api_endpoints.xml',
],
```

### Step 3 — Upgrade the module to sync DB

```bash
cd 18.0
docker compose exec odoo odoo -u thedevkitchen_agents --stop-after-init
```

### Step 4 — Verify in Swagger UI

Open `http://localhost:8069/api/docs` and confirm the new endpoint appears under the correct tag.

---

## Procedure 2 — Update an Existing Endpoint

1. Edit the `<record>` block in the module's `api_endpoints.xml` (same `id` attribute).
2. Upgrade the module (`noupdate="0"` ensures Odoo overwrites existing records).
3. Verify at `/api/docs`.

> **Note**: `noupdate="0"` is mandatory so upgrades propagate changes to the DB.

---

## Procedure 3 — Remove an Endpoint

Removing an XML record does **NOT** automatically delete it from the DB.

### Step 1 — Remove from XML

Delete or comment out the `<record>` block in `api_endpoints.xml`.

### Step 2 — Delete the orphan record from DB (REQUIRED)

```bash
docker compose exec db psql -U odoo -d realestate -c "
DELETE FROM thedevkitchen_api_endpoint
WHERE path = '/api/v1/old-endpoint' AND method = 'GET';
"
```

### Step 3 — Upgrade the module

```bash
docker compose exec odoo odoo -u <module_name> --stop-after-init
```

### Step 4 — Verify the endpoint is gone from `/api/docs`

---

## Procedure 4 — Check for Orphan Records

Run this SQL to inspect registered endpoints and detect orphans:

```sql
-- All active endpoints
SELECT id, name, path, method, module_name, active
FROM thedevkitchen_api_endpoint
ORDER BY module_name, path;

-- Endpoints for a specific module
SELECT id, name, path, method
FROM thedevkitchen_api_endpoint
WHERE module_name = 'thedevkitchen_agents';

-- Inactive / possibly orphaned
SELECT id, name, path, method
FROM thedevkitchen_api_endpoint
WHERE active = False;
```

```bash
# Run via Docker
docker compose exec db psql -U odoo -d realestate -c \
  "SELECT id, name, path, method, module_name FROM thedevkitchen_api_endpoint ORDER BY path;"
```

---

## ADR-005 Standards (OpenAPI 3.0)

All endpoints MUST comply with ADR-005:

| Requirement | Rule |
|-------------|------|
| Naming | `{Model}Create`, `{Model}Update`, `{Model}Response`, `{Model}ListResponse` |
| POST/PUT/PATCH | Must include request body example in `description` |
| All responses | Must document `200`, `400`, `401`, `403`, `404` where applicable |
| All fields | Must include examples in schema documentation |
| Error schema | Use `{"error": "...", "message": "...", "code": 400}` pattern |
| Public endpoints | Set `protected = False`; also add `# public endpoint` in controller |
| Auth endpoints | Set `protected = True`; use triple decorators in controller |

---

## Security Alignment (ADR-011)

Swagger `protected` field must match the controller decorator:

| Controller decorators | `protected` value |
|-----------------------|-------------------|
| `@require_jwt` + `@require_session` + `@require_company` | `True` |
| `# public endpoint` (no auth decorators) | `False` |

---

## Quick Commands Reference

```bash
# Navigate to working directory
cd /opt/homebrew/var/www/realestate/realestate_backend/18.0

# Upgrade a specific module
docker compose exec odoo odoo -u <module_name> --stop-after-init

# Open Swagger UI
open http://localhost:8069/api/docs

# Inspect DB table
docker compose exec db psql -U odoo -d realestate -c \
  "SELECT path, method, active FROM thedevkitchen_api_endpoint ORDER BY path;"

# Delete specific endpoint record
docker compose exec db psql -U odoo -d realestate -c \
  "DELETE FROM thedevkitchen_api_endpoint WHERE path = '/api/v1/...' AND method = 'GET';"
```
