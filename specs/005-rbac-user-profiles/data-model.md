# Phase 1: Data Model Design - RBAC User Profiles System

**Date**: 2026-01-20  
**Feature**: [spec.md](spec.md)  
**Research**: [research.md](research.md)  
**Purpose**: Define complete data model for 9 security groups, record rules, and commission split functionality

## Security Groups (res.groups)

### Group Hierarchy

```
base.group_user (Odoo Internal User)
├── group_real_estate_user (Base Real Estate User)
│   ├── group_real_estate_manager (Manager)
│   │   └── group_real_estate_director (Director - inherits Manager)
│   ├── group_real_estate_agent (Agent - inherits User)
│   ├── group_real_estate_receptionist (Receptionist - inherits User)
│   ├── group_real_estate_financial (Financial - inherits User)
│   └── group_real_estate_legal (Legal - inherits User)
├── group_real_estate_owner (Owner - standalone, full access)
└── group_real_estate_prospector (Prospector - standalone, limited)

base.group_portal (Odoo Portal User)
└── group_real_estate_portal_user (Portal User - external clients)
```

### Group Definitions (security/groups.xml)

#### 1. Owner Profile

```xml
<record id="group_real_estate_owner" model="res.groups">
    <field name="name">Real Estate Owner</field>
    <field name="category_id" ref="module_category_real_estate"/>
    <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
    <field name="comment">Company owner with full access: create users, manage all company data, configure integrations. Can assign users to their own companies only.</field>
</record>
```

**Permissions**:
- Full CRUD on all models within assigned companies
- Create/update `res.users` for their companies
- Cannot access other companies' data
- Cannot delete their own account if last owner

---

#### 2. Director Profile

```xml
<record id="group_real_estate_director" model="res.groups">
    <field name="name">Real Estate Director</field>
    <field name="category_id" ref="module_category_real_estate"/>
    <field name="implied_ids" eval="[(4, ref('group_real_estate_manager'))]"/>
    <field name="comment">Executive with all Manager permissions plus access to financial reports, dashboards, and business intelligence.</field>
</record>
```

**Permissions**:
- All Manager permissions (inherited)
- Access to executive dashboards
- View detailed financial reports including commission breakdowns
- No user creation (only owners)

---

#### 3. Manager Profile (EXISTING - Modified)

```xml
<record id="group_real_estate_manager" model="res.groups">
    <field name="name">Real Estate Manager</field>
    <field name="category_id" ref="module_category_real_estate"/>
    <field name="implied_ids" eval="[(4, ref('group_real_estate_user'))]"/>
    <field name="comment">Operational manager: CRUD on properties, agents, contracts, leads. Can reassign leads, generate reports. Cannot create users.</field>
</record>
```

**Permissions**:
- CRUD on properties, agents, contracts, leads (company-scoped)
- Assign/reassign leads to agents
- Generate performance reports
- Edit `prospector_id` field on properties
- No user creation/deletion

---

#### 4. User Profile (EXISTING - Base Group)

```xml
<record id="group_real_estate_user" model="res.groups">
    <field name="name">Real Estate User</field>
    <field name="category_id" ref="module_category_real_estate"/>
    <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
    <field name="comment">Base group for internal real estate users. Provides foundational access to company data.</field>
</record>
```

**Permissions**:
- Read access to most company data
- Limited write access (inherited by specialized profiles)
- Base for other operational profiles

---

#### 5. Agent Profile (EXISTING - Modified)

```xml
<record id="group_real_estate_agent" model="res.groups">
    <field name="name">Real Estate Agent</field>
    <field name="category_id" ref="module_category_real_estate"/>
    <field name="implied_ids" eval="[(4, ref('group_real_estate_user'))]"/>
    <field name="comment">Real estate agent/broker: CRUD on own properties and leads. Can create proposals. Cannot modify commissions or change clients on proposals.</field>
</record>
```

**Permissions**:
- CRUD on properties where `agent_id.user_id = user.id` OR `assignment_ids.agent_id.user_id = user.id`
- CRUD on own leads
- Create proposals (cannot change partner_id)
- View property prices
- Cannot edit commission amounts
- Cannot edit `prospector_id` field

---

#### 6. Prospector Profile (NEW)

