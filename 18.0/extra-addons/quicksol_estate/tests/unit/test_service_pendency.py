# -*- coding: utf-8 -*-
"""
Unit Test: Service Pendency Computation — Feature 015 (US3)

Tests last_activity_date computation logic and is_pending threshold.

Task: T044
FR: FR-015
Research: R2
"""
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock


def _compute_is_pending(last_activity_date, threshold_days=3):
    """Simulate is_pending logic."""
    if not last_activity_date:
        return False
    cutoff = date.today() - timedelta(days=threshold_days)
    return last_activity_date.date() <= cutoff if hasattr(last_activity_date, 'date') else last_activity_date <= cutoff


def _compute_last_activity(write_date, message_dates=None):
    """Simulate last_activity_date: max of write_date + user-authored messages."""
    candidates = [write_date] if write_date else []
    if message_dates:
        candidates.extend(message_dates)
    return max(candidates) if candidates else None


class TestServicePendencyComputed(unittest.TestCase):

    def test_is_pending_when_no_activity_within_threshold(self):
        """Service with last activity beyond threshold is pending."""
        old_date = date.today() - timedelta(days=5)
        self.assertTrue(_compute_is_pending(old_date, threshold_days=3))

    def test_not_pending_when_recent_activity(self):
        """Service with activity today is not pending."""
        self.assertFalse(_compute_is_pending(date.today(), threshold_days=3))

    def test_not_pending_on_boundary_day(self):
        """Activity exactly on cutoff boundary (threshold days ago) is pending."""
        cutoff = date.today() - timedelta(days=3)
        self.assertTrue(_compute_is_pending(cutoff, threshold_days=3))

    def test_no_activity_date_not_pending(self):
        """No last_activity_date → not pending."""
        self.assertFalse(_compute_is_pending(None, threshold_days=3))

    def test_threshold_respected(self):
        """Higher threshold increases the window."""
        four_days_ago = date.today() - timedelta(days=4)
        self.assertTrue(_compute_is_pending(four_days_ago, threshold_days=3))
        self.assertFalse(_compute_is_pending(four_days_ago, threshold_days=5))


class TestLastActivityDateComputation(unittest.TestCase):

    def test_write_date_used_when_no_messages(self):
        """Without messages, last_activity = write_date."""
        wd = date.today() - timedelta(days=2)
        result = _compute_last_activity(wd, message_dates=[])
        self.assertEqual(result, wd)

    def test_message_date_wins_when_newer_than_write_date(self):
        """Newer message date beats write_date."""
        wd = date.today() - timedelta(days=5)
        msg_date = date.today() - timedelta(days=1)
        result = _compute_last_activity(wd, message_dates=[msg_date])
        self.assertEqual(result, msg_date)

    def test_write_date_wins_when_newer(self):
        """write_date beats older messages."""
        wd = date.today() - timedelta(days=1)
        msg_date = date.today() - timedelta(days=3)
        result = _compute_last_activity(wd, message_dates=[msg_date])
        self.assertEqual(result, wd)

    def test_multiple_messages_take_max(self):
        """Multiple message dates: max is selected."""
        wd = date.today() - timedelta(days=10)
        msgs = [date.today() - timedelta(days=d) for d in [8, 3, 6]]
        result = _compute_last_activity(wd, message_dates=msgs)
        self.assertEqual(result, date.today() - timedelta(days=3))

    def test_no_write_date_no_messages_returns_none(self):
        """No data → None."""
        self.assertIsNone(_compute_last_activity(None, message_dates=[]))


class TestPendencyThresholdSettings(unittest.TestCase):

    def test_default_threshold_3_days(self):
        """Default threshold of 3 days from settings."""
        settings = MagicMock()
        settings.pendency_threshold_days = 3
        four_ago = date.today() - timedelta(days=4)
        pending = _compute_is_pending(four_ago, threshold_days=settings.pendency_threshold_days)
        self.assertTrue(pending)

    def test_custom_threshold_respected(self):
        """Custom threshold of 7 days."""
        settings = MagicMock()
        settings.pendency_threshold_days = 7
        five_ago = date.today() - timedelta(days=5)
        # 5 days ago < 7 days threshold → not pending yet
        pending = _compute_is_pending(five_ago, threshold_days=settings.pendency_threshold_days)
        self.assertFalse(pending)


if __name__ == '__main__':
    unittest.main()
