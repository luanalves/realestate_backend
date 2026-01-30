# Data Model: Real Estate Lead Management

**Branch**: `006-lead-management` | **Date**: 2026-01-29  
**Phase**: 1 - Data Model Design

## Entity: real.estate.lead

### Description
Represents a potential real estate client/sale opportunity tracked through a sales pipeline. Captures contact information, property preferences, budget constraints, and sales stage progression. Each lead is owned by an agent and belongs to one or more companies (multi-tenancy).

### Model Definition

```python
_name = 'real.estate.lead'
_inherit = ['mail.thread', 'mail.activity.mixin']
_description = 'Real Estate Lead'
_order = 'create_date desc'
```

### Fields

| Field Name | Type | Required | Tracking | Constraints | Description |
|------------|------|----------|----------|-------------|-------------|
| **Core Identity** |
| `name` | Char(100) | Yes | Yes | - | Lead name/title (e.g., "João Silva - Apartamento Centro") |
| `active` | Boolean | Yes | No | default=True | Soft delete flag (active=False = archived) |
| `state` | Selection | Yes | Yes | default='new' | Pipeline stage: new, contacted, qualified, won, lost |
| `create_date` | Datetime | Auto | No | index=True | Lead creation timestamp (Odoo built-in) |
| **Contact Information** |
| `partner_id` | Many2one(res.partner) | No | Yes | - | Linked contact record (optional, can create later) |
| `phone` | Char(20) | No | Yes | - | Primary phone number |
| `email` | Char(120) | No | Yes | - | Email address |
| **Ownership & Multi-Tenancy** |
| `agent_id` | Many2one(real.estate.agent) | Yes | Yes | - | Assigned sales agent (owner of lead) |
| `company_ids` | Many2many(thedevkitchen.estate.company) | Yes | Yes | - | Companies this lead belongs to (multi-tenancy) |
| **Property Preferences** |
| `budget_min` | Float | No | Yes | currency='BRL' | Minimum budget (Brazilian Reais) |
| `budget_max` | Float | No | Yes | currency='BRL' | Maximum budget (Brazilian Reais) |
| `property_type_interest` | Many2one(real.estate.property.type) | No | Yes | - | Desired property type (apartamento, casa, etc.) |
| `location_preference` | Char(200) | No | Yes | - | Preferred locations (free text) |
| `bedrooms_needed` | Integer | No | Yes | - | Desired number of bedrooms |
| `min_area` | Float | No | Yes | - | Minimum area in m² |
| `max_area` | Float | No | Yes | - | Maximum area in m² |
| `property_interest` | Many2one(real.estate.property) | No | Yes | - | Specific property of interest (optional) |
| **Lifecycle Tracking** |
| `first_contact_date` | Date | No | Yes | - | Date of first contact with client |
| `expected_closing_date` | Date | No | Yes | - | Expected deal closing date (for forecasting) |
| `lost_date` | Date | No | Yes | - | Date lead was marked as lost |
| `lost_reason` | Text | No | Yes | - | Reason why lead was lost |
| **Conversion** |
| `converted_property_id` | Many2one(real.estate.property) | No | Yes | - | Property linked when converted to sale |
| `converted_sale_id` | Many2one(real.estate.sale) | No | Yes | - | Sale record created from conversion |

### State Transitions

```
[New] → [Contacted] → [Qualified] → [Won]
  ↓         ↓             ↓
[Lost] ← ← ← ← ← ← ← ← ← ← ← 
  ↓
[Contacted] (reopened)
```

**Valid States**:
- `new`: Initial state when lead is created
- `contacted`: Agent has made first contact with client
- `qualified`: Lead meets criteria for serious pursuit
- `won`: Lead successfully converted to sale
- `lost`: Lead did not result in sale

**Transition Rules**:
- Any state can transition to any other state (bidirectional)
- `won` state automatically set during conversion
- `lost` requires `lost_reason` to be filled
- Reopening from `lost` changes state to `contacted`

### Relationships

```
real.estate.lead
├── Many2one → real.estate.agent (agent_id) [owner]
├── Many2many → thedevkitchen.estate.company (company_ids) [multi-tenancy]
├── Many2one → res.partner (partner_id) [contact]
├── Many2one → real.estate.property.type (property_type_interest)
├── Many2one → real.estate.property (property_interest) [optional interest]
├── Many2one → real.estate.property (converted_property_id) [conversion result]
└── Many2one → real.estate.sale (converted_sale_id) [conversion result]
```

### Validation Rules

