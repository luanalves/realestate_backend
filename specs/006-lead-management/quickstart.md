# Quickstart: Real Estate Lead Management

**Branch**: `006-lead-management`  
**Last Updated**: 2026-01-29

## Overview

This guide helps developers quickly understand and work with the lead management system. For detailed architecture, see [data-model.md](data-model.md) and [contracts/openapi.yaml](contracts/openapi.yaml).

## What is a Lead?

A **lead** represents a potential real estate client tracked through the sales pipeline. Think of it as a "sales opportunity" that moves from initial contact → qualified → closed (won/lost).

**Key Concepts**:
- Each lead is owned by one **agent** (salesperson)
- Leads belong to one or more **companies** (multi-tenancy)
- Agents see only their own leads; managers see all company leads
- Leads track contact info, property preferences, budget, and sales stage
- Conversion: Qualified leads can be converted to property sales

## Quick Setup (Development)

### 1. Start the Environment

```bash
cd /opt/homebrew/var/www/realestate/realestate_backend/18.0
docker compose up -d
```

### 2. Install Module

```bash
# Access Odoo container
docker compose exec odoo bash

# Update module list
odoo-bin -c /etc/odoo/odoo.conf -d realestate -u quicksol_estate --stop-after-init

# Or via UI: Apps → Update Apps List → Search "Real Estate" → Upgrade
```

### 3. Verify Installation

```bash
# Check model exists
docker compose exec db psql -U odoo -d realestate -c "SELECT COUNT(*) FROM real_estate_lead;"

# Check API endpoint
curl -X GET http://localhost:8069/api/v1/leads \
  -H "Authorization: Bearer <JWT>" \
  -H "Cookie: session_id=<SESSION>" \
  -H "X-Company-ID: 1"
```

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js SSR Frontend                    │
│                  (Agency Interface - Headless)              │
└────────────────────────────┬────────────────────────────────┘
                             │ REST API (JSON)
                             │ Auth: JWT + Session + Company
┌────────────────────────────▼────────────────────────────────┐
│                        Odoo Backend                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Controllers: lead_api.py                            │   │
│  │  ├─ @require_jwt (OAuth 2.0)                        │   │
│  │  ├─ @require_session (User context)                 │   │
│  │  └─ @require_company (Multi-tenancy)                │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Models: real_estate_lead.py                         │   │
│  │  ├─ mail.thread (Activity tracking)                 │   │
│  │  ├─ mail.activity.mixin (Scheduled tasks)           │   │
│  │  └─ Business logic (validation, conversion)         │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Security: real_estate_lead_security.xml             │   │
│  │  ├─ Agent Rule: Own leads only                      │   │
│  │  └─ Manager Rule: All company leads                 │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  PostgreSQL: realestate database                            │
│  ├─ real_estate_lead table                                  │
│  ├─ real_estate_lead_company_rel (Many2many)                │
│  └─ Indexes: state, agent_id, create_date                   │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow Examples

### Example 1: Agent Creates Lead

```
1. Agent fills form in Next.js frontend
   ↓
2. SSR backend sends POST /api/v1/leads
   Headers: Authorization, session_id, X-Company-ID
   Body: { name, phone, email, budget_min, budget_max, ... }
   ↓
3. Odoo controller: lead_api.py
   - @require_jwt: Validates OAuth token
   - @require_session: Validates session & user context
   - @require_company: Validates company access
   ↓
4. Model: real_estate_lead.py
   - Auto-assigns agent_id (current user's agent)
   - Auto-assigns company_ids (user's companies)
   - Validates duplicate (phone/email for this agent)
   - Validates budget_min <= budget_max
   ↓
5. PostgreSQL: Insert into real_estate_lead
   ↓
6. Response: 201 Created with lead data
   ↓
7. Frontend shows success + redirects to lead detail
```

### Example 2: Manager Views Dashboard

```
1. Manager opens dashboard in Next.js
   ↓
2. SSR backend sends GET /api/v1/leads?page=1&limit=50
   ↓
3. Odoo applies record rule: Manager Rule
   domain_force: [('company_ids', 'in', user.estate_company_ids.ids)]
   → Returns ALL leads from user's companies (all agents)
   ↓
4. PostgreSQL query with pagination:
   SELECT * FROM real_estate_lead
   WHERE company_ids && user_companies
   ORDER BY create_date DESC
   LIMIT 50 OFFSET 0
   ↓
5. Response: 200 OK with paginated leads
   ↓
6. Frontend renders lead list + pagination controls
```

