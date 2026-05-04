# -*- coding: utf-8 -*-

import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class RealEstateServiceSource(models.Model):
    _name = 'real.estate.service.source'
    _description = 'Service Source (Atendimento)'
    _order = 'name'

    # ------------------------------------------------------------------ #
    #  SQL constraints                                                     #
    # ------------------------------------------------------------------ #
    _sql_constraints = [
        (
            'unique_source_code_per_company',
            'UNIQUE(code, company_id)',
            'Source code must be unique per company.',
        ),
    ]

    # ------------------------------------------------------------------ #
    #  Fields                                                              #
    # ------------------------------------------------------------------ #
    name = fields.Char('Name', size=80, required=True, tracking=True)
    code = fields.Char(
        'Code',
        size=30,
        required=True,
        help='Stable machine-readable code, e.g. "site", "whatsapp". '
             'Must be unique per company.',
    )
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
