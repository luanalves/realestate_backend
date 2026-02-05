# Symbols and Conventions - Símbolos e Convenções de Nomenclatura

## Model Name (Nome do Modelo)

Usa notação de ponto, prefixado pelo nome do módulo.

### Regras

1. **Odoo Model (models.Model):** Use **forma singular**
   ```python
   class ResPartner(models.Model):
       _name = 'res.partner'  # ✅ Singular
       # ❌ Evite: 'res.partners'
   ```

2. **Odoo Transient (Wizard):** Use `<base_model>.<action>`
   ```python
   class AccountInvoiceMake(models.TransientModel):
       _name = 'account.invoice.make'
       # Formato: <related_base_model>.<action>
   ```
   
   **Evite a palavra "wizard":**
   - ✅ `project.task.delegate.batch`
   - ❌ `project.task.wizard.delegate`

3. **Report Model (SQL View):** Use `<base_model>.report.<action>`
   ```python
   class SaleReport(models.Model):
       _name = 'sale.report'
       _auto = False
       # Formato: <related_base_model>.report.<action>
   ```

### Exemplos

| Tipo | Padrão | Exemplo |
|------|--------|---------|
| **Model** | `module.entity` | `sale.order`, `res.partner` |
| **Transient** | `base_model.action` | `account.invoice.make`, `project.task.delegate.batch` |
| **Report** | `base_model.report.action` | `sale.report`, `account.invoice.report` |

## Python Class (Classe Python)

Use **PascalCase** (Object-Oriented style):

```python
class AccountInvoice(models.Model):
    _name = 'account.invoice'
    ...

class SaleOrder(models.Model):
    _name = 'sale.order'
    ...

class ResPartner(models.Model):
    _name = 'res.partner'
    ...
```

## Variable Name (Nome de Variável)

### Regras

1. **PascalCase para variáveis de modelo:**
   ```python
   Partner = self.env['res.partner']
   SaleOrder = self.env['sale.order']
   ```

2. **underscore_lowercase para variáveis comuns:**
   ```python
   partner_name = 'John Doe'
   order_total = 1500.00
   is_validated = True
   ```

3. **Sufixo `_id` ou `_ids` para IDs de registros:**
   ```python
   # ✅ Correto - ID do partner
   partner_id = partners[0].id
   
   # ✅ Correto - Lista de IDs
   partner_ids = partners.ids
   
   # ❌ Errado - Não use partner_id para o record
   partner_id = self.env['res.partner'].browse(1)  # Deveria ser 'partner'
   ```

### Exemplo Completo

```python
# Variável de modelo (PascalCase)
Partner = self.env['res.partner']

# Recordset
partners = Partner.browse(ids)

# ID individual
partner_id = partners[0].id

# Lista de IDs
partner_ids = partners.ids

# Variáveis comuns (underscore_lowercase)
partner_name = partners[0].name
total_amount = 1500.00
is_active = True
```

## Field Names (Nomes de Campos)

### Many2One e One2Many

- **Many2One:** Sufixo `_id`
  ```python
  partner_id = fields.Many2one('res.partner', string='Customer')
  user_id = fields.Many2one('res.users', string='Salesperson')
  company_id = fields.Many2one('res.company', string='Company')
  ```

- **One2Many:** Sufixo `_ids`
  ```python
  sale_order_line_ids = fields.One2many('sale.order.line', 'order_id', string='Order Lines')
  invoice_ids = fields.One2many('account.invoice', 'order_id', string='Invoices')
  ```

### Many2Many

**SEMPRE** use sufixo `_ids`:

```python
tag_ids = fields.Many2many('product.tag', string='Tags')
category_ids = fields.Many2many('product.category', string='Categories')
user_ids = fields.Many2many('res.users', string='Followers')
```

## Method Conventions (Convenções de Métodos)

### Padrões de Nomenclatura

| Tipo de Método | Padrão | Exemplo |
|----------------|--------|---------|
| **Compute** | `_compute_<field_name>` | `_compute_total_price` |
| **Search** | `_search_<field_name>` | `_search_is_company` |
| **Default** | `_default_<field_name>` | `_default_date_order` |
| **Selection** | `_selection_<field_name>` | `_selection_state` |
| **Onchange** | `_onchange_<field_name>` | `_onchange_partner_id` |
| **Constraint** | `_check_<constraint_name>` | `_check_date_validity` |
| **Action** | `action_<action_name>` | `action_confirm`, `action_cancel` |

### Exemplos Detalhados

#### Compute Method
```python
total_price = fields.Float(compute='_compute_total_price')

@api.depends('line_ids.price_subtotal')
def _compute_total_price(self):
    for record in self:
        record.total_price = sum(record.line_ids.mapped('price_subtotal'))
```

#### Search Method
```python
is_company = fields.Boolean(search='_search_is_company')

def _search_is_company(self, operator, value):
    return [('company_type', '=', 'company' if value else 'person')]
```

#### Default Method
```python
date_order = fields.Date(default=lambda self: self._default_date_order())

def _default_date_order(self):
    return fields.Date.context_today(self)
```

#### Selection Method
```python
state = fields.Selection(selection='_selection_state')

@api.model
def _selection_state(self):
    return [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ]
```

#### Onchange Method
```python
@api.onchange('partner_id')
def _onchange_partner_id(self):
    if self.partner_id:
        self.payment_term_id = self.partner_id.property_payment_term_id
```

