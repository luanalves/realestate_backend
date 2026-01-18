from odoo import http, fields
from odoo.http import request
from ..services.audit_logger import AuditLogger
from ..middleware import require_jwt, require_session
import logging

_logger = logging.getLogger(__name__)


class UserAuthController(http.Controller):

    @http.route('/api/v1/users/login', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    def login(self, email=None, password=None):
        ip_address = request.httprequest.remote_addr
        user_agent = request.httprequest.headers.get('User-Agent', 'Unknown')
        application = request.jwt_application
        
        # Extrai dados do JSON quando não vêm como parâmetros diretos
        if email is None or password is None:
            data = request.get_json_data() or {}
            email = email or data.get('email') or data.get('login') or ''
            password = password or data.get('password') or ''
        
        # Normaliza email
        email = (email or '').strip().lower()

        try:
            _logger.info(f"Login attempt: {email} from {ip_address} by app: {application.name}")

            # IMPORTANTE: auth='none' significa env.uid=None, então precisamos .sudo() para buscar usuários
            _logger.info(f"Searching for user: {email}")
            users = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
            _logger.info(f"Search result: {users}, count: {len(users) if users else 0}")

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

            try:
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
                    
                # Captura session_id APÓS authenticate (que pode gerar novo sid)
                session_id = request.session.sid
                _logger.info(f"Session ID after auth: {session_id}")
                
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

            if not has_companies and not is_system_admin:
                _logger.warning(f"User has no companies: {email}")
                AuditLogger.log_failed_login(ip_address, email, 'No companies')
                return {
                    'error': {
                        'status': 403,
                        'message': 'User has no companies assigned'
                    }
                }

            _logger.info(f"Creating API session for user {email}, session_id: {session_id}")

            # Usar .sudo() para operações de API session porque:
            # 1. É uma operação de sistema (registrar sessões), não do usuário
            # 2. O usuário não deve precisar de permissão explícita para o sistema registrar sua própria sessão
            # 3. Evita problemas de cache de permissões após autenticação
            try:
                old_sessions = request.env['thedevkitchen.api.session'].sudo().search([
                    ('user_id', '=', user.id),
                    ('is_active', '=', True),
                ])
                for old_session in old_sessions:
                    _logger.info(f"Invalidating previous session {old_session.session_id} for user {email}")
                    old_session.write({
                        'is_active': False,
                        'logout_at': fields.Datetime.now()
                    })
                    AuditLogger.log_logout(ip_address, email, user.id)
            except Exception as session_error:
                _logger.error(f"Error invalidating old sessions: {type(session_error).__name__}: {session_error}", exc_info=True)
                raise

            try:
                api_session_record = request.env['thedevkitchen.api.session'].sudo().create({
                    'session_id': session_id,
                    'user_id': user.id,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                })
                
            except Exception as create_error:
                _logger.error(f"Error creating API session: {type(create_error).__name__}: {create_error}", exc_info=True)
                raise

            AuditLogger.log_successful_login(ip_address, email, user.id)

            _logger.info(f"Login successful for {email}")

            # Generate JWT token for session security (prevents session hijacking)
            try:
                ir_http = request.env['ir.http']
                security_token = ir_http._generate_session_token(user.id)
                if security_token:
                    request.session['_security_token'] = security_token
                    # Também armazenar no registro de API session para persistência
                    api_session_record.security_token = security_token
                    _logger.info(f"[SESSION TOKEN] Created for user {email} (UID {user.id})")
                else:
                    _logger.warning(f"Failed to generate session token for {email}")
            except Exception as token_error:
                _logger.error(f"Error generating session token: {token_error}", exc_info=True)

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
    @require_session
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
            # Usar .sudo() pois logout é operação de sistema
            try:
                api_session = request.env['thedevkitchen.api.session'].sudo().search([
                    ('session_id', '=', session_id),
                    ('is_active', '=', True)
                ], limit=1)
            except Exception as search_error:
                _logger.error(f"Error searching for session: {type(search_error).__name__}: {search_error}", exc_info=True)
                raise

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
            try:
                api_session.write({
                    'is_active': False,
                    'logout_at': fields.Datetime.now()
                })
            except Exception as write_error:
                _logger.error(f"Error deactivating session: {type(write_error).__name__}: {write_error}", exc_info=True)
                raise

            AuditLogger.log_logout(ip_address, user.email or user.login, user.id)
            _logger.info(f"Logout successful for {user.login}")

            return {'message': 'Logged out successfully'}

        except Exception as e:
            _logger.error(f"Logout error: {str(e)}", exc_info=True)
            return {
                'error': {
                    'status': 500,
                    'message': 'Internal server error'
                }
            }

    @http.route('/api/v1/users/profile', type='json', auth='none', methods=['PATCH'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def update_profile(self):
        try:
            user = request.env.user
            data = request.get_json_data()
            ip_address = request.httprequest.remote_addr
            
            updates = {}
            
            if 'email' in data:
                email = str(data['email']).strip().lower()
                if '@' not in email or '.' not in email.split('@')[1]:
                    return {'error': {'status': 400, 'message': 'Invalid email format'}}
                
                existing = request.env['res.users'].search([
                    ('email', '=', email),
                    ('id', '!=', user.id),
                    ('active', '=', True)
                ], limit=1)
                
                if existing:
                    return {'error': {'status': 409, 'message': 'Email already in use'}}
                
                updates['email'] = email
            
            if 'phone' in data:
                updates['phone'] = str(data['phone']).strip() or False
            
            if 'mobile' in data:
                updates['mobile'] = str(data['mobile']).strip() or False
            
            if not updates:
                return {'error': {'status': 400, 'message': 'No fields to update'}}
            
            user.write(updates)
            AuditLogger.log_successful_login(ip_address, user.email or user.login, user.id)
            
            return {
                'user': self._build_user_response(user),
                'message': 'Profile updated successfully'
            }

        except Exception as e:
            _logger.error(f"Profile update error: {e}", exc_info=True)
            return {'error': {'status': 500, 'message': 'Internal server error'}}

    @http.route('/api/v1/users/change-password', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def change_password(self):
        try:
            # Obter a sessão da API e encontrar o usuário
            session_id = request.get_json_data().get('session_id')
            data = request.get_json_data()
            ip_address = request.httprequest.remote_addr
            
            if not session_id:
                _logger.warning(f"Change password failed: no session_id provided")
                return {'error': {'status': 400, 'message': 'session_id is required'}}
            
            # Buscar a sessão da API
            api_session = request.env['thedevkitchen.api.session'].sudo().search([
                ('session_id', '=', session_id),
                ('is_active', '=', True)
            ], limit=1)
            
            if not api_session:
                _logger.warning(f"Change password failed: Invalid or inactive session {session_id}")
                return {'error': {'status': 401, 'message': 'Invalid session'}}
            
            user = api_session.user_id
            _logger.info(f"Change password request for user: {user.email or user.login}")
            
            # Validação de campos vazios
            current_password = data.get('current_password', '').strip() if data.get('current_password') else ''
            new_password = data.get('new_password', '').strip() if data.get('new_password') else ''
            confirm_password = data.get('confirm_password', '').strip() if data.get('confirm_password') else ''
            
            # Validação 1: Campos obrigatórios
            if not current_password:
                _logger.warning(f"Change password failed: current_password is empty for {user.email or user.login}")
                return {'error': {'status': 400, 'message': 'Current password is required'}}
            
            if not new_password:
                _logger.warning(f"Change password failed: new_password is empty for {user.email or user.login}")
                return {'error': {'status': 400, 'message': 'New password is required'}}
            
            if not confirm_password:
                _logger.warning(f"Change password failed: confirm_password is empty for {user.email or user.login}")
                return {'error': {'status': 400, 'message': 'Password confirmation is required'}}
            
            # Validação 2: Passwords coincidem
            if new_password != confirm_password:
                _logger.warning(f"Change password failed: Passwords do not match for {user.email or user.login}")
                return {'error': {'status': 400, 'message': 'New password and confirmation do not match'}}
            
            # Validação 3: Comprimento mínimo
            if len(new_password) < 8:
                _logger.warning(f"Change password failed: Password too short ({len(new_password)} chars) for {user.email or user.login}")
                return {'error': {'status': 400, 'message': 'Password must be at least 8 characters long'}}
            
            # Validação 4: Verificar senha atual
            # Usa o método padrão de autenticação do Odoo
            try:
                # Tenta autenticar o usuário com a senha fornecida
                user_id = request.env['res.users'].authenticate(
                    request.env.cr.dbname,  # database name
                    user.login,
                    current_password
                )
                
                if not user_id or user_id != user.id:
                    _logger.warning(f"Change password failed: Invalid current password for {user.email or user.login}")
                    AuditLogger.log_failed_login(ip_address, user.email or user.login, 'Invalid current password during change')
                    return {'error': {'status': 401, 'message': 'Current password is incorrect'}}
            except Exception as cred_error:
                _logger.error(f"Error checking credentials for {user.email or user.login}: {cred_error}", exc_info=True)
                return {'error': {'status': 401, 'message': 'Failed to verify current password'}}
            
            # Atualizar password
            try:
                user.write({'password': new_password})
                _logger.info(f"Password changed successfully for {user.email or user.login}")
                AuditLogger.log_successful_login(ip_address, user.email or user.login, user.id)
                return {'message': 'Password changed successfully'}
            except Exception as write_error:
                _logger.error(f"Error writing new password for {user.email or user.login}: {write_error}", exc_info=True)
                return {'error': {'status': 500, 'message': 'Failed to update password in database'}}

        except Exception as e:
            _logger.error(f"Unexpected error in change_password: {e}", exc_info=True)
            return {'error': {'status': 500, 'message': f'Internal server error'}}

    def _build_user_response(self, user):
        return {
            'id': user.id,
            'name': user.name,
            'email': user.email or user.login,
            'phone': user.phone or '',
            'mobile': user.mobile or '',
            'companies': [
                {
                    'id': c.id,
                    'name': c.name,
                    'cnpj': getattr(c, 'vat', None)
                }
                for c in user.estate_company_ids
            ],
            'default_company_id': (
                user.company_id.id
                if user.company_id
                else (user.estate_company_ids[0].id if user.estate_company_ids else None)
            )
        }
