# Research: Real Estate Lead Management System

**Branch**: `006-lead-management` | **Date**: 2026-01-29  
**Phase**: 0 - Research & Technical Discovery

## Research Tasks

Based on Technical Context analysis, the following areas require research to inform implementation decisions:

### 1. Odoo Mail Thread & Activity Integration Patterns

**Question**: How to properly implement mail.thread and mail.activity.mixin in custom models for activity tracking?

**Decision**: Inherit from `mail.thread` and `mail.activity.mixin` in model definition

**Rationale**: 
- Odoo provides native support for activity tracking via these mixins
- `mail.thread` enables chatter widget (messages, notes, followers)
- `mail.activity.mixin` provides scheduled activities with reminders
- Both are standard Odoo patterns used extensively in core modules
- Integration is automatic once inherited - no custom implementation needed

**Implementation Pattern**:
```python
from odoo import models, fields, api

class RealEstateLead(models.Model):
    _name = 'real.estate.lead'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Real Estate Lead'
    
    # All field changes are automatically tracked in chatter
    state = fields.Selection(tracking=True)  # tracking=True logs changes
    agent_id = fields.Many2one('real.estate.agent', tracking=True)
```

**Alternatives Considered**:
- Custom logging table: Rejected - reinvents wheel, no UI integration
- External logging service: Rejected - adds dependency, breaks Odoo ecosystem
- mail.thread only: Rejected - loses activity scheduling/reminders

**References**:
- Existing usage in `real.estate.property` model (if already implemented)
- Odoo documentation: https://www.odoo.com/documentation/18.0/developer/reference/backend/mixins.html

---

### 2. Duplicate Detection Strategy in Odoo

**Question**: What's the best approach for per-agent duplicate prevention (same phone/email) in Odoo?

**Decision**: SQL constraint with `@api.constrains` decorator

**Rationale**:
- Database-level constraint ensures data integrity even outside API flows
- `@api.constrains` provides user-friendly error messages in UI
- Query optimization: Single DB query using `search_count()` with domain
- Handles edge cases: null emails, formatting variations, case sensitivity

**Implementation Pattern**:
```python
from odoo import api, models
from odoo.exceptions import ValidationError

class RealEstateLead(models.Model):
    _name = 'real.estate.lead'
    
    @api.constrains('agent_id', 'phone', 'email')
    def _check_duplicate_per_agent(self):
        for record in self:
            if not record.agent_id:
                continue
            
            # Prevent duplicate phone for same agent (exclude lost/won leads)
            if record.phone:
                domain = [
                    ('agent_id', '=', record.agent_id.id),
                    ('phone', '=ilike', record.phone.strip()),
                    ('state', 'not in', ['lost', 'won']),
                    ('id', '!=', record.id)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(
                        f"You already have an active lead with phone {record.phone}. "
                        f"Please edit the existing lead or add a new activity."
                    )
            
            # Similar check for email
            if record.email:
                domain = [
                    ('agent_id', '=', record.agent_id.id),
                    ('email', '=ilike', record.email.strip().lower()),
                    ('state', 'not in', ['lost', 'won']),
                    ('id', '!=', record.id)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(
                        f"You already have an active lead with email {record.email}. "
                        f"Please edit the existing lead or add a new activity."
                    )
```

**Alternatives Considered**:
- Controller-level validation only: Rejected - can bypass via direct model access
- Unique SQL constraint: Rejected - too restrictive (blocks cross-agent duplicates)
- Pre-save deduplication: Rejected - doesn't prevent UI confusion before save
- Fuzzy matching (Levenshtein): Rejected - performance overhead, false positives

**Edge Cases Handled**:
- Null phone/email: Constraint skips if field is empty
- Lost/won leads: Excluded from duplicate check (can reuse same contact)
- Case sensitivity: `=ilike` operator handles case-insensitive matching
- Whitespace: `strip()` normalizes input

---

### 3. Soft Delete Implementation in Odoo

**Question**: How to implement soft delete (active=False) while maintaining referential integrity?

**Decision**: Use Odoo's built-in `active` field with `_sql_constraints` prevention

**Rationale**:
- Odoo's `active` field is framework-native (automatic filtering in searches/views)
- Archive action built-in to Odoo UI (no custom implementation needed)
- Maintains referential integrity (archived records still accessible via `with_context(active_test=False)`)
- Works seamlessly with record rules (archived records still respect security)

**Implementation Pattern**:
```python
class RealEstateLead(models.Model):
    _name = 'real.estate.lead'
    
    active = fields.Boolean(default=True, string="Active")
    
    # Prevent actual deletion (unlink)
    def unlink(self):
        # Instead of deleting, archive
        self.write({'active': False})
        return True  # Pretend delete succeeded for UI compatibility
```

