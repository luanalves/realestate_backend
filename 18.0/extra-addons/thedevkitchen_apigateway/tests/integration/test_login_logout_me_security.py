"""Advanced QA scenarios for login, logout and /me endpoints.

These integration tests execute the real HTTP endpoints with complex
security validations focused on session hijacking prevention and
multi-layer authentication required by ADRs 008, 009 and 011.
"""

import json
import logging
import os
from pathlib import Path

import jwt

from odoo import fields
from odoo.tests.common import HttpCase
from odoo.tools import config

_logger = logging.getLogger(__name__)


def _load_env_file():
    env_path = Path(__file__).resolve().parents[4] / '.env'
    if not env_path.exists():
        return
    with env_path.open('r', encoding='utf-8') as handler:
        for line in handler:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            if key and key not in os.environ:
                os.environ[key] = value


class TestLoginLogoutMeSecurity(HttpCase):
    """Security-focused integration tests for authentication endpoints."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _load_env_file()
        cls.base_url = cls.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'http://localhost:8069'
        )
        cls.client_id = os.getenv('OAUTH_CLIENT_ID')
        cls.client_secret = os.getenv('OAUTH_CLIENT_SECRET')
        cls.user_email = os.getenv('TEST_USER_A_EMAIL')
        cls.user_password = os.getenv('TEST_USER_A_PASSWORD')
        cls.user_b_email = os.getenv('TEST_USER_B_EMAIL')
        cls.user_b_password = os.getenv('TEST_USER_B_PASSWORD')
        missing = [
            key
            for key, value in [
                ('OAUTH_CLIENT_ID', cls.client_id),
                ('OAUTH_CLIENT_SECRET', cls.client_secret),
                ('TEST_USER_A_EMAIL', cls.user_email),
                ('TEST_USER_A_PASSWORD', cls.user_password),
                ('TEST_USER_B_EMAIL', cls.user_b_email),
                ('TEST_USER_B_PASSWORD', cls.user_b_password),
            ]
            if not value
        ]
        if missing:
            raise RuntimeError(
                'Missing required environment variables for integration tests: '
                + ', '.join(missing)
            )

    def setUp(self):
        super().setUp()
        self.secret = (
            self.env['ir.config_parameter'].sudo().get_param('database.secret')
            or config.get('database_secret')
            or config.get('admin_passwd')
        )
        self.assertTrue(
            self.secret,
            'database_secret or admin_passwd must be configured for JWT validation',
        )
        self.default_user_agent = 'QA-Test-Agent/1.0'
        self.default_language = 'pt-BR,en;q=0.9'
        self.api_session_model = self.env['thedevkitchen.api.session'].sudo()
        self.user_record = self.env['res.users'].sudo().search(
            [('login', '=', self.user_email)], limit=1
        )
        self.assertTrue(
            self.user_record,
            f'Fixture user {self.user_email} must exist for integration tests',
        )

        # Ensure no stale active sessions interfere with the scenarios.
        stale_sessions = self.api_session_model.search([
            ('user_id', '=', self.user_record.id),
            ('is_active', '=', True),
        ])
        if stale_sessions:
            stale_sessions.write({
                'is_active': False,
                'logout_at': fields.Datetime.now(),
            })

        self.bearer_token = self._obtain_bearer_token()

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _obtain_bearer_token(self):
        url = f'{self.base_url}/api/v1/auth/token'
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
        }
        headers = {'Content-Type': 'application/json'}

        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json',
        )
        self.assertEqual(
            response.status_code,
            200,
            msg=f'Failed to obtain bearer token: {response.status_code} {response.text}',
        )
        data = json.loads(response.text)
        self.assertIn('access_token', data)
        return data['access_token']

    def _login(self, email=None, password=None, extra_headers=None):
        url = f'{self.base_url}/api/v1/users/login'
        payload = {
            'email': email or self.user_email,
            'password': password or self.user_password,
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.bearer_token}',
            'User-Agent': self.default_user_agent,
            'Accept-Language': self.default_language,
        }
        if extra_headers:
            headers.update(extra_headers)

        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json',
        )
        data = json.loads(response.text)
        return response, data

    def _call_me(self, session_id, override_headers=None):
        url = f'{self.base_url}/api/v1/me'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.bearer_token}',
            'X-Openerp-Session-Id': session_id,
            'User-Agent': self.default_user_agent,
            'Accept-Language': self.default_language,
        }
        if override_headers:
            headers.update(override_headers)

        response = self.opener.post(
            url,
            data=json.dumps({}),
            headers=headers,
            content_type='application/json',
        )
        data = json.loads(response.text)
        return response, data

    def _logout(self, session_id, override_headers=None):
        url = f'{self.base_url}/api/v1/users/logout'
        payload = {'session_id': session_id} if session_id else {}
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.bearer_token}',
            'User-Agent': self.default_user_agent,
            'Accept-Language': self.default_language,
        }
        if override_headers:
            headers.update(override_headers)

        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json',
        )
        data = json.loads(response.text)
        return response, data

    def _get_api_session(self, session_id):
        return self.api_session_model.search([
            ('session_id', '=', session_id),
        ], limit=1)

    # ------------------------------------------------------------------
    # Test scenarios
    # ------------------------------------------------------------------
    def test_login_creates_session_with_security_token(self):
        """Login must yield an active API session including the JWT token."""
        response, data = self._login()
        self.assertEqual(response.status_code, 200, data)
        session_id = data.get('session_id')
        self.assertTrue(session_id)

        api_session = self._get_api_session(session_id)
        self.assertTrue(api_session, 'API session record should exist')
        self.assertTrue(api_session.is_active)
        self.assertTrue(api_session.security_token)

        me_response, me_data = self._call_me(session_id)
        self.assertEqual(me_response.status_code, 200, me_data)
        self.assertIn('user', me_data)
        self.assertEqual(me_data['user']['email'], self.user_email)

    def test_login_replaces_previous_session(self):
        """A new login must revoke any previous active sessions for the user."""
        first_response, first_data = self._login(extra_headers={'User-Agent': 'QA-Agent/1.0'})
        self.assertEqual(first_response.status_code, 200)
        first_session_id = first_data['session_id']

        second_response, second_data = self._login(extra_headers={'User-Agent': 'QA-Agent/2.0'})
        self.assertEqual(second_response.status_code, 200)
        second_session_id = second_data['session_id']
        self.assertNotEqual(first_session_id, second_session_id)

        first_session = self._get_api_session(first_session_id)
        self.assertTrue(first_session)
        self.assertFalse(first_session.is_active)
        self.assertTrue(first_session.logout_at)

        second_session = self._get_api_session(second_session_id)
        self.assertTrue(second_session.is_active)

    def test_logout_revokes_session_and_blocks_me(self):
        """Logout must deactivate the session and block further /me calls."""
        response, data = self._login()
        session_id = data['session_id']

        me_response, _ = self._call_me(session_id)
        self.assertEqual(me_response.status_code, 200)

        logout_response, logout_data = self._logout(session_id)
        self.assertEqual(logout_response.status_code, 200, logout_data)
        self.assertEqual(logout_data.get('message'), 'Logged out successfully')

        post_logout_me, post_logout_data = self._call_me(session_id)
        self.assertEqual(post_logout_me.status_code, 401)
        self.assertEqual(post_logout_data['error']['message'], 'Invalid or expired session')

    def test_logout_requires_session_id(self):
        """Logout without session information must be rejected."""
        response, data = self._logout(session_id=None)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error']['message'], 'session_id is required')

    def test_me_requires_security_token(self):
        """/me must refuse sessions missing the generated security JWT."""
        response, data = self._login()
        session_id = data['session_id']

        api_session = self._get_api_session(session_id)
        self.assertTrue(api_session)
        api_session.write({'security_token': False})

        me_response, me_data = self._call_me(session_id)
        self.assertEqual(me_response.status_code, 401)
        self.assertEqual(me_data['error']['message'], 'Session token required')

    def test_me_detects_fingerprint_mismatch(self):
        """Tampering the session fingerprint must invalidate the session."""
        response, data = self._login()
        session_id = data['session_id']

        api_session = self._get_api_session(session_id)
        self.assertTrue(api_session)
        original_token = api_session.security_token
        self.assertTrue(original_token)

        try:
            payload = jwt.decode(
                original_token,
                self.secret,
                algorithms=['HS256'],
                options={'verify_signature': True},
            )
        except jwt.InvalidSignatureError:
            payload = jwt.decode(
                original_token,
                options={'verify_signature': False},
                algorithms=['HS256'],
            )
        fingerprint = payload.get('fingerprint', {})
        fingerprint['ua'] = 'Malicious-Agent/9.9'
        payload['fingerprint'] = fingerprint
        forged_token = jwt.encode(payload, self.secret, algorithm='HS256')
        if isinstance(forged_token, bytes):
            forged_token = forged_token.decode('utf-8')
        api_session.write({'security_token': forged_token})

        forged_me_response, forged_me_data = self._call_me(session_id)
        self.assertEqual(forged_me_response.status_code, 401)
        self.assertEqual(forged_me_data['error']['message'], 'Session validation failed')

        # Restore original token to avoid side effects on other tests.
        api_session.write({'security_token': original_token})

    def test_session_hijack_reveals_stolen_user(self):
        """/me must reflect the session owner even when reused by another login."""
        first_response, first_data = self._login(
            email=self.user_email,
            password=self.user_password,
            extra_headers={'User-Agent': 'Hijacker-Agent/1.0'},
        )
        self.assertEqual(first_response.status_code, 200, first_data)
        first_session = first_data['session_id']

        second_response, second_data = self._login(
            email=self.user_b_email,
            password=self.user_b_password,
            extra_headers={'User-Agent': 'Victim-Agent/2.0'},
        )
        self.assertEqual(second_response.status_code, 200, second_data)
        second_session = second_data['session_id']

        hijack_response, hijack_data = self._call_me(
            second_session,
            override_headers={'User-Agent': 'Victim-Agent/2.0'},
        )
        self.assertEqual(hijack_response.status_code, 200, hijack_data)
        self.assertEqual(hijack_data['user']['email'], self.user_b_email)
        self.assertNotEqual(hijack_data['user']['email'], self.user_email)

        # sanity: original owner still sees own data
        original_response, original_data = self._call_me(
            first_session,
            override_headers={'User-Agent': 'Hijacker-Agent/1.0'},
        )
        self.assertEqual(original_response.status_code, 200, original_data)
        self.assertEqual(original_data['user']['email'], self.user_email)