```xml
<record id="group_real_estate_prospector" model="res.groups">
    <field name="name">Real Estate Prospector</field>
    <field name="category_id" ref="module_category_real_estate"/>
    <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
    <field name="comment">Property hunter: Can create properties (auto-assigned as prospector). Earns commission split with selling agent (30/70 default). Cannot manage leads or sales.</field>
</record>
```

**Permissions**:
- Create properties (auto-sets `prospector_id = current_user.agent_id`)
- Read properties where `prospector_id.user_id = user.id`
- Cannot edit properties after creation (read-only except create)
- Cannot access leads or sales modules
- Cannot edit commission rules

---

#### 7. Receptionist Profile (NEW)

```xml
<record id="group_real_estate_receptionist" model="res.groups">
    <field name="name">Real Estate Receptionist</field>
    <field name="category_id" ref="module_category_real_estate"/>
    <field name="implied_ids" eval="[(4, ref('group_real_estate_user'))]"/>
    <field name="comment">Administrative staff: CRUD on lease contracts and key management. Read-only access to properties. Cannot modify commissions or agent assignments.</field>
</record>
```

**Permissions**:
- CRUD on `real.estate.lease` (contracts)
- CRUD on `real.estate.key` (key management)
- Read-only on `real.estate.property`
- Cannot edit property details, prices, or agent assignments
- Cannot modify commissions

---

#### 8. Financial Profile (NEW)

```xml
<record id="group_real_estate_financial" model="res.groups">
    <field name="name">Real Estate Financial</field>
    <field name="category_id" ref="module_category_real_estate"/>
    <field name="implied_ids" eval="[(4, ref('group_real_estate_user'))]"/>
    <field name="comment">Financial team: CRUD on commissions. Can generate financial reports, mark commissions as paid. Read-only access to sales/leases.</field>
</record>
```

**Permissions**:
- CRUD on `real.estate.commission.transaction`
- Read-only on `real.estate.sale`, `real.estate.lease`, `real.estate.property`
- Generate commission reports (by agent, date range, status)
- Mark commissions as paid
- Cannot edit properties or leads

---

#### 9. Legal Profile (NEW)

```xml
<record id="group_real_estate_legal" model="res.groups">
    <field name="name">Real Estate Legal</field>
    <field name="category_id" ref="module_category_real_estate"/>
    <field name="implied_ids" eval="[(4, ref('group_real_estate_user'))]"/>
    <field name="comment">Legal team: Read-only access to all contracts. Can add legal opinions/notes. Cannot modify financial terms or property details.</field>
</record>
```

**Permissions**:
- Read-only on `real.estate.lease`, `real.estate.sale`, `real.estate.property`
- Can add notes/messages to contracts (mail.thread)
- Cannot edit contract values, commissions, or prices
- Filter contracts by status for review workflows

---

#### 10. Portal User Profile (EXISTING - Unchanged)

```xml
<record id="group_real_estate_portal_user" model="res.groups">
    <field name="name">Real Estate Portal User</field>
    <field name="category_id" ref="module_category_real_estate"/>
    <field name="implied_ids" eval="[(4, ref('base.group_portal'))]"/>
    <field name="comment">External client/tenant: View own contracts, upload documents. Cannot see other clients' data.</field>
</record>
```

**Permissions**:
- Read on records where `partner_id = user.partner_id`
- Upload documents to own contracts
- Cannot see other clients' data
- Cannot see agent commission information

---

## Model Changes

### 0. Event Bus Infrastructure (NEW - ADR-020 + ADR-021)

**Purpose**: Implementar Observer Pattern para desacoplar lógica de negócio

#### Event Bus (Abstract Model)

```python
# models/event_bus.py

class EventBus(models.AbstractModel):
    _name = 'quicksol.event.bus'
    _description = 'Event Bus for decoupled business logic (ADR-020)'
    
    @api.model
    def emit(self, event_name, data):
        """
        Emite um evento para todos os observers registrados.
        
        Args:
            event_name (str): Nome do evento (ex: 'property.created')
            data (dict): Dados do evento
            
        Reference: ADR-020 - Observer Pattern
        """
        _logger.debug(f"EventBus: Emitting {event_name} with data keys: {data.keys()}")
        
        observers = self._get_observers(event_name)
        for observer in observers:
            try:
                observer.handle(event_name, data)
            except Exception as e:
                _logger.error(
                    f"Observer {observer._name} failed for event {event_name}: {e}",
                    exc_info=True
                )
                raise
    
    @api.model
    def _get_observers(self, event_name):
        """Retorna lista de observers registrados para o evento."""
        observers = []
        
        for model_name in self.env.registry.keys():
            if not model_name.startswith('quicksol.observer.'):
                continue
            
            observer = self.env[model_name]
            if hasattr(observer, 'can_handle') and observer.can_handle(event_name):
                observers.append(observer)
        
        return observers
```