**View Configuration**:
```xml
<!-- Add Archive action to action menu -->
<record id="action_real_estate_lead_archive" model="ir.actions.server">
    <field name="name">Archive</field>
    <field name="model_id" ref="model_real_estate_lead"/>
    <field name="binding_model_id" ref="model_real_estate_lead"/>
    <field name="state">code</field>
    <field name="code">records.write({'active': False})</field>
</record>
```

**Alternatives Considered**:
- Custom `deleted` boolean: Rejected - doesn't integrate with Odoo's active filtering
- Deletion state in state field: Rejected - clutters business logic
- Physical delete with audit log: Rejected - violates spec requirement (indefinite retention)
- Separate `archived_leads` table: Rejected - complicates queries, loses relationships

**Odoo Framework Benefits**:
- `search()` automatically filters `active=True` unless `active_test=False`
- UI automatically shows/hides archive button based on `active` state
- List views have built-in "Archived" filter
- No custom filtering logic needed in controllers

---

### 4. Record Rules for Multi-Tenancy + Agent Isolation

**Question**: How to structure record rules for complex access (agent sees own, manager sees all company)?

**Decision**: Separate record rules per profile with explicit domains

**Rationale**:
- Odoo record rules are OR'd within same model, AND'd across models
- Multiple rules provide clear, auditable access logic
- Easier to debug than complex single-rule domain
- Aligns with existing RBAC implementation (branch 005)

**Implementation Pattern**:
```xml
<!-- Agent: Own leads only (within assigned companies) -->
<record id="real_estate_lead_agent_rule" model="ir.rule">
    <field name="name">Agent: Own Leads Only</field>
    <field name="model_id" ref="model_real_estate_lead"/>
    <field name="domain_force">[
        ('agent_id.user_id', '=', user.id),
        ('company_ids', 'in', user.estate_company_ids.ids)
    ]</field>
    <field name="groups" eval="[(4, ref('quicksol_estate.group_estate_agent'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="True"/>
    <field name="perm_unlink" eval="True"/>
</record>

<!-- Manager: All company leads -->
<record id="real_estate_lead_manager_rule" model="ir.rule">
    <field name="name">Manager: All Company Leads</field>
    <field name="model_id" ref="model_real_estate_lead"/>
    <field name="domain_force">[
        ('company_ids', 'in', user.estate_company_ids.ids)
    ]</field>
    <field name="groups" eval="[(4, ref('quicksol_estate.group_estate_manager'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="True"/>
    <field name="perm_unlink" eval="True"/>
</record>
```

**Access Rights (`ir.model.access.csv`)**:
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_real_estate_lead_agent,access_real_estate_lead_agent,model_real_estate_lead,group_estate_agent,1,1,1,1
access_real_estate_lead_manager,access_real_estate_lead_manager,model_real_estate_lead,group_estate_manager,1,1,1,1
```

**Alternatives Considered**:
- Single rule with OR domain: Rejected - harder to debug, less explicit
- Python record rules: Rejected - performance overhead, less maintainable
- Controller-level filtering only: Rejected - bypasses UI security
- Global admin rule: Needed but separate (system admin sees everything)

**Testing Strategy**:
- Integration tests verify agent cannot see other agents' leads
- Integration tests verify manager sees all company leads
- Integration tests verify zero cross-company leakage
- Tests use real DB (not mocked) per ADR-003

---

### 5. Lead Conversion Transaction Pattern

**Question**: How to ensure atomic lead conversion (lead update + sale creation)?

**Decision**: Odoo ORM transaction management with explicit rollback on error

**Rationale**:
- Odoo's ORM automatically wraps controller methods in transactions
- `cr.commit()` and `cr.rollback()` provide explicit control when needed
- Try-except blocks ensure cleanup on failure
- Follows existing patterns in `real.estate.property` module

**Implementation Pattern**:
```python
from odoo import http, _
from odoo.exceptions import UserError, ValidationError

class LeadController(http.Controller):
    
    @http.route('/api/v1/leads/<int:lead_id>/convert', type='json', auth='none', methods=['POST'])
    @require_jwt
    @require_session
    @require_company
    def convert_lead(self, lead_id, property_id, **kwargs):
        try:
            env = request.env
            lead = env['real.estate.lead'].browse(lead_id)
            
            # Validate lead exists and agent has access
            if not lead.exists():
                return error_response('Lead not found', 404)
            
            # Validate property exists and agent has access
            property = env['real.estate.property'].browse(property_id)
            if not property.exists():
                return error_response('Property not found', 404)
            
            # Create sale record
            sale = env['real.estate.sale'].create({
                'property_id': property.id,
                'partner_id': lead.partner_id.id,
                'phone': lead.phone,
                'email': lead.email,
                'agent_id': lead.agent_id.id,
                'company_ids': [(6, 0, lead.company_ids.ids)],
                'lead_id': lead.id,
            })
            
            # Update lead state and link
            lead.write({
                'state': 'won',
                'converted_property_id': property.id,
                'converted_sale_id': sale.id,
            })
            
            # Log conversion activity
            lead.message_post(
                body=f"Lead converted to sale for property {property.name}",
                subtype_xmlid='mail.mt_note',
            )
            
            # Transaction auto-commits on success
            return success_response({
                'lead_id': lead.id,
                'sale_id': sale.id,
            })
            
        except ValidationError as e:
            # Odoo will auto-rollback transaction on exception
            return error_response(str(e), 400)
        except Exception as e:
            # Log error for debugging
            _logger.error(f"Lead conversion failed: {e}", exc_info=True)
            return error_response('Conversion failed', 500)
