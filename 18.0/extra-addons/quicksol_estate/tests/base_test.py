# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from datetime import date, datetime
import re


class BaseRealEstateTest(unittest.TestCase):
    """
    Base class for Real Estate unit tests with comprehensive mocking.
    
    This class provides:
    - Mock Odoo environment and models
    - Common test data
    - Helper methods for creating mock records
    - Utilities for testing validations and business logic
    """
    
    def setUp(self):
        """Setup common mocks and test data for all tests"""
        super().setUp()
        
        # Mock Odoo environment
        self.env = Mock()
        self.cr = Mock()  # Database cursor mock
        self.uid = 1      # User ID mock
        self.context = {}  # Context mock
        
        # Mock recordset behaviors
        self.empty_recordset = Mock()
        self.empty_recordset.__bool__ = Mock(return_value=False)
        self.empty_recordset.__len__ = Mock(return_value=0)
        self.empty_recordset.exists = Mock(return_value=self.empty_recordset)
        
        # Setup test data
        self._setup_test_data()
        
        # Setup model mocks
        self._setup_model_mocks()
    
    def _setup_test_data(self):
        """Initialize common test data"""
        
        # Company test data
        self.mock_company_data = {
            'id': 1,
            'name': 'Test Real Estate Company',
            'email': 'test@company.com',
            'phone': '+55 11 3333-4444',
            'cnpj': '12.345.678/0001-90',
            'address': 'Test Address, 123',
            'city': 'São Paulo',
            'state_id': cls.env['real.estate.state'].search([('code', '=', 'SP')], limit=1).id,
            'zip_code': '01234-567',
            'active': True,
            'property_count': 5,
            'agent_count': 3,
            'lease_count': 2,
            'sale_count': 1
        }
        
        # User test data
        self.mock_user_data = {
            'id': 1,
            'name': 'Test User',
            'login': 'testuser',
            'email': 'test@user.com',
            'estate_company_ids': [1],
            'main_estate_company_id': 1
        }
        
        # Agent test data
        self.mock_agent_data = {
            'id': 1,
            'name': 'Test Agent',
            'email': 'agent@test.com',
            'phone': '+55 11 99999-9999',
            'user_id': 1,
            'company_ids': [1],
            'agency_name': 'Top Real Estate',
            'years_experience': 5,
            'properties': [1, 2]
        }
        
        # Tenant test data  
        self.mock_tenant_data = {
            'id': 1,
            'name': 'Test Tenant',
            'email': 'tenant@test.com',
            'phone': '+55 11 88888-8888',
            'company_ids': [1],
            'occupation': 'Engineer',
            'birthdate': date(1990, 5, 15),
            'leases': [1]
        }
        
        # Property test data
        self.mock_property_data = {
            'id': 1,
            'name': 'Test Property',
            'price': 250000.00,
            'currency_id': 1,  # BRL
            'num_rooms': 3,
            'num_bathrooms': 2,
            'num_floors': 1,
            'area': 120.5,
            'address': 'Property Address, 456',
            'city': 'São Paulo',
            'country_id': 1,  # Brazil
            'status': 'available',
            'condition': 'good',
            'company_ids': [1],
            'agent_id': 1
        }
        
        # Lease test data
        self.mock_lease_data = {
            'id': 1,
            'property_id': 1,
            'tenant_id': 1,
            'company_ids': [1],
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
            'rent_amount': 2500.00
        }
        
        # Sale test data
        self.mock_sale_data = {
            'id': 1,
            'property_id': 1,
            'buyer_name': 'Test Buyer',
            'company_ids': [1],
            'sale_date': date(2024, 6, 15),
            'sale_price': 250000.00
        }
    
    def _setup_model_mocks(self):
        """Setup mock models with common methods"""
        
        # Company model mock
        self.company_model = Mock()
        self.company_model._name = 'thedevkitchen.estate.company'
        self.company_model.create = Mock()
        self.company_model.search = Mock()
        self.company_model.browse = Mock()
        
        # Agent model mock  
        self.agent_model = Mock()
        self.agent_model._name = 'real.estate.agent'
        self.agent_model.create = Mock()
        self.agent_model.search = Mock()
        self.agent_model.browse = Mock()
        
        # Setup env model access
        self.env.__getitem__ = Mock(side_effect=self._get_model_mock)
    
    def _get_model_mock(self, model_name):
        """Return appropriate model mock based on model name"""
        model_mapping = {
            'thedevkitchen.estate.company': self.company_model,
            'real.estate.agent': self.agent_model,
            'real.estate.tenant': Mock(),
            'real.estate.property': Mock(),
            'real.estate.lease': Mock(),
            'real.estate.sale': Mock(),
            'res.users': Mock()
        }
        return model_mapping.get(model_name, Mock())
    
    def create_mock_record(self, model_name, data, methods=None):
        """
        Create a mock record with specified data and methods.
        
        Args:
            model_name (str): Name of the Odoo model
            data (dict): Field data for the record
            methods (dict): Optional custom methods to add
            
        Returns:
            Mock: Configured mock record
        """
        record = Mock()
        
        # Add data as attributes
        for key, value in data.items():
            setattr(record, key, value)
        
        # Add custom methods if provided
        if methods:
            for method_name, method_mock in methods.items():
                setattr(record, method_name, method_mock)
        
        # Standard recordset methods
        record._name = model_name
        record.exists = Mock(return_value=record)
        record.ensure_one = Mock(return_value=None)
        record.write = Mock(return_value=True)
        record.unlink = Mock(return_value=True)
        record.copy = Mock(return_value=record)
        
        # Mock recordset behaviors
        record.__bool__ = Mock(return_value=True)
        record.__len__ = Mock(return_value=1)
        record.__iter__ = Mock(return_value=iter([record]))
        
        return record
    
    def create_mock_recordset(self, model_name, records_data):
        """
        Create a mock recordset with multiple records.
        
        Args:
            model_name (str): Name of the Odoo model
            records_data (list): List of data dicts for each record
            
        Returns:
            Mock: Configured mock recordset
        """
        records = []
        for data in records_data:
            records.append(self.create_mock_record(model_name, data))
        
        recordset = Mock()
        recordset._name = model_name
        recordset.__bool__ = Mock(return_value=len(records) > 0)
        recordset.__len__ = Mock(return_value=len(records))
        recordset.__iter__ = Mock(return_value=iter(records))
        recordset.exists = Mock(return_value=recordset if records else self.empty_recordset)
        
        return recordset
    
    def create_mock_validation_error(self, message="Validation Error"):
        """Create a mock ValidationError for testing"""
        from odoo.exceptions import ValidationError
        return ValidationError(message)
    
    def assert_validation_error(self, callable_obj, *args, **kwargs):
        """
        Helper to assert that a ValidationError is raised.
        
        Args:
            callable_obj: Function/method to call
            *args: Arguments for the callable
            **kwargs: Keyword arguments for the callable
        """
        from odoo.exceptions import ValidationError
        
        with self.assertRaises(ValidationError):
            callable_obj(*args, **kwargs)
    
    def assert_no_validation_error(self, callable_obj, *args, **kwargs):
        """
        Helper to assert that no ValidationError is raised.
        
        Args:
            callable_obj: Function/method to call
            *args: Arguments for the callable  
            **kwargs: Keyword arguments for the callable
        """
        from odoo.exceptions import ValidationError
        
        try:
            callable_obj(*args, **kwargs)
        except ValidationError:
            self.fail("ValidationError was raised when it shouldn't have been")
    
    def mock_email_validation(self, email, should_be_valid=True):
        """
        Mock email validation behavior for testing.
        
        Args:
            email (str): Email to validate
            should_be_valid (bool): Whether email should be considered valid
            
        Returns:
            bool: True if email passes validation
        """
        if should_be_valid:
            # Simple email regex for testing
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(pattern, email))
        else:
            return False
    
    def mock_cnpj_validation(self, cnpj, should_be_valid=True):
        """
        Mock CNPJ validation behavior for testing.
        
        Args:
            cnpj (str): CNPJ to validate
            should_be_valid (bool): Whether CNPJ should be considered valid
            
        Returns:
            bool: True if CNPJ passes validation
        """
        if should_be_valid:
            # Remove formatting
            clean_cnpj = re.sub(r'[^\d]', '', cnpj)
            return len(clean_cnpj) == 14 and clean_cnpj.isdigit()
        else:
            return False
    
    def mock_date_validation(self, start_date, end_date):
        """
        Mock date validation for lease dates.
        
        Args:
            start_date (date): Start date
            end_date (date): End date
            
        Returns:
            bool: True if dates are valid (end > start)
        """
        if start_date and end_date:
            return end_date > start_date
        return True  # Allow None dates
    
    def tearDown(self):
        """Cleanup after each test"""
        super().tearDown()
        # Reset all mocks
        self.env.reset_mock()
        if hasattr(self, 'company_model'):
            self.company_model.reset_mock()
        if hasattr(self, 'agent_model'):
            self.agent_model.reset_mock()