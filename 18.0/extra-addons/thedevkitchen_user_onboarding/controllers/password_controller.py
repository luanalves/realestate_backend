# -*- coding: utf-8 -*-
"""
Password Controller

Handles password-related public endpoints:
- POST /api/v1/auth/set-password (for invite links)
- POST /api/v1/auth/forgot-password (request reset)
- POST /api/v1/auth/reset-password (reset with token)

All endpoints are public (no authentication required).

Author: TheDevKitchen
Date: 2026-02-16
ADRs: ADR-005 (API-First), ADR-008 (Anti-enumeration), ADR-011 (Public endpoints)
"""

import json
import logging
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import ValidationError
from ..services.password_service import PasswordService
from ..services.token_service import PasswordTokenService

_logger = logging.getLogger(__name__)


class PasswordController(http.Controller):
    
    @http.route('/api/v1/auth/set-password', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    # public endpoint - user sets password from invite link
    def set_password(self, **kwargs):
        """
        POST /api/v1/auth/set-password
        
        Set password for a user with a valid invite token.
        Public endpoint - no authentication required.
        
        Request Body:
        {
            "token": "string (required)",
            "password": "string (required, min 8 chars)",
            "confirm_password": "string (required, must match password)"
        }
        
        Returns:
            200: Password set successfully
            400: Validation error (password too short, mismatch, etc.)
            404: Token not found
            410: Token expired or already used
        """
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return self._error_response(400, 'validation_error', 'Invalid JSON in request body')
        
        # Validate required fields
        required_fields = ['token', 'password', 'confirm_password']
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return self._error_response(
                400,
                'validation_error',
                f'Missing required fields: {", ".join(missing)}'
            )
        
        password_service = PasswordService(request.env)
        
        try:
            ip_address = request.httprequest.remote_addr
            user_agent = request.httprequest.headers.get('User-Agent', '')
            
            password_service.set_password(
                raw_token=data['token'],
                password=data['password'],
                confirm_password=data['confirm_password'],
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return self._success_response(
                200,
                None,
                'Password set successfully. You can now log in.',
                [{'href': '/api/v1/users/login', 'rel': 'login', 'type': 'POST'}]
            )
            
        except ValidationError as e:
            if 'not found' in str(e).lower():
                return self._error_response(404, 'not_found', 'Token not found')
            if 'expired' in str(e).lower():
                return self._error_response(
                    410,
                    'token_expired',
                    'This link has expired. Please request a new invite.'
                )
            if 'used' in str(e).lower():
                return self._error_response(
                    410,
                    'token_used',
                    'This link has already been used.'
                )
            return self._error_response(400, 'validation_error', str(e))
        except Exception as e:
            _logger.exception(f'Unexpected error in set_password: {e}')
            return self._error_response(500, 'internal_error', 'An unexpected error occurred')
    
    @http.route('/api/v1/auth/forgot-password', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    # public endpoint - request password reset link
    def forgot_password(self, **kwargs):
        """
        POST /api/v1/auth/forgot-password
        
        Request password reset link (anti-enumeration: always returns 200).
        Public endpoint - no authentication required.
        Rate limited: 3 requests per email per hour.
        
        Request Body:
        {
            "email": "string (required, valid email format)"
        }
        
        Returns:
            200: Always (whether email exists or not)
            400: Validation error (missing email, invalid format)
            429: Rate limit exceeded
        """
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return self._error_response(400, 'validation_error', 'Invalid JSON in request body')
        
        email = data.get('email')
        if not email:
            return self._error_response(400, 'validation_error', 'Email is required')
        
        if not self._validate_email_format(email):
            return self._error_response(400, 'validation_error', 'Invalid email format')
        
        password_service = PasswordService(request.env)
        token_service = PasswordTokenService(request.env)
        
        # Check rate limit
        rate_limit = token_service.check_rate_limit(email, token_type='reset')
        if not rate_limit['allowed']:
            return self._error_response(
                429,
                'rate_limited',
                'Too many requests. Please try again later.'
            )
        
        # Always return success (anti-enumeration per ADR-008)
        password_service.forgot_password(email)
        
        return self._success_response(
            200,
            None,
            'If this email is registered, a password reset link has been sent.'
        )
    
    @http.route('/api/v1/auth/reset-password', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    # public endpoint - reset password with token
    def reset_password(self, **kwargs):
        """
        POST /api/v1/auth/reset-password
        
        Reset password with valid reset token.
        Public endpoint - no authentication required.
        Invalidates all active sessions after reset.
        
        Request Body:
        {
            "token": "string (required)",
            "password": "string (required, min 8 chars)",
            "confirm_password": "string (required, must match password)"
        }
        
        Returns:
            200: Password reset successfully
            400: Validation error
            404: Token not found
            410: Token expired or already used
        """
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return self._error_response(400, 'validation_error', 'Invalid JSON in request body')
        
        required_fields = ['token', 'password', 'confirm_password']
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return self._error_response(
                400,
                'validation_error',
                f'Missing required fields: {", ".join(missing)}'
            )
        
        password_service = PasswordService(request.env)
        
        try:
            ip_address = request.httprequest.remote_addr
            user_agent = request.httprequest.headers.get('User-Agent', '')
            
            password_service.reset_password(
                raw_token=data['token'],
                password=data['password'],
                confirm_password=data['confirm_password'],
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return self._success_response(
                200,
                None,
                'Password reset successfully. You can now log in with your new password.',
                [{'href': '/api/v1/users/login', 'rel': 'login', 'type': 'POST'}]
            )
            
        except ValidationError as e:
            if 'not found' in str(e).lower():
                return self._error_response(404, 'not_found', 'Token not found')
            if 'expired' in str(e).lower():
                return self._error_response(
                    410,
                    'token_expired',
                    'This link has expired. Please request a new password reset.'
                )
            if 'used' in str(e).lower():
                return self._error_response(
                    410,
                    'token_used',
                    'This link has already been used.'
                )
            return self._error_response(400, 'validation_error', str(e))
        except Exception as e:
            _logger.exception(f'Unexpected error in reset_password: {e}')
            return self._error_response(500, 'internal_error', 'An unexpected error occurred')
    
    # Helper methods
    
    def _validate_email_format(self, email):
        """Basic email format validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _success_response(self, status_code, data, message, links=None):
        """Build success response"""
        response_body = {
            'success': True,
            'message': message,
        }
        if data is not None:
            response_body['data'] = data
        if links:
            response_body['links'] = links
        
        return Response(
            json.dumps(response_body, default=str),
            status=status_code,
            content_type='application/json'
        )
    
    def _error_response(self, status_code, error_type, message, details=None):
        """Build error response"""
        response_body = {
            'success': False,
            'error': error_type,
            'message': message,
        }
        if details:
            response_body['details'] = details
        
        return Response(
            json.dumps(response_body),
            status=status_code,
            content_type='application/json'
        )
