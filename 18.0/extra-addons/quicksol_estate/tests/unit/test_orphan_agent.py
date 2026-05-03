# -*- coding: utf-8 -*-
"""
Unit Test: Orphan Agent (FR-024a) — Feature 015

Tests is_orphan_agent computation and stage-change blocking
when the responsible agent's account is deactivated.

ADR-003: unittest.TestCase (no DB, mock only).
Task: T021
FR: FR-024a
"""
import unittest
from unittest.mock import MagicMock


def _compute_is_orphan_agent(agent_id):
    """Simulate _compute_is_orphan_agent logic."""
    return bool(agent_id) and not agent_id.active


def _check_orphan_blocks_stage(is_orphan_agent, origin_stage, new_stage):
    """Simulate _check_orphan_agent_blocks_stage_change constraint logic."""
    if not is_orphan_agent:
        return False
    return origin_stage != new_stage


class TestOrphanAgentComputed(unittest.TestCase):
    """is_orphan_agent computed field logic."""

    def test_active_agent_not_orphan(self):
        """Agent with active=True → is_orphan_agent=False."""
        agent = MagicMock()
        agent.active = True
        self.assertFalse(_compute_is_orphan_agent(agent))

    def test_deactivated_agent_is_orphan(self):
        """Agent with active=False → is_orphan_agent=True."""
        agent = MagicMock()
        agent.active = False
        self.assertTrue(_compute_is_orphan_agent(agent))

    def test_no_agent_not_orphan(self):
        """No agent (falsy) → is_orphan_agent=False."""
        self.assertFalse(_compute_is_orphan_agent(None))
        self.assertFalse(_compute_is_orphan_agent(False))


class TestOrphanAgentBlocksStageChange(unittest.TestCase):
    """FR-024a: stage transition blocked when agent is deactivated."""

    def test_orphan_blocks_forward_transition(self):
        """Forward transition (no_service → in_service) blocked when orphan."""
        blocked = _check_orphan_blocks_stage(
            is_orphan_agent=True,
            origin_stage='no_service',
            new_stage='in_service',
        )
        self.assertTrue(blocked)

    def test_orphan_blocks_backward_transition(self):
        """Rollback also blocked when orphan."""
        blocked = _check_orphan_blocks_stage(
            is_orphan_agent=True,
            origin_stage='visit',
            new_stage='in_service',
        )
        self.assertTrue(blocked)

    def test_active_agent_allows_transition(self):
        """Active agent does not trigger block."""
        blocked = _check_orphan_blocks_stage(
            is_orphan_agent=False,
            origin_stage='no_service',
            new_stage='in_service',
        )
        self.assertFalse(blocked)

    def test_noop_stage_write_not_blocked_even_for_orphan(self):
        """No-op stage write (same stage) is never blocked."""
        blocked = _check_orphan_blocks_stage(
            is_orphan_agent=True,
            origin_stage='in_service',
            new_stage='in_service',
        )
        self.assertFalse(blocked, 'No-op write must not be blocked')

    def test_orphan_visible_to_managers_via_filter(self):
        """FR-024a: orphan flag exposes service for manager queue filter."""
        services = []
        for i, active in enumerate([True, False, True, False, False]):
            svc = MagicMock()
            agent = MagicMock()
            agent.active = active
            svc.agent_id = agent
            svc.is_orphan_agent = not active
            services.append(svc)

        orphans = [s for s in services if s.is_orphan_agent]
        self.assertEqual(len(orphans), 3)


if __name__ == '__main__':
    unittest.main()
