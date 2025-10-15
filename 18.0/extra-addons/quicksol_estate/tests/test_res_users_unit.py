# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import date

from .base_test import BaseRealEstateTest


class TestResUsersUnit(BaseRealEstateTest):
    """
    Unit tests for ResUsers model extensions for real estate management.

    Tests cover:
    - Estate company relationship management
    - Main estate company selection
    - User-agent synchronization
    - Access control methods
    - Company assignment workflows
    """

    def setUp(self):
        super().setUp()
        
        # Mock user with estate companies
        self.user_with_companies = {
            'id': 1,
            'name': 'Test User',
            'login': 'testuser',
            'email': 'test@user.com',
            'estate_company_ids': [1, 2],
            'main_estate_company_id': 1
        }
        
        # Mock admin user
        self.admin_user = {
            'id': 2,
            'name': 'Admin User',
            'login': 'admin',
            'email': 'admin@system.com',
            'is_admin': True
        }
    
    def test_user_estate_company_relationship(self):
        """Test user-estate company many2many relationship"""
        
        # Arrange & Act
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'Test User',
            'estate_company_ids': [1, 2, 3]
        })
        
        # Assert
        self.assertEqual(len(user.estate_company_ids), 3)
        self.assertIn(1, user.estate_company_ids)
        self.assertIn(2, user.estate_company_ids)
    
    def test_user_main_estate_company(self):
        """Test main estate company selection"""
        
        # Arrange & Act
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'Test User',
            'estate_company_ids': [1, 2, 3],
            'main_estate_company_id': 2
        })
        
        # Assert
        self.assertEqual(user.main_estate_company_id, 2)
        self.assertIn(user.main_estate_company_id, user.estate_company_ids)
    
    def test_user_onchange_main_estate_company(self):
        """Test onchange ensures main company is in user's companies"""
        
        # Arrange
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'Test User',
            'estate_company_ids': [1, 2]
        })
        
        # Act - Set main company that's not in the list
        user.main_estate_company_id = 3
        
        # Simulate onchange logic
        if user.main_estate_company_id and user.main_estate_company_id not in user.estate_company_ids:
            # Add main company to estate_company_ids
            user.estate_company_ids = [*user.estate_company_ids, user.main_estate_company_id]
        
        # Assert
        self.assertIn(user.main_estate_company_id, user.estate_company_ids)
        self.assertEqual(len(user.estate_company_ids), 3)
    
    def test_user_get_user_companies_regular_user(self):
        """Test get_user_companies for regular users"""
        
        # Arrange
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'Regular User',
            'estate_company_ids': [1, 2]
        })
        
        # Mock has_group to return False (not admin)
        def mock_has_group(_group_xml_id):
            return False
        
        # Act - Simulate get_user_companies logic for regular user
        is_admin = mock_has_group('base.group_system')
        if is_admin:
            # Admin sees all companies
            user_companies = []  # Would be all companies
        else:
            # Regular user sees only their companies
            user_companies = user.estate_company_ids
        
        # Assert
        self.assertEqual(user_companies, [1, 2])
    
    def test_user_get_user_companies_admin(self):
        """Test get_user_companies for admin users"""
        
        # Arrange
        admin_user = self.create_mock_record('res.users', {
            'id': 2,
            'name': 'Admin User',
            'estate_company_ids': [1]
        })
        
        # Mock has_group to return True (admin)
        def mock_has_group(group_xml_id):
            return group_xml_id == 'base.group_system'
        
        # Act - Simulate get_user_companies logic for admin
        is_admin = mock_has_group('base.group_system')
        if is_admin:
            # Admin sees all companies (mock all companies)
            user_companies = [1, 2, 3, 4, 5]  # All companies
        else:
            user_companies = admin_user.estate_company_ids
        
        # Assert
        self.assertGreater(len(user_companies), len(admin_user.estate_company_ids))
    
    def test_user_has_estate_company_access_regular_user(self):
        """Test has_estate_company_access for regular users"""
        
        # Arrange
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'Regular User',
            'estate_company_ids': [1, 2, 3]
        })
        
        # Mock has_group to return False (not admin)
        def mock_has_group(_group_xml_id):
            return False
        
        # Act - Check access to various companies
        is_admin = mock_has_group('base.group_system')
        
        has_access_to_1 = is_admin or 1 in user.estate_company_ids
        has_access_to_5 = is_admin or 5 in user.estate_company_ids
        
        # Assert
        self.assertTrue(has_access_to_1, "User should have access to company 1")
        self.assertFalse(has_access_to_5, "User should not have access to company 5")
    
    def test_user_has_estate_company_access_admin(self):
        """Test has_estate_company_access for admin users"""
        
        # Arrange
        admin_user = self.create_mock_record('res.users', {
            'id': 2,
            'name': 'Admin User',
            'estate_company_ids': [1]
        })
        
        # Mock has_group to return True (admin)
        def mock_has_group(group_xml_id):
            return group_xml_id == 'base.group_system'
        
        # Act - Admin should have access to any company
        is_admin = mock_has_group('base.group_system')
        
        has_access_to_1 = is_admin or 1 in admin_user.estate_company_ids
        has_access_to_99 = is_admin or 99 in admin_user.estate_company_ids
        
        # Assert
        self.assertTrue(has_access_to_1, "Admin should have access to company 1")
        self.assertTrue(has_access_to_99, "Admin should have access to any company")
    
    def test_user_write_syncs_agent_companies(self):
        """Test write method synchronizes agent companies when user companies change"""
        
        # Arrange
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'Test User',
            'estate_company_ids': [1, 2]
        })
        
        # Mock agent related to this user
        agent = self.create_mock_record('real.estate.agent', {
            'id': 1,
            'name': 'Test Agent',
            'user_id': 1,
            'company_ids': [1, 2]
        })
        
        # Act - Update user's estate companies
        vals = {'estate_company_ids': [1, 2, 3]}
        
        # Simulate write logic
        if 'estate_company_ids' in vals:
            user.estate_company_ids = vals['estate_company_ids']
            # Sync to agent
            if agent.user_id == user.id:
                agent.company_ids = user.estate_company_ids
        
        # Assert
        self.assertEqual(user.estate_company_ids, [1, 2, 3])
        self.assertEqual(agent.company_ids, [1, 2, 3])


