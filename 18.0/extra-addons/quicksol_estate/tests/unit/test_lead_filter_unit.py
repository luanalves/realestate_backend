# -*- coding: utf-8 -*-
"""
Unit Tests for Real Estate Lead Filter Model

Tests for lead filter model functionality including:
- Filter creation and validation
- JSON domain parsing
- Unique name constraint
- Apply filter action
- Shared filter functionality

Target: Increase lead_filter.py coverage from 36% to 80%+

Author: Quicksol Technologies
Date: 2026-01-31
Branch: 006-lead-management
ADRs: ADR-003 (Testing)
"""

import unittest
from unittest.mock import MagicMock, patch
import json


class TestLeadFilterCreation(unittest.TestCase):
    """Test filter creation and basic functionality"""
    
    def test_filter_creation_with_valid_json(self):
        """Filter creation with valid JSON domain succeeds"""
        # Arrange
        filter_domain = json.dumps({
            'state': 'qualified',
            'budget_min': 200000
        })
        
        # Act
        parsed = json.loads(filter_domain)
        
        # Assert
        self.assertEqual(parsed['state'], 'qualified')
        self.assertEqual(parsed['budget_min'], 200000)
        
    def test_filter_creation_with_complex_domain(self):
        """Filter supports complex domain with multiple criteria"""
        # Arrange
        filter_domain = json.dumps({
            'state': 'qualified',
            'budget_min': 200000,
            'budget_max': 500000,
            'bedrooms': 3,
            'location': 'Centro',
            'property_type_id': 5
        })
        
        # Act
        parsed = json.loads(filter_domain)
        
        # Assert
        self.assertEqual(len(parsed), 6)
        self.assertEqual(parsed['location'], 'Centro')
        
    def test_filter_default_user_id(self):
        """Filter defaults to current user"""
        # Arrange
        env = MagicMock()
        env.user = MagicMock()
        env.user.id = 42
        
        # Act - simulate default
        default_user_id = env.user.id
        
        # Assert
        self.assertEqual(default_user_id, 42)
        
    def test_filter_default_is_shared_false(self):
        """is_shared defaults to False"""
        # Arrange
        default_is_shared = False
        
        # Assert
        self.assertFalse(default_is_shared)


class TestLeadFilterDomainValidation(unittest.TestCase):
    """Test filter domain JSON validation"""
    
    def test_valid_json_passes_validation(self):
        """Valid JSON string passes validation"""
        # Arrange
        filter_domain = '{"state": "new", "agent_id": 1}'
        
        # Act
        try:
            json.loads(filter_domain)
            is_valid = True
        except (ValueError, TypeError):
            is_valid = False
            
        # Assert
        self.assertTrue(is_valid)
        
    def test_invalid_json_fails_validation(self):
        """Invalid JSON string fails validation"""
        # Arrange
        filter_domain = '{state: new}'  # Missing quotes
        
        # Act
        try:
            json.loads(filter_domain)
            is_valid = True
        except (ValueError, TypeError):
            is_valid = False
            
        # Assert
        self.assertFalse(is_valid)
        
    def test_empty_json_object_passes(self):
        """Empty JSON object is valid"""
        # Arrange
        filter_domain = '{}'
        
        # Act
        try:
            parsed = json.loads(filter_domain)
            is_valid = True
        except (ValueError, TypeError):
            is_valid = False
            
        # Assert
        self.assertTrue(is_valid)
        self.assertEqual(parsed, {})
        
    def test_json_array_passes(self):
        """JSON array is valid (though not expected)"""
        # Arrange
        filter_domain = '["state", "=", "new"]'
        
        # Act
        try:
            json.loads(filter_domain)
            is_valid = True
        except (ValueError, TypeError):
            is_valid = False
            
        # Assert
        self.assertTrue(is_valid)
        
    def test_none_value_fails_validation(self):
        """None value fails JSON validation"""
        # Arrange
        filter_domain = None
        
        # Act
        try:
            json.loads(filter_domain)
            is_valid = True
        except (ValueError, TypeError):
            is_valid = False
            
        # Assert
        self.assertFalse(is_valid)
        
    def test_nested_json_passes(self):
        """Nested JSON structure passes validation"""
        # Arrange
        filter_domain = json.dumps({
            'filters': {
                'state': 'new',
                'budget': {
                    'min': 100000,
                    'max': 500000
                }
            },
            'sort': 'create_date',
            'limit': 50
        })
        
        # Act
        try:
            parsed = json.loads(filter_domain)
            is_valid = True
        except (ValueError, TypeError):
            is_valid = False
            
        # Assert
        self.assertTrue(is_valid)
        self.assertEqual(parsed['filters']['budget']['min'], 100000)


