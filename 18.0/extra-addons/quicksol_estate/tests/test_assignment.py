# -*- coding: utf-8 -*-
"""
Test Agent-Property Assignment

Tests for User Story 3: Assign agents to properties with multi-tenant validation
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestAgentPropertyAssignment(TransactionCase):
    """Test agent-property assignment functionality"""
    
    def setUp(self):
        super().setUp()
        
        # Get or create test companies
        self.company_a = self.env['thedevkitchen.estate.company'].search([('name', '=', 'Company A Test')], limit=1)
        if not self.company_a:
            self.company_a = self.env['thedevkitchen.estate.company'].create({
                'name': 'Company A Test',
                'cnpj': '12.345.678/0001-95',
                'email': 'companya@test.com',
                'phone': '+55 11 1111-1111',
            })
        
        self.company_b = self.env['thedevkitchen.estate.company'].search([('name', '=', 'Company B Test')], limit=1)
        if not self.company_b:
            self.company_b = self.env['thedevkitchen.estate.company'].create({
                'name': 'Company B Test',
                'cnpj': '98.765.432/0001-98',
                'email': 'companyb@test.com',
                'phone': '+55 11 2222-2222',
            })
        
        # Create test agents
        self.agent_a = self.env['real.estate.agent'].create({
            'name': 'Agent A',
            'cpf': '11111111111',
            'email': 'agent.a@test.com',
            'company_id': self.company_a.id,
        })
        
        self.agent_b = self.env['real.estate.agent'].create({
            'name': 'Agent B',
            'cpf': '22222222222',
            'email': 'agent.b@test.com',
            'company_id': self.company_b.id,
        })
        
        # Get or create location types and property types
        self.location_type_urban = self.env['real.estate.location.type'].search([('code', '=', 'URB')], limit=1)
        if not self.location_type_urban:
            self.location_type_urban = self.env['real.estate.location.type'].create({
                'name': 'Urban',
                'code': 'URB',
                'sequence': 10,
            })
        
        self.property_type_house = self.env['real.estate.property.type'].search([('name', '=', 'House')], limit=1)
        if not self.property_type_house:
            self.property_type_house = self.env['real.estate.property.type'].create({
                'name': 'House'
            })
        
        self.property_type_apartment = self.env['real.estate.property.type'].search([('name', '=', 'Apartment')], limit=1)
        if not self.property_type_apartment:
            self.property_type_apartment = self.env['real.estate.property.type'].create({
                'name': 'Apartment'
            })
        
        # Create test properties
        self.property_a = self.env['real.estate.property'].create({
            'name': 'Property A',
            'reference_code': 'PROP-A-001',
            'company_ids': [(6, 0, [self.company_a.id])],
            'property_type_id': self.property_type_house.id,
            'location_type_id': self.location_type_urban.id,
            'state_id': self.env['real.estate.state'].search([], limit=1).id,
            'price': 250000.00,
            'area': 100.0,
            'num_rooms': 3,
            'num_bathrooms': 2,
            'zip_code': '12345-678',
            'city': 'São Paulo',
            'street': 'Avenida Paulista',
            'street_number': '1000',
        })
        
        self.property_b = self.env['real.estate.property'].create({
            'name': 'Property B',
            'reference_code': 'PROP-B-001',
            'company_ids': [(6, 0, [self.company_b.id])],
            'property_type_id': self.property_type_apartment.id,
            'location_type_id': self.location_type_urban.id,
            'state_id': self.env['real.estate.state'].search([], limit=1).id,
            'price': 180000.00,
            'area': 75.0,
            'num_rooms': 2,
            'num_bathrooms': 1,
            'zip_code': '98765-432',
            'city': 'Rio de Janeiro',
            'street': 'Avenida Atlântica',
            'street_number': '500',
        })
        
        self.Assignment = self.env['real.estate.agent.property.assignment']
    
    def test_assign_agent_to_property(self):
        """T050: Create agent-property assignment"""
        assignment = self.Assignment.create({
            'agent_id': self.agent_a.id,
            'property_id': self.property_a.id,
            'responsibility_type': 'primary',
        })
        
        self.assertTrue(assignment.id, "Assignment should be created")
        self.assertEqual(assignment.agent_id, self.agent_a)
        self.assertEqual(assignment.property_id, self.property_a)
        self.assertEqual(assignment.company_id, self.company_a)
        self.assertIsNotNone(assignment.assignment_date, "Assignment date should be set")
    
    def test_assign_agent_cross_company_forbidden(self):
        """T051: Reject assignment when agent and property in different companies"""
        with self.assertRaises(ValidationError, msg="Should reject cross-company assignment"):
            self.Assignment.create({
                'agent_id': self.agent_a.id,  # Company A
                'property_id': self.property_b.id,  # Company B
                'responsibility_type': 'primary',
            })
    
    def test_multiple_agents_per_property(self):
        """T052: Allow multiple agents assigned to same property"""
        # Create second agent in Company A
        agent_a2 = self.env['real.estate.agent'].create({
            'name': 'Agent A2',
            'cpf': '33333333333',
            'email': 'agent.a2@test.com',
            'company_id': self.company_a.id,
        })
        
        # Assign first agent
        assignment1 = self.Assignment.create({
            'agent_id': self.agent_a.id,
            'property_id': self.property_a.id,
            'responsibility_type': 'primary',
        })
        
        # Assign second agent
        assignment2 = self.Assignment.create({
            'agent_id': agent_a2.id,
            'property_id': self.property_a.id,
            'responsibility_type': 'secondary',
        })
        
        self.assertTrue(assignment1.id and assignment2.id, "Both assignments should be created")
        
        # Verify property has both agents
        self.assertEqual(len(self.property_a.assigned_agent_ids), 2)
        self.assertIn(self.agent_a, self.property_a.assigned_agent_ids)
        self.assertIn(agent_a2, self.property_a.assigned_agent_ids)
    
    def test_list_agent_properties(self):
        """T053: List all properties assigned to an agent"""
        # Create second property in Company A
        property_a2 = self.env['real.estate.property'].create({
            'name': 'Property A2',
            'reference_code': 'PROP-A-002',
            'company_ids': [(6, 0, [self.company_a.id])],
            'property_type_id': self.env['real.estate.property.type'].search([], limit=1).id,
            'location_type_id': self.env['real.estate.location.type'].search([], limit=1).id,
            'state_id': self.env['real.estate.state'].search([], limit=1).id,
            'price': 300000.00,
            'area': 120.0,
            'num_rooms': 4,
            'num_bathrooms': 3,
            'zip_code': '11111-111',
            'city': 'São Paulo',
            'street': 'Rua Oscar Freire',
            'street_number': '200',
        })
        
        # Assign agent to both properties
        self.Assignment.create({
            'agent_id': self.agent_a.id,
            'property_id': self.property_a.id,
            'responsibility_type': 'primary',
        })
        
        self.Assignment.create({
            'agent_id': self.agent_a.id,
            'property_id': property_a2.id,
            'responsibility_type': 'primary',
        })
        
        # Verify agent has both properties
        self.assertEqual(len(self.agent_a.agent_property_ids), 2)
        self.assertIn(self.property_a, self.agent_a.agent_property_ids)
        self.assertIn(property_a2, self.agent_a.agent_property_ids)
        
        # Verify computed field
        self.assertEqual(self.agent_a.assigned_property_count, 2)
    
    def test_assignment_company_auto_set(self):
        """Test assignment company_id is automatically set from agent"""
        assignment = self.Assignment.create({
            'agent_id': self.agent_a.id,
            'property_id': self.property_a.id,
            'responsibility_type': 'primary',
        })
        
        self.assertEqual(assignment.company_id, self.agent_a.company_id)
    
    def test_unassign_agent_from_property(self):
        """Test removing agent assignment"""
        assignment = self.Assignment.create({
            'agent_id': self.agent_a.id,
            'property_id': self.property_a.id,
            'responsibility_type': 'primary',
        })
        
        assignment_id = assignment.id
        assignment.unlink()
        
        # Verify assignment deleted
        self.assertFalse(
            self.Assignment.search([('id', '=', assignment_id)]),
            "Assignment should be deleted"
        )
        
        # Verify property no longer has agent
        self.assertNotIn(self.agent_a, self.property_a.assigned_agent_ids)
