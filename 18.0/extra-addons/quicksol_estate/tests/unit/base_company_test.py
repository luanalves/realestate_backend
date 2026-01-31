# -*- coding: utf-8 -*-
"""
Base test class for Company unit tests.

Provides common fixtures, mock data, and helper methods for testing
Company model business logic without Odoo dependencies.
"""

import unittest
from unittest.mock import Mock, MagicMock
from datetime import date


class BaseCompanyTest(unittest.TestCase):
    """
    Base class for Company unit tests with common fixtures and utilities.
    
    Provides:
    - Mock record creation utilities
    - Standard test data fixtures
    - Common assertions for Company model testing
    """
    
    def setUp(self):
        """Set up common test fixtures."""
        super().setUp()
        
        # Standard mock company data
        self.mock_company_data = {
            'id': 1,
            'name': 'Test Real Estate Company',
            'email': 'contact@testrealestate.com',
            'phone': '+55 11 99999-9999',
            'cnpj': '12.345.678/0001-90',
            'address': 'Test Street, 123',
            'city': 'São Paulo',
            'state': 'SP',
            'zip_code': '01234-567',
            'active': True,
            'create_date': date(2024, 1, 1),
        }
        
        # Mock user data
        self.mock_user_data = {
            'id': 1,
            'name': 'Test User',
            'login': 'testuser@example.com',
            'company_id': Mock(id=1, name='Test Company'),
        }
        
        # Mock environment
        self.mock_env = MagicMock()
        self.mock_env.user = self.create_mock_record('res.users', self.mock_user_data)
        self.mock_env.context = {}
    
    def create_mock_record(self, model_name, data):
        """
        Create a mock Odoo record with the given data.
        
        Args:
            model_name: The Odoo model name (e.g., 'thedevkitchen.estate.company')
            data: Dictionary of field values
            
        Returns:
            Mock object with attributes matching the data keys
        """
        mock = Mock()
        mock._name = model_name
        
        for key, value in data.items():
            setattr(mock, key, value)
        
        # Set up recordset-like behavior
        mock.__bool__ = lambda self: True
        mock.__len__ = lambda self: 1
        mock.ids = [data.get('id', 1)]
        mock.id = data.get('id', 1)
        mock.env = self.mock_env
        
        return mock
    
    def create_mock_recordset(self, model_name, records_data):
        """
        Create a mock Odoo recordset with multiple records.
        
        Args:
            model_name: The Odoo model name
            records_data: List of dictionaries, each representing a record
            
        Returns:
            Mock object behaving like a recordset
        """
        mock = Mock()
        mock._name = model_name
        mock.ids = [r.get('id', i) for i, r in enumerate(records_data)]
        mock.__len__ = lambda self: len(records_data)
        mock.__iter__ = lambda self: iter([
            self.create_mock_record(model_name, r) for r in records_data
        ])
        mock.__bool__ = lambda self: bool(records_data)
        mock.env = self.mock_env
        
        return mock
    
    def assertRecordHasField(self, record, field_name, msg=None):
        """Assert that a mock record has a specific field."""
        self.assertTrue(
            hasattr(record, field_name),
            msg or f"Record should have field '{field_name}'"
        )
    
    def assertRecordFieldEquals(self, record, field_name, expected_value, msg=None):
        """Assert that a record field has the expected value."""
        self.assertRecordHasField(record, field_name)
        actual_value = getattr(record, field_name)
        self.assertEqual(
            actual_value,
            expected_value,
            msg or f"Field '{field_name}' should equal {expected_value}, got {actual_value}"
        )
