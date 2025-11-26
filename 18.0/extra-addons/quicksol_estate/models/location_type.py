# -*- coding: utf-8 -*-
from odoo import models, fields


class LocationType(models.Model):
    _name = 'real.estate.location.type'
    _description = 'Location Type'
    _order = 'sequence, name'

    name = fields.Char(string='Location Type', required=True)
    code = fields.Char(string='Code', required=True, size=20)
    sequence = fields.Integer(string='Sequence', default=10)
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Location type code must be unique!')
    ]
