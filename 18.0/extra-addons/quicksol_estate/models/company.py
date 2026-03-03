from odoo import models, fields, api
from odoo.exceptions import ValidationError
from ..utils import validators  # Feature 007: Import validators (T005)
import re


class ResCompany(models.Model):

    _inherit = 'res.company'

    # -------------------------------------------------------------------------
    # Discriminator: identifies this company as a real estate agency
    # -------------------------------------------------------------------------
    is_real_estate = fields.Boolean(
        string='Is Real Estate Company',
        default=False,
        help='When True, this company is a real estate agency with CNPJ/CRECI fields.',
    )

    # -------------------------------------------------------------------------
    # Legal Information (real estate specific)
    # -------------------------------------------------------------------------
    cnpj = fields.Char(
        string='CNPJ',
        size=18,
        copy=False,
        help='XX.XXX.XXX/XXXX-XX',
    )
    creci = fields.Char(
        string='CRECI',
        help='Regional Council Registration',
    )
    legal_name = fields.Char(string='Legal Name')
    foundation_date = fields.Date(string='Foundation Date')
    description = fields.Text(string='Description')

    # -------------------------------------------------------------------------
    # Statistics (computed fields)
    # -------------------------------------------------------------------------
    property_count = fields.Integer(
        string='Properties Count',
        compute='_compute_property_count',
    )
    agent_count = fields.Integer(
        string='Agents Count',
        compute='_compute_agent_count',
    )
    profile_count = fields.Integer(
        string='Profiles Count',
        compute='_compute_profile_count',
    )
    lease_count = fields.Integer(
        string='Active Leases',
        compute='_compute_lease_count',
    )
    sale_count = fields.Integer(
        string='Sales Count',
        compute='_compute_sale_count',
    )
    owner_count = fields.Integer(
        string='Owners Count',
        compute='_compute_owner_count',
    )

    _sql_constraints = [
        ('cnpj_unique', 'UNIQUE(cnpj)', 'CNPJ must be unique'),
    ]

    # -------------------------------------------------------------------------
    # Computed Fields
    # -------------------------------------------------------------------------

    def _compute_property_count(self):
        for company in self:
            company.property_count = self.env['real.estate.property'].search_count(
                [('company_id', '=', company.id)]
            )

    def _compute_agent_count(self):
        for company in self:
            company.agent_count = self.env['real.estate.agent'].search_count(
                [('company_id', '=', company.id)]
            )

    def _compute_profile_count(self):
        for company in self:
            company.profile_count = self.env['thedevkitchen.estate.profile'].search_count(
                [('company_id', '=', company.id)]
            )

    def _compute_lease_count(self):
        for company in self:
            company.lease_count = self.env['real.estate.lease'].search_count(
                [('company_id', '=', company.id)]
            )

    def _compute_sale_count(self):
        for company in self:
            company.sale_count = self.env['real.estate.sale'].search_count(
                [('company_id', '=', company.id)]
            )

    def _compute_owner_count(self):
        """Compute count of Owners linked to this company."""
        for company in self:
            owner_group = self.env.ref(
                'quicksol_estate.group_real_estate_owner',
                raise_if_not_found=False,
            )
            if not owner_group:
                company.owner_count = 0
                continue
            domain = [
                ('company_ids', 'in', company.id),
                ('groups_id', 'in', owner_group.id),
            ]
            # Admin sees all owners, others see only active
            if not self.env.user.has_group('base.group_system'):
                domain.append(('active', '=', True))
            company.owner_count = self.env['res.users'].search_count(domain)

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

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
        """Full CNPJ format and check digit validation."""
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
        def calculate_digit(cnpj_str, weights):
            total = sum(int(digit) * weight for digit, weight in zip(cnpj_str, weights))
            remainder = total % 11
            return '0' if remainder < 2 else str(11 - remainder)
        weights_first = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        weights_second = [6] + weights_first
        first_digit = calculate_digit(cnpj_clean[:12], weights_first)
        second_digit = calculate_digit(cnpj_clean[:12] + first_digit, weights_second)
        return cnpj_clean[-2:] == first_digit + second_digit

    @api.onchange('cnpj')
    def _onchange_cnpj(self):
        """Format CNPJ automatically."""
        if self.cnpj:
            cnpj_clean = re.sub(r'[^0-9]', '', self.cnpj)
            if len(cnpj_clean) == 14:
                self.cnpj = (
                    f"{cnpj_clean[:2]}.{cnpj_clean[2:5]}.{cnpj_clean[5:8]}"
                    f"/{cnpj_clean[8:12]}-{cnpj_clean[12:14]}"
                )

    # -------------------------------------------------------------------------
    # Smart Button Actions
    # -------------------------------------------------------------------------

    def action_view_properties(self):
        """Action to view company properties."""
        self.ensure_one()
        return {
            'name': f'Properties - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'real.estate.property',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.id)],
            'context': {'default_company_id': self.id},
        }

    def action_view_agents(self):
        """Action to view company agents."""
        self.ensure_one()
        return {
            'name': f'Agents - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'real.estate.agent',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.id)],
            'context': {'default_company_id': self.id},
        }

    def action_view_owners(self):
        """Action to view company owners."""
        self.ensure_one()
        owner_group = self.env.ref(
            'quicksol_estate.group_real_estate_owner',
            raise_if_not_found=False,
        )
        if not owner_group:
            return {'type': 'ir.actions.act_window_close'}
        domain = [
            ('company_ids', 'in', self.id),
            ('groups_id', 'in', owner_group.id),
        ]
        if not self.env.user.has_group('base.group_system'):
            domain.append(('active', '=', True))
        return {
            'name': f'Owners - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('quicksol_estate.view_owner_tree').id, 'list'),
                (self.env.ref('quicksol_estate.view_owner_form').id, 'form'),
            ],
            'domain': domain,
            'context': {
                'default_groups_id': [(4, owner_group.id)],
                'search_default_active_owners': 1,
            },
        }

    def action_view_profiles(self):
        """Action to view company profiles."""
        self.ensure_one()
        return {
            'name': f'Profiles - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'thedevkitchen.estate.profile',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.id)],
            'context': {'default_company_id': self.id},
        }

    def action_view_leases(self):
        """Action to view company leases."""
        self.ensure_one()
        return {
            'name': f'Leases - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'real.estate.lease',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.id)],
            'context': {'default_company_id': self.id},
        }

    def action_view_sales(self):
        """Action to view company sales."""
        self.ensure_one()
        return {
            'name': f'Sales - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'real.estate.sale',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.id)],
            'context': {'default_company_id': self.id},
        }