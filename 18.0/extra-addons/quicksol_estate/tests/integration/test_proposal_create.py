# -*- coding: utf-8 -*-
"""
Unit tests — Proposal creation (T019)
Covers: FR-001, FR-002, FR-003, FR-004, FR-032 (pessimistic lock slot logic)
"""
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import ValidationError

from .base_proposal_test import BaseProposalTest


@tagged('post_install', '-at_install', 'proposal', 'proposal_create')
class TestProposalCreate(BaseProposalTest):

    def test_create_draft_when_no_active_proposal(self):
        """US1/FR-001: First proposal for a property goes to draft."""
        proposal = self._create_proposal()
        self.assertEqual(proposal.state, 'draft')
        self.assertTrue(proposal.proposal_code.startswith('PRP'))

    def test_create_queued_when_active_proposal_exists(self):
        """US3/FR-009: Second proposal for same property goes to queued."""
        first = self._create_proposal()
        first.action_send()  # first → sent
        second = self._create_proposal(partner_id=self._make_partner().id)
        self.assertEqual(second.state, 'queued')

    def test_proposal_code_generated(self):
        """FR-003: Proposal code follows PRP##### pattern."""
        proposal = self._create_proposal()
        self.assertRegex(proposal.proposal_code, r'^PRP\d+$')

    def test_proposal_value_positive(self):
        """FR-004: Proposal value must be positive."""
        with self.assertRaises(Exception):
            self._create_proposal(proposal_value=0)

    def test_valid_until_bounds(self):
        """FR-005: valid_until must be in range (today, today+90d]."""
        from datetime import date, timedelta
        # Too early
        with self.assertRaises(ValidationError):
            self._create_proposal(valid_until=date.today())
        # Too far
        with self.assertRaises(ValidationError):
            self._create_proposal(valid_until=date.today() + timedelta(days=91))

    def test_lead_created_on_proposal_create(self):
        """US5/FR-028: Creating a proposal creates or links a lead with source=proposal."""
        proposal = self._create_proposal()
        self.assertTrue(proposal.lead_id)
        self.assertEqual(proposal.lead_id.source, 'proposal')

    def test_property_company_mismatch_rejected(self):
        """FR-006: Property must belong to same company as proposal."""
        other_company = self.env['res.company'].create({'name': 'Other Co F013'})
        other_prop = self.env['real.estate.property'].create({
            'name': 'Other Property',
            'property_purpose': 'residential',
            'property_type_id': self.property.property_type_id.id,
            'company_id': other_company.id,
            'origin_media': 'website',
            'country_id': self.property.country_id.id,
            'state_id': self.property.state_id.id,
            'city': 'Curitiba', 'zip_code': '80010-100',
            'street': 'Rua Teste', 'street_number': '1',
            'location_type_id': self.property.location_type_id.id,
            'area': 60.0,
        })
        with self.assertRaises(ValidationError):
            self._create_proposal(
                property_id=other_prop.id,
                company_id=self.company.id,
            )

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _make_partner(self):
        return self.env['res.partner'].create({
            'name': 'Extra Client',
            'vat': '11144477735',
        })