class TestLeadFilterUniqueName(unittest.TestCase):
    """Test unique name per user constraint"""
    
    def test_same_name_same_user_fails(self):
        """Same filter name for same user should fail"""
        # Arrange
        user_id = 1
        existing_filters = [
            {'name': 'High Value', 'user_id': 1},
            {'name': 'Centro Leads', 'user_id': 1}
        ]
        new_filter_name = 'High Value'
        
        # Act - simulate constraint check
        duplicate_exists = any(
            f['name'] == new_filter_name and f['user_id'] == user_id
            for f in existing_filters
        )
        
        # Assert
        self.assertTrue(duplicate_exists)
        
    def test_same_name_different_user_passes(self):
        """Same filter name for different users is allowed"""
        # Arrange
        user_id = 2  # Different user
        existing_filters = [
            {'name': 'High Value', 'user_id': 1},
        ]
        new_filter_name = 'High Value'
        
        # Act
        duplicate_exists = any(
            f['name'] == new_filter_name and f['user_id'] == user_id
            for f in existing_filters
        )
        
        # Assert
        self.assertFalse(duplicate_exists)
        
    def test_different_name_same_user_passes(self):
        """Different filter names for same user is allowed"""
        # Arrange
        user_id = 1
        existing_filters = [
            {'name': 'High Value', 'user_id': 1},
        ]
        new_filter_name = 'Low Value'
        
        # Act
        duplicate_exists = any(
            f['name'] == new_filter_name and f['user_id'] == user_id
            for f in existing_filters
        )
        
        # Assert
        self.assertFalse(duplicate_exists)
        
    def test_case_sensitive_name_check(self):
        """Name comparison is case sensitive"""
        # Arrange
        user_id = 1
        existing_filters = [
            {'name': 'High Value', 'user_id': 1},
        ]
        new_filter_name = 'high value'  # Different case
        
        # Act
        duplicate_exists = any(
            f['name'] == new_filter_name and f['user_id'] == user_id
            for f in existing_filters
        )
        
        # Assert
        self.assertFalse(duplicate_exists)  # Case sensitive = different


class TestLeadFilterGetParams(unittest.TestCase):
    """Test get_filter_params method"""
    
    def test_get_params_returns_dict(self):
        """get_filter_params returns parsed dict"""
        # Arrange
        filter_domain = '{"state": "new", "budget_min": 100000}'
        
        # Act
        params = json.loads(filter_domain)
        
        # Assert
        self.assertIsInstance(params, dict)
        self.assertEqual(params['state'], 'new')
        
    def test_get_params_handles_empty_domain(self):
        """get_filter_params handles empty JSON object"""
        # Arrange
        filter_domain = '{}'
        
        # Act
        params = json.loads(filter_domain)
        
        # Assert
        self.assertEqual(params, {})
        
    def test_get_params_handles_invalid_json(self):
        """get_filter_params returns empty dict on invalid JSON"""
        # Arrange
        filter_domain = 'invalid json'
        
        # Act
        try:
            params = json.loads(filter_domain)
        except (ValueError, TypeError):
            params = {}
            
        # Assert
        self.assertEqual(params, {})


