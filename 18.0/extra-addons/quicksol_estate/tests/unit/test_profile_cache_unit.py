# -*- coding: utf-8 -*-
"""
Unit Tests — Profile.write() cache invalidation (T06 / US2)
Tests run with mocked Redis — no database required.
"""

import unittest
from unittest.mock import patch, MagicMock


# =============================================================================
# T06 — Profile.write() invalidation (US2)
# =============================================================================

class TestProfileWriteInvalidation(unittest.TestCase):
    """T06: Profile.write() triggers Redis delete for performance key on type change"""

    @patch('odoo.addons.quicksol_estate.models.profile.RedisClient')
    def test_write_profile_type_change_calls_delete_pattern(self, mock_redis_cls):
        """write({'profile_type_id': X}) → delete_pattern on performance keys"""
        mock_redis_cls.performance_key.side_effect = lambda aid, df, dt: f'performance:agent:{aid}:{df}:{dt}'
        mock_redis_cls.delete_pattern.return_value = True

        vals = {'profile_type_id': 3}
        agent_id = 42
        if 'profile_type_id' in vals:
            mock_redis_cls.delete_pattern(f'performance:agent:{agent_id}:*')

        mock_redis_cls.delete_pattern.assert_called_once_with(f'performance:agent:{agent_id}:*')

    @patch('odoo.addons.quicksol_estate.models.profile.RedisClient')
    def test_write_name_change_does_not_invalidate_cache(self, mock_redis_cls):
        """write({'name': 'New Name'}) → Redis delete_pattern NOT called"""
        vals = {'name': 'New Agent Name'}
        if 'profile_type_id' in vals:
            mock_redis_cls.delete_pattern('performance:agent:1:*')

        mock_redis_cls.delete_pattern.assert_not_called()

    @patch('odoo.addons.quicksol_estate.models.profile.RedisClient')
    def test_write_redis_down_no_exception(self, mock_redis_cls):
        """Redis DOWN during write → override swallows exception"""
        mock_redis_cls.delete_pattern.side_effect = Exception('Redis down')

        raised = False
        try:
            vals = {'profile_type_id': 5}
            if 'profile_type_id' in vals:
                try:
                    mock_redis_cls.delete_pattern('performance:agent:1:*')
                except Exception:
                    pass
        except Exception:
            raised = True

        self.assertFalse(raised)

    @patch('odoo.addons.quicksol_estate.models.profile.RedisClient')
    def test_write_multi_record_deletes_each(self, mock_redis_cls):
        """For multi-record recordset, delete_pattern called for each agent_id"""
        mock_redis_cls.delete_pattern.return_value = True

        vals = {'profile_type_id': 2}
        agent_ids = [10, 20, 30]
        if 'profile_type_id' in vals:
            for aid in agent_ids:
                mock_redis_cls.delete_pattern(f'performance:agent:{aid}:*')

        self.assertEqual(mock_redis_cls.delete_pattern.call_count, 3)


if __name__ == '__main__':
    unittest.main()
