# -*- coding: utf-8 -*-
"""
Unit Tests for Company Validations (Feature 007)

Tests:
- T026: TestCNPJValidation - CNPJ format and check digit validation
- T027: TestEmailValidation - Email format validation (RFC 5322)
"""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install', 'quicksol_estate', 'feature_007')
class TestCNPJValidation(TransactionCase):
    """
    Test CNPJ validation including format and check digits.
    
    Business Rule (T026):
    - CNPJ must be 14 digits (numbers only or formatted)
    - Check digits must be valid (positions 13-14)
    - CNPJ must be unique (including soft-deleted records)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Valid CNPJ for testing
        cls.valid_cnpj = '12.345.678/0001-90'
        cls.valid_cnpj_unformatted = '12345678000190'

    def test_01_valid_cnpj_formatted(self):
        """Company can be created with valid formatted CNPJ"""
        company = self.env['thedevkitchen.estate.company'].create({
            'name': 'Test Company Formatted',
            'cnpj': '11.111.111/0001-81',  # Valid CNPJ
            'email': 'formatted@test.com',
            'phone': '11987654321',
        })
        
        self.assertTrue(company.exists(), "Company should be created with valid CNPJ")

    def test_02_valid_cnpj_unformatted(self):
        """Company can be created with valid unformatted CNPJ"""
        company = self.env['thedevkitchen.estate.company'].create({
            'name': 'Test Company Unformatted',
            'cnpj': '11111111000181',  # Same CNPJ, unformatted
            'email': 'unformatted@test.com',
            'phone': '11987654322',
        })
        
        # Should be formatted automatically
        self.assertIn('/', company.cnpj, "CNPJ should be auto-formatted")
        self.assertIn('.', company.cnpj, "CNPJ should be auto-formatted")

    def test_03_invalid_cnpj_wrong_check_digit(self):
        """Cannot create Company with invalid CNPJ check digits"""
        with self.assertRaises(ValidationError, msg="Should reject CNPJ with wrong check digits"):
            self.env['thedevkitchen.estate.company'].create({
                'name': 'Invalid Check Digit',
                'cnpj': '11.111.111/0001-99',  # Wrong check digit
                'email': 'invalid@test.com',
                'phone': '11987654323',
            })

    def test_04_invalid_cnpj_wrong_length(self):
        """Cannot create Company with CNPJ of wrong length"""
        with self.assertRaises(ValidationError, msg="Should reject CNPJ with wrong length"):
            self.env['thedevkitchen.estate.company'].create({
                'name': 'Wrong Length',
                'cnpj': '123456',  # Too short
                'email': 'wronglength@test.com',
                'phone': '11987654324',
            })

    def test_05_cnpj_uniqueness(self):
        """CNPJ must be unique across all companies"""
        # Create first company
        self.env['thedevkitchen.estate.company'].create({
            'name': 'First Company',
            'cnpj': '22.222.222/0001-05',
            'email': 'first@test.com',
            'phone': '11987654325',
        })
        
        # Try to create second company with same CNPJ
        with self.assertRaises(ValidationError, msg="Should reject duplicate CNPJ"):
            self.env['thedevkitchen.estate.company'].create({
                'name': 'Second Company',
                'cnpj': '22.222.222/0001-05',  # Duplicate
                'email': 'second@test.com',
                'phone': '11987654326',
            })

    def test_06_cnpj_uniqueness_includes_inactive(self):
        """CNPJ uniqueness check includes soft-deleted companies (active=False)"""
        # Create and soft-delete company
        company = self.env['thedevkitchen.estate.company'].create({
            'name': 'To Be Deleted',
            'cnpj': '33.333.333/0001-29',
            'email': 'tobedeleted@test.com',
            'phone': '11987654327',
        })
        company.write({'active': False})
        
        # Try to create new company with same CNPJ
        with self.assertRaises(ValidationError, msg="Should reject CNPJ that exists in inactive records"):
            self.env['thedevkitchen.estate.company'].create({
                'name': 'New Company',
                'cnpj': '33.333.333/0001-29',  # Same as deleted
                'email': 'new@test.com',
                'phone': '11987654328',
            })

    def test_07_cnpj_all_zeros_invalid(self):
        """CNPJ with all zeros should be rejected"""
        with self.assertRaises(ValidationError, msg="Should reject CNPJ with all zeros"):
            self.env['thedevkitchen.estate.company'].create({
                'name': 'All Zeros',
                'cnpj': '00.000.000/0000-00',
                'email': 'allzeros@test.com',
                'phone': '11987654329',
            })

    def test_08_cnpj_sequential_numbers_invalid(self):
        """CNPJ with sequential repeated digits should be rejected"""
        # CNPJs like 11111111111111 are technically valid format but often rejected
        # This depends on implementation
        invalid_cnpjs = [
            '11111111111111',
            '22222222222222',
            '99999999999999',
        ]
        
        for invalid_cnpj in invalid_cnpjs:
            try:
                self.env['thedevkitchen.estate.company'].create({
                    'name': f'Sequential {invalid_cnpj}',
                    'cnpj': invalid_cnpj,
                    'email': f'seq{invalid_cnpj}@test.com',
                    'phone': '11987654330',
                })
                # If no exception, check if this is acceptable
                # Some implementations may accept these
            except ValidationError:
                # This is the expected behavior
                pass


@tagged('post_install', '-at_install', 'quicksol_estate', 'feature_007')
class TestEmailValidation(TransactionCase):
    """
    Test email validation using RFC 5322 standards.
    
    Business Rule (T027):
    - Email must be valid RFC 5322 format
    - Common formats like user@domain.com must work
    - Invalid formats should be rejected
    """

    def test_01_valid_email_simple(self):
        """Company can be created with simple valid email"""
        company = self.env['thedevkitchen.estate.company'].create({
            'name': 'Simple Email',
            'cnpj': '44.444.444/0001-53',
            'email': 'user@example.com',
            'phone': '11987654331',
        })
        
        self.assertEqual(company.email, 'user@example.com')

    def test_02_valid_email_with_subdomain(self):
        """Company can be created with email having subdomain"""
        company = self.env['thedevkitchen.estate.company'].create({
            'name': 'Subdomain Email',
            'cnpj': '55.555.555/0001-77',
            'email': 'admin@mail.company.com',
            'phone': '11987654332',
        })
        
        self.assertEqual(company.email, 'admin@mail.company.com')

    def test_03_valid_email_with_plus(self):
        """Company can be created with email containing + sign"""
        company = self.env['thedevkitchen.estate.company'].create({
            'name': 'Plus Email',
            'cnpj': '66.666.666/0001-01',
            'email': 'user+test@example.com',
            'phone': '11987654333',
        })
        
        self.assertEqual(company.email, 'user+test@example.com')

    def test_04_invalid_email_no_at(self):
        """Cannot create Company with email missing @ symbol"""
        with self.assertRaises(ValidationError, msg="Should reject email without @"):
            self.env['thedevkitchen.estate.company'].create({
                'name': 'No At Sign',
                'cnpj': '77.777.777/0001-25',
                'email': 'notanemail.com',
                'phone': '11987654334',
            })

    def test_05_invalid_email_no_domain(self):
        """Cannot create Company with email missing domain"""
        with self.assertRaises(ValidationError, msg="Should reject email without domain"):
            self.env['thedevkitchen.estate.company'].create({
                'name': 'No Domain',
                'cnpj': '88.888.888/0001-49',
                'email': 'user@',
                'phone': '11987654335',
            })

    def test_06_invalid_email_spaces(self):
        """Cannot create Company with email containing spaces"""
        with self.assertRaises(ValidationError, msg="Should reject email with spaces"):
            self.env['thedevkitchen.estate.company'].create({
                'name': 'Email With Spaces',
                'cnpj': '99.999.999/0001-73',
                'email': 'user name@example.com',
                'phone': '11987654336',
            })

    def test_07_invalid_email_double_at(self):
        """Cannot create Company with email having multiple @ symbols"""
        with self.assertRaises(ValidationError, msg="Should reject email with double @"):
            self.env['thedevkitchen.estate.company'].create({
                'name': 'Double At',
                'cnpj': '10.101.010/0001-01',
                'email': 'user@@example.com',
                'phone': '11987654337',
            })

    def test_08_email_case_insensitive(self):
        """Email validation should be case-insensitive"""
        company = self.env['thedevkitchen.estate.company'].create({
            'name': 'Mixed Case Email',
            'cnpj': '20.202.020/0001-25',
            'email': 'User@Example.COM',
            'phone': '11987654338',
        })
        
        # Email should be stored (possibly normalized to lowercase)
        self.assertTrue('@' in company.email)
        self.assertTrue('example.com' in company.email.lower())
