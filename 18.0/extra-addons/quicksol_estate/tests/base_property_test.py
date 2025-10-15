# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import date


class BasePropertyTest(unittest.TestCase):
    """
    Base class for Property model unit tests.
    
    Provides:
    - Property-specific test data and mocks
    - Helper methods for property testing scenarios
    - Relationship validation utilities
    """
    
    def setUp(self):
        super().setUp()
        
        # Mock Odoo environment
        self.env = Mock()
        self.cr = Mock()
        self.uid = 1
        
        # Property test data
        self.property_data = {
            'id': 1,
            'name': 'Luxury Apartment Downtown',
            'price': 350000.00,
            'currency_id': 1,
            'area': 120.5,
            'num_rooms': 3,
            'num_bathrooms': 2,
            'num_floors': 1,
            'address': '123 Main Street',
            'city': 'São Paulo',
            'state': 'SP',
            'zip_code': '01310-100',
            'country_id': 1,
            'status': 'available',
            'condition': 'good',
            'company_ids': [1],
            'agent_id': 1,
            'property_type_id': 1,
            'latitude': -23.550520,
            'longitude': -46.633308
        }
        
        # Property type test data
        self.property_type_data = {
            'id': 1,
            'name': 'Apartment'
        }
        
        # Valid property status values
        self.valid_statuses = ['available', 'pending', 'sold', 'rented']
        
        # Valid property conditions
        self.valid_conditions = ['new', 'good', 'needs_renovation']
        
        # Amenity test data
        self.amenity_data = [
            {'id': 1, 'name': 'Swimming Pool'},
            {'id': 2, 'name': 'Garage'},
            {'id': 3, 'name': 'Garden'}
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
    
    def create_property_mock(self, data=None):
        """Create a mock property record"""
        property_data = data or self.property_data
        return self.create_mock_record('real.estate.property', property_data)
    
    def create_property_type_mock(self, data=None):
        """Create a mock property type record"""
        type_data = data or self.property_type_data
        return self.create_mock_record('real.estate.property.type', type_data)