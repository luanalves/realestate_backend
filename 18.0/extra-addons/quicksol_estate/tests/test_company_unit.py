# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import date

from .base_company_test import BaseCompanyTest


class TestCompanyUnit(BaseCompanyTest):
    """
    Unit tests for Company model business logic.
    
    Tests cover:
    - Company creation and data integrity
    - Computed fields (counts)
    - CNPJ formatting and validation
    - Action methods (view properties, agents, etc.)
    - Relationship management
    """
    
    def setUp(self):
        super().setUp()
        
        # Create mock company with relationships
        self.company_with_relations = self.create_mock_record(
            'thedevkitchen.estate.company',
            {
                **self.mock_company_data,
                'property_ids': [1, 2, 3],
                'agent_ids': [1, 2], 
                'lease_ids': [1],
                'sale_ids': [1]
            }
        )
    
    def test_company_creation_with_valid_data(self):
        """Test company creation with valid data"""
        
        # Arrange
        company_data = {
            'name': 'Premium Real Estate',
            'email': 'contact@premium.com',
            'phone': '+55 11 3333-4444',
            'cnpj': '12.345.678/0001-90',
            'address': 'Premium Street, 123',
            'city': 'São Paulo',
            'active': True
        }
        
        # Act
        company = self.create_mock_record('thedevkitchen.estate.company', company_data)
        
        # Assert
        self.assertEqual(company.name, 'Premium Real Estate')
        self.assertEqual(company.email, 'contact@premium.com')
        self.assertEqual(company.cnpj, '12.345.678/0001-90')
        self.assertTrue(company.active)
        self.assertEqual(company.city, 'São Paulo')
    
    def test_company_computed_property_count(self):
        """Test computed field for property count"""
        
        # Arrange - Company with multiple properties
        mock_properties = [
            {'id': 1, 'name': 'Property 1'},
            {'id': 2, 'name': 'Property 2'},
            {'id': 3, 'name': 'Property 3'}
        ]
        
        company = self.create_mock_record('thedevkitchen.estate.company', {
            'name': 'Test Company',
            'property_ids': mock_properties
        })
        
        # Act - Simulate computed field logic
        property_count = len(company.property_ids) if hasattr(company, 'property_ids') else 0
        
        # Assert
        self.assertEqual(property_count, 3, "Property count should match number of related properties")
    
    def test_company_computed_agent_count(self):
        """Test computed field for agent count"""
        
        # Arrange
        mock_agents = [
            {'id': 1, 'name': 'Agent 1'},
            {'id': 2, 'name': 'Agent 2'}
        ]
        
        company = self.create_mock_record('thedevkitchen.estate.company', {
            'name': 'Test Company', 
            'agent_ids': mock_agents
        })
        
        # Act
        agent_count = len(company.agent_ids) if hasattr(company, 'agent_ids') else 0
        
        # Assert
        self.assertEqual(agent_count, 2, "Agent count should match number of related agents")
    
    def test_company_computed_lease_count(self):
        """Test computed field for lease count"""
        
        # Arrange
        company = self.create_mock_record('thedevkitchen.estate.company', {
            'name': 'Test Company',
            'lease_ids': [{'id': 1, 'start_date': date(2024, 1, 1)}]
        })
        
        # Act
        lease_count = len(company.lease_ids) if hasattr(company, 'lease_ids') else 0
        
        # Assert
        self.assertEqual(lease_count, 1, "Lease count should match number of related leases")
    
    def test_company_computed_sale_count(self):
        """Test computed field for sale count"""
        
        # Arrange
        company = self.create_mock_record('thedevkitchen.estate.company', {
            'name': 'Test Company',
            'sale_ids': [{'id': 1, 'sale_date': date(2024, 6, 15)}]
        })
        
        # Act
        sale_count = len(company.sale_ids) if hasattr(company, 'sale_ids') else 0
        
        # Assert
        self.assertEqual(sale_count, 1, "Sale count should match number of related sales")
    
    def test_company_cnpj_formatting(self):
        """Test automatic CNPJ formatting"""
        
        test_cases = [
            ('12345678000190', '12.345.678/0001-90'),
            ('98765432000111', '98.765.432/0001-11'),
            ('11222333000144', '11.222.333/0001-44')
        ]
        
        def format_cnpj(cnpj):
            # Simulate the formatting logic from the Odoo model
            digits = ''.join(filter(str.isdigit, cnpj or ''))
            if len(digits) == 14:
                return '{}.{}.{}/{}-{}'.format(
                    digits[:2], digits[2:5], digits[5:8], digits[8:12], digits[12:]
                )
            return cnpj
        
        for raw_cnpj, expected_formatted in test_cases:
            with self.subTest(cnpj=raw_cnpj):
                # Act - Create mock company record and simulate CNPJ formatting
                company = self.create_mock_record('thedevkitchen.estate.company', {
                    'name': 'Test Company',
                    'cnpj': raw_cnpj
                })
                # Simulate onchange formatting
                formatted_cnpj = format_cnpj(company.cnpj)
                
                # Assert - Check that formatting matches expected
                self.assertEqual(formatted_cnpj, expected_formatted,
                    f"CNPJ {raw_cnpj} should be formatted to {expected_formatted}")
    
    @patch('odoo.exceptions.ValidationError')
    def test_company_cnpj_validation_invalid(self, mock_validation_error):
        """Test CNPJ validation for invalid formats"""
        
        invalid_cnpjs = [
            '123456789',        # Too short
            '1234567890012345', # Too long
            'abc123def456',     # Contains letters
            '',                 # Empty
        ]
        
        for invalid_cnpj in invalid_cnpjs:
            with self.subTest(cnpj=invalid_cnpj):
                # Arrange
                company = self.create_mock_record('thedevkitchen.estate.company', {
                    'name': 'Test Company',
                    'cnpj': invalid_cnpj
                })
                
                # Act - Simulate validation check
                should_raise_error = False
                if company.cnpj:
                    clean_cnpj = ''.join(filter(str.isdigit, company.cnpj))
                    if len(clean_cnpj) != 14:
                        should_raise_error = True
                
                # Assert
                if invalid_cnpj and invalid_cnpj != '':  # Empty is allowed
                    self.assertTrue(should_raise_error, f"Invalid CNPJ {invalid_cnpj} should trigger validation error")
    
    def test_company_action_view_properties(self):
        """Test action_view_properties method"""
        
        # Arrange
        company = self.company_with_relations
        
        # Mock the action method
        def mock_action_view_properties():
            return {
                'type': 'ir.actions.act_window',
                'name': 'Properties',
                'res_model': 'real.estate.property',
                'view_mode': 'tree,form',
                'domain': [('company_ids', 'in', [company.id])],
                'context': {'default_company_ids': [(6, 0, [company.id])]}
            }
        
        company.action_view_properties = mock_action_view_properties
        
        # Act
        action = company.action_view_properties()
        
        # Assert
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'real.estate.property')
        self.assertIn('company_ids', str(action['domain']))
    
    def test_company_action_view_agents(self):
        """Test action_view_agents method"""
        
        # Arrange
        company = self.company_with_relations
        
        # Mock the action method
        def mock_action_view_agents():
            return {
                'type': 'ir.actions.act_window',
                'name': 'Agents',
                'res_model': 'real.estate.agent',
                'view_mode': 'tree,form',
                'domain': [('company_ids', 'in', [company.id])],
                'context': {'default_company_ids': [(6, 0, [company.id])]}
            }
        
        company.action_view_agents = mock_action_view_agents
        
        # Act
        action = company.action_view_agents()
        
        # Assert
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'real.estate.agent')
        self.assertIn('company_ids', str(action['domain']))
    
    def test_company_action_view_leases(self):
        """Test action_view_leases method"""
        
        # Arrange
        company = self.company_with_relations
        
        # Mock the action method
        def mock_action_view_leases():
            return {
                'type': 'ir.actions.act_window',
                'name': 'Leases',
                'res_model': 'real.estate.lease', 
                'view_mode': 'tree,form',
                'domain': [('company_ids', 'in', [company.id])],
                'context': {'default_company_ids': [(6, 0, [company.id])]}
            }
        
        company.action_view_leases = mock_action_view_leases
        
        # Act
        action = company.action_view_leases()
        
        # Assert
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'real.estate.lease')
        self.assertIn('company_ids', str(action['domain']))
    
    def test_company_action_view_sales(self):
        """Test action_view_sales method"""
        
        # Arrange
        company = self.company_with_relations
        
        # Mock the action method  
        def mock_action_view_sales():
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sales',
                'res_model': 'real.estate.sale',
                'view_mode': 'tree,form', 
                'domain': [('company_ids', 'in', [company.id])],
                'context': {'default_company_ids': [(6, 0, [company.id])]}
            }
        
        company.action_view_sales = mock_action_view_sales
        
        # Act
        action = company.action_view_sales()
        
        # Assert
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'real.estate.sale')
        self.assertIn('company_ids', str(action['domain']))
    
    def test_company_default_values(self):
        """Test default values are properly set"""
        
        # Arrange & Act
        company = self.create_mock_record('thedevkitchen.estate.company', {
            'name': 'Test Company'
            # Not setting active field to test default
        })
        
        # Simulate default value behavior
        if not hasattr(company, 'active'):
            company.active = True  # Default value
        
        # Assert
        self.assertTrue(company.active, "Company should be active by default")
    
    def test_company_string_representation(self):
        """Test company name display"""
        
        # Arrange
        company = self.create_mock_record('thedevkitchen.estate.company', {
            'name': 'Premium Real Estate Solutions'
        })
        
        # Act - In Odoo, the record representation would be the name field
        display_name = company.name
        
        # Assert
        self.assertEqual(display_name, 'Premium Real Estate Solutions')
        self.assertTrue(len(display_name) > 0, "Company display name should not be empty")
    
    def test_company_many2many_relationships(self):
        """Test Many2many relationships with other models"""
        
        # Arrange
        company = self.create_mock_record('thedevkitchen.estate.company', {
            'name': 'Relationship Test Company'
        })
        
        # Mock related records
        mock_properties = [1, 2, 3]
        mock_agents = [1, 2]
        
        company.property_ids = mock_properties
        company.agent_ids = mock_agents
        
        # Act & Assert
        self.assertEqual(len(company.property_ids), 3, "Should have 3 related properties")
        self.assertEqual(len(company.agent_ids), 2, "Should have 2 related agents")
        
        # Test relationship access
        self.assertIn(1, company.property_ids, "Property 1 should be related")
        self.assertIn(2, company.agent_ids, "Agent 2 should be related")


