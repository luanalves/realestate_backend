# -*- coding: utf-8 -*-
"""
Invite Service

Handles user invitation logic including authorization matrix, profile-to-group mapping,
dual record creation for portal profile, and email dispatch.

Author: TheDevKitchen
Date: 2026-02-16
ADRs: ADR-004 (Naming), ADR-008 (Multi-tenancy), ADR-019 (RBAC)
"""

import logging
from odoo import _
from odoo.exceptions import UserError, ValidationError
from validate_docbr import CPF

_logger = logging.getLogger(__name__)


class InviteService:
    """Service for managing user invitations"""
    
    # Authorization Matrix (R11): Who can invite which profiles
    INVITE_AUTHORIZATION = {
        'quicksol_estate.group_real_estate_owner': ['owner', 'director', 'manager', 'agent', 'prospector', 'receptionist', 'financial', 'legal', 'portal'],
        'quicksol_estate.group_real_estate_director': ['agent', 'prospector', 'receptionist', 'financial', 'legal'],
        'quicksol_estate.group_real_estate_manager': ['agent', 'prospector', 'receptionist', 'financial', 'legal'],
        'quicksol_estate.group_real_estate_agent': ['owner', 'portal'],
    }
    
    # Profile to Odoo Group Mapping (R11)
    PROFILE_TO_GROUP = {
        'owner': 'quicksol_estate.group_real_estate_owner',
        'director': 'quicksol_estate.group_real_estate_director',
        'manager': 'quicksol_estate.group_real_estate_manager',
        'agent': 'quicksol_estate.group_real_estate_agent',
        'prospector': 'quicksol_estate.group_real_estate_prospector',
        'receptionist': 'quicksol_estate.group_real_estate_receptionist',
        'financial': 'quicksol_estate.group_real_estate_financial',
        'legal': 'quicksol_estate.group_real_estate_legal',
        'portal': 'base.group_portal',
    }
    
    def __init__(self, env):
        self.env = env
    
    def check_authorization(self, requester_user, target_profile):
        """
        Check if requester_user can invite target_profile.
        
        Args:
            requester_user: res.users record (the authenticated user)
            target_profile: string (e.g., 'manager', 'agent', 'portal')
        
        Returns:
            bool: True if authorized, raises UserError otherwise
        """
        # Get requester's groups
        requester_groups = requester_user.groups_id.mapped('complete_name')
        
        # Check each authorization rule
        for group_xml_id, allowed_profiles in self.INVITE_AUTHORIZATION.items():
            group = self.env.ref(group_xml_id, raise_if_not_found=False)
            if group and group.complete_name in requester_groups:
                if target_profile in allowed_profiles:
                    return True
        
        # Not authorized
        raise UserError(_(
            'You do not have permission to invite {} profile. '
            'Contact your administrator for assistance.'
        ).format(target_profile))
    
    def create_invited_user(self, name, email, document, profile, company, created_by, **extra_fields):
        """
        Create a new res.users with the specified profile (without password).
        Standard flow for non-portal profiles.
        
        Args:
            name: User full name
            email: User email (login)
            document: CPF (11 digits)
            profile: Profile name (e.g., 'manager', 'agent')
            company: thedevkitchen.estate.company record
            created_by: res.users record (who is inviting)
            **extra_fields: phone, mobile, etc.
        
        Returns:
            res.users record (new user)
        """
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
            'estate_company_ids': [(4, company.id)] if hasattr(company, 'id') else [],
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
        """
        Create portal user with dual record: res.users + real.estate.tenant.
        Atomic transaction ensures both records are created or neither.
        
        Args:
            name: User/tenant name
            email: User email
            document: CPF or CNPJ
            phone: Tenant phone (required)
            birthdate: Tenant birthdate (YYYY-MM-DD, required)
            company_id: thedevkitchen.estate.company ID (required)
            created_by: res.users record (who is inviting)
            occupation: Tenant occupation (optional)
        
        Returns:
            tuple: (user, tenant) records
        """
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
        company = self.env['thedevkitchen.estate.company'].sudo().browse(company_id)
        
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
    
    def send_invite_email(self, user, raw_token, expires_hours, frontend_base_url):
        """
        Send invite email using mail.template.
        
        Args:
            user: res.users record
            raw_token: Plain token string (not hashed)
            expires_hours: Token validity in hours
            frontend_base_url: Frontend URL for link construction
        
        Returns:
            bool: True if email sent/queued, False if failed
        """
        try:
            # Get email template
            template = self.env.ref('thedevkitchen_user_onboarding.email_template_user_invite')
            
            # Construct invite link
            invite_link = f"{frontend_base_url}/set-password?token={raw_token}"
            
            # Prepare template context
            ctx = {
                'invite_link': invite_link,
                'expires_hours': expires_hours,
            }
            
            # Send email (async via Odoo mail queue)
            template.with_context(ctx).send_mail(
                user.id,
                force_send=False,  # Queue for async sending
                raise_exception=False,  # Don't block on email failure
            )
            
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
        """
        Validate CPF or CNPJ for portal profile.
        Uses validate_docbr for CPF, custom logic for CNPJ.
        """
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