#### Abstract Observer Base Class

```python
# models/observers/abstract_observer.py

class AbstractObserver(models.AbstractModel):
    _name = 'quicksol.abstract.observer'
    _description = 'Base class for all observers (ADR-020)'
    
    _observe_events = []
    
    @api.model
    def handle(self, event_name, data):
        """
        Método chamado quando evento é emitido.
        Subclasses devem implementar.
        
        Reference: ADR-020 - Observer Pattern
        """
        raise NotImplementedError(
            f"{self._name} must implement handle() method"
        )
    
    @api.model
    def can_handle(self, event_name):
        """Verifica se observer está registrado para este evento."""
        return event_name in self._observe_events
```

#### Observers Implementados

**1. ProspectorAutoAssignObserver** (implementado em Model Changes → 1. real.estate.property)

**2. CommissionSplitObserver**

```python
# models/observers/commission_split_observer.py

class CommissionSplitObserver(models.AbstractModel):
    _name = 'quicksol.observer.commission.split'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Creates commission transactions when split is calculated'
    
    _observe_events = ['commission.split.calculated']
    
    @api.model
    def handle(self, event_name, data):
        """
        ADR-019: Cria transações de comissão separadas para prospector e agente.
        ADR-013: Usa regras de comissão configuráveis.
        """
        split = data['split']
        property_id = data['property_id']
        
        # Busca venda/aluguel associado (assumindo que event vem de sale.completed)
        sale = self.env['real.estate.sale'].search([
            ('property_id', '=', property_id),
            ('state', '=', 'completed')
        ], limit=1)
        
        if not sale:
            return
        
        CommissionTransaction = self.env['real.estate.commission.transaction']
        
        # Comissão do prospector (30%)
        if split['prospector_commission'] > 0:
            CommissionTransaction.create({
                'sale_id': sale.id,
                'agent_id': data['prospector_id'],
                'amount': split['prospector_commission'],
                'type': 'prospector',
                'status': 'pending'
            })
        
        # Comissão do agente vendedor (70%)
        CommissionTransaction.create({
            'sale_id': sale.id,
            'agent_id': sale.agent_id.id,
            'amount': split['agent_commission'],
            'type': 'agent',
            'status': 'pending'
        })
```

**3. UserCompanyValidatorObserver** (implementado em User Model Rules → Special Case)

**4. SecurityGroupAuditObserver** (opcional - compliance/LGPD)

```python
# models/observers/security_group_audit_observer.py

class SecurityGroupAuditObserver(models.AbstractModel):
    _name = 'quicksol.observer.security.group.audit'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Logs security group changes for compliance (LGPD)'
    
    _observe_events = ['user.created', 'user.updated']
    
    @api.model
    def handle(self, event_name, data):
        """ADR-019: Audit trail for security group assignments."""
        user_ids = data.get('user_ids', [data.get('user_id')])
        
        for user_id in user_ids:
            user = self.env['res.users'].browse(user_id)
            
            _logger.info(
                f"Security Audit: User {user.login} (ID: {user.id}) "
                f"has groups: {user.groups_id.mapped('name')} "
                f"Changed by: {self.env.user.login}"
            )
            
            # Opcional: criar registro em tabela de auditoria
            # self.env['quicksol.audit.log'].create({...})
```

---

### 1. real.estate.property (MODIFIED)

**New Field: prospector_id**

```python
# models/property.py

prospector_id = fields.Many2one(
    'real.estate.agent',
    string='Prospector',
    tracking=True,
    index=True,
    help='Agent who prospected/found this property. Earns commission split with selling agent.',
    groups='quicksol_estate.group_real_estate_manager,quicksol_estate.group_real_estate_owner'
)
```

