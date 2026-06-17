# -*- coding: utf-8 -*-
"""
Unit Tests — Profile.write() session invalidation on profile_type_id change (US2)
Tests run with mocked env — no database required.
"""

import unittest
import odoo.models
from unittest.mock import patch, MagicMock


# =============================================================================
# T06 — Profile.write() session deactivation on type change (US2)
# =============================================================================

class TestProfileWriteInvalidation(unittest.TestCase):
    """T06: Profile.write() deactivates active sessions when profile_type_id changes"""

    def _make_recordset(self, partner_id=10, profile_id=42):
        """
        Return a mock recordset whose __class__ is Profile so that
        super(Profile, self) inside write() passes the isinstance check.
        """
        from odoo.addons.quicksol_estate.models.profile import Profile
        mock_record = MagicMock()
        mock_record.id = profile_id
        mock_record.partner_id = MagicMock()
        mock_record.partner_id.id = partner_id
        mock_self = MagicMock()
        mock_self.__class__ = Profile
        mock_self.__iter__ = MagicMock(return_value=iter([mock_record]))
        return mock_self, mock_record

    def _setup_env(self, mock_self, mock_user_id=5):
        """Wire mock_self.env to return proper model mocks."""
        mock_user = MagicMock()
        mock_user.id = mock_user_id

        mock_sessions = MagicMock()  # truthy by default

        users_model = MagicMock()
        users_model.sudo.return_value.search.return_value = [mock_user]

        sessions_model = MagicMock()
        sessions_model.sudo.return_value.search.return_value = mock_sessions

        # side_effect (not direct assignment) is required for magic methods on MagicMock
        mock_self.env.__getitem__.side_effect = lambda key: {
            'res.users': users_model,
            'thedevkitchen.api.session': sessions_model,
        }.get(key, MagicMock())

        return mock_sessions

    def test_write_profile_type_change_deactivates_sessions(self):
        """write({'profile_type_id': X}) → finds user → active sessions set is_active=False"""
        from odoo.addons.quicksol_estate.models.profile import Profile

        mock_self, _ = self._make_recordset()
        mock_sessions = self._setup_env(mock_self)

        with patch.object(odoo.models.Model, 'write', return_value=True):
            Profile.write(mock_self, {'profile_type_id': 3})

        mock_sessions.write.assert_called_once_with({'is_active': False})

    def test_write_name_change_does_not_deactivate_sessions(self):
        """write({'name': 'New Name'}) → session deactivation NOT triggered"""
        from odoo.addons.quicksol_estate.models.profile import Profile

        mock_self, _ = self._make_recordset()
        mock_sessions = self._setup_env(mock_self)

        with patch.object(odoo.models.Model, 'write', return_value=True):
            Profile.write(mock_self, {'name': 'New Agent Name'})

        mock_sessions.write.assert_not_called()

    def test_write_no_partner_id_skips_deactivation(self):
        """Profile without partner_id → session deactivation skipped (no partner bridge)"""
        from odoo.addons.quicksol_estate.models.profile import Profile

        mock_record = MagicMock()
        mock_record.id = 99
        mock_record.partner_id = False  # no partner

        mock_self = MagicMock()
        mock_self.__class__ = Profile
        mock_self.__iter__ = MagicMock(return_value=iter([mock_record]))

        users_model = MagicMock()
        sessions_model = MagicMock()

        mock_self.env.__getitem__.side_effect = lambda key: {
                'res.users': users_model,
                'thedevkitchen.api.session': sessions_model,
            }.get(key, MagicMock())

        with patch.object(odoo.models.Model, 'write', return_value=True):
            Profile.write(mock_self, {'profile_type_id': 5})

        sessions_model.sudo.return_value.search.assert_not_called()

    def test_write_redis_down_no_exception(self):
        """Exception during session deactivation is swallowed — write still completes"""
        from odoo.addons.quicksol_estate.models.profile import Profile

        mock_self, _ = self._make_recordset()

        # Force exception in env lookup
        mock_self.env.__getitem__.side_effect = Exception('env error')

        with patch.object(odoo.models.Model, 'write', return_value=True):
            try:
                result = Profile.write(mock_self, {'profile_type_id': 5})
            except Exception as e:
                self.fail('Profile.write() raised an unexpected exception: {}'.format(e))

        self.assertTrue(result)

    def test_write_multi_record_deactivates_sessions_for_each(self):
        """For multi-record recordset, sessions deactivated for each profile's user"""
        from odoo.addons.quicksol_estate.models.profile import Profile

        records = []
        for i in range(3):
            r = MagicMock()
            r.id = 10 + i
            r.partner_id = MagicMock()
            r.partner_id.id = 100 + i
            records.append(r)

        mock_self = MagicMock()
        mock_self.__class__ = Profile
        mock_self.__iter__ = MagicMock(return_value=iter(records))

        sessions_per_record = []
        call_count = [0]

        def env_getitem(key):
            if key == 'res.users':
                m = MagicMock()
                m.sudo.return_value.search.return_value = [MagicMock()]
                return m
            elif key == 'thedevkitchen.api.session':
                sess = MagicMock()
                sessions_per_record.append(sess.sudo.return_value.search.return_value)
                return sess
            return MagicMock()

        mock_self.env.__getitem__.side_effect = env_getitem

        with patch.object(odoo.models.Model, 'write', return_value=True):
            Profile.write(mock_self, {'profile_type_id': 2})

        # write({'is_active': False}) should be called once per record
        total_writes = sum(
            1 for s in sessions_per_record if s.write.called
        )
        self.assertEqual(total_writes, 3)


if __name__ == '__main__':
    unittest.main()
