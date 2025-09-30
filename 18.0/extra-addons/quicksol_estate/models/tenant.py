from odoo import models, fields

class Tenant(models.Model):
    _name = 'real.estate.tenant'
    _description = 'Tenant'

    name = fields.Char(string='Tenant Name', required=True)
    phone = fields.Char(string='Phone Number')
    email = fields.Char(string='Email')
    leases = fields.One2many('real.estate.lease', 'tenant_id', string='Leases')
    profile_picture = fields.Binary('Profile Picture')
    occupation = fields.Char('Occupation')
    birthdate = fields.Date('Birthdate')