#### 1. Per-Agent Duplicate Prevention (FR-005a)
```python
@api.constrains('agent_id', 'phone', 'email')
def _check_duplicate_per_agent(self):
    for record in self:
        if not record.agent_id:
            continue
        
        # Check phone duplicate
        if record.phone:
            domain = [
                ('agent_id', '=', record.agent_id.id),
                ('phone', '=ilike', record.phone.strip()),
                ('state', 'not in', ['lost', 'won']),
                ('id', '!=', record.id),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(
                    f"You already have an active lead with phone {record.phone}. "
                    f"Please edit the existing lead or add a new activity."
                )
        
        # Check email duplicate
        if record.email:
            domain = [
                ('agent_id', '=', record.agent_id.id),
                ('email', '=ilike', record.email.strip().lower()),
                ('state', 'not in', ['lost', 'won']),
                ('id', '!=', record.id),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(
                    f"You already have an active lead with email {record.email}. "
                    f"Please edit the existing lead or add a new activity."
                )
```

#### 2. Budget Validation
```python
@api.constrains('budget_min', 'budget_max')
def _check_budget_range(self):
    for record in self:
        if record.budget_min and record.budget_max:
            if record.budget_min > record.budget_max:
                raise ValidationError("Minimum budget cannot exceed maximum budget.")
```

#### 3. Company Validation (FR-023)
```python
@api.constrains('agent_id', 'company_ids')
def _check_agent_company(self):
    for record in self:
        if record.agent_id and record.company_ids:
            agent_companies = record.agent_id.company_ids
            lead_companies = record.company_ids
            if not (lead_companies & agent_companies):
                raise ValidationError(
                    "Agent must belong to at least one of the lead's companies."
                )
```

#### 4. Lost Reason Required
```python
@api.constrains('state', 'lost_reason')
def _check_lost_reason(self):
    for record in self:
        if record.state == 'lost' and not record.lost_reason:
            raise ValidationError("Lost reason is required when marking lead as lost.")
```

### Computed Fields

```python
# Display name with partner info
@api.depends('name', 'partner_id')
def _compute_display_name(self):
    for record in self:
        if record.partner_id:
            record.display_name = f"{record.name} ({record.partner_id.name})"
        else:
            record.display_name = record.name

# Days in current state (for pipeline metrics)
@api.depends('create_date', 'write_date')
def _compute_days_in_state(self):
    for record in self:
        if record.write_date:
            delta = fields.Datetime.now() - record.write_date
            record.days_in_state = delta.days
        else:
            delta = fields.Datetime.now() - record.create_date
            record.days_in_state = delta.days
```

### Default Values

```python
@api.model
def _default_agent_id(self):
    """Auto-assign current user's agent record (FR-002)"""
    agent = self.env['real.estate.agent'].search([
        ('user_id', '=', self.env.uid)
    ], limit=1)
    return agent.id if agent else False

@api.model
def _default_company_ids(self):
    """Auto-assign user's companies (FR-031)"""
    return self.env.user.estate_company_ids.ids

# Field definitions with defaults
agent_id = fields.Many2one('real.estate.agent', default=_default_agent_id)
company_ids = fields.Many2many('thedevkitchen.estate.company', default=_default_company_ids)
state = fields.Selection(default='new')
active = fields.Boolean(default=True)
```

### Methods

#### Soft Delete Override (FR-018b)
```python
def unlink(self):
    """Prevent hard delete - archive instead"""
    self.write({'active': False})
    return True
```

#### Lead Reopen (FR-018a)
```python
def action_reopen(self):
    """Reopen lost lead"""
    for record in self:
        if record.state != 'lost':
            raise UserError("Only lost leads can be reopened.")
        
        record.write({'state': 'contacted'})
        record.message_post(
            body="Lead reopened and set to Contacted state.",
            subtype_xmlid='mail.mt_note',
        )
```

#### State Change with Logging
```python
def write(self, vals):
    """Override write to log state changes"""
    if 'state' in vals:
        old_state = self.state
        new_state = vals['state']
        
        # Auto-set lost_date
        if new_state == 'lost':
            vals['lost_date'] = fields.Date.today()
        
        # Log state change in chatter
        res = super().write(vals)
        if old_state != new_state:
            self.message_post(
                body=f"State changed from {old_state} to {new_state}",
                subtype_xmlid='mail.mt_note',
            )
        return res
    
    return super().write(vals)
```

## Security Model

### Access Groups (reusing RBAC from branch 005)

- `group_estate_agent`: Individual sales agents
- `group_estate_manager`: Team managers
- `group_estate_director`: Directors (same as manager for leads)
- `group_estate_owner`: Company owners (full access)

### Record Rules

#### Agent Rule (FR-019, FR-020, FR-021)
```xml
<record id="real_estate_lead_agent_rule" model="ir.rule">
    <field name="name">Agent: Own Leads Only</field>
    <field name="model_id" ref="model_real_estate_lead"/>
    <field name="domain_force">[
        ('agent_id.user_id', '=', user.id),
        ('company_ids', 'in', user.estate_company_ids.ids)
    ]</field>
    <field name="groups" eval="[(4, ref('group_estate_agent'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="True"/>
    <field name="perm_unlink" eval="True"/>  <!-- Actually archives due to unlink override -->
</record>
```

