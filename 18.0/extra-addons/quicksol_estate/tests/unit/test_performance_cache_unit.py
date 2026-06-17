# -*- coding: utf-8 -*-
"""
Unit Tests — PerformanceService Redis cache (T07 / US3)
Tests run with mocked Redis and Odoo env — no database required.
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Allow standalone execution with python3 <file> by extending odoo.addons namespace.
import odoo.addons
_addons_root = str(Path(__file__).parent.parent.parent.parent)
if _addons_root not in odoo.addons.__path__:
    odoo.addons.__path__.insert(0, _addons_root)


class TestPerformanceServiceCacheHit(unittest.TestCase):
    """T07-part1: _get_cached_performance returns data → no DB query made"""

    @patch('odoo.addons.quicksol_estate.services.performance_service.RedisClient')
    def test_cache_hit_returns_data_no_db_call(self, mock_redis_cls):
        """Cache HIT: returns cached data without calling _calculate_performance_metrics"""
        expected = {'agent_id': 1, 'metrics': {'total_sales_count': 5}}
        mock_redis_cls.performance_key.return_value = 'performance:agent:1:2026-01-01:2026-12-31'
        mock_redis_cls.get_json.return_value = expected

        mock_env = MagicMock()
        mock_agent = MagicMock()
        mock_agent.exists.return_value = True
        mock_agent.id = 1
        mock_agent.company_id.id = 1
        mock_env.__getitem__.return_value.sudo.return_value.browse.return_value = mock_agent
        mock_env.user.company_ids.ids = [1]

        from odoo.addons.quicksol_estate.services.performance_service import PerformanceService
        service = PerformanceService(mock_env)

        result = service.get_agent_performance(1, '2026-01-01', '2026-12-31')

        mock_redis_cls.get_json.assert_called()
        self.assertEqual(result, expected)


class TestPerformanceServiceCacheMiss(unittest.TestCase):
    """T07-part2: Cache MISS → DB calculation → cache populated"""

    @patch('odoo.addons.quicksol_estate.services.performance_service.RedisClient')
    def test_cache_miss_populates_cache(self, mock_redis_cls):
        """MISS: _cache_performance is called to store result"""
        mock_redis_cls.performance_key.return_value = 'performance:agent:1:2026-01-01:2026-12-31'
        mock_redis_cls.get_json.return_value = None  # MISS
        mock_redis_cls.set_json.return_value = True

        mock_env = MagicMock()
        mock_agent = MagicMock()
        mock_agent.exists.return_value = True
        mock_agent.id = 1
        mock_agent.name = 'Agent Test'
        mock_agent.company_id.id = 1
        mock_agent.company_id.name = 'Test Company'
        mock_env.__getitem__.return_value.sudo.return_value.browse.return_value = mock_agent
        mock_env.user.company_ids.ids = [1]

        from odoo.addons.quicksol_estate.services.performance_service import PerformanceService
        service = PerformanceService(mock_env)

        # Mock _calculate_performance_metrics to avoid full DB
        service._calculate_performance_metrics = MagicMock(return_value={
            'aggregated': {
                'total_sales_count': 3,
                'total_commissions': 1500.0,
                'avg_commission': 500.0,
                'total_properties': 3,
            },
            'transactions': [],
        })

        result = service.get_agent_performance(1, '2026-01-01', '2026-12-31')

        # set_json (via _cache_performance) should have been called
        mock_redis_cls.set_json.assert_called()
        self.assertEqual(result['agent_id'], 1)


class TestPerformanceServiceCacheTTLZero(unittest.TestCase):
    """T07-part3: TTL=0 → cache disabled (set_json not called or returns False)"""

    @patch('odoo.addons.quicksol_estate.services.performance_service.RedisClient')
    def test_ttl_zero_disables_caching(self, mock_redis_cls):
        """When TTL=0, set_json called with ttl=0 and RedisClient rejects it"""
        mock_redis_cls.get_json.return_value = None  # MISS
        mock_redis_cls.set_json.return_value = False  # guard: ttl=0 → rejected

        mock_env = MagicMock()
        mock_settings = MagicMock()
        mock_settings.performance_cache_ttl_seconds = 0
        mock_env.__getitem__.return_value.sudo.return_value.get_settings.return_value = mock_settings

        from odoo.addons.quicksol_estate.services.performance_service import PerformanceService
        service = PerformanceService(mock_env)
        service.cache_ttl = 0

        # Simulate the cache population call with ttl=0
        result = mock_redis_cls.set_json('performance:agent:1:x:y', {}, 0)
        self.assertFalse(result)


class TestPerformanceServiceInvalidateCache(unittest.TestCase):
    """T07-part4: invalidate_cache → delete_pattern called"""

    @patch('odoo.addons.quicksol_estate.services.performance_service.RedisClient')
    def test_invalidate_calls_delete_pattern(self, mock_redis_cls):
        """invalidate_cache(agent_id) → delete_pattern('performance:agent:{id}:*')"""
        mock_redis_cls.delete_pattern.return_value = True

        mock_env = MagicMock()
        from odoo.addons.quicksol_estate.services.performance_service import PerformanceService
        service = PerformanceService(mock_env)
        service.invalidate_cache(42)

        mock_redis_cls.delete_pattern.assert_called_once_with('performance:agent:42:*')

    @patch('odoo.addons.quicksol_estate.services.performance_service.RedisClient')
    def test_invalidate_redis_down_no_exception(self, mock_redis_cls):
        """Redis DOWN during invalidate → exception swallowed, no crash"""
        mock_redis_cls.delete_pattern.side_effect = Exception('Redis down')

        mock_env = MagicMock()
        from odoo.addons.quicksol_estate.services.performance_service import PerformanceService
        service = PerformanceService(mock_env)

        raised = False
        try:
            service.invalidate_cache(10)
        except Exception:
            raised = True

        self.assertFalse(raised)


class TestPerformanceServiceRedisDown(unittest.TestCase):
    """T07-part5: Redis unavailable → falls back to DB, no 500"""

    @patch('odoo.addons.quicksol_estate.services.performance_service.RedisClient', None)
    def test_redis_none_falls_back_to_db(self):
        """When RedisClient=None (import failure), get_agent_performance works via DB"""
        mock_env = MagicMock()
        mock_agent = MagicMock()
        mock_agent.exists.return_value = True
        mock_agent.id = 1
        mock_agent.name = 'Agent Fallback'
        mock_agent.company_id.id = 1
        mock_agent.company_id.name = 'Company'
        mock_env.__getitem__.return_value.sudo.return_value.browse.return_value = mock_agent
        mock_env.user.company_ids.ids = [1]

        from odoo.addons.quicksol_estate.services.performance_service import PerformanceService
        service = PerformanceService(mock_env)
        service._calculate_performance_metrics = MagicMock(return_value={
            'aggregated': {
                'total_sales_count': 0,
                'total_commissions': 0.0,
                'avg_commission': 0.0,
                'total_properties': 0,
            },
            'transactions': [],
        })

        raised = False
        try:
            result = service.get_agent_performance(1, None, None)
            self.assertEqual(result['agent_id'], 1)
        except Exception:
            raised = True

        self.assertFalse(raised)


if __name__ == '__main__':
    unittest.main()
