# -*- coding: utf-8 -*-
import logging
from odoo.http import request
from .response import error_response

_logger = logging.getLogger(__name__)


def require_jwt(func):
    """
    Decorator to require JWT authentication.
    Validates token and injects jwt_payload into request.
    
    STRATEGY: Stateless JWT validation first (for test mode), fallback to database lookup
    - Test mode: Tokens not saved to DB (read-only transactions)
    - Production: Database lookup for revocation checking
    
    Usage:
        @http.route('/api/v1/endpoint', ...)
        @require_jwt
        def my_endpoint(self, **kwargs):
            # jwt_payload is available in request.jwt_payload
            pass
    """
    def wrapper(*args, **kwargs):
        import jwt
        from odoo.tools import config
        
        # Get Authorization header
        auth_header = request.httprequest.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return error_response(401, 'Missing or invalid Authorization header')
        
        access_token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # FIRST: Try stateless JWT validation (works in test mode)
        try:
            jwt_secret = config.get('oauth_jwt_secret') or config.get('admin_passwd')
            if not jwt_secret:
                _logger.critical("No JWT secret configured (oauth_jwt_secret or admin_passwd required)")
                return error_response(500, 'Server configuration error')
            
            # Decode and validate JWT
            payload = jwt.decode(access_token, jwt_secret, algorithms=['HS256'])
            
            # Get application from client_id in JWT
            app_model = request.env['thedevkitchen.oauth.application'].sudo()
            app = app_model.search([('client_id', '=', payload.get('client_id'))], limit=1)
            
            if not app:
                _logger.warning(f"JWT valid but application not found: {payload.get('client_id')}")
                return error_response(401, 'Invalid token')
            
            # Inject token payload into request
            request.jwt_payload = {
                'sub': app.client_id,
                'user_id': app.create_uid.id if app.create_uid else None,
                'scopes': ['read', 'write']  # TODO: Get from token
            }
            
            # Set user context from token
            if app.create_uid:
                request.update_env(user=app.create_uid.id)
            
            return func(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return error_response(401, 'Token expired')
        except jwt.InvalidTokenError as e:
            _logger.debug(f"JWT validation failed, trying database lookup: {e}")
            # Fall through to database validation
        
        # FALLBACK: Database token lookup (production mode, revocation checking)
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