**Field Characteristics**:
- **Type**: Many2one to `real.estate.agent`
- **Visibility**: Only managers and owners can edit (field-level security via `groups` attribute)
- **Auto-populate**: When prospector creates property, auto-set `prospector_id = env.user.agent_id`
- **Tracking**: Audit log enabled
- **Indexed**: For faster queries filtering by prospector
- **Optional**: Can be null (not all properties have prospectors)

**Event-Driven Logic (ADR-020: Observer Pattern)**:
```python
@api.model_create_multi
def create(self, vals_list):
    """
    Emite evento para observers procesarem lógica de negócio.
    ADR-020: Desacopla auto-populate usando Observer pattern.
    """
    for vals in vals_list:
        self.env['quicksol.event.bus'].emit('property.before_create', {
            'vals': vals,
            'model': self._name
        })
    
    properties = super().create(vals_list)
    
    for prop in properties:
        self.env['quicksol.event.bus'].emit('property.created', {
            'property_id': prop.id,
            'user_id': self.env.user.id
        })
    
    return properties
```

**Observer: ProspectorAutoAssignObserver**
```python
# models/observers/prospector_auto_assign_observer.py

class ProspectorAutoAssignObserver(models.AbstractModel):
    _name = 'quicksol.observer.prospector.auto.assign'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Auto-assigns prospector when property is created'
    
    _observe_events = ['property.before_create']
    
    @api.model
    def handle(self, event_name, data):
        """ADR-019: Auto-populate prospector_id for prospector users."""
        if not self.env.user.has_group('quicksol_estate.group_real_estate_prospector'):
            return
        
        agent = self.env['real.estate.agent'].search([
            ('user_id', '=', self.env.user.id)
        ], limit=1)
        
        if agent and 'vals' in data:
            data['vals']['prospector_id'] = agent.id
```

---

### 2. real.estate.commission.rule (MODIFIED)

**New Method: calculate_split_commission**

```python
# models/commission_rule.py

def calculate_split_commission(self, property_record, transaction_amount):
    """
    Calculate commission split between prospector and selling agent.
    
    Args:
        property_record: real.estate.property record
        transaction_amount: Sale/rental amount (Decimal/float)
    
    Returns:
        dict: {
            'prospector_commission': float,
            'agent_commission': float,
            'total_commission': float,
            'prospector_percentage': float,
            'agent_percentage': float
        }
    """
    if self.structure_type == 'percentage':
        total_commission = transaction_amount * (self.percentage / 100.0)
    else:
        total_commission = self.fixed_amount
    
    if not property_record.prospector_id:
        return {
            'prospector_commission': 0.0,
            'agent_commission': total_commission,
            'total_commission': total_commission,
            'prospector_percentage': 0.0,
            'agent_percentage': 100.0
        }
    
    prospector_pct = self._get_prospector_split_percentage()
    agent_pct = 1.0 - prospector_pct
    
    split_result = {
        'prospector_commission': total_commission * prospector_pct,
        'agent_commission': total_commission * agent_pct,
        'total_commission': total_commission,
        'prospector_percentage': prospector_pct * 100.0,
        'agent_percentage': agent_pct * 100.0
    }
    
    # ADR-020: Emit event for observers (logging, notifications, etc.)
    self.env['quicksol.event.bus'].emit('commission.split.calculated', {
        'property_id': property_record.id,
        'prospector_id': property_record.prospector_id.id,
        'split': split_result
    })
    
    return split_result

def _get_prospector_split_percentage(self):
    """Get prospector commission split percentage from config (default 30%)."""
    return float(self.env['ir.config_parameter'].sudo().get_param(
        'quicksol_estate.prospector_commission_percentage',
        default='0.30'
    ))
```

**System Parameter**:
```xml
<!-- data/config_params.xml -->
<odoo>
    <data noupdate="1">
        <record id="param_prospector_commission_pct" model="ir.config_parameter">
            <field name="key">quicksol_estate.prospector_commission_percentage</field>
            <field name="value">0.30</field>
        </record>
    </data>
</odoo>
```

---

## Access Control Lists (security/ir.model.access.csv)

**Format**: `id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink`

### Property Model