### Example 3: Lead Conversion

```
1. Agent clicks "Convert to Sale" for lead #123
   Selects property #456
   ↓
2. SSR backend sends POST /api/v1/leads/123/convert
   Body: { property_id: 456 }
   ↓
3. Odoo controller starts transaction:
   - Fetch lead #123 (validates access via record rule)
   - Fetch property #456 (validates access)
   - Create sale record:
     {
       property_id: 456,
       partner_id: lead.partner_id,
       phone: lead.phone,
       email: lead.email,
       agent_id: lead.agent_id,
       lead_id: 123
     }
   - Update lead:
     {
       state: 'won',
       converted_property_id: 456,
       converted_sale_id: <new_sale_id>
     }
   - Log activity: "Lead converted to sale"
   ↓
4. If any step fails: ROLLBACK (no partial commit)
   If all succeed: COMMIT
   ↓
5. Response: 200 OK { lead_id: 123, sale_id: <new_id> }
   ↓
6. Frontend shows success + redirects to sale detail
```

## File Structure

```
18.0/extra-addons/quicksol_estate/
├── models/
│   └── real_estate_lead.py          # NEW: Lead model
│       ├─ _name = 'real.estate.lead'
│       ├─ _inherit = ['mail.thread', 'mail.activity.mixin']
│       ├─ Fields: name, phone, email, budget, preferences, state
│       ├─ Validations: duplicate check, budget range, company
│       └─ Methods: action_reopen(), unlink() override
│
├── controllers/
│   └── lead_api.py                   # NEW: REST API
│       ├─ GET /api/v1/leads (list with pagination)
│       ├─ POST /api/v1/leads (create)
│       ├─ GET /api/v1/leads/{id} (detail)
│       ├─ PUT /api/v1/leads/{id} (update)
│       ├─ DELETE /api/v1/leads/{id} (archive)
│       ├─ POST /api/v1/leads/{id}/convert (convert to sale)
│       ├─ POST /api/v1/leads/{id}/reopen (reopen lost)
│       └─ GET /api/v1/leads/statistics (dashboard stats)
│
├── views/
│   └── real_estate_lead_views.xml    # NEW: UI views
│       ├─ List view (FR-034)
│       ├─ Form view with tabs (FR-035)
│       ├─ Kanban view by state (FR-036)
│       ├─ Calendar view (FR-037)
│       └─ Dashboard pivot/graph (FR-038)
│
├── security/
│   ├── ir.model.access.csv           # UPDATE: Add lead access
│   │   └─ 4 rows: agent, manager, director, owner
│   │
│   └── real_estate_lead_security.xml # NEW: Record rules
│       ├─ Agent Rule: own leads only
│       ├─ Manager Rule: all company leads
│       └─ Owner Rule: all leads (global)
│
└── tests/
    ├── unit/
    │   └── test_lead_validations_unit.py  # NEW: Mocked tests
    │       ├─ test_duplicate_prevention
    │       ├─ test_budget_validation
    │       ├─ test_state_transitions
    │       └─ test_soft_delete
    │
    └── api/
        └── test_lead_api.py               # NEW: E2E API tests
            ├─ test_create_lead_success
            ├─ test_create_lead_duplicate_fails
            ├─ test_list_leads_agent_isolation
            ├─ test_list_leads_manager_access
            ├─ test_convert_lead_success
            ├─ test_convert_lead_rollback_on_error
            └─ test_multitenancy_isolation
```

## Security Model Quick Reference

### Authentication (Triple Decorator Pattern)

**ALL** API endpoints require three decorators:

```python
@http.route('/api/v1/leads', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt          # OAuth 2.0 token validation
@require_session      # User session + context
@require_company      # Multi-tenancy company validation
def list_leads(self, **kwargs):
    # Auto-filtered by record rules
    env = request.env
    leads = env['real.estate.lead'].search([])  # Already filtered!
    return success_response({'leads': leads})
```

### Record Rules (Automatic Filtering)

| User Profile | Can See | Can Edit | Rule Domain |
|--------------|---------|----------|-------------|
| **Agent** | Own leads only | Own leads only | `[('agent_id.user_id', '=', user.id), ('company_ids', 'in', user.estate_company_ids.ids)]` |
| **Manager** | All company leads | All company leads | `[('company_ids', 'in', user.estate_company_ids.ids)]` |
| **Director** | All company leads | All company leads | Same as Manager |
| **Owner** | All company leads | All company leads | Same as Manager |

