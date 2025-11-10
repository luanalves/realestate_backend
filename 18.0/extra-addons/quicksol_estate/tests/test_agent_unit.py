# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestAgentUnit(TransactionCase):
    """
    Unit tests for Agent model business logic.
    
    Tests cover:
    - Agent creation and data synchronization with users
    - Email validation using email_normalize
    - User-Agent company synchronization logic 
    - Write method behavior and edge cases
    - onchange methods and field updates
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create real estate company records for testing
        cls.company_1 = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Estate Company 1',
        })
        cls.company_2 = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Estate Company 2',
        })
        cls.company_3 = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Estate Company 3',
        })
    
    def setUp(self):
        super().setUp()
        
        # Create real user with estate companies
        self.user_with_companies = self.env['res.users'].create({
            'name': 'John Agent User',
            'login': 'john@agent.com',
            'email': 'john@agent.com',
            'estate_company_ids': [(6, 0, [self.company_1.id, self.company_2.id])]
        })
        
        # Create real user without estate companies 
        self.user_without_companies = self.env['res.users'].create({
            'name': 'Jane Agent User',
            'login': 'jane@agent.com',
            'email': 'jane@agent.com',
        })
    
    def test_agent_creation_with_user_sync(self):
        """Test agent creation with user data synchronization"""
        
        # Act - Create agent with user, without explicit company_ids
        agent = self.env['real.estate.agent'].create({
            'name': 'Test Agent',
            'user_id': self.user_with_companies.id
        })
        
        # Assert - Agent should inherit companies from user automatically
        self.assertEqual(agent.name, 'Test Agent')
        self.assertEqual(agent.user_id, self.user_with_companies)
        self.assertEqual(len(agent.company_ids), 2)
        self.assertIn(self.company_1, agent.company_ids)
        self.assertIn(self.company_2, agent.company_ids)
    
    def test_agent_onchange_user_id_sync_data(self):
        """Test onchange user_id synchronizes agent data with user data"""
        
        # Create agent without user
        agent = self.env['real.estate.agent'].create({
            'name': 'Initial Name',
            'email': 'initial@email.com',
        })
        
        # Trigger onchange by setting user_id (in form context)
        agent.user_id = self.user_with_companies
        agent._onchange_user_id()
        
        # Assert - Name and email should NOT change (already set)
        # But companies should sync
        self.assertEqual(agent.name, 'Initial Name')  # Not overridden
        self.assertEqual(agent.email, 'initial@email.com')  # Not overridden
        self.assertEqual(len(agent.company_ids), 2)
        self.assertIn(self.company_1, agent.company_ids)
        self.assertIn(self.company_2, agent.company_ids)
        
    def test_agent_onchange_user_id_empty_fields(self):
        """Test onchange fills empty name and email from user"""
        
        # Create agent with empty name and email (edge case)
        agent = self.env['real.estate.agent'].new({
            'name': '',  # Empty name
        })
        
        # Set user and trigger onchange
        agent.user_id = self.user_with_companies
        agent._onchange_user_id()
        
        # Assert - Empty fields should be filled
        self.assertEqual(agent.name, 'John Agent User')
        self.assertEqual(agent.email, 'john@agent.com')
    
    def test_agent_onchange_user_id_preserve_existing_data(self):
        """Test onchange doesn't override existing agent data"""
        
        # Create agent with existing data
        agent = self.env['real.estate.agent'].new({
            'name': 'Existing Agent Name',
            'email': 'existing@agent.com',
        })
        
        # Set user and trigger onchange
        agent.user_id = self.user_with_companies
        agent._onchange_user_id()
        
        # Assert - Existing data should be preserved
        self.assertEqual(agent.name, 'Existing Agent Name')
        self.assertEqual(agent.email, 'existing@agent.com')
        # But companies should still sync
        self.assertEqual(len(agent.company_ids), 2)
    
    def test_agent_email_validation_valid(self):
        """Test email validation for valid emails"""
        
        valid_emails = [
            'agent@company.com',
            'john.doe@realestate.com.br',
            'agent+tag@domain.org'
        ]
        
        for email in valid_emails:
            with self.subTest(email=email):
                # Should not raise ValidationError
                agent = self.env['real.estate.agent'].create({
                    'name': 'Test Agent',
                    'email': email
                })
                
                self.assertEqual(agent.email, email)
    
    def test_agent_write_user_id_change_sync_companies(self):
        """Test write method syncs companies when user_id changes"""
        
        # Create agent without user
        agent = self.env['real.estate.agent'].create({
            'name': 'Test Agent',
        })
        
        self.assertEqual(len(agent.company_ids), 0)
        
        # Act - Update user_id via write (without explicit company_ids)
        agent.write({'user_id': self.user_with_companies.id})
        
        # Assert - Companies should sync from user
        self.assertEqual(agent.user_id, self.user_with_companies)
        self.assertEqual(len(agent.company_ids), 2)
        self.assertIn(self.company_1, agent.company_ids)
        self.assertIn(self.company_2, agent.company_ids)
    
    def test_agent_write_user_id_change_no_sync_when_companies_provided(self):
        """Test write method doesn't sync companies when company_ids explicitly provided"""
        
        # Create agent without user
        agent = self.env['real.estate.agent'].create({
            'name': 'Test Agent',
        })
        
        # Act - Update both user_id AND company_ids explicitly
        agent.write({
            'user_id': self.user_with_companies.id,
            'company_ids': [(6, 0, [self.company_3.id])]  # Explicitly set different company
        })
        
        # Assert - Explicit company_ids should be preserved (not synced from user)
        self.assertEqual(len(agent.company_ids), 1)
        self.assertIn(self.company_3, agent.company_ids)
        self.assertNotIn(self.company_1, agent.company_ids)
        self.assertNotIn(self.company_2, agent.company_ids)
    
    def test_agent_write_user_id_change_safe_access_no_estate_companies(self):
        """Test write method safely handles users without estate_company_ids"""
        
        # Create agent
        agent = self.env['real.estate.agent'].create({
            'name': 'Test Agent',
        })
        
        # Act - Update to user without estate companies
        agent.write({'user_id': self.user_without_companies.id})
        
        # Assert - Should not crash, company_ids should remain empty
        self.assertEqual(agent.user_id, self.user_without_companies)
        self.assertEqual(len(agent.company_ids), 0)
    
    def test_agent_write_other_fields_no_sync(self):
        """Test write method doesn't sync when other fields are updated"""
        
        # Create agent with user and companies
        agent = self.env['real.estate.agent'].create({
            'name': 'Original Name',
            'email': 'original@email.com',
            'user_id': self.user_with_companies.id,
        })
        
        # Companies should be synced on creation
        original_company_count = len(agent.company_ids)
        self.assertEqual(original_company_count, 2)
        
        # Act - Update other fields (not user_id)
        agent.write({
            'name': 'Updated Name',
            'phone': '+55 11 99999-9999'
        })
        
        # Assert - Companies should remain unchanged
        self.assertEqual(agent.name, 'Updated Name')
        self.assertEqual(agent.phone, '+55 11 99999-9999')
        self.assertEqual(len(agent.company_ids), original_company_count)
    
    def test_agent_relationships_integrity(self):
        """Test agent relationships with companies and properties"""
        
        # Create agent with companies
        agent = self.env['real.estate.agent'].create({
            'name': 'Relationship Agent',
            'company_ids': [(6, 0, [self.company_1.id, self.company_2.id])]
        })
        
        # Assert relationships
        self.assertEqual(len(agent.company_ids), 2)
        self.assertIn(self.company_1, agent.company_ids)
        self.assertIn(self.company_2, agent.company_ids)
    
    def test_agent_default_values(self):
        """Test agent default values"""
        
        # Create agent with minimal data
        agent = self.env['real.estate.agent'].create({
            'name': 'Default Test Agent'
        })
        
        # Assert default values
        self.assertEqual(agent.years_experience, 0)
        self.assertTrue(agent.name and len(agent.name.strip()) > 0)