```csv
access_property_owner,access_property_owner,model_real_estate_property,group_real_estate_owner,1,1,1,1
access_property_director,access_property_director,model_real_estate_property,group_real_estate_director,1,1,1,1
access_property_manager,access_property_manager,model_real_estate_property,group_real_estate_manager,1,1,1,1
access_property_agent,access_property_agent,model_real_estate_property,group_real_estate_agent,1,1,1,0
access_property_prospector,access_property_prospector,model_real_estate_property,group_real_estate_prospector,1,0,1,0
access_property_receptionist,access_property_receptionist,model_real_estate_property,group_real_estate_receptionist,1,0,0,0
access_property_financial,access_property_financial,model_real_estate_property,group_real_estate_financial,1,0,0,0
access_property_legal,access_property_legal,model_real_estate_property,group_real_estate_legal,1,0,0,0
access_property_portal,access_property_portal,model_real_estate_property,group_real_estate_portal_user,1,0,0,0
```

**Legend**:
- Owner/Director/Manager: Full CRUD (1,1,1,1)
- Agent: Read, Write, Create (no delete) (1,1,1,0)
- Prospector: Read, Create only (1,0,1,0)
- Receptionist/Financial/Legal: Read only (1,0,0,0)
- Portal: Read only (1,0,0,0)

### Agent Model

```csv
access_agent_owner,access_agent_owner,model_real_estate_agent,group_real_estate_owner,1,1,1,1
access_agent_director,access_agent_director,model_real_estate_agent,group_real_estate_director,1,1,1,1
access_agent_manager,access_agent_manager,model_real_estate_agent,group_real_estate_manager,1,1,1,1
access_agent_agent,access_agent_agent,model_real_estate_agent,group_real_estate_agent,1,1,0,0
access_agent_prospector,access_agent_prospector,model_real_estate_agent,group_real_estate_prospector,1,0,0,0
access_agent_receptionist,access_agent_receptionist,model_real_estate_agent,group_real_estate_receptionist,1,0,0,0
access_agent_financial,access_agent_financial,model_real_estate_agent,group_real_estate_financial,1,0,0,0
access_agent_legal,access_agent_legal,model_real_estate_agent,group_real_estate_legal,1,0,0,0
```

### Lease/Contract Model

```csv
access_lease_owner,access_lease_owner,model_real_estate_lease,group_real_estate_owner,1,1,1,1
access_lease_director,access_lease_director,model_real_estate_lease,group_real_estate_director,1,1,1,1
access_lease_manager,access_lease_manager,model_real_estate_lease,group_real_estate_manager,1,1,1,1
access_lease_agent,access_lease_agent,model_real_estate_lease,group_real_estate_agent,1,1,1,0
access_lease_receptionist,access_lease_receptionist,model_real_estate_lease,group_real_estate_receptionist,1,1,1,1
access_lease_financial,access_lease_financial,model_real_estate_lease,group_real_estate_financial,1,0,0,0
access_lease_legal,access_lease_legal,model_real_estate_lease,group_real_estate_legal,1,0,0,0
access_lease_portal,access_lease_portal,model_real_estate_lease,group_real_estate_portal_user,1,0,0,0
```

### Commission Transaction Model

```csv
access_commission_transaction_owner,access_commission_transaction_owner,model_real_estate_commission_transaction,group_real_estate_owner,1,1,1,1
access_commission_transaction_director,access_commission_transaction_director,model_real_estate_commission_transaction,group_real_estate_director,1,1,1,1
access_commission_transaction_manager,access_commission_transaction_manager,model_real_estate_commission_transaction,group_real_estate_manager,1,1,1,1
access_commission_transaction_financial,access_commission_transaction_financial,model_real_estate_commission_transaction,group_real_estate_financial,1,1,1,1
access_commission_transaction_agent,access_commission_transaction_agent,model_real_estate_commission_transaction,group_real_estate_agent,1,0,0,0
```

**Total ACL Entries**: ~100 (10 models × 9 profiles + variations)

---

## Record Rules (security/record_rules.xml)

### Strategy

1. **Multi-Company Base Rule** - Applies to User, Manager, Director, Owner
2. **Agent-Specific Rule** - Filters to own records
3. **Prospector-Specific Rule** - Filters to prospected properties
4. **Portal-Specific Rule** - Filters to own contracts (partner_id)
5. **Receptionist/Financial/Legal** - Inherit multi-company base (no additional filters)

---

### Property Model Rules

#### Rule 1: Owner/Director/Manager - All Company Properties