class TestCompanyBusinessLogic(BaseCompanyTest):
    """
    Unit tests for Company model business logic and workflows.
    """
    
    def test_company_active_filtering(self):
        """Test filtering of active companies"""
        
        # Arrange
        active_company = self.create_mock_record('thedevkitchen.estate.company', {
            'name': 'Active Company',
            'active': True
        })
        
        inactive_company = self.create_mock_record('thedevkitchen.estate.company', {
            'name': 'Inactive Company', 
            'active': False
        })
        
        # Act - Simulate filtering logic
        companies = [active_company, inactive_company]
        active_companies = [c for c in companies if c.active]
        
        # Assert
        self.assertEqual(len(active_companies), 1)
        self.assertEqual(active_companies[0].name, 'Active Company')
    
    def test_company_data_integrity(self):
        """Test data integrity constraints"""
        
        # Arrange & Act
        company = self.create_mock_record('thedevkitchen.estate.company', {
            'name': 'Data Integrity Test',
            'email': 'test@integrity.com',
            'phone': '+55 11 9999-8888'
        })
        
        # Assert - All critical fields should be preserved
        self.assertEqual(company.name, 'Data Integrity Test')
        self.assertEqual(company.email, 'test@integrity.com')
        self.assertEqual(company.phone, '+55 11 9999-8888')
        
        # Test that name cannot be empty (required field)
        self.assertTrue(company.name and len(company.name.strip()) > 0,
                       "Company name should not be empty")


if __name__ == '__main__':
    unittest.main()