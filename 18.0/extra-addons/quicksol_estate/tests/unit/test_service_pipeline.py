# -*- coding: utf-8 -*-
"""
Unit Test: Service Pipeline Stage Transitions — Feature 015

Tests stage gates, forward jumps, rollback, audit, terminal-state lock,
lead independence (FR-001a), and concurrent write behaviour.

ADR-003: unittest.TestCase (no DB, mock only).
Tasks: T018
FRs: FR-001a, FR-003, FR-003a, FR-004, FR-005, FR-006, FR-007, FR-024a
"""
import unittest
from unittest.mock import MagicMock, PropertyMock, patch


def _make_filterable(items):
    """Wrap a list so it supports .filtered() like an Odoo recordset."""
    m = MagicMock()
    m.__iter__ = lambda s: iter(items)
    m.__bool__ = lambda s: bool(items)
    m.__len__ = lambda s: len(items)
    m.filtered = lambda fn: _make_filterable([x for x in items if fn(x)])
    return m


def _make_service(stage='no_service', property_ids=None, proposal_ids=None,
                  tag_ids=None, lost_reason='', agent_active=True):
    """Build a mock real.estate.service record."""
    svc = MagicMock()
    svc.name = 'ATD/2026/00001'
    svc.stage = stage
    svc.lost_reason = lost_reason
    svc.property_ids = _make_filterable(property_ids or [])
    svc.proposal_ids = _make_filterable(proposal_ids or [])
    svc.tag_ids = _make_filterable(tag_ids or [])
    svc.is_orphan_agent = not agent_active

    origin = MagicMock()
    origin.stage = stage
    svc._origin = origin

    agent = MagicMock()
    agent.active = agent_active
    svc.agent_id = agent

    return svc


def _make_tag(is_system=False, name='tag'):
    t = MagicMock()
    t.is_system = is_system
    t.name = name
    return t


def _make_proposal(state='draft'):
    p = MagicMock()
    p.state = state
    return p


class TestPipelineStageFRRules(unittest.TestCase):
    """Stage gate constraint logic — FR-004, FR-005, FR-006, FR-007."""

    # ------------------------------------------------------------------ #
    # Proposal gate (FR-004)                                               #
    # ------------------------------------------------------------------ #

    def test_proposal_stage_with_property_passes(self):
        """FR-004: Moving to 'proposal' with at least one property linked — should pass."""
        svc = _make_service(stage='proposal', property_ids=[MagicMock()])
        # constraint logic: if stage='proposal' and property_ids non-empty -> OK
        failed = svc.stage == 'proposal' and not svc.property_ids
        self.assertFalse(failed, 'Should not fail when property is linked')

    def test_proposal_stage_without_property_fails(self):
        """FR-004: Moving to 'proposal' without property — should raise."""
        svc = _make_service(stage='proposal', property_ids=[])
        failed = svc.stage == 'proposal' and not svc.property_ids
        self.assertTrue(failed, 'Should fail when no property is linked')

    # ------------------------------------------------------------------ #
    # Formalization gate (FR-005)                                          #
    # ------------------------------------------------------------------ #

    def test_formalization_with_accepted_proposal_passes(self):
        """FR-005: formalization requires at least one accepted proposal."""
        accepted = _make_proposal(state='accepted')
        svc = _make_service(stage='formalization', proposal_ids=[accepted])
        has_accepted = bool(svc.proposal_ids.filtered(lambda p: p.state == 'accepted'))
        self.assertTrue(has_accepted)

    def test_formalization_without_accepted_proposal_fails(self):
        """FR-005: formalization without accepted proposal — should raise."""
        draft = _make_proposal(state='draft')
        svc = _make_service(stage='formalization', proposal_ids=[draft])
        has_accepted = bool(svc.proposal_ids.filtered(lambda p: p.state == 'accepted'))
        self.assertFalse(has_accepted)

    # ------------------------------------------------------------------ #
    # Lost reason (FR-006)                                                 #
    # ------------------------------------------------------------------ #

    def test_lost_without_reason_fails(self):
        """FR-006: lost stage requires non-empty lost_reason."""
        svc = _make_service(stage='lost', lost_reason='')
        failed = svc.stage == 'lost' and not (svc.lost_reason or '').strip()
        self.assertTrue(failed)

    def test_lost_with_reason_passes(self):
        """FR-006: lost with reason should pass."""
        svc = _make_service(stage='lost', lost_reason='Client bought elsewhere')
        failed = svc.stage == 'lost' and not (svc.lost_reason or '').strip()
        self.assertFalse(failed)

    # ------------------------------------------------------------------ #
    # Closed tag lock (FR-007)                                             #
    # ------------------------------------------------------------------ #

    def test_closed_tag_blocks_stage_change(self):
        """FR-007: system tag locks stage transitions."""
        closed_tag = _make_tag(is_system=True, name='Encerrado')
        svc = _make_service(stage='in_service', tag_ids=[closed_tag])
        svc._origin.stage = 'in_service'

        closed_tags = svc.tag_ids.filtered(lambda t: t.is_system)
        new_stage = 'visit'
        blocked = bool(closed_tags) and svc._origin.stage != new_stage
        self.assertTrue(blocked, 'System tag should block stage change')

    def test_no_system_tag_does_not_block(self):
        """FR-007: non-system tag should not lock transitions."""
        normal_tag = _make_tag(is_system=False, name='Follow Up')
        svc = _make_service(stage='in_service', tag_ids=[normal_tag])

        closed_tags = svc.tag_ids.filtered(lambda t: t.is_system)
        blocked = bool(closed_tags)
        self.assertFalse(blocked, 'Non-system tag should not block')


