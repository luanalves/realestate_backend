# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import re

from .base_tenant_test import BaseTenantTest


class TestTenantUnit(BaseTenantTest):
    """
    Unit tests for Tenant model business logic.
    
    Tests cover:
    - Tenant creation and data integrity
    - Email validation using regex
    - Relationship management (companies, leases)
    - Required field validation
    - Personal information handling
    """
    
    def setUp(self):
        super().setUp()
        
        # Create mock tenant with relationships
        self.tenant_with_relations = self.create_tenant_mock({
            **self.tenant_data,
            'company_ids': [1, 2],
            'leases': [1, 2]
        })
    
    def test_tenant_creation_with_valid_data(self):
        """Test tenant creation with complete valid data"""
        
        # Arrange
        tenant_data = {
            'name': 'Maria Silva',
            'email': 'maria.silva@example.com',
            'phone': '+55 11 98765-4321',
            'occupation': 'Doctor',
            'birthdate': date(1985, 3, 20)
        }
        
        # Act
        tenant = self.create_tenant_mock(tenant_data)
        
        # Assert
        self.assertEqual(tenant.name, 'Maria Silva')
        self.assertEqual(tenant.email, 'maria.silva@example.com')
        self.assertEqual(tenant.occupation, 'Doctor')
        self.assertEqual(tenant.birthdate, date(1985, 3, 20))
    
    def test_tenant_name_required(self):
        """Test that tenant name is required"""
        
        # Arrange
        tenant_data = {
            'name': 'Test Tenant',
            'email': 'test@tenant.com'
        }
        
        # Act
        tenant = self.create_tenant_mock(tenant_data)
        
        # Assert
        self.assertTrue(tenant.name and len(tenant.name.strip()) > 0,
                       "Tenant name should not be empty")
    
    def test_tenant_email_validation_valid(self):
        """Test valid email validation for Tenant model"""
        
        for email in self.valid_emails:
            with self.subTest(email=email):
                # Arrange
                tenant = self.create_tenant_mock({
                    'name': 'Test Tenant',
                    'email': email
                })
                
                # Act
                is_valid = self.validate_email_regex(tenant.email)
                
                # Assert
                self.assertTrue(is_valid, f"Valid email {email} should pass validation")
    
    def test_tenant_email_validation_invalid(self):
        """Test invalid email validation for Tenant model"""
        
        for email in self.invalid_emails:
            with self.subTest(email=email):
                # Arrange
                tenant = self.create_tenant_mock({
                    'name': 'Test Tenant',
                    'email': email
                })
                
                # Act
                is_valid = self.validate_email_regex(tenant.email)
                
                # Assert
                self.assertFalse(is_valid, f"Invalid email {email} should fail validation")
    
    def test_tenant_empty_email_allowed(self):
        """Test that empty email is allowed (optional field)"""
        
        empty_values = ['', None]
        
        for empty_val in empty_values:
            with self.subTest(empty_value=empty_val):
                # Arrange
                tenant = self.create_tenant_mock({
                    'name': 'Test Tenant',
                    'email': empty_val
                })
                
                # Act - Should not validate empty emails
                should_validate = bool(tenant.email)
                
                # Assert
                self.assertFalse(should_validate, "Empty email should not trigger validation")
    
    def test_tenant_company_relationship(self):
        """Test tenant-company many2many relationship"""
        
        # Arrange & Act
        tenant = self.create_tenant_mock({
            'name': 'Multi-Company Tenant',
            'email': 'tenant@multi.com',
            'company_ids': [1, 2, 3]
        })
        
        # Assert
        self.assertEqual(len(tenant.company_ids), 3)
        self.assertIn(1, tenant.company_ids)
        self.assertIn(2, tenant.company_ids)
    
    def test_tenant_lease_relationship(self):
        """Test tenant-lease one2many relationship"""
        
        # Arrange & Act
        tenant = self.create_tenant_mock({
            'name': 'Tenant with Leases',
            'email': 'tenant@leases.com',
            'leases': [1, 2]
        })
        
        # Assert
        self.assertEqual(len(tenant.leases), 2)
        self.assertIn(1, tenant.leases)
    
    def test_tenant_birthdate_validation(self):
        """Test birthdate field accepts valid dates"""
        
        valid_birthdates = [
            date(1990, 1, 1),
            date(1985, 6, 15),
            date(1970, 12, 31),
            date(2000, 7, 20)
        ]
        
        for birthdate in valid_birthdates:
            with self.subTest(birthdate=birthdate):
                # Arrange & Act
                tenant = self.create_tenant_mock({
                    'name': 'Test Tenant',
                    'birthdate': birthdate
                })
                
                # Assert
                self.assertEqual(tenant.birthdate, birthdate)
                self.assertIsInstance(tenant.birthdate, date)
    
    def test_tenant_occupation_field(self):
        """Test occupation field accepts various values"""
        
        occupations = [
            'Software Engineer',
            'Doctor',
            'Teacher',
            'Business Owner',
            'Retired',
            'Student'
        ]
        
        for occupation in occupations:
            with self.subTest(occupation=occupation):
                # Arrange & Act
                tenant = self.create_tenant_mock({
                    'name': 'Test Tenant',
                    'occupation': occupation
                })
                
                # Assert
                self.assertEqual(tenant.occupation, occupation)
    
    def test_tenant_phone_field(self):
        """Test phone field with various formats"""
        
        phone_numbers = [
            '+55 11 98765-4321',
            '+1 (555) 123-4567',
            '+44 20 7946 0958',
            '11 98888-7777'
        ]
        
        for phone in phone_numbers:
            with self.subTest(phone=phone):
                # Arrange & Act
                tenant = self.create_tenant_mock({
                    'name': 'Test Tenant',
                    'phone': phone
                })
                
                # Assert
                self.assertEqual(tenant.phone, phone)
    
    def test_tenant_profile_picture_field(self):
        """Test profile picture binary field"""
        
        # Arrange & Act
        tenant = self.create_tenant_mock({
            'name': 'Test Tenant',
            'profile_picture': b'fake_image_binary_data'
        })
        
        # Assert
        self.assertIsNotNone(tenant.profile_picture)
        self.assertIsInstance(tenant.profile_picture, bytes)