```xml
<record id="rule_property_manager_all_company" model="ir.rule">
    <field name="name">Property: Owner/Director/Manager - All Company</field>
    <field name="model_id" ref="model_real_estate_property"/>
    <field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_owner')), (4, ref('group_real_estate_director')), (4, ref('group_real_estate_manager')), (4, ref('group_real_estate_user'))]"/>
</record>
```

#### Rule 2: Agent - Own Properties Only

```xml
<record id="rule_property_agent_own" model="ir.rule">
    <field name="name">Property: Agent - Own Properties</field>
    <field name="model_id" ref="model_real_estate_property"/>
    <field name="domain_force">[
        '|',
            ('agent_id.user_id', '=', user.id),
            ('assignment_ids.agent_id.user_id', '=', user.id),
        ('company_ids', 'in', user.estate_company_ids.ids)
    ]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_agent'))]"/>
</record>
```

**Logic**: Agent sees properties where they are the primary agent OR assigned via assignment records. Must also be in their companies.

#### Rule 3: Prospector - Prospected Properties Only

```xml
<record id="rule_property_prospector_own" model="ir.rule">
    <field name="name">Property: Prospector - Prospected Properties Only</field>
    <field name="model_id" ref="model_real_estate_property"/>
    <field name="domain_force">[
        ('prospector_id.user_id', '=', user.id),
        ('company_ids', 'in', user.estate_company_ids.ids)
    ]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_prospector'))]"/>
</record>
```

#### Rule 4: Receptionist/Financial/Legal - Read-Only All Company

```xml
<record id="rule_property_support_staff_read" model="ir.rule">
    <field name="name">Property: Support Staff - Read All Company</field>
    <field name="model_id" ref="model_real_estate_property"/>
    <field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_receptionist')), (4, ref('group_real_estate_financial')), (4, ref('group_real_estate_legal'))]"/>
</record>
```

---

### Agent Model Rules

#### Rule 1: Manager/Owner - All Company Agents

```xml
<record id="rule_agent_manager_all_company" model="ir.rule">
    <field name="name">Agent: Manager/Owner - All Company</field>
    <field name="model_id" ref="model_real_estate_agent"/>
    <field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_owner')), (4, ref('group_real_estate_director')), (4, ref('group_real_estate_manager'))]"/>
</record>
```

#### Rule 2: Agent - Own Record Only

```xml
<record id="rule_agent_own_record" model="ir.rule">
    <field name="name">Agent: Own Record Only</field>
    <field name="model_id" ref="model_real_estate_agent"/>
    <field name="domain_force">[('user_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_agent'))]"/>
</record>
```

---

### Lease/Contract Model Rules

#### Rule 1: Manager/Owner - All Company Leases

```xml
<record id="rule_lease_manager_all_company" model="ir.rule">
    <field name="name">Lease: Manager/Owner - All Company</field>
    <field name="model_id" ref="model_real_estate_lease"/>
    <field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_owner')), (4, ref('group_real_estate_director')), (4, ref('group_real_estate_manager')), (4, ref('group_real_estate_user'))]"/>
</record>
```

#### Rule 2: Agent - Own Leases (via Property)

```xml
<record id="rule_lease_agent_own" model="ir.rule">
    <field name="name">Lease: Agent - Own Leases</field>
    <field name="model_id" ref="model_real_estate_lease"/>
    <field name="domain_force">[
        ('property_id.agent_id.user_id', '=', user.id),
        ('company_ids', 'in', user.estate_company_ids.ids)
    ]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_agent'))]"/>
</record>
```

#### Rule 3: Receptionist - All Company Leases (CRUD)

```xml
<record id="rule_lease_receptionist_all" model="ir.rule">
    <field name="name">Lease: Receptionist - All Company</field>
    <field name="model_id" ref="model_real_estate_lease"/>
    <field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_receptionist'))]"/>
</record>
```

#### Rule 4: Legal/Financial - Read-Only All Company

```xml
<record id="rule_lease_legal_financial_read" model="ir.rule">
    <field name="name">Lease: Legal/Financial - Read All Company</field>
    <field name="model_id" ref="model_real_estate_lease"/>
    <field name="domain_force">[('company_ids', 'in', user.estate_company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_legal')), (4, ref('group_real_estate_financial'))]"/>
</record>
```