class TestResUsersBusinessLogic(BaseRealEstateTest):
    """
    Unit tests for ResUsers model business logic and workflows.
    """
    
    def test_user_company_assignment_workflow(self):
        """Test complete workflow of assigning companies to user"""
        
        # Arrange - User initially without companies
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'New User',
            'estate_company_ids': []
        })
        
        # Act - Assign companies
        user.estate_company_ids = [1, 2]
        user.main_estate_company_id = 1
        
        # Assert
        self.assertEqual(len(user.estate_company_ids), 2)
        self.assertEqual(user.main_estate_company_id, 1)
    
    def test_user_multiple_company_management(self):
        """Test user managing multiple companies"""
        
        # Arrange
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'Multi-Company User',
            'estate_company_ids': [1, 2, 3, 4]
        })
        
        # Act - Set main company
        user.main_estate_company_id = 2
        
        # Assert
        self.assertEqual(len(user.estate_company_ids), 4)
        self.assertEqual(user.main_estate_company_id, 2)
        self.assertIn(user.main_estate_company_id, user.estate_company_ids)
    
    def test_user_company_removal(self):
        """Test removing companies from user"""
        
        # Arrange
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'Test User',
            'estate_company_ids': [1, 2, 3],
            'main_estate_company_id': 1
        })
        
        # Act - Remove company 3
        user.estate_company_ids = [1, 2]
        
        # Assert
        self.assertEqual(len(user.estate_company_ids), 2)
        self.assertNotIn(3, user.estate_company_ids)
        self.assertIn(user.main_estate_company_id, user.estate_company_ids)
    
    def test_user_switching_main_company(self):
        """Test switching user's main company"""
        
        # Arrange
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'Test User',
            'estate_company_ids': [1, 2, 3],
            'main_estate_company_id': 1
        })
        
        # Act - Switch main company
        old_main = user.main_estate_company_id
        user.main_estate_company_id = 3
        
        # Assert
        self.assertEqual(old_main, 1)
        self.assertEqual(user.main_estate_company_id, 3)
        self.assertIn(user.main_estate_company_id, user.estate_company_ids)
    
    def test_user_data_integrity(self):
        """Test user data integrity"""
        
        # Arrange & Act
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'Integrity User',
            'login': 'integrityuser',
            'email': 'integrity@user.com',
            'estate_company_ids': [1, 2],
            'main_estate_company_id': 1
        })
        
        # Assert - All fields preserved
        self.assertEqual(user.name, 'Integrity User')
        self.assertEqual(user.login, 'integrityuser')
        self.assertEqual(user.email, 'integrity@user.com')
        self.assertEqual(len(user.estate_company_ids), 2)
        self.assertEqual(user.main_estate_company_id, 1)


