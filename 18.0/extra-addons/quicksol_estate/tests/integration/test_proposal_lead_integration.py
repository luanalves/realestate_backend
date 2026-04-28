# -*- coding: utf-8 -*-
"""
Integration tests — Lead integration (T050-T053)
Covers: US5 — lead created/linked on proposal create, source=proposal,
        lead state progression, duplicate detection
"""
from odoo.tests import tagged

from .base_proposal_test import BaseProposalTest


@tagged('post_install', '-at_install', 'proposal', 'proposal_lead')
class TestProposalLeadIntegration(BaseProposalTest):

    def test_proposal_creates_lead(self):
        """US5/FR-028: First proposal for partner+property creates a lead."""
        proposal = self._create_proposal()
        self.assertTrue(proposal.lead_id)

    def test_lead_source_is_proposal(self):
        """US5/FR-028: Lead source field is set to 'proposal'."""
        proposal = self._create_proposal()
        self.assertEqual(proposal.lead_id.source, 'proposal')

    def test_second_proposal_reuses_open_lead(self):
        """US5/FR-029: If an open lead exists for same partner+property, reuse it."""
        p1 = self._create_proposal()
        lead_id = p1.lead_id.id

        # Cancel and create a new proposal for the same partner+property
        p1.action_cancel('testing reuse')
        p2 = self._create_proposal()
        self.assertEqual(p2.lead_id.id, lead_id)

    def test_lead_state_when_proposal_accepted(self):
        """US5/FR-031: Lead state → won when proposal is accepted."""
        proposal = self._create_proposal()
        proposal.action_send()
        proposal.with_user(self.manager_user).action_accept()
        proposal.lead_id.invalidate_recordset()
        self.assertEqual(proposal.lead_id.state, 'won')

    def test_lead_state_when_proposal_rejected(self):
        """US5/FR-030: Lead state remains open when proposal is rejected (can retry)."""
        proposal = self._create_proposal()
        proposal.action_send()
        proposal.with_user(self.manager_user).action_reject('too expensive')
        proposal.lead_id.invalidate_recordset()
        self.assertNotEqual(proposal.lead_id.state, 'lost')

    def test_proposal_ids_on_lead(self):
        """Reverse relation: lead.proposal_ids contains the proposal."""
        proposal = self._create_proposal()
        self.assertIn(proposal, proposal.lead_id.proposal_ids)
