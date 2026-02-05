# Practical Examples - Exemplos Práticos Completos

Este arquivo contém exemplos práticos e completos de implementações comuns em Odoo.

## 📦 Módulo Completo: Real Estate

### Estrutura do Módulo

```
thedevkitchen_estate/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── estate_property.py
│   ├── estate_property_type.py
│   └── res_partner.py
├── views/
│   ├── estate_property_views.xml
│   ├── estate_property_type_views.xml
│   └── estate_menus.xml
├── security/
│   ├── ir.model.access.csv
│   ├── thedevkitchen_estate_groups.xml
│   └── estate_property_security.xml
├── data/
│   └── estate_property_type_data.xml
└── static/
    └── description/
        └── icon.png
```

### 1. __manifest__.py

```python
# -*- coding: utf-8 -*-
{
    'name': 'Real Estate',
    'version': '1.0',
    'category': 'Real Estate/Brokerage',
    'summary': 'Manage real estate properties and sales',
    'description': """
        Real Estate Management
        ======================
        * Manage properties
        * Track property types
        * Manage offers and sales
    """,
    'author': 'TheDevKitchen',
    'website': 'https://www.thedevkitchen.com',
    'depends': ['base', 'mail'],
    'data': [
        # Security
        'security/thedevkitchen_estate_groups.xml',
        'security/ir.model.access.csv',
        'security/estate_property_security.xml',
        
        # Data
        'data/estate_property_type_data.xml',
        
        # Views
        'views/estate_property_type_views.xml',
        'views/estate_property_views.xml',
        'views/estate_menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
```

### 2. models/__init__.py

```python
# -*- coding: utf-8 -*-

from . import estate_property
from . import estate_property_type
from . import res_partner
```

### 3. models/estate_property_type.py

```python
# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EstatePropertyType(models.Model):
    """Property Type Model"""
    
    # Private attributes
    _name = 'estate.property.type'
    _description = 'Real Estate Property Type'
    _order = 'sequence, name'
    
    # Fields
    name = fields.Char(string='Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    property_ids = fields.One2many(
        'estate.property', 
        'property_type_id', 
        string='Properties'
    )
    property_count = fields.Integer(
        string='Property Count',
        compute='_compute_property_count'
    )
    
    # SQL Constraints
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Property type name must be unique!'),
    ]
    
    # Compute methods
    @api.depends('property_ids')
    def _compute_property_count(self):
        """Compute the number of properties for this type"""
        for record in self:
            record.property_count = len(record.property_ids)
    
    # Action methods
    def action_view_properties(self):
        """Open properties of this type"""
        self.ensure_one()
        return {
            'name': f'Properties - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'estate.property',
            'view_mode': 'list,form',
            'domain': [('property_type_id', '=', self.id)],
            'context': {'default_property_type_id': self.id},
        }
```

### 4. models/estate_property.py

