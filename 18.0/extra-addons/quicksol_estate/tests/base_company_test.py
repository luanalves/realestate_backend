# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import date


class BaseCompanyTest(unittest.TestCase):
    """
    Base class for Company model unit tests.
    
    Provides:
    - Company-specific test data and mocks
    - Helper methods for company testing scenarios
    - CNPJ validation utilities
    """
    
    def setUp(self):
        super().setUp()
        
        # Mock Odoo environment
        self.env = Mock()
        self.cr = Mock()
        self.uid = 1
        
        # Company test data
        self.company_data = {
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
        
        # Valid CNPJ test cases
        self.valid_cnpjs = [
            ('12345678000190', '12.345.678/0001-90'),
            ('98765432000111', '98.765.432/0001-11'),
            ('11222333000144', '11.222.333/0001-44'),
        ]
        
        # Invalid CNPJ test cases
        self.invalid_cnpjs = [
            '123456789',        # Too short
            '1234567890012345', # Too long
            'abcd1234567890',   # Contains letters
            '',                 # Empty
            '00000000000000',   # All zeros
        ]
    
    def create_company_mock(self, data=None):
        """Create a mock company record"""
        company_data = data or self.company_data
        company = Mock()
        
        for key, value in company_data.items():
            setattr(company, key, value)
        
        company._name = 'thedevkitchen.estate.company'
        company.exists = Mock(return_value=company)
        company.ensure_one = Mock(return_value=None)
        
        return company
    
    def mock_cnpj_validation(self, cnpj):
        """Mock CNPJ validation logic"""
        if not cnpj:
            return True  # Empty is allowed
        
        clean_cnpj = ''.join(filter(str.isdigit, cnpj))
        return len(clean_cnpj) == 14
    
    def mock_cnpj_formatting(self, cnpj):
        """Mock CNPJ formatting logic"""
        if len(cnpj) == 14 and cnpj.isdigit():
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
        return cnpj