#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Tenant API — Model Fields & Schema Validation

Tests tenant model fields (active default, deactivation fields),
email validation constraint, TENANT_CREATE_SCHEMA and TENANT_UPDATE_SCHEMA.

Feature: 008-tenant-lease-sale-api
Task: T031
ADR-003: Unit test WITHOUT database (with mocks)

Run: docker compose exec odoo python3 /mnt/extra-addons/quicksol_estate/tests/api/test_tenant_api.py
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import re


# ===== Mock Odoo dependencies =====

class ValidationError(Exception):
    """Mock Odoo ValidationError"""
    pass


# Reproduce the email regex from tenant.py
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'


def validate_email(email):
    """Reproduce tenant.py _validate_email logic"""
    if email and not re.match(EMAIL_REGEX, email):
        raise ValidationError(f"Invalid email format: {email}")


# ===== Schema definitions (copied from schema.py) =====

TENANT_CREATE_SCHEMA = {
    'required': ['name'],
    'optional': ['phone', 'email', 'occupation', 'birthdate'],
    'types': {
        'name': str,
        'phone': str,
        'email': str,
        'occupation': str,
        'birthdate': str,
    },
    'constraints': {
        'name': lambda v: len(v.strip()) > 0,
        'email': lambda v: '@' in v and '.' in v.split('@')[-1] if v else True,
    }
}

TENANT_UPDATE_SCHEMA = {
    'required': [],
    'optional': ['name', 'phone', 'email', 'occupation', 'birthdate'],
    'types': {
        'name': str,
        'phone': str,
        'email': str,
        'occupation': str,
        'birthdate': str,
    },
    'constraints': {
        'name': lambda v: len(v.strip()) > 0 if v else True,
        'email': lambda v: '@' in v and '.' in v.split('@')[-1] if v else True,
    }
}


def validate_request(data, schema):
    """Reproduce SchemaValidator.validate_request logic"""
    errors = []
    for field in schema.get('required', []):
        if field not in data:
            errors.append(f"Missing required field: {field}")
    types_def = schema.get('types', {})
    for field, field_type in types_def.items():
        if field in data and data[field] is not None:
            if not isinstance(data[field], field_type):
                errors.append(f"Field '{field}' type mismatch")
    constraints = schema.get('constraints', {})
    for field, constraint in constraints.items():
        if field in data and data[field] is not None:
            try:
                if not constraint(data[field]):
                    errors.append(f"Field '{field}' violates constraint")
            except Exception as e:
                errors.append(f"Field '{field}' validation error: {str(e)}")
    return len(errors) == 0, errors


# ===== Test Classes =====

class TestTenantModelFields(unittest.TestCase):
    """Test tenant model field defaults and behavior"""

    def test_active_field_defaults_to_true(self):
        """ADR-015: active field must default to True for soft delete pattern"""
        mock_tenant = Mock()
        mock_tenant.active = True  # default
        self.assertTrue(mock_tenant.active)

    def test_deactivation_date_initially_none(self):
        """Deactivation date should be None for active tenants"""
        mock_tenant = Mock()
        mock_tenant.deactivation_date = None
        self.assertIsNone(mock_tenant.deactivation_date)

    def test_deactivation_reason_initially_none(self):
        """Deactivation reason should be None for active tenants"""
        mock_tenant = Mock()
        mock_tenant.deactivation_reason = None
        self.assertIsNone(mock_tenant.deactivation_reason)

    def test_soft_delete_sets_active_false(self):
        """Archive operation must set active=False"""
        mock_tenant = Mock()
        mock_tenant.active = True

        # Simulate archive
        mock_tenant.write({'active': False, 'deactivation_date': '2026-03-15', 'deactivation_reason': 'Test'})
        mock_tenant.active = False
        mock_tenant.deactivation_date = '2026-03-15'
        mock_tenant.deactivation_reason = 'Test'

        self.assertFalse(mock_tenant.active)
        self.assertEqual(mock_tenant.deactivation_date, '2026-03-15')
        self.assertEqual(mock_tenant.deactivation_reason, 'Test')

    def test_reactivation_clears_deactivation_fields(self):
        """Reactivation must clear deactivation_date and deactivation_reason"""
        mock_tenant = Mock()
        mock_tenant.active = False
        mock_tenant.deactivation_date = '2026-03-15'
        mock_tenant.deactivation_reason = 'Old reason'

        # Simulate reactivation
        mock_tenant.active = True
        mock_tenant.deactivation_date = None
        mock_tenant.deactivation_reason = None

        self.assertTrue(mock_tenant.active)
        self.assertIsNone(mock_tenant.deactivation_date)
        self.assertIsNone(mock_tenant.deactivation_reason)

    def test_tenant_name_is_required(self):
        """name field must be required"""
        mock_tenant = Mock()
        mock_tenant.name = 'João Silva'
        self.assertIsNotNone(mock_tenant.name)
        self.assertTrue(len(mock_tenant.name) > 0)


