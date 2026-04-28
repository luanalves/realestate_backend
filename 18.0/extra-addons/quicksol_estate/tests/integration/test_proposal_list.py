# -*- coding: utf-8 -*-
"""
Integration tests — Proposal list / search / pagination (T054-T058)
Covers: US6 — list, filter by state/agent/property, pagination, RBAC visibility
"""
from odoo.tests import tagged
from odoo.exceptions import AccessError

from .base_proposal_test import BaseProposalTest


@tagged('post_install', '-at_install', 'proposal', 'proposal_list')
class TestProposalList(BaseProposalTest):

    def test_owner_sees_all_company_proposals(self):
        """FR-035: Owner sees all proposals in company."""
        p1 = self._create_proposal()
        results = self.env['real.estate.proposal'].with_user(self.owner_user).search([
            ('company_id', '=', self.company.id),
        ])
        self.assertIn(p1, results)

    def test_manager_sees_all_company_proposals(self):
        """FR-035: Manager sees all proposals in company."""
        p1 = self._create_proposal()
        results = self.env['real.estate.proposal'].with_user(self.manager_user).search([
            ('company_id', '=', self.company.id),
        ])
        self.assertIn(p1, results)

    def test_agent_sees_only_own_proposals(self):
        """FR-035: Agent sees only proposals where agent_id == own agent record."""
        p1 = self._create_proposal()  # created with self.agent

        # Create second agent with different proposals
        other_agent_user = self.env['res.users'].create({
            'name': 'Other Agent F013',
            'login': 'f013_other_agent@test.local',
            'groups_id': [(6, 0, [self.env.ref('quicksol_estate.group_real_estate_agent').id])],
            'company_ids': [(4, self.company.id)],
            'company_id': self.company.id,
        })
        other_agent = self.env['real.estate.agent'].create({
            'name': 'Other Agent F013',
            'user_id': other_agent_user.id,
            'company_id': self.company.id,
            'cpf': '714.287.938-60',
        })
        other_client = self.env['res.partner'].create({
            'name': 'Other Client', 'vat': '11144477735',
        })
        # Assign other_agent to cls.property so the constraint passes
        self.env['real.estate.agent.property.assignment'].create({
            'agent_id': other_agent.id,
            'property_id': self.property.id,
            'company_id': self.company.id,
        })
        p2 = self._create_proposal(agent_id=other_agent.id, partner_id=other_client.id)

        agent_results = self.env['real.estate.proposal'].with_user(self.agent_user).search([
            ('company_id', '=', self.company.id),
        ])
        self.assertIn(p1, agent_results)
        self.assertNotIn(p2, agent_results)

    def test_receptionist_sees_proposals_read_only(self):
        """FR-036: Receptionist can read proposals but not write."""
        p1 = self._create_proposal()
        results = self.env['real.estate.proposal'].with_user(self.receptionist_user).search([
            ('company_id', '=', self.company.id),
        ])
        self.assertIn(p1, results)
        with self.assertRaises(AccessError):
            p1.with_user(self.receptionist_user).write({'description': 'x'})

    def test_filter_by_state(self):
        """FR-034: Proposals can be filtered by state."""
        p = self._create_proposal()
        p.action_send()
        sent_proposals = self.env['real.estate.proposal'].search([
            ('state', '=', 'sent'),
            ('company_id', '=', self.company.id),
        ])
        self.assertIn(p, sent_proposals)

    def test_company_isolation(self):
        """FR-048: Proposals from a different company are not visible."""
        other_co = self.env['res.company'].create({'name': 'Other Co F013 List'})
        other_prop = self.env['real.estate.property'].create({
            'name': 'Other Prop', 'property_purpose': 'residential',
            'property_type_id': self.property.property_type_id.id,
            'company_id': other_co.id, 'origin_media': 'website',
            'country_id': self.property.country_id.id,
            'state_id': self.property.state_id.id,
            'city': 'Campinas', 'zip_code': '13010-100',
            'street': 'Rua Teste', 'street_number': '1',
            'location_type_id': self.property.location_type_id.id,
            'area': 60.0,
        })
        other_agent = self.env['real.estate.agent'].create({
            'name': 'Other Agent', 'company_id': other_co.id,
            'cpf': '987.654.321-00',
        })
        other_client = self.env['res.partner'].create({
            'name': 'Other', 'vat': '71428793860',
        })
        # Assign other_agent to other_prop so the constraint passes
        self.env['real.estate.agent.property.assignment'].create({
            'agent_id': other_agent.id,
            'property_id': other_prop.id,
            'company_id': other_co.id,
        })
        other_proposal = self.env['real.estate.proposal'].sudo().create([{
            'property_id': other_prop.id,
            'partner_id': other_client.id,
            'agent_id': other_agent.id,
            'proposal_type': 'sale',
            'proposal_value': 100_000,
            'company_id': other_co.id,
        }])
        visible = self.env['real.estate.proposal'].with_user(self.owner_user).search([])
        self.assertNotIn(other_proposal, visible)