#### Rule 5: Portal User - Own Leases Only

```xml
<record id="rule_lease_portal_own" model="ir.rule">
    <field name="name">Lease: Portal User - Own Contracts</field>
    <field name="model_id" ref="model_real_estate_lease"/>
    <field name="domain_force">[('partner_id', '=', user.partner_id.id)]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_portal_user'))]"/>
</record>
```

---

### Commission Transaction Model Rules

#### Rule 1: Manager/Owner - All Company Commissions

```xml
<record id="rule_commission_manager_all" model="ir.rule">
    <field name="name">Commission: Manager/Owner - All Company</field>
    <field name="model_id" ref="model_real_estate_commission_transaction"/>
    <field name="domain_force">[('company_id', 'in', user.estate_company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_owner')), (4, ref('group_real_estate_director')), (4, ref('group_real_estate_manager'))]"/>
</record>
```

#### Rule 2: Financial - All Company Commissions (CRUD)

```xml
<record id="rule_commission_financial_all" model="ir.rule">
    <field name="name">Commission: Financial - All Company</field>
    <field name="model_id" ref="model_real_estate_commission_transaction"/>
    <field name="domain_force">[('company_id', 'in', user.estate_company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_financial'))]"/>
</record>
```

#### Rule 3: Agent - Own Commissions (Read-Only)

```xml
<record id="rule_commission_agent_own_read" model="ir.rule">
    <field name="name">Commission: Agent - Own Commissions Read</field>
    <field name="model_id" ref="model_real_estate_commission_transaction"/>
    <field name="domain_force">[
        ('agent_id.user_id', '=', user.id),
        ('company_id', 'in', user.estate_company_ids.ids)
    ]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_agent'))]"/>
</record>
```

---

### User Model Rules (Special Case)

#### Rule: Owner Can Create/Edit Users for Their Companies

**Note**: Odoo's user management requires special handling. We use `ir.rule` for filtering but also need to override create/write methods.

```python
# models/res_users.py

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        ADR-020: Emit events for observers to validate/process.
        Desacopla validação usando Observer pattern.
        """
        for vals in vals_list:
            self.env['quicksol.event.bus'].emit('user.before_create', {
                'vals': vals,
                'model': self._name
            })
        
        users = super().create(vals_list)
        
        for user in users:
            self.env['quicksol.event.bus'].emit('user.created', {
                'user_id': user.id
            })
        
        return users
    
    def write(self, vals):
        """
        ADR-020: Emit events for observers to validate before write.
        """
        self.env['quicksol.event.bus'].emit('user.before_write', {
            'vals': vals,
            'user_ids': self.ids
        })
        
        result = super().write(vals)
        
        self.env['quicksol.event.bus'].emit('user.updated', {
            'user_ids': self.ids
        })
        
        return result
```

**Observer: UserCompanyValidatorObserver**
```python
# models/observers/user_company_validator_observer.py

class UserCompanyValidatorObserver(models.AbstractModel):
    _name = 'quicksol.observer.user.company.validator'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Validates owner can only assign users to their companies'
    
    _observe_events = ['user.before_create', 'user.before_write']
    
    @api.model
    def handle(self, event_name, data):
        """
        ADR-019: Owners can only create users for their companies.
        ADR-008: Multi-tenancy isolation enforcement.
        """
        if not self.env.user.has_group('quicksol_estate.group_real_estate_owner'):
            return
        
        vals = data.get('vals', {})
        if 'estate_company_ids' not in vals:
            return
        
        user_companies = set(self.env.user.estate_company_ids.ids)
        new_user_companies = set(vals['estate_company_ids'][0][2])
        
        if not new_user_companies.issubset(user_companies):
            raise AccessError(
                "Você só pode atribuir usuários às suas próprias empresas. "
                "ADR-019: Multi-tenancy isolation."
            )
```

**Record Rule**:
```xml
<record id="rule_user_owner_company_users" model="ir.rule">
    <field name="name">User: Owner - Manage Own Company Users</field>
    <field name="model_id" ref="base.model_res_users"/>
    <field name="domain_force">[('estate_company_ids', 'in', user.estate_company_ids.ids)]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_owner'))]"/>
</record>
```

---

## Total Record Rules Count

