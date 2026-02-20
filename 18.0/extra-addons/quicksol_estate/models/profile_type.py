# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProfileType(models.Model):
    _name = 'thedevkitchen.profile.type'
    _description = 'Profile Type (Lookup Table)'
    _order = 'name asc'
    _rec_name = 'name'

    # === Fields ===
    code = fields.Char(
        'Code',
        size=30,
        required=True,
        index=True,
        copy=False,
        help='Machine identifier (e.g., owner, agent, portal)'
    )
    name = fields.Char(
        'Name',
        size=100,
        required=True,
        translate=True,
        help='Display name (e.g., Proprietário, Corretor)'
    )
    group_xml_id = fields.Char(
        'Security Group XML ID',
        size=100,
        required=True,
        help='Full XML ID of the Odoo security group (e.g., quicksol_estate.group_real_estate_owner)'
    )
    level = fields.Selection(
        [
            ('admin', 'Admin'),
            ('operational', 'Operational'),
            ('external', 'External'),
        ],
        string='Level',
        required=True,
        help='ADR-019 hierarchy level classification'
    )
    is_active = fields.Boolean(
        'Active',
        default=True,
        help='Soft delete for lookup entries (KB-09 §9)'
    )

    # === Audit Fields (spec D10) ===
    created_at = fields.Datetime(
        'Created At',
        default=fields.Datetime.now,
        readonly=True,
        help='Creation timestamp'
    )
    updated_at = fields.Datetime(
        'Updated At',
        default=fields.Datetime.now,
        readonly=True,
        help='Last modification timestamp'
    )

    # === SQL Constraints ===
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'O código do tipo de perfil deve ser único.'),
    ]

    # === Methods ===
    @api.model
    def write(self, vals):
        """Override write to update updated_at timestamp."""
        vals['updated_at'] = fields.Datetime.now()
        return super(ProfileType, self).write(vals)
