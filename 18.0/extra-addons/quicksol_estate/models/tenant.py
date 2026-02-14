from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re

class Tenant(models.Model):
    _name = 'real.estate.tenant'
    _description = 'Tenant'

    name = fields.Char(string='Tenant Name', required=True)
    partner_id = fields.Many2one('res.partner', string='Related Partner', help='Partner record for tenant (enables Portal access)')
    phone = fields.Char(string='Phone Number')
    email = fields.Char(string='Email')
    company_ids = fields.Many2many('thedevkitchen.estate.company', 'thedevkitchen_company_tenant_rel', 'tenant_id', 'company_id', string='Real Estate Companies')
    leases = fields.One2many('real.estate.lease', 'tenant_id', string='Leases')
    profile_picture = fields.Binary('Profile Picture')
    occupation = fields.Char('Occupation')
    birthdate = fields.Date('Birthdate')

    # Feature 008: Soft delete fields (ADR-015)
    active = fields.Boolean(string='Active', default=True)
    deactivation_date = fields.Datetime(string='Deactivation Date')
    deactivation_reason = fields.Text(string='Deactivation Reason')

    @api.constrains('email')
    def _validate_email(self):
        """Validate email format using regex pattern"""
        for record in self:
            if record.email:
                # Email validation regex pattern
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, record.email):
                    raise ValidationError("Please enter a valid email address.")