```python
# -*- coding: utf-8 -*-

from datetime import date, timedelta

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


class EstateProperty(models.Model):
    """Real Estate Property Model"""
    
    # Private attributes
    _name = 'estate.property'
    _description = 'Real Estate Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    
    # Default methods
    def _default_date_availability(self):
        """Default availability date is 3 months from now"""
        return date.today() + timedelta(days=90)
    
    # Fields declaration
    # Basic Info
    name = fields.Char(string='Title', required=True, tracking=True)
    description = fields.Text(string='Description')
    postcode = fields.Char(string='Postcode')
    date_availability = fields.Date(
        string='Available From',
        default=_default_date_availability,
        copy=False
    )
    expected_price = fields.Float(string='Expected Price', required=True)
    selling_price = fields.Float(
        string='Selling Price', 
        readonly=True, 
        copy=False
    )
    
    # Relational fields
    property_type_id = fields.Many2one(
        'estate.property.type', 
        string='Property Type'
    )
    buyer_id = fields.Many2one(
        'res.partner', 
        string='Buyer', 
        copy=False,
        tracking=True
    )
    salesperson_id = fields.Many2one(
        'res.users', 
        string='Salesperson',
        default=lambda self: self.env.user
    )
    tag_ids = fields.Many2many(
        'estate.property.tag', 
        string='Tags'
    )
    offer_ids = fields.One2many(
        'estate.property.offer', 
        'property_id', 
        string='Offers'
    )
    
    # Computed fields
    total_area = fields.Float(
        string='Total Area (sqm)',
        compute='_compute_total_area'
    )
    best_price = fields.Float(
        string='Best Offer',
        compute='_compute_best_price'
    )
    
    # State
    state = fields.Selection(
        selection='_selection_state',
        string='Status',
        required=True,
        copy=False,
        default='new',
        tracking=True
    )
    
    # Other fields
    bedrooms = fields.Integer(string='Bedrooms', default=2)
    living_area = fields.Float(string='Living Area (sqm)')
    facades = fields.Integer(string='Facades')
    garage = fields.Boolean(string='Garage')
    garden = fields.Boolean(string='Garden')
    garden_area = fields.Float(string='Garden Area (sqm)')
    garden_orientation = fields.Selection(
        [
            ('north', 'North'),
            ('south', 'South'),
            ('east', 'East'),
            ('west', 'West'),
        ],
        string='Garden Orientation'
    )
    active = fields.Boolean(string='Active', default=True)
    
    # SQL Constraints
    _sql_constraints = [
        (
            'expected_price_positive',
            'CHECK(expected_price > 0)',
            'Expected price must be strictly positive!'
        ),
        (
            'selling_price_positive',
            'CHECK(selling_price >= 0)',
            'Selling price must be positive!'
        ),
    ]
    
    # Compute methods (same order as field declaration)
    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        """Compute total area (living + garden)"""
        for record in self:
            record.total_area = record.living_area + record.garden_area
    
    @api.depends('offer_ids.price')
    def _compute_best_price(self):
        """Compute best offer price"""
        for record in self:
            if record.offer_ids:
                record.best_price = max(record.offer_ids.mapped('price'))
            else:
                record.best_price = 0.0
    
    # Selection method
    @api.model
    def _selection_state(self):
        """Return available states"""
        return [
            ('new', 'New'),
            ('offer_received', 'Offer Received'),
            ('offer_accepted', 'Offer Accepted'),
            ('sold', 'Sold'),
            ('cancelled', 'Cancelled'),
        ]
    
    # Constraints and onchange methods
    @api.constrains('selling_price', 'expected_price')
    def _check_selling_price(self):
        """Check that selling price is at least 90% of expected price"""
        for record in self:
            if float_is_zero(record.selling_price, precision_digits=2):
                continue
                
            min_price = record.expected_price * 0.9
            if float_compare(
                record.selling_price, 
                min_price, 
                precision_digits=2
            ) < 0:
                raise ValidationError(
                    "Selling price cannot be lower than 90% of expected price!"
                )
    
    @api.onchange('garden')
    def _onchange_garden(self):
        """Set garden defaults when garden is checked"""
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = 'north'
        else:
            self.garden_area = 0
            self.garden_orientation = False
    
    # CRUD methods
    @api.model
    def create(self, vals_list):
        """Override create to update state"""
        records = super().create(vals_list)
        for record in records:
            if record.offer_ids:
                record.state = 'offer_received'
        return records
    
    def write(self, vals):
        """Prevent editing sold or cancelled properties"""
        if 'state' not in vals:
            for record in self:
                if record.state in ('sold', 'cancelled'):
                    raise UserError(
                        "Cannot modify sold or cancelled properties!"
                    )
        return super().write(vals)
    
    def unlink(self):
        """Prevent deletion of non-new/cancelled properties"""
        for record in self:
            if record.state not in ('new', 'cancelled'):
                raise UserError(
                    "Only new or cancelled properties can be deleted!"
                )
        return super().unlink()
    
    # Action methods
    def action_sold(self):
        """Mark property as sold"""
        self.ensure_one()
        if self.state == 'cancelled':
            raise UserError("Cancelled properties cannot be sold!")
        
        self.state = 'sold'
        return True
    
    def action_cancel(self):
        """Cancel property"""
        self.ensure_one()
        if self.state == 'sold':
            raise UserError("Sold properties cannot be cancelled!")
        
        self.state = 'cancelled'
        return True
    
    # Business methods
    def _prepare_invoice_line_values(self):
        """Prepare invoice line values"""
        self.ensure_one()
        return {
            'name': self.name,
            'quantity': 1,
            'price_unit': self.selling_price,
        }


class EstatePropertyTag(models.Model):
    """Property Tags"""
    
    _name = 'estate.property.tag'
    _description = 'Property Tag'
    _order = 'name'
    
    name = fields.Char(string='Name', required=True)
    color = fields.Integer(string='Color')
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Tag name must be unique!'),
    ]


class EstatePropertyOffer(models.Model):
    """Property Offer"""
    
    _name = 'estate.property.offer'
    _description = 'Property Offer'
    _order = 'price desc'
    
    price = fields.Float(string='Price', required=True)
    status = fields.Selection(
        [
            ('accepted', 'Accepted'),
            ('refused', 'Refused'),
        ],
        string='Status',
        copy=False
    )
    partner_id = fields.Many2one(
        'res.partner', 
        string='Partner', 
        required=True
    )
    property_id = fields.Many2one(
        'estate.property', 
        string='Property', 
        required=True
    )
    validity = fields.Integer(string='Validity (days)', default=7)
    date_deadline = fields.Date(
        string='Deadline',
        compute='_compute_date_deadline',
        inverse='_inverse_date_deadline'
    )
    
    _sql_constraints = [
        ('price_positive', 'CHECK(price > 0)', 'Offer price must be positive!'),
    ]
    
    @api.depends('create_date', 'validity')
    def _compute_date_deadline(self):
        """Compute deadline based on validity"""
        for record in self:
            create_date = record.create_date.date() if record.create_date else date.today()
            record.date_deadline = create_date + timedelta(days=record.validity)
    
    def _inverse_date_deadline(self):
        """Compute validity based on deadline"""
        for record in self:
            create_date = record.create_date.date() if record.create_date else date.today()
            delta = record.date_deadline - create_date
            record.validity = delta.days
    
    @api.model
    def create(self, vals_list):
        """Auto-update property state when offer is created"""
        records = super().create(vals_list)
        for record in records:
            if record.property_id.state == 'new':
                record.property_id.state = 'offer_received'
        return records
    
    def action_accept(self):
        """Accept offer"""
        self.ensure_one()
        # Refuse all other offers
        self.property_id.offer_ids.filtered(
            lambda o: o != self
        ).write({'status': 'refused'})
        
        self.status = 'accepted'
        self.property_id.write({
            'buyer_id': self.partner_id.id,
            'selling_price': self.price,
            'state': 'offer_accepted',
        })
        return True
    
    def action_refuse(self):
        """Refuse offer"""
        self.ensure_one()
        self.status = 'refused'
        return True
```

