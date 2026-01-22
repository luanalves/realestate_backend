# RBAC User Profiles - Developer Quickstart Guide

## Overview

This guide provides step-by-step instructions for implementing the 9-profile RBAC system defined in ADR-019. All changes are in the `quicksol_estate` addon.

**Feature Branch**: `005-rbac-user-profiles`  
**Module Version**: `18.0.2.0.0`  
**Target Coverage**: ≥80% (ADR-003)

## Prerequisites

1. Read [spec.md](spec.md) for functional requirements
2. Read [data-model.md](data-model.md) for complete implementation details
3. Read [research.md](research.md) for existing patterns
4. Ensure Python environment is configured:
   ```bash
   cd 18.0/extra-addons/quicksol_estate
   source ../../../venv/bin/activate  # If using venv
   ```

## Implementation Steps

### Step 1: Update Security Groups (30 mins)

**File**: `security/groups.xml`

1. **Add 5 new security groups** (Owner, Director, Prospector, Receptionist, Financial, Legal)
2. **Preserve hierarchy** using `implied_ids`:
   - Owner → Director → Manager → User
   - Prospector, Receptionist, Financial, Legal → User
3. **Reuse 4 existing groups** (Manager, User, Agent, Portal User)

**Implementation**:
```xml
<!-- After existing group_real_estate_manager -->
<record id="group_real_estate_owner" model="res.groups">
    <field name="name">Real Estate Owner</field>
    <field name="category_id" ref="module_category_real_estate"/>
    <field name="implied_ids" eval="[(4, ref('group_real_estate_director'))]"/>
    <field name="comment">Complete system access: User management, critical settings, all operations.</field>
</record>

<record id="group_real_estate_director" model="res.groups">
    <field name="name">Real Estate Director</field>
    <field name="category_id" ref="module_category_real_estate"/>
    <field name="implied_ids" eval="[(4, ref('group_real_estate_manager'))]"/>
    <field name="comment">Strategic oversight: Analytics, high-value deals, manager supervision.</field>
</record>

<!-- Add Prospector, Receptionist, Financial, Legal similarly -->
```

