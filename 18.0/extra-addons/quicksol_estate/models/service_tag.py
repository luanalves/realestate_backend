# -*- coding: utf-8 -*-

import re
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

_COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')


class RealEstateServiceTag(models.Model):
    _name = 'real.estate.service.tag'
    _description = 'Service Tag (Atendimento)'
    _order = 'name'

    # ------------------------------------------------------------------ #
    #  SQL constraints                                                     #
    # ------------------------------------------------------------------ #
    _sql_constraints = [
        (
            'unique_tag_name_per_company',
            'UNIQUE(name, company_id)',
            'Tag name must be unique per company.',
        ),
        (
            'valid_color_format',
            r"CHECK(color ~ '^#[0-9A-Fa-f]{6}$')",
            'Color must be a valid 6-digit hex color (e.g. #3498db).',
        ),
    ]

    # ------------------------------------------------------------------ #
    #  Fields                                                              #
    # ------------------------------------------------------------------ #
    name = fields.Char('Name', size=50, required=True, tracking=True)
    color = fields.Char('Color (hex)', size=7, required=True, default='#808080')
    is_system = fields.Boolean(
        'System Tag',
        default=False,
        help='System tags drive pipeline rules (e.g. "Encerrado" locks stage changes). '
             'Cannot be modified by regular users.',
    )
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # ------------------------------------------------------------------ #
    #  Python constraints                                                  #
    # ------------------------------------------------------------------ #
    @api.constrains('name', 'active', 'is_system', 'color')
    def _check_system_tag_immutable(self):
        """Block writes to system tags unless admin context flag is set (FR-018)."""
        for tag in self:
            if not tag.is_system:
                continue
            # Allow if explicit admin bypass in context (post_init hook, migrations)
            if self.env.context.get('service.tag_admin'):
                continue
            # Allow on creation (record doesn't exist yet in DB)
            origin = tag._origin
            if not origin or not origin.id:
                continue
            # Any actual change on an existing system tag is blocked
            changed_fields = {
                f for f in ('name', 'active', 'is_system', 'color')
                if getattr(tag, f) != getattr(origin, f)
            }
            if changed_fields:
                raise ValidationError(_(
                    'System tag "%(name)s" is immutable. '
                    'Fields %(fields)s cannot be changed.',
                    name=origin.name,
                    fields=', '.join(sorted(changed_fields)),
                ))

    @api.constrains('color')
    def _check_color_format(self):
        for tag in self:
            if tag.color and not _COLOR_RE.match(tag.color):
                raise ValidationError(_(
                    'Color "%(color)s" is not a valid hex color (expected #RRGGBB).',
                    color=tag.color,
                ))
