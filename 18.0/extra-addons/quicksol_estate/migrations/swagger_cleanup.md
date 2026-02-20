# Swagger/OpenAPI Cleanup - Tenant Endpoints

**Date**: 2026-02-20
**Context**: Feature 010 Profile Unification (ADR-024)

## Issue

After removing the Tenant API (`tenant_api.py`) and database tables, the Swagger UI at `/api/docs` was still displaying 6 tenant endpoints:

- `GET /api/v1/tenants` - List Tenants
- `POST /api/v1/tenants` - Create Tenant
- `GET /api/v1/tenants/{tenant_id}` - Get Tenant
- `PUT /api/v1/tenants/{tenant_id}` - Update Tenant
- `DELETE /api/v1/tenants/{tenant_id}` - Archive Tenant
- `GET /api/v1/tenants/{tenant_id}/leases` - Get Tenant Lease History

## Root Cause

The Swagger UI is generated dynamically by `thedevkitchen_apigateway/controllers/swagger_controller.py`, which queries the `thedevkitchen_api_endpoint` table. Even though the XML data records were removed from `data/api_endpoints.xml` (commit 1b7cc7b), the **database records persisted** from a previous module load.

## Solution

Executed direct database cleanup to remove orphaned endpoint records:

```sql
DELETE FROM thedevkitchen_api_endpoint 
WHERE path LIKE '%tenant%' AND id BETWEEN 638 AND 643;
-- Result: DELETE 6
```

## Verification

```bash
# Check OpenAPI spec has no tenant endpoints
curl -s http://localhost:8069/api/v1/openapi.json | jq '.paths | keys | map(select(. | contains("tenant")))'
# Result: []
```

## Prevention

When removing API endpoints:
1. ✅ Remove controller file (`controllers/tenant_api.py`)
2. ✅ Remove data records (`data/api_endpoints.xml`)
3. ✅ Restart Odoo container (module reload)
4. ✅ **Verify database** (`SELECT * FROM thedevkitchen_api_endpoint WHERE path LIKE '%removed%'`)
5. ✅ Clean orphaned records if needed

**Note**: Odoo data files only control *initial installation* and *module upgrades*. If records were created in a previous version, they persist unless explicitly deleted.

## Related Commits

- `d20d7c3` - Remove tenant_api.py controller
- `1b7cc7b` - Remove tenant endpoint data records from api_endpoints.xml
- `60bd60e` - Remove tenant.py model
- `09f9c82` - Database table cleanup (DROP real_estate_tenant)