**See**: [data-model.md#Security Groups](data-model.md#security-groups) for complete XML

**Validation**:
```bash
# After Odoo restart, check groups exist:
docker compose exec odoo odoo shell -d realestate
>>> self.env['res.groups'].search([('name', 'like', 'Real Estate %')]).mapped('name')
```

### Step 2: Update ACLs (45 mins)

**File**: `security/ir.model.access.csv`

1. **Add ~100 ACL entries** for 9 profiles × 10 models
2. **Apply principle of least privilege**:
   - Portal Partner: Read-only for own assignments
   - Prospector: Create properties, read-only for others
   - Receptionist: Assign agents to properties (no financial data)
   - Financial: Read-only all, write commissions/invoices
   - Legal: Read-only all (no write access)
   - Agent: Manage own assignments/commissions
   - Manager: Full CRUD except delete
   - Director/Owner: Full CRUD including delete

**Implementation**:
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_real_estate_property_prospector,real.estate.property.prospector,model_real_estate_property,group_real_estate_prospector,1,0,1,0
access_real_estate_property_receptionist,real.estate.property.receptionist,model_real_estate_property,group_real_estate_receptionist,1,1,0,0
access_real_estate_commission_financial,real.estate.commission.financial,model_real_estate_commission,group_real_estate_financial,1,1,1,0
access_real_estate_property_legal,real.estate.property.legal,model_real_estate_property,group_real_estate_legal,1,0,0,0
```

**See**: [data-model.md#Access Control Lists](data-model.md#access-control-lists) for complete CSV

**Validation**:
```bash
# Check ACL count (should be ~100 entries):
grep -c "^access_" security/ir.model.access.csv
```

### Step 3: Add Record Rules (60 mins)

**File**: `security/record_rules.xml`

1. **Add 23+ profile-specific rules** with domain filtering
2. **Combine with existing multi-company rules** (they stack via OR logic)
3. **Implement ORM-level security** (not just UI hiding)

**Key Patterns**:

**Own-data access** (Agent):
```xml
<record id="rule_real_estate_agent_own_assignments" model="ir.rule">
    <field name="name">Agent: Own Assignments Only</field>
    <field name="model_id" ref="model_real_estate_assignment"/>
    <field name="groups" eval="[(4, ref('group_real_estate_agent'))]"/>
    <field name="domain_force">[
        ('agent_id.user_id', '=', user.id),
        ('company_ids', 'in', user.estate_company_ids.ids)
    ]</field>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="True"/>
    <field name="perm_unlink" eval="False"/>
</record>
```

**Partner-based access** (Portal Partner):
```xml
<record id="rule_real_estate_portal_partner_own_assignments" model="ir.rule">
    <field name="name">Portal Partner: Own Assignments Only</field>
    <field name="model_id" ref="model_real_estate_assignment"/>
    <field name="groups" eval="[(4, ref('group_real_estate_portal_user'))]"/>
    <field name="domain_force">[
        ('partner_id', '=', user.partner_id.id),
        ('company_ids', 'in', user.estate_company_ids.ids)
    ]</field>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="False"/>
    <field name="perm_create" eval="False"/>
    <field name="perm_unlink" eval="False"/>
</record>
```

**Financial data restriction** (Prospector/Receptionist):
```xml
<record id="rule_real_estate_commission_deny_prospector" model="ir.rule">
    <field name="name">Prospector: No Commission Access</field>
    <field name="model_id" ref="model_real_estate_commission"/>
    <field name="groups" eval="[(4, ref('group_real_estate_prospector'))]"/>
    <field name="domain_force">[(0, '=', 1)]</field>  <!-- Always False -->
    <field name="perm_read" eval="False"/>
</record>
```

**See**: [data-model.md#Record Rules](data-model.md#record-rules) for complete XML with all 23+ rules

**Validation**:
```python
# Test in Odoo shell as prospector user:
prospector_user = self.env['res.users'].search([('login', '=', 'prospector@test.com')])
self.env = self.env(user=prospector_user)
commissions = self.env['real.estate.commission'].search([])
# Should return empty recordset
```

### Step 4: Add prospector_id Field (20 mins)

**File**: `models/property.py`

1. **Add Many2one field** linking property to prospecting agent
2. **Auto-populate on create** if user is prospector
3. **Restrict editing** to managers only (field-level security)

**Implementation**:
```python
# After agent_id field definition:
prospector_id = fields.Many2one(
    'real.estate.agent',
    string='Prospector',
    tracking=True,
    index=True,
    help='Agent who prospected/found this property. Earns commission split (default 30%).',
    groups='quicksol_estate.group_real_estate_manager,quicksol_estate.group_real_estate_owner'
)

@api.model_create_multi
def create(self, vals_list):
    """Auto-assign prospector if current user is in prospector group."""
    for vals in vals_list:
        if not vals.get('prospector_id') and self.env.user.has_group('quicksol_estate.group_real_estate_prospector'):
            agent = self.env['real.estate.agent'].search([('user_id', '=', self.env.user.id)], limit=1)
            if agent:
                vals['prospector_id'] = agent.id
    return super().create(vals_list)
```

**Validation**:
```python
# Test auto-assign in unit test:
prospector_agent = self.env['real.estate.agent'].create({'user_id': prospector_user.id, 'name': 'Pro'})
prop = self.env['real.estate.property'].with_user(prospector_user).create({'name': 'Test Property'})
self.assertEqual(prop.prospector_id, prospector_agent)
```

### Step 5: Add Commission Split Logic (30 mins)

**File**: `models/commission_rule.py`

1. **Add system parameter** for prospector split percentage (default 30%)
2. **Implement calculate_split_commission()** method
3. **Return dict** with prospector/agent/total breakdown

**Implementation**:
```python
def _get_prospector_split_percentage(self):
    """Get prospector commission split from system parameters."""
    return float(self.env['ir.config_parameter'].sudo().get_param(
        'quicksol_estate.prospector_commission_split', default='0.30'
    ))

def calculate_split_commission(self, property_record, transaction_amount):
    """
    Calculate commission split between prospector and selling agent.
    
    Returns:
        dict: {
            'prospector_commission': float,
            'agent_commission': float,
            'total_commission': float
        }
    """
    total = self.calculate_commission(transaction_amount)
    
    if not property_record.prospector_id:
        return {
            'prospector_commission': 0.0,
            'agent_commission': total,
            'total_commission': total
        }
    
    prospector_pct = self._get_prospector_split_percentage()
    return {
        'prospector_commission': total * prospector_pct,
        'agent_commission': total * (1.0 - prospector_pct),
        'total_commission': total
    }
```

**Configuration** (Settings → Technical → System Parameters):
```
Key: quicksol_estate.prospector_commission_split
Value: 0.30
```

**Validation**:
```python
# Test split calculation:
rule = self.env['real.estate.commission.rule'].create({'percentage': 5.0})
prop = self.property_model.create({'prospector_id': prospector_agent.id})
split = rule.calculate_split_commission(prop, 100000)
self.assertEqual(split['prospector_commission'], 1500.0)  # 30% of 5000
self.assertEqual(split['agent_commission'], 3500.0)       # 70% of 5000
```

### Step 6: Write Tests (120 mins)

**Directory**: `tests/`

**Coverage Targets** (ADR-003):
- Unit tests: ≥80% line coverage
- Integration tests: All critical workflows
- E2E tests: Security scenarios

**Test Files to Create** (11 files):
```
tests/
├── test_rbac_groups.py           # Group hierarchy, membership
├── test_rbac_acl.py              # CRUD permissions per profile
├── test_rbac_record_rules.py     # Domain filtering, own-data access
├── test_rbac_prospector.py       # Auto-assign, commission split
├── test_rbac_receptionist.py     # Assignment permissions
├── test_rbac_financial.py        # Financial data access
├── test_rbac_legal.py            # Read-only enforcement
├── test_rbac_agent.py            # Own-data restrictions
├── test_rbac_portal.py           # Partner-based access
├── test_rbac_multi_tenancy.py    # Cross-company isolation
└── test_commission_split.py      # Split calculation logic
```

**Example Test** (test_rbac_prospector.py):
```python
from odoo.tests import tagged, TransactionCase
from odoo.exceptions import AccessError

@tagged('post_install', '-at_install', 'rbac')
class TestProspectorProfile(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.prospector_user = cls.env['res.users'].create({
            'name': 'Test Prospector',
            'login': 'prospector@test.com',
            'groups_id': [(6, 0, [cls.env.ref('quicksol_estate.group_real_estate_prospector').id])]
        })
        cls.prospector_agent = cls.env['real.estate.agent'].create({
            'user_id': cls.prospector_user.id,
            'name': 'Prospector Agent'
        })
    
    def test_prospector_can_create_property(self):
        """FR-023: Prospectors can create properties."""
        prop = self.env['real.estate.property'].with_user(self.prospector_user).create({
            'name': 'Prospect Property',
            'sale_price': 200000
        })
        self.assertTrue(prop.exists())
        self.assertEqual(prop.prospector_id, self.prospector_agent)
    
    def test_prospector_cannot_view_commissions(self):
        """FR-030: Prospectors cannot access financial data."""
        commission = self.env['real.estate.commission'].create({'amount': 5000})
        with self.assertRaises(AccessError):
            commission.with_user(self.prospector_user).read(['amount'])
    
    def test_prospector_split_calculation(self):
        """FR-027: Commission split 30/70 between prospector and agent."""
        prop = self.env['real.estate.property'].create({
            'prospector_id': self.prospector_agent.id
        })
        rule = self.env['real.estate.commission.rule'].create({'percentage': 5.0})
        split = rule.calculate_split_commission(prop, 100000)
        
        self.assertEqual(split['total_commission'], 5000.0)
        self.assertEqual(split['prospector_commission'], 1500.0)  # 30%
        self.assertEqual(split['agent_commission'], 3500.0)       # 70%
```

**See**: [data-model.md#Testing Strategy](data-model.md#testing-strategy) for complete test plan

**Run Tests**:
```bash
# All RBAC tests:
docker compose exec odoo odoo -d test_rbac_profiles -i quicksol_estate --test-tags=rbac --stop-after-init

# Specific test:
docker compose exec odoo odoo -d test_rbac_profiles -i quicksol_estate --test-file=addons/quicksol_estate/tests/test_rbac_prospector.py --stop-after-init

# Coverage report:
docker compose exec odoo pytest --cov=addons/quicksol_estate --cov-report=html
```

### Step 7: Create Migration Scripts (45 mins)

**Directory**: `migrations/18.0.2.0.0/`

**Files**:
- `pre-migrate.py` - Backup existing user groups, validate data
- `post-migrate.py` - Assign users to new groups, create system parameters

**Implementation** (pre-migrate.py):
```python
import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """Pre-migration: Backup existing group assignments."""
    _logger.info("=== RBAC Migration 18.0.2.0.0: Starting pre-migration ===")
    
    # Create backup table
    cr.execute("""
        CREATE TABLE IF NOT EXISTS res_groups_users_rel_backup_20250101 AS
        SELECT * FROM res_groups_users_rel
        WHERE gid IN (
            SELECT id FROM res_groups WHERE name LIKE 'Real Estate %'
        )
    """)
    
    # Log current group counts
    cr.execute("""
        SELECT g.name, COUNT(r.uid) 
        FROM res_groups g
        JOIN res_groups_users_rel r ON g.id = r.gid
        WHERE g.name LIKE 'Real Estate %'
        GROUP BY g.name
    """)
    
    for row in cr.fetchall():
        _logger.info(f"Group '{row[0]}': {row[1]} users")
    
    _logger.info("=== Pre-migration complete ===")
```

**Implementation** (post-migrate.py):
```python
import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """Post-migration: Assign default groups, create parameters."""
    _logger.info("=== RBAC Migration 18.0.2.0.0: Starting post-migration ===")
    
    # Create prospector commission split parameter
    cr.execute("""
        INSERT INTO ir_config_parameter (key, value, create_date, create_uid)
        VALUES ('quicksol_estate.prospector_commission_split', '0.30', NOW(), 1)
        ON CONFLICT (key) DO NOTHING
    """)
    
    # Assign existing 'Real Estate User' members to 'Real Estate Agent' if they have agent records
    cr.execute("""
        INSERT INTO res_groups_users_rel (gid, uid)
        SELECT 
            (SELECT id FROM res_groups WHERE name = 'Real Estate Agent'),
            u.id
        FROM res_users u
        JOIN real_estate_agent a ON a.user_id = u.id
        WHERE u.id IN (
            SELECT uid FROM res_groups_users_rel 
            WHERE gid = (SELECT id FROM res_groups WHERE name = 'Real Estate User')
        )
        ON CONFLICT DO NOTHING
    """)
    
    _logger.info("=== Post-migration complete ===")
```

**See**: [data-model.md#Migration Strategy](data-model.md#migration-strategy)

**Test Migration**:
```bash
# Create test database with old schema:
docker compose exec odoo odoo -d test_migration_before -i quicksol_estate --stop-after-init

# Apply migration:
docker compose exec odoo odoo -d test_migration_before -u quicksol_estate --stop-after-init

# Verify:
docker compose exec db psql -U odoo -d test_migration_before -c "SELECT key, value FROM ir_config_parameter WHERE key LIKE 'quicksol_estate%';"
```

### Step 8: Create Cypress E2E Tests (90 mins)

**Directory**: `cypress/e2e/rbac/`

**Test Files** (6 scenarios):
```
cypress/e2e/rbac/
├── prospector-workflow.cy.js      # Create property, verify auto-assign
├── receptionist-workflow.cy.js    # Assign agents, verify no financial access
├── financial-workflow.cy.js       # View commissions, verify read-only properties
├── legal-workflow.cy.js           # View all data, verify no write access
├── agent-workflow.cy.js           # Manage own assignments, verify isolation
└── portal-workflow.cy.js          # View own assignments, verify partner filtering
```

**Example Test** (prospector-workflow.cy.js):
```javascript
describe('RBAC: Prospector Workflow', () => {
  beforeEach(() => {
    cy.loginAsProspector(); // Custom command
  });

  it('should create property and auto-assign as prospector', () => {
    cy.visit('/web#model=real.estate.property&view_type=list');
    cy.contains('Create').click();
    
    cy.get('input[name="name"]').type('Prospected Property');
    cy.get('input[name="sale_price"]').type('250000');
    cy.contains('Save').click();
    
    // Verify prospector_id is set (managers only can see this field)
    cy.loginAsManager();
    cy.visit('/web#model=real.estate.property&view_type=list');
    cy.contains('Prospected Property').click();
    cy.get('input[name="prospector_id"]').should('contain', 'Prospector Agent');
  });

  it('should NOT access commission records', () => {
    cy.visit('/web#model=real.estate.commission&view_type=list');
    cy.contains('Access Denied').should('be.visible');
  });

  it('should NOT edit properties created by others', () => {
    const othersProperty = cy.createProperty({ creator: 'manager@test.com' });
    cy.visit(`/web#id=${othersProperty.id}&model=real.estate.property&view_type=form`);
    cy.get('button.o_form_button_edit').should('not.exist');
  });
});
```

**Run E2E Tests**:
```bash
# All RBAC scenarios:
npx cypress run --spec "cypress/e2e/rbac/**/*.cy.js"

# Specific scenario:
npx cypress run --spec "cypress/e2e/rbac/prospector-workflow.cy.js"

# Interactive mode:
npx cypress open
```

### Step 9: Update Module Manifest (10 mins)

**File**: `__manifest__.py`

1. **Increment version** to `18.0.2.0.0`
2. **Add migration path** in description
3. **Update data files** list

**Implementation**:
```python
{
    'name': 'QuickSol Real Estate',
    'version': '18.0.2.0.0',  # Changed from 18.0.1.0.0
    'category': 'Real Estate',
    'summary': 'Complete real estate management with 9-profile RBAC system',
    'description': """
        Real Estate Management System
        ==============================
        
        Version 18.0.2.0.0 Changes:
        - Added 9-profile RBAC system (ADR-019)
        - Added prospector role with commission split
        - Added receptionist, financial, legal profiles
        - Added director and owner administrative roles
        - Enhanced multi-tenancy security
        
        See docs/adr/ADR-019-rbac-9-profile-system.md for details.
    """,
    'data': [
        'security/groups.xml',         # Updated
        'security/ir.model.access.csv', # Updated
        'security/record_rules.xml',    # Updated
        'views/property_views.xml',     # Add prospector_id field
        # ... existing files
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
```

### Step 10: Test Deployment (30 mins)

**Pre-Deployment Checklist**:
- [ ] All unit tests pass (≥80% coverage)
- [ ] All E2E tests pass
- [ ] Migration scripts tested on copy of production data
- [ ] System parameter `quicksol_estate.prospector_commission_split` documented
- [ ] ADR-019 compliance verified (all 77 requirements satisfied)

**Deployment Steps**:

1. **Backup production database**:
   ```bash
   docker compose exec db pg_dump -U odoo realestate > backup_pre_rbac_$(date +%Y%m%d).sql
   ```

2. **Deploy to staging**:
   ```bash
   git checkout 005-rbac-user-profiles
   docker compose down
   docker compose build odoo
   docker compose up -d
   docker compose exec odoo odoo -d realestate_staging -u quicksol_estate --stop-after-init
   ```

3. **Verify staging**:
   - Log in as each profile (9 users)
   - Test critical workflows per profile
   - Check record rule filtering (no cross-company data)
   - Verify commission split calculations

4. **Deploy to production** (after approval):
   ```bash
   docker compose exec odoo odoo -d realestate -u quicksol_estate --stop-after-init
   docker compose logs -f odoo  # Monitor for errors
   ```

5. **Post-deployment verification**:
   - Check migration logs for errors
   - Verify user group assignments
   - Test prospector property creation
   - Verify commission split parameter exists

**Rollback Plan** (if issues):
```bash
docker compose down
docker compose exec db psql -U odoo -c "DROP DATABASE realestate;"
docker compose exec db psql -U odoo -c "CREATE DATABASE realestate;"
docker compose exec db psql -U odoo realestate < backup_pre_rbac_YYYYMMDD.sql
git checkout main
docker compose up -d
```

## Troubleshooting

### Issue: Users can't see properties after upgrade

**Cause**: Record rules too restrictive or missing company assignment

**Solution**:
```python
# Check user's company assignments:
user = self.env['res.users'].browse(USER_ID)
print(user.estate_company_ids)  # Should not be empty

# Check record rules applying to user:
rules = self.env['ir.rule'].search([('groups', 'in', user.groups_id.ids)])
print(rules.mapped('name'))
```

### Issue: Prospector not auto-assigned to properties

**Cause**: User missing agent record or group membership

**Solution**:
```python
# Verify prospector user has agent record:
agent = self.env['real.estate.agent'].search([('user_id', '=', USER_ID)])
if not agent:
    agent = self.env['real.estate.agent'].create({'user_id': USER_ID, 'name': 'Agent Name'})

# Verify group membership:
user.groups_id = [(4, self.env.ref('quicksol_estate.group_real_estate_prospector').id)]
```

### Issue: Commission split not calculating

**Cause**: System parameter missing

**Solution**:
```python
self.env['ir.config_parameter'].sudo().set_param(
    'quicksol_estate.prospector_commission_split', '0.30'
)
```

### Issue: Tests failing with AccessError

**Cause**: Test user missing required groups

**Solution**:
```python
# In test setup:
self.test_user.groups_id = [(6, 0, [
    self.env.ref('base.group_user').id,
    self.env.ref('quicksol_estate.group_real_estate_agent').id
])]
```

## Performance Considerations

- **Record rules execute on every ORM operation**: Keep domain filters simple
- **Index prospector_id field**: Already included in field definition
- **Cache system parameter**: Retrieved once per request via sudo().get_param()
- **Limit group hierarchy depth**: 4 levels max (Owner → Director → Manager → User)

## Next Steps

After completing this implementation:

1. **Generate implementation tasks**: Run `/speckit.tasks` to create detailed task breakdown
2. **Review with stakeholders**: Present data-model.md to business users for validation
3. **Plan Phase 2 enhancements**: Advanced commission rules, audit logs, reporting dashboards

## References

- [spec.md](spec.md) - Feature specification with all requirements
- [data-model.md](data-model.md) - Complete implementation details
- [research.md](research.md) - Existing codebase patterns
- [ADR-019](../../docs/adr/ADR-019-rbac-9-profile-system.md) - RBAC architecture decision
- [ADR-003](../../docs/adr/ADR-003-mandatory-test-coverage.md) - Testing requirements
- [ADR-008](../../docs/adr/ADR-008-api-security-multi-tenancy.md) - Multi-tenancy patterns

## Support

For questions or issues during implementation:
- Check [TECHNICAL_DEBIT.md](../../TECHNICAL_DEBIT.md) for known issues
- Review Odoo security documentation: https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html
- Consult existing tests in `tests/` for patterns
