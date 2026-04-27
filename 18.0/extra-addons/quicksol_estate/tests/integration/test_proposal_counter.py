# -*- coding: utf-8 -*-
"""
Unit tests — Counter-proposal chain (T037-T042)
Covers: US4 — action_counter(), parent/child linkage, negotiation state
"""
from odoo.tests import tagged
from odoo.exceptions import ValidationError, UserError

from .base_proposal_test import BaseProposalTest


@tagged('post_install', '-at_install', 'proposal', 'proposal_counter')
class TestProposalCounter(BaseProposalTest):

    def test_counter_creates_child_in_negotiation(self):
        """FR-018: counter-proposal creates a child linked to parent."""
        p1 = self._create_proposal()
        p1.action_send()
        counter = p1.action_counter({'proposal_value': 320_000})
        self.assertEqual(p1.state, 'negotiation')
        self.assertEqual(counter.state, 'draft')  # child takes active slot as draft
        self.assertEqual(counter.parent_proposal_id, p1)

    def test_counter_value_differs_from_parent(self):
        """FR-019: counter_value must differ from parent value."""
        p1 = self._create_proposal(proposal_value=350_000)
        p1.action_send()
        with self.assertRaises(UserError):
            p1.action_counter({'proposal_value': 350_000})

    def test_counter_chain_get_proposal_chain(self):
        """FR-020: get_proposal_chain() returns full ancestry."""
        p1 = self._create_proposal()
        p1.action_send()
        p2 = p1.action_counter({'proposal_value': 320_000})
        p2.action_send()  # send p2 before creating p3 counter
        p3 = p2.action_counter({'proposal_value': 330_000})
        chain = p3.get_proposal_chain()
        ids = [p.id for p in chain]
        self.assertIn(p1.id, ids)
        self.assertIn(p2.id, ids)
        self.assertIn(p3.id, ids)

    def test_counter_from_non_sent_raises(self):
        """FSM guard: cannot counter a draft proposal."""
        p1 = self._create_proposal()
        with self.assertRaises(UserError):
            p1.action_counter({'proposal_value': 300_000})

    def test_counter_from_terminal_raises(self):
        """FSM guard: cannot counter a cancelled proposal."""
        p1 = self._create_proposal()
        p1.action_send()
        p1.action_cancel('changed mind')
        with self.assertRaises(UserError):
            p1.action_counter({'proposal_value': 300_000})
