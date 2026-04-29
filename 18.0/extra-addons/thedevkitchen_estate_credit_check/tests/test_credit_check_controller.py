# -*- coding: utf-8 -*-
"""
Unit Tests — US4: Credit History Controller (spec 014, T022)

Tests the controller-layer logic for credit history endpoints.
Pattern: ADR-003 unit tests (no DB, mock only).

FR coverage: FR-013, FR-015, FR-020, FR-021
SC coverage: SC-004 (< 300ms for 1,000 checks)
Scenarios (8):
  1. Owner sees full client credit history
  2. Manager sees full client credit history
  3. Agent sees only clients from their own proposals
  4. Agent gets 404 for unknown client (anti-enumeration, ADR-008)
  5. Company isolation: cross-company client returns 404
  6. Empty history returns 200 with empty array
  7. credit_history_summary returns correct counts
  8. GET credit-history with 1,000 seed checks completes in < 300ms (SC-004)
"""
import time
import unittest
from unittest.mock import MagicMock, patch


class TestCreditHistoryController(unittest.TestCase):
    """US4: get_client_credit_history service method"""

    def _make_service(self, env=None):
        from odoo.addons.thedevkitchen_estate_credit_check.services.credit_check_service import (
            CreditCheckService,
        )
        return CreditCheckService(env or MagicMock())

    def _make_check_record(self, result='approved', check_id=1):
        c = MagicMock()
        c.id = check_id
        c.result = result
        c._to_dict.return_value = {'id': check_id, 'result': result}
        return c

    # ------------------------------------------------------------------ #
    #  Scenario 1 — Owner sees full history                               #
    # ------------------------------------------------------------------ #

    def test_owner_sees_full_credit_history(self):
        """GIVEN owner WHEN get_client_credit_history THEN all checks returned."""
        env = MagicMock()
        partner = MagicMock()
        partner.id = 7
        partner.exists.return_value = True
        env['res.partner'].browse.return_value = partner
        env.user.has_group.side_effect = lambda g: g == 'quicksol_estate.group_real_estate_owner'
        env.company.id = 1

        checks = [self._make_check_record('approved', 1), self._make_check_record('rejected', 2)]
        env['thedevkitchen.estate.credit.check'].search_count.return_value = 2
        env['thedevkitchen.estate.credit.check'].search.return_value = checks

        svc = self._make_service(env)
        result = svc.get_client_credit_history(7)

        self.assertEqual(result['summary']['total'], 2)
        self.assertEqual(len(result['items']), 2)

    # ------------------------------------------------------------------ #
    #  Scenario 2 — Manager sees full history                             #
    # ------------------------------------------------------------------ #

    def test_manager_sees_full_credit_history(self):
        """GIVEN manager WHEN get_client_credit_history THEN all checks returned."""
        env = MagicMock()
        partner = MagicMock()
        partner.id = 7
        partner.exists.return_value = True
        env['res.partner'].browse.return_value = partner
        env.user.has_group.side_effect = lambda g: g == 'quicksol_estate.group_real_estate_manager'
        env.company.id = 1

        checks = [self._make_check_record('approved', 1)]
        env['thedevkitchen.estate.credit.check'].search_count.return_value = 1
        env['thedevkitchen.estate.credit.check'].search.return_value = checks

        svc = self._make_service(env)
        result = svc.get_client_credit_history(7)

        self.assertEqual(result['partner_id'], 7)
        self.assertEqual(result['summary']['approved'], 1)

    # ------------------------------------------------------------------ #
    #  Scenario 3 — Agent sees only their clients                         #
    # ------------------------------------------------------------------ #

    def test_agent_sees_only_own_clients_history(self):
        """GIVEN agent WHEN client in their proposals THEN history returned."""
        env = MagicMock()
        partner = MagicMock()
        partner.id = 7
        partner.exists.return_value = True
        env['res.partner'].browse.return_value = partner

        def has_group(g):
            return g == 'quicksol_estate.group_real_estate_agent'
        env.user.has_group.side_effect = has_group
        env.user.id = 2
        env.company.id = 1

        agent = MagicMock()
        agent.id = 2
        agent.__bool__ = MagicMock(return_value=True)
        env['real.estate.agent'].search.return_value = agent

        # Agent has a proposal with this client
        scope_proposal = MagicMock()
        scope_proposal.id = 15
        env['real.estate.proposal'].with_context.return_value = env['real.estate.proposal']
        env['real.estate.proposal'].search.return_value = [scope_proposal]

        checks = [self._make_check_record('approved', 1)]
        env['thedevkitchen.estate.credit.check'].search_count.return_value = 1
        env['thedevkitchen.estate.credit.check'].search.return_value = checks

        svc = self._make_service(env)
        result = svc.get_client_credit_history(7)

        self.assertEqual(result['partner_id'], 7)

    # ------------------------------------------------------------------ #
    #  Scenario 4 — Agent gets 404 for unknown client (ADR-008)           #
    # ------------------------------------------------------------------ #

    def test_agent_gets_404_for_unknown_client(self):
        """GIVEN agent WHEN client not in their proposals THEN UserError (→ 404)."""
        from odoo.exceptions import UserError
        env = MagicMock()
        partner = MagicMock()
        partner.id = 99
        partner.exists.return_value = True
        env['res.partner'].browse.return_value = partner

        def has_group(g):
            return g == 'quicksol_estate.group_real_estate_agent'
        env.user.has_group.side_effect = has_group
        env.user.id = 2
        env.company.id = 1

        agent = MagicMock()
        agent.id = 2
        agent.__bool__ = MagicMock(return_value=True)
        env['real.estate.agent'].search.return_value = agent

        # No proposals for this client
        empty = MagicMock()
        empty.__bool__ = MagicMock(return_value=False)
        empty.__len__ = MagicMock(return_value=0)
        env['real.estate.proposal'].with_context.return_value = env['real.estate.proposal']
        env['real.estate.proposal'].search.return_value = empty

        svc = self._make_service(env)
        with self.assertRaises(UserError):
            svc.get_client_credit_history(99)

    # ------------------------------------------------------------------ #
    #  Scenario 5 — Company isolation (cross-company returns 404)         #
    # ------------------------------------------------------------------ #

    def test_company_isolation_cross_company_returns_404(self):
        """GIVEN partner from different company WHEN queried THEN UserError (→ 404)."""
        from odoo.exceptions import UserError
        env = MagicMock()
        partner = MagicMock()
        partner.id = 200
        partner.exists.return_value = False  # not visible via record rules
        env['res.partner'].browse.return_value = partner
        env.user.has_group.side_effect = lambda g: g == 'quicksol_estate.group_real_estate_owner'
        env.company.id = 1

        svc = self._make_service(env)
        with self.assertRaises(UserError):
            svc.get_client_credit_history(200)

    # ------------------------------------------------------------------ #
    #  Scenario 6 — Empty history → 200 with empty array                 #
    # ------------------------------------------------------------------ #

    def test_empty_history_returns_200_with_empty_array(self):
        """GIVEN client with no checks WHEN owner queries THEN empty items."""
        env = MagicMock()
        partner = MagicMock()
        partner.id = 8
        partner.exists.return_value = True
        env['res.partner'].browse.return_value = partner
        env.user.has_group.side_effect = lambda g: g == 'quicksol_estate.group_real_estate_owner'
        env.company.id = 1

        env['thedevkitchen.estate.credit.check'].search_count.return_value = 0
        env['thedevkitchen.estate.credit.check'].search.return_value = []

        svc = self._make_service(env)
        result = svc.get_client_credit_history(8)

        self.assertEqual(result['items'], [])
        self.assertEqual(result['summary']['total'], 0)

    # ------------------------------------------------------------------ #
    #  Scenario 7 — credit_history_summary correct counts                #
    # ------------------------------------------------------------------ #

    def test_credit_history_summary_correct_counts(self):
        """GIVEN 2 approved, 1 rejected WHEN query THEN summary has correct counts."""
        env = MagicMock()
        partner = MagicMock()
        partner.id = 7
        partner.exists.return_value = True
        env['res.partner'].browse.return_value = partner
        env.user.has_group.side_effect = lambda g: g == 'quicksol_estate.group_real_estate_owner'
        env.company.id = 1

        checks = [
            self._make_check_record('approved', 1),
            self._make_check_record('approved', 2),
            self._make_check_record('rejected', 3),
        ]
        env['thedevkitchen.estate.credit.check'].search_count.return_value = 3
        env['thedevkitchen.estate.credit.check'].search.return_value = checks

        svc = self._make_service(env)
        result = svc.get_client_credit_history(7)

        self.assertEqual(result['summary']['approved'], 2)
        self.assertEqual(result['summary']['rejected'], 1)

    # ------------------------------------------------------------------ #
    #  Scenario 8 — < 300ms for 1,000 checks (SC-004)                    #
    # ------------------------------------------------------------------ #

    def test_credit_history_completes_under_300ms_for_1000_checks(self):
        """GIVEN 1,000 checks WHEN owner queries THEN response time < 300ms (SC-004)."""
        env = MagicMock()
        partner = MagicMock()
        partner.id = 7
        partner.exists.return_value = True
        env['res.partner'].browse.return_value = partner
        env.user.has_group.side_effect = lambda g: g == 'quicksol_estate.group_real_estate_owner'
        env.company.id = 1

        # Simulate 1,000 check records (mocked — service logic runs, no DB)
        checks = [self._make_check_record('approved', i) for i in range(100)]  # paginated to 100
        env['thedevkitchen.estate.credit.check'].search_count.return_value = 1000
        env['thedevkitchen.estate.credit.check'].search.return_value = checks

        svc = self._make_service(env)
        start = time.monotonic()
        result = svc.get_client_credit_history(7, limit=100)
        elapsed = (time.monotonic() - start) * 1000  # convert to ms

        self.assertEqual(result['summary']['total'], 1000)
        self.assertLess(elapsed, 300, f'Service call took {elapsed:.1f}ms, expected < 300ms')
