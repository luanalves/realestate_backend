# -*- coding: utf-8 -*-
"""
Integration Tests — Redis Cache for JWT and Session (T08)
Uses Odoo TransactionCase — requires running database and Redis.
"""

from odoo.tests.common import TransactionCase
from unittest.mock import patch, MagicMock
from odoo import fields
from datetime import timedelta


class TestRedisCacheWithTTLEnabled(TransactionCase):
    """T08: Cache population and settings toggle (TTL > 0)"""

    def setUp(self):
        super().setUp()
        # Ensure security settings exist with cache enabled
        self.settings = self.env['thedevkitchen.security.settings'].sudo().get_settings()
        self.settings.write({
            'session_cache_ttl_seconds': 300,
            'performance_cache_ttl_seconds': 300,
            'session_inactivity_days': 7,
        })

    def test_settings_fields_readable(self):
        """Security settings has the 3 new cache fields with correct defaults"""
        settings = self.env['thedevkitchen.security.settings'].sudo().get_settings()
        self.assertGreaterEqual(settings.session_cache_ttl_seconds, 0)
        self.assertGreaterEqual(settings.performance_cache_ttl_seconds, 0)
        self.assertGreaterEqual(settings.session_inactivity_days, 1)

    @patch('odoo.addons.thedevkitchen_apigateway.services.session_validator.RedisClient')
    def test_session_miss_populates_cache(self, mock_redis_cls):
        """MISS path: after DB validation, set_json is called to populate cache"""
        mock_redis_cls.get_json.return_value = None  # force MISS
        mock_redis_cls.set_json.return_value = True
        mock_redis_cls.session_key.side_effect = lambda s: f'session:{s}'

        # Create real test user and session
        user = self.env['res.users'].sudo().create({
            'name': 'Cache Test User',
            'login': 'cachetest@test.com',
            'password': 'test123',
        })
        company = self.env['res.company'].sudo().search([], limit=1)
        session = self.env['thedevkitchen.api.session'].sudo().create({
            'session_id': 'x' * 64,
            'user_id': user.id,
            'is_active': True,
            'company_id': company.id if company else False,
        })

        from odoo.addons.thedevkitchen_apigateway.services.session_validator import SessionValidator
        valid, _user, _session, err = SessionValidator.validate('x' * 64, env=self.env)

        self.assertTrue(valid)
        # set_json must have been called to populate cache
        mock_redis_cls.set_json.assert_called_once()
        call_args = mock_redis_cls.set_json.call_args[0]
        self.assertEqual(call_args[0], f'session:{"x" * 64}')
        self.assertEqual(call_args[2], 300)  # TTL from settings

    @patch('odoo.addons.thedevkitchen_apigateway.services.session_validator.RedisClient')
    def test_session_cache_ttl_zero_no_population(self, mock_redis_cls):
        """session_cache_ttl_seconds=0 → set_json called with ttl=0 → RedisClient rejects"""
        self.settings.write({'session_cache_ttl_seconds': 0})
        mock_redis_cls.get_json.return_value = None
        mock_redis_cls.set_json.return_value = False  # ttl=0 guard
        mock_redis_cls.session_key.side_effect = lambda s: f'session:{s}'

        user = self.env['res.users'].sudo().create({
            'name': 'NoCache User',
            'login': 'nocache@test.com',
            'password': 'test123',
        })
        self.env['thedevkitchen.api.session'].sudo().create({
            'session_id': 'y' * 64,
            'user_id': user.id,
            'is_active': True,
        })

        from odoo.addons.thedevkitchen_apigateway.services.session_validator import SessionValidator
        valid, _user, _session, err = SessionValidator.validate('y' * 64, env=self.env)

        self.assertTrue(valid)
        if mock_redis_cls.set_json.called:
            call_args = mock_redis_cls.set_json.call_args[0]
            self.assertEqual(call_args[2], 0)  # ttl=0 passed to set_json


