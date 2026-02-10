from odoo import http, fields
from odoo.http import request
from ..services.audit_logger import AuditLogger
from ..middleware import require_jwt, require_session
import json
import logging

_logger = logging.getLogger(__name__)


class UserAuthController(http.Controller):

    @http.route('/api/v1/users/login', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    def login(self, **kwargs):
        ip_address = request.httprequest.remote_addr
        user_agent = request.httprequest.headers.get('User-Agent', 'Unknown')
        application = request.jwt_application
        
        # Extrai dados do JSON body
        try:
            data = json.loads(request.httprequest.get_data(as_text=True) or '{}')
        except (json.JSONDecodeError, ValueError):
            return request.make_json_response(
                {'error': {'status': 400, 'message': 'Invalid JSON body'}},
                status=400
            )
        
        email = data.get('email') or data.get('login') or ''
        password = data.get('password') or ''
        
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
                return request.make_json_response(
                    {'error': {'status': 401, 'message': 'Invalid credentials'}},
                    status=401
                )

            user = users[0]
            _logger.info(f"User found: {user.login}, active: {user.active}")

            if not user.active:
                _logger.warning(f"User inactive: {email}")
                AuditLogger.log_failed_login(ip_address, email, 'User inactive')
                return request.make_json_response(
                    {'error': {'status': 403, 'message': 'User inactive'}},
                    status=403
                )

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
                    return request.make_json_response(
                        {'error': {'status': 401, 'message': 'Invalid credentials'}},
                        status=401
                    )
                    
                # Captura session_id APÓS authenticate (que pode gerar novo sid)
                session_id = request.session.sid
                _logger.info(f"Session ID after auth: {session_id}")
                
            except Exception as auth_error:
                _logger.error(f"Auth exception for {email}: {type(auth_error).__name__}: {auth_error}")
                AuditLogger.log_failed_login(ip_address, email, str(auth_error))
                return request.make_json_response(
                    {'error': {'status': 401, 'message': 'Invalid credentials'}},
                    status=401
                )

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

            return request.make_json_response({
                'session_id': session_id,
                'user': user_response
            })

        except Exception as e:
            AuditLogger.log_error('user.login', email, str(e))
            return request.make_json_response(
                {'error': {'status': 500, 'message': 'Internal server error'}},
                status=500
            )

    @http.route('/api/v1/users/logout', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def logout(self, **kwargs):
        try:
            try:
                data = json.loads(request.httprequest.get_data(as_text=True) or '{}')
            except (json.JSONDecodeError, ValueError):
                data = {}
            session_id = data.get('session_id')
            ip_address = request.httprequest.remote_addr
            
            _logger.info(f"Logout attempt for session_id: {session_id} from {ip_address}")
            
            if not session_id:
                _logger.warning(f"Logout failed: no session_id provided from {ip_address}")
                return request.make_json_response(
                    {'error': {'status': 400, 'message': 'session_id is required'}},
                    status=400
                )

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
                return request.make_json_response(
                    {'error': {'status': 401, 'message': 'Session not found or already logged out'}},
                    status=401
                )

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

            return request.make_json_response({'message': 'Logged out successfully'})

        except Exception as e:
            _logger.error(f"Logout error: {str(e)}", exc_info=True)
            return request.make_json_response(
                {'error': {'status': 500, 'message': 'Internal server error'}},
                status=500
            )

    @http.route('/api/v1/users/profile', type='http', auth='none', methods=['PATCH'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def update_profile(self, **kwargs):
        try:
            user = request.env.user
            try:
                data = json.loads(request.httprequest.get_data(as_text=True) or '{}')
            except (json.JSONDecodeError, ValueError):
                return request.make_json_response(
                    {'error': {'status': 400, 'message': 'Invalid JSON body'}},
                    status=400
                )
            ip_address = request.httprequest.remote_addr
            
            updates = {}
            
            if 'email' in data:
                email = str(data['email']).strip().lower()
                if '@' not in email or '.' not in email.split('@')[1]:
                    return request.make_json_response(
                        {'error': {'status': 400, 'message': 'Invalid email format'}},
                        status=400
                    )
                
                existing = request.env['res.users'].search([
                    ('email', '=', email),
                    ('id', '!=', user.id),
                    ('active', '=', True)
                ], limit=1)
                
                if existing:
                    return request.make_json_response(
                        {'error': {'status': 409, 'message': 'Email already in use'}},
                        status=409
                    )
                
                updates['email'] = email
            
            if 'phone' in data:
                updates['phone'] = str(data['phone']).strip() or False
            
            if 'mobile' in data:
                updates['mobile'] = str(data['mobile']).strip() or False
            
            if not updates:
                return request.make_json_response(
                    {'error': {'status': 400, 'message': 'No fields to update'}},
                    status=400
                )
            
            user.write(updates)
            AuditLogger.log_successful_login(ip_address, user.email or user.login, user.id)
            
            return request.make_json_response({
                'user': self._build_user_response(user),
                'message': 'Profile updated successfully'
            })

        except Exception as e:
            _logger.error(f"Profile update error: {e}", exc_info=True)
            return request.make_json_response(
                {'error': {'status': 500, 'message': 'Internal server error'}},
                status=500
            )

    @http.route('/api/v1/users/change-password', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def change_password(self, **kwargs):
        try:
            # Extrai dados do JSON body
            try:
                data = json.loads(request.httprequest.get_data(as_text=True) or '{}')
            except (json.JSONDecodeError, ValueError):
                return request.make_json_response(
                    {'error': {'status': 400, 'message': 'Invalid JSON body'}},
                    status=400
                )
            session_id = data.get('session_id')
            ip_address = request.httprequest.remote_addr
            
            if not session_id:
                _logger.warning(f"Change password failed: no session_id provided")
                return request.make_json_response(
                    {'error': {'status': 400, 'message': 'session_id is required'}},
                    status=400
                )
            
            # Buscar a sessão da API
            api_session = request.env['thedevkitchen.api.session'].sudo().search([
                ('session_id', '=', session_id),
                ('is_active', '=', True)
            ], limit=1)
            
            if not api_session:
                _logger.warning(f"Change password failed: Invalid or inactive session {session_id}")
                return request.make_json_response(
                    {'error': {'status': 401, 'message': 'Invalid session'}},
                    status=401
                )
            
            user = api_session.user_id
            _logger.info(f"Change password request for user: {user.email or user.login}")
            
            # Validação de campos vazios
            current_password = data.get('current_password', '').strip() if data.get('current_password') else ''
            new_password = data.get('new_password', '').strip() if data.get('new_password') else ''
            confirm_password = data.get('confirm_password', '').strip() if data.get('confirm_password') else ''
            
            # Validação 1: Campos obrigatórios
            if not current_password:
                _logger.warning(f"Change password failed: current_password is empty for {user.email or user.login}")
                return request.make_json_response(
                    {'error': {'status': 400, 'message': 'Current password is required'}},
                    status=400
                )
            
            if not new_password:
                _logger.warning(f"Change password failed: new_password is empty for {user.email or user.login}")
                return request.make_json_response(
                    {'error': {'status': 400, 'message': 'New password is required'}},
                    status=400
                )
            
            if not confirm_password:
                _logger.warning(f"Change password failed: confirm_password is empty for {user.email or user.login}")
                return request.make_json_response(
                    {'error': {'status': 400, 'message': 'Password confirmation is required'}},
                    status=400
                )
            
            # Validação 2: Passwords coincidem
            if new_password != confirm_password:
                _logger.warning(f"Change password failed: Passwords do not match for {user.email or user.login}")
                return request.make_json_response(
                    {'error': {'status': 400, 'message': 'New password and confirmation do not match'}},
                    status=400
                )
            
            # Validação 3: Comprimento mínimo
            if len(new_password) < 8:
                _logger.warning(f"Change password failed: Password too short ({len(new_password)} chars) for {user.email or user.login}")
                return request.make_json_response(
                    {'error': {'status': 400, 'message': 'Password must be at least 8 characters long'}},
                    status=400
                )
            
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
                    return request.make_json_response(
                        {'error': {'status': 401, 'message': 'Current password is incorrect'}},
                        status=401
                    )
            except Exception as cred_error:
                _logger.error(f"Error checking credentials for {user.email or user.login}: {cred_error}", exc_info=True)
                return request.make_json_response(
                    {'error': {'status': 401, 'message': 'Failed to verify current password'}},
                    status=401
                )
            
            # Atualizar password
            try:
                user.write({'password': new_password})
                _logger.info(f"Password changed successfully for {user.email or user.login}")
                AuditLogger.log_successful_login(ip_address, user.email or user.login, user.id)
                return request.make_json_response({'message': 'Password changed successfully'})
            except Exception as write_error:
                _logger.error(f"Error writing new password for {user.email or user.login}: {write_error}", exc_info=True)
                return request.make_json_response(
                    {'error': {'status': 500, 'message': 'Failed to update password in database'}},
                    status=500
                )

        except Exception as e:
            _logger.error(f"Unexpected error in change_password: {e}", exc_info=True)
            return request.make_json_response(
                {'error': {'status': 500, 'message': 'Internal server error'}},
                status=500
            )

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
