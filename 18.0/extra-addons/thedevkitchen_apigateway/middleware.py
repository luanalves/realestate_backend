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
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return _error_response(401, 'invalid_token', 'Authorization header must be "Bearer <token>"')
        
        token = parts[1]
        
        Token = request.env['thedevkitchen.oauth.token'].sudo()
        token_record = Token.search([('access_token', '=', token)], limit=1)
        
        if not token_record:
            return _error_response(401, 'invalid_token', 'Token not found or invalid')
        
        if token_record.token_type != 'Bearer':
            return _error_response(401, 'invalid_token', 'Token type must be Bearer')
        
        if token_record.expires_at and token_record.expires_at < fields.Datetime.now():
            return _error_response(401, 'token_expired', 'Token has expired')
        
        if token_record.revoked:
            return _error_response(401, 'token_revoked', 'Token has been revoked')
        
        request.jwt_token = token_record
        request.jwt_application = token_record.application_id
        
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
    from odoo.tools import config

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Try to get session_id from multiple sources
        session_id = None
        
        # 1. From kwargs (function parameters - highest priority for API calls)
        session_id = kwargs.get('session_id')
        
        # 2. From request body (for JSON-RPC calls)
        if not session_id:
            try:
                json_data = request.get_json_data()
                if json_data:
                    session_id = json_data.get('session_id')
            except Exception:
                pass
        
        # 3. From headers/cookies/session if not in body
        if not session_id:
            session_id = (
                request.httprequest.headers.get('X-Openerp-Session-Id') or
                request.httprequest.cookies.get('session_id') or
                request.session.sid
            )

        # Validate session_id format (length check)
        if session_id and (len(session_id) < 60 or len(session_id) > 100):
            return request.make_json_response({
                'error': {
                    'status': 401,
                    'message': 'Invalid session_id format (must be 60-100 characters)'
                }
            }, status=401)

        valid, user, api_session, error_msg = SessionValidator.validate(session_id)

        if not valid:
            return request.make_json_response({
                'error': {
                    'status': 401,
                    'message': error_msg or 'Session required'
                }
            }, status=401)

        # SECURITY: Validate JWT token (MANDATORY for APIs)
        # This prevents session hijacking by validating UID + fingerprint (IP/UA/Lang)
        # Token já foi buscado pelo SessionValidator (sem .sudo() duplicado)
        stored_token = api_session.security_token if api_session else None
        
        if not stored_token:
            _logger.warning(
                f'[SESSION SECURITY] No JWT token found for session {session_id[:16]}... '
                f'user_id={user.id}'
            )
            return request.make_json_response({
                'error': {
                    'status': 401,
                    'message': 'Session token required'
                }
            }, status=401)
        
        try:
            secret = config.get('database_secret') or config.get('admin_passwd')
            if not secret:
                _logger.critical("No secret configured for JWT validation (database_secret or admin_passwd required)")
                return request.make_json_response({
                    'error': {
                        'status': 500,
                        'message': 'Server configuration error'
                    }
                }, status=500)
            
            payload = jwt.decode(stored_token, secret, algorithms=['HS256'])
            token_uid = payload.get('uid')
            
            # Validate UID match
            if token_uid != user.id:
                _logger.warning(
                    f'[SESSION HIJACKING DETECTED - UID MISMATCH] '
                    f'JWT uid={token_uid} != session user_id={user.id} '
                    f'session_id={session_id[:16]}...'
                )
                return request.make_json_response({
                    'error': {
                        'status': 401,
                        'message': 'Session validation failed'
                    }
                }, status=401)
            
            # Validate fingerprint (IP/UA/Lang) for APIs
            token_fingerprint = payload.get('fingerprint', {})
            current_ip = request.httprequest.remote_addr
            current_ua = request.httprequest.headers.get('User-Agent', '')
            current_lang = request.httprequest.headers.get('Accept-Language', '')
            
            if token_fingerprint.get('ip') and token_fingerprint.get('ip') != current_ip:
                _logger.warning(
                    f'[SESSION HIJACKING DETECTED - IP MISMATCH] '
                    f'Token IP={token_fingerprint.get("ip")} != Current IP={current_ip} '
                    f'user_id={user.id} session_id={session_id[:16]}...'
                )
                return request.make_json_response({
                    'error': {
                        'status': 401,
                        'message': 'Session validation failed'
                    }
                }, status=401)
            
            if token_fingerprint.get('ua') and token_fingerprint.get('ua') != current_ua:
                _logger.warning(
                    f'[SESSION HIJACKING DETECTED - USER-AGENT MISMATCH] '
                    f'user_id={user.id} session_id={session_id[:16]}...'
                )
                return request.make_json_response({
                    'error': {
                        'status': 401,
                        'message': 'Session validation failed'
                    }
                }, status=401)
            
            if token_fingerprint.get('lang') and token_fingerprint.get('lang') != current_lang:
                _logger.warning(
                    f'[SESSION HIJACKING DETECTED - LANGUAGE MISMATCH] '
                    f'user_id={user.id} session_id={session_id[:16]}...'
                )
                return request.make_json_response({
                    'error': {
                        'status': 401,
                        'message': 'Session validation failed'
                    }
                }, status=401)
            
        except jwt.ExpiredSignatureError:
            _logger.warning(f'JWT token expired for session {session_id[:16]}...')
            return request.make_json_response({
                'error': {
                    'status': 401,
                    'message': 'Session expired'
                }
            }, status=401)
        except jwt.InvalidTokenError as e:
            _logger.warning(f'Invalid JWT token for session {session_id[:16]}...: {e}')
            return request.make_json_response({
                'error': {
                    'status': 401,
                    'message': 'Invalid session token'
                }
            }, status=401)

        request.env = request.env(user=user)
        return func(*args, **kwargs)

    return wrapper


def require_company(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user = request.env.user

        if user.has_group('base.group_system'):
            request.company_domain = []
            request.user_company_ids = []  # Admin has access to all companies
            return func(*args, **kwargs)

        if not user.estate_company_ids:
            _logger.warning(f'User {user.login} has no companies')
            return _error_response(403, 'no_company', 'User has no company access')

        request.company_domain = [('company_ids', 'in', user.estate_company_ids.ids)]
        request.user_company_ids = user.estate_company_ids.ids

        return func(*args, **kwargs)

    return wrapper

def require_csrf(func):
    """
    Middleware para validar token CSRF em operações sensíveis
    Use em endpoints POST, PUT, DELETE
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Apenas para métodos que modificam dados
        if request.httprequest.method not in ('POST', 'PUT', 'DELETE', 'PATCH'):
            return func(*args, **kwargs)
        
        from .services.csrf_service import CSRFService
        
        # Obtém token do header ou body
        csrf_token = (
            request.httprequest.headers.get('X-CSRF-Token') or
            request.jsonrequest.get('csrf_token') if hasattr(request, 'jsonrequest') and request.jsonrequest else None
        )
        
        # Valida token
        is_valid, error_msg = CSRFService.validate_token(csrf_token)
        
        if not is_valid:
            _logger.warning(f'CSRF validation failed: {error_msg}')
            return _error_response(
                403,
                'csrf_invalid',
                error_msg or 'CSRF token validation failed'
            )
        
        return func(*args, **kwargs)
    
    return wrapper