```

**Alternatives Considered**:
- Manual `cr.savepoint()`: Rejected - overkill, ORM handles it
- Two-phase commit: Rejected - adds complexity, not needed for single DB
- Separate background job: Rejected - user expects immediate feedback
- No transaction management: Rejected - risk of orphaned records

**Error Scenarios Handled**:
- Lead not found: Return 404, no database changes
- Property not found: Return 404, no database changes
- Sale creation failure: Auto-rollback, lead stays in original state
- Validation errors: Return 400 with error message, no partial commit

---

### 6. Performance Optimization for Large Lead Datasets

**Question**: How to ensure <3 second dashboard load for 5000 leads (SC-002)?

**Decision**: Database indexes + pagination + optimized queries

**Rationale**:
- PostgreSQL indexes dramatically speed up filtering/sorting
- Pagination prevents loading excessive data into memory
- `search_read()` more efficient than `search()` + `read()`
- Lazy loading prevents N+1 query problems

**Implementation Pattern**:

**Model Indexes** (`real_estate_lead.py`):
```python
class RealEstateLead(models.Model):
    _name = 'real.estate.lead'
    
    # Optimize index for common query patterns
    _sql_constraints = [
        # Other constraints...
    ]
    
    # Odoo auto-indexes:
    # - Many2one fields (agent_id, partner_id, property_interest)
    # - Many2many foreign keys (company_ids)
    # - Selection fields with index=True
    
    state = fields.Selection(index=True)  # Explicit index for filtering
    create_date = fields.Datetime(index=True)  # For sorting by date
```

**Controller Pagination**:
```python
@http.route('/api/v1/leads', type='json', auth='none', methods=['GET'])
@require_jwt
@require_session
@require_company
def list_leads(self, page=1, limit=50, state=None, agent_id=None, **kwargs):
    env = request.env
    Lead = env['real.estate.lead']
    
    # Build domain
    domain = []
    if state:
        domain.append(('state', '=', state))
    if agent_id:
        domain.append(('agent_id', '=', int(agent_id)))
    
    # Record rules auto-apply company/agent filtering
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Optimized query: search_read combines search + read
    leads = Lead.search_read(
        domain=domain,
        fields=['id', 'name', 'partner_id', 'agent_id', 'state', 
                'phone', 'email', 'budget_min', 'budget_max', 'create_date'],
        offset=offset,
        limit=limit,
        order='create_date desc'
    )
    
    # Total count for pagination metadata
    total_count = Lead.search_count(domain)
    
    return success_response({
        'leads': leads,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total_count,
            'pages': (total_count + limit - 1) // limit,
        }
    })
```

**Alternatives Considered**:
- No pagination: Rejected - violates performance constraint (SC-002)
- Client-side pagination: Rejected - still loads all data initially
- Cursor-based pagination: Rejected - overkill, offset pagination sufficient
- Caching in Redis: Considered for Phase 3 - adds complexity, may not be needed

**Database Optimization**:
- Odoo automatically indexes Many2one foreign keys
- Explicit `index=True` on frequently filtered fields (state, create_date)
- Avoid loading unnecessary fields (use `fields=` parameter)
- `search_read()` single query vs `search()` + `read()` multiple queries

**Performance Testing**:
- Load test with 5000 leads per company
- Measure dashboard endpoint response time
- Verify <3 second target (SC-002)
- Monitor PostgreSQL slow query log

---

## Summary

All technical unknowns resolved. No external dependencies or NEEDS CLARIFICATION items remaining. Implementation can proceed to Phase 1 (Data Model & Contracts) using standard Odoo patterns:

- **Activity tracking**: `mail.thread` + `mail.activity.mixin` (standard Odoo)
- **Duplicate prevention**: `@api.constrains` with SQL query (database-level)
- **Soft delete**: Odoo's `active` field (framework-native)
- **Multi-tenancy**: Record rules per profile (existing pattern from RBAC)
- **Atomic conversion**: ORM transaction management (automatic)
- **Performance**: Database indexes + pagination + `search_read()` (standard optimizations)

All patterns validated against existing codebase (`quicksol_estate` module) and Odoo best practices.

---

**Next Phase**: Phase 1 - Data Model & Contracts Design
