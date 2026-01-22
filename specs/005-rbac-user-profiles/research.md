# Phase 0: Research - RBAC User Profiles System

**Date**: 2026-01-20  
**Feature**: [spec.md](spec.md)  
**Purpose**: Analyze existing codebase patterns to inform implementation decisions

## Existing Security Infrastructure

### Current Groups (quicksol_estate/security/groups.xml)

**Existing Groups** (4 groups already defined):

1. **`group_real_estate_manager`** - "Real Estate Company Manager"
   - Inherits from: `base.group_user`
   - Full CRUD access to company data
   - Used as base for many record rules

2. **`group_real_estate_user`** - "Real Estate Company User"
   - Inherits from: `base.group_user`
   - Limited access (view + edit, no delete)
   - Base group for common users

3. **`group_real_estate_agent`** - "Real Estate Agent"
   - Inherits from: `group_real_estate_user`
   - Agent-specific record rules (own properties/leads only)

4. **`group_real_estate_portal_user`** - "Real Estate Portal User"
   - Inherits from: `base.group_portal`
   - Client/tenant limited access

**Pattern Identified**: Group hierarchy using `implied_ids` field for inheritance.

**Decision for New Groups**:
- **Reuse**: `group_real_estate_manager`, `group_real_estate_user`, `group_real_estate_agent`, `group_real_estate_portal_user`
- **Add**: `group_real_estate_owner`, `group_real_estate_director`, `group_real_estate_prospector`, `group_real_estate_receptionist`, `group_real_estate_financial`, `group_real_estate_legal`
- **Hierarchy**:
  - Owner: standalone (full access, inherits base.group_user)
  - Director: inherits Manager
  - Manager: existing (inherits User)
  - User: existing base group
  - Agent: existing (inherits User)
  - Prospector: standalone (limited create access)
  - Receptionist, Financial, Legal: inherit User

**Rationale**: Leverage existing groups where possible to minimize migration impact. New groups fill gaps identified in ADR-019.

---

### Current Record Rules (quicksol_estate/security/record_rules.xml)

**Pattern Analysis** - All rules follow multi-tenancy pattern:

**Multi-Company Base Rule**:
```xml
<field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
<field name="groups" eval="[(4, ref('group_real_estate_user')), (4, ref('group_real_estate_manager'))]"/>
```

**Agent-Specific Rule (Own Records)**:
```xml
<field name="domain_force">[('user_id', '=', user.id)]</field>
<field name="groups" eval="[(4, ref('group_real_estate_agent'))]"/>
```

**Agent-Specific Rule (Related Records via Nested Field)**:
```xml
<field name="domain_force">[('property_id.agent_id.user_id', '=', user.id)]</field>
<field name="groups" eval="[(4, ref('group_real_estate_agent'))]"/>
```

**Existing Models with Record Rules**:
- ✅ `real.estate.property` - Multi-company + agent own
- ✅ `real.estate.agent` - Multi-company + own record
- ✅ `real.estate.tenant` - Multi-company only
- ✅ `real.estate.lease` - Multi-company + agent own
- ✅ `real.estate.sale` - Multi-company + agent own
- ✅ `real.estate.agent.property.assignment` - Multi-company + agent own
- ✅ `real.estate.commission.rule` - Multi-company + agent own

**Models Needing New Rules** (for new profiles):
- `real.estate.commission.transaction` - Financial profile needs CRUD access
- `real.estate.lease` - Receptionist needs CRUD, Legal needs read-only
- `real.estate.key` (if exists) - Receptionist needs CRUD
- `res.users` - Owner needs create/update access with company restriction

**Decision: Record Rule Strategy**:

1. **Keep existing rules** - They provide base multi-tenancy isolation
2. **Add profile-specific rules**:
   - **Prospector**: Only see properties where `prospector_id.user_id = user.id`
   - **Receptionist**: Read-only properties, CRUD on leases/keys
   - **Financial**: Read-only properties/sales, CRUD on commissions
   - **Legal**: Read-only contracts, can add notes
   - **Portal**: Only see records where `partner_id = user.partner_id`

3. **Use Odoo's rule combining logic**:
   - Multiple rules for same group are OR'd together
   - Rules from different groups are AND'd together (user must satisfy all)