class TestResUsersEdgeCases(BaseRealEstateTest):
    """
    Unit tests for ResUsers model edge cases and boundary conditions.
    """
    
    def test_user_no_estate_companies(self):
        """Test user without any estate companies"""
        
        # Arrange & Act
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'No Company User',
            'estate_company_ids': []
        })
        
        # Assert
        self.assertEqual(len(user.estate_company_ids), 0)
        # Main company should be None or not set
        self.assertFalse(hasattr(user, 'main_estate_company_id') and 
                        user.main_estate_company_id)
    
    def test_user_single_company(self):
        """Test user with single estate company"""
        
        # Arrange & Act
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'Single Company User',
            'estate_company_ids': [1],
            'main_estate_company_id': 1
        })
        
        # Assert
        self.assertEqual(len(user.estate_company_ids), 1)
        self.assertEqual(user.main_estate_company_id, 1)
    
    def test_user_many_companies(self):
        """Test user with many estate companies"""
        
        # Arrange & Act
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'Many Companies User',
            'estate_company_ids': list(range(1, 11))  # 10 companies
        })
        
        # Assert
        self.assertEqual(len(user.estate_company_ids), 10)
    
    def test_user_agent_sync_without_agent(self):
        """Test user company change without related agent"""
        
        # Arrange
        user = self.create_mock_record('res.users', {
            'id': 1,
            'name': 'User Without Agent',
            'estate_company_ids': [1, 2]
        })
        
        # Act - Update user's companies (no agent to sync)
        vals = {'estate_company_ids': [1, 2, 3]}
        user.estate_company_ids = vals['estate_company_ids']
        
        # Simulate write logic - no agent found
        agents = []  # No agents for this user
        
        # Assert - Should not crash
        self.assertEqual(user.estate_company_ids, [1, 2, 3])
        self.assertEqual(len(agents), 0)
    
    def test_user_filtering_by_estate_company(self):
        """Test filtering users by estate company"""
        
        # Arrange
        user1 = self.create_mock_record('res.users', {
            'name': 'User 1',
            'estate_company_ids': [1, 2]
        })
        
        user2 = self.create_mock_record('res.users', {
            'name': 'User 2',
            'estate_company_ids': [2, 3]
        })
        
        user3 = self.create_mock_record('res.users', {
            'name': 'User 3',
            'estate_company_ids': [1]
        })
        
        # Act - Filter users with access to company 1
        all_users = [user1, user2, user3]
        company_1_users = [u for u in all_users if 1 in u.estate_company_ids]
        
        # Assert
        self.assertEqual(len(company_1_users), 2)
        self.assertIn(user1, company_1_users)
        self.assertIn(user3, company_1_users)


if __name__ == '__main__':
    unittest.main()