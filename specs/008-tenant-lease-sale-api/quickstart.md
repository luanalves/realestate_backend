# Quickstart: Tenant, Lease & Sale API

**Feature**: 008-tenant-lease-sale-api
**Branch**: `008-tenant-lease-sale-api`
**Reference Implementation**: Feature 007 — `owner_api.py`

## Prerequisites

```bash
cd 18.0
docker compose up -d
docker compose exec db psql -U odoo -d realestate -c "SELECT 1"  # verify DB
docker compose exec redis redis-cli PING                          # verify Redis
```

## Implementation Order

Follow this sequence — each step builds on the previous:

### Step 1: Model Modifications (models/)

**1a. Extend `tenant.py`** — Add soft-delete and deactivation fields:

```python
# New fields to add
active = fields.Boolean(default=True)
deactivation_date = fields.Datetime(string="Deactivation Date")
deactivation_reason = fields.Text(string="Deactivation Reason")
```

**1b. Extend `lease.py`** — Add status, termination, and renewal fields:

```python
# New fields
active = fields.Boolean(default=True)
status = fields.Selection([
    ('draft', 'Draft'),
    ('active', 'Active'),
    ('terminated', 'Terminated'),
    ('expired', 'Expired'),
], string='Status', default='draft', required=True)
termination_date = fields.Date(string="Termination Date")
termination_reason = fields.Text(string="Termination Reason")
termination_penalty = fields.Float(string="Termination Penalty")
renewal_history_ids = fields.One2many(
    'real.estate.lease.renewal.history', 'lease_id',
    string="Renewal History"
)
```

Add constraint for concurrent leases:

```python
@api.constrains('property_id', 'start_date', 'end_date', 'status')
def _check_concurrent_lease(self):
    for record in self:
        if record.status in ('draft', 'active'):
            overlapping = self.search([
                ('id', '!=', record.id),
                ('property_id', '=', record.property_id.id),
                ('status', 'in', ['draft', 'active']),
                ('start_date', '<=', record.end_date),
                ('end_date', '>=', record.start_date),
            ])
            if overlapping:
                raise ValidationError("Property already has an active lease in this period.")
```

**1c. Extend `sale.py`** — Add status and cancellation fields:

```python
# New fields
active = fields.Boolean(default=True)
status = fields.Selection([
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
], string='Status', default='completed', required=True)
cancellation_date = fields.Date(string="Cancellation Date")
cancellation_reason = fields.Text(string="Cancellation Reason")
```

**1d. Create `lease_renewal_history.py`** — New audit model:

```python
from odoo import models, fields

class LeaseRenewalHistory(models.Model):
    _name = 'real.estate.lease.renewal.history'
    _description = 'Lease Renewal History'
    _order = 'renewal_date desc'

    lease_id = fields.Many2one('real.estate.lease', required=True, ondelete='cascade')
    previous_end_date = fields.Date(required=True)
    previous_rent_amount = fields.Float(required=True)
    new_end_date = fields.Date(required=True)
    new_rent_amount = fields.Float(required=True)
    renewed_by_id = fields.Many2one('res.users', required=True)
    reason = fields.Text()
    renewal_date = fields.Datetime(default=fields.Datetime.now, required=True)
```

**1e. Update `models/__init__.py`**:

```python
from . import lease_renewal_history  # add this import
```

### Step 2: Security Rules (security/)

**2a. `ir.model.access.csv`** — Add row for the new model:

```csv
access_lease_renewal_history,real.estate.lease.renewal.history,model_real_estate_lease_renewal_history,base.group_user,1,1,1,0
```

