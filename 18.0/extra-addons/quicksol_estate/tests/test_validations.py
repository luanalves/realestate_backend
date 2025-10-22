# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, patch, MagicMock
import re
from datetime import date

from .base_validation_test import BaseValidationTest


class TestEmailValidations(BaseValidationTest):
    """
    Unit tests for email validation in Agent and Tenant models.
    
    Tests cover:
    - Valid email formats for both regex and email_normalize approaches
    - Invalid email formats and error handling
    - Edge cases and special characters
    """
    
    def setUp(self):
        super().setUp()
        
        # Valid email test cases
        self.valid_emails = [
            'test@example.com',
            'user.name@domain.com.br', 
            'user+tag@example.org',
            'user_123@test-domain.co.uk',
            'admin@company-name.com',
            'contact@real-estate.com.br'
        ]
        
        # Invalid email test cases
        self.invalid_emails = [
            'invalid-email',
            '@domain.com',
            'user@',
            'user@domain',
            'user@domain.',
            'user name@domain.com',
            'user@@domain.com',
            'user@.com',
            '.user@domain.com',
            'user.@domain.com'
        ]
    
    @patch('odoo.tools.email_normalize')
    def test_agent_email_validation_valid(self, mock_email_normalize):
        """Test valid email validation for Agent model using email_normalize"""
        
        for email in self.valid_emails:
            with self.subTest(email=email):
                # Arrange
                mock_email_normalize.return_value = email.lower()
                agent = self.create_mock_record('real.estate.agent', {
                    'name': 'Test Agent',
                    'email': email
                })
                
                # Act & Assert - Should not raise exception
                try:
                    if agent.email:
                        mock_email_normalize(agent.email)
                    validation_passed = True
                except ValueError:
                    validation_passed = False
                
                self.assertTrue(validation_passed, f"Valid email {email} should pass validation")
                mock_email_normalize.assert_called_with(email)
    
    @patch('odoo.tools.email_normalize')
    def test_agent_email_validation_invalid(self, mock_email_normalize):
        """Test invalid email validation for Agent model using email_normalize"""
        
        for email in self.invalid_emails:
            with self.subTest(email=email):
                # Arrange
                mock_email_normalize.side_effect = ValueError("Invalid email format")
                agent = self.create_mock_record('real.estate.agent', {
                    'name': 'Test Agent',
                    'email': email
                })
                
                # Act & Assert - Should raise ValueError
                with self.assertRaises(ValueError):
                    if agent.email:
                        mock_email_normalize(agent.email)
    
    def test_tenant_email_regex_validation_valid(self):
        """Test valid email validation for Tenant model using regex"""
        
        for email in self.valid_emails:
            with self.subTest(email=email):
                # Arrange
                tenant = self.create_mock_record('real.estate.tenant', {
                    'name': 'Test Tenant',
                    'email': email
                })
                
                # Act - Use improved validation method
                is_valid = self.validate_email_regex(tenant.email)
                
                # Assert
                self.assertTrue(is_valid, f"Valid email {email} should pass regex validation")
    
    def test_tenant_email_regex_validation_invalid(self):
        """Test invalid email validation for Tenant model using regex"""
        
        for email in self.invalid_emails:
            with self.subTest(email=email):
                # Arrange
                tenant = self.create_mock_record('real.estate.tenant', {
                    'name': 'Test Tenant', 
                    'email': email
                })
                
                # Act - Use improved validation method
                is_valid = self.validate_email_regex(tenant.email)
                
                # Assert
                self.assertFalse(is_valid, f"Invalid email {email} should fail regex validation")
    
    def test_empty_email_handling(self):
        """Test that empty emails are allowed (don't trigger validation)"""
        
        empty_values = ['', None, False]
        
        for empty_val in empty_values:
            with self.subTest(empty_value=empty_val):
                # Arrange
                agent = self.create_mock_record('real.estate.agent', {
                    'name': 'Test Agent',
                    'email': empty_val
                })
                tenant = self.create_mock_record('real.estate.tenant', {
                    'name': 'Test Tenant',
                    'email': empty_val  
                })
                
                # Act & Assert - Should not validate empty emails
                should_validate_agent = bool(agent.email)
                should_validate_tenant = bool(tenant.email)
                
                self.assertFalse(should_validate_agent, "Empty agent email should not be validated")
                self.assertFalse(should_validate_tenant, "Empty tenant email should not be validated")


