import json
import jwt
import os
import logging
from datetime import datetime, timedelta
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AuthController(http.Controller):
    """OAuth 2.0 Authentication Controller"""

    @http.route('/api/v1/auth/token', type='http', auth='none', methods=['POST'], csrf=False)
    def token(self, **kwargs):
        """
        OAuth 2.0 Token Endpoint (Client Credentials Grant)
        
        POST /api/v1/auth/token
        Content-Type: application/json OR application/x-www-form-urlencoded
        
        JSON Body:
        {
            "grant_type": "client_credentials",
            "client_id": "xxx",
            "client_secret": "yyy"
        }
        
        Returns:
        {
            "access_token": "eyJ...",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "xxx"
        }
        """
        try:
            _logger.info("=== OAuth Token Request Started ===")
            _logger.info(f"Content-Type: {request.httprequest.content_type}")
            _logger.info(f"Request data (raw): {request.httprequest.data[:200]}")
            _logger.info(f"Kwargs: {kwargs}")
            
            # Accept both JSON and form data
            data = kwargs
            if request.httprequest.content_type == 'application/json':
                try:
                    data = json.loads(request.httprequest.data.decode('utf-8'))
                    _logger.info(f"Parsed JSON data (full): {data}")
                except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
                    _logger.warning(f"JSON parsing failed: {e}, falling back to kwargs")
                    # Fall back to kwargs if JSON parsing fails
                    pass
            
            grant_type = data.get('grant_type')
            client_id = data.get('client_id')
            client_secret = data.get('client_secret')

            _logger.info(f"Grant type: {grant_type}, Client ID: {client_id}, Secret: {client_secret[:10] if client_secret else None}...")

            # Validate grant type
            if grant_type != 'client_credentials':
                _logger.warning(f"Invalid grant type: {grant_type}")
                return self._error_response('unsupported_grant_type', 'Only client_credentials grant is supported')

            # Validate client credentials
            if not client_id or not client_secret:
                _logger.warning(f"Missing credentials - client_id: {bool(client_id)}, client_secret: {bool(client_secret)}")
                _logger.error(f"Full data dict: {data}")
                return self._error_response('invalid_request', 'client_id and client_secret are required')

            # Find application by client_id only (we'll verify secret separately)
            _logger.info(f"Searching for application with client_id: {client_id}")
            Application = request.env['thedevkitchen.oauth.application'].sudo()
            application = Application.search([
                ('client_id', '=', client_id),
                ('active', '=', True),
            ], limit=1)

            _logger.info(f"Application found: {bool(application)}")
            
            # Verify client secret using bcrypt hash comparison
            if not application:
                _logger.warning(f"No application found for client_id: {client_id}")
                return self._error_response('invalid_client', 'Invalid client credentials')
            
            _logger.info("Verifying client secret...")
            if not application.verify_secret(client_secret):
                _logger.warning("Client secret verification failed")
                return self._error_response('invalid_client', 'Invalid client credentials')

            _logger.info("Generating access token...")
            # Generate tokens
            access_token, expires_in = self._generate_access_token(application)
            refresh_token = self._generate_refresh_token()

            # Store token in database (skip if in test mode to avoid read-only transaction errors)
            test_mode = request.env.context.get('test_mode') or request.registry.in_test_mode()
            if not test_mode:
                _logger.info("Storing token in database...")
                Token = request.env['thedevkitchen.oauth.token'].sudo()
                try:
                    Token.create({
                        'application_id': application.id,
                        'access_token': access_token,
                        'refresh_token': refresh_token,
                        'expires_at': datetime.now() + timedelta(seconds=expires_in),
                        'token_type': 'Bearer',
                        'active': True,
                    })
                except Exception as token_error:
                    _logger.error(f"Failed to create token in database: {str(token_error)}", exc_info=True)
                    # Rollback the current transaction
                    request.env.cr.rollback()
                    raise
            else:
                _logger.info("Test mode detected, skipping token database storage")

            _logger.info("=== OAuth Token Request Successful ===")
            # Return token response
            return request.make_json_response({
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': expires_in,
                'refresh_token': refresh_token,
            })

        except Exception as e:
            _logger.error(f"=== OAuth Token Request Failed ===")
            _logger.error(f"Exception type: {type(e).__name__}")
            _logger.error(f"Exception message: {str(e)}", exc_info=True)
            return self._error_response('server_error', str(e))

    @http.route('/api/v1/auth/revoke', type='http', auth='none', methods=['POST'], csrf=False)
    def revoke(self, **kwargs):
        """
        OAuth 2.0 Token Revocation Endpoint (RFC 7009)
        
        POST /api/v1/auth/revoke
        
        Option 1 - Token in Body:
        Content-Type: application/json
        {
            "token": "xxx",
            "token_type_hint": "access_token" (optional)
        }
        
        Option 2 - Token in Header:
        Authorization: Bearer xxx
        """
        try:
            # Accept both JSON and form data
            data = kwargs
            if request.httprequest.content_type == 'application/json':
                try:
                    data = json.loads(request.httprequest.data.decode('utf-8'))
                except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
                    # Fall back to kwargs if JSON parsing fails
                    pass
            
            # Try to get token from body first, then from Authorization header
            token = data.get('token')
            
            if not token:
                # Try to get from Authorization header
                auth_header = request.httprequest.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:]  # Remove 'Bearer ' prefix
            
            if not token:
                return self._error_response('invalid_request', 'token parameter is required (in body or Authorization header)')

            # Find and revoke token
            Token = request.env['thedevkitchen.oauth.token'].sudo()
            token_record = Token.search([
                ('access_token', '=', token),
            ], limit=1)

            if token_record:
                token_record.action_revoke()

            # RFC 7009: Always return success even if token not found
            return request.make_json_response({'success': True})

        except Exception as e:
            return self._error_response('server_error', str(e))

    @http.route('/api/v1/auth/refresh', type='http', auth='none', methods=['POST'], csrf=False)
    def refresh(self, **kwargs):
        """
        OAuth 2.0 Token Refresh Endpoint
        
        POST /api/v1/auth/refresh
        Content-Type: application/json OR application/x-www-form-urlencoded
        
        JSON Body:
        {
            "refresh_token": "xxx" (required),
            "grant_type": "refresh_token" (optional, default),
            "client_id": "xxx" (optional),
            "client_secret": "yyy" (optional)
        }
        
        Returns:
        {
            "access_token": "eyJ...",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "xxx" (same as before)
        }
        """
        try:
            # Accept both JSON and form data
            data = kwargs
            if request.httprequest.content_type == 'application/json':
                try:
                    data = json.loads(request.httprequest.data.decode('utf-8'))
                except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
                    # Fall back to kwargs if JSON parsing fails
                    pass
            
            grant_type = data.get('grant_type', 'refresh_token')  # Default to refresh_token
            refresh_token = data.get('refresh_token')
            client_id = data.get('client_id')
            client_secret = data.get('client_secret')

            # Validate grant type (if provided)
            if grant_type and grant_type != 'refresh_token':
                return self._error_response('unsupported_grant_type', 'Only refresh_token grant is supported')

            # Validate refresh token
            if not refresh_token:
                return self._error_response('invalid_request', 'refresh_token is required')

            # Find token by refresh_token
            Token = request.env['thedevkitchen.oauth.token'].sudo()
            token_record = Token.search([
                ('refresh_token', '=', refresh_token),
            ], limit=1)

            if not token_record:
                return self._error_response('invalid_grant', 'Invalid refresh token')

            # Check if token is revoked
            if token_record.revoked:
                return self._error_response('invalid_grant', 'Refresh token has been revoked')

            # Validate client credentials if provided (verify secret using bcrypt)
            application = token_record.application_id
            if client_id and client_secret:
                if application.client_id != client_id or not application.verify_secret(client_secret):
                    return self._error_response('invalid_client', 'Invalid client credentials')

            # Check if application is still active
            if not application.active:
                return self._error_response('invalid_client', 'Application is inactive')

            # Generate new access token (reuse same refresh token)
            access_token, expires_in = self._generate_access_token(application)

            # Update token record with new access token
            token_record.write({
                'access_token': access_token,
                'expires_at': datetime.utcnow() + timedelta(seconds=expires_in),
                'last_used': datetime.utcnow(),
            })

            # Return new access token
            return request.make_json_response({
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': expires_in,
                'refresh_token': refresh_token,  # Same refresh token
            })

        except Exception as e:
            return self._error_response('server_error', str(e))

    def _generate_access_token(self, application):
        """Generate JWT access token"""
        import secrets
        
        # Get JWT secret from environment variable
        secret = os.getenv('JWT_SECRET')
        
        _logger.info(f"JWT_SECRET from env: {'SET' if secret else 'NOT SET'}")
        
        if not secret:
            _logger.error("JWT_SECRET not configured!")
            raise ValueError(
                'JWT secret not configured. Please set the environment variable: JWT_SECRET'
            )
        
        try:
            expires_in = 3600  # 1 hour
            payload = {
                'client_id': application.client_id,
                'exp': datetime.utcnow() + timedelta(seconds=expires_in),
                'iat': datetime.utcnow(),
                'iss': os.getenv('JWT_ISSUER', 'thedevkitchen-api-gateway'),
                'sub': application.client_id,
                'jti': secrets.token_urlsafe(16),  # JWT ID único para evitar duplicatas
            }
            
            _logger.info(f"Encoding JWT with payload: {payload}")
            token = jwt.encode(payload, secret, algorithm='HS256')
            _logger.info("JWT encoded successfully")
            return token, expires_in
        except Exception as e:
            _logger.error(f"Failed to generate JWT token: {str(e)}", exc_info=True)
            raise

    def _generate_refresh_token(self):
        """Generate refresh token"""
        import secrets
        return secrets.token_urlsafe(32)

    def _error_response(self, error, error_description=None):
        """Return OAuth 2.0 error response"""
        response = {'error': error}
        if error_description:
            response['error_description'] = error_description
        return request.make_json_response(response, status=400)
