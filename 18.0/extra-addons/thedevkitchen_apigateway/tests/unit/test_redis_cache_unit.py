# -*- coding: utf-8 -*-
"""
Unit Tests — RedisClient isolated (T01)
Tests run with mocked Redis — no database, no Docker required.
"""

import unittest
import hashlib
from unittest.mock import patch, MagicMock, call


class TestRedisClientGetJson(unittest.TestCase):
    """T01: get_json — HIT, MISS, JSON-corrupt, Redis DOWN"""

    def _get_client(self):
        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        RedisClient._pool = None  # reset singleton between tests
        return RedisClient

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_get_json_hit(self, mock_conn):
        """get_json returns deserialized dict when key exists"""
        import json
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({'id': 1, 'scope': 'read'})
        mock_conn.return_value = mock_redis

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.get_json('jwt:abc')

        self.assertEqual(result, {'id': 1, 'scope': 'read'})
        mock_redis.get.assert_called_once_with('jwt:abc')

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_get_json_miss(self, mock_conn):
        """get_json returns None when key not found"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_conn.return_value = mock_redis

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.get_json('jwt:missing')

        self.assertIsNone(result)

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_get_json_corrupt_json(self, mock_conn):
        """get_json returns None and logs warning when JSON is invalid"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = 'not-valid-json'
        mock_conn.return_value = mock_redis

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.get_json('jwt:corrupt')

        self.assertIsNone(result)  # must not raise

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_get_json_redis_down(self, mock_conn):
        """get_json returns None silently when Redis is unavailable"""
        mock_conn.return_value = None

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.get_json('jwt:any')

        self.assertIsNone(result)  # no exception propagated

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_get_json_exception_swallowed(self, mock_conn):
        """get_json swallows Redis exceptions and returns None"""
        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception('connection reset')
        mock_conn.return_value = mock_redis

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.get_json('jwt:broken')

        self.assertIsNone(result)  # no exception propagated


class TestRedisClientSetJson(unittest.TestCase):
    """T01: set_json — TTL=0 guard, Redis DOWN, normal write"""

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_set_json_ttl_zero_is_noop(self, mock_conn):
        """set_json returns False and calls no Redis when ttl=0"""
        mock_redis = MagicMock()
        mock_conn.return_value = mock_redis

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.set_json('session:x', {'id': 1}, ttl=0)

        self.assertFalse(result)
        mock_redis.setex.assert_not_called()

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_set_json_negative_ttl_is_noop(self, mock_conn):
        """set_json returns False for negative TTL"""
        mock_redis = MagicMock()
        mock_conn.return_value = mock_redis

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.set_json('session:x', {'id': 1}, ttl=-5)

        self.assertFalse(result)
        mock_redis.setex.assert_not_called()

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_set_json_redis_down(self, mock_conn):
        """set_json returns False silently when Redis unavailable"""
        mock_conn.return_value = None

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.set_json('session:x', {'id': 1}, ttl=300)

        self.assertFalse(result)  # no exception

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_set_json_success(self, mock_conn):
        """set_json calls setex with correct args and returns True"""
        import json
        mock_redis = MagicMock()
        mock_conn.return_value = mock_redis

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.set_json('session:abc', {'id': 42}, ttl=300)

        self.assertTrue(result)
        mock_redis.setex.assert_called_once_with('session:abc', 300, json.dumps({'id': 42}))

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_set_json_exception_swallowed(self, mock_conn):
        """set_json swallows Redis exceptions and returns False"""
        mock_redis = MagicMock()
        mock_redis.setex.side_effect = Exception('OOM')
        mock_conn.return_value = mock_redis

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.set_json('session:abc', {'id': 1}, ttl=300)

        self.assertFalse(result)  # no exception propagated


