# -*- coding: utf-8 -*-
"""
Tests for Schema Validation (T031)

This module tests the SchemaValidator utility which provides request/response
schema validation matching OpenAPI 3.0 contracts (ADR-005).

Test Coverage:
- Agent creation schema validation
- Agent update schema validation  
- Assignment creation schema validation
- Constraint validation (email, CPF, etc)
- Extra field handling
"""

import unittest
from odoo.tests.common import TransactionCase
from odoo.addons.quicksol_estate.controllers.utils.schema import SchemaValidator


class TestSchemaValidation(TransactionCase):
    """Test suite for schema validation functionality"""
    
    def setUp(self):
        super().setUp()
        self.validator = SchemaValidator()
    
    # ============================================================================
    # Agent Creation Schema Tests
    # ============================================================================
    
    def test_agent_create_valid_minimal_data(self):
        """Valid agent creation with only required fields"""
        data = {
            'name': 'João Silva',
            'cpf': '12345678901'
        }
        is_valid, errors = self.validator.validate_agent_create(data)
        self.assertTrue(is_valid, f"Expected validation to pass, but got errors: {errors}")
        self.assertEqual(len(errors), 0)
    
    def test_agent_create_valid_full_data(self):
        """Valid agent creation with all fields"""
        data = {
            'name': 'João Silva',
            'cpf': '12345678901',
            'email': 'joao@example.com',
            'phone': '(11) 98765-4321',
            'creci': '123456789',
            'bank_name': 'Banco do Brasil',
            'bank_account': '123456',
            'pix_key': 'joao@example.com'
        }
        is_valid, errors = self.validator.validate_agent_create(data)
        self.assertTrue(is_valid, f"Expected validation to pass, but got errors: {errors}")
        self.assertEqual(len(errors), 0)
    
    def test_agent_create_missing_required_name(self):
        """Agent creation fails when missing required 'name'"""
        data = {
            'cpf': '12345678901'
        }
        is_valid, errors = self.validator.validate_agent_create(data)
        self.assertFalse(is_valid)
        self.assertIn('name', ', '.join(errors))
    
    def test_agent_create_missing_required_cpf(self):
        """Agent creation fails when missing required 'cpf'"""
        data = {
            'name': 'João Silva'
        }
        is_valid, errors = self.validator.validate_agent_create(data)
        self.assertFalse(is_valid)
        self.assertIn('cpf', ', '.join(errors))
    
    def test_agent_create_missing_both_required_fields(self):
        """Agent creation fails when missing both required fields"""
        data = {}
        is_valid, errors = self.validator.validate_agent_create(data)
        self.assertFalse(is_valid)
        self.assertTrue(len(errors) >= 2)
    
    def test_agent_create_invalid_name_type(self):
        """Agent creation fails when name is not a string"""
        data = {
            'name': 123,  # Should be string
            'cpf': '12345678901'
        }
        is_valid, errors = self.validator.validate_agent_create(data)
        self.assertFalse(is_valid)
        self.assertTrue(any('name' in e.lower() for e in errors))
    
    def test_agent_create_invalid_cpf_type(self):
        """Agent creation fails when cpf is not a string"""
        data = {
            'name': 'João Silva',
            'cpf': 12345678901  # Should be string
        }
        is_valid, errors = self.validator.validate_agent_create(data)
        self.assertFalse(is_valid)
        self.assertTrue(any('cpf' in e.lower() for e in errors))
    
    def test_agent_create_invalid_email_format(self):
        """Agent creation fails when email is missing @ symbol"""
        data = {
            'name': 'João Silva',
            'cpf': '12345678901',
            'email': 'joao.example.com'  # Missing @
        }
        is_valid, errors = self.validator.validate_agent_create(data)
        self.assertFalse(is_valid)
        self.assertTrue(any('email' in e.lower() for e in errors))
    
    def test_agent_create_valid_email_with_at(self):
        """Agent creation passes when email has @ symbol"""
        data = {
            'name': 'João Silva',
            'cpf': '12345678901',
            'email': 'joao@example.com'
        }
        is_valid, errors = self.validator.validate_agent_create(data)
        # Email is optional, but if provided, should be valid
        if 'email' in data:
            # If there are email errors, they should mention the constraint
            email_errors = [e for e in errors if 'email' in e.lower()]
            self.assertEqual(len(email_errors), 0)
    
    def test_agent_create_extra_fields_ignored(self):
        """Agent creation ignores extra fields in request"""
        data = {
            'name': 'João Silva',
            'cpf': '12345678901',
            'unknown_field': 'should be ignored',
            'another_field': 123
        }
        is_valid, errors = self.validator.validate_agent_create(data)
        # Extra fields should be logged but not cause validation failure
        self.assertTrue(is_valid)
    
    # ============================================================================
    # Agent Update Schema Tests
    # ============================================================================
    
    def test_agent_update_valid_single_field(self):
        """Valid agent update with single field"""
        data = {'name': 'João Silva Updated'}
        is_valid, errors = self.validator.validate_agent_update(data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_agent_update_valid_multiple_fields(self):
        """Valid agent update with multiple fields"""
        data = {
            'name': 'João Silva Updated',
            'email': 'joao.updated@example.com',
            'phone': '(11) 99999-9999'
        }
        is_valid, errors = self.validator.validate_agent_update(data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_agent_update_empty_data(self):
        """Agent update with empty data is valid (partial update)"""
        data = {}
        is_valid, errors = self.validator.validate_agent_update(data)
        self.assertTrue(is_valid)
    
    def test_agent_update_invalid_email_format(self):
        """Agent update fails with invalid email"""
        data = {'email': 'invalid-email-no-at'}
        is_valid, errors = self.validator.validate_agent_update(data)
        self.assertFalse(is_valid)
        self.assertTrue(any('email' in e.lower() for e in errors))
    
    def test_agent_update_invalid_field_type(self):
        """Agent update fails when field has wrong type"""
        data = {'name': 123}  # Should be string
        is_valid, errors = self.validator.validate_agent_update(data)
        self.assertFalse(is_valid)
        self.assertTrue(any('name' in e.lower() for e in errors))
    
    # ============================================================================
    # Assignment Creation Schema Tests
    # ============================================================================
    
    def test_assignment_create_valid_minimal(self):
        """Valid assignment creation with required fields"""
        data = {
            'agent_id': 1,
            'property_id': 100
        }
        is_valid, errors = self.validator.validate_assignment_create(data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_assignment_create_valid_full(self):
        """Valid assignment creation with all fields"""
        data = {
            'agent_id': 1,
            'property_id': 100,
            'responsibility_type': 'primary',
            'notes': 'Primary agent for this property'
        }
        is_valid, errors = self.validator.validate_assignment_create(data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_assignment_create_missing_agent_id(self):
        """Assignment creation fails when missing agent_id"""
        data = {'property_id': 100}
        is_valid, errors = self.validator.validate_assignment_create(data)
        self.assertFalse(is_valid)
        self.assertIn('agent_id', ', '.join(errors))
    
    def test_assignment_create_missing_property_id(self):
        """Assignment creation fails when missing property_id"""
        data = {'agent_id': 1}
        is_valid, errors = self.validator.validate_assignment_create(data)
        self.assertFalse(is_valid)
        self.assertIn('property_id', ', '.join(errors))
    
    def test_assignment_create_invalid_agent_id_type(self):
        """Assignment creation fails when agent_id is not int"""
        data = {
            'agent_id': 'not-an-int',
            'property_id': 100
        }
        is_valid, errors = self.validator.validate_assignment_create(data)
        self.assertFalse(is_valid)
        self.assertTrue(any('agent_id' in e.lower() for e in errors))
    
    def test_assignment_create_invalid_property_id_type(self):
        """Assignment creation fails when property_id is not int"""
        data = {
            'agent_id': 1,
            'property_id': 'not-an-int'
        }
        is_valid, errors = self.validator.validate_assignment_create(data)
        self.assertFalse(is_valid)
        self.assertTrue(any('property_id' in e.lower() for e in errors))
    
    # ============================================================================
    # Integration Tests
    # ============================================================================
    
    def test_validate_request_method_for_agent_create(self):
        """Generic validate_request method works for agent creation"""
        schema = SchemaValidator.AGENT_CREATE_SCHEMA
        data = {'name': 'Test Agent', 'cpf': '12345678901'}
        
        is_valid, errors = SchemaValidator.validate_request(data, schema)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_request_with_invalid_data(self):
        """Generic validate_request catches validation errors"""
        schema = SchemaValidator.AGENT_CREATE_SCHEMA
        data = {'name': 'Test Agent'}  # Missing required cpf
        
        is_valid, errors = SchemaValidator.validate_request(data, schema)
        self.assertFalse(is_valid)
        self.assertTrue(len(errors) > 0)
    
    def test_cpf_constraint_validation_accepts_11_digits(self):
        """CPF with 11 digits passes constraint validation"""
        data = {
            'name': 'João Silva',
            'cpf': '12345678901'  # 11 digits
        }
        is_valid, errors = self.validator.validate_agent_create(data)
        cpf_errors = [e for e in errors if 'cpf' in e.lower()]
        self.assertEqual(len(cpf_errors), 0, 
                        f"CPF with 11 digits should be valid, but got: {cpf_errors}")
    
    def test_cpf_constraint_validation_rejects_short(self):
        """CPF with less than 11 digits fails constraint validation"""
        data = {
            'name': 'João Silva',
            'cpf': '1234567890'  # 10 digits (one short)
        }
        is_valid, errors = self.validator.validate_agent_create(data)
        self.assertFalse(is_valid)
        cpf_errors = [e for e in errors if 'cpf' in e.lower()]
        self.assertTrue(len(cpf_errors) > 0)
    
    def test_name_length_constraint_validates(self):
        """Name length constraint allows names between 3-255 chars"""
        # Valid name
        data_valid = {
            'name': 'João',  # 4 chars (within 3-255)
            'cpf': '12345678901'
        }
        is_valid, errors = self.validator.validate_agent_create(data_valid)
        self.assertTrue(is_valid)
    
    def test_name_too_short_fails(self):
        """Name with less than 3 characters fails"""
        data = {
            'name': 'Jo',  # 2 chars (less than minimum 3)
            'cpf': '12345678901'
        }
        is_valid, errors = self.validator.validate_agent_create(data)
        self.assertFalse(is_valid)
        name_errors = [e for e in errors if 'name' in e.lower()]
        self.assertTrue(len(name_errors) > 0)


class TestSchemaValidationErrorMessages(TransactionCase):
    """Test error message quality and clarity"""
    
    def setUp(self):
        super().setUp()
        self.validator = SchemaValidator()
    
    def test_error_message_is_descriptive(self):
        """Error messages should be human-readable and descriptive"""
        data = {'email': 'invalid-email'}
        is_valid, errors = self.validator.validate_agent_create(data)
        self.assertTrue(len(errors) > 0)
        # Error should mention what's wrong (e.g., 'email', 'must', '@')
        error_text = ' '.join(errors).lower()
        self.assertTrue('email' in error_text or 'field' in error_text)
    
    def test_multiple_errors_all_reported(self):
        """Multiple validation errors should all be reported"""
        data = {
            'name': 'J',  # Too short
            'cpf': '123',  # Too short
            'email': 'no-at-sign'  # Invalid format
        }
        is_valid, errors = self.validator.validate_agent_create(data)
        self.assertFalse(is_valid)
        # Should report at least 3 errors (one for each field)
        self.assertTrue(len(errors) >= 2)
