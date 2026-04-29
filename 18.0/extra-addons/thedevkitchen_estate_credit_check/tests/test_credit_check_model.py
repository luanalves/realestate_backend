# -*- coding: utf-8 -*-
"""
Unit Tests — US1: Agent Initiates Credit Check (spec 014, T008)

Tests the service-layer logic for initiating a credit check.
Pattern: ADR-003 unit tests (no DB, mock only).

FR coverage: FR-001, FR-002, FR-006, FR-010, FR-011 (terminal guard), FR-022
SC coverage: SC-007, SC-008
Scenarios (6):
  1. Initiate on sent lease proposal → succeeds
  2. Initiate on negotiation lease proposal → succeeds
  3. Initiate on sale proposal → raises error (SC-007)
  4. Initiate with existing pending check → raises error (SC-008)
  5. Initiate on terminal proposal → raises error
  6. Agent blocked from another agent's proposal → raises error
"""
import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from odoo.exceptions import UserError


class TestCreditCheckInitiate(unittest.TestCase):
    """US1: initiate_credit_check service method"""

    def _make_service(self, env=None):
        """Build a CreditCheckService with a mocked env."""
        from odoo.addons.thedevkitchen_estate_credit_check.services.credit_check_service import (
            CreditCheckService,
        )
        return CreditCheckService(env or MagicMock())

    def _make_proposal(self, proposal_type='lease', state='sent', agent_user_id=1):
        """Create a minimal mock proposal."""
        proposal = MagicMock()
        proposal.id = 10
        proposal.proposal_code = 'PRP001'
        proposal.proposal_type = proposal_type
        proposal.state = state
        proposal.company_id.id = 1
        proposal.partner_id.id = 5
        proposal.agent_id.id = 1
        proposal.agent_id.user_id.id = agent_user_id
        proposal.exists.return_value = True
        proposal.message_post = MagicMock()
        return proposal

    # ------------------------------------------------------------------ #
    #  Scenario 1 — sent lease → success                                  #
    # ------------------------------------------------------------------ #

    def test_initiate_on_sent_lease_succeeds(self):
        """GIVEN sent lease proposal WHEN initiate THEN check created, state updated."""
        env = MagicMock()
        svc = self._make_service(env)

        proposal = self._make_proposal(proposal_type='lease', state='sent')

        # browse returns the proposal, search returns empty (no existing pending)
        env['real.estate.proposal'].browse.return_value = proposal
        env['thedevkitchen.estate.credit.check'].search.return_value = []

        mock_check = MagicMock()
        mock_check.id = 42
        env['thedevkitchen.estate.credit.check'].create.return_value = mock_check

        # Owner group → unrestricted
        env.user.has_group.side_effect = lambda g: g == 'quicksol_estate.group_real_estate_owner'

        result = svc.initiate_credit_check(10, 'Tokio Marine')

        # Check created with correct fields
        create_call = env['thedevkitchen.estate.credit.check'].create.call_args[0][0]
        self.assertEqual(create_call['proposal_id'], 10)
        self.assertEqual(create_call['insurer_name'], 'Tokio Marine')
        self.assertEqual(create_call['result'], 'pending')

        # Proposal state updated
        proposal.write.assert_called_once_with({'state': 'credit_check_pending'})
        # Timeline message posted
        proposal.message_post.assert_called_once()
        self.assertEqual(result, mock_check)

    # ------------------------------------------------------------------ #
    #  Scenario 2 — negotiation lease → success                           #
    # ------------------------------------------------------------------ #

    def test_initiate_on_negotiation_lease_succeeds(self):
        """GIVEN negotiation lease proposal WHEN initiate THEN succeeds."""
        env = MagicMock()
        svc = self._make_service(env)

        proposal = self._make_proposal(proposal_type='lease', state='negotiation')
        env['real.estate.proposal'].browse.return_value = proposal
        env['thedevkitchen.estate.credit.check'].search.return_value = []
        env['thedevkitchen.estate.credit.check'].create.return_value = MagicMock()
        env.user.has_group.side_effect = lambda g: g == 'quicksol_estate.group_real_estate_owner'

        # Should not raise
        svc.initiate_credit_check(10, 'Porto Seguro')

        create_call = env['thedevkitchen.estate.credit.check'].create.call_args[0][0]
        self.assertEqual(create_call['result'], 'pending')
        proposal.write.assert_called_once_with({'state': 'credit_check_pending'})

    # ------------------------------------------------------------------ #
    #  Scenario 3 — sale proposal → raises error (FR-006, SC-007)         #
    # ------------------------------------------------------------------ #

    def test_initiate_on_sale_proposal_raises(self):
        """GIVEN sale proposal WHEN initiate THEN UserError raised."""
        env = MagicMock()
        svc = self._make_service(env)

        proposal = self._make_proposal(proposal_type='sale', state='sent')
        env['real.estate.proposal'].browse.return_value = proposal
        env.user.has_group.side_effect = lambda g: g == 'quicksol_estate.group_real_estate_owner'

        with self.assertRaises(UserError) as ctx:
            svc.initiate_credit_check(10, 'Tokio Marine')

        self.assertIn('lease', str(ctx.exception).lower())
        # No check created, no state written
        env['thedevkitchen.estate.credit.check'].create.assert_not_called()
        proposal.write.assert_not_called()

    # ------------------------------------------------------------------ #
    #  Scenario 4 — existing pending check → raises error (FR-010, SC-008)
    # ------------------------------------------------------------------ #

    def test_initiate_with_existing_pending_check_raises(self):
        """GIVEN pending check exists WHEN initiate THEN UserError (conflict)."""
        env = MagicMock()
        svc = self._make_service(env)

        proposal = self._make_proposal(proposal_type='lease', state='credit_check_pending')
        env['real.estate.proposal'].browse.return_value = proposal
        env.user.has_group.side_effect = lambda g: g == 'quicksol_estate.group_real_estate_owner'

        # Proposal state is not sent/negotiation — guard fires before the search
        with self.assertRaises(UserError) as ctx:
            svc.initiate_credit_check(10, 'Tokio Marine')

        # Could also be triggered by existing pending check found in search
        # either way no check is created
        env['thedevkitchen.estate.credit.check'].create.assert_not_called()

    def test_initiate_when_search_returns_pending_check_raises(self):
        """GIVEN search returns existing pending check WHEN initiate THEN conflict."""
        env = MagicMock()
        svc = self._make_service(env)

        proposal = self._make_proposal(proposal_type='lease', state='sent')
        env['real.estate.proposal'].browse.return_value = proposal
        env.user.has_group.side_effect = lambda g: g == 'quicksol_estate.group_real_estate_owner'

        existing_check = MagicMock()
        existing_check.__bool__ = MagicMock(return_value=True)
        existing_check.__len__ = MagicMock(return_value=1)
        env['thedevkitchen.estate.credit.check'].search.return_value = existing_check

        with self.assertRaises(UserError) as ctx:
            svc.initiate_credit_check(10, 'Tokio Marine')

        self.assertIn('already pending', str(ctx.exception).lower())
        env['thedevkitchen.estate.credit.check'].create.assert_not_called()

    # ------------------------------------------------------------------ #
    #  Scenario 5 — terminal proposal → raises error                      #
    # ------------------------------------------------------------------ #

    def test_initiate_on_terminal_proposal_raises(self):
        """GIVEN accepted/rejected/expired/cancelled proposal WHEN initiate THEN error."""
        env = MagicMock()
        svc = self._make_service(env)
        env.user.has_group.side_effect = lambda g: g == 'quicksol_estate.group_real_estate_owner'

        for terminal_state in ('accepted', 'rejected', 'expired', 'cancelled'):
            with self.subTest(state=terminal_state):
                proposal = self._make_proposal(proposal_type='lease', state=terminal_state)
                env['real.estate.proposal'].browse.return_value = proposal

                with self.assertRaises(UserError):
                    svc.initiate_credit_check(10, 'Tokio Marine')

                env['thedevkitchen.estate.credit.check'].create.reset_mock()
                proposal.write.reset_mock()

    # ------------------------------------------------------------------ #
    #  Scenario 6 — agent blocked from another agent's proposal           #
    # ------------------------------------------------------------------ #

    def test_agent_blocked_from_other_agents_proposal(self):
        """GIVEN agent WHEN proposal.agent_id != current agent THEN UserError."""
        env = MagicMock()
        svc = self._make_service(env)

        proposal = self._make_proposal(proposal_type='lease', state='sent')
        proposal.agent_id.id = 99  # different agent
        env['real.estate.proposal'].browse.return_value = proposal

        # Current user is an Agent (not owner, not manager)
        def has_group(g):
            return g == 'quicksol_estate.group_real_estate_agent'
        env.user.has_group.side_effect = has_group
        env.user.id = 1

        # Agent record does NOT match the proposal agent
        mock_agent = MagicMock()
        mock_agent.id = 1  # current agent id
        mock_agent.__bool__ = MagicMock(return_value=True)
        env['real.estate.agent'].search.return_value = mock_agent

        with self.assertRaises(UserError) as ctx:
            svc.initiate_credit_check(10, 'Tokio Marine')

        self.assertIn('access denied', str(ctx.exception).lower())
        env['thedevkitchen.estate.credit.check'].create.assert_not_called()
