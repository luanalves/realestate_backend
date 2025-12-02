# -*- coding: utf-8 -*-
"""
JWT Authentication Middleware for API Gateway

This module provides decorators and utilities for protecting API endpoints
with JWT authentication.
"""

import jwt
import json
import logging
import functools
from datetime import datetime
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


def require_jwt(func):
    """
    Decorator to protect endpoints with JWT authentication
    
    Usage in controllers:
        @http.route('/api/v1/protected', auth='none', methods=['GET'], csrf=False)
        @require_jwt
        def protected_endpoint(self, **kwargs):
            # Access authenticated application via request.jwt_application
            # Access token info via request.jwt_token
            return {'message': 'Success'}
    
    Returns:
        - 401 if no token provided
        - 401 if token is invalid
        - 401 if token is expired
        - 200 with original function result if authenticated
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get Authorization header
        auth_header = request.httprequest.headers.get('Authorization')
        
        if not auth_header:
            return _error_response(401, 'unauthorized', 'Authorization header is required')
        
        # Extract token from "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return _error_response(401, 'invalid_token', 'Authorization header must be "Bearer <token>"')
        
        token = parts[1]
        
        # Validate token
        Token = request.env['thedevkitchen.oauth.token'].sudo()
        token_record = Token.search([
            ('access_token', '=', token),
            ('token_type', '=', 'Bearer'),
        ], limit=1)
        
        if not token_record:
            return _error_response(401, 'invalid_token', 'Token not found or invalid')
        
        # Check if token is expired (compare UTC-aware datetimes)
        if token_record.expires_at and token_record.expires_at < fields.Datetime.now():
            return _error_response(401, 'token_expired', 'Token has expired')
        
        # Check if token is revoked
        if token_record.revoked:
            return _error_response(401, 'token_revoked', 'Token has been revoked')
        
        # Token is valid - attach to request for use in endpoint
        request.jwt_token = token_record
        request.jwt_application = token_record.application_id
        
        # Call the original function
        return func(*args, **kwargs)
    
    return wrapper


def require_jwt_with_scope(*required_scopes):
    """
    Decorator to protect endpoints with JWT authentication and scope validation
    
    Usage:
        @http.route('/api/v1/admin', auth='none', methods=['GET'], csrf=False)
        @require_jwt_with_scope('admin', 'write')
        def admin_endpoint(self, **kwargs):
            return {'message': 'Admin access granted'}
    
    Args:
        *required_scopes: Variable number of scope strings required
    
    Returns:
        - 401 if not authenticated
        - 403 if authenticated but missing required scopes
        - 200 with original function result if authorized
    """
    def decorator(func):
        @functools.wraps(func)
        @require_jwt
        def wrapper(*args, **kwargs):
            # Get token scopes
            token_scopes = request.jwt_token.scope.split() if request.jwt_token.scope else []
            
            # Check if all required scopes are present
            missing_scopes = [s for s in required_scopes if s not in token_scopes]
            
            if missing_scopes:
                return _error_response(
                    403, 
                    'insufficient_scope', 
                    f'Missing required scopes: {", ".join(missing_scopes)}'
                )
            
            # All scopes present - call original function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def log_api_access(endpoint_path, method, status_code, response_time=None):
    """
    Helper function to log API access
    
    Args:
        endpoint_path: API endpoint path (e.g., /api/v1/properties)
        method: HTTP method (GET, POST, etc.)
        status_code: HTTP status code (200, 401, etc.)
        response_time: Response time in milliseconds (optional)
    """
    try:
        # Find endpoint registration
        Endpoint = request.env['api.endpoint'].sudo()
        endpoint = Endpoint.search([
            ('path', '=', endpoint_path),
            ('method', '=', method)
        ], limit=1)
        
        if endpoint:
            # Increment call counter
            endpoint.increment_call_count()
        
        # Create access log
        AccessLog = request.env['api.access.log'].sudo()
        
        # Get client info
        ip_address = request.httprequest.remote_addr
        user_agent = request.httprequest.headers.get('User-Agent', '')
        
        # Prepare log data
        log_data = {
            'endpoint_path': endpoint_path,
            'method': method,
            'status_code': status_code,
            'response_time': response_time,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'authenticated': hasattr(request, 'jwt_token'),
        }
        
        # Add auth info if available
        if hasattr(request, 'jwt_application'):
            log_data['application_id'] = request.jwt_application.id
        if hasattr(request, 'jwt_token'):
            log_data['token_id'] = request.jwt_token.id
        
        # Add endpoint if found
        if endpoint:
            log_data['endpoint_id'] = endpoint.id
        
        # Create log entry
        AccessLog.create(log_data)
        
    except Exception as e:
        # Don't let logging errors break the API
        _logger.exception("Error creating API access log: %s", str(e))


def _error_response(status_code, error_code, error_description):
    """
    Helper to return standardized error responses
    
    Args:
        status_code: HTTP status code (401, 403, etc.)
        error_code: OAuth 2.0 error code (invalid_token, insufficient_scope, etc.)
        error_description: Human-readable error description
    
    Returns:
        Response object with proper headers and status
    """
    response = request.make_json_response({
        'error': error_code,
        'error_description': error_description
    }, status=status_code)
    
    response.headers['Content-Type'] = 'application/json'
    return response


def validate_json_schema(schema):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                if not request.jsonrequest:
                    return _error_response(400, 'invalid_request', 'Request body must be JSON')

                return func(*args, **kwargs)

            except Exception as e:
                return _error_response(400, 'validation_error', str(e))

        return wrapper
    return decorator


def require_session(func):
    from .services.session_validator import SessionValidator

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        session_id = (
            request.httprequest.headers.get('X-Openerp-Session-Id') or
            request.httprequest.cookies.get('session_id') or
            request.session.sid
        )

        valid, user, error_msg = SessionValidator.validate(session_id)

        if not valid:
            return {
                'error': {
                    'status': 401,
                    'message': error_msg or 'Unauthorized'
                }
            }

        request.env = request.env(user=user)
        return func(*args, **kwargs)

    return wrapper

