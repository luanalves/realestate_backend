# -*- coding: utf-8 -*-
import jwt
import json
import logging
import functools
from datetime import datetime
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


def require_jwt(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
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
    def decorator(func):
        @functools.wraps(func)
        @require_jwt
        def wrapper(*args, **kwargs):
            token_scopes = request.jwt_token.scope.split() if request.jwt_token.scope else []

            missing_scopes = [s for s in required_scopes if s not in token_scopes]

            if missing_scopes:
                return _error_response(
                    403,
                    'insufficient_scope',
                    f'Missing required scopes: {", ".join(missing_scopes)}'
                )

            return func(*args, **kwargs)

        return wrapper
    return decorator


def log_api_access(endpoint_path, method, status_code, response_time=None):
    try:
        Endpoint = request.env['api.endpoint'].sudo()
        endpoint = Endpoint.search([
            ('path', '=', endpoint_path),
            ('method', '=', method)
        ], limit=1)

        if endpoint:
            endpoint.increment_call_count()

        AccessLog = request.env['api.access.log'].sudo()

        ip_address = request.httprequest.remote_addr
        user_agent = request.httprequest.headers.get('User-Agent', '')

        log_data = {
            'endpoint_path': endpoint_path,
            'method': method,
            'status_code': status_code,
            'response_time': response_time,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'authenticated': hasattr(request, 'jwt_token'),
        }

        if hasattr(request, 'jwt_application'):
            log_data['application_id'] = request.jwt_application.id
        if hasattr(request, 'jwt_token'):
            log_data['token_id'] = request.jwt_token.id

        if endpoint:
            log_data['endpoint_id'] = endpoint.id

        AccessLog.create(log_data)
        

    except Exception as e:
        _logger.exception("Error creating API access log: %s", str(e))


def _error_response(status_code, error_code, error_description):
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