# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import date, timedelta


class BaseLeaseTest(unittest.TestCase):
    """
    Base class for Lease model unit tests.
    
    Provides:
    - Lease-specific test data and mocks
    - Date validation utilities
    - Helper methods for lease testing scenarios
    """
    
    def setUp(self):
        super().setUp()
        
        # Mock Odoo environment
        self.env = Mock()
        self.cr = Mock()
        self.uid = 1
        
        # Lease test data
        self.lease_data = {
            'id': 1,
            'property_id': 1,
            'tenant_id': 1,
            'company_ids': [1],
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
            'rent_amount': 2500.00
        }
        
        # Valid date ranges
        self.valid_date_ranges = [
            (date(2024, 1, 1), date(2024, 12, 31)),
            (date(2024, 6, 1), date(2024, 6, 30)),
            (date(2024, 1, 15), date(2024, 1, 16)),
        ]
        
        # Invalid date ranges
        self.invalid_date_ranges = [
            (date(2024, 12, 31), date(2024, 1, 1)),    # End before start
            (date(2024, 6, 15), date(2024, 6, 14)),    # Previous day
            (date(2024, 6, 15), date(2024, 6, 15)),    # Same day
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
    
    def create_lease_mock(self, data=None):
        """Create a mock lease record"""
        lease_data = data or self.lease_data
        return self.create_mock_record('real.estate.lease', lease_data)
    
    def validate_date_range(self, start_date, end_date):
        """Validate date range (end > start)"""
        if start_date and end_date:
            return end_date > start_date
        return True