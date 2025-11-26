# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PropertyOwner(models.Model):
    _name = 'real.estate.property.owner'
    _description = 'Property Owner'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Owner Name', required=True, tracking=True)
    cpf = fields.Char(string='CPF', size=14)
    cnpj = fields.Char(string='CNPJ', size=18)
    rg = fields.Char(string='RG', size=20)
    email = fields.Char(string='Primary Email')
    phone = fields.Char(string='Primary Phone')
    mobile = fields.Char(string='Mobile Phone')
    whatsapp = fields.Char(string='WhatsApp')
    address = fields.Text(string='Address')
    city = fields.Char(string='City')
    state_id = fields.Many2one('real.estate.state', string='State')
    zip_code = fields.Char(string='CEP')
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env['res.country'].search([('code', '=', 'BR')], limit=1).id)
    birth_date = fields.Date(string='Birth Date')
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ], string='Marital Status')
    nationality = fields.Char(string='Nationality', default='Brazilian')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    
    # Relationships
    property_ids = fields.One2many('real.estate.property', 'owner_id', string='Properties')
    property_count = fields.Integer(string='Property Count', compute='_compute_property_count')

    @api.depends('property_ids')
    def _compute_property_count(self):
        for owner in self:
            owner.property_count = len(owner.property_ids)

    @api.constrains('cpf')
    def _check_cpf(self):
        for owner in self:
            if owner.cpf and len(owner.cpf.replace('.', '').replace('-', '')) != 11:
                raise ValidationError('CPF must contain 11 digits.')

    @api.constrains('cnpj')
    def _check_cnpj(self):
        for owner in self:
            if owner.cnpj and len(owner.cnpj.replace('.', '').replace('/', '').replace('-', '')) != 14:
                raise ValidationError('CNPJ must contain 14 digits.')
