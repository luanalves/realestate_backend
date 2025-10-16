# -*- coding: utf-8 -*-
from odoo import models, fields


class PropertyBuilding(models.Model):
    _name = 'real.estate.property.building'
    _description = 'Building/Condominium'
    _rec_name = 'name'

    name = fields.Char(string='Building Name', required=True, tracking=True)
    address = fields.Text(string='Address')
    city = fields.Char(string='City')
    state = fields.Char(string='State')
    zip_code = fields.Char(string='CEP')
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.ref('base.br').id)
    
    # Building Details
    total_floors = fields.Integer(string='Total Floors')
    total_units = fields.Integer(string='Total Units')
    construction_year = fields.Integer(string='Construction Year')
    has_elevator = fields.Boolean(string='Has Elevator')
    has_security = fields.Boolean(string='Has Security 24h')
    has_pool = fields.Boolean(string='Has Pool')
    has_gym = fields.Boolean(string='Has Gym')
    has_playground = fields.Boolean(string='Has Playground')
    has_party_room = fields.Boolean(string='Has Party Room')
    has_sports_court = fields.Boolean(string='Has Sports Court')
    
    # Financial
    monthly_fee = fields.Monetary(string='Monthly Condominium Fee', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    
    # Administrator
    administrator_name = fields.Char(string='Administrator Name')
    administrator_phone = fields.Char(string='Administrator Phone')
    administrator_email = fields.Char(string='Administrator Email')
    
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    
    # Relationships
    property_ids = fields.One2many('real.estate.property', 'building_id', string='Properties')
    property_count = fields.Integer(string='Property Count', compute='_compute_property_count')

    def _compute_property_count(self):
        for building in self:
            building.property_count = len(building.property_ids)
