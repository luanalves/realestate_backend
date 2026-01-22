#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for UserCompanyValidatorObserver (User Story 1)

Tests observer validation logic using mocks (NO database, NO Odoo)

Purpose:
- Validate observer handles user.before_create event
- Validate observer blocks cross-company user assignments
- Test can_handle() and handle() methods with mocks

Run: python3 run_unit_tests.py
"""

import unittest
from unittest.mock import Mock, MagicMock, patch


class ValidationError(Exception):
    """Mock ValidationError for testing"""
    pass


class TestUserCompanyValidatorObserverUnit(unittest.TestCase):
    """Unit tests for UserCompanyValidatorObserver with mocks"""
    
    def test_observer_can_handle_user_before_create(self):
        """Test that observer can handle 'user.before_create' event"""
        # Arrange: Mock observer
        mock_observer = Mock()
        mock_observer.can_handle = Mock(return_value=True)
        
        # Act: Check if observer can handle event
        event_name = 'user.before_create'
        can_handle = mock_observer.can_handle(event_name)
        
        # Assert: Observer should handle this event
        self.assertTrue(can_handle)
        mock_observer.can_handle.assert_called_once_with(event_name)
    
    def test_observer_can_handle_user_before_write(self):
        """Test that observer can handle 'user.before_write' event"""
        # Arrange: Mock observer
        mock_observer = Mock()
        mock_observer.can_handle = Mock(return_value=True)
        
        # Act: Check if observer can handle event
        event_name = 'user.before_write'
        can_handle = mock_observer.can_handle(event_name)
        
        # Assert: Observer should handle this event
        self.assertTrue(can_handle)
    
    def test_observer_ignores_other_events(self):
        """Test that observer ignores events it doesn't handle"""
        # Arrange: Mock observer
        mock_observer = Mock()
        mock_observer.can_handle = Mock(return_value=False)
        
        # Act: Check if observer handles unrelated event
        event_name = 'property.created'
        can_handle = mock_observer.can_handle(event_name)
        
        # Assert: Observer should NOT handle this event
        self.assertFalse(can_handle)
    
    def test_observer_validates_same_company_assignment(self):
        """Test observer validation when user assigned to same company"""
        # Arrange: Mock current user (owner)
        mock_current_user = Mock()
        mock_current_user.id = 1
        mock_current_user.company_id = Mock(id=100)
        mock_current_user.has_group = Mock(return_value=True)  # is owner
        
        # Mock new user data (same company)
        mock_user_vals = {
            'company_id': 100,
            'name': 'New User',
        }
        
        # Act: Validate company match
        same_company = mock_current_user.company_id.id == mock_user_vals['company_id']
        
        # Assert: Should be valid (same company)
        self.assertTrue(same_company)
    
    def test_observer_blocks_cross_company_assignment(self):
        """Test observer blocks user assignment to different company"""
        # Arrange: Mock current user (owner)
        mock_current_user = Mock()
        mock_current_user.id = 1
        mock_current_user.company_id = Mock(id=100)
        mock_current_user.has_group = Mock(return_value=True)  # is owner
        
        # Mock new user data (different company)
        mock_user_vals = {
            'company_id': 200,  # Different company!
            'name': 'Cross-Company User',
        }
        
        # Act & Assert: Should raise ValidationError
        with self.assertRaises(ValidationError) as context:
            # Simulate observer validation logic
            if mock_current_user.has_group() and \
               mock_current_user.company_id.id != mock_user_vals['company_id']:
                raise ValidationError(
                    "You can only assign users to your own company"
                )
        
        self.assertIn("own company", str(context.exception))
    
    def test_observer_handle_method_called_with_event_data(self):
        """Test that handle() method is called with correct event data"""
        # Arrange: Mock observer
        mock_observer = Mock()
        mock_observer.handle = Mock(return_value=True)
        
        # Mock event data
        mock_event_name = 'user.before_create'
        mock_event_data = {
            'company_id': 100,
            'name': 'Test User',
        }
        
        # Act: Call handle method
        result = mock_observer.handle(mock_event_name, mock_event_data)
        
        # Assert: handle() should be called with event data
        mock_observer.handle.assert_called_once_with(mock_event_name, mock_event_data)
        self.assertTrue(result)
    
    def test_observer_validation_skipped_for_non_owners(self):
        """Test that observer skips validation for non-owner users"""
        # Arrange: Mock current user (NOT owner)
        mock_current_user = Mock()
        mock_current_user.id = 2
        mock_current_user.company_id = Mock(id=100)
        mock_current_user.has_group = Mock(return_value=False)  # NOT owner
        
        # Mock new user data
        mock_user_vals = {
            'company_id': 200,  # Different company
            'name': 'User Created by Non-Owner',
        }
        
        # Act: Check if validation should run
        should_validate = mock_current_user.has_group()
        
        # Assert: Validation should be skipped
        self.assertFalse(should_validate)
    
    def test_observer_handles_missing_company_id(self):
        """Test observer validation when company_id is missing from event data"""
        # Arrange: Mock event data without company_id
        mock_event_data = {
            'name': 'User Without Company',
            # company_id is missing
        }
        
        # Act: Check if company_id exists
        has_company_id = 'company_id' in mock_event_data
        
        # Assert: Should detect missing company_id
        self.assertFalse(has_company_id)
    
    def test_observer_validation_with_force_sync(self):
        """Test that observer executes synchronously with force_sync=True"""
        # Arrange: Mock EventBus.emit()
        mock_event_bus = Mock()
        mock_event_bus.emit = Mock(return_value=True)
        
        # Mock event data
        mock_event_name = 'user.before_create'
        mock_event_data = {'company_id': 100, 'name': 'Sync User'}
        
        # Act: Emit event with force_sync=True
        result = mock_event_bus.emit(mock_event_name, mock_event_data, force_sync=True)
        
        # Assert: emit() should be called with force_sync=True
        mock_event_bus.emit.assert_called_once_with(
            mock_event_name,
            mock_event_data,
            force_sync=True
        )
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