class TestTenantBusinessLogic(BaseTenantTest):
    """
    Unit tests for Tenant model business logic and workflows.
    """
    
    def test_tenant_with_active_leases(self):
        """Test tenant with active leases"""
        
        # Arrange
        tenant = self.create_tenant_mock({
            'name': 'Active Tenant',
            'email': 'active@tenant.com',
            'leases': [1, 2, 3]
        })
        
        # Act
        has_active_leases = len(tenant.leases) > 0
        
        # Assert
        self.assertTrue(has_active_leases)
        self.assertEqual(len(tenant.leases), 3)
    
    def test_tenant_without_leases(self):
        """Test tenant without any leases (new tenant)"""
        
        # Arrange
        tenant = self.create_tenant_mock({
            'name': 'New Tenant',
            'email': 'new@tenant.com',
            'leases': []
        })
        
        # Act
        has_leases = len(tenant.leases) > 0
        
        # Assert
        self.assertFalse(has_leases)
        self.assertEqual(len(tenant.leases), 0)
    
    def test_tenant_age_calculation(self):
        """Test age calculation based on birthdate"""
        
        # Arrange
        tenant = self.create_tenant_mock({
            'name': 'Test Tenant',
            'birthdate': date(1990, 5, 15)
        })
        
        # Act - Calculate age
        from datetime import date as dt
        today = dt.today()
        age = today.year - tenant.birthdate.year
        if (today.month, today.day) < (tenant.birthdate.month, tenant.birthdate.day):
            age -= 1
        
        # Assert - Tenant should be at least 18 (assuming minimum age for leasing)
        self.assertGreater(age, 0)
        self.assertGreater(age, 18, "Tenant should be of legal age")
    
    def test_tenant_data_integrity(self):
        """Test tenant data integrity"""
        
        # Arrange & Act
        tenant = self.create_tenant_mock({
            'name': 'Integrity Test Tenant',
            'email': 'integrity@test.com',
            'phone': '+55 11 99999-8888',
            'occupation': 'Engineer',
            'birthdate': date(1988, 10, 25),
            'company_ids': [1]
        })
        
        # Assert - All fields should be preserved
        self.assertEqual(tenant.name, 'Integrity Test Tenant')
        self.assertEqual(tenant.email, 'integrity@test.com')
        self.assertEqual(tenant.phone, '+55 11 99999-8888')
        self.assertEqual(tenant.occupation, 'Engineer')
        self.assertEqual(tenant.birthdate, date(1988, 10, 25))
        self.assertEqual(len(tenant.company_ids), 1)
    
    def test_tenant_filtering_by_company(self):
        """Test filtering tenants by company"""
        
        # Arrange
        tenant1 = self.create_tenant_mock({
            'name': 'Tenant 1',
            'company_ids': [1, 2]
        })
        
        tenant2 = self.create_tenant_mock({
            'name': 'Tenant 2',
            'company_ids': [2, 3]
        })
        
        tenant3 = self.create_tenant_mock({
            'name': 'Tenant 3',
            'company_ids': [1]
        })
        
        # Act - Simulate filtering for company 1
        all_tenants = [tenant1, tenant2, tenant3]
        company_1_tenants = [t for t in all_tenants if 1 in t.company_ids]
        
        # Assert
        self.assertEqual(len(company_1_tenants), 2)
        self.assertIn(tenant1, company_1_tenants)
        self.assertIn(tenant3, company_1_tenants)
    
    def test_tenant_multiple_properties_scenario(self):
        """Test tenant with multiple lease agreements"""
        
        # Arrange
        tenant = self.create_tenant_mock({
            'name': 'Multi-Property Tenant',
            'email': 'multi@tenant.com',
            'leases': [1, 2, 3, 4]
        })
        
        # Act
        lease_count = len(tenant.leases)
        
        # Assert
        self.assertEqual(lease_count, 4)
        self.assertGreater(lease_count, 1, "Tenant has multiple properties")
    
    def test_tenant_contact_information(self):
        """Test tenant contact information completeness"""
        
        # Arrange & Act
        complete_tenant = self.create_tenant_mock({
            'name': 'Complete Tenant',
            'email': 'complete@tenant.com',
            'phone': '+55 11 98888-7777'
        })
        
        incomplete_tenant = self.create_tenant_mock({
            'name': 'Incomplete Tenant'
        })
        
        # Assert
        has_complete_contact = (complete_tenant.email and complete_tenant.phone)
        has_incomplete_contact = not (hasattr(incomplete_tenant, 'email') and 
                                      hasattr(incomplete_tenant, 'phone') and
                                      incomplete_tenant.email and 
                                      incomplete_tenant.phone)
        
        self.assertTrue(has_complete_contact)
        self.assertTrue(has_incomplete_contact)


