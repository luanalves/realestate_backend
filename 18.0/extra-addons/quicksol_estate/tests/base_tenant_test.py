# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import date
import re


class BaseTenantTest(unittest.TestCase):
    """
    Base class for Tenant model unit tests.
    
    Provides:
    - Tenant-specific test data and mocks
    - Email validation utilities (regex-based)
    - Helper methods for tenant testing scenarios
    """
    
    def setUp(self):
        super().setUp()
        
        # Mock Odoo environment
        self.env = Mock()
        self.cr = Mock()
        self.uid = 1
        
        # Tenant test data
        self.tenant_data = {
            'id': 1,
            'name': 'John Tenant',
            'email': 'john.tenant@example.com',
            'phone': '+55 11 98888-7777',
            'company_ids': [1],
            'occupation': 'Software Engineer',
            'birthdate': date(1990, 5, 15),
            'leases': [1]
        }
        
        # Valid email test cases
        self.valid_emails = [
            'tenant@example.com',
            'john.doe@company.com.br',
            'tenant_123@domain.org',
            'contact@real-estate.com'
        ]
        
        # Invalid email test cases
        self.invalid_emails = [
            'invalid-email',
            '@domain.com',
            'tenant@',
            'tenant@domain',
            'tenant name@domain.com',
            'tenant@@domain.com',
            '.tenant@domain.com',
            'tenant.@domain.com'
        ]
    
    def create_mock_record(self, model_name, data):
        """Create a generic mock record"""
        record = Mock()
        
        for key, value in data.items():
            setattr(record, key, value)
        
        record._name = model_name
        record.exists = Mock(return_value=record)
        record.ensure_one = Mock(return_value=None)
        
        return record
    
    def create_tenant_mock(self, data=None):
        """Create a mock tenant record"""
        tenant_data = data or self.tenant_data
        return self.create_mock_record('real.estate.tenant', tenant_data)
    
    def validate_email_regex(self, email):
        """Validate email using regex pattern (matches tenant model)"""
        if not email or not isinstance(email, str):
            return False
        
        # Email validation regex pattern from tenant model
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))