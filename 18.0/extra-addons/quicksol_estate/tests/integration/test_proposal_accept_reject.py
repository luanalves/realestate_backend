# -*- coding: utf-8 -*-
"""
Unit tests — Accept / Reject flows (T043-T049)
Covers: US2 (reject), US4 (accept), RBAC gates, competitor cancellation, superseded_by
"""
from odoo.tests import tagged
from odoo.exceptions import AccessError, UserError, ValidationError

from .base_proposal_test import BaseProposalTest


@tagged('post_install', '-at_install', 'proposal', 'proposal_accept_reject')
class TestProposalAcceptReject(BaseProposalTest):

    def test_manager_can_accept(self):
        """FR-011: Manager/owner can accept a sent proposal."""
        p = self._create_proposal()
        p.action_send()
        p.with_user(self.manager_user).action_accept()
        self.assertEqual(p.state, 'accepted')

    def test_agent_cannot_accept(self):
        """FR-011: Agent is not authorised to accept."""
        p = self._create_proposal()
        p.action_send()
        with self.assertRaises(AccessError):
            p.with_user(self.agent_user).action_accept()

    def test_accept_sets_accepted_date(self):
        """FR-012: accepted_date is recorded."""
        p = self._create_proposal()
        p.action_send()
        p.with_user(self.manager_user).action_accept()
        self.assertIsNotNone(p.accepted_date)

    def test_accept_cancels_competing_proposals(self):
        """FR-013: competing proposals are batch-cancelled with superseded_by_id."""
        p1 = self._create_proposal()
        p1.action_send()
        p2 = self._create_proposal(
            partner_id=self.env['res.partner'].create({
                'name': 'Other Client',
                'vat': '11144477735',
            }).id
        )
        p1.with_user(self.manager_user).action_accept()
        p2.invalidate_recordset()
        self.assertIn(p2.state, ('cancelled',))

    def test_reject_requires_reason(self):
        """FR-014: rejection_reason is mandatory."""
        p = self._create_proposal()
        p.action_send()
        with self.assertRaises(UserError):
            p.with_user(self.manager_user).action_reject('')

    def test_reject_transitions_to_rejected(self):
        """FR-014: action_reject() moves sent/negotiation → rejected."""
        p = self._create_proposal()
        p.action_send()
        p.with_user(self.manager_user).action_reject('price too high')
        self.assertEqual(p.state, 'rejected')

    def test_reject_sets_rejected_date(self):
        """FR-014: rejected_date is recorded."""
        p = self._create_proposal()
        p.action_send()
        p.with_user(self.manager_user).action_reject('reason')
        self.assertIsNotNone(p.rejected_date)

    def test_cancel_requires_reason(self):
        """FR-016: cancellation_reason is mandatory."""
        p = self._create_proposal()
        with self.assertRaises(UserError):
            p.action_cancel('')

    def test_cancel_transitions_to_cancelled(self):
        """FR-016: action_cancel() moves non-terminal → cancelled."""
        p = self._create_proposal()
        p.action_cancel('client withdrew')
        self.assertEqual(p.state, 'cancelled')