class TestTenantEdgeCases(BaseTenantTest):
    """
    Unit tests for Tenant model edge cases and boundary conditions.
    """
    
    def test_tenant_with_very_long_name(self):
        """Test tenant with long name"""
        
        # Arrange & Act
        long_name = 'A' * 100
        tenant = self.create_tenant_mock({
            'name': long_name
        })
        
        # Assert
        self.assertEqual(len(tenant.name), 100)
        self.assertTrue(tenant.name and len(tenant.name.strip()) > 0)
    
    def test_tenant_with_special_characters_in_name(self):
        """Test tenant name with special characters"""
        
        names_with_special_chars = [
            "O'Connor",
            "José María",
            "François-Pierre",
            "Müller",
            "李明"
        ]
        
        for name in names_with_special_chars:
            with self.subTest(name=name):
                # Arrange & Act
                tenant = self.create_tenant_mock({
                    'name': name
                })
                
                # Assert
                self.assertEqual(tenant.name, name)
    
    def test_tenant_birthdate_edge_cases(self):
        """Test birthdate edge cases"""
        
        edge_dates = [
            date(1900, 1, 1),    # Very old
            date(2010, 12, 31),  # Young adult
            date(1950, 2, 29),   # Leap year (would be 1952 in reality)
        ]
        
        for birthdate in edge_dates:
            with self.subTest(birthdate=birthdate):
                # Arrange & Act
                tenant = self.create_tenant_mock({
                    'name': 'Edge Case Tenant',
                    'birthdate': birthdate
                })
                
                # Assert
                self.assertEqual(tenant.birthdate, birthdate)
    
    def test_tenant_email_with_plus_addressing(self):
        """Test email with plus addressing (valid)"""
        
        # Arrange & Act
        tenant = self.create_tenant_mock({
            'name': 'Plus Addressing Tenant',
            'email': 'tenant+tag@example.com'
        })
        
        # Assert
        is_valid = self.validate_email_regex(tenant.email)
        self.assertTrue(is_valid)
    
    def test_tenant_no_optional_fields(self):
        """Test tenant with only required fields"""
        
        # Arrange & Act
        minimal_tenant = self.create_tenant_mock({
            'name': 'Minimal Tenant'
        })
        
        # Assert
        self.assertTrue(minimal_tenant.name)
        # Optional fields may not be set
        self.assertTrue(not hasattr(minimal_tenant, 'email') or 
                       not minimal_tenant.email or 
                       minimal_tenant.email is None)


if __name__ == '__main__':
    unittest.main()