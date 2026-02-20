# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from ..utils import validators


class Profile(models.Model):
    _name = 'thedevkitchen.estate.profile'
    _description = 'Unified Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'
    _rec_name = 'name'

    # ===== Relationships =====
    profile_type_id = fields.Many2one(
        'thedevkitchen.profile.type',
        string='Profile Type',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
        help='Type classification (owner, agent, portal, etc.)'
    )
    company_id = fields.Many2one(
        'thedevkitchen.estate.company',
        string='Company',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
        help='Company this profile belongs to (from request body, not header)'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Related Partner',
        ondelete='restrict',
        help='Auto-created Odoo partner. Bridges to res.users for system access.'
    )

    # ===== Cadastral Fields =====
    name = fields.Char(
        'Full Name',
        size=200,
        required=True,
        tracking=True,
        help='Full legal name'
    )
    document = fields.Char(
        'CPF/CNPJ',
        size=20,
        required=True,
        index=True,
        copy=False,
        tracking=True,
        help='Brazilian CPF (11 digits) or CNPJ (14 digits), with or without formatting'
    )
    document_normalized = fields.Char(
        'Document (normalized)',
        size=14,
        compute='_compute_document_normalized',
        store=True,
        index=True,
        help='Digits-only version of document for search and validation'
    )
    email = fields.Char(
        'Email',
        size=100,
        required=True,
        tracking=True,
        help='Contact email address'
    )
    phone = fields.Char(
        'Phone',
        size=20,
        help='Phone number (landline or mobile)'
    )
    mobile = fields.Char(
        'Mobile',
        size=20,
        help='Mobile phone number'
    )
    occupation = fields.Char(
        'Occupation',
        size=100,
        help='Professional occupation (relevant for portal/tenant type)'
    )
    birthdate = fields.Date(
        'Date of Birth',
        required=True,
        help='Date of birth (required for all 9 profile types — spec D9)'
    )
    hire_date = fields.Date(
        'Hire Date',
        help='Employment hire date (relevant for internal profiles)'
    )
    profile_picture = fields.Binary(
        'Profile Picture',
        help='Profile photo'
    )

    # ===== Soft Delete (ADR-015) =====
    active = fields.Boolean(
        'Active',
        default=True,
        help='Soft delete flag. False = profile is deactivated.'
    )
    deactivation_date = fields.Datetime(
        'Deactivation Date',
        help='Timestamp when profile was deactivated'
    )
    deactivation_reason = fields.Text(
        'Deactivation Reason',
        help='Why this profile was deactivated'
    )

    # ===== Audit Fields (spec D10) =====
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

    # ===== SQL Constraints =====
    _sql_constraints = [
        (
            'document_company_type_unique',
            'UNIQUE(document, company_id, profile_type_id)',
            'Este documento já está cadastrado para este tipo de perfil nesta empresa.'
        ),
    ]

    # ===== Computed Fields =====
    @api.depends('document')
    def _compute_document_normalized(self):
        """Strip formatting from document to digits only via centralized normalize_document()."""
        for record in self:
            if record.document:
                record.document_normalized = validators.normalize_document(record.document)
            else:
                record.document_normalized = False

    # ===== Python Constraints =====
    @api.constrains('document')
    def _check_document(self):
        """Validate CPF/CNPJ using centralized validators (constitution, spec D11)."""
        for record in self:
            if record.document:
                normalized = validators.normalize_document(record.document)
                if not validators.validate_document(normalized):
                    raise ValidationError(
                        _('Documento inválido (CPF ou CNPJ): %s') % record.document
                    )

    @api.constrains('email')
    def _check_email(self):
        """Validate email format via centralized validator."""
        for record in self:
            if record.email and not validators.validate_email_format(record.email):
                raise ValidationError(_('Email inválido: %s') % record.email)

    @api.constrains('birthdate')
    def _check_birthdate(self):
        """Birthdate must be in the past."""
        for record in self:
            if record.birthdate and record.birthdate >= fields.Date.today():
                raise ValidationError(
                    _('Data de nascimento deve ser anterior à data atual.')
                )

    # ===== Methods =====
    @api.model
    def write(self, vals):
        """Override write to update updated_at timestamp."""
        vals['updated_at'] = fields.Datetime.now()
        return super(Profile, self).write(vals)

    @api.model
    def create(self, vals):
        """Override create to auto-create partner if needed."""
        # Auto-create partner_id if not provided (for portal/system access bridge)
        if not vals.get('partner_id') and vals.get('name') and vals.get('email'):
            partner = self.env['res.partner'].sudo().create({
                'name': vals['name'],
                'email': vals['email'],
                'phone': vals.get('phone'),
                'mobile': vals.get('mobile'),
            })
            vals['partner_id'] = partner.id
        
        return super(Profile, self).create(vals)
