# Research: Tenant, Lease & Sale API Endpoints

**Feature**: 008-tenant-lease-sale-api
**Date**: 2026-02-14

## Research Tasks & Findings

### R1: Existing Model State — What needs to change?

**Decision**: Modify 3 existing models (tenant, lease, sale) + create 1 new model (lease_renewal_history)

**Rationale**: Models already exist with core fields but lack `active` (soft-delete per ADR-015), `status` (lifecycle tracking per spec), and termination/cancellation audit fields. Adding fields to existing models is non-breaking and follows Odoo's inheritance pattern.

**Current State → Target State**:

| Model | Missing Fields | Action |
|-------|---------------|--------|
| `real.estate.tenant` | `active`, `deactivation_date`, `deactivation_reason` | ADD fields |
| `real.estate.lease` | `active`, `status` (selection), `termination_date`, `termination_reason`, `termination_penalty` | ADD fields |
| `real.estate.sale` | `active`, `status` (selection), `cancellation_date`, `cancellation_reason` | ADD fields |
| `real.estate.lease.renewal.history` | (entire model) | CREATE new model |

**Alternatives considered**:
- Creating new models inheriting original ones (`_inherit`) → Rejected: unnecessary complexity, existing models are in same module
- Using Odoo's `mail.activity.mixin` for audit → Rejected: overkill for simple renewal tracking

### R2: Controller Security Pattern — Triple Decorator

**Decision**: All endpoints use `@require_jwt` + `@require_session` + `@require_company` (triple decorator pattern)

**Rationale**: Established pattern across all existing controllers (property, agent, lead, owner, company). Constitution Principle I mandates this. `@require_company` provides automatic company_ids validation.

**Import pattern** (from existing controllers):
```python
from .utils.auth import require_jwt
from odoo.addons.thedevkitchen_apigateway.middleware import require_session, require_company
```

**Alternatives considered**:
- `@require_jwt` + `@require_session` only (without `@require_company`) → Rejected: Constitution explicitly requires all three for multi-tenant endpoints
- Custom middleware → Rejected: existing decorators already solve this

### R3: RBAC for Agents — Transitive Scope via Property Assignment

**Decision**: Agents access tenants/leases via property assignment chain (Agent → assigned Properties → Leases on those properties → Tenants on those leases). Sales filtered by `agent_id` match.

**Rationale**: Clarification session confirmed this approach. Property assignment is the existing RBAC hinge for agents (see `agent_api.py` and `assignment` model).

**Implementation pattern**:
```python
# For agents: get properties they're assigned to, then filter related records
assigned_property_ids = env['real.estate.assignment'].search([
    ('agent_id', '=', agent.id),
    ('company_ids', 'in', company_ids)
]).mapped('property_id').ids

# Tenants: those with leases on assigned properties
# Leases: those on assigned properties
# Sales: where agent_id matches current agent
```

**Alternatives considered**:
- Direct `created_by` tracking → Rejected: too restrictive, doesn't account for team reassignment
- Full company access for agents → Rejected: violates RBAC principle

### R4: Soft Delete Pattern — ADR-015 Compliance

**Decision**: Use Odoo's built-in `active = fields.Boolean(default=True)` with optional `deactivation_date` and `deactivation_reason` fields.

**Rationale**: ADR-015 mandates this exact pattern. Odoo automatically filters `active=True` in default queries. Use `with_context(active_test=False)` to include inactive records.

**API query parameter**: `?is_active=true|false` (consistent with existing endpoints)

**Key rules from ADR-015**:
- Never use `ondelete='set null'` on historical FKs — preserve references
- Use `action_archive()` / `action_unarchive()` for custom logic
- Track `deactivation_date` (Datetime) and `deactivation_reason` (Text)
- Default queries auto-exclude inactive records

### R5: Lease Renewal — In-Place Mutation with Audit History

**Decision**: Extend the existing lease's `end_date` and `rent_amount` in-place. Create a `real.estate.lease.renewal.history` record capturing: previous end_date, previous rent_amount, renewed_by (user), reason, timestamp.

**Rationale**: Clarification session chose Option B (mutate in-place with history). This is simpler than creating new lease records and avoids complex chain-of-leases queries.

**New model**: `real.estate.lease.renewal.history`
| Field | Type | Purpose |
|-------|------|---------|
| `lease_id` | Many2one → `real.estate.lease` | Parent lease |
| `previous_end_date` | Date | End date before renewal |
| `previous_rent_amount` | Float | Rent before renewal |
| `new_end_date` | Date | End date after renewal |
| `new_rent_amount` | Float | Rent after renewal |
| `renewed_by_id` | Many2one → `res.users` | Who renewed |
| `reason` | Text | Why renewed |
| `renewal_date` | Datetime | When renewed (auto) |

### R6: Sale → Property Status Change

**Decision**: When a sale is created, automatically set the property's status to "sold". When a sale is cancelled, revert the property status.

**Rationale**: Clarification session confirmed this behavior. Prevents new leases on sold properties. Consistent with real estate domain expectations.

**Implementation**: Override `create()` on sale model to call `property_id.write({'state': 'sold'})`. On cancel, revert to previous state.

**Edge case**: Property with active leases can still be sold (leases run to term), but no new leases created on sold property.

### R7: Concurrent Lease Constraint

**Decision**: One active lease per property at a time. Reject creation if overlapping active lease exists.

**Rationale**: Clarification session confirmed Option A. Standard real estate model — one tenant per property at a time.

**Implementation**: Add `@api.constrains` on lease model that checks for overlapping active leases on same property. Also validate in controller before ORM call for better error messages.

### R8: Response Format & HATEOAS Links

**Decision**: Use existing `success_response()`, `error_response()`, `paginated_response()` from `utils/responses.py`. Add HATEOAS links using `build_hateoas_links()`.

**Rationale**: Established pattern across all existing controllers. ADR-007 mandates HATEOAS. Reusing existing utils ensures consistency.

**HATEOAS relations for each entity**:
- Tenant: self, collection, leases (sub-resource)
- Lease: self, collection, property (parent), tenant (related), renew (action), terminate (action)
- Sale: self, collection, property (parent), agent (related), cancel (action)

### R9: Schema Validation

**Decision**: Add `TENANT_CREATE_SCHEMA`, `TENANT_UPDATE_SCHEMA`, `LEASE_CREATE_SCHEMA`, `LEASE_UPDATE_SCHEMA`, `SALE_CREATE_SCHEMA`, `SALE_UPDATE_SCHEMA` to `controllers/utils/schema.py`.

**Rationale**: Existing `SchemaValidator` class handles validation with `required`, `optional`, `types`, and `constraints` dictionaries. Follow exact same pattern as `AGENT_CREATE_SCHEMA`.

### R10: Postman Collection — ADR-016 Compliance

**Decision**: Create `docs/postman/quicksol_api_v1.9_postman_collection.json` following ADR-016 standards.

**Rationale**: Constitution Principle III and ADR-016 mandate Postman collections for all new features. Feature 007 collection serves as template.

**Required sections**: OAuth flow, session management, Tenant CRUD, Lease lifecycle, Sale management, test scripts auto-saving tokens.