**No code needed in controllers** - record rules automatically filter results!

### Multi-Tenancy

All leads are scoped to companies via `company_ids` field:

```python
# User A (Company 1) creates lead
lead = env['real.estate.lead'].create({
    'name': 'João Silva',
    # company_ids auto-assigned to [Company 1]
})

# User B (Company 2) tries to read
leads = env['real.estate.lead'].search([])
# → Result: [] (record rule filters out Company 1 leads)
```

**Zero cross-company leakage** enforced at database level.

## Common Development Tasks

### Add New Field to Lead Model

1. Edit `models/real_estate_lead.py`:
   ```python
   class RealEstateLead(models.Model):
       _inherit = 'real.estate.lead'
       
       my_new_field = fields.Char(string="My Field", tracking=True)
   ```

2. Update database:
   ```bash
   docker compose exec odoo odoo-bin -c /etc/odoo/odoo.conf -d realestate -u quicksol_estate --stop-after-init
   ```

3. Add to views (`views/real_estate_lead_views.xml`):
   ```xml
   <field name="my_new_field"/>
   ```

4. Add to API response (`controllers/lead_api.py`):
   ```python
   fields=['id', 'name', ..., 'my_new_field']
   ```

### Add New Endpoint

1. Add route to `controllers/lead_api.py`:
   ```python
   @http.route('/api/v1/leads/<int:lead_id>/custom-action', 
               type='json', auth='none', methods=['POST'], csrf=False, cors='*')
   @require_jwt
   @require_session
   @require_company
   def custom_action(self, lead_id, **kwargs):
       lead = request.env['real.estate.lead'].browse(lead_id)
       # Record rule auto-checks access
       if not lead.exists():
           return error_response('Not found', 404)
       
       # Your logic here
       lead.do_something()
       
       return success_response({'message': 'Success'})
   ```

2. Add to OpenAPI schema (`contracts/openapi.yaml`):
   ```yaml
   /leads/{lead_id}/custom-action:
     post:
       summary: Custom action
       # ... full spec
   ```

3. Write tests:
   - Unit test: `tests/unit/test_custom_action_unit.py`
   - E2E test: `tests/api/test_custom_action_api.py`

### Run Tests

```bash
# Unit tests (fast, mocked)
docker compose exec odoo python3 /mnt/extra-addons/quicksol_estate/tests/unit/test_lead_validations_unit.py

# E2E API tests (real DB)
cd integration_tests
./test_us_lead_agent_crud.sh

# Cypress E2E (UI)
cd cypress
npx cypress run --spec "e2e/lead-agent-crud.cy.js"
```

## Debugging Tips

### Check Record Rules

```python
# In Odoo shell (docker compose exec odoo odoo-bin shell -d realestate)
env = api.Environment(cr, uid, {})
lead = env['real.estate.lead'].browse(123)

# Check if visible
lead.exists()  # False = filtered out by record rule

# Bypass rules (debug only!)
lead_sudo = lead.sudo()
lead_sudo.exists()  # True = record exists in DB
```

### Check Duplicate Detection

```python
# Test duplicate logic
agent = env['real.estate.agent'].browse(1)
lead1 = env['real.estate.lead'].create({
    'name': 'Test',
    'agent_id': agent.id,
    'phone': '+55 11 12345-6789',
})

# Should fail with ValidationError
lead2 = env['real.estate.lead'].create({
    'name': 'Test 2',
    'agent_id': agent.id,
    'phone': '+55 11 12345-6789',  # Same phone, same agent
})
```

### Monitor Redis Sessions

```bash
# Connect to Redis
docker compose exec redis redis-cli

# List all sessions
KEYS session:*

# Check specific session
GET session:<session_id>

# Monitor real-time
MONITOR
```

### SQL Query Performance

```bash
# Enable slow query log in PostgreSQL
docker compose exec db psql -U odoo -d realestate

# Check query plan
EXPLAIN ANALYZE 
SELECT * FROM real_estate_lead 
WHERE state = 'qualified' 
  AND agent_id = 5 
ORDER BY create_date DESC 
LIMIT 50;

# Should use indexes on state, agent_id, create_date
```

## API Testing with curl

### 1. Authenticate

```bash
# Get OAuth token (replace with actual endpoint)
JWT=$(curl -s -X POST http://localhost:8069/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"app","client_secret":"secret"}' \
  | jq -r '.access_token')

# Get session (login)
SESSION=$(curl -s -X POST http://localhost:8069/api/v1/auth/login \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"username":"agent1","password":"agent1"}' \
  -c /tmp/cookies.txt \
  | jq -r '.session_id')
```

