# -*- coding: utf-8 -*-

import logging
from odoo import _
from odoo.exceptions import UserError, ValidationError
from validate_docbr import CPF

_logger = logging.getLogger(__name__)


class InviteService:
    """Service for managing user invitations"""
    
    # Authorization Matrix (ADR-024): Who can invite which profiles
    INVITE_AUTHORIZATION = {
        'quicksol_estate.group_real_estate_owner': ['owner', 'director', 'manager', 'agent', 'prospector', 'receptionist', 'financial', 'legal', 'property_owner', 'tenant'],
        'quicksol_estate.group_real_estate_director': ['agent', 'prospector', 'receptionist', 'financial', 'legal'],
        'quicksol_estate.group_real_estate_manager': ['agent', 'prospector', 'receptionist', 'financial', 'legal'],
        'quicksol_estate.group_real_estate_agent': ['property_owner', 'tenant'],
    }
    
    # Profile to Odoo Group Mapping (ADR-024)
    PROFILE_TO_GROUP = {
        'owner': 'quicksol_estate.group_real_estate_owner',
        'director': 'quicksol_estate.group_real_estate_director',
        'manager': 'quicksol_estate.group_real_estate_manager',
        'agent': 'quicksol_estate.group_real_estate_agent',
        'prospector': 'quicksol_estate.group_real_estate_prospector',
        'receptionist': 'quicksol_estate.group_real_estate_receptionist',
        'financial': 'quicksol_estate.group_real_estate_financial',
        'legal': 'quicksol_estate.group_real_estate_legal',
        'portal': 'base.group_portal',  # Legacy
        'tenant': 'base.group_portal',  # Portal user - tenant profile
        'property_owner': 'base.group_portal',  # Portal user - property owner profile
    }
    
    def __init__(self, env):
        self.env = env
    
    def check_authorization(self, requester_user, target_profile):

        # Get requester's group IDs
        requester_group_ids = requester_user.groups_id.ids
        
        # Check each authorization rule
        for group_xml_id, allowed_profiles in self.INVITE_AUTHORIZATION.items():
            group = self.env.ref(group_xml_id, raise_if_not_found=False)
            if group and group.id in requester_group_ids:
                if target_profile in allowed_profiles:
                    return True
        
        # Not authorized
        raise UserError(_(
            'You do not have permission to invite {} profile. '
            'Contact your administrator for assistance.'
        ).format(target_profile))
    
    def create_invited_user(self, name, email, document, profile, company, created_by, **extra_fields):

        # Validate document (CPF for non-portal profiles)
        if profile != 'portal':
            self._validate_cpf(document)
        
        # Check email uniqueness
        existing_email = self.env['res.users'].sudo().search([
            ('login', '=', email)
        ], limit=1)
        if existing_email:
            raise ValidationError(_('Email already exists: {}').format(email))
        
        # Check document uniqueness
        if profile != 'portal':
            existing_cpf = self.env['res.users'].sudo().search([
                ('cpf', '=', document)
            ], limit=1)
            if existing_cpf:
                raise ValidationError(_('CPF already exists: {}').format(document))
        
        # Get target group
        group_xml_id = self.PROFILE_TO_GROUP.get(profile)
        if not group_xml_id:
            raise ValidationError(_('Invalid profile: {}').format(profile))
        
        target_group = self.env.ref(group_xml_id)
        
        # Prepare user data
        user_vals = {
            'name': name,
            'login': email,
            'email': email,
            'password': False,  # No password yet
            'signup_pending': True,  # Waiting for invite link
            'groups_id': [(6, 0, [target_group.id])],
            'company_ids': [(4, company.id)] if hasattr(company, 'id') else [],
        }
        
        # Add CPF for non-portal profiles
        if profile != 'portal':
            user_vals['cpf'] = document
        
        # Add extra fields
        if extra_fields.get('phone'):
            user_vals['phone'] = extra_fields['phone']
        if extra_fields.get('mobile'):
            user_vals['mobile'] = extra_fields['mobile']
        
        # Create user
        new_user = self.env['res.users'].sudo().create(user_vals)
        
        _logger.info(
            f'User invited: {email} (profile: {profile}) by {created_by.login}'
        )
        
        return new_user
    
    def create_portal_user(self, name, email, document, phone, birthdate, company_id, 
                           created_by, occupation=None):

        # Validate required fields
        if not phone:
            raise ValidationError(_('Phone is required for portal profile'))
        if not birthdate:
            raise ValidationError(_('Birthdate is required for portal profile'))
        if not company_id:
            raise ValidationError(_('Company ID is required for portal profile'))
        
        # Validate document (CPF or CNPJ for portal)
        self._validate_document_portal(document)
        
        # Check email uniqueness
        existing_email = self.env['res.users'].sudo().search([
            ('login', '=', email)
        ], limit=1)
        if existing_email:
            raise ValidationError(_('Email already exists: {}').format(email))
        
        # Check if document exists in tenant table without linked user (409 conflict)
        existing_tenant = self.env['real.estate.tenant'].sudo().search([
            ('document', '=', document)
        ], limit=1)
        if existing_tenant and not existing_tenant.user_id:
            raise ValidationError(_(
                'Document already registered for another tenant. '
                'Please link the existing tenant to a user account manually.'
            ))
        
        # Get portal group
        portal_group = self.env.ref('base.group_portal')
        
        # Step 1: Create res.users with portal group
        user_vals = {
            'name': name,
            'login': email,
            'email': email,
            'password': False,
            'signup_pending': True,
            'groups_id': [(6, 0, [portal_group.id])],
        }
        
        user = self.env['res.users'].sudo().create(user_vals)
        
        # Step 2: Create real.estate.tenant linked via partner_id
        # Note: res.users.create() automatically creates res.partner
        company = self.env['res.company'].sudo().browse(company_id)
        
        tenant_vals = {
            'name': name,
            'email': email,
            'document': document,
            'phone': phone,
            'birthdate': birthdate,
            'partner_id': user.partner_id.id,  # Link to auto-created partner
            'company_ids': [(4, company_id)],
            'user_id': user.id,  # Back-reference to res.users
        }
        
        if occupation:
            tenant_vals['occupation'] = occupation
        
        tenant = self.env['real.estate.tenant'].sudo().create(tenant_vals)
        
        _logger.info(
            f'Portal user + tenant created: {email} (tenant_id: {tenant.id}) '
            f'by {created_by.login}'
        )
        
        return user, tenant
    
    def create_user_from_profile(self, profile_record, created_by):
        """Feature 010: Create res.users from a unified thedevkitchen.estate.profile record.

        This replaces the old create_invited_user / create_portal_user split.
        The profile already holds all cadastral data; here we only create the
        user account and link it back to the profile via partner_id.

        Args:
            profile_record: thedevkitchen.estate.profile browse record
            created_by: res.users of the person performing the invite

        Returns:
            res.users record
        """
        profile_type_code = profile_record.profile_type_id.code
        email = profile_record.email

        # Check email uniqueness
        existing = self.env['res.users'].sudo().search(
            [('login', '=', email)], limit=1
        )
        if existing:
            raise ValidationError(
                _('Email already exists: {}').format(email)
            )

        # Resolve security group from profile type code
        group_xml_id = self.PROFILE_TO_GROUP.get(profile_type_code)
        if not group_xml_id:
            raise ValidationError(
                _('Unknown profile type: {}').format(profile_type_code)
            )
        target_group = self.env.ref(group_xml_id)

        # profile.company_id points to res.company
        estate_company = profile_record.company_id

        # Build user values — NO password field so account starts locked
        # (user sets password via invite token, not directly)
        user_vals = {
            'name': profile_record.name,
            'login': email,
            'email': email,
            'signup_pending': True,
            'groups_id': [(6, 0, [target_group.id])],
        }

        if estate_company:
            user_vals['company_ids'] = [(4, estate_company.id)]

        # Carry over phone if present
        if profile_record.phone:
            user_vals['phone'] = profile_record.phone

        new_user = self.env['res.users'].sudo().create(user_vals)

        # Link profile → user via partner_id (profile gains the auto-created partner)
        profile_record.sudo().write({'partner_id': new_user.partner_id.id})

        _logger.info(
            '[INVITE] User created from profile %s (profile_type=%s, email=%s) by %s',
            profile_record.id,
            profile_type_code,
            email,
            created_by.login,
        )

        return new_user

    def send_invite_email(self, user, raw_token, expires_hours, frontend_base_url):

        try:
            invite_link = f"{frontend_base_url}/set-password?token={raw_token}"
            user_name = user.name or user.login
            company_name = user.company_id.name or 'Sistema Imobiliário'
            company_email = user.company_id.email or 'noreply@thedevkitchen.com'

            subject = f"Convite para Criar Senha - {company_name}"
            body_html = f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #007bff; color: white; padding: 20px; text-align: center;">
        <h2>Bem-vindo(a) ao Sistema Imobiliário</h2>
    </div>
    <div style="padding: 30px; background-color: #f9f9f9;">
        <p>Olá, <strong>{user_name}</strong>!</p>
        <p>Você foi convidado(a) para acessar o sistema <strong>{company_name}</strong>.</p>
        <p>Para criar sua senha e ativar sua conta, clique no botão abaixo:</p>
        <p style="text-align: center;">
            <a href="{invite_link}" style="display: inline-block; padding: 12px 24px; background-color: #28a745; color: white; text-decoration: none; border-radius: 4px;">Criar Minha Senha</a>
        </p>
        <p><strong>⚠️ Este link expira em {expires_hours} horas.</strong></p>
        <p>Se você não conseguir clicar no botão, copie e cole o link abaixo:</p>
        <p style="word-break: break-all; background-color: #fff; padding: 10px; border: 1px solid #ddd;">{invite_link}</p>
        <p>Se você não solicitou este convite, ignore este email.</p>
    </div>
    <div style="padding: 20px; text-align: center; font-size: 12px; color: #666;">
        <p>{company_name} - Todos os direitos reservados</p>
    </div>
