# -*- coding: utf-8 -*-
"""
Password Service

Handles password set/reset logic and session invalidation.

Author: TheDevKitchen
Date: 2026-02-16
ADRs: ADR-008 (Anti-enumeration), ADR-015 (Soft Delete)
"""

import logging
from odoo import _, fields
from odoo.exceptions import ValidationError
from .token_service import PasswordTokenService

_logger = logging.getLogger(__name__)


class PasswordService:
    """Service for password set/reset operations"""
    
    def __init__(self, env):
        self.env = env
        self.token_service = PasswordTokenService(env)
    
    def set_password(self, raw_token, password, confirm_password, ip_address=None, user_agent=None):
        """
        Set password for a user using invite token.
        
        Args:
            raw_token: Plain token from email link
            password: New password
            confirm_password: Password confirmation
            ip_address: Request IP (audit)
            user_agent: Request User-Agent (audit)
        
        Returns:
            res.users record
        
        Raises:
            ValidationError: on invalid token or password validation failure
        """
        # Validate password
        if len(password) < 8:
            raise ValidationError(_('Password must be at least 8 characters'))
        
        if password != confirm_password:
            raise ValidationError(_('Password and confirmation do not match'))
        
        # Validate token
        validation = self.token_service.validate_token(raw_token)
        
        if not validation['valid']:
            error = validation['error']
            if error == 'not_found':
                raise ValidationError(_('Token not found'))
            elif error == 'expired':
                raise ValidationError(_('Token has expired'))
            elif error in ('used', 'invalidated'):
                raise ValidationError(_('Token has already been used'))
            else:
                raise ValidationError(_('Invalid token'))
        
        user = validation['user']
        token_record = validation['token_record']
        
        # Set password
        user.sudo().write({
            'password': password,
            'signup_pending': False,
        })
        
        # Mark token as used
        token_record.sudo().write({
            'status': 'used',
            'used_at': fields.Datetime.now(),
            'ip_address': ip_address,
            'user_agent': user_agent,
        })
        
        _logger.info(f'Password set for user {user.login} via invite token')
        
        return user
    
    def forgot_password(self, email):
        """
        Handle forgot password request.
        Always returns success (anti-enumeration).
        Only sends email if user exists and is active.
        
        Args:
            email: User email
        """
        # Find user (NEVER reveal if email exists)
        user = self.env['res.users'].sudo().search([
            ('login', '=', email),
            ('active', '=', True),
        ], limit=1)
        
        if not user:
            # Anti-enumeration: return success without sending email
            _logger.info(f'Forgot password requested for non-existent/inactive email: {email}')
            return
        
        # Invalidate previous reset tokens
        self.token_service.invalidate_previous_tokens(user.id, 'reset')
        
        # Generate new reset token
        company = user.estate_company_ids[0] if user.estate_company_ids else None
        raw_token, token_record = self.token_service.generate_token(
            user=user,
            token_type='reset',
            company=company
        )
        
        # Send reset email
        self._send_reset_email(user, raw_token)
        
        _logger.info(f'Password reset token generated for {email}')
    
    def reset_password(self, raw_token, password, confirm_password, ip_address=None, user_agent=None):
        """
        Reset password using reset token.
        Invalidates all active sessions after reset.
        
        Args:
            raw_token: Plain token from email link
            password: New password
            confirm_password: Password confirmation
            ip_address: Request IP (audit)
            user_agent: Request User-Agent (audit)
        
        Returns:
            res.users record
        
        Raises:
            ValidationError: on invalid token or password validation failure
        """
        # Validate password
        if len(password) < 8:
            raise ValidationError(_('Password must be at least 8 characters'))
        
        if password != confirm_password:
            raise ValidationError(_('Password and confirmation do not match'))
        
        # Validate token
        validation = self.token_service.validate_token(raw_token)
        
        if not validation['valid']:
            error = validation['error']
            if error == 'not_found':
                raise ValidationError(_('Token not found'))
            elif error == 'expired':
                raise ValidationError(_('Token has expired'))
            elif error in ('used', 'invalidated'):
                raise ValidationError(_('Token has already been used'))
            else:
                raise ValidationError(_('Invalid token'))
        
        user = validation['user']
        token_record = validation['token_record']
        
        # Set new password
        user.sudo().write({'password': password})
        
        # Mark token as used
        token_record.sudo().write({
            'status': 'used',
            'used_at': fields.Datetime.now(),
            'ip_address': ip_address,
            'user_agent': user_agent,
        })
        
        # Invalidate all active sessions (security requirement FR4.7)
        self._invalidate_user_sessions(user.id)
        
        _logger.info(f'Password reset successfully for user {user.login}')
        
        return user
    
    def _send_reset_email(self, user, raw_token):
        """
        Send password reset email by creating mail.mail directly with pre-rendered HTML.

        Odoo 18's inline_template engine restricts ctx.get() expressions
        in regex mode (non-admin users). We bypass this by rendering the
        HTML body in Python and creating mail.mail directly.
        """
        try:
            settings = self.env['thedevkitchen.email.link.settings'].get_settings()
            reset_link = f"{settings.frontend_base_url}/reset-password?token={raw_token}"
            expires_hours = settings.reset_link_ttl_hours
            user_name = user.name or user.login
            company_name = user.company_id.name or 'Sistema Imobiliário'
            company_email = user.company_id.email or 'noreply@thedevkitchen.com'

            subject = f"Recuperação de Senha - {company_name}"
            body_html = f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #dc3545; color: white; padding: 20px; text-align: center;">
        <h2>Recuperação de Senha</h2>
    </div>
    <div style="padding: 30px; background-color: #f9f9f9;">
        <p>Olá, <strong>{user_name}</strong>!</p>
        <p>Recebemos uma solicitação para redefinir sua senha no sistema <strong>{company_name}</strong>.</p>
        <p>Para criar uma nova senha, clique no botão abaixo:</p>
        <p style="text-align: center;">
            <a href="{reset_link}" style="display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px;">Redefinir Senha</a>
        </p>
        <p><strong>⚠️ Este link expira em {expires_hours} horas.</strong></p>
        <p>Se você não conseguir clicar no botão, copie e cole o link abaixo:</p>
        <p style="word-break: break-all; background-color: #fff; padding: 10px; border: 1px solid #ddd;">{reset_link}</p>
        <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 15px 0;">
            <p><strong>⚠️ Importante:</strong></p>
            <ul>
                <li>Se você não solicitou esta recuperação, ignore este email.</li>
                <li>Nunca compartilhe este link com outras pessoas.</li>
                <li>Todas as suas sessões ativas serão encerradas após a redefinição.</li>
            </ul>
        </div>
    </div>
    <div style="padding: 20px; text-align: center; font-size: 12px; color: #666;">
        <p>{company_name} - Todos os direitos reservados</p>
    </div>
</div>
"""

            mail_values = {
                'subject': subject,
                'body_html': body_html,
                'email_from': company_email,
                'email_to': user.email or user.login,
                'auto_delete': True,
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()

            _logger.info(f'Password reset email sent to {user.email}')

        except Exception as e:
            _logger.error(f'Failed to send password reset email to {user.email}: {e}')
    
    def _invalidate_user_sessions(self, user_id):
        """
        Invalidate all active sessions for a user.
        Sessions are stored in thedevkitchen.api.session (PostgreSQL).
        """
        try:
            sessions = self.env['thedevkitchen.api.session'].sudo().search([
                ('user_id', '=', user_id),
                ('is_active', '=', True),
            ])
            
            if sessions:
                sessions.write({'is_active': False})
                _logger.info(f'Invalidated {len(sessions)} active sessions for user ID {user_id}')
                
        except Exception as e:
            _logger.error(f'Failed to invalidate sessions for user ID {user_id}: {e}')