### 2. Create Lead

```bash
curl -X POST http://localhost:8069/api/v1/leads \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION" \
  -H "X-Company-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "João Silva - Apto Centro",
    "phone": "+55 11 98765-4321",
    "email": "joao@example.com",
    "budget_min": 200000,
    "budget_max": 350000,
    "bedrooms_needed": 2,
    "location_preference": "Centro, Jardins"
  }' | jq
```

### 3. List Leads

```bash
curl -X GET "http://localhost:8069/api/v1/leads?page=1&limit=10&state=qualified" \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION" \
  -H "X-Company-ID: 1" \
  | jq
```

### 4. Convert Lead

```bash
curl -X POST http://localhost:8069/api/v1/leads/123/convert \
  -H "Authorization: Bearer $JWT" \
  -H "Cookie: session_id=$SESSION" \
  -H "X-Company-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{"property_id": 456}' \
  | jq
```

## Performance Optimization

### Database Indexes (Automatic)

Odoo auto-creates indexes for:
- Primary keys (`id`)
- Many2one foreign keys (`agent_id`, `partner_id`, etc.)
- Many2many relation tables

**Manual indexes** (already in model):
```python
state = fields.Selection(index=True)       # Frequently filtered
create_date = fields.Datetime(index=True)  # Frequently sorted
```

### Query Optimization

**❌ BAD** (N+1 queries):
```python
leads = env['real.estate.lead'].search([])
for lead in leads:
    print(lead.agent_id.name)  # Query per lead!
```

**✅ GOOD** (Single query):
```python
leads = env['real.estate.lead'].search_read(
    domain=[],
    fields=['id', 'name', 'agent_id']  # Prefetch related
)
```

### Pagination (Mandatory)

```python
# Always use limit/offset
leads = env['real.estate.lead'].search(
    domain=[],
    limit=50,
    offset=(page - 1) * 50,
    order='create_date desc'
)
```

## Testing Strategy

Per [ADR-003](../../docs/adr/ADR-003-mandatory-test-coverage.md):

### Unit Tests (Mock everything)
- **Location**: `tests/unit/`
- **Run**: `python3 test_file.py`
- **Coverage**: Business logic, validations, calculations
- **No DB access**: Use `unittest.mock`

### E2E Tests (Real environment)
- **Cypress**: UI flows (`cypress/e2e/`)
- **Shell/curl**: API endpoints (`integration_tests/`)
- **Real DB**: Test actual behavior end-to-end

**Target**: 80% overall coverage (SC-003 compliance)

### Test Creation - Use Specialized Agents (Constitution Required)

The constitution **mandates** using specialized prompts/agents for test creation:

| Agent | Prompt File | Purpose |
|-------|-------------|---------|
| **Test Strategy Agent** | `.github/prompts/test-strategy.prompt.md` | Analyzes code and recommends correct test type (applies "Golden Rule") |
| **Test Executor Agent** | `.github/prompts/test-executor.prompt.md` | Creates test code automatically based on recommendations |
| **SpecKit Tests Agent** | `.github/agents/speckit.tests.agent.md` | Generates complete tests from acceptance scenarios (spec.md) |

**Recommended Workflow**:
```bash
# Option 1: Strategic approach (analyze then execute)
1. Consult Test Strategy Agent → Get test type recommendation
2. Use Test Executor Agent → Generate test code

# Option 2: Scenario-based approach (from spec)
Use SpecKit Tests Agent → Generates multiple tests from spec.md acceptance criteria
```

**Rationale**: Specialized prompts ensure:
- Consistency across test files
- ADR-003 compliance (correct test type selection)
- Proper `.env` credential usage (no hardcoded values)
- Test template adherence

## Next Steps

1. **Read full specs**:
   - [data-model.md](data-model.md) - Complete model definition
   - [contracts/openapi.yaml](contracts/openapi.yaml) - Full API spec
   - [research.md](research.md) - Technical decisions

2. **Check ADRs**:
   - ADR-001: Module structure
   - ADR-003: Test coverage
   - ADR-011: Controller security

3. **Start coding**:
   - Follow [tasks.md](tasks.md) (generated by `/speckit.tasks`)
   - Write tests first (TDD)
   - Use existing patterns from `quicksol_estate`

---

**Questions?** Check [../README.md](../README.md) or existing module code.