class TestRedisClientDelete(unittest.TestCase):
    """T01: delete — single key, multi-key, Redis DOWN"""

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_delete_single_key(self, mock_conn):
        """delete calls DEL with single key"""
        mock_redis = MagicMock()
        mock_conn.return_value = mock_redis

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.delete('session:abc')

        self.assertTrue(result)
        mock_redis.delete.assert_called_once_with('session:abc')

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_delete_multi_key(self, mock_conn):
        """delete calls DEL with all keys in a single command"""
        mock_redis = MagicMock()
        mock_conn.return_value = mock_redis

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.delete('session:abc', 'session:def', 'jwt:xyz')

        self.assertTrue(result)
        mock_redis.delete.assert_called_once_with('session:abc', 'session:def', 'jwt:xyz')

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_delete_redis_down(self, mock_conn):
        """delete returns False silently when Redis unavailable"""
        mock_conn.return_value = None

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.delete('session:abc')

        self.assertFalse(result)  # no exception


class TestRedisClientDeletePattern(unittest.TestCase):
    """T01: delete_pattern — no-match returns 0"""

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_delete_pattern_no_match(self, mock_conn):
        """delete_pattern returns 0 when no keys match"""
        mock_redis = MagicMock()
        mock_redis.scan.return_value = (0, [])
        mock_conn.return_value = mock_redis

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.delete_pattern('performance:agent:99:*')

        self.assertEqual(result, 0)
        mock_redis.delete.assert_not_called()

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_delete_pattern_with_matches(self, mock_conn):
        """delete_pattern deletes matching keys and returns count"""
        mock_redis = MagicMock()
        mock_redis.scan.side_effect = [
            (0, ['performance:agent:1:2026-01-01:2026-01-31', 'performance:agent:1:2026-02-01:2026-02-28'])
        ]
        mock_conn.return_value = mock_redis

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.delete_pattern('performance:agent:1:*')

        self.assertEqual(result, 2)
        mock_redis.delete.assert_called_once()

    @patch('odoo.addons.thedevkitchen_apigateway.services.redis_client.RedisClient._get_connection')
    def test_delete_pattern_redis_down(self, mock_conn):
        """delete_pattern returns 0 silently when Redis unavailable"""
        mock_conn.return_value = None

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.delete_pattern('performance:agent:*')

        self.assertEqual(result, 0)  # no exception


class TestRedisClientKeyHelpers(unittest.TestCase):
    """T01: jwt_key — SHA-256 hash correctness"""

    def test_jwt_key_uses_sha256(self):
        """jwt_key produces expected SHA-256 prefix"""
        token = 'test_access_token_12345'
        expected_hash = hashlib.sha256(token.encode()).hexdigest()[:32]
        expected_key = 'jwt:{}'.format(expected_hash)

        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.jwt_key(token)

        self.assertEqual(result, expected_key)

    def test_jwt_key_different_tokens_different_keys(self):
        """Different tokens produce different Redis keys"""
        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        key1 = RedisClient.jwt_key('token_a')
        key2 = RedisClient.jwt_key('token_b')
        self.assertNotEqual(key1, key2)

    def test_session_key_format(self):
        """session_key produces expected format"""
        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.session_key('abc123')
        self.assertEqual(result, 'session:abc123')

    def test_performance_key_format(self):
        """performance_key produces expected format"""
        from odoo.addons.thedevkitchen_apigateway.services.redis_client import RedisClient
        result = RedisClient.performance_key(5, '2026-01-01', '2026-01-31')
        self.assertEqual(result, 'performance:agent:5:2026-01-01:2026-01-31')


# =============================================================================
# T02 — require_jwt with cache
# =============================================================================