| Model | Rules | Notes |
|-------|-------|-------|
| real.estate.property | 4 | Manager, Agent, Prospector, Support Staff |
| real.estate.agent | 2 | Manager, Agent own |
| real.estate.lease | 5 | Manager, Agent, Receptionist, Legal/Financial, Portal |
| real.estate.sale | 4 | Manager, Agent, Financial read, Portal |
| real.estate.commission.transaction | 3 | Manager, Financial, Agent read |
| real.estate.commission.rule | 2 | Manager, Agent own (existing) |
| real.estate.assignment | 2 | Manager, Agent own (existing) |
| res.users | 1 | Owner company restriction |
| **TOTAL** | **23+** | Minimum; may add more for edge cases |

---

## Migration Strategy

### Version Bump

**Current**: `18.0.1.x.x`  
**New**: `18.0.2.0.0` (minor version bump due to data model changes)

### Migration Scripts

#### pre-migrate.py

```python
# migrations/18.0.2.0.0/pre-migrate.py

def migrate(cr, version):
    """Backup current group assignments before restructuring."""
    # Create backup table
    cr.execute("""
        CREATE TABLE IF NOT EXISTS res_groups_users_backup_rbac (
            user_id INTEGER,
            group_id INTEGER,
            backup_date TIMESTAMP DEFAULT NOW()
        );
    """)
    
    # Backup current assignments
    cr.execute("""
        INSERT INTO res_groups_users_backup_rbac (user_id, group_id)
        SELECT uid, gid FROM res_groups_users_rel
        WHERE gid IN (
            SELECT id FROM res_groups 
            WHERE name LIKE 'Real Estate%'
        );
    """)
```

#### post-migrate.py

```python
# migrations/18.0.2.0.0/post-migrate.py

def migrate(cr, version):
    """Add prospector_id field to properties and create new groups."""
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # 1. Add prospector_id column
    cr.execute("""
        ALTER TABLE real_estate_property
        ADD COLUMN IF NOT EXISTS prospector_id INTEGER
        REFERENCES real_estate_agent(id) ON DELETE SET NULL;
    """)
    
    # 2. Create index for performance
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_property_prospector
        ON real_estate_property(prospector_id)
        WHERE prospector_id IS NOT NULL;
    """)
    
    # 3. Load new groups (will be loaded from groups.xml automatically)
    # But ensure they're available before assigning users
    
    # 4. Migrate existing users to new group structure
    # (Manual step - admin must reassign users to appropriate new groups)
    # No automatic migration as business must decide each user's role
```

---

## Data Model Summary

### New Infrastructure (ADR-020: Observer Pattern)
- EventBus (`quicksol.event.bus`) - Central event dispatcher
- AbstractObserver (`quicksol.abstract.observer`) - Base class for all observers

### New Observers: 4
- `quicksol.observer.prospector.auto.assign` - Auto-assigns prospector_id
- `quicksol.observer.commission.split` - Creates commission transactions
- `quicksol.observer.user.company.validator` - Validates multi-tenancy isolation
- `quicksol.observer.security.group.audit` - Logs security changes (LGPD compliance)

### New Groups: 5
- group_real_estate_owner
- group_real_estate_director
- group_real_estate_prospector
- group_real_estate_receptionist
- group_real_estate_financial
- group_real_estate_legal

### Modified Groups: 4 (Updated descriptions/permissions)
- group_real_estate_manager
- group_real_estate_user
- group_real_estate_agent
- group_real_estate_portal_user

### New Fields: 1
- `prospector_id` on `real.estate.property`

### New Methods: 2
- `calculate_split_commission()` on `real.estate.commission.rule`
- `create()` override on `res.users` for owner validation

### New ACL Entries: ~100
- 10 models × 9 profiles with varying CRUD permissions

### New Record Rules: ~23
- Comprehensive coverage of property, agent, lease, sale, commission models

### New System Parameters: 1
- `quicksol_estate.prospector_commission_percentage` (default: 0.30)

---

## Next Steps → Phase 1: Contracts & Quickstart

Since this is a **backend security feature with no API changes**, the `contracts/` directory will not be needed.

**Next Deliverable**: [quickstart.md](quickstart.md) - Developer implementation guide with step-by-step instructions for:
1. Implementing security groups
2. Writing record rules
3. Adding prospector_id field
4. Testing RBAC functionality
5. Deployment checklist