**Example: Agent with Multiple Rules**:
```python
# Rule 1: Multi-company (from group_real_estate_user)
[('company_ids', 'in', user.estate_company_ids.ids)]

# Rule 2: Own properties (from group_real_estate_agent)
[('agent_id.user_id', '=', user.id)]

# Combined (AND): Agent sees own properties within their companies
```

**Rationale**: Odoo's rule engine automatically combines multiple rules per user's groups. This allows granular permission composition.

---

### Current Data Model Patterns

**Multi-Tenancy Field** (`estate_company_ids`):

**Location**: `res.users` model extended in `quicksol_estate/models/res_users.py`

```python
estate_company_ids = fields.Many2many(
    'thedevkitchen.estate.company',
    string='Real Estate Companies',
    help='Companies this user has access to'
)
```

**Pattern**: Many2many allows users to belong to multiple companies (e.g., SaaS admin managing multiple agencies).

**Decision**: **No changes needed** - Existing field supports all RBAC requirements.

---

**Agent Model** (`real.estate.agent`):

**Key Fields**:
- `user_id` - Many2one to `res.users` (links agent to system user)
- `company_ids` - Many2many to `thedevkitchen.estate.company` (multi-tenancy)
- `creci` - Brazilian real estate broker license (optional for trainees)

**Pattern**: Agent records link to users via `user_id`. A user can have an agent profile by:
1. Being in `group_real_estate_agent` group
2. Having a corresponding `real.estate.agent` record with `user_id` set

**Decision for Prospector**:
- **Reuse agent model** - Prospectors are agents with limited permissions
- Add `prospector_id` field to `real.estate.property` pointing to `real.estate.agent`
- Prospector users are in `group_real_estate_prospector` group (not agent group)
- Commission split logic checks both `agent_id` and `prospector_id`

**Rationale**: Avoids creating duplicate "person" models. Prospector is a role/permission variant of agent, not a different entity.

---

**Commission Rule Model** (`real.estate.commission.rule`):

**Current Structure**:
```python
agent_id = fields.Many2one('real.estate.agent')  # Agent this rule applies to
company_id = fields.Many2one('thedevkitchen.estate.company')  # Company
transaction_type = fields.Selection([('sale', 'Sale'), ('rental', 'Rental'), ('both', 'Both')])
structure_type = fields.Selection([('percentage', 'Percentage'), ('fixed', 'Fixed Amount')])
percentage = fields.Float()  # Commission %
fixed_amount = fields.Monetary()  # Or fixed amount
valid_from = fields.Date()  # Effective date
valid_to = fields.Date()  # Expiration (optional)
```

**Pattern**: One rule per agent per transaction type. Non-retroactive (only applies to future transactions).

**Decision for Commission Split**:

**Add new method to commission_rule.py**:
```python
def calculate_split_commission(self, property_record):
    """
    Calculate commission split between prospector and selling agent.
    
    Args:
        property_record: real.estate.property record with agent_id and prospector_id
    
    Returns:
        dict: {'prospector': Decimal, 'agent': Decimal, 'total': Decimal}
    """
    if not property_record.prospector_id:
        # No prospector, 100% to agent
        return {
            'prospector': 0.0,
            'agent': self._calculate_agent_commission(property_record),
            'total': self._calculate_agent_commission(property_record)
        }
    
    # Get split percentages from configuration (default 30/70)
    prospector_pct = self.env['ir.config_parameter'].sudo().get_param(
        'quicksol_estate.prospector_commission_percentage', 
        default=0.30
    )
    agent_pct = 1 - float(prospector_pct)
    
    total_commission = self._calculate_agent_commission(property_record)
    
    return {
        'prospector': total_commission * float(prospector_pct),
        'agent': total_commission * agent_pct,
        'total': total_commission
    }
```

**Rationale**: 
- Configurable split via system parameters (allows changing default 30/70 without code changes)
- Backward compatible (works with or without prospector)
- Deterministic and testable

---

### Testing Infrastructure

**Current Test Structure**:

```
tests/
├── __init__.py
├── test_property.py            # Property model tests
├── test_agent.py               # Agent model + CRECI validation
├── test_commission_rule.py     # Commission calculation tests
├── test_multi_company.py       # Multi-tenancy isolation tests
└── common.py                   # Test utilities (create_company, create_user, etc.)
```

**Pattern**: 
- Use `odoo.tests.TransactionCase` for unit tests
- Use `odoo.tests.HttpCase` for integration tests (if HTTP endpoints exist)
- Common utilities in `common.py` for test data creation

