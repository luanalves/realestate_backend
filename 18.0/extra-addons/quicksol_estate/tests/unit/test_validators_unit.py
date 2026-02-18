# -*- coding: utf-8 -*-
"""
Unit Tests for Validator Functions (Feature 010 - T09)

Tests 4 new validator functions without Odoo/database access:
- normalize_document()
- is_cpf()
- is_cnpj()
- validate_document()

Run:
    docker compose exec odoo python3 /mnt/extra-addons/quicksol_estate/tests/unit/test_validators_unit.py
"""

import unittest
import sys
from pathlib import Path

# Add module to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.validators import normalize_document, is_cpf, is_cnpj, validate_document


class TestNormalizeDocument(unittest.TestCase):
    """Test normalize_document() strips non-digit characters"""
    
    def test_formatted_cpf(self):
        """CPF with formatting → digits only"""
        result = normalize_document('123.456.789-01')
        self.assertEqual(result, '12345678901')
    
    def test_formatted_cnpj(self):
        """CNPJ with formatting → digits only"""
        result = normalize_document('12.345.678/0001-95')
        self.assertEqual(result, '12345678000195')
    
    def test_already_clean(self):
        """Already clean document → unchanged"""
        result = normalize_document('12345678901')
        self.assertEqual(result, '12345678901')
    
    def test_empty_string(self):
        """Empty string → empty string"""
        result = normalize_document('')
        self.assertEqual(result, '')
    
    def test_mixed_special_chars(self):
        """Document with mixed special chars → digits only"""
        result = normalize_document('123-456.789/01')
        self.assertEqual(result, '12345678901')


class TestIsCpf(unittest.TestCase):
    """Test is_cpf() validates CPF checksum"""
    
    def test_valid_cpf(self):
        """Valid CPF passes checksum"""
        # CPF: 191.000.000-01 (valid checksum)
        self.assertTrue(is_cpf('19100000001'))
    
    def test_invalid_checksum(self):
        """Invalid CPF checksum fails"""
        self.assertFalse(is_cpf('19100000099'))
    
    def test_all_same_digits(self):
        """CPF with all same digits fails"""
        self.assertFalse(is_cpf('11111111111'))
        self.assertFalse(is_cpf('00000000000'))
        self.assertFalse(is_cpf('99999999999'))
    
    def test_wrong_length(self):
        """CPF with wrong length fails"""
        self.assertFalse(is_cpf('123456'))
        self.assertFalse(is_cpf('123456789012'))  # 12 digits
    
    def test_empty_cpf(self):
        """Empty CPF fails"""
        self.assertFalse(is_cpf(''))
    
    def test_another_valid_cpf(self):
        """Another valid CPF (52998224725)"""
        self.assertTrue(is_cpf('52998224725'))


class TestIsCnpj(unittest.TestCase):
    """Test is_cnpj() validates CNPJ"""
    
    def test_valid_cnpj(self):
        """Valid CNPJ passes"""
        # CNPJ: 11.222.333/0001-81 (valid)
        self.assertTrue(is_cnpj('11222333000181'))
    
    def test_invalid_cnpj(self):
        """Invalid CNPJ fails"""
        self.assertFalse(is_cnpj('11222333000199'))
    
    def test_wrong_length(self):
        """CNPJ with wrong length fails"""
        self.assertFalse(is_cnpj('123456'))
        self.assertFalse(is_cnpj('123456789012345'))  # 15 digits
    
    def test_empty_cnpj(self):
        """Empty CNPJ fails"""
        self.assertFalse(is_cnpj(''))


class TestValidateDocument(unittest.TestCase):
    """Test validate_document() dispatch logic"""
    
    def test_dispatch_to_cpf(self):
        """11 digits → dispatch to is_cpf"""
        # Valid CPF
        self.assertTrue(validate_document('19100000001'))
        # Invalid CPF
        self.assertFalse(validate_document('19100000099'))
    
    def test_dispatch_to_cnpj(self):
        """14 digits → dispatch to is_cnpj"""
        # Valid CNPJ
        self.assertTrue(validate_document('11222333000181'))
        # Invalid CNPJ
        self.assertFalse(validate_document('11222333000199'))
    
    def test_invalid_length(self):
        """Invalid length → False"""
        self.assertFalse(validate_document('123'))
        self.assertFalse(validate_document('123456'))
        self.assertFalse(validate_document('12345678901234567'))  # 17 digits
    
    def test_empty_document(self):
        """Empty document → False"""
        self.assertFalse(validate_document(''))
    
    def test_normalized_input(self):
        """Works with pre-normalized input"""
        # Already normalized valid CPF
        self.assertTrue(validate_document('52998224725'))
        # Already normalized valid CNPJ
        self.assertTrue(validate_document('11222333000181'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