### 5. models/res_partner.py

```python
# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    """Inherit res.partner to add property relation"""
    
    _inherit = 'res.partner'
    
    property_ids = fields.One2many(
        'estate.property',
        'buyer_id',
        string='Properties',
        domain=[('state', 'in', ['offer_accepted', 'sold'])]
    )
```

### 6. security/ir.model.access.csv

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_estate_property_user,estate.property.user,model_estate_property,base.group_user,1,1,1,0
access_estate_property_manager,estate.property.manager,model_estate_property,thedevkitchen_estate_group_manager,1,1,1,1
access_estate_property_type_user,estate.property.type.user,model_estate_property_type,base.group_user,1,0,0,0
access_estate_property_type_manager,estate.property.type.manager,model_estate_property_type,thedevkitchen_estate_group_manager,1,1,1,1
access_estate_property_tag_user,estate.property.tag.user,model_estate_property_tag,base.group_user,1,0,0,0
access_estate_property_tag_manager,estate.property.tag.manager,model_estate_property_tag,thedevkitchen_estate_group_manager,1,1,1,1
access_estate_property_offer_user,estate.property.offer.user,model_estate_property_offer,base.group_user,1,1,1,0
access_estate_property_offer_manager,estate.property.offer.manager,model_estate_property_offer,thedevkitchen_estate_group_manager,1,1,1,1
```

### 7. views/estate_property_views.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Form View -->
    <record id="estate_property_view_form" model="ir.ui.view">
        <field name="name">estate.property.view.form</field>
        <field name="model">estate.property</field>
        <field name="arch" type="xml">
            <form string="Property">
                <header>
                    <button name="action_sold" string="Sold" type="object" 
                            invisible="state in ('sold', 'cancelled')"/>
                    <button name="action_cancel" string="Cancel" type="object" 
                            invisible="state in ('sold', 'cancelled')"/>
                    <field name="state" widget="statusbar" 
                           statusbar_visible="new,offer_received,offer_accepted,sold"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1>
                            <field name="name" placeholder="Property Name"/>
                        </h1>
                        <field name="tag_ids" widget="many2many_tags" 
                               options="{'color_field': 'color'}"/>
                    </div>
                    <group>
                        <group>
                            <field name="property_type_id"/>
                            <field name="postcode"/>
                            <field name="date_availability"/>
                        </group>
                        <group>
                            <field name="expected_price"/>
                            <field name="best_price"/>
                            <field name="selling_price"/>
                        </group>
                    </group>
                    <notebook>
                        <page string="Description">
                            <group>
                                <field name="description"/>
                                <field name="bedrooms"/>
                                <field name="living_area"/>
                                <field name="facades"/>
                                <field name="garage"/>
                                <field name="garden"/>
                                <field name="garden_area" invisible="not garden"/>
                                <field name="garden_orientation" invisible="not garden"/>
                                <field name="total_area"/>
                            </group>
                        </page>
                        <page string="Offers">
                            <field name="offer_ids">
                                <list editable="bottom">
                                    <field name="price"/>
                                    <field name="partner_id"/>
                                    <field name="validity"/>
                                    <field name="date_deadline"/>
                                    <button name="action_accept" string="Accept" 
                                            type="object" icon="fa-check"/>
                                    <button name="action_refuse" string="Refuse" 
                                            type="object" icon="fa-times"/>
                                    <field name="status"/>
                                </list>
                            </field>
                        </page>
                        <page string="Other Info">
                            <group>
                                <field name="salesperson_id"/>
                                <field name="buyer_id"/>
                            </group>
                        </page>
                    </notebook>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="activity_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>
        </field>
    </record>

    <!-- List View -->
    <record id="estate_property_view_list" model="ir.ui.view">
        <field name="name">estate.property.view.list</field>
        <field name="model">estate.property</field>
        <field name="arch" type="xml">
            <list string="Properties" default_order="id desc">
                <field name="name"/>
                <field name="property_type_id"/>
                <field name="postcode"/>
                <field name="bedrooms"/>
                <field name="living_area"/>
                <field name="expected_price"/>
                <field name="selling_price"/>
                <field name="state" 
                       decoration-success="state == 'offer_accepted'"
                       decoration-muted="state == 'sold'"/>
            </list>
        </field>
    </record>

    <!-- Search View -->
    <record id="estate_property_view_search" model="ir.ui.view">
        <field name="name">estate.property.view.search</field>
        <field name="model">estate.property</field>
        <field name="arch" type="xml">
            <search string="Properties">
                <field name="name"/>
                <field name="postcode"/>
                <field name="property_type_id"/>
                <separator/>
                <filter string="Available" name="available" 
                        domain="[('state', 'in', ['new', 'offer_received'])]"/>
                <filter string="New" name="new" domain="[('state', '=', 'new')]"/>
                <group expand="1" string="Group By">
                    <filter string="Property Type" name="property_type" 
                            context="{'group_by': 'property_type_id'}"/>
                    <filter string="Salesperson" name="salesperson" 
                            context="{'group_by': 'salesperson_id'}"/>
                </group>
            </search>
        </field>
    </record>

    <!-- Action -->
    <record id="estate_property_action" model="ir.actions.act_window">
        <field name="name">Properties</field>
        <field name="res_model">estate.property</field>
        <field name="view_mode">list,form</field>
        <field name="context">{'search_default_available': 1}</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                Create your first property!
            </p>
        </field>
    </record>
</odoo>
```

Este exemplo completo demonstra:
- ✅ Estrutura correta de módulo
- ✅ Nomenclatura padronizada
- ✅ Herança de modelos
- ✅ Campos computados
- ✅ Constraints
- ✅ Onchanges
- ✅ CRUD overrides
- ✅ Action methods
- ✅ Segurança (access rights e record rules)
- ✅ Views completas (form, list, search)
- ✅ Integration com mail (chatter)

## Referências

Veja os outros arquivos da knowledge base para mais detalhes sobre cada aspecto:
- [Module Structure](01-module-structure.md)
- [Python Guidelines](03-python-coding-guidelines.md)
- [Programming in Odoo](07-programming-in-odoo.md)
- [Symbols and Conventions](08-symbols-conventions.md)
