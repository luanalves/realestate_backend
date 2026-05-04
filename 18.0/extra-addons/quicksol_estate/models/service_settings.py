# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ThedevkitchenServiceSettings(models.Model):
    _name = 'thedevkitchen.service.settings'
    _description = 'Service Pipeline Settings (per company)'
    _order = 'company_id'

    # ------------------------------------------------------------------ #
    #  SQL constraints                                                     #
    # ------------------------------------------------------------------ #
    _sql_constraints = [
        (
            'unique_settings_per_company',
            'UNIQUE(company_id)',
            'Service settings must be unique per company.',
        ),
    ]

    # ------------------------------------------------------------------ #
    #  Fields                                                              #
    # ------------------------------------------------------------------ #
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    pendency_threshold_days = fields.Integer(
        'Pendency Threshold (days)',
        required=True,
        default=3,
        help='Services with no interaction for more than this many days are marked as pending.',
    )
    auto_close_after_days = fields.Integer(
        'Auto-close After (days)',
        default=0,
        help='0 = disabled. Future use: automatically archive services after N days of inactivity.',
    )

    # ------------------------------------------------------------------ #
    #  Python constraints                                                  #
    # ------------------------------------------------------------------ #
    @api.constrains('pendency_threshold_days')
    def _check_pendency_threshold(self):
        for rec in self:
            if not (1 <= rec.pendency_threshold_days <= 30):
                raise ValidationError(_(
                    'Pendency threshold must be between 1 and 30 days '
                    '(got %(value)d).',
                    value=rec.pendency_threshold_days,
                ))

    @api.constrains('auto_close_after_days')
    def _check_auto_close_days(self):
        for rec in self:
            if not (0 <= rec.auto_close_after_days <= 365):
                raise ValidationError(_(
                    'Auto-close days must be between 0 (disabled) and 365 '
                    '(got %(value)d).',
                    value=rec.auto_close_after_days,
                ))

    # ------------------------------------------------------------------ #
    #  Class method — convenience getter                                   #
    # ------------------------------------------------------------------ #
    @classmethod
    def get_settings(cls, env, company_id=None):
        """Return (or create) the singleton settings record for a company.

        Usage:
            settings = ThedevkitchenServiceSettings.get_settings(request.env)
            threshold = settings.pendency_threshold_days
        """
        cid = company_id or env.company.id
        rec = env['thedevkitchen.service.settings'].search(
            [('company_id', '=', cid)], limit=1
        )
        if not rec:
            rec = env['thedevkitchen.service.settings'].create({'company_id': cid})
        return rec