**Decision for RBAC Tests**:

**Add 11 new test files**:

1. **`test_rbac_owner.py`** - Owner can create users, see all company data
2. **`test_rbac_director.py`** - Director inherits manager permissions + reports
3. **`test_rbac_manager.py`** - Manager sees all company data, cannot create users
4. **`test_rbac_agent.py`** - Agent sees only own properties/leads
5. **`test_rbac_prospector.py`** - Prospector sees only prospected properties
6. **`test_rbac_receptionist.py`** - Receptionist CRUD contracts, read-only properties
7. **`test_rbac_financial.py`** - Financial CRUD commissions, read-only sales
8. **`test_rbac_legal.py`** - Legal read-only contracts, can add notes
9. **`test_rbac_portal.py`** - Portal user sees only own contracts
10. **`test_multi_tenancy_isolation.py`** - Company A cannot see Company B (expanded)
11. **`test_commission_split.py`** - Prospector/agent commission split calculations

**Test Structure Pattern**:
```python
from odoo.tests import TransactionCase
from odoo.exceptions import AccessError

class TestRBACAgent(TransactionCase):
    def setUp(self):
        super().setUp()
        # Create test company
        self.company_a = self.env['thedevkitchen.estate.company'].create({...})
        
        # Create agent user
        self.agent_user = self.env['res.users'].create({
            'name': 'Test Agent',
            'login': 'agent@test.com',
            'groups_id': [(6, 0, [self.env.ref('quicksol_estate.group_real_estate_agent').id])],
            'estate_company_ids': [(6, 0, [self.company_a.id])]
        })
        
        # Create agent record
        self.agent = self.env['real.estate.agent'].create({
            'name': 'Test Agent',
            'user_id': self.agent_user.id,
            'company_ids': [(6, 0, [self.company_a.id])]
        })
    
    def test_agent_can_create_property(self):
        """Agent can create property and it's auto-assigned to them"""
        property = self.env['real.estate.property'].with_user(self.agent_user).create({
            'name': 'Test Property',
            'company_ids': [(6, 0, [self.company_a.id])],
            # agent_id should auto-populate from context
        })
        self.assertEqual(property.agent_id, self.agent)
    
    def test_agent_cannot_see_other_agent_property(self):
        """Agent cannot see properties of other agents"""
        # Create another agent's property
        other_property = self.env['real.estate.property'].create({
            'name': 'Other Property',
            'agent_id': self.other_agent.id,  # Different agent
            'company_ids': [(6, 0, [self.company_a.id])]
        })
        
        # Agent user searches for properties
        properties = self.env['real.estate.property'].with_user(self.agent_user).search([])
        
        # Should NOT see other agent's property
        self.assertNotIn(other_property, properties)
```

**Rationale**: Follow existing test patterns for consistency. Each profile gets dedicated test file for clarity.

---

### Cypress E2E Testing Patterns

**Existing E2E Tests**:
```
cypress/e2e/
├── agents-dual-auth.cy.js           # Agent authentication flow
├── properties-dual-auth.cy.js       # Property CRUD with auth
├── commissions-dual-auth.cy.js      # Commission workflows
└── jornada-completa-imoveis.cy.js   # Complete property journey
```

**Pattern**:
- Use custom command `cy.loginWithSession()` for authentication
- Create test data via API calls (`cy.request()`)
- Verify UI elements and permissions
- Clean up test data after each test

**Decision for RBAC E2E Tests**:

**Add 6 new E2E test files**:

1. **`rbac-owner-onboarding.cy.js`**
   - Owner creates company
   - Owner creates users with different profiles
   - Verify each user has correct access

2. **`rbac-agent-property-access.cy.js`**
   - Agent creates property
   - Verify property appears in agent's list
   - Verify property does NOT appear for other agent

3. **`rbac-manager-oversight.cy.js`**
   - Manager sees all properties from all agents
   - Manager reassigns lead to different agent

4. **`rbac-prospector-commission.cy.js`**
   - Prospector registers new property
   - Manager assigns selling agent
   - Verify commission split calculation (30/70)

5. **`rbac-portal-user-isolation.cy.js`**
   - Portal user logs in
   - Sees only own contracts
   - Cannot see other clients' data

6. **`rbac-multi-tenancy-isolation.cy.js`**
   - User from Company A logs in
   - Verifies cannot see Company B data
   - Even if user has same profile type