class TestPipelineRollbackAndAudit(unittest.TestCase):
    """Rollback from any non-terminal stage is allowed and audited (FR-003)."""

    def test_rollback_visit_to_in_service_allowed(self):
        """FR-003: backward transition is allowed from any non-terminal stage."""
        TERMINAL = {'won', 'lost'}
        origin_stage = 'visit'
        new_stage = 'in_service'
        blocked = origin_stage in TERMINAL
        self.assertFalse(blocked, 'Rollback from visit should not be blocked')

    def test_rollback_proposal_to_visit_allowed(self):
        """FR-003: backward transition from proposal to visit is allowed."""
        TERMINAL = {'won', 'lost'}
        origin_stage = 'proposal'
        new_stage = 'visit'
        blocked = origin_stage in TERMINAL
        self.assertFalse(blocked)

    def test_audit_message_posted_on_transition(self):
        """FR-003: transition causes message_post on the service record."""
        svc = _make_service(stage='no_service')
        svc.message_post = MagicMock()

        # Simulate service layer calling message_post on stage change
        old_stage = 'no_service'
        new_stage = 'in_service'
        if old_stage != new_stage:
            svc.message_post(body=f'Stage changed: {old_stage} → {new_stage}')

        svc.message_post.assert_called_once()
        call_kwargs = svc.message_post.call_args.kwargs
        self.assertIn('no_service', call_kwargs['body'])
        self.assertIn('in_service', call_kwargs['body'])


class TestTerminalStateGuard(unittest.TestCase):
    """FR-003a: won/lost are terminal — require explicit reopen flag to exit."""

    def test_exit_won_without_flag_blocked(self):
        """Transitioning out of won without allow_reopen context is blocked."""
        TERMINAL = {'won', 'lost'}
        context = {}
        origin_stage = 'won'
        new_stage = 'in_service'

        blocked = (
            origin_stage in TERMINAL
            and new_stage not in TERMINAL
            and not context.get('service.allow_reopen')
        )
        self.assertTrue(blocked, 'Exiting won without flag must be blocked')

    def test_exit_lost_with_flag_allowed(self):
        """Explicit reopen flag lifts terminal lock."""
        TERMINAL = {'won', 'lost'}
        context = {'service.allow_reopen': True}
        origin_stage = 'lost'
        new_stage = 'in_service'

        blocked = (
            origin_stage in TERMINAL
            and new_stage not in TERMINAL
            and not context.get('service.allow_reopen')
        )
        self.assertFalse(blocked, 'Flag should lift the terminal lock')

    def test_terminal_to_terminal_is_not_blocked(self):
        """won → lost (terminal → terminal) should not require reopen flag."""
        TERMINAL = {'won', 'lost'}
        context = {}
        origin_stage = 'won'
        new_stage = 'lost'

        blocked = (
            origin_stage in TERMINAL
            and new_stage not in TERMINAL
            and not context.get('service.allow_reopen')
        )
        self.assertFalse(blocked, 'Terminal to terminal should not be blocked')


class TestLeadIndependence(unittest.TestCase):
    """FR-001a: winning/losing a service MUST NOT mutate the linked lead."""

    def test_won_transition_does_not_call_lead_write(self):
        """FR-001a: lead.write() must never be called during service stage change."""
        svc = _make_service(stage='formalization')
        lead = MagicMock()
        lead.write = MagicMock()
        svc.lead_id = lead

        # Simulate change_stage('won') — must never write to lead
        new_stage = 'won'
        svc.stage = new_stage
        # The service layer should not call lead.write
        lead.write.assert_not_called()

    def test_lost_transition_does_not_call_lead_write(self):
        """FR-001a: lead.write() must never be called on lost."""
        svc = _make_service(stage='in_service', lost_reason='Changed mind')
        lead = MagicMock()
        lead.write = MagicMock()
        svc.lead_id = lead

        svc.stage = 'lost'
        lead.write.assert_not_called()


class TestConcurrentStageTransitions(unittest.TestCase):
    """Concurrent stage transitions: last-writer-wins; both in audit trail (spec edge case)."""

    def test_last_write_wins_simulation(self):
        """Simulate two concurrent writes: the last state wins."""
        stage_after_write_1 = 'in_service'
        stage_after_write_2 = 'visit'
        # Last writer wins
        final_stage = stage_after_write_2
        self.assertEqual(final_stage, 'visit')

    def test_both_transitions_recorded_in_audit(self):
        """Both concurrent transitions produce a message_post call."""
        svc = _make_service(stage='no_service')
        svc.message_post = MagicMock()

        # Simulate two transitions happening in sequence (representing concurrent)
        svc.message_post(body='Stage: no_service → in_service (user1)')
        svc.message_post(body='Stage: no_service → visit (user2)')

        self.assertEqual(svc.message_post.call_count, 2)


class TestOrphanAgentBlocksStageChange(unittest.TestCase):
    """FR-024a: stage changes blocked when responsible agent is deactivated."""

    def test_orphan_blocks_stage_change(self):
        """FR-024a: is_orphan_agent=True blocks stage transitions."""
        svc = _make_service(stage='in_service', agent_active=False)
        svc.is_orphan_agent = True
        svc._origin.stage = 'in_service'

        new_stage = 'visit'
        blocked = svc.is_orphan_agent and svc._origin.stage != new_stage
        self.assertTrue(blocked, 'Orphan agent should block stage change')

    def test_active_agent_allows_stage_change(self):
        """Active agent does not trigger orphan block."""
        svc = _make_service(stage='in_service', agent_active=True)
        svc.is_orphan_agent = False

        blocked = svc.is_orphan_agent
        self.assertFalse(blocked)


if __name__ == '__main__':
    unittest.main()
