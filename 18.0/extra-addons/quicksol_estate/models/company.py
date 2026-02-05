from odoo import models, fields, api
from odoo.exceptions import ValidationError
from ..utils import validators  # Feature 007: Import validators (T005)
import re


class RealEstateCompany(models.Model):
    _name = 'thedevkitchen.estate.company'
    _description = 'Real Estate Company'
    _table = 'thedevkitchen_estate_company'
    _order = 'name'

    # Basic Information
    name = fields.Char(string='Company Name', required=True)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Contact Information
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    website = fields.Char(string='Website')
    
    # Address Information
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('real.estate.state', string='State')
    zip_code = fields.Char(string='ZIP Code')
    country_id = fields.Many2one('res.country', string='Country')
    
    # Legal Information
    cnpj = fields.Char(string='CNPJ', size=18)
    creci = fields.Char(string='CRECI', help='Regional Council Registration')
    legal_name = fields.Char(string='Legal Name')
    
    # Visual Information
    logo = fields.Binary(string='Company Logo')
    color = fields.Integer(string='Color', default=0)
    
    # Business Information
    foundation_date = fields.Date(string='Foundation Date')
    description = fields.Text(string='Description')
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    
    # Statistics (computed fields)
    property_count = fields.Integer(string='Properties Count', compute='_compute_counts')
    agent_count = fields.Integer(string='Agents Count', compute='_compute_counts')
    tenant_count = fields.Integer(string='Tenants Count', compute='_compute_counts')
    lease_count = fields.Integer(string='Active Leases', compute='_compute_counts')
    sale_count = fields.Integer(string='Sales Count', compute='_compute_counts')
    owner_count = fields.Integer(string='Owners Count', compute='_compute_owner_count')  # T039
    
    # Relationships (Many2many com tabelas intermediárias)
    property_ids = fields.Many2many('real.estate.property', 'thedevkitchen_company_property_rel', 'company_id', 'property_id', string='Properties')
    agent_ids = fields.Many2many('real.estate.agent', 'thedevkitchen_company_agent_rel', 'company_id', 'agent_id', string='Agents')
    tenant_ids = fields.Many2many('real.estate.tenant', 'thedevkitchen_company_tenant_rel', 'company_id', 'tenant_id', string='Tenants')
    lease_ids = fields.Many2many('real.estate.lease', 'thedevkitchen_company_lease_rel', 'company_id', 'lease_id', string='Leases')
    sale_ids = fields.Many2many('real.estate.sale', 'thedevkitchen_company_sale_rel', 'company_id', 'sale_id', string='Sales')

    @api.depends('name', 'legal_name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.legal_name or record.name

    @api.depends('property_ids', 'agent_ids', 'tenant_ids', 'lease_ids', 'sale_ids')
    def _compute_counts(self):
        for record in self:
            record.property_count = len(record.property_ids)
            record.agent_count = len(record.agent_ids)
            record.tenant_count = len(record.tenant_ids)
            record.lease_count = len(record.lease_ids)
            record.sale_count = len(record.sale_ids)

    def _compute_owner_count(self):
        """T039: Compute count of Owners linked to this company"""
        for record in self:
            # T042: Admin bypasses filters - count all owners
            # For regular users, count only active owners
            owner_group = self.env.ref('quicksol_estate.group_real_estate_owner')
            domain = [
                ('estate_company_ids', 'in', record.id),
                ('groups_id', 'in', owner_group.id),
            ]
            # T042: Admin sees all owners, others see only active
            if not self.env.user.has_group('base.group_system'):
                domain.append(('active', '=', True))
            record.owner_count = self.env['res.users'].search_count(domain)

    @api.constrains('cnpj')
    def _check_cnpj(self):
        for record in self:
            if record.cnpj and not self._validate_cnpj(record.cnpj):
                raise ValidationError('Invalid CNPJ format. Please use: XX.XXX.XXX/XXXX-XX')
    
    @api.constrains('email')
    def _check_email(self):
        """Feature 007: Email format validation (T005)"""
        for record in self:
            if record.email and not validators.validate_email_format(record.email):
                raise ValidationError(f'Invalid email format: {record.email}')

    def _validate_cnpj(self, cnpj):
        """Full CNPJ format and check digit validation"""
        if not cnpj:
            return True
        # Remove any formatting
        cnpj_clean = re.sub(r'[^0-9]', '', cnpj)
        # Check if it has 14 digits
        if len(cnpj_clean) != 14:
            return False
        # Check for sequence of same digit (invalid CNPJ)
        if cnpj_clean == cnpj_clean[0] * 14:
            return False
        # Calculate first check digit
        def calculate_digit(cnpj, weights):
            total = sum(int(digit) * weight for digit, weight in zip(cnpj, weights))
            remainder = total % 11
            return '0' if remainder < 2 else str(11 - remainder)
        weights_first = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        weights_second = [6] + weights_first
        first_digit = calculate_digit(cnpj_clean[:12], weights_first)
        second_digit = calculate_digit(cnpj_clean[:12] + first_digit, weights_second)
        return cnpj_clean[-2:] == first_digit + second_digit

    @api.onchange('cnpj')
    def _onchange_cnpj(self):
        """Format CNPJ automatically"""
        if self.cnpj:
            # Remove any non-digit characters
            cnpj_clean = re.sub(r'[^0-9]', '', self.cnpj)
            if len(cnpj_clean) == 14:
                # Format: XX.XXX.XXX/XXXX-XX
                self.cnpj = f"{cnpj_clean[:2]}.{cnpj_clean[2:5]}.{cnpj_clean[5:8]}/{cnpj_clean[8:12]}-{cnpj_clean[12:14]}"

    def action_view_properties(self):
        """Action to view company properties"""
        self.ensure_one()
        return {
            'name': f'Properties - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'real.estate.property',
            'view_mode': 'list,form',
            'domain': [('company_ids', 'in', self.id)],
            'context': {'default_company_ids': [(6, 0, [self.id])]}
        }

    def action_view_agents(self):
        """Action to view company agents"""
        self.ensure_one()
        return {
            'name': f'Agents - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'real.estate.agent',
            'view_mode': 'list,form',
            'domain': [('company_ids', 'in', self.id)],
            'context': {'default_company_ids': [(6, 0, [self.id])]}
        }

    def action_view_owners(self):
        """T040: Action to view company owners"""
        self.ensure_one()
        owner_group = self.env.ref('quicksol_estate.group_real_estate_owner')
        domain = [
            ('estate_company_ids', 'in', self.id),
            ('groups_id', 'in', owner_group.id),
        ]
        # T042: Admin can see inactive owners, others see only active
        if not self.env.user.has_group('base.group_system'):
            domain.append(('active', '=', True))
        
        return {
            'name': f'Owners - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('quicksol_estate.view_owner_tree').id, 'tree'),
                (self.env.ref('quicksol_estate.view_owner_form').id, 'form'),
            ],
            'domain': domain,
            'context': {
                'default_groups_id': [(4, owner_group.id)],
                'search_default_active_owners': 1,
            }
        }

    def action_view_tenants(self):
        """Action to view company tenants"""
        self.ensure_one()
        return {
            'name': f'Tenants - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'real.estate.tenant',
            'view_mode': 'list,form',
            'domain': [('company_ids', 'in', self.id)],
            'context': {'default_company_ids': [(6, 0, [self.id])]}
        }

    def action_view_leases(self):
        """Action to view company leases"""
        self.ensure_one()
        return {
            'name': f'Leases - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'real.estate.lease',
            'view_mode': 'list,form',
            'domain': [('company_ids', 'in', self.id)],
            'context': {'default_company_ids': [(6, 0, [self.id])]}
        }

    def action_view_sales(self):
        """Action to view company sales"""
        self.ensure_one()
        return {
            'name': f'Sales - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'real.estate.sale',
            'view_mode': 'list,form',
            'domain': [('company_ids', 'in', self.id)],
            'context': {'default_company_ids': [(6, 0, [self.id])]}
        }