</div>
"""

            # Create mail.mail directly (bypasses template rendering restrictions)
            mail_values = {
                'subject': subject,
                'body_html': body_html,
                'email_from': company_email,
                'email_to': user.email or user.login,
                'auto_delete': True,
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()

            _logger.info(f'Invite email sent to {user.email}')
            return True

        except Exception as e:
            _logger.error(f'Failed to send invite email to {user.email}: {e}')
            return False
    
    # Private helper methods
    
    def _validate_cpf(self, cpf):
        """Validate CPF using validate_docbr"""
        cpf_validator = CPF()
        cpf_clean = ''.join(filter(str.isdigit, cpf))
        
        if not cpf_validator.validate(cpf_clean):
            raise ValidationError(_('Invalid CPF: {}. Must have 11 valid digits.').format(cpf))
    
    def _validate_document_portal(self, document):

        document_clean = ''.join(filter(str.isdigit, document))
        
        if len(document_clean) == 11:
            # CPF
            self._validate_cpf(document)
        elif len(document_clean) == 14:
            # CNPJ - Use existing quicksol_estate validator
            from ..utils import validators
            if hasattr(validators, 'validate_cnpj'):
                if not validators.validate_cnpj(document):
                    raise ValidationError(_('Invalid CNPJ: {}').format(document))
            else:
                # Fallback: basic length check
                _logger.warning('CNPJ validation unavailable - using basic length check')
        else:
            raise ValidationError(_(
                'Invalid document: {}. Must be CPF (11 digits) or CNPJ (14 digits).'
            ).format(document))