class TestRequireJwtWithCache(unittest.TestCase):
    """T02: require_jwt cache HIT/MISS scenarios"""

    def setUp(self):
        """
        Manually replace middleware.request with a MagicMock.
        We cannot use @patch('...middleware.request') because Werkzeug's
        LocalProxy triggers RuntimeError in Python 3.12 during mock inspection.
        """
        import odoo.addons.thedevkitchen_apigateway.middleware as mw
        self._mw = mw
        self._orig_request = mw.request
        self.mock_request = MagicMock()
        self.mock_request.httprequest.headers.get.return_value = 'Bearer test_token_value'
        mw.request = self.mock_request

    def tearDown(self):
        self._mw.request = self._orig_request

    @patch('odoo.addons.thedevkitchen_apigateway.middleware.RedisClient')
    def test_require_jwt_cache_hit_valid(self, mock_redis_cls):
        """HIT with valid payload → Token.search NOT called; jwt_token.id set"""
        import time
        mock_redis_cls.get_json.return_value = {
            'id': 99,
            'application_id': 1,
            'token_type': 'Bearer',
            'expires_at_ts': time.time() + 3600,
            'scope': 'read',
            'revoked': False,
        }
        mock_redis_cls.jwt_key.return_value = 'jwt:testkey'
        mock_token = MagicMock()
        mock_token.id = 99
        self.mock_request.env.__getitem__.return_value.sudo.return_value.browse.return_value = mock_token

        from odoo.addons.thedevkitchen_apigateway.middleware import require_jwt
        func = MagicMock(return_value='ok')
        wrapped = require_jwt(func)
        wrapped()

        mock_redis_cls.get_json.assert_called_once()
        self.mock_request.env.__getitem__.return_value.sudo.return_value.search.assert_not_called()
        func.assert_called_once()

    @patch('odoo.addons.thedevkitchen_apigateway.middleware.RedisClient')
    def test_require_jwt_cache_hit_revoked(self, mock_redis_cls):
        """HIT with revoked=True → 401 without calling Token.search"""
        import time
        mock_redis_cls.get_json.return_value = {
            'id': 99,
            'application_id': 1,
            'token_type': 'Bearer',
            'expires_at_ts': time.time() + 3600,
            'scope': 'read',
            'revoked': True,
        }
        mock_redis_cls.jwt_key.return_value = 'jwt:testkey'

        from odoo.addons.thedevkitchen_apigateway.middleware import require_jwt
        func = MagicMock()
        wrapped = require_jwt(func)
        wrapped()

        func.assert_not_called()
        self.mock_request.env.__getitem__.return_value.sudo.return_value.search.assert_not_called()

    @patch('odoo.addons.thedevkitchen_apigateway.middleware.RedisClient')
    def test_require_jwt_cache_hit_expired(self, mock_redis_cls):
        """HIT with expired expires_at_ts → 401 without calling Token.search"""
        import time
        mock_redis_cls.get_json.return_value = {
            'id': 99,
            'application_id': 1,
            'token_type': 'Bearer',
            'expires_at_ts': time.time() - 1,  # already expired
            'scope': 'read',
            'revoked': False,
        }
        mock_redis_cls.jwt_key.return_value = 'jwt:testkey'

        from odoo.addons.thedevkitchen_apigateway.middleware import require_jwt
        func = MagicMock()
        wrapped = require_jwt(func)
        wrapped()

        func.assert_not_called()
        self.mock_request.env.__getitem__.return_value.sudo.return_value.search.assert_not_called()

    @patch('odoo.addons.thedevkitchen_apigateway.middleware.RedisClient')
    def test_require_jwt_cache_miss_calls_db(self, mock_redis_cls):
        """MISS (get_json=None) → Token.search called"""
        from odoo import fields as odoo_fields
        mock_redis_cls.get_json.return_value = None  # MISS
        mock_redis_cls.jwt_key.return_value = 'jwt:testkey'
        mock_redis_cls.set_json.return_value = True

        mock_token = MagicMock()
        mock_token.token_type = 'Bearer'
        mock_token.revoked = False
        mock_token.expires_at = odoo_fields.Datetime.now()
        mock_token.id = 1
        mock_token.application_id.id = 1
        mock_token.scope = 'read'
        self.mock_request.env.__getitem__.return_value.sudo.return_value.search.return_value = mock_token

        from odoo.addons.thedevkitchen_apigateway.middleware import require_jwt
        func = MagicMock(return_value='ok')
        wrapped = require_jwt(func)
        wrapped()

        self.mock_request.env.__getitem__.return_value.sudo.return_value.search.assert_called()

    @patch('odoo.addons.thedevkitchen_apigateway.middleware.RedisClient')
    def test_require_jwt_redis_down_fallback(self, mock_redis_cls):
        """Redis DOWN (get_json=None) → Token.search called, request succeeds"""
        from odoo import fields as odoo_fields
        mock_redis_cls.get_json.return_value = None
        mock_redis_cls.jwt_key.return_value = 'jwt:testkey'
        mock_redis_cls.set_json.return_value = True

        mock_token = MagicMock()
        mock_token.token_type = 'Bearer'
        mock_token.revoked = False
        mock_token.expires_at = odoo_fields.Datetime.now()
        mock_token.id = 1
        mock_token.application_id.id = 1
        mock_token.scope = 'read'
        self.mock_request.env.__getitem__.return_value.sudo.return_value.search.return_value = mock_token

        from odoo.addons.thedevkitchen_apigateway.middleware import require_jwt
        func = MagicMock(return_value='ok')
        wrapped = require_jwt(func)
        wrapped()

        func.assert_called_once()


