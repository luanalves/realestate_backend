# -*- coding: utf-8 -*-
import json
import hashlib
import logging

_logger = logging.getLogger(__name__)


class RedisClient:
    _pool = None

    @classmethod
    def _get_connection(cls):
        """Lazy init connection pool. Returns None if Redis disabled or unavailable."""
        try:
            from odoo.tools import config
            if not config.get('enable_redis'):
                return None

            import redis

            if cls._pool is None:
                cls._pool = redis.ConnectionPool(
                    host=config.get('redis_host', 'localhost'),
                    port=int(config.get('redis_port', 6379)),
                    db=int(config.get('redis_dbindex', 1)),
                    password=config.get('redis_pass') or None,
                    decode_responses=True,
                    max_connections=10,
                )
            return redis.Redis(connection_pool=cls._pool)
        except Exception as e:
            _logger.warning('[CACHE] Redis connection failed: %s', e)
            return None

    @classmethod
    def get_json(cls, key):
        """GET key and deserialize JSON. Returns None on miss, error, or invalid JSON."""
        try:
            conn = cls._get_connection()
            if not conn:
                return None
            raw = conn.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            _logger.warning('[CACHE] get_json error key=%s: %s', key, e)
            return None

    @classmethod
    def set_json(cls, key, data, ttl):
        """SETEX key with JSON-serialized data. Returns False if ttl<=0 or on error."""
        if ttl <= 0:
            return False
        try:
            conn = cls._get_connection()
            if not conn:
                return False
            conn.setex(key, ttl, json.dumps(data))
            return True
        except Exception as e:
            _logger.warning('[CACHE] set_json error key=%s: %s', key, e)
            return False

    @classmethod
    def delete(cls, *keys):
        """DEL one or more keys. Returns False on error."""
        try:
            conn = cls._get_connection()
            if not conn:
                return False
            conn.delete(*keys)
            return True
        except Exception as e:
            _logger.warning('[CACHE] delete error keys=%s: %s', keys, e)
            return False

    @classmethod
    def delete_pattern(cls, pattern):
        """SCAN + DEL keys matching pattern. Returns count of deleted keys."""
        try:
            conn = cls._get_connection()
            if not conn:
                return 0
            cursor = 0
            keys = []
            while True:
                cursor, batch = conn.scan(cursor, match=pattern, count=100)
                keys.extend(batch)
                if cursor == 0:
                    break
            if keys:
                conn.delete(*keys)
            return len(keys)
        except Exception as e:
            _logger.warning('[CACHE] delete_pattern error pattern=%s: %s', pattern, e)
            return 0

    @classmethod
    def is_available(cls):
        """PING Redis. Returns False if unavailable."""
        try:
            conn = cls._get_connection()
            if not conn:
                return False
            conn.ping()
            return True
        except Exception:
            return False

    @staticmethod
    def jwt_key(raw_token):
        """Compute Redis key for a JWT access token (SHA-256 hash, first 32 hex chars)."""
        return 'jwt:{}'.format(hashlib.sha256(raw_token.encode()).hexdigest()[:32])

    @staticmethod
    def session_key(session_id):
        """Compute Redis key for a session ID."""
        return 'session:{}'.format(session_id)

    @staticmethod
    def performance_key(agent_id, date_from, date_to):
        """Compute Redis key for agent performance metrics."""
        return 'performance:agent:{}:{}:{}'.format(agent_id, date_from, date_to)