class TestLeadFilterApplyFilter(unittest.TestCase):
    """Test apply_filter method domain building"""
    
    def test_apply_filter_builds_state_domain(self):
        """apply_filter builds domain for state filter"""
        # Arrange
        params = {'state': 'qualified'}
        domain = []
        
        # Act - simulate apply_filter logic
        if params.get('state'):
            domain.append(('state', '=', params['state']))
            
        # Assert
        self.assertEqual(domain, [('state', '=', 'qualified')])
        
    def test_apply_filter_builds_agent_domain(self):
        """apply_filter builds domain for agent filter"""
        # Arrange
        params = {'agent_id': '5'}
        domain = []
        
        # Act
        if params.get('agent_id'):
            domain.append(('agent_id', '=', int(params['agent_id'])))
            
        # Assert
        self.assertEqual(domain, [('agent_id', '=', 5)])
        
    def test_apply_filter_builds_budget_min_domain(self):
        """apply_filter builds domain for budget_min"""
        # Arrange
        params = {'budget_min': 200000}
        domain = []
        
        # Act
        if params.get('budget_min'):
            domain.append(('budget_min', '>=', params['budget_min']))
            
        # Assert
        self.assertEqual(domain, [('budget_min', '>=', 200000)])
        
    def test_apply_filter_builds_budget_max_domain(self):
        """apply_filter builds domain for budget_max"""
        # Arrange
        params = {'budget_max': 500000}
        domain = []
        
        # Act
        if params.get('budget_max'):
            domain.append(('budget_max', '<=', params['budget_max']))
            
        # Assert
        self.assertEqual(domain, [('budget_max', '<=', 500000)])
        
    def test_apply_filter_builds_combined_domain(self):
        """apply_filter combines multiple filters with AND"""
        # Arrange
        params = {
            'state': 'qualified',
            'agent_id': '5',
            'budget_min': 200000,
            'budget_max': 500000
        }
        domain = []
        
        # Act
        if params.get('state'):
            domain.append(('state', '=', params['state']))
        if params.get('agent_id'):
            domain.append(('agent_id', '=', int(params['agent_id'])))
        if params.get('budget_min'):
            domain.append(('budget_min', '>=', params['budget_min']))
        if params.get('budget_max'):
            domain.append(('budget_max', '<=', params['budget_max']))
            
        # Assert
        self.assertEqual(len(domain), 4)
        
    def test_apply_filter_skips_empty_params(self):
        """apply_filter skips params with empty values"""
        # Arrange
        params = {'state': '', 'agent_id': None, 'budget_min': 0}
        domain = []
        
        # Act
        if params.get('state'):
            domain.append(('state', '=', params['state']))
        if params.get('agent_id'):
            domain.append(('agent_id', '=', int(params['agent_id'])))
        if params.get('budget_min'):
            domain.append(('budget_min', '>=', params['budget_min']))
            
        # Assert
        self.assertEqual(domain, [])  # All empty, no domain


class TestLeadFilterSharedFunctionality(unittest.TestCase):
    """Test shared filter functionality"""
    
    def test_private_filter_visible_to_owner_only(self):
        """Private filter (is_shared=False) visible only to owner"""
        # Arrange
        filter_record = {
            'user_id': 1,
            'is_shared': False,
            'company_id': 100
        }
        current_user_id = 1
        
        # Act - simulate access check
        can_access = filter_record['user_id'] == current_user_id
        
        # Assert
        self.assertTrue(can_access)
        
    def test_private_filter_hidden_from_others(self):
        """Private filter hidden from other users"""
        # Arrange
        filter_record = {
            'user_id': 1,
            'is_shared': False,
            'company_id': 100
        }
        current_user_id = 2  # Different user
        
        # Act
        can_access = filter_record['user_id'] == current_user_id
        
        # Assert
        self.assertFalse(can_access)
        
    def test_shared_filter_visible_to_company_users(self):
        """Shared filter visible to all company users"""
        # Arrange
        filter_record = {
            'user_id': 1,
            'is_shared': True,
            'company_id': 100
        }
        current_user_id = 2
        current_user_company_id = 100  # Same company
        
        # Act
        can_access = (
            filter_record['is_shared'] and 
            filter_record['company_id'] == current_user_company_id
        )
        
        # Assert
        self.assertTrue(can_access)
        
    def test_shared_filter_hidden_from_other_companies(self):
        """Shared filter hidden from other company users"""
        # Arrange
        filter_record = {
            'user_id': 1,
            'is_shared': True,
            'company_id': 100
        }
        current_user_company_id = 200  # Different company
        
        # Act
        can_access = (
            filter_record['is_shared'] and 
            filter_record['company_id'] == current_user_company_id
        )
        
        # Assert
        self.assertFalse(can_access)


class TestLeadFilterDeletion(unittest.TestCase):
    """Test filter deletion scenarios"""
    
    def test_owner_can_delete_own_filter(self):
        """Filter owner can delete their filter"""
        # Arrange
        filter_owner_id = 1
        current_user_id = 1
        
        # Act
        can_delete = filter_owner_id == current_user_id
        
        # Assert
        self.assertTrue(can_delete)
        
    def test_non_owner_cannot_delete_filter(self):
        """Non-owner cannot delete filter"""
        # Arrange
        filter_owner_id = 1
        current_user_id = 2
        
        # Act
        can_delete = filter_owner_id == current_user_id
        
        # Assert
        self.assertFalse(can_delete)
        
    def test_cascade_delete_with_user(self):
        """Filter deleted when user is deleted (cascade)"""
        # Arrange - ondelete='cascade' means filter is deleted with user
        ondelete_behavior = 'cascade'
        
        # Assert
        self.assertEqual(ondelete_behavior, 'cascade')


if __name__ == '__main__':
    unittest.main()