#### Constraint Method
```python
@api.constrains('date_start', 'date_end')
def _check_date_validity(self):
    for record in self:
        if record.date_start > record.date_end:
            raise ValidationError("Start date must be before end date!")
```

#### Action Method
```python
def action_confirm(self):
    self.ensure_one()  # Sempre adicione em action methods
    self.state = 'confirmed'
    return True

def action_cancel(self):
    self.ensure_one()
    self.state = 'cancelled'
    return True
```

## Model Attribute Order (Ordem dos Atributos no Modelo)

Organize os atributos da classe na seguinte ordem:

### 1. Private Attributes
```python
class SaleOrder(models.Model):
    _name = 'sale.order'
    _description = 'Sales Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_order desc, id desc'
```

### 2. Default Methods
```python
    def _default_date_order(self):
        return fields.Date.context_today(self)
```

### 3. Field Declarations
```python
    # Campos básicos
    name = fields.Char(string='Order Reference', required=True)
    date_order = fields.Date(string='Order Date', default=_default_date_order)
    
    # Campos relacionais
    partner_id = fields.Many2one('res.partner', string='Customer')
    order_line_ids = fields.One2many('sale.order.line', 'order_id', string='Order Lines')
    
    # Campos computados
    total_amount = fields.Float(string='Total', compute='_compute_total_amount', store=True)
```

### 4. SQL Constraints and Indexes
```python
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Order reference must be unique!'),
    ]
```

### 5. Compute, Inverse and Search Methods
```python
    @api.depends('order_line_ids.price_subtotal')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.order_line_ids.mapped('price_subtotal'))
```

### 6. Selection Methods
```python
    @api.model
    def _selection_state(self):
        return [('draft', 'Draft'), ('confirmed', 'Confirmed')]
```

### 7. Constrains and Onchange Methods
```python
    @api.constrains('date_order', 'date_delivery')
    def _check_dates(self):
        for record in self:
            if record.date_delivery < record.date_order:
                raise ValidationError("Delivery date must be after order date!")
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.payment_term_id = self.partner_id.property_payment_term_id
```

### 8. CRUD Methods (ORM Overrides)
```python
    @api.model
    def create(self, vals_list):
        # Customização do create
        return super().create(vals_list)
    
    def write(self, vals):
        # Customização do write
        return super().write(vals)
    
    def unlink(self):
        # Customização do unlink
        return super().unlink()
```

### 9. Action Methods
```python
    def action_confirm(self):
        self.ensure_one()
        self.state = 'confirmed'
        return True
```

### 10. Business Methods
```python
    def _prepare_invoice(self):
        self.ensure_one()
        return {
            'partner_id': self.partner_id.id,
            'invoice_line_ids': self._prepare_invoice_lines(),
        }
    
    def _prepare_invoice_lines(self):
        lines = []
        for line in self.order_line_ids:
            lines.append((0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.quantity,
            }))
        return lines
```

## Exemplo Completo

```python
class Event(models.Model):
    # 1. Private attributes
    _name = 'event.event'
    _description = 'Event'
    
    # 2. Default methods
    def _default_name(self):
        return 'New Event'
    
    # 3. Fields declaration
    name = fields.Char(string='Name', default=_default_name)
    seats_reserved = fields.Integer(
        string='Reserved Seats', 
        store=True,
        readonly=True, 
        compute='_compute_seats'
    )
    seats_available = fields.Integer(
        string='Available Seats', 
        store=True,
        readonly=True, 
        compute='_compute_seats'
    )
    price = fields.Integer(string='Price')
    event_type = fields.Selection(
        string="Type", 
        selection='_selection_type'
    )
    
    # 4. SQL constraints
    _sql_constraints = [
        ('seats_positive', 'CHECK(seats_max > 0)', 'Seats must be positive!'),
    ]
    
    # 5. Compute and search fields
    @api.depends('seats_max', 'registration_ids.state')
    def _compute_seats(self):
        for record in self:
            record.seats_reserved = len(record.registration_ids.filtered(
                lambda r: r.state != 'cancel'
            ))
            record.seats_available = record.seats_max - record.seats_reserved
    
    @api.model
    def _selection_type(self):
        return [
            ('conference', 'Conference'),
            ('workshop', 'Workshop'),
        ]
    
    # 6. Constraints and onchanges
    @api.constrains('seats_max', 'seats_available')
    def _check_seats_limit(self):
        for record in self:
            if record.seats_available < 0:
                raise ValidationError("Not enough seats available!")
    
    @api.onchange('date_begin')
    def _onchange_date_begin(self):
        if self.date_begin and not self.date_end:
            self.date_end = self.date_begin
    
    # 7. CRUD methods
    @api.model
    def create(self, vals_list):
        records = super().create(vals_list)
        records._send_creation_email()
        return records
    
    # 8. Action methods
    def action_validate(self):
        self.ensure_one()
        self.state = 'confirmed'
        return True
    
    # 9. Business methods
    def _send_creation_email(self):
        for record in self:
            record.message_post(body=f"Event {record.name} has been created")
```

## Referências

- [Odoo Symbols and Conventions](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html#symbols-and-conventions)
- [Python Naming Conventions (PEP 8)](https://pep8.org/#naming-conventions)
