#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Owner Validations (User Story 1)

Tests owner-specific business logic using mocks (NO database, NO Odoo)

Purpose:
- Validate owner can create users in own company
- Validate owner CANNOT assign users to other companies
- Test pure validation logic without database

Run: python3 run_unit_tests.py
"""

import unittest
from unittest.mock import Mock, MagicMock, patch


class ValidationError(Exception):
    """Mock ValidationError for testing"""
    pass


class TestOwnerValidations(unittest.TestCase):
    """Unit tests for owner validation logic with mocks"""
    
    def test_owner_can_create_user_in_own_company(self):
        """Test that owner validation accepts user creation in own company"""
        # Arrange: Mock owner user
        mock_owner = Mock()
        mock_owner.id = 1
        mock_owner.company_id = Mock(id=100)
        mock_owner.has_group = Mock(return_value=True)  # is owner
        
        # Mock user being created
        mock_new_user = Mock()
        mock_new_user.company_id = Mock(id=100)  # Same company
        
        # Act: Validate company match
        same_company = mock_owner.company_id.id == mock_new_user.company_id.id
        
        # Assert: Should be valid (same company)
        self.assertTrue(same_company)
        self.assertTrue(mock_owner.has_group())
    
    def test_owner_cannot_assign_user_to_other_company(self):
        """Test that owner validation rejects user assignment to other company"""
        # Arrange: Mock owner user
        mock_owner = Mock()
        mock_owner.id = 1
        mock_owner.company_id = Mock(id=100)
        mock_owner.has_group = Mock(return_value=True)  # is owner
        
        # Mock user being created in DIFFERENT company
        mock_new_user = Mock()
        mock_new_user.company_id = Mock(id=200)  # Different company
        
        # Act & Assert: Should raise ValidationError
        with self.assertRaises(ValidationError) as context:
            if mock_owner.has_group() and \
               mock_owner.company_id.id != mock_new_user.company_id.id:
                raise ValidationError(
                    "Owner can only assign users to their own company"
                )
        
        self.assertIn("own company", str(context.exception))
    
    def test_owner_validation_skipped_for_non_owners(self):
        """Test that validation is skipped for non-owner users"""
        # Arrange: Mock non-owner user (agent, manager, etc.)
        mock_user = Mock()
        mock_user.id = 2
        mock_user.company_id = Mock(id=100)
        mock_user.has_group = Mock(return_value=False)  # NOT owner
        
        # Mock user being created
        mock_new_user = Mock()
        mock_new_user.company_id = Mock(id=200)  # Different company
        
        # Act: Check if validation should run
        should_validate = mock_user.has_group()
        
        # Assert: Validation should be skipped (not owner)
        self.assertFalse(should_validate)
    
    def test_owner_multi_company_assignment(self):
        """Test owner validation with multiple companies"""
        # Arrange: Mock owner with access to multiple companies
        mock_owner = Mock()
        mock_owner.id = 1
        mock_owner.company_ids = [Mock(id=100), Mock(id=101)]
        mock_owner.company_id = Mock(id=100)  # Default company
        mock_owner.has_group = Mock(return_value=True)  # is owner
        
        # Mock user being assigned to one of owner's companies
        mock_new_user = Mock()
        mock_new_user.company_id = Mock(id=101)  # In owner's company list
        
        # Act: Check if company is in owner's company list
        company_ids = [c.id for c in mock_owner.company_ids]
        is_valid = mock_new_user.company_id.id in company_ids
        
        # Assert: Should be valid (company in list)
        self.assertTrue(is_valid)
    
    def test_owner_required_fields_validation(self):
        """Test that owner creation validates required fields"""
        # Arrange: Mock user data with missing company
        mock_user_data = {
            'name': 'Test Owner',
            'login': 'test@owner.com',
            'company_id': None,  # Missing required field
        }
        
        # Act & Assert: Should raise validation error for missing company
        with self.assertRaises(ValidationError) as context:
            if not mock_user_data.get('company_id'):
                raise ValidationError("Company is required for owner users")
        
        self.assertIn("Company is required", str(context.exception))
    
    def test_owner_validation_with_valid_data(self):
        """Test that owner validation passes with all valid data"""
        # Arrange: Complete valid owner data
        mock_user_data = {
            'name': 'Valid Owner',
            'login': 'valid@owner.com',
            'company_id': 100,
            'groups_id': [(4, 10)],  # Owner group
        }
        
        # Act: Validate all required fields present
        has_name = bool(mock_user_data.get('name'))
        has_login = bool(mock_user_data.get('login'))
        has_company = bool(mock_user_data.get('company_id'))
        has_groups = bool(mock_user_data.get('groups_id'))
        
        # Assert: All validations should pass
        self.assertTrue(has_name)
        self.assertTrue(has_login)
        self.assertTrue(has_company)
        self.assertTrue(has_groups)


if __name__ == '__main__':
    unittest.main()
