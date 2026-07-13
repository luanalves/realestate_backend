# -*- coding: utf-8 -*-
"""
Unit Tests for Session Fingerprint JWT Security

Tests the pure fingerprint/token helpers on ir.http (_build_fingerprint_components,
_build_session_token, _check_session_token). These take plain arguments and never
touch odoo.http.request, so there is no need to mock Werkzeug/Odoo framework
internals - see ADR-003 (unit tests should not depend on the Odoo framework).
"""

import time

import jwt

from odoo.tests.common import TransactionCase


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

    def test_generate_fingerprint_components(self):
        """Test fingerprint components generation"""
        components = self.ir_http._build_fingerprint_components(
            self.settings,
            ip='192.168.1.100',
            user_agent='Mozilla/5.0 Test',
            accept_language='en-US,en;q=0.9',
        )

        self.assertIsInstance(components, dict)
        self.assertEqual(components.get('ip'), '192.168.1.100')
        self.assertEqual(components.get('ua'), 'Mozilla/5.0 Test')
        self.assertEqual(components.get('lang'), 'en-US,en;q=0.9')

    def test_generate_fingerprint_components_partial(self):
        """Test fingerprint with only IP enabled"""
        self.settings.write({
            'use_ip_in_fingerprint': True,
            'use_user_agent': False,
            'use_accept_language': False,
        })

        components = self.ir_http._build_fingerprint_components(
            self.settings,
            ip='192.168.1.100',
            user_agent='',
            accept_language='',
        )

        self.assertEqual(components.get('ip'), '192.168.1.100')
        self.assertNotIn('ua', components)
        self.assertNotIn('lang', components)

    def test_generate_session_token(self):
        """Test JWT token generation"""
        uid = self.test_user.id
        components = {'ip': '192.168.1.100', 'ua': 'Test Browser', 'lang': 'en-US'}

        token = self.ir_http._build_session_token(uid, components, 'test_secret_key')

        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)

        decoded = jwt.decode(token, 'test_secret_key', algorithms=['HS256'])
        self.assertEqual(decoded['uid'], uid)
        self.assertIn('fingerprint', decoded)
        self.assertIn('iat', decoded)
        self.assertIn('exp', decoded)
        self.assertEqual(decoded['iss'], 'odoo-session-security')

    def test_validate_session_token_valid(self):
        """Test successful token validation"""
        secret = 'test_secret_key'
        uid = self.test_user.id
        current_time = int(time.time())
        fingerprint = {'ip': '192.168.1.100', 'ua': 'Test Browser', 'lang': 'en-US'}

        payload = {
            'uid': uid,
            'fingerprint': fingerprint,
            'iat': current_time,
            'exp': current_time + 86400,
            'iss': 'odoo-session-security',
        }
        token = jwt.encode(payload, secret, algorithm='HS256')

        is_valid, reason = self.ir_http._check_session_token(token, uid, fingerprint, secret)

        self.assertTrue(is_valid)
        self.assertEqual(reason, "Valid")

    def test_validate_session_token_uid_mismatch(self):
        """Test token validation fails on UID mismatch"""
        secret = 'test_secret_key'
        token_uid = 9999
        request_uid = self.test_user.id
        current_time = int(time.time())
        fingerprint = {'ip': '192.168.1.100', 'ua': 'Test Browser', 'lang': 'en-US'}

        payload = {
            'uid': token_uid,
            'fingerprint': fingerprint,
            'iat': current_time,
            'exp': current_time + 86400,
            'iss': 'odoo-session-security',
        }
        token = jwt.encode(payload, secret, algorithm='HS256')

        is_valid, reason = self.ir_http._check_session_token(
            token, request_uid, fingerprint, secret
        )

        self.assertFalse(is_valid)
        self.assertEqual(reason, "UID mismatch")

    def test_validate_session_token_fingerprint_mismatch(self):
        """Test token validation fails on fingerprint mismatch (session hijacking)"""
        secret = 'test_secret_key'
        uid = self.test_user.id
        current_time = int(time.time())

        payload = {
            'uid': uid,
            'fingerprint': {'ip': '192.168.1.100', 'ua': 'Test Browser', 'lang': 'en-US'},
            'iat': current_time,
            'exp': current_time + 86400,
            'iss': 'odoo-session-security',
        }
        token = jwt.encode(payload, secret, algorithm='HS256')

        current_components = {
            'ip': '192.168.1.100', 'ua': 'DIFFERENT BROWSER', 'lang': 'en-US'
        }
        is_valid, reason = self.ir_http._check_session_token(
            token, uid, current_components, secret
        )

        self.assertFalse(is_valid)
        self.assertIn("Fingerprint mismatch", reason)

    def test_validate_session_token_expired(self):
        """Test token validation fails on expired token"""
        secret = 'test_secret_key'
        uid = self.test_user.id
        current_time = int(time.time())
        fingerprint = {'ip': '192.168.1.100', 'ua': 'Test Browser', 'lang': 'en-US'}

        payload = {
            'uid': uid,
            'fingerprint': fingerprint,
            'iat': current_time - 90000,
            'exp': current_time - 3600,
            'iss': 'odoo-session-security',
        }
        token = jwt.encode(payload, secret, algorithm='HS256')

        is_valid, reason = self.ir_http._check_session_token(token, uid, fingerprint, secret)

        self.assertFalse(is_valid)
        self.assertEqual(reason, "Token expired")

    def test_validate_session_token_not_found(self):
        """Test token validation fails when no token stored"""
        is_valid, reason = self.ir_http._check_session_token(
            None, self.test_user.id, {}, 'test_secret_key'
        )

        self.assertFalse(is_valid)
        self.assertEqual(reason, "Token not found")

    def test_token_includes_all_fingerprint_components(self):
        """Test that generated token includes all enabled fingerprint components"""
        uid = self.test_user.id
        components = self.ir_http._build_fingerprint_components(
            self.settings,
            ip='10.0.0.50',
            user_agent='Custom Browser/1.0',
            accept_language='pt-BR,pt;q=0.9',
        )

        token = self.ir_http._build_session_token(uid, components, 'test_secret')
        decoded = jwt.decode(token, 'test_secret', algorithms=['HS256'])

        self.assertIn('fingerprint', decoded)
        self.assertEqual(decoded['fingerprint']['ip'], '10.0.0.50')
        self.assertEqual(decoded['fingerprint']['ua'], 'Custom Browser/1.0')
        self.assertEqual(decoded['fingerprint']['lang'], 'pt-BR,pt;q=0.9')

    def test_token_expiration_is_24_hours(self):
        """Test that token expiration is set to 24 hours"""
        token = self.ir_http._build_session_token(
            self.test_user.id, {'ip': '192.168.1.1'}, 'test_secret'
        )
        decoded = jwt.decode(token, 'test_secret', algorithms=['HS256'])

        time_diff = decoded['exp'] - decoded['iat']
        self.assertEqual(time_diff, 86400)
