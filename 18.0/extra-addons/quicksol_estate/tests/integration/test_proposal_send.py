# -*- coding: utf-8 -*-
"""
Unit tests — Proposal send action (T020)
Covers: US1/FR-007 (draft→sent), FR-008 (default validity), FR-038 (email notification)
"""
from datetime import date, timedelta
from odoo.tests import tagged
from odoo.exceptions import UserError, ValidationError

from .base_proposal_test import BaseProposalTest


@tagged('post_install', '-at_install', 'proposal', 'proposal_send')
class TestProposalSend(BaseProposalTest):

    def test_send_transitions_to_sent(self):
        """FR-007: action_send() moves draft → sent."""
        proposal = self._create_proposal()
        proposal.action_send()
        self.assertEqual(proposal.state, 'sent')

    def test_send_sets_sent_date(self):
        """FR-007: sent_date is recorded on send."""
        proposal = self._create_proposal()
        proposal.action_send()
        self.assertIsNotNone(proposal.sent_date)

    def test_send_sets_default_validity(self):
        """FR-008: If valid_until not set, default is today+7d."""
        proposal = self._create_proposal()
        proposal.action_send()
        expected = date.today() + timedelta(days=7)
        self.assertEqual(proposal.valid_until, expected)

    def test_send_preserves_explicit_validity(self):
        """FR-008: If valid_until already set, it is kept."""
        valid = self._valid_until(days=30)
        proposal = self._create_proposal(valid_until=valid)
        proposal.action_send()
        self.assertEqual(proposal.valid_until, valid)

    def test_send_from_wrong_state_raises(self):
        """FSM guard: cannot send a queued proposal."""
        proposal = self._create_proposal()
        proposal.write({'state': 'queued'})
        with self.assertRaises(UserError):
            proposal.action_send()

    def test_send_terminal_proposal_raises(self):
        """FSM guard: cannot re-send a cancelled proposal."""
        proposal = self._create_proposal()
        proposal.action_send()
        proposal.action_cancel('test')
        with self.assertRaises(UserError):
            proposal.action_send()
