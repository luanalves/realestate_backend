# -*- coding: utf-8 -*-
import logging
from odoo.http import request
from .response import error_response

_logger = logging.getLogger(__name__)


def require_jwt(func):
    """
    Decorator to require JWT authentication.
    Validates token and injects jwt_payload into request.
    
    Usage:
        @http.route('/api/v1/endpoint', ...)
        @require_jwt
        def my_endpoint(self, **kwargs):
            # jwt_payload is available in request.jwt_payload
            pass
    """
    def wrapper(*args, **kwargs):
        # Get Authorization header
        auth_header = request.httprequest.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return error_response(401, 'Missing or invalid Authorization header')
        
        access_token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Validate token using api_gateway
        try:
            token_model = request.env['thedevkitchen.oauth.token'].sudo()
            token = token_model.search([
                ('access_token', '=', access_token),
                ('revoked', '=', False)
            ], limit=1)
            
            if not token:
                return error_response(401, 'Invalid or revoked token')
            
            # Check if token is expired
            if token.is_expired:
                return error_response(401, 'Token expired')
            
            # Inject token payload into request
            request.jwt_payload = {
                'sub': token.application_id.client_id,
                'user_id': token.application_id.create_uid.id if token.application_id.create_uid else None,
                'scopes': ['read', 'write']  # TODO: Get from token
            }
            
            # Set user context from token
            if token.application_id.create_uid:
                request.update_env(user=token.application_id.create_uid.id)
            
        except Exception as e:
            _logger.error(f"Error validating JWT token: {e}")
            return error_response(401, 'Invalid token')
        
        return func(*args, **kwargs)
    
    return wrapper