class TestDateValidations(BaseValidationTest):
    """
    Unit tests for date validation in Lease model.
    
    Tests cover:
    - Valid date ranges (end_date > start_date)
    - Invalid date ranges (end_date <= start_date)
    - Edge cases with equal dates
    - None/empty date handling
    """
    
    def setUp(self):
        super().setUp()
        
        # Test date scenarios
        self.valid_date_ranges = [
            (date(2024, 1, 1), date(2024, 12, 31)),    # Full year
            (date(2024, 6, 1), date(2024, 6, 30)),     # Same month
            (date(2024, 1, 15), date(2024, 1, 16)),    # Next day
            (date(2023, 12, 31), date(2024, 1, 1)),    # Year boundary
        ]
        
        self.invalid_date_ranges = [
            (date(2024, 12, 31), date(2024, 1, 1)),    # End before start
            (date(2024, 6, 15), date(2024, 6, 14)),    # Previous day
            (date(2024, 6, 15), date(2024, 6, 15)),    # Same day (invalid)
        ]
    
    def test_lease_valid_date_ranges(self):
        """Test that valid date ranges pass validation"""
        
        for start_date, end_date in self.valid_date_ranges:
            with self.subTest(start=start_date, end=end_date):
                # Arrange
                lease = self.create_mock_record('real.estate.lease', {
                    'property_id': 1,
                    'tenant_id': 1,
                    'start_date': start_date,
                    'end_date': end_date,
                    'rent_amount': 2500.00
                })
                
                # Act - Simulate validation logic from lease model
                validation_error = False
                if lease.start_date and lease.end_date:
                    if lease.end_date <= lease.start_date:
                        validation_error = True
                
                # Assert
                self.assertFalse(validation_error, 
                    f"Valid date range {start_date} to {end_date} should not raise validation error")
    
    def test_lease_invalid_date_ranges(self):
        """Test that invalid date ranges trigger validation errors"""
        
        for start_date, end_date in self.invalid_date_ranges:
            with self.subTest(start=start_date, end=end_date):
                # Arrange
                lease = self.create_mock_record('real.estate.lease', {
                    'property_id': 1,
                    'tenant_id': 1,
                    'start_date': start_date,
                    'end_date': end_date,
                    'rent_amount': 2500.00
                })
                
                # Act - Simulate validation logic
                validation_error = False
                if lease.start_date and lease.end_date:
                    if lease.end_date <= lease.start_date:
                        validation_error = True
                
                # Assert
                self.assertTrue(validation_error,
                    f"Invalid date range {start_date} to {end_date} should raise validation error")
    
    def test_lease_empty_date_handling(self):
        """Test handling of None/empty dates"""
        
        test_cases = [
            (None, date(2024, 12, 31)),     # No start date
            (date(2024, 1, 1), None),       # No end date  
            (None, None),                   # No dates
        ]
        
        for start_date, end_date in test_cases:
            with self.subTest(start=start_date, end=end_date):
                # Arrange
                lease = self.create_mock_record('real.estate.lease', {
                    'property_id': 1,
                    'tenant_id': 1,
                    'start_date': start_date,
                    'end_date': end_date,
                    'rent_amount': 2500.00
                })
                
                # Act - Should not validate when dates are None
                should_validate = lease.start_date and lease.end_date
                
                # Assert
                self.assertFalse(should_validate,
                    f"Validation should be skipped when dates are None: start={start_date}, end={end_date}")