**2b. `record_rules.xml`** — Add company isolation rule for the new model (lease renewal history is accessed via the parent lease's company).

### Step 3: Validation Schemas (controllers/utils/schema.py)

Add 6 schemas following the existing `SchemaValidator` pattern:

```python
TENANT_CREATE_SCHEMA = {
    'required': ['name'],
    'optional': ['phone', 'email', 'occupation', 'birthdate'],
    'types': {
        'name': str, 'phone': str, 'email': str,
        'occupation': str, 'birthdate': str,
    },
    'constraints': {
        'name': lambda v: len(v.strip()) > 0,
        'email': lambda v: validate_email_format(v) if v else True,
    }
}

LEASE_CREATE_SCHEMA = {
    'required': ['property_id', 'tenant_id', 'start_date', 'end_date', 'rent_amount'],
    'optional': [],
    'types': {
        'property_id': int, 'tenant_id': int,
        'start_date': str, 'end_date': str, 'rent_amount': (int, float),
    },
    'constraints': {
        'rent_amount': lambda v: v > 0,
    }
}

SALE_CREATE_SCHEMA = {
    'required': ['property_id', 'company_id', 'buyer_name', 'sale_date', 'sale_price'],
    'optional': ['buyer_phone', 'buyer_email', 'agent_id', 'lead_id'],
    'types': {
        'property_id': int, 'company_id': int,
        'buyer_name': str, 'sale_date': str, 'sale_price': (int, float),
        'buyer_phone': str, 'buyer_email': str, 'agent_id': int, 'lead_id': int,
    },
    'constraints': {
        'sale_price': lambda v: v > 0,
        'buyer_email': lambda v: validate_email_format(v) if v else True,
    }
}
```

### Step 4: Controllers (controllers/)

Each controller follows this pattern from `owner_api.py`:

```python
import json
import logging
from odoo import http
from odoo.http import request
from .utils.auth import require_jwt
from .utils.schema import SchemaValidator, TENANT_CREATE_SCHEMA
from .utils.responses import success_response, error_response, paginated_response, build_hateoas_links
from odoo.addons.thedevkitchen_apigateway.middleware import require_session, require_company

_logger = logging.getLogger(__name__)

class TenantAPI(http.Controller):

    @http.route('/api/v1/tenants', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_tenants(self, **kwargs):
        ...
```

**Create 3 files**: `tenant_api.py`, `lease_api.py`, `sale_api.py`

**Update `controllers/__init__.py`**:

```python
from . import tenant_api, lease_api, sale_api  # add these imports
```

### Step 5: Tests

**Unit tests** (`tests/utils/`):
- Validation schemas
- Date constraint logic
- Status transition logic

**Integration tests** (`integration_tests/`):
- `test_us8_s1_tenant_crud.sh` — Full CRUD + archive
- `test_us8_s2_lease_lifecycle.sh` — Create, renew, terminate
- `test_us8_s3_sale_management.sh` — Create, cancel, property status
- `test_us8_s4_tenant_lease_history.sh` — Sub-resource endpoint
- `test_us8_s5_soft_delete.sh` — Archive/unarchive across entities

**E2E tests** (`cypress/e2e/`):
- `tenant-management.cy.js`
- `lease-management.cy.js`
- `sale-management.cy.js`

### Step 6: Postman Collection

Create `docs/postman/feature008_tenant_lease_sale_v1.0_postman_collection.json` following ADR-016:
- OAuth token endpoint with auto-save script
- Session management
- All 18 endpoints organized by entity folder
- Required variables: `base_url`, `access_token`, `session_id`

## Key Patterns to Follow

### Triple Auth Decorator (Constitution Principle I)

```python
@http.route('/api/v1/...', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company
def endpoint(self, **kwargs):
```

### Soft Delete (ADR-015)

```python
# Archive
record.write({'active': False, 'deactivation_date': fields.Datetime.now(), 'deactivation_reason': reason})

# Query with inactive
env['model'].with_context(active_test=False).search(domain)
```

### HATEOAS Links (ADR-007)

```python
links = build_hateoas_links(
    self_url=f'/api/v1/tenants/{tenant.id}',
    collection_url='/api/v1/tenants',
    related={'leases': f'/api/v1/tenants/{tenant.id}/leases'}
)
```

### Event Bus (sale.created)

```python
# Already in sale.py create() override — verify it emits on new sales
event_bus = self.env['quicksol.event.bus']
event_bus.emit('sale.created', {'sale_id': sale.id})
```

### Agent RBAC (Transitive)

```python
# Agents access via property assignment chain
assigned_props = env['real.estate.assignment'].search([
    ('agent_id', '=', agent.id),
    ('company_ids', 'in', company_ids)
]).mapped('property_id').ids

# Filter leases/tenants by assigned properties
leases = env['real.estate.lease'].search([
    ('property_id', 'in', assigned_props),
    ('company_ids', 'in', company_ids)
])
```

## Verification Checklist

After implementation, verify:

- [ ] All 18 endpoints respond with correct status codes
- [ ] Triple auth rejects unauthenticated requests (401)
- [ ] Company isolation prevents cross-tenant access (403)
- [ ] Soft delete hides records from default queries
- [ ] Lease renewal creates history entry
- [ ] Lease termination records penalty (optional)
- [ ] Sale creation marks property as "sold"
- [ ] Sale cancellation reverts property status
- [ ] Concurrent lease constraint rejects overlapping leases
- [ ] HATEOAS links present in all responses
- [ ] Pagination works with limit/offset
- [ ] Agent RBAC limits access to assigned properties
- [ ] Postman collection passes all requests
- [ ] Test coverage ≥80%