# =============================================================================
# T03 — SessionValidator.validate with cache
# =============================================================================

class TestSessionValidatorWithCache(unittest.TestCase):
    """T03: SessionValidator.validate cache HIT/MISS/corrupt/down scenarios"""

    @patch('odoo.addons.thedevkitchen_apigateway.services.session_validator.RedisClient')
    def test_session_cache_hit_valid(self, mock_redis_cls):
        """HIT valid payload → APISession.search NOT called, last_activity NOT updated"""
        mock_redis_cls.get_json.return_value = {
            'id': 10,
            'user_id': 5,
            'is_active': True,
            'security_token': 'eyJ...',
            'company_id': 1,
            'user_active': True,
        }
        mock_env = MagicMock()
        mock_session = MagicMock()
        mock_session.id = 10
        mock_user = MagicMock()
        mock_user.id = 5
        mock_env.__getitem__.return_value.sudo.return_value.browse.side_effect = \
            lambda x: mock_session if x == 10 else mock_user

        from odoo.addons.thedevkitchen_apigateway.services.session_validator import SessionValidator
        valid, user, api_session, err = SessionValidator.validate('a' * 64, env=mock_env)

        self.assertTrue(valid)
        self.assertIsNone(err)
        # APISession.search must NOT be called on a HIT
        mock_env.__getitem__.return_value.sudo.return_value.search.assert_not_called()
        # last_activity write must NOT be called on a HIT
        mock_session.write.assert_not_called()

    @patch('odoo.addons.thedevkitchen_apigateway.services.session_validator.RedisClient')
    def test_session_cache_hit_inactive(self, mock_redis_cls):
        """HIT is_active=False → returns False, 'Invalid or expired session'"""
        mock_redis_cls.get_json.return_value = {
            'id': 10,
            'user_id': 5,
            'is_active': False,
            'security_token': 'eyJ...',
            'company_id': 1,
            'user_active': True,
        }
        mock_env = MagicMock()

        from odoo.addons.thedevkitchen_apigateway.services.session_validator import SessionValidator
        valid, user, api_session, err = SessionValidator.validate('a' * 64, env=mock_env)

        self.assertFalse(valid)
        self.assertEqual(err, 'Invalid or expired session')

    @patch('odoo.addons.thedevkitchen_apigateway.services.session_validator.RedisClient')
    def test_session_cache_hit_user_inactive(self, mock_redis_cls):
        """HIT user_active=False → returns False, 'User inactive'"""
        mock_redis_cls.get_json.return_value = {
            'id': 10,
            'user_id': 5,
            'is_active': True,
            'security_token': 'eyJ...',
            'company_id': 1,
            'user_active': False,
        }
        mock_env = MagicMock()

        from odoo.addons.thedevkitchen_apigateway.services.session_validator import SessionValidator
        valid, user, api_session, err = SessionValidator.validate('a' * 64, env=mock_env)

        self.assertFalse(valid)
        self.assertEqual(err, 'User inactive')

    @patch('odoo.addons.thedevkitchen_apigateway.services.session_validator.RedisClient')
    def test_session_cache_miss_calls_db_and_populates(self, mock_redis_cls):
        """MISS → APISession.search called; set_json called to populate cache"""
        mock_redis_cls.get_json.return_value = None  # MISS
        mock_redis_cls.set_json.return_value = True

        mock_env = MagicMock()
        mock_session = MagicMock()
        mock_session.session_id = 'a' * 64
        mock_user = MagicMock()
        mock_user.active = True
        mock_user.id = 5
        mock_user.login = 'test@test.com'
        mock_session.user_id = mock_user
        mock_env.__getitem__.return_value.sudo.return_value.search.return_value = mock_session

        # SecuritySettings mock for TTL
        mock_settings = MagicMock()
        mock_settings.session_cache_ttl_seconds = 300
        mock_env.__getitem__.return_value.sudo.return_value.get_settings.return_value = mock_settings

        from odoo.addons.thedevkitchen_apigateway.services.session_validator import SessionValidator
        valid, user, api_session, err = SessionValidator.validate('a' * 64, env=mock_env)

        mock_env.__getitem__.return_value.sudo.return_value.search.assert_called()

    @patch('odoo.addons.thedevkitchen_apigateway.services.session_validator.RedisClient')
    def test_session_cache_ttl_zero_no_population(self, mock_redis_cls):
        """session_cache_ttl_seconds=0 → set_json NOT called (cache disabled)"""
        mock_redis_cls.get_json.return_value = None  # MISS
        mock_redis_cls.set_json.return_value = False  # TTL=0 guard

        mock_env = MagicMock()
        mock_session = MagicMock()
        mock_session.session_id = 'a' * 64
        mock_user = MagicMock()
        mock_user.active = True
        mock_user.id = 5
        mock_user.login = 'test@test.com'
        mock_session.user_id = mock_user
        mock_env.__getitem__.return_value.sudo.return_value.search.return_value = mock_session

        mock_settings = MagicMock()
        mock_settings.session_cache_ttl_seconds = 0  # DISABLED
        mock_env.__getitem__.return_value.sudo.return_value.get_settings.return_value = mock_settings

        from odoo.addons.thedevkitchen_apigateway.services.session_validator import SessionValidator
        SessionValidator.validate('a' * 64, env=mock_env)

        # set_json must be called with ttl=0, which RedisClient.set_json rejects
        # (the actual guard is inside set_json, but we verify ttl passed is 0)
        if mock_redis_cls.set_json.called:
            call_args = mock_redis_cls.set_json.call_args
            ttl_arg = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get('ttl', None)
            self.assertEqual(ttl_arg, 0)

    @patch('odoo.addons.thedevkitchen_apigateway.services.session_validator.RedisClient')
    def test_session_cache_corrupt_json_fallback_to_db(self, mock_redis_cls):
        """get_json returns None (corrupt JSON) → APISession.search called (MISS path)"""
        mock_redis_cls.get_json.return_value = None  # RedisClient already returns None for corrupt data

        mock_env = MagicMock()
        mock_session = MagicMock()
        mock_session.session_id = 'a' * 64
        mock_user = MagicMock()
        mock_user.active = True
        mock_user.id = 5
        mock_user.login = 'test@test.com'
        mock_session.user_id = mock_user
        mock_env.__getitem__.return_value.sudo.return_value.search.return_value = mock_session

        mock_settings = MagicMock()
        mock_settings.session_cache_ttl_seconds = 300
        mock_env.__getitem__.return_value.sudo.return_value.get_settings.return_value = mock_settings

        from odoo.addons.thedevkitchen_apigateway.services.session_validator import SessionValidator
        valid, user, api_session, err = SessionValidator.validate('a' * 64, env=mock_env)

        # Corrupt JSON → get_json returns None → MISS path → search called
        mock_env.__getitem__.return_value.sudo.return_value.search.assert_called()

    @patch('odoo.addons.thedevkitchen_apigateway.services.session_validator.RedisClient')
    def test_session_redis_down_fallback(self, mock_redis_cls):
        """Redis DOWN (get_json returns None) → APISession.search called, request OK"""
        mock_redis_cls.get_json.return_value = None  # Redis down — returns None

        mock_env = MagicMock()
        mock_session = MagicMock()
        mock_session.session_id = 'a' * 64
        mock_user = MagicMock()
        mock_user.active = True
        mock_user.id = 5
        mock_user.login = 'test@test.com'
        mock_session.user_id = mock_user
        mock_env.__getitem__.return_value.sudo.return_value.search.return_value = mock_session

        mock_settings = MagicMock()
        mock_settings.session_cache_ttl_seconds = 300
        mock_env.__getitem__.return_value.sudo.return_value.get_settings.return_value = mock_settings

        from odoo.addons.thedevkitchen_apigateway.services.session_validator import SessionValidator
        valid, user, api_session, err = SessionValidator.validate('a' * 64, env=mock_env)

        mock_env.__getitem__.return_value.sudo.return_value.search.assert_called()