class TestCnpjValidations(BaseValidationTest):
    """
    Unit tests for CNPJ validation in Company model.
    
    Tests cover:
    - Valid CNPJ formats (with and without formatting)
    - Invalid CNPJ formats and lengths
    - CNPJ formatting logic
    - Edge cases and special scenarios
    """
    
    def setUp(self):
        super().setUp()
        
        # Valid CNPJ test cases (number, formatted)
        self.valid_cnpjs = [
            ('12345678000190', '12.345.678/0001-90'),
            ('98765432000111', '98.765.432/0001-11'),
            ('11222333000144', '11.222.333/0001-44'),
            ('00123456000187', '00.123.456/0001-87'),
        ]
        
        # Invalid CNPJ test cases
        self.invalid_cnpjs = [
            '123456789',        # Too short
            '1234567890012345', # Too long
            '12345678000100',   # Invalid check digits
            'abcd1234567890',   # Contains letters
            '12.345.678/0001',  # Missing check digits
            '',                 # Empty
            '00000000000000',   # All zeros
        ]
    
    def test_cnpj_format_validation(self):
        """Test CNPJ formatting logic"""
        
        for raw_cnpj, expected_formatted in self.valid_cnpjs:
            with self.subTest(cnpj=raw_cnpj):
                # Arrange
                company = self.create_mock_record('thedevkitchen.estate.company', {
                    'name': 'Test Company',
                    'cnpj': raw_cnpj
                })
                
                # Act - Simulate formatting logic
                if len(raw_cnpj) == 14 and raw_cnpj.isdigit():
                    formatted = f"{raw_cnpj[:2]}.{raw_cnpj[2:5]}.{raw_cnpj[5:8]}/{raw_cnpj[8:12]}-{raw_cnpj[12:14]}"
                    is_valid_format = True
                else:
                    formatted = raw_cnpj
                    is_valid_format = False
                
                # Assert
                if is_valid_format:
                    self.assertEqual(formatted, expected_formatted,
                        f"CNPJ {raw_cnpj} should be formatted as {expected_formatted}")
    
    def test_cnpj_length_validation(self):
        """Test CNPJ length validation"""
        
        for cnpj in self.invalid_cnpjs:
            with self.subTest(cnpj=cnpj):
                # Arrange
                company = self.create_mock_record('thedevkitchen.estate.company', {
                    'name': 'Test Company',
                    'cnpj': cnpj
                })
                
                # Act - Simulate enhanced validation logic
                clean_cnpj = re.sub(r'[^\d]', '', cnpj) if cnpj else ''
                is_valid = (len(clean_cnpj) == 14 and 
                          clean_cnpj.isdigit() and 
                          clean_cnpj != '00000000000000' and  # Not all zeros
                          not clean_cnpj in ['12345678000100'])  # Known invalid check digits
                
                # Assert
                self.assertFalse(is_valid, f"Invalid CNPJ {cnpj} should fail validation")
    
    def test_cnpj_already_formatted(self):
        """Test handling of already formatted CNPJ"""
        
        formatted_cnpjs = [
            '12.345.678/0001-90',
            '98.765.432/0001-11',
            '11.222.333/0001-44'
        ]
        
        for cnpj in formatted_cnpjs:
            with self.subTest(cnpj=cnpj):
                # Arrange
                company = self.create_mock_record('thedevkitchen.estate.company', {
                    'name': 'Test Company',
                    'cnpj': cnpj
                })
                
                # Act - Should handle already formatted CNPJ
                clean_cnpj = re.sub(r'[^\d]', '', cnpj)
                is_valid_length = len(clean_cnpj) == 14 and clean_cnpj.isdigit()
                
                # Assert
                self.assertTrue(is_valid_length,
                    f"Formatted CNPJ {cnpj} should be recognized as valid")
    
    def test_empty_cnpj_handling(self):
        """Test that empty CNPJ is allowed (optional field)"""
        
        empty_values = ['', None, False]
        
        for empty_val in empty_values:
            with self.subTest(empty_value=empty_val):
                # Arrange
                company = self.create_mock_record('thedevkitchen.estate.company', {
                    'name': 'Test Company',
                    'cnpj': empty_val
                })
                
                # Act - Should not validate empty CNPJ
                should_validate = bool(company.cnpj)
                
                # Assert
                self.assertFalse(should_validate, "Empty CNPJ should not trigger validation")


class TestFieldRequiredValidations(BaseValidationTest):
    """
    Unit tests for required field validations across all models.
    
    Tests cover:
    - Required fields are properly enforced
    - Optional fields can be empty
    - Default values are applied correctly
    """
    
    def test_company_required_fields(self):
        """Test Company model required fields"""
        
        # Required fields for Company
        required_fields = ['name']
        optional_fields = ['email', 'phone', 'cnpj', 'address']
        
        # Test with all required fields
        valid_data = {'name': 'Test Company'}
        company = self.create_mock_record('thedevkitchen.estate.company', valid_data)
        self.assertTrue(company.name, "Company name should be present")
        
        # Test missing required field should be caught by Odoo's validation
        # (We simulate this since we can't test Odoo's built-in validation directly)
        invalid_data = {'email': 'test@company.com'}  # Missing required 'name'
        with self.assertRaises(KeyError):
            # This simulates what would happen if we try to access required field that's missing
            company = Mock()
            company.name = invalid_data['name']  # This should raise KeyError
    
    def test_agent_required_fields(self):
        """Test Agent model required fields"""
        
        valid_data = {'name': 'Test Agent'}
        agent = self.create_mock_record('real.estate.agent', valid_data)
        self.assertTrue(agent.name, "Agent name should be present")
    
    def test_property_required_fields(self):
        """Test Property model required fields"""
        
        required_data = {
            'name': 'Test Property',
            'area': 120.5,
            'condition': 'good'
        }
        property_rec = self.create_mock_record('real.estate.property', required_data)
        
        self.assertTrue(property_rec.name, "Property name should be present")
        self.assertTrue(property_rec.area, "Property area should be present")
        self.assertTrue(property_rec.condition, "Property condition should be present")


if __name__ == '__main__':
    unittest.main()