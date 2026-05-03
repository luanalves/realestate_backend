# -*- coding: utf-8 -*-
"""
Model: real.estate.partner.phone — Feature 015 (Service Pipeline)
Also extends res.partner with phone_ids One2many.

Multi-phone support for clients with type classification (FR-021).
At most one phone per partner can be marked is_primary (FR-022 / dedup).

data-model.md: E4
"""
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class RealEstatePartnerPhone(models.Model):
    _name = 'real.estate.partner.phone'
    _description = 'Partner Phone (Service)'
    _order = 'is_primary desc, id'

    # ------------------------------------------------------------------ #
    #  Fields                                                              #
    # ------------------------------------------------------------------ #
    partner_id = fields.Many2one(
        'res.partner',
        'Partner',
        required=True,
        ondelete='cascade',
        index=True,
    )
    phone_type = fields.Selection(
        selection=[
            ('mobile',    'Celular'),
            ('home',      'Residencial'),
            ('work',      'Comercial'),
            ('whatsapp',  'WhatsApp'),
            ('fax',       'Fax'),
        ],
        string='Type',
        required=True,
    )
    number = fields.Char('Number', size=30, required=True)
    is_primary = fields.Boolean('Primary', default=False)

    # ------------------------------------------------------------------ #
    #  Python constraints                                                  #
    # ------------------------------------------------------------------ #
    @api.constrains('partner_id', 'is_primary')
    def _check_at_most_one_primary(self):
        """At most one phone per partner can have is_primary=True (data-model.md E4)."""
        for phone in self:
            if not phone.is_primary:
                continue
            count = self.search_count([
                ('partner_id', '=', phone.partner_id.id),
                ('is_primary', '=', True),
                ('id', '!=', phone.id),
            ])
            if count:
                raise ValidationError(_(
                    'Partner "%(partner)s" already has a primary phone. '
                    'Only one primary phone is allowed per partner.',
                    partner=phone.partner_id.name,
                ))


class ResPartnerPhoneExtension(models.Model):
    """Extend res.partner with One2many back-reference to partner phones."""
    _inherit = 'res.partner'

    phone_ids = fields.One2many(
        'real.estate.partner.phone',
        'partner_id',
        string='Phones (Service)',
    )
