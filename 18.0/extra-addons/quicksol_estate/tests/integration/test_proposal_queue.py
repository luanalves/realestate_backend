# -*- coding: utf-8 -*-
"""
Unit tests — Queue management (T031-T036)
Covers: US3 — slot invariant, FIFO promotion, queue_position computation
"""
from odoo.tests import tagged
from odoo.exceptions import ValidationError

from .base_proposal_test import BaseProposalTest


@tagged('post_install', '-at_install', 'proposal', 'proposal_queue')
class TestProposalQueue(BaseProposalTest):

    def _client(self, n):
        """Create a distinct client partner."""
        return self.env['res.partner'].create({
            'name': f'Cliente Queue {n}',
            'vat': ['52998224725', '11144477735', '71428793860'][n % 3],
        })

    def test_first_proposal_is_draft_not_queued(self):
        """FR-009 invariant: only one root proposal may be draft/sent/accepted."""
        p1 = self._create_proposal()
        self.assertEqual(p1.state, 'draft')

    def test_second_proposal_goes_to_queued(self):
        """FR-009: second proposal queued while first is active."""
        p1 = self._create_proposal()
        p1.action_send()
        p2 = self._create_proposal(partner_id=self._client(1).id)
        self.assertEqual(p2.state, 'queued')

    def test_queue_position_increments(self):
        """Queue position: p2=0, p3=1 (0-indexed position in queue)."""
        p1 = self._create_proposal()
        p1.action_send()
        p2 = self._create_proposal(partner_id=self._client(1).id)
        p3 = self._create_proposal(partner_id=self._client(2).id)
        self.assertEqual(p2.queue_position, 0)
        self.assertEqual(p3.queue_position, 1)

    def test_accept_cancels_competitors_and_promotes(self):
        """US3/FR-013: accepting p1 should cancel all queued siblings."""
        p1 = self._create_proposal()
        p1.action_send()
        p2 = self._create_proposal(partner_id=self._client(1).id)

        # Only manager/owner can accept — use manager env
        p1.with_user(self.manager_user).action_accept()

        self.assertEqual(p1.state, 'accepted')
        # p2 should be cancelled (superseded) since p1 was accepted
        self.assertIn(p2.state, ('cancelled',))

    def test_cancel_active_promotes_first_queued(self):
        """FR-015: when active proposal is cancelled, oldest queued → draft."""
        p1 = self._create_proposal()
        p1.action_send()
        p2 = self._create_proposal(partner_id=self._client(1).id)
        p3 = self._create_proposal(partner_id=self._client(2).id)

        p1.action_cancel('withdrawn')
        p2.invalidate_recordset()
        self.assertEqual(p2.state, 'draft')  # promoted
        self.assertEqual(p3.queue_position, 0)  # p3 now first in queue

    def test_reject_active_promotes_first_queued(self):
        """FR-015: rejected active proposal promotes oldest queued."""
        p1 = self._create_proposal()
        p1.action_send()
        p2 = self._create_proposal(partner_id=self._client(1).id)

        p1.with_user(self.manager_user).action_reject('price too low')
        p2.invalidate_recordset()
        self.assertEqual(p2.state, 'draft')
