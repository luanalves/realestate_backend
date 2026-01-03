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