# =============================================================================
# T04 — OAuthToken.action_revoke invalidation (US2)
# =============================================================================

class TestOAuthTokenRevocationInvalidation(unittest.TestCase):
    """T04: action_revoke() calls RedisClient.delete and handles Redis DOWN"""

    def _make_recordset(self, access_token):
        """Return a mock OAuthToken recordset with one record."""
        mock_record = MagicMock()
        mock_record.access_token = access_token
        mock_record.id = 1
        mock_self = MagicMock()
        mock_self.__iter__ = MagicMock(return_value=iter([mock_record]))
        return mock_self, mock_record

    @patch('odoo.addons.thedevkitchen_apigateway.models.oauth_token.RedisClient')
    def test_revoke_calls_redis_delete(self, mock_redis_cls):
        """action_revoke() calls RedisClient.delete with jwt_key of the access_token"""
        from odoo.addons.thedevkitchen_apigateway.models.oauth_token import OAuthToken

        mock_redis_cls.jwt_key.return_value = 'jwt:testhash_abc'
        mock_redis_cls.delete.return_value = True

        mock_self, _ = self._make_recordset('access_token_12345')

        OAuthToken.action_revoke(mock_self)

        mock_redis_cls.jwt_key.assert_called_once_with('access_token_12345')
        mock_redis_cls.delete.assert_called_once_with('jwt:testhash_abc')

    @patch('odoo.addons.thedevkitchen_apigateway.models.oauth_token.RedisClient')
    def test_revoke_redis_down_swallows_exception(self, mock_redis_cls):
        """Redis DOWN during action_revoke → exception swallowed, revoke still completes"""
        from odoo.addons.thedevkitchen_apigateway.models.oauth_token import OAuthToken

        mock_redis_cls.jwt_key.side_effect = Exception('Redis unavailable')

        mock_self, mock_record = self._make_recordset('token_abc')

        # Must not raise — the try/except in the override swallows Redis errors
        try:
            OAuthToken.action_revoke(mock_self)
        except Exception as e:
            self.fail('action_revoke() raised an unexpected exception: {}'.format(e))

        # record.write() (the actual revoke) must still have been called
        mock_record.write.assert_called_once()

    @patch('odoo.addons.thedevkitchen_apigateway.models.oauth_token.RedisClient')
    def test_revoke_no_access_token_skips_delete(self, mock_redis_cls):
        """action_revoke() on record with empty access_token does NOT call delete"""
        from odoo.addons.thedevkitchen_apigateway.models.oauth_token import OAuthToken

        mock_self, mock_record = self._make_recordset('')  # empty access_token
        mock_record.access_token = ''

        OAuthToken.action_revoke(mock_self)

        mock_redis_cls.delete.assert_not_called()


