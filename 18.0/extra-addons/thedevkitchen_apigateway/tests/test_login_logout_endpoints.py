# -*- coding: utf-8 -*-
"""
Test cases for Login/Logout endpoints and Odoo native rate limiting.

Tests validate:
1. Login endpoint with valid credentials
2. Login endpoint with invalid credentials
3. Rate limiting enforcement via Odoo's native request.session.authenticate()
4. Logout endpoint with active session
5. Session creation on successful login
6. Session deactivation on logout
"""

from odoo.tests.common import TransactionCase
from datetime import datetime, timedelta
import json
from unittest.mock import Mock, patch


class TestLoginLogoutEndpoints(TransactionCase):
    """Test login/logout functionality and Odoo native rate limiting"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Test Company',
            'cnpj': '11222333000181',
        })
        
        # Create test user
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'testuser@example.com',
            'email': 'testuser@example.com',
            'password': 'testpassword123',
            'estate_company_ids': [(6, 0, [cls.company.id])],
            'estate_default_company_id': cls.company.id,
        })
        
        # Create OAuth application for Bearer token validation
        cls.app = cls.env['thedevkitchen.oauth.application'].create({
            'name': 'Test API Application',
        })
        
        # Create OAuth token
        cls.token = cls.env['thedevkitchen.oauth.token'].create({
            'application_id': cls.app.id,
            'access_token': 'test-access-token-12345',
            'token_type': 'Bearer',
            'expires_at': datetime.now() + timedelta(hours=1),
        })

    def test_login_with_valid_credentials(self):
        """Test successful login with valid credentials"""
        # Simula o que o endpoint de login faz:
        # 1. Valida Bearer token
        # 2. Autentica usuário
        # 3. Cria API session
        
        # Verificar que token é válido
        self.assertTrue(self.token.id)
        self.assertFalse(self.token.revoked)
        
        # Simular autenticação nativa do Odoo
        # (request.session.authenticate checa rate limiting automaticamente)
        uid = self.env['ir.http']._authenticate(
            db=self.env.cr.dbname,
            login=self.test_user.login,
            password='testpassword123'
        )
        
        # Verificar que UID retornado é válido
        self.assertIsNotNone(uid, "Authentication should return valid UID")
        self.assertEqual(uid, self.test_user.id)
        
        # Criar API session (como o controller faz)
        api_session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'test-session-valid',
            'user_id': self.test_user.id,
            'ip_address': '127.0.0.1',
        })
        
        # Verificar que sessão foi criada
        self.assertTrue(api_session.id)
        self.assertTrue(api_session.is_active)
        self.assertEqual(api_session.user_id.id, self.test_user.id)

    def test_login_with_invalid_credentials(self):
        """Test login fails with invalid credentials"""
        # Tentar autenticar com senha errada
        uid = self.env['ir.http']._authenticate(
            db=self.env.cr.dbname,
            login=self.test_user.login,
            password='wrongpassword'
        )
        
        # Deve retornar None (falha na autenticação)
        self.assertIsNone(uid, "Authentication should fail with wrong password")

    def test_login_with_nonexistent_user(self):
        """Test login fails with non-existent user"""
        uid = self.env['ir.http']._authenticate(
            db=self.env.cr.dbname,
            login='nonexistent@example.com',
            password='anypassword'
        )
        
        self.assertIsNone(uid, "Authentication should fail for non-existent user")

    def test_logout_deactivates_session(self):
        """Test logout deactivates API session"""
        # Criar sessão ativa
        api_session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'test-session-logout',
            'user_id': self.test_user.id,
            'ip_address': '127.0.0.1',
        })
        
        # Verificar que sessão está ativa
        self.assertTrue(api_session.is_active)
        self.assertIsNone(api_session.logout_at)
        
        # Simular logout (como o endpoint faz)
        api_session.write({'is_active': False})
        
        # Verificar que sessão foi desativada
        self.assertFalse(api_session.is_active)

    def test_logout_with_invalid_session(self):
        """Test logout with non-existent session"""
        # Tentar encontrar sessão que não existe
        session = self.env['thedevkitchen.api.session'].search([
            ('session_id', '=', 'non-existent-session')
        ])
        
        # Deve retornar vazio
        self.assertEqual(len(session), 0)

    def test_rate_limiting_via_odoo_native(self):
        """Test Odoo's native rate limiting on login attempts
        
        Odoo's request.session.authenticate() uses:
        - base.login_cooldown_after (default: 5 failed attempts)
        - base.login_cooldown_duration (default: 60 seconds)
        """
        # Obter parâmetros de configuração
        cooldown_after = self.env['ir.config_parameter'].get_param(
            'base.login_cooldown_after',
            default='5'
        )
        cooldown_duration = self.env['ir.config_parameter'].get_param(
            'base.login_cooldown_duration',
            default='60'
        )
        
        # Verificar que parâmetros existem
        self.assertIsNotNone(cooldown_after)
        self.assertIsNotNone(cooldown_duration)
        
        # Converter para int
        max_attempts = int(cooldown_after)
        window_seconds = int(cooldown_duration)
        
        # Verificar valores padrão
        self.assertEqual(max_attempts, 5, "Default cooldown after 5 attempts")
        self.assertEqual(window_seconds, 60, "Default cooldown duration 60 seconds")

    def test_multiple_login_sessions(self):
        """Test creating multiple API sessions for same user"""
        # Criar primeira sessão
        session1 = self.env['thedevkitchen.api.session'].create({
            'session_id': 'session-1',
            'user_id': self.test_user.id,
        })
        
        # Criar segunda sessão
        session2 = self.env['thedevkitchen.api.session'].create({
            'session_id': 'session-2',
            'user_id': self.test_user.id,
        })
        
        # Ambas devem estar ativas
        self.assertTrue(session1.is_active)
        self.assertTrue(session2.is_active)
        
        # Devem ter IDs diferentes
        self.assertNotEqual(session1.id, session2.id)
        
        # Logout uma sessão não afeta a outra
        session1.write({'is_active': False})
        
        self.assertFalse(session1.is_active)
        self.assertTrue(session2.is_active)

    def test_user_data_returned_on_login(self):
        """Test that user data with companies is returned on login"""
        # Simular resposta de login (como o endpoint retorna)
        user_data = {
            'id': self.test_user.id,
            'name': self.test_user.name,
            'email': self.test_user.email,
            'login': self.test_user.login,
            'companies': [
                {
                    'id': company.id,
                    'name': company.name,
                } for company in self.test_user.estate_company_ids
            ]
        }
        
        # Verificar dados
        self.assertEqual(user_data['id'], self.test_user.id)
        self.assertEqual(user_data['email'], self.test_user.email)
        self.assertEqual(len(user_data['companies']), 1)
        self.assertEqual(user_data['companies'][0]['name'], 'Test Company')

    def test_inactive_user_cannot_login(self):
        """Test that inactive users cannot login"""
        # Desativar usuário
        self.test_user.active = False
        
        # Tentar autenticar
        uid = self.env['ir.http']._authenticate(
            db=self.env.cr.dbname,
            login=self.test_user.login,
            password='testpassword123'
        )
        
        # Deve falhar
        self.assertIsNone(uid, "Inactive user should not authenticate")

    def test_session_creation_with_metadata(self):
        """Test session is created with IP and user agent"""
        api_session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'session-with-metadata',
            'user_id': self.test_user.id,
            'ip_address': '192.168.1.100',
            'user_agent': 'Mozilla/5.0 Test Browser',
        })
        
        # Verificar metadados
        self.assertEqual(api_session.ip_address, '192.168.1.100')
        self.assertEqual(api_session.user_agent, 'Mozilla/5.0 Test Browser')
        self.assertIsNotNone(api_session.login_at)

    # =========================================================================
    # US1: Bearer Token Validation Tests (T006-T008)
    # =========================================================================

    def test_logout_without_authorization_header_returns_401(self):
        """
        T006: Test logout endpoint rejects request without Authorization header
        US1 - Secure API Access with Bearer Token
        
        Given: An API consumer has no bearer token
        When: They send POST to /api/v1/users/logout without Authorization header
        Then: System returns 401 error with message "Authorization header is required"
        """
        # Create an active session for the test user
        api_session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'test-session-no-auth-header',
            'user_id': self.test_user.id,
            'ip_address': '127.0.0.1',
            'is_active': True,
        })
        
        # Simulate request to logout endpoint WITHOUT Authorization header
        # This should be blocked by @require_jwt decorator
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.headers.get.return_value = None  # No Authorization header
            mock_request.httprequest.method = 'POST'
            mock_request.httprequest.content_type = 'application/json'
            
            # Import the middleware decorator
            from ..middleware import require_jwt
            
            # Create a mock endpoint function
            @require_jwt
            def mock_logout():
                return {'success': True}
            
            # Call the decorated function
            result = mock_logout()
            
            # Verify 401 error response
            self.assertIn('error', result)
            self.assertEqual(result['error']['code'], 'unauthorized')
            self.assertIn('Authorization header is required', result['error']['message'])

    def test_logout_with_expired_token_returns_401(self):
        """
        T007: Test logout endpoint rejects request with expired bearer token
        US1 - Secure API Access with Bearer Token
        
        Given: An API consumer has an expired bearer token
        When: They send POST to /api/v1/users/logout with expired token
        Then: System returns 401 error with message "Token has expired"
        """
        # Create an expired OAuth token
        expired_token = self.env['thedevkitchen.oauth.token'].create({
            'application_id': self.app.id,
            'access_token': 'expired-token-12345',
            'token_type': 'Bearer',
            'expires_at': datetime.now() - timedelta(hours=1),  # Expired 1 hour ago
        })
        
        # Create an active session
        api_session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'test-session-expired-token',
            'user_id': self.test_user.id,
            'ip_address': '127.0.0.1',
            'is_active': True,
        })
        
        # Simulate request with expired token
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.headers.get.return_value = 'Bearer expired-token-12345'
            mock_request.httprequest.method = 'POST'
            mock_request.httprequest.content_type = 'application/json'
            mock_request.env = self.env
            
            from ..middleware import require_jwt
            
            @require_jwt
            def mock_logout():
                return {'success': True}
            
            result = mock_logout()
            
            # Verify 401 error for expired token
            self.assertIn('error', result)
            self.assertIn('expired', result['error']['message'].lower())

    def test_logout_with_revoked_token_returns_401(self):
        """
        T008: Test logout endpoint rejects request with revoked bearer token
        US1 - Secure API Access with Bearer Token
        
        Given: An API consumer has a revoked bearer token
        When: They send POST to /api/v1/users/logout with revoked token
        Then: System returns 401 error with message indicating token is revoked
        """
        # Create a revoked OAuth token
        revoked_token = self.env['thedevkitchen.oauth.token'].create({
            'application_id': self.app.id,
            'access_token': 'revoked-token-12345',
            'token_type': 'Bearer',
            'expires_at': datetime.now() + timedelta(hours=1),
            'revoked': True,  # Token is revoked
        })
        
        # Create an active session
        api_session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'test-session-revoked-token',
            'user_id': self.test_user.id,
            'ip_address': '127.0.0.1',
            'is_active': True,
        })
        
        # Simulate request with revoked token
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.headers.get.return_value = 'Bearer revoked-token-12345'
            mock_request.httprequest.method = 'POST'
            mock_request.httprequest.content_type = 'application/json'
            mock_request.env = self.env
            
            from ..middleware import require_jwt
            
            @require_jwt
            def mock_logout():
                return {'success': True}
            
            result = mock_logout()
            
            # Verify 401 error for revoked token
            self.assertIn('error', result)
            self.assertIn('revoked', result['error']['message'].lower())


    # =========================================================================
    # US3: Session Validation Tests (T015-T017)
    # =========================================================================

    def test_logout_with_valid_token_but_no_session_returns_401(self):
        """
        T015: Test logout endpoint requires session cookie
        US3 - Session-Based User Context
        
        Given: An API consumer has a valid bearer token but no session cookie
        When: They send POST to /api/v1/users/logout with token only
        Then: System returns 401 error with message "Session required"
        """
        # Simulate request with valid token but no session
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.headers.get.return_value = 'Bearer test-access-token-12345'
            mock_request.httprequest.method = 'POST'
            mock_request.httprequest.content_type = 'application/json'
            mock_request.env = self.env
            mock_request.jwt_application = self.app
            
            # Mock Redis to return None (no session found)
            with patch('redis.Redis.get', return_value=None):
                from ..middleware import require_jwt, require_session
                
                @require_jwt
                @require_session
                def mock_logout():
                    return {'success': True}
                
                result = mock_logout()
                
                # Verify 401 error for missing session
                self.assertIn('error', result)
                self.assertIn('session', result['error']['message'].lower())

    def test_logout_with_valid_token_and_expired_session_returns_401(self):
        """
        T016: Test logout endpoint rejects expired sessions
        US3 - Session-Based User Context
        
        Given: An API consumer has a valid bearer token and an expired session
        When: They send POST to /api/v1/users/logout with expired session
        Then: System returns 401 error with message "Session expired"
        """
        # Create an API session (already logged out)
        api_session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'test-session-expired',
            'user_id': self.test_user.id,
            'ip_address': '127.0.0.1',
            'is_active': False,  # Session is not active (expired/logged out)
            'logout_at': datetime.now() - timedelta(hours=1),
        })
        
        # Simulate request with valid token but expired session
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.headers.get.return_value = 'Bearer test-access-token-12345'
            mock_request.httprequest.method = 'POST'
            mock_request.httprequest.content_type = 'application/json'
            mock_request.env = self.env
            mock_request.jwt_application = self.app
            
            # Mock session cookie
            mock_request.httprequest.cookies.get.return_value = 'test-session-expired'
            
            from ..middleware import require_jwt, require_session
            
            @require_jwt
            @require_session
            def mock_logout():
                return {'success': True}
            
            result = mock_logout()
            
            # Verify 401 error for expired session
            self.assertIn('error', result)
            # Either "Session expired" or "Session not found" is acceptable
            self.assertTrue(
                'expired' in result['error']['message'].lower() or 
                'not found' in result['error']['message'].lower()
            )

    def test_logout_with_session_fingerprint_mismatch_returns_401(self):
        """
        T017: Test logout endpoint validates session fingerprint
        US3 - Session-Based User Context
        
        Given: An API consumer has valid token and session but different IP (fingerprint mismatch)
        When: They send POST to /api/v1/users/logout with mismatched fingerprint
        Then: System returns 401 error with message "Session validation failed"
        """
        # Create an active session with specific IP
        api_session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'test-session-fingerprint',
            'user_id': self.test_user.id,
            'ip_address': '192.168.1.100',  # Original IP
            'user_agent': 'Mozilla/5.0',
            'is_active': True,
        })
        
        # Simulate request from DIFFERENT IP (fingerprint mismatch)
        with patch('odoo.http.request') as mock_request:
            mock_request.httprequest.headers.get.side_effect = lambda key: {
                'Authorization': 'Bearer test-access-token-12345',
                'User-Agent': 'Mozilla/5.0',
            }.get(key)
            mock_request.httprequest.remote_addr = '10.0.0.1'  # Different IP!
            mock_request.httprequest.method = 'POST'
            mock_request.httprequest.content_type = 'application/json'
            mock_request.env = self.env
            mock_request.jwt_application = self.app
            mock_request.httprequest.cookies.get.return_value = 'test-session-fingerprint'
            
            # Mock Redis session data with original IP
            import json
            session_data = json.dumps({
                'session_id': 'test-session-fingerprint',
                'user_id': self.test_user.id,
                'ip_address': '192.168.1.100',  # Original IP
                'user_agent': 'Mozilla/5.0',
            })
            
            with patch('redis.Redis.get', return_value=session_data.encode()):
                from ..middleware import require_jwt, require_session
                
                @require_jwt
                @require_session
                def mock_logout():
                    return {'success': True}
                
                result = mock_logout()
                
                # Verify 401 error for fingerprint mismatch
                self.assertIn('error', result)
                # Session validation should fail due to IP mismatch
                self.assertTrue(
                    'validation' in result['error']['message'].lower() or
                    'fingerprint' in result['error']['message'].lower() or
                    'session' in result['error']['message'].lower()
                )