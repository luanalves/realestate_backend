# -*- coding: utf-8 -*-
from odoo import models, fields


class State(models.Model):
    _name = 'real.estate.state'
    _description = 'State/Province'
    _order = 'name'

    name = fields.Char(string='State Name', required=True)
    code = fields.Char(string='State Code', required=True, size=3)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    
    _sql_constraints = [
        ('code_country_unique', 'unique(code, country_id)', 'State code must be unique per country!')
    ]
