from odoo import http, fields
from odoo.http import request
from ..services.rate_limiter import RateLimiter
from ..services.audit_logger import AuditLogger
from ..middleware import require_jwt
import logging

_logger = logging.getLogger(__name__)


class UserAuthController(http.Controller):

    @http.route('/api/v1/users/login', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    def login(self):
        ip_address = request.httprequest.remote_addr
        user_agent = request.httprequest.headers.get('User-Agent', 'Unknown')
        application = request.jwt_application
        
        email = request.get_json_data().get('email')
        password = request.get_json_data().get('password')

        try:
            _logger.info(f"Login attempt: {email} from {ip_address} by app: {application.name}")
            
            if not RateLimiter.check(ip_address, email):
                _logger.warning(f"Rate limit exceeded for {email}")
                AuditLogger.log_failed_login(ip_address, email, 'Rate limit exceeded')
                return {
                    'error': {
                        'status': 429,
                        'message': 'Too many login attempts. Try again in 15 minutes.'
                    }
                }

            _logger.info(f"Searching for user: {email}")
            users = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
            _logger.info(f"Search result: {users}")

            if not users:
                _logger.warning(f"User not found: {email}")
                AuditLogger.log_failed_login(ip_address, email)
                return {
                    'error': {
                        'status': 401,
                        'message': 'Invalid credentials'
                    }
                }

            user = users[0]
            _logger.info(f"User found: {user.login}, active: {user.active}")

            if not user.active:
                _logger.warning(f"User inactive: {email}")
                AuditLogger.log_failed_login(ip_address, email, 'User inactive')
                return {
                    'error': {
                        'status': 403,
                        'message': 'User inactive'
                    }
                }

            _logger.info(f"Authenticating user: {email}")
            
            # Usar a validação nativa do Odoo
            try:
                # Odoo's Session.authenticate(dbname, credential_dict)
                # credential_dict must have 'type' key with authentication method
                credential = {
                    'type': 'password',
                    'login': email,
                    'password': password
                }
                auth_info = request.session.authenticate(request.env.cr.dbname, credential)
                _logger.info(f"Authentication result: uid={auth_info.get('uid')}")
                
                uid = auth_info.get('uid')
                if not uid or uid == -1:
                    _logger.warning(f"Auth failed for {email}: uid={uid}")
                    AuditLogger.log_failed_login(ip_address, email)
                    return {
                        'error': {
                            'status': 401,
                            'message': 'Invalid credentials'
                        }
                    }
                
                if not uid:
                    _logger.warning(f"Auth failed for {email}: authentication returned False")
                    AuditLogger.log_failed_login(ip_address, email)
                    return {
                        'error': {
                            'status': 401,
                            'message': 'Invalid credentials'
                        }
                    }
            except Exception as auth_error:
                _logger.error(f"Auth exception for {email}: {type(auth_error).__name__}: {auth_error}")
                AuditLogger.log_failed_login(ip_address, email, str(auth_error))
                return {
                    'error': {
                        'status': 401,
                        'message': 'Invalid credentials'
                    }
                }

            _logger.info(f"Checking companies for user {email}")
            has_companies = bool(user.estate_company_ids)
            is_system_admin = user.has_group('base.group_system')
            _logger.info(f"User {email}: has_companies={has_companies}, is_system_admin={is_system_admin}")
            
            if not has_companies and not is_system_admin:
                _logger.warning(f"User has no companies: {email}")
                AuditLogger.log_failed_login(ip_address, email, 'No companies')
                return {
                    'error': {
                        'status': 403,
                        'message': 'User has no companies assigned'
                    }
                }

            session_id = request.session.sid
            _logger.info(f"Creating API session for user {email}, session_id: {session_id}")

            request.env['thedevkitchen.api.session'].sudo().create({
                'session_id': session_id,
                'user_id': user.id,
                'ip_address': ip_address,
                'user_agent': user_agent,
            })

            AuditLogger.log_successful_login(ip_address, email, user.id)
            RateLimiter.clear(ip_address, email)

            _logger.info(f"Login successful for {email}")
            _logger.info(f"Building user response...")
            
            try:
                user_response = self._build_user_response(user)
                _logger.info(f"User response built: {user_response}")
            except Exception as build_error:
                _logger.error(f"Error building user response: {type(build_error).__name__}: {build_error}", exc_info=True)
                raise
            
            return {
                'session_id': session_id,
                'user': user_response
            }

        except Exception as e:
            AuditLogger.log_error('user.login', email, str(e))
            return {
                'error': {
                    'status': 500,
                    'message': 'Internal server error'
                }
            }

    @http.route('/api/v1/users/logout', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    def logout(self):
        try:
            session_id = request.get_json_data().get('session_id')
            ip_address = request.httprequest.remote_addr
            
            _logger.info(f"Logout attempt for session_id: {session_id} from {ip_address}")
            
            if not session_id:
                _logger.warning(f"Logout failed: no session_id provided from {ip_address}")
                return {
                    'error': {
                        'status': 400,
                        'message': 'session_id is required'
                    }
                }

            # Find and validate API session
            api_session = request.env['thedevkitchen.api.session'].sudo().search([
                ('session_id', '=', session_id),
                ('is_active', '=', True)
            ], limit=1)

            if not api_session:
                _logger.warning(f"Logout failed: no active session found for {session_id}")
                return {
                    'error': {
                        'status': 401,
                        'message': 'Session not found or already logged out'
                    }
                }

            # Get user info before deactivating
            user = api_session.user_id
            _logger.info(f"Logging out user: {user.login}")

            # Deactivate session
            api_session.write({
                'is_active': False,
                'logout_at': fields.Datetime.now()
            })

            AuditLogger.log_logout(ip_address, user.email or user.login, user.id)
            _logger.info(f"Logout successful for {user.login}")

            return {'message': 'Logged out successfully'}

        except Exception as e:
            return {
                'error': {
                    'status': 500,
                    'message': 'Internal server error'
                }
            }

    def _build_user_response(self, user):
        return {
            'id': user.id,
            'name': user.name,
            'email': user.email or user.login,
            'companies': [
                {
                    'id': c.id,
                    'name': c.name,
                    'cnpj': getattr(c, 'cnpj', None)
                }
                for c in user.estate_company_ids
            ],
            'default_company_id': (
                user.main_estate_company_id.id
                if user.main_estate_company_id
                else (user.estate_company_ids[0].id if user.estate_company_ids else None)
            )
        }
