# -*- coding: utf-8 -*-
"""
Integration Tests for Owner RBAC (User Story 1)

Tests owner permissions using TransactionCase with real database and ACLs

Purpose:
- Test owner full CRUD access to all company models
- Test multi-tenancy: owner cannot see other companies' data
- Test record rules and access control lists (ACLs)

Run: docker compose run --rm odoo odoo --test-enable --test-tags=quicksol_estate
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, ValidationError


class TestRBACOwnerIntegration(TransactionCase):
    """Integration tests for Owner RBAC with real database"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        super(TestRBACOwnerIntegration, cls).setUpClass()
        
        # Get models
        cls.User = cls.env['res.users']
        cls.Company = cls.env['res.company']
        cls.Property = cls.env['real.estate.property']
        cls.Agent = cls.env['real.estate.agent']
        cls.PropertyType = cls.env['real.estate.property.type']
        
        # Create test companies
        cls.company_a = cls.Company.create({
            'name': 'Real Estate Company A',
        })
        
        cls.company_b = cls.Company.create({
            'name': 'Real Estate Company B',
        })
        
        # Get owner security group
        cls.group_owner = cls.env.ref('quicksol_estate.group_real_estate_owner')
        
        # Create owner user for Company A
        cls.owner_a = cls.User.create({
            'name': 'Owner A',
            'login': 'owner_a@test.com',
            'email': 'owner_a@test.com',
            'company_id': cls.company_a.id,
            'company_ids': [(4, cls.company_a.id)],
            'groups_id': [(4, cls.group_owner.id)],
        })
        
        # Create owner user for Company B
        cls.owner_b = cls.User.create({
            'name': 'Owner B',
            'login': 'owner_b@test.com',
            'email': 'owner_b@test.com',
            'company_id': cls.company_b.id,
            'company_ids': [(4, cls.company_b.id)],
            'groups_id': [(4, cls.group_owner.id)],
        })
        
        # Create property type
        cls.property_type = cls.PropertyType.create({
            'name': 'Residential',
        })
    
    def test_owner_full_crud_access_to_properties(self):
        """Test that owner has full CRUD access to all company properties"""
        # Act as owner_a
        Property = self.Property.with_user(self.owner_a)
        
        # CREATE: Owner should be able to create properties
        new_property = Property.create({
            'name': 'Owner A Property 1',
            'expected_price': 100000,
            'property_type_id': self.property_type.id,
            'company_id': self.company_a.id,
        })
        
        self.assertTrue(new_property.id)
        self.assertEqual(new_property.name, 'Owner A Property 1')
        
        # READ: Owner should be able to read own properties
        properties = Property.search([('company_id', '=', self.company_a.id)])
        self.assertGreater(len(properties), 0)
        self.assertIn(new_property.id, properties.ids)
        
        # UPDATE: Owner should be able to update properties
        new_property.write({'expected_price': 120000})
        self.assertEqual(new_property.expected_price, 120000)
        
        # DELETE: Owner should be able to delete properties
        property_id = new_property.id
        new_property.unlink()
        
        # Verify deleted
        deleted = Property.search([('id', '=', property_id)])
        self.assertEqual(len(deleted), 0)
    
    def test_owner_can_create_users_in_own_company(self):
        """Test that owner can create users in their own company"""
        # Act as owner_a
        User = self.User.with_user(self.owner_a)
        
        # Owner should be able to create user in same company
        new_user = User.create({
            'name': 'New Agent for Company A',
            'login': 'agent_a1@test.com',
            'email': 'agent_a1@test.com',
            'company_id': self.company_a.id,
            'company_ids': [(4, self.company_a.id)],
        })
        
        self.assertTrue(new_user.id)
        self.assertEqual(new_user.company_id.id, self.company_a.id)
        self.assertEqual(new_user.name, 'New Agent for Company A')
    
    def test_owner_cannot_see_other_companies_data(self):
        """Test multi-tenancy: owner cannot see other companies' data"""
        # Create property for Company A
        property_a = self.Property.create({
            'name': 'Company A Property',
            'expected_price': 100000,
            'property_type_id': self.property_type.id,
            'company_id': self.company_a.id,
        })
        
        # Create property for Company B
        property_b = self.Property.create({
            'name': 'Company B Property',
            'expected_price': 200000,
            'property_type_id': self.property_type.id,
            'company_id': self.company_b.id,
        })
        
        # Act as owner_a
        Property = self.Property.with_user(self.owner_a)
        
        # Owner A should only see Company A properties
        visible_properties = Property.search([])
        visible_ids = visible_properties.ids
        
        self.assertIn(property_a.id, visible_ids)
        self.assertNotIn(property_b.id, visible_ids, 
                        "Owner A should NOT see Company B properties")
    
    def test_owner_full_access_to_agents(self):
        """Test that owner has full CRUD access to agents in their company"""
        # Act as owner_a
        Agent = self.Agent.with_user(self.owner_a)
        
        # CREATE: Owner should be able to create agents
        new_agent = Agent.create({
            'name': 'Agent for Company A',
            'email': 'agent_companya@test.com',
            'creci': '12345',
            'company_id': self.company_a.id,
        })
        
        self.assertTrue(new_agent.id)
        
        # READ: Owner should be able to read agents
        agents = Agent.search([('company_id', '=', self.company_a.id)])
        self.assertGreater(len(agents), 0)
        
        # UPDATE: Owner should be able to update agents
        new_agent.write({'creci': '54321'})
        self.assertEqual(new_agent.creci, '54321')
        
        # DELETE: Owner should be able to delete agents
        agent_id = new_agent.id
        new_agent.unlink()
        
        deleted = Agent.search([('id', '=', agent_id)])
        self.assertEqual(len(deleted), 0)
    
    def test_owner_can_manage_own_company_settings(self):
        """Test that owner can read and update their company settings"""
        # Act as owner_a
        Company = self.Company.with_user(self.owner_a)
        
        # Owner should be able to read their company
        own_company = Company.browse(self.company_a.id)
        self.assertEqual(own_company.name, 'Real Estate Company A')
        
        # Owner should be able to update their company
        own_company.write({'phone': '+1234567890'})
        self.assertEqual(own_company.phone, '+1234567890')
    
    def test_owner_multi_tenancy_isolation_for_agents(self):
        """Test that owner cannot see agents from other companies"""
        # Create agent for Company A
        agent_a = self.Agent.create({
            'name': 'Agent Company A',
            'email': 'agent_a@test.com',
            'creci': 'CRECI-A',
            'company_id': self.company_a.id,
        })
        
        # Create agent for Company B
        agent_b = self.Agent.create({
            'name': 'Agent Company B',
            'email': 'agent_b@test.com',
            'creci': 'CRECI-B',
            'company_id': self.company_b.id,
        })
        
        # Act as owner_a
        Agent = self.Agent.with_user(self.owner_a)
        
        # Owner A should only see Company A agents
        visible_agents = Agent.search([])
        visible_ids = visible_agents.ids
        
        self.assertIn(agent_a.id, visible_ids)
        self.assertNotIn(agent_b.id, visible_ids,
                        "Owner A should NOT see Company B agents")
    
    def test_owner_access_to_all_company_models(self):
        """Test that owner has read access to all key company models"""
        # Act as owner_a
        env = self.env(user=self.owner_a)
        
        # Owner should be able to access these models
        models_to_test = [
            'real.estate.property',
            'real.estate.agent',
            'real.estate.property.type',
            'real.estate.amenity',
            'res.company',
            'res.users',
        ]
        
        for model_name in models_to_test:
            try:
                Model = env[model_name]
                # Try to search (should not raise AccessError)
                records = Model.search([], limit=1)
                # If we get here, access is granted (test passes)
                self.assertTrue(True, f"Owner has access to {model_name}")
            except AccessError:
                self.fail(f"Owner should have access to {model_name}")
