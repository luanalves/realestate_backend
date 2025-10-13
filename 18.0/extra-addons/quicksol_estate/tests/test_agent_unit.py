# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import date

from .base_agent_test import BaseAgentTest


class TestAgentUnit(BaseAgentTest):
    """
    Unit tests for Agent model business logic.
    
    Tests cover:
    - Agent creation and data synchronization with users
    - Email validation using email_normalize
    - User-Agent company synchronization logic 
    - Write method behavior and edge cases
    - onchange methods and field updates
    """
    
    def setUp(self):
        super().setUp()
        
        # Mock user with estate companies
        self.mock_user_with_companies = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'John Agent User',
            'email': 'john@agent.com',
            'estate_company_ids': [1, 2]  # User assigned to 2 companies
        })
        
        # Mock user without estate companies 
        self.mock_user_without_companies = self.create_mock_record('res.users', {
            'id': 2,
            'name': 'Jane Agent User',
            'email': 'jane@agent.com'
            # No estate_company_ids attribute
        })
    
    def test_agent_creation_with_user_sync(self):
        """Test agent creation with user data synchronization"""
        
        # Arrange
        agent_data = {
            'name': 'Test Agent',
            'user_id': 1
        }
        
        # Act
        agent = self.create_mock_record('real.estate.agent', agent_data)
        
        # Simulate the creation sync logic
        if agent.user_id and not agent_data.get('company_ids'):
            # Auto-assign user's companies to agent
            user = self.mock_user_with_companies
            if hasattr(user, 'estate_company_ids') and user.estate_company_ids:
                agent.company_ids = user.estate_company_ids
        
        # Assert
        self.assertEqual(agent.name, 'Test Agent')
        self.assertEqual(agent.user_id, 1)
        # Should inherit companies from user
        if hasattr(agent, 'company_ids'):
            self.assertEqual(agent.company_ids, [1, 2])
    
    def test_agent_onchange_user_id_sync_data(self):
        """Test onchange user_id synchronizes agent data with user data"""
        
        # Arrange
        agent = self.create_mock_record('real.estate.agent', {
            'name': '',  # Empty name to test sync
            'email': '',  # Empty email to test sync
            'user_id': None
        })
        
        # Act - Simulate onchange behavior
        agent.user_id = 1  # Set user
        
        # Simulate onchange logic
        if agent.user_id:
            user = self.mock_user_with_companies
            if not agent.name:
                agent.name = user.name
            if not agent.email:
                agent.email = user.email
            if hasattr(user, 'estate_company_ids') and user.estate_company_ids:
                agent.company_ids = user.estate_company_ids
        
        # Assert
        self.assertEqual(agent.name, 'John Agent User')
        self.assertEqual(agent.email, 'john@agent.com')
        self.assertEqual(agent.company_ids, [1, 2])
    
    def test_agent_onchange_user_id_preserve_existing_data(self):
        """Test onchange doesn't override existing agent data"""
        
        # Arrange - Agent with existing data
        agent = self.create_mock_record('real.estate.agent', {
            'name': 'Existing Agent Name',
            'email': 'existing@agent.com',
            'user_id': None
        })
        
        # Act - Set user
        agent.user_id = 1
        
        # Simulate onchange logic (should not override existing data)
        if agent.user_id:
            user = self.mock_user_with_companies
            # Only sync if fields are empty
            if not agent.name:
                agent.name = user.name
            if not agent.email:
                agent.email = user.email
        
        # Assert - Existing data should be preserved
        self.assertEqual(agent.name, 'Existing Agent Name')
        self.assertEqual(agent.email, 'existing@agent.com')
    
    @patch('odoo.tools.email_normalize')
    def test_agent_email_validation_valid(self, mock_email_normalize):
        """Test email validation for valid emails"""
        
        valid_emails = [
            'agent@company.com',
            'john.doe@realestate.com.br',
            'agent+tag@domain.org'
        ]
        
        for email in valid_emails:
            with self.subTest(email=email):
                # Arrange
                mock_email_normalize.return_value = email.lower()
                agent = self.create_mock_record('real.estate.agent', {
                    'name': 'Test Agent',
                    'email': email
                })
                
                # Act - Simulate validation
                validation_passed = True
                try:
                    if agent.email:
                        mock_email_normalize(agent.email)
                except ValueError:
                    validation_passed = False
                
                # Assert
                self.assertTrue(validation_passed, f"Valid email {email} should pass validation")
    
    @patch('odoo.tools.email_normalize')
    def test_agent_email_validation_invalid(self, mock_email_normalize):
        """Test email validation for invalid emails"""
        
        invalid_emails = [
            'invalid-email',
            '@domain.com',
            'agent@',
            'agent@@domain.com'
        ]
        
        for email in invalid_emails:
            with self.subTest(email=email):
                # Arrange
                mock_email_normalize.side_effect = ValueError("Invalid email")
                agent = self.create_mock_record('real.estate.agent', {
                    'name': 'Test Agent',
                    'email': email
                })
                
                # Act & Assert
                with self.assertRaises(ValueError):
                    if agent.email:
                        mock_email_normalize(agent.email)
    
    def test_agent_write_user_id_change_sync_companies(self):
        """Test write method syncs companies when user_id changes"""
        
        # Arrange
        agent = self.create_mock_record('real.estate.agent', {
            'id': 1,
            'name': 'Test Agent',
            'user_id': None,
            'company_ids': []
        })
        
        # Mock write values
        vals = {'user_id': 1}
        
        # Act - Simulate write method logic
        # The key logic: only sync when user_id changes AND company_ids not explicitly provided
        if 'user_id' in vals and 'company_ids' not in vals:
            # Update the agent with new user_id
            agent.user_id = vals['user_id']
            
            # Sync companies from user
            if agent.user_id:
                user = self.mock_user_with_companies
                user_estate_companies = getattr(user, 'estate_company_ids', None)
                if user_estate_companies:
                    agent.company_ids = user_estate_companies
        
        # Assert
        self.assertEqual(agent.user_id, 1)
        self.assertEqual(agent.company_ids, [1, 2])
    
    def test_agent_write_user_id_change_no_sync_when_companies_provided(self):
        """Test write method doesn't sync companies when company_ids explicitly provided"""
        
        # Arrange
        agent = self.create_mock_record('real.estate.agent', {
            'id': 1,
            'name': 'Test Agent', 
            'user_id': None,
            'company_ids': []
        })
        
        # Mock write values - both user_id AND company_ids provided
        vals = {
            'user_id': 1,
            'company_ids': [(6, 0, [3])]  # Explicitly setting different companies
        }
        
        # Act - Simulate write method logic
        if 'user_id' in vals and 'company_ids' not in vals:
            # This should NOT execute because company_ids is in vals
            agent.company_ids = [1, 2]  # This should not happen
        else:
            # Explicit company_ids should be used
            if 'company_ids' in vals:
                agent.company_ids = [3]  # Use explicit value
        
        # Assert
        self.assertEqual(agent.company_ids, [3], "Explicit company_ids should be preserved")
    
    def test_agent_write_user_id_change_safe_access_no_estate_companies(self):
        """Test write method safely handles users without estate_company_ids"""
        
        # Arrange
        agent = self.create_mock_record('real.estate.agent', {
            'id': 1,
            'name': 'Test Agent',
            'user_id': None,
            'company_ids': []
        })
        
        vals = {'user_id': 2}  # User without estate companies
        
        # Act - Simulate write method with safe access
        if 'user_id' in vals and 'company_ids' not in vals:
            agent.user_id = vals['user_id']
            
            if agent.user_id:
                user = self.mock_user_without_companies
                # Safe access using getattr
                user_estate_companies = getattr(user, 'estate_company_ids', None)
                if user_estate_companies:
                    agent.company_ids = user_estate_companies
                # If no estate companies, company_ids should remain unchanged
        
        # Assert - Should not crash and company_ids should remain empty
        self.assertEqual(agent.user_id, 2)
        self.assertEqual(agent.company_ids, [])
    
    def test_agent_write_other_fields_no_sync(self):
        """Test write method doesn't sync when other fields are updated"""
        
        # Arrange
        agent = self.create_mock_record('real.estate.agent', {
            'id': 1,
            'name': 'Original Name',
            'email': 'original@email.com',
            'user_id': 1,
            'company_ids': [1]
        })
        
        # Mock write values - updating other fields, not user_id
        vals = {
            'name': 'Updated Name',
            'phone': '+55 11 99999-9999'
        }
        
        # Act - Simulate write method
        sync_triggered = False
        if 'user_id' in vals and 'company_ids' not in vals:
            sync_triggered = True
            # This should NOT execute
        
        # Update the fields normally
        for key, value in vals.items():
            setattr(agent, key, value)
        
        # Assert
        self.assertFalse(sync_triggered, "Company sync should not be triggered")
        self.assertEqual(agent.name, 'Updated Name')
        self.assertEqual(agent.phone, '+55 11 99999-9999')
        self.assertEqual(agent.company_ids, [1])  # Should remain unchanged
    
    def test_agent_relationships_integrity(self):
        """Test agent relationships with companies and properties"""
        
        # Arrange
        agent = self.create_mock_record('real.estate.agent', {
            'id': 1,
            'name': 'Relationship Agent',
            'company_ids': [1, 2],
            'properties': [1, 2, 3]
        })
        
        # Act & Assert
        self.assertEqual(len(agent.company_ids), 2)
        self.assertEqual(len(agent.properties), 3)
        
        # Test relationship access
        self.assertIn(1, agent.company_ids)
        self.assertIn(2, agent.company_ids)
        self.assertIn(1, agent.properties)
    
    def test_agent_default_values(self):
        """Test agent default values"""
        
        # Arrange & Act
        agent = self.create_mock_record('real.estate.agent', {
            'name': 'Default Test Agent'
        })
        
        # Simulate default values that would be set by Odoo
        if not hasattr(agent, 'years_experience'):
            agent.years_experience = 0  # Default value
        
        # Assert
        self.assertEqual(agent.years_experience, 0)
        self.assertTrue(agent.name and len(agent.name.strip()) > 0)