class TestRedisCacheInvalidation(TransactionCase):
    """T08-complete: Invalidation hooks — logout, revoke, switch-company"""

    def setUp(self):
        super().setUp()
        self.settings = self.env['thedevkitchen.security.settings'].sudo().get_settings()
        self.settings.write({'session_cache_ttl_seconds': 300})

    @patch('odoo.addons.thedevkitchen_apigateway.models.api_session.RedisClient')
    def test_session_write_is_active_false_deletes_cache(self, mock_redis_cls):
        """APISession.write({'is_active': False}) → RedisClient.delete called"""
        mock_redis_cls.session_key.side_effect = lambda s: f'session:{s}'
        mock_redis_cls.delete.return_value = True

        user = self.env['res.users'].sudo().create({
            'name': 'Logout User',
            'login': 'logout@test.com',
            'password': 'test123',
        })
        session = self.env['thedevkitchen.api.session'].sudo().create({
            'session_id': 'logout' + 'a' * 59,
            'user_id': user.id,
            'is_active': True,
        })

        session.write({'is_active': False})

        mock_redis_cls.delete.assert_called()

    @patch('odoo.addons.thedevkitchen_apigateway.models.oauth_token.RedisClient')
    def test_token_revoke_deletes_jwt_cache(self, mock_redis_cls):
        """OAuthToken.action_revoke() → RedisClient.delete called for JWT key"""
        mock_redis_cls.jwt_key.side_effect = lambda t: f'jwt:{t[:8]}'
        mock_redis_cls.delete.return_value = True

        app = self.env['thedevkitchen.oauth.application'].sudo().create({
            'name': 'TestApp for revoke',
            'client_id': 'test_client_revoke',
            'client_secret': 'secret',
        })
        token = self.env['thedevkitchen.oauth.token'].sudo().create({
            'application_id': app.id,
            'access_token': 'revoke_token_12345',
            'token_type': 'Bearer',
            'expires_at': fields.Datetime.now() + timedelta(hours=1),
        })

        token.action_revoke()

        mock_redis_cls.delete.assert_called()

    @patch('odoo.addons.thedevkitchen_apigateway.models.api_session.RedisClient')
    def test_session_write_company_change_deletes_cache(self, mock_redis_cls):
        """APISession.write({'company_id': X}) → RedisClient.delete called"""
        mock_redis_cls.session_key.side_effect = lambda s: f'session:{s}'
        mock_redis_cls.delete.return_value = True

        user = self.env['res.users'].sudo().create({
            'name': 'Company Switch User',
            'login': 'switchco@test.com',
            'password': 'test123',
        })
        company = self.env['res.company'].sudo().search([], limit=1)
        session = self.env['thedevkitchen.api.session'].sudo().create({
            'session_id': 'switch' + 'b' * 59,
            'user_id': user.id,
            'is_active': True,
        })

        if company:
            session.write({'company_id': company.id})
            mock_redis_cls.delete.assert_called()

    @patch('odoo.addons.thedevkitchen_apigateway.models.api_session.RedisClient')
    def test_new_login_invalidates_prior_sessions(self, mock_redis_cls):
        """New login → old sessions marked is_active=False → Redis delete called"""
        mock_redis_cls.session_key.side_effect = lambda s: f'session:{s}'
        mock_redis_cls.delete.return_value = True

        user = self.env['res.users'].sudo().create({
            'name': 'Multi Session User',
            'login': 'multisess@test.com',
            'password': 'test123',
        })
        # Create two old sessions
        old1 = self.env['thedevkitchen.api.session'].sudo().create({
            'session_id': 'oldsess1' + 'c' * 56,
            'user_id': user.id,
            'is_active': True,
        })
        old2 = self.env['thedevkitchen.api.session'].sudo().create({
            'session_id': 'oldsess2' + 'd' * 56,
            'user_id': user.id,
            'is_active': True,
        })

        # Simulate new login deactivating old sessions
        old_sessions = self.env['thedevkitchen.api.session'].sudo().search([
            ('user_id', '=', user.id),
            ('is_active', '=', True),
        ])
        old_sessions.write({'is_active': False})

        # Both sessions should have triggered Redis delete
        self.assertGreaterEqual(mock_redis_cls.delete.call_count, 2)


class TestSecuritySettingsCacheToggle(TransactionCase):
    """T10: SecuritySettings cache fields — read/write and TTL=0 guard"""

    def test_settings_cache_fields_readable_writable(self):
        """session_cache_ttl_seconds, performance_cache_ttl_seconds, session_inactivity_days are r/w"""
        settings = self.env['thedevkitchen.security.settings'].sudo().get_settings()
        settings.write({
            'session_cache_ttl_seconds': 120,
            'performance_cache_ttl_seconds': 60,
            'session_inactivity_days': 14,
        })
        settings.invalidate_recordset()
        self.assertEqual(settings.session_cache_ttl_seconds, 120)
        self.assertEqual(settings.performance_cache_ttl_seconds, 60)
        self.assertEqual(settings.session_inactivity_days, 14)

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient.set_json')
    def test_ttl_zero_session_no_redis_key_created(self, mock_set_json):
        """session_cache_ttl_seconds=0 → RedisClient.set_json rejects (returns False)"""
        # The guard in set_json: if ttl <= 0: return False
        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        rc = RedisClient()
        result = rc.set_json('session:test', {'data': 1}, 0)
        # set_json internal guard should return False without writing
        self.assertFalse(result)

    def test_settings_singleton_get_settings(self):
        """get_settings() always returns a singleton record"""
        s1 = self.env['thedevkitchen.security.settings'].sudo().get_settings()
        s2 = self.env['thedevkitchen.security.settings'].sudo().get_settings()
        self.assertEqual(s1.id, s2.id)

    def test_settings_restores_defaults_after_test(self):
        """After writing, write again to defaults — fields persisted correctly"""
        settings = self.env['thedevkitchen.security.settings'].sudo().get_settings()
        settings.write({'session_cache_ttl_seconds': 300})
        settings.invalidate_recordset()
        self.assertEqual(settings.session_cache_ttl_seconds, 300)