#### Manager Rule (FR-024, FR-025, FR-026)
```xml
<record id="real_estate_lead_manager_rule" model="ir.rule">
    <field name="name">Manager: All Company Leads</field>
    <field name="model_id" ref="model_real_estate_lead"/>
    <field name="domain_force">[
        ('company_ids', 'in', user.estate_company_ids.ids)
    ]</field>
    <field name="groups" eval="[(4, ref('group_estate_manager'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="True"/>
    <field name="perm_unlink" eval="True"/>
</record>
```

### Access Rights (ir.model.access.csv)

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_real_estate_lead_agent,real.estate.lead agent,model_real_estate_lead,group_estate_agent,1,1,1,1
access_real_estate_lead_manager,real.estate.lead manager,model_real_estate_lead,group_estate_manager,1,1,1,1
access_real_estate_lead_director,real.estate.lead director,model_real_estate_lead,group_estate_director,1,1,1,1
access_real_estate_lead_owner,real.estate.lead owner,model_real_estate_lead,group_estate_owner,1,1,1,1
```

## Database Schema (PostgreSQL)

```sql
CREATE TABLE real_estate_lead (
    id SERIAL PRIMARY KEY,
    
    -- Core
    name VARCHAR(100) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    state VARCHAR(20) NOT NULL DEFAULT 'new',
    create_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    write_date TIMESTAMP WITHOUT TIME ZONE,
    create_uid INTEGER REFERENCES res_users(id),
    write_uid INTEGER REFERENCES res_users(id),
    
    -- Contact
    partner_id INTEGER REFERENCES res_partner(id),
    phone VARCHAR(20),
    email VARCHAR(120),
    
    -- Ownership
    agent_id INTEGER NOT NULL REFERENCES real_estate_agent(id),
    
    -- Preferences
    budget_min NUMERIC(12,2),
    budget_max NUMERIC(12,2),
    property_type_interest INTEGER REFERENCES real_estate_property_type(id),
    location_preference VARCHAR(200),
    bedrooms_needed INTEGER,
    min_area NUMERIC(10,2),
    max_area NUMERIC(10,2),
    property_interest INTEGER REFERENCES real_estate_property(id),
    
    -- Lifecycle
    first_contact_date DATE,
    expected_closing_date DATE,
    lost_date DATE,
    lost_reason TEXT,
    
    -- Conversion
    converted_property_id INTEGER REFERENCES real_estate_property(id),
    converted_sale_id INTEGER REFERENCES real_estate_sale(id)
);

-- Indexes for performance (FR-045)
CREATE INDEX idx_real_estate_lead_state ON real_estate_lead(state);
CREATE INDEX idx_real_estate_lead_create_date ON real_estate_lead(create_date);
CREATE INDEX idx_real_estate_lead_agent_id ON real_estate_lead(agent_id);  -- Auto by Odoo
CREATE INDEX idx_real_estate_lead_active ON real_estate_lead(active);  -- Auto by Odoo

-- Many2many table for company_ids
CREATE TABLE real_estate_lead_thedevkitchen_estate_company_rel (
    real_estate_lead_id INTEGER NOT NULL REFERENCES real_estate_lead(id) ON DELETE CASCADE,
    thedevkitchen_estate_company_id INTEGER NOT NULL REFERENCES thedevkitchen_estate_company(id) ON DELETE CASCADE,
    PRIMARY KEY (real_estate_lead_id, thedevkitchen_estate_company_id)
);
CREATE INDEX idx_lead_company_rel_lead ON real_estate_lead_thedevkitchen_estate_company_rel(real_estate_lead_id);
CREATE INDEX idx_lead_company_rel_company ON real_estate_lead_thedevkitchen_estate_company_rel(thedevkitchen_estate_company_id);
```

## Views Structure

### List View (FR-034)
- Columns: name, partner_id, agent_id, state, budget_min, budget_max, phone, email, create_date
- Filters: By state, by agent, by date range, archived
- Group by: State, Agent, Create date

### Form View (FR-035)
- Tab 1: General Info (contact, budget, preferences)
- Tab 2: Property Interest (property_interest, converted info)
- Tab 3: Activities (mail.activity.mixin chatter)
- Tab 4: History (mail.thread messages)

### Kanban View (FR-036)
- Grouped by state
- Drag-and-drop to change state
- Cards show: name, phone, budget_min-budget_max, days_in_state

### Calendar View (FR-037)
- Date field: expected_closing_date
- Color by: agent_id
- Shows: name, partner_id, budget

### Dashboard (FR-038)
- Pie chart: Leads by state
- Bar chart: Leads by agent
- KPI tiles: Total leads, Conversion rate, Avg days to convert

---

**Next**: Contract definitions (OpenAPI schemas for REST endpoints)