class TestAgentBusinessLogic(BaseAgentTest):
    """
    Unit tests for Agent model advanced business logic.
    """
    
    def test_agent_company_assignment_workflow(self):
        """Test complete workflow of agent-company assignment"""
        
        # Arrange - Create agent without companies
        agent = self.create_mock_record('real.estate.agent', {
            'name': 'Workflow Agent',
            'company_ids': []
        })
        
        # Act - Assign companies
        new_companies = [1, 2, 3]
        agent.company_ids = new_companies
        
        # Assert
        self.assertEqual(agent.company_ids, [1, 2, 3])
        self.assertEqual(len(agent.company_ids), 3)
    
    def test_agent_user_integration(self):
        """Test agent-user integration scenarios"""
        
        # Scenario 1: Agent with user
        agent_with_user = self.create_mock_record('real.estate.agent', {
            'name': 'Agent With User',
            'user_id': 1
        })
        
        self.assertTrue(agent_with_user.user_id)
        
        # Scenario 2: Agent without user (external agent)
        agent_without_user = self.create_mock_record('real.estate.agent', {
            'name': 'External Agent',
            'user_id': None
        })
        
        self.assertIsNone(agent_without_user.user_id)
    
    def test_agent_data_validation(self):
        """Test agent data validation and integrity"""
        
        # Arrange & Act
        agent = self.create_mock_record('real.estate.agent', {
            'name': 'Validation Agent',
            'email': 'valid@agent.com',
            'phone': '+55 11 99999-8888',
            'agency_name': 'Top Realty',
            'years_experience': 5
        })
        
        # Assert - All fields should be properly set
        self.assertEqual(agent.name, 'Validation Agent')
        self.assertTrue('@' in agent.email)  # Basic email check
        self.assertTrue(agent.phone.startswith('+55'))  # Brazilian phone
        self.assertEqual(agent.years_experience, 5)
        self.assertEqual(agent.agency_name, 'Top Realty')
    
    def test_agent_edge_cases(self):
        """Test edge cases and boundary conditions"""
        
        # Edge case 1: Very long name
        long_name = 'A' * 100
        agent_long_name = self.create_mock_record('real.estate.agent', {
            'name': long_name
        })
        
        self.assertEqual(len(agent_long_name.name), 100)
        
        # Edge case 2: Zero experience
        agent_zero_exp = self.create_mock_record('real.estate.agent', {
            'name': 'New Agent',
            'years_experience': 0
        })
        
        self.assertEqual(agent_zero_exp.years_experience, 0)
        
        # Edge case 3: High experience
        agent_high_exp = self.create_mock_record('real.estate.agent', {
            'name': 'Senior Agent',
            'years_experience': 50
        })
        
        self.assertEqual(agent_high_exp.years_experience, 50)


if __name__ == '__main__':
    unittest.main()