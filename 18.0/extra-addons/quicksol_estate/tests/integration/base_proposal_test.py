# -*- coding: utf-8 -*-

from datetime import date, timedelta
from odoo.tests.common import TransactionCase


class BaseProposalTest(TransactionCase):
    """
    Base TransactionCase for all Feature 013 integration tests.
    Creates a minimal but realistic data set:
      - 1 company
      - 1 owner user + res.partner
      - 1 manager user + res.partner
      - 1 agent record + user + res.partner
      - 1 property (active, assigned to agent)
      - 1 client partner (buyer/renter) with CPF
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_company()
        cls._setup_users()
        cls._setup_property()
        cls._setup_client()

    # ------------------------------------------------------------------ #
    # Company                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def _setup_company(cls):
        cls.company = cls.env['res.company'].create({
            'name': 'Test Imobiliária F013',
        })
        cls.env.user.company_ids = [(4, cls.company.id)]
        cls.env.user.company_id = cls.company

    # ------------------------------------------------------------------ #
    # Users                                                                #
    # ------------------------------------------------------------------ #

    @classmethod
    def _setup_users(cls):
        group_owner = cls.env.ref('quicksol_estate.group_real_estate_owner')
        group_manager = cls.env.ref('quicksol_estate.group_real_estate_manager')
        group_agent = cls.env.ref('quicksol_estate.group_real_estate_agent')
        group_receptionist = cls.env.ref('quicksol_estate.group_real_estate_receptionist')

        cls.owner_user = cls.env['res.users'].create({
            'name': 'Owner F013',
            'login': 'f013_owner@test.local',
            'groups_id': [(6, 0, [group_owner.id])],
            'company_ids': [(4, cls.company.id)],
            'company_id': cls.company.id,
        })

        cls.manager_user = cls.env['res.users'].create({
            'name': 'Manager F013',
            'login': 'f013_manager@test.local',
            'groups_id': [(6, 0, [group_manager.id])],
            'company_ids': [(4, cls.company.id)],
            'company_id': cls.company.id,
        })

        cls.agent_user = cls.env['res.users'].create({
            'name': 'Agent F013',
            'login': 'f013_agent@test.local',
            'groups_id': [(6, 0, [group_agent.id])],
            'company_ids': [(4, cls.company.id)],
            'company_id': cls.company.id,
        })

        cls.receptionist_user = cls.env['res.users'].create({
            'name': 'Receptionist F013',
            'login': 'f013_receptionist@test.local',
            'groups_id': [(6, 0, [group_receptionist.id])],
            'company_ids': [(4, cls.company.id)],
            'company_id': cls.company.id,
        })

        # Create agent record linked to agent_user
        cls.agent = cls.env['real.estate.agent'].create({
            'name': 'Agent F013',
            'user_id': cls.agent_user.id,
            'company_id': cls.company.id,
            'cpf': '123.456.789-09',
        })

    # ------------------------------------------------------------------ #
    # Property                                                             #
    # ------------------------------------------------------------------ #

    @classmethod
    def _setup_property(cls):
        prop_type = cls.env['real.estate.property.type'].search([], limit=1)
        if not prop_type:
            prop_type = cls.env['real.estate.property.type'].create({'name': 'Residencial'})
        country = cls.env.ref('base.br')
        state = cls.env['res.country.state'].search([
            ('country_id', '=', country.id)
        ], limit=1)
        location_type = cls.env['real.estate.location.type'].search([], limit=1)
        if not location_type:
            location_type = cls.env['real.estate.location.type'].create({'name': 'Urbano'})
        cls.property = cls.env['real.estate.property'].create({
            'name': 'Test Property F013',
            'property_purpose': 'residential',
            'property_type_id': prop_type.id,
            'company_id': cls.company.id,
            'active': True,
            'origin_media': 'website',
            'country_id': country.id,
            'state_id': state.id if state else False,
            'city': 'São Paulo',
            'zip_code': '01310-100',
            'street': 'Av. Paulista',
            'street_number': '1000',
            'location_type_id': location_type.id,
            'area': 80.0,
        })
        # Assign agent to property (required by proposal validation)
        cls.env['real.estate.agent.property.assignment'].create({
            'agent_id': cls.agent.id,
            'property_id': cls.property.id,
            'company_id': cls.company.id,
        })

    # ------------------------------------------------------------------ #
    # Client partner                                                       #
    # ------------------------------------------------------------------ #

    @classmethod
    def _setup_client(cls):
        cls.client_partner = cls.env['res.partner'].create({
            'name': 'Cliente Teste F013',
            'vat': '52998224725',  # valid CPF (Módulo 11)
            'email': 'cliente@f013.test',
        })

    # ------------------------------------------------------------------ #
    # Proposal factory                                                     #
    # ------------------------------------------------------------------ #

    def _create_proposal(self, **overrides):
        """
        Create a minimal valid draft proposal.
        Override any field via keyword arguments.
        """
        vals = {
            'property_id': self.property.id,
            'partner_id': self.client_partner.id,
            'agent_id': self.agent.id,
            'proposal_type': 'sale',
            'proposal_value': 350_000.00,
            'company_id': self.company.id,
        }
        vals.update(overrides)
        return self.env['real.estate.proposal'].create([vals])

    def _create_proposal_with_lead(self, **overrides):
        """Create a proposal and also return the linked lead."""
        proposal = self._create_proposal(**overrides)
        return proposal, proposal.lead_id

    def _valid_until(self, days=7):
        """Return a future date (today + days)."""
        return date.today() + timedelta(days=days)

    # ------------------------------------------------------------------ #
    # Environment helpers                                                  #
    # ------------------------------------------------------------------ #

    def env_as_user(self, user):
        """Switch environment to a specific user."""
        return self.env(user=user)