class TestAgentBusinessLogic(TransactionCase):
    """
    Unit tests for Agent model advanced business logic.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create companies for testing
        cls.company_1 = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Business Company 1',
        })
        cls.company_2 = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Business Company 2',
        })
        cls.company_3 = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Business Company 3',
        })
        
        # Create test user
        cls.test_user = cls.env['res.users'].create({
            'name': 'Business Test User',
            'login': 'business@test.com',
            'email': 'business@test.com',
        })
    
    def test_agent_company_assignment_workflow(self):
        """Test complete workflow of agent-company assignment"""
        
        # Create agent without companies
        agent = self.env['real.estate.agent'].create({
            'name': 'Workflow Agent',
        })
        
        self.assertEqual(len(agent.company_ids), 0)
        
        # Act - Assign companies
        agent.write({
            'company_ids': [(6, 0, [self.company_1.id, self.company_2.id, self.company_3.id])]
        })
        
        # Assert
        self.assertEqual(len(agent.company_ids), 3)
        self.assertIn(self.company_1, agent.company_ids)
        self.assertIn(self.company_2, agent.company_ids)
        self.assertIn(self.company_3, agent.company_ids)
    
    def test_agent_user_integration(self):
        """Test agent-user integration scenarios"""
        
        # Scenario 1: Agent with user
        agent_with_user = self.env['real.estate.agent'].create({
            'name': 'Agent With User',
            'user_id': self.test_user.id
        })
        
        self.assertTrue(agent_with_user.user_id)
        self.assertEqual(agent_with_user.user_id, self.test_user)
        
        # Scenario 2: Agent without user (external agent)
        agent_without_user = self.env['real.estate.agent'].create({
            'name': 'External Agent',
        })
        
        self.assertFalse(agent_without_user.user_id)
    
    def test_agent_data_validation(self):
        """Test agent data validation and integrity"""
        
        # Create agent with all fields
        agent = self.env['real.estate.agent'].create({
            'name': 'Validation Agent',
            'email': 'valid@agent.com',
            'phone': '+55 11 99999-8888',
            'agency_name': 'Top Realty',
            'years_experience': 5
        })
        
        # Assert - All fields should be properly set
        self.assertEqual(agent.name, 'Validation Agent')
        self.assertEqual(agent.email, 'valid@agent.com')
        self.assertTrue('@' in agent.email)  # Basic email check
        self.assertTrue(agent.phone.startswith('+55'))  # Brazilian phone
        self.assertEqual(agent.years_experience, 5)
        self.assertEqual(agent.agency_name, 'Top Realty')
    
    def test_agent_edge_cases(self):
        """Test edge cases and boundary conditions"""
        
        # Edge case 1: Very long name
        long_name = 'A' * 100
        agent_long_name = self.env['real.estate.agent'].create({
            'name': long_name
        })
        
        self.assertEqual(len(agent_long_name.name), 100)
        
        # Edge case 2: Zero experience
        agent_zero_exp = self.env['real.estate.agent'].create({
            'name': 'New Agent',
            'years_experience': 0
        })
        
        self.assertEqual(agent_zero_exp.years_experience, 0)
        
        # Edge case 3: High experience
        agent_high_exp = self.env['real.estate.agent'].create({
            'name': 'Senior Agent',
            'years_experience': 50
        })
        
        self.assertEqual(agent_high_exp.years_experience, 50)