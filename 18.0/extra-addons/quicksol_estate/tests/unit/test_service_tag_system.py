# -*- coding: utf-8 -*-
"""
Unit Test: Service Tag System Flag — Feature 015

Tests is_system immutability logic and closed-tag pipeline lock behaviour.

ADR-003: unittest.TestCase (no DB, mock only).
Task: T020
FRs: FR-007, FR-018
"""
import unittest
from unittest.mock import MagicMock


def _make_tag(name='tag', is_system=False, active=True, color='#3498db'):
    tag = MagicMock()
    tag.name = name
    tag.is_system = is_system
    tag.active = active
    tag.color = color
    origin = MagicMock()
    origin.name = name
    origin.is_system = is_system
    origin.active = active
    origin.color = color
    origin.id = 1
    tag._origin = origin
    return tag


def _check_system_tag_immutable(tag, new_vals, admin_context=False):
    """Simulate _check_system_tag_immutable constraint logic."""
    if not tag.is_system:
        return False  # Not a system tag — always OK
    if admin_context:
        return False  # Admin bypass
    if not tag._origin or not tag._origin.id:
        return False  # Creation — allowed

    changed = {
        f for f in ('name', 'active', 'is_system', 'color')
        if new_vals.get(f) is not None and new_vals[f] != getattr(tag._origin, f)
    }
    return bool(changed)


def _has_system_tags(tag_ids):
    """Returns list of system tags among tag_ids."""
    return [t for t in tag_ids if t.is_system]


class TestSystemTagImmutability(unittest.TestCase):
    """FR-018: system tags cannot be modified by regular users."""

    def test_system_tag_name_change_blocked(self):
        """Changing name of a system tag without admin context raises."""
        tag = _make_tag(name='Encerrado', is_system=True)
        would_raise = _check_system_tag_immutable(tag, {'name': 'Closed'}, admin_context=False)
        self.assertTrue(would_raise, 'Name change on system tag must be blocked')

    def test_system_tag_deactivation_blocked(self):
        """Deactivating a system tag without admin context raises."""
        tag = _make_tag(name='Encerrado', is_system=True, active=True)
        would_raise = _check_system_tag_immutable(tag, {'active': False}, admin_context=False)
        self.assertTrue(would_raise, 'Deactivating system tag must be blocked')

    def test_system_tag_color_change_blocked(self):
        """Changing color of a system tag without admin context raises."""
        tag = _make_tag(name='Encerrado', is_system=True, color='#7f8c8d')
        would_raise = _check_system_tag_immutable(tag, {'color': '#ff0000'}, admin_context=False)
        self.assertTrue(would_raise, 'Color change on system tag must be blocked')

    def test_system_tag_admin_context_bypasses_lock(self):
        """Admin context flag service.tag_admin allows changes to system tags."""
        tag = _make_tag(name='Encerrado', is_system=True)
        would_raise = _check_system_tag_immutable(tag, {'name': 'Closed'}, admin_context=True)
        self.assertFalse(would_raise, 'Admin context should bypass the lock')

    def test_non_system_tag_always_editable(self):
        """Non-system tags are freely editable."""
        tag = _make_tag(name='Follow Up', is_system=False)
        would_raise = _check_system_tag_immutable(
            tag, {'name': 'Follow Up 2', 'color': '#ff0000'}, admin_context=False
        )
        self.assertFalse(would_raise, 'Non-system tag should always be editable')

    def test_new_system_tag_creation_allowed(self):
        """Creating a new system tag (no _origin.id) is allowed (post_init hook)."""
        tag = _make_tag(is_system=True)
        tag._origin.id = None  # No existing DB record
        would_raise = _check_system_tag_immutable(
            tag, {'name': 'Encerrado'}, admin_context=False
        )
        self.assertFalse(would_raise, 'New system tag creation must be allowed')


class TestClosedTagLocksPipeline(unittest.TestCase):
    """FR-007: service with system tag 'Encerrado' blocks stage changes."""

    def test_system_tag_blocks_stage_transition(self):
        """FR-007: stage change blocked when service has any is_system=True tag."""
        closed_tag = _make_tag(name='Encerrado', is_system=True)
        tag_ids = [closed_tag]
        origin_stage = 'in_service'
        new_stage = 'visit'

        system_tags = _has_system_tags(tag_ids)
        blocked = bool(system_tags) and origin_stage != new_stage
        self.assertTrue(blocked, 'System tag must block stage transition')

    def test_no_system_tag_does_not_block(self):
        """FR-007: service without system tags can change stage freely."""
        normal_tag = _make_tag(name='Follow Up', is_system=False)
        tag_ids = [normal_tag]
        origin_stage = 'in_service'
        new_stage = 'visit'

        system_tags = _has_system_tags(tag_ids)
        blocked = bool(system_tags) and origin_stage != new_stage
        self.assertFalse(blocked, 'Normal tag must not block stage transition')

    def test_same_stage_no_block_even_with_system_tag(self):
        """FR-007: no-op stage write (same stage) is not blocked."""
        closed_tag = _make_tag(name='Encerrado', is_system=True)
        tag_ids = [closed_tag]
        origin_stage = 'in_service'
        new_stage = 'in_service'  # No change

        system_tags = _has_system_tags(tag_ids)
        blocked = bool(system_tags) and origin_stage != new_stage
        self.assertFalse(blocked, 'No-op stage write must never be blocked')

    def test_mixed_tags_blocked_if_any_system(self):
        """FR-007: if one of multiple tags is_system, still blocked."""
        normal_tag = _make_tag(name='Follow Up', is_system=False)
        closed_tag = _make_tag(name='Encerrado', is_system=True)
        tag_ids = [normal_tag, closed_tag]

        system_tags = _has_system_tags(tag_ids)
        blocked = bool(system_tags)
        self.assertTrue(blocked)


if __name__ == '__main__':
    unittest.main()
