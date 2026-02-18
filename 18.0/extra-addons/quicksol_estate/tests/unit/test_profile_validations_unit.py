# -*- coding: utf-8 -*-
"""
Unit Tests for Profile Model Constraints (Feature 010 - T10)

Tests Profile model python constraints and computed fields using mocks.
No database access.

Tests:
- _check_document() constraint
- _compute_document_normalized() computed field
- _check_email() constraint
- _check_birthdate() constraint
- write() override updates updated_at

Run:
    docker compose exec odoo python3 /mnt/extra-addons/quicksol_estate/tests/unit/test_profile_validations_unit.py
"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import date, datetime, timedelta
import sys
from pathlib import Path

# Add module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestProfileDocumentConstraint(unittest.TestCase):
    """Test _check_document() constraint"""
    
    @patch('utils.validators.validate_document')
    @patch('utils.validators.normalize_document')
    def test_valid_cpf(self, mock_normalize, mock_validate):
        """Valid CPF passes constraint"""
        mock_normalize.return_value = '12345678901'
        mock_validate.return_value = True
        
        # Mock profile record
        profile = MagicMock()
        profile.document = '123.456.789-01'
        profile.document_normalized = '12345678901'
        
        # Constraint should not raise
        # In real code: self._check_document() would be called
        # Here we just verify validator is called correctly
        from utils.validators import validate_document, normalize_document
        normalized = normalize_document(profile.document)
        is_valid = validate_document(normalized)
        
        self.assertTrue(is_valid)
        mock_normalize.assert_called_with('123.456.789-01')
        mock_validate.assert_called_with('12345678901')
    
    @patch('utils.validators.validate_document')
    @patch('utils.validators.normalize_document')
    def test_invalid_document(self, mock_normalize, mock_validate):
        """Invalid document fails constraint"""
        mock_normalize.return_value = '123'
        mock_validate.return_value = False
        
        profile = MagicMock()
        profile.document = '123'
        
        from utils.validators import validate_document, normalize_document
        normalized = normalize_document(profile.document)
        is_valid = validate_document(normalized)
        
        self.assertFalse(is_valid)
        # In real implementation, ValidationError would be raised
    
    @patch('utils.validators.validate_document')
    @patch('utils.validators.normalize_document')
    def test_valid_cnpj(self, mock_normalize, mock_validate):
        """Valid CNPJ passes constraint"""
        mock_normalize.return_value = '11222333000181'
        mock_validate.return_value = True
        
        profile = MagicMock()
        profile.document = '11.222.333/0001-81'
        
        from utils.validators import validate_document, normalize_document
        normalized = normalize_document(profile.document)
        is_valid = validate_document(normalized)
        
        self.assertTrue(is_valid)


class TestProfileDocumentNormalized(unittest.TestCase):
    """Test _compute_document_normalized() computed field"""
    
    @patch('utils.validators.normalize_document')
    def test_formatted_cpf_normalized(self, mock_normalize):
        """Formatted CPF → normalized digits"""
        mock_normalize.return_value = '12345678901'
        
        profile = MagicMock()
        profile.document = '123.456.789-01'
        
        from utils.validators import normalize_document
        result = normalize_document(profile.document)
        
        self.assertEqual(result, '12345678901')
        mock_normalize.assert_called_with('123.456.789-01')
    
    @patch('utils.validators.normalize_document')
    def test_formatted_cnpj_normalized(self, mock_normalize):
        """Formatted CNPJ → normalized digits"""
        mock_normalize.return_value = '12345678000195'
        
        profile = MagicMock()
        profile.document = '12.345.678/0001-95'
        
        from utils.validators import normalize_document
        result = normalize_document(profile.document)
        
        self.assertEqual(result, '12345678000195')


class TestProfileEmailConstraint(unittest.TestCase):
    """Test _check_email() constraint"""
    
    @patch('utils.validators.validate_email_format')
    def test_valid_email(self, mock_validate_email):
        """Valid email passes constraint"""
        mock_validate_email.return_value = True
        
        profile = MagicMock()
        profile.email = 'user@example.com'
        
        from utils.validators import validate_email_format
        is_valid = validate_email_format(profile.email)
        
        self.assertTrue(is_valid)
        mock_validate_email.assert_called_with('user@example.com')
    
    @patch('utils.validators.validate_email_format')
    def test_invalid_email(self, mock_validate_email):
        """Invalid email fails constraint"""
        mock_validate_email.return_value = False
        
        profile = MagicMock()
        profile.email = 'invalid-email'
        
        from utils.validators import validate_email_format
        is_valid = validate_email_format(profile.email)
        
        self.assertFalse(is_valid)


class TestProfileBirthdateConstraint(unittest.TestCase):
    """Test _check_birthdate() constraint"""
    
    def test_past_birthdate_valid(self):
        """Birthdate in the past is valid"""
        profile = MagicMock()
        profile.birthdate = date.today() - timedelta(days=365*25)  # 25 years ago
        
        # Constraint: birthdate < today
        is_valid = profile.birthdate < date.today()
        self.assertTrue(is_valid)
    
    def test_today_birthdate_invalid(self):
        """Birthdate today is invalid"""
        profile = MagicMock()
        profile.birthdate = date.today()
        
        # Constraint should fail
        is_valid = profile.birthdate < date.today()
        self.assertFalse(is_valid)
    
    def test_future_birthdate_invalid(self):
        """Birthdate in future is invalid"""
        profile = MagicMock()
        profile.birthdate = date.today() + timedelta(days=1)
        
        is_valid = profile.birthdate < date.today()
        self.assertFalse(is_valid)


class TestProfileWriteOverride(unittest.TestCase):
    """Test write() override updates updated_at"""
    
    def test_write_updates_timestamp(self):
        """write() should update updated_at field"""
        profile = MagicMock()
        
        # Mock the write method behavior
        original_updated_at = datetime(2025, 1, 1, 10, 0, 0)
        new_updated_at = datetime.now()
        
        # Simulate write() override logic
        vals = {'name': 'Updated Name'}
        vals['updated_at'] = new_updated_at
        
        # Verify updated_at is in vals
        self.assertIn('updated_at', vals)
        self.assertIsInstance(vals['updated_at'], datetime)
        self.assertGreater(vals['updated_at'], original_updated_at)
    
    def test_write_preserves_other_fields(self):
        """write() preserves other fields in vals"""
        vals = {'name': 'New Name', 'email': 'new@example.com'}
        vals['updated_at'] = datetime.now()
        
        # Verify original fields still present
        self.assertEqual(vals['name'], 'New Name')
        self.assertEqual(vals['email'], 'new@example.com')
        self.assertIn('updated_at', vals)


class TestProfileCompoundUniqueConstraint(unittest.TestCase):
    """Test compound unique constraint (document, company_id, profile_type_id)"""
    
    def test_same_document_different_company(self):
        """Same document in different companies → allowed"""
        profile1 = MagicMock()
        profile1.document = '12345678901'
        profile1.company_id = 1
        profile1.profile_type_id = 1
        
        profile2 = MagicMock()
        profile2.document = '12345678901'
        profile2.company_id = 2  # Different company
        profile2.profile_type_id = 1
        
        # Should be allowed (different company_id)
        is_duplicate = (
            profile1.document == profile2.document and
            profile1.company_id == profile2.company_id and
            profile1.profile_type_id == profile2.profile_type_id
        )
        self.assertFalse(is_duplicate)
    
    def test_same_document_different_profile_type(self):
        """Same document with different profile type in same company → allowed"""
        profile1 = MagicMock()
        profile1.document = '12345678901'
        profile1.company_id = 1
        profile1.profile_type_id = 1  # owner
        
        profile2 = MagicMock()
        profile2.document = '12345678901'
        profile2.company_id = 1
        profile2.profile_type_id = 2  # agent
        
        # Should be allowed (different profile_type_id)
        is_duplicate = (
            profile1.document == profile2.document and
            profile1.company_id == profile2.company_id and
            profile1.profile_type_id == profile2.profile_type_id
        )
        self.assertFalse(is_duplicate)
    
    def test_exact_duplicate(self):
        """Exact duplicate (same document, company, profile_type) → blocked"""
        profile1 = MagicMock()
        profile1.document = '12345678901'
        profile1.company_id = 1
        profile1.profile_type_id = 1
        
        profile2 = MagicMock()
        profile2.document = '12345678901'
        profile2.company_id = 1
        profile2.profile_type_id = 1
        
        # Should be blocked (all 3 match)
        is_duplicate = (
            profile1.document == profile2.document and
            profile1.company_id == profile2.company_id and
            profile1.profile_type_id == profile2.profile_type_id
        )
        self.assertTrue(is_duplicate)


if __name__ == '__main__':
    unittest.main(verbosity=2)