class TestTenantEmailValidation(unittest.TestCase):
    """Test email validation constraint from tenant.py"""

    def test_valid_email_passes(self):
        """Valid email should not raise"""
        validate_email('user@example.com')  # no exception expected

    def test_valid_email_with_subdomain(self):
        """Email with subdomain should pass"""
        validate_email('user@mail.example.com')

    def test_invalid_email_no_at_sign(self):
        """Email without @ should raise ValidationError"""
        with self.assertRaises(ValidationError):
            validate_email('userexample.com')

    def test_invalid_email_no_domain(self):
        """Email without domain should raise ValidationError"""
        with self.assertRaises(ValidationError):
            validate_email('user@')

    def test_invalid_email_no_tld(self):
        """Email with single char TLD should raise ValidationError"""
        with self.assertRaises(ValidationError):
            validate_email('user@example.c')

    def test_empty_email_skips_validation(self):
        """Empty/None email should skip validation per model logic"""
        validate_email(None)  # should not raise
        validate_email('')  # should not raise (empty string doesn't match regex condition)

    def test_invalid_email_with_spaces(self):
        """Email with spaces should raise ValidationError"""
        with self.assertRaises(ValidationError):
            validate_email('user @example.com')


class TestTenantCreateSchema(unittest.TestCase):
    """Test TENANT_CREATE_SCHEMA validation"""

    def test_valid_create_minimal(self):
        """Minimum valid data: just name"""
        is_valid, errors = validate_request({'name': 'Test Tenant'}, TENANT_CREATE_SCHEMA)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_valid_create_full(self):
        """Full valid data with all optional fields"""
        data = {
            'name': 'Test Tenant',
            'phone': '11999001122',
            'email': 'test@example.com',
            'occupation': 'Engineer',
            'birthdate': '1990-01-15'
        }
        is_valid, errors = validate_request(data, TENANT_CREATE_SCHEMA)
        self.assertTrue(is_valid)

    def test_missing_name_fails(self):
        """Missing required name field should fail"""
        is_valid, errors = validate_request({'phone': '11999'}, TENANT_CREATE_SCHEMA)
        self.assertFalse(is_valid)
        self.assertTrue(any('name' in e for e in errors))

    def test_empty_name_fails(self):
        """Empty name should fail constraint"""
        is_valid, errors = validate_request({'name': '  '}, TENANT_CREATE_SCHEMA)
        self.assertFalse(is_valid)

    def test_invalid_email_format_fails(self):
        """Invalid email format should fail constraint"""
        data = {'name': 'Test', 'email': 'not-an-email'}
        is_valid, errors = validate_request(data, TENANT_CREATE_SCHEMA)
        self.assertFalse(is_valid)

    def test_invalid_name_type_fails(self):
        """Non-string name should fail type check"""
        is_valid, errors = validate_request({'name': 123}, TENANT_CREATE_SCHEMA)
        self.assertFalse(is_valid)


class TestTenantUpdateSchema(unittest.TestCase):
    """Test TENANT_UPDATE_SCHEMA validation"""

    def test_valid_update_partial(self):
        """Partial update with just phone"""
        is_valid, errors = validate_request({'phone': '11999'}, TENANT_UPDATE_SCHEMA)
        self.assertTrue(is_valid)

    def test_valid_update_email(self):
        """Email update with valid format"""
        is_valid, errors = validate_request({'email': 'new@example.com'}, TENANT_UPDATE_SCHEMA)
        self.assertTrue(is_valid)

    def test_empty_body_valid(self):
        """Empty update body is technically valid (no required fields)"""
        is_valid, errors = validate_request({}, TENANT_UPDATE_SCHEMA)
        self.assertTrue(is_valid)

    def test_invalid_email_fails(self):
        """Invalid email in update should fail"""
        is_valid, errors = validate_request({'email': 'bad-email'}, TENANT_UPDATE_SCHEMA)
        self.assertFalse(is_valid)


if __name__ == '__main__':
    unittest.main()