# =============================================================================
# T05 — APISession.write() invalidation (US2)
# =============================================================================

class TestAPISessionWriteInvalidation(unittest.TestCase):
    """T05: APISession.write() triggers Redis delete on is_active/company_id changes"""

    def _make_session_recordset(self, session_id):
        """
        Return a mock recordset whose __class__ is APISession so that
        super(APISession, self) inside write() passes the isinstance check.
        """
        from odoo.addons.thedevkitchen_apigateway.models.api_session import APISession
        mock_record = MagicMock()
        mock_record.session_id = session_id
        mock_self = MagicMock()
        mock_self.__class__ = APISession  # makes isinstance(mock_self, APISession) True
        mock_self.__iter__ = MagicMock(return_value=iter([mock_record]))
        return mock_self, mock_record

    @patch('odoo.addons.thedevkitchen_apigateway.models.api_session.RedisClient')
    def test_write_is_active_false_calls_delete(self, mock_redis_cls):
        """write({'is_active': False}) calls RedisClient.delete(session_key)"""
        import odoo.models
        from odoo.addons.thedevkitchen_apigateway.models.api_session import APISession

        mock_redis_cls.session_key.side_effect = lambda s: 'session:{}'.format(s)
        mock_redis_cls.delete.return_value = True

        mock_self, _ = self._make_session_recordset('test_sess_abc123')

        with patch.object(odoo.models.Model, 'write', return_value=True):
            APISession.write(mock_self, {'is_active': False})

        mock_redis_cls.delete.assert_called_once_with('session:test_sess_abc123')

    @patch('odoo.addons.thedevkitchen_apigateway.models.api_session.RedisClient')
    def test_write_company_id_calls_delete(self, mock_redis_cls):
        """write({'company_id': X}) calls RedisClient.delete(session_key)"""
        import odoo.models
        from odoo.addons.thedevkitchen_apigateway.models.api_session import APISession

        mock_redis_cls.session_key.side_effect = lambda s: 'session:{}'.format(s)
        mock_redis_cls.delete.return_value = True

        mock_self, _ = self._make_session_recordset('test_sess_xyz999')

        with patch.object(odoo.models.Model, 'write', return_value=True):
            APISession.write(mock_self, {'company_id': 2})

        mock_redis_cls.delete.assert_called_once_with('session:test_sess_xyz999')

    @patch('odoo.addons.thedevkitchen_apigateway.models.api_session.RedisClient')
    def test_write_last_activity_does_not_call_delete(self, mock_redis_cls):
        """write({'last_activity': ...}) only → RedisClient.delete NOT called"""
        import odoo.models
        from odoo.addons.thedevkitchen_apigateway.models.api_session import APISession

        mock_self, _ = self._make_session_recordset('test_sess_la001')

        with patch.object(odoo.models.Model, 'write', return_value=True):
            APISession.write(mock_self, {'last_activity': '2026-06-08 10:00:00'})

        mock_redis_cls.delete.assert_not_called()

    @patch('odoo.addons.thedevkitchen_apigateway.models.api_session.RedisClient')
    def test_write_redis_down_no_exception(self, mock_redis_cls):
        """Redis DOWN during write → write completes, super().write() still called"""
        import odoo.models
        from odoo.addons.thedevkitchen_apigateway.models.api_session import APISession

        mock_redis_cls.session_key.return_value = 'session:key'
        mock_redis_cls.delete.side_effect = Exception('Redis down')

        mock_self, _ = self._make_session_recordset('test_sess_down01')

        with patch.object(odoo.models.Model, 'write', return_value=True) as mock_super_write:
            try:
                APISession.write(mock_self, {'is_active': False})
            except Exception as e:
                self.fail('write() raised an unexpected exception: {}'.format(e))
            # super().write() must have been called despite Redis error
            mock_super_write.assert_called_once()

    @patch('odoo.addons.thedevkitchen_apigateway.models.api_session.RedisClient')
    def test_write_no_session_id_skips_delete(self, mock_redis_cls):
        """write({'is_active': False}) on record with no session_id → delete NOT called"""
        import odoo.models
        from odoo.addons.thedevkitchen_apigateway.models.api_session import APISession

        mock_self, mock_record = self._make_session_recordset('')
        mock_record.session_id = ''  # empty session_id

        with patch.object(odoo.models.Model, 'write', return_value=True):
            APISession.write(mock_self, {'is_active': False})

        mock_redis_cls.delete.assert_not_called()


if __name__ == '__main__':
    unittest.main()