**Example E2E Test**:
```javascript
describe('RBAC - Agent Property Access', () => {
  beforeEach(() => {
    // Create test company and agents
    cy.task('createTestCompany', { name: 'Test Agency' }).then((company) => {
      cy.wrap(company.id).as('companyId')
      
      cy.task('createAgent', { 
        name: 'Agent 1', 
        companyId: company.id 
      }).as('agent1')
      
      cy.task('createAgent', { 
        name: 'Agent 2', 
        companyId: company.id 
      }).as('agent2')
    })
  })

  it('Agent sees only own properties', function() {
    // Agent 1 creates property
    cy.loginWithSession(this.agent1.email, 'password')
    cy.visit('/properties/new')
    cy.get('[name="name"]').type('Agent 1 Property')
    cy.get('button[type="submit"]').click()
    
    // Agent 2 logs in
    cy.loginWithSession(this.agent2.email, 'password')
    cy.visit('/properties')
    
    // Should NOT see Agent 1's property
    cy.contains('Agent 1 Property').should('not.exist')
  })
})
```

**Rationale**: E2E tests validate permissions from user perspective, catching UI-level permission leaks that unit tests might miss.

---

## Technology Stack Decisions

### Odoo Native Security vs External Systems

**Evaluated Options**:

1. **Odoo Native** (res.groups, ir.rule, ir.model.access)
   - ✅ Built-in, battle-tested
   - ✅ Zero external dependencies
   - ✅ Automatic integration with ORM
   - ✅ Well-documented
   - ❌ Less flexible than custom systems

2. **OCA base_user_role** (external module)
   - ✅ More flexible role management
   - ✅ Temporal permissions
   - ❌ External dependency
   - ❌ Added complexity
   - ❌ Not needed for Phase 1

3. **Custom RBAC System** (build from scratch)
   - ✅ Complete control
   - ❌ High development cost
   - ❌ Maintenance burden
   - ❌ Reinventing the wheel

**Decision**: **Use Odoo Native Security** (ADR-019 decision)

**Rationale**:
- Phase 1 MVP doesn't need advanced features (temporal roles, dynamic permissions)
- Odoo's security is proven at scale
- Faster time-to-market
- Can add `base_user_role` in Phase 2 if validated

---

### Commission Split Implementation

**Evaluated Approaches**:

1. **System Parameter (Chosen)**
   - Split percentage in `ir.config_parameter`
   - Default: 30% prospector, 70% agent
   - Changeable via Settings UI
   - ✅ Simple, no migration needed for percentage changes
   - ✅ Testable with different values

2. **Field on Commission Rule**
   - Add `prospector_split_percentage` field to `commission.rule` model
   - ❌ More complex (per-agent split configs)
   - ❌ Overkill for Phase 1

3. **Hardcoded Constant**
   - `PROSPECTOR_SPLIT = 0.30` in code
   - ❌ Requires code changes to adjust split
   - ❌ Not flexible enough

**Decision**: **System Parameter with 30/70 default**

**Implementation**:
```python
# In commission_rule.py
def _get_prospector_split_percentage(self):
    """Get prospector commission split percentage from config."""
    return float(self.env['ir.config_parameter'].sudo().get_param(
        'quicksol_estate.prospector_commission_percentage',
        default='0.30'
    ))
```

**Rationale**: Balances simplicity (single system-wide default) with flexibility (changeable without code deployment).

---

## Implementation Decisions Summary

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Groups** | Reuse 4 existing + add 5 new | Minimize migration impact |
| **Record Rules** | Extend existing multi-tenancy rules | Leverage proven patterns |
| **prospector_id** | Add to property model, Many2one to agent | Reuse agent entity |
| **Commission Split** | System parameter (30/70 default) | Simple + flexible |
| **Testing** | 11 unit test files + 6 E2E tests | Comprehensive coverage |
| **Migration** | pre/post migration scripts | Safe upgrade path |
| **Documentation** | ADR-019 + quickstart.md | Clear guidance |

---

## Next Steps → Phase 1: Data Model Design

With research complete, proceed to:
1. **data-model.md** - Detailed entity definitions, field specifications, record rule pseudo-code
2. **contracts/** - N/A (no API changes)
3. **quickstart.md** - Developer implementation guide

**All NEEDS CLARIFICATION items resolved** - Ready to proceed to Phase 1.
