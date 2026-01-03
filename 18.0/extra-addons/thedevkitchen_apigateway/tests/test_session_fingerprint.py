# -*- coding: utf-8 -*-
"""
Unit Tests for Session Fingerprint JWT Security
Tests the ir.http session_info() override with JWT token validation
"""

from odoo.tests.common import TransactionCase
from odoo.http import request
from unittest.mock import Mock, patch, MagicMock
import jwt
import time


class TestSessionFingerprint(TransactionCase):
    """Test session fingerprint JWT generation and validation"""

    def setUp(self):
        super(TestSessionFingerprint, self).setUp()
        
        self.settings = self.env['thedevkitchen.security.settings'].sudo().create({
            'name': 'Test Security Configuration',
            'use_ip_in_fingerprint': True,
            'use_user_agent': True,
            'use_accept_language': True,
        })
        
        self.test_user = self.env['res.users'].create({
            'name': 'Test User Session',
            'login': 'test_session@example.com',
            'password': 'test_password_123',
        })
        
        self.ir_http = self.env['ir.http']

    def test_security_settings_model_exists(self):
        """Test that security settings model can be created"""
        self.assertTrue(self.settings.id)
        self.assertEqual(self.settings.name, 'Test Security Configuration')
        self.assertTrue(self.settings.use_ip_in_fingerprint)
        self.assertTrue(self.settings.use_user_agent)
        self.assertTrue(self.settings.use_accept_language)

    def test_security_settings_get_settings(self):
        """Test get_settings() returns existing or creates default"""
        settings = self.env['thedevkitchen.security.settings'].get_settings()
        self.assertTrue(settings.id)
        self.assertIn('Security Configuration', settings.name)

    @patch('odoo.http.request')
    def test_generate_fingerprint_components(self, mock_request):
        """Test fingerprint components generation"""
        mock_request.httprequest = Mock()
        mock_request.httprequest.remote_addr = '192.168.1.100'
        mock_request.httprequest.headers = {
            'User-Agent': 'Mozilla/5.0 Test',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        mock_request.env = self.env
        
        components = self.ir_http._generate_fingerprint_components()
        
        self.assertIsInstance(components, dict)
        self.assertEqual(components.get('ip'), '192.168.1.100')
        self.assertEqual(components.get('ua'), 'Mozilla/5.0 Test')
        self.assertEqual(components.get('lang'), 'en-US,en;q=0.9')

    @patch('odoo.http.request')
    def test_generate_fingerprint_components_partial(self, mock_request):
        """Test fingerprint with only IP enabled"""
        self.settings.write({
            'use_ip_in_fingerprint': True,
            'use_user_agent': False,
            'use_accept_language': False,
        })
        
        mock_request.httprequest = Mock()
        mock_request.httprequest.remote_addr = '192.168.1.100'
        mock_request.httprequest.headers = {}
        mock_request.env = self.env
        
        components = self.ir_http._generate_fingerprint_components()
        
        self.assertEqual(components.get('ip'), '192.168.1.100')
        self.assertNotIn('ua', components)
        self.assertNotIn('lang', components)

    @patch('odoo.http.request')
    @patch('odoo.tools.config')
    def test_generate_session_token(self, mock_config, mock_request):
        """Test JWT token generation"""
        mock_config.get.return_value = 'test_secret_key'
        mock_request.httprequest = Mock()
        mock_request.httprequest.remote_addr = '192.168.1.100'
        mock_request.httprequest.headers = {
            'User-Agent': 'Test Browser',
            'Accept-Language': 'en-US'
        }
        mock_request.session = Mock()
        mock_request.session.sid = 'test_session_abc123'
        mock_request.env = self.env
        
        uid = self.test_user.id
        token = self.ir_http._generate_session_token(uid)
        
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        
        decoded = jwt.decode(token, 'test_secret_key', algorithms=['HS256'])
        self.assertEqual(decoded['uid'], uid)
        self.assertIn('fingerprint', decoded)
        self.assertIn('iat', decoded)
        self.assertIn('exp', decoded)
        self.assertEqual(decoded['iss'], 'odoo-session-security')

    @patch('odoo.http.request')
    @patch('odoo.tools.config')
    def test_validate_session_token_valid(self, mock_config, mock_request):
        """Test successful token validation"""
        secret = 'test_secret_key'
        mock_config.get.return_value = secret
        
        mock_request.httprequest = Mock()
        mock_request.httprequest.remote_addr = '192.168.1.100'
        mock_request.httprequest.headers = {
            'User-Agent': 'Test Browser',
            'Accept-Language': 'en-US'
        }
        mock_request.env = self.env
        
        uid = self.test_user.id
        current_time = int(time.time())
        
        payload = {
            'uid': uid,
            'fingerprint': {
                'ip': '192.168.1.100',
                'ua': 'Test Browser',
                'lang': 'en-US'
            },
            'iat': current_time,
            'exp': current_time + 86400,
            'iss': 'odoo-session-security'
        }
        
        token = jwt.encode(payload, secret, algorithm='HS256')
        mock_request.session = Mock()
        mock_request.session.get.return_value = token
        
        is_valid, reason = self.ir_http._validate_session_token(uid)
        
        self.assertTrue(is_valid)
        self.assertEqual(reason, "Valid")

    @patch('odoo.http.request')
    @patch('odoo.tools.config')
    def test_validate_session_token_uid_mismatch(self, mock_config, mock_request):
        """Test token validation fails on UID mismatch"""
        secret = 'test_secret_key'
        mock_config.get.return_value = secret
        
        mock_request.httprequest = Mock()
        mock_request.httprequest.remote_addr = '192.168.1.100'
        mock_request.httprequest.headers = {
            'User-Agent': 'Test Browser',
            'Accept-Language': 'en-US'
        }
        mock_request.env = self.env
        
        token_uid = 9999
        request_uid = self.test_user.id
        current_time = int(time.time())
        
        payload = {
            'uid': token_uid,
            'fingerprint': {
                'ip': '192.168.1.100',
                'ua': 'Test Browser',
                'lang': 'en-US'
            },
            'iat': current_time,
            'exp': current_time + 86400,
            'iss': 'odoo-session-security'
        }
        
        token = jwt.encode(payload, secret, algorithm='HS256')
        mock_request.session = Mock()
        mock_request.session.get.return_value = token
        mock_request.session.sid = 'test_session_abc'
        
        is_valid, reason = self.ir_http._validate_session_token(request_uid)
        
        self.assertFalse(is_valid)
        self.assertEqual(reason, "UID mismatch")

    @patch('odoo.http.request')
    @patch('odoo.tools.config')
    def test_validate_session_token_fingerprint_mismatch(self, mock_config, mock_request):
        """Test token validation fails on fingerprint mismatch (session hijacking)"""
        secret = 'test_secret_key'
        mock_config.get.return_value = secret
        
        mock_request.httprequest = Mock()
        mock_request.httprequest.remote_addr = '192.168.1.100'
        mock_request.httprequest.headers = {
            'User-Agent': 'DIFFERENT BROWSER',
            'Accept-Language': 'en-US'
        }
        mock_request.env = self.env
        
        uid = self.test_user.id
        current_time = int(time.time())
        
        payload = {
            'uid': uid,
            'fingerprint': {
                'ip': '192.168.1.100',
                'ua': 'Test Browser',
                'lang': 'en-US'
            },
            'iat': current_time,
            'exp': current_time + 86400,
            'iss': 'odoo-session-security'
        }
        
        token = jwt.encode(payload, secret, algorithm='HS256')
        mock_request.session = Mock()
        mock_request.session.get.return_value = token
        mock_request.session.sid = 'test_session_abc'
        
        is_valid, reason = self.ir_http._validate_session_token(uid)
        
        self.assertFalse(is_valid)
        self.assertIn("Fingerprint mismatch", reason)

    @patch('odoo.http.request')
    @patch('odoo.tools.config')
    def test_validate_session_token_expired(self, mock_config, mock_request):
        """Test token validation fails on expired token"""
        secret = 'test_secret_key'
        mock_config.get.return_value = secret
        
        mock_request.httprequest = Mock()
        mock_request.httprequest.remote_addr = '192.168.1.100'
        mock_request.httprequest.headers = {
            'User-Agent': 'Test Browser',
            'Accept-Language': 'en-US'
        }
        mock_request.env = self.env
        
        uid = self.test_user.id
        current_time = int(time.time())
        
        payload = {
            'uid': uid,
            'fingerprint': {
                'ip': '192.168.1.100',
                'ua': 'Test Browser',
                'lang': 'en-US'
            },
            'iat': current_time - 90000,
            'exp': current_time - 3600,
            'iss': 'odoo-session-security'
        }
        
        token = jwt.encode(payload, secret, algorithm='HS256')
        mock_request.session = Mock()
        mock_request.session.get.return_value = token
        
        is_valid, reason = self.ir_http._validate_session_token(uid)
        
        self.assertFalse(is_valid)
        self.assertEqual(reason, "Token expired")

    @patch('odoo.http.request')
    @patch('odoo.tools.config')
    def test_validate_session_token_not_found(self, mock_config, mock_request):
        """Test token validation fails when no token stored"""
        mock_config.get.return_value = 'test_secret_key'
        mock_request.session = Mock()
        mock_request.session.get.return_value = None
        mock_request.env = self.env
        
        is_valid, reason = self.ir_http._validate_session_token(self.test_user.id)
        
        self.assertFalse(is_valid)
        self.assertEqual(reason, "Token not found")

    @patch('odoo.http.request')
    @patch('odoo.tools.config')
    def test_token_includes_all_fingerprint_components(self, mock_config, mock_request):
        """Test that generated token includes all enabled fingerprint components"""
        mock_config.get.return_value = 'test_secret'
        
        mock_request.httprequest = Mock()
        mock_request.httprequest.remote_addr = '10.0.0.50'
        mock_request.httprequest.headers = {
            'User-Agent': 'Custom Browser/1.0',
            'Accept-Language': 'pt-BR,pt;q=0.9'
        }
        mock_request.session = Mock()
        mock_request.session.sid = 'test_abc'
        mock_request.env = self.env
        
        uid = self.test_user.id
        token = self.ir_http._generate_session_token(uid)
        
        decoded = jwt.decode(token, 'test_secret', algorithms=['HS256'])
        
        self.assertIn('fingerprint', decoded)
        self.assertEqual(decoded['fingerprint']['ip'], '10.0.0.50')
        self.assertEqual(decoded['fingerprint']['ua'], 'Custom Browser/1.0')
        self.assertEqual(decoded['fingerprint']['lang'], 'pt-BR,pt;q=0.9')

    def test_token_expiration_is_24_hours(self):
        """Test that token expiration is set to 24 hours"""
        with patch('odoo.http.request') as mock_request, \
             patch('odoo.tools.config') as mock_config:
            
            mock_config.get.return_value = 'test_secret'
            mock_request.httprequest = Mock()
            mock_request.httprequest.remote_addr = '192.168.1.1'
            mock_request.httprequest.headers = {}
            mock_request.session = Mock()
            mock_request.session.sid = 'test'
            mock_request.env = self.env
            
            token = self.ir_http._generate_session_token(self.test_user.id)
            decoded = jwt.decode(token, 'test_secret', algorithms=['HS256'])
            
            time_diff = decoded['exp'] - decoded['iat']
            self.assertEqual(time_diff, 86400)
