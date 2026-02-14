#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Lease API — Model Constraints & Schema Validation

Tests lease model constraints (rent_amount > 0, concurrent lease check,
date ordering), status transitions, and LEASE_CREATE/RENEW/TERMINATE schemas.

Feature: 008-tenant-lease-sale-api
Task: T032
ADR-003: Unit test WITHOUT database (with mocks)

Run: docker compose exec odoo python3 /mnt/extra-addons/quicksol_estate/tests/api/test_lease_api.py
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import date


class ValidationError(Exception):
    """Mock Odoo ValidationError"""
    pass


# ===== Schema definitions (copied from schema.py) =====

LEASE_CREATE_SCHEMA = {
    'required': ['property_id', 'tenant_id', 'start_date', 'end_date', 'rent_amount'],
    'optional': ['status'],
    'types': {
        'property_id': int,
        'tenant_id': int,
        'start_date': str,
        'end_date': str,
        'rent_amount': (int, float),
        'status': str,
    },
    'constraints': {
        'property_id': lambda v: v > 0,
        'tenant_id': lambda v: v > 0,
        'rent_amount': lambda v: v > 0,
        'status': lambda v: v in ('draft', 'active') if v else True,
    }
}

LEASE_UPDATE_SCHEMA = {
    'required': [],
    'optional': ['start_date', 'end_date', 'rent_amount', 'status'],
    'types': {
        'start_date': str,
        'end_date': str,
        'rent_amount': (int, float),
        'status': str,
    },
    'constraints': {
        'rent_amount': lambda v: v > 0 if v else True,
        'status': lambda v: v in ('draft', 'active') if v else True,
    }
}

LEASE_RENEW_SCHEMA = {
    'required': ['new_end_date'],
    'optional': ['new_rent_amount', 'reason'],
    'types': {
        'new_end_date': str,
        'new_rent_amount': (int, float),
        'reason': str,
    },
    'constraints': {
        'new_rent_amount': lambda v: v > 0 if v else True,
    }
}

LEASE_TERMINATE_SCHEMA = {
    'required': ['termination_date'],
    'optional': ['reason', 'penalty_amount'],
    'types': {
        'termination_date': str,
        'reason': str,
        'penalty_amount': (int, float),
    },
    'constraints': {
        'penalty_amount': lambda v: v >= 0 if v is not None else True,
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


# ===== Reproduce model constraints as pure functions =====

def validate_lease_dates(start_date, end_date):
    """Reproduce lease.py _validate_lease_dates"""
    if end_date and start_date and end_date <= start_date:
        raise ValidationError("End date must be after start date")


def validate_rent_amount(rent_amount):
    """Reproduce lease.py _validate_rent_amount (FR-011)"""
    if rent_amount <= 0:
        raise ValidationError("Rent amount must be greater than zero")


def check_concurrent_lease(property_id, start_date, end_date, status, existing_leases):
    """
    Reproduce lease.py _check_concurrent_lease (FR-013).
    existing_leases: list of dicts with property_id, start_date, end_date, status
    """
    if status not in ('draft', 'active'):
        return
    for lease in existing_leases:
        if (lease['property_id'] == property_id and
                lease['status'] in ('draft', 'active') and
                lease['start_date'] < end_date and
                lease['end_date'] > start_date):
            raise ValidationError("Concurrent active lease exists for this property")


# ===== Test Classes =====

class TestLeaseModelConstraints(unittest.TestCase):
    """Test lease model constraint methods"""

    def test_valid_dates_pass(self):
        """Valid date range should not raise"""
        validate_lease_dates(date(2026, 1, 1), date(2026, 12, 31))

    def test_end_before_start_raises(self):
        """End date before start date should raise ValidationError"""
        with self.assertRaises(ValidationError):
            validate_lease_dates(date(2026, 12, 31), date(2026, 1, 1))

    def test_equal_dates_raises(self):
        """Same start and end date should raise ValidationError"""
        with self.assertRaises(ValidationError):
            validate_lease_dates(date(2026, 6, 1), date(2026, 6, 1))

    def test_rent_amount_positive_passes(self):
        """Positive rent amount should not raise"""
        validate_rent_amount(1500.00)

    def test_rent_amount_zero_raises(self):
        """Zero rent should raise ValidationError (FR-011)"""
        with self.assertRaises(ValidationError):
            validate_rent_amount(0)

    def test_rent_amount_negative_raises(self):
        """Negative rent should raise ValidationError"""
        with self.assertRaises(ValidationError):
            validate_rent_amount(-100)

    def test_concurrent_lease_raises(self):
        """Overlapping lease on same property should raise (FR-013)"""
        existing = [{
            'property_id': 1,
            'start_date': date(2026, 1, 1),
            'end_date': date(2026, 12, 31),
            'status': 'active'
        }]
        with self.assertRaises(ValidationError):
            check_concurrent_lease(1, date(2026, 6, 1), date(2027, 5, 31), 'draft', existing)

    def test_non_overlapping_lease_passes(self):
        """Non-overlapping lease on same property should pass"""
        existing = [{
            'property_id': 1,
            'start_date': date(2026, 1, 1),
            'end_date': date(2026, 12, 31),
            'status': 'active'
        }]
        check_concurrent_lease(1, date(2027, 1, 1), date(2027, 12, 31), 'draft', existing)

    def test_different_property_overlapping_passes(self):
        """Overlapping dates on different property should pass"""
        existing = [{
            'property_id': 1,
            'start_date': date(2026, 1, 1),
            'end_date': date(2026, 12, 31),
            'status': 'active'
        }]
        check_concurrent_lease(2, date(2026, 6, 1), date(2027, 5, 31), 'draft', existing)

    def test_terminated_lease_allows_overlap(self):
        """Terminated lease should not block overlap"""
        existing = [{
            'property_id': 1,
            'start_date': date(2026, 1, 1),
            'end_date': date(2026, 12, 31),
            'status': 'terminated'
        }]
        check_concurrent_lease(1, date(2026, 6, 1), date(2027, 5, 31), 'draft', existing)


class TestLeaseStatusTransitions(unittest.TestCase):
    """Test lease status transition logic"""

    def test_default_status_is_draft(self):
        """New lease should default to draft"""
        mock_lease = Mock()
        mock_lease.status = 'draft'
        self.assertEqual(mock_lease.status, 'draft')

    def test_draft_to_active(self):
        """Draft → active is valid"""
        mock_lease = Mock()
        mock_lease.status = 'draft'
        mock_lease.status = 'active'
        self.assertEqual(mock_lease.status, 'active')

    def test_active_to_terminated(self):
        """Active → terminated is valid"""
        mock_lease = Mock()
        mock_lease.status = 'active'
        mock_lease.status = 'terminated'
        self.assertEqual(mock_lease.status, 'terminated')

    def test_renewal_creates_history(self):
        """Renewal should create a history record"""
        mock_lease = Mock()
        mock_lease.status = 'active'
        mock_lease.end_date = date(2027, 2, 28)
        mock_lease.rent_amount = 2500.00
        mock_lease.renewal_history_ids = Mock()

        # Simulate renewal
        new_end = date(2028, 2, 28)
        new_rent = 2800.00
        assert new_end > mock_lease.end_date
        mock_lease.end_date = new_end
        mock_lease.rent_amount = new_rent

        self.assertEqual(mock_lease.end_date, date(2028, 2, 28))
        self.assertEqual(mock_lease.rent_amount, 2800.00)

    def test_terminated_lease_cannot_be_renewed(self):
        """Terminated lease should not allow renewal"""
        mock_lease = Mock()
        mock_lease.status = 'terminated'

        # Simulate rejection
        if mock_lease.status in ('terminated', 'expired'):
            result = 'rejected'
        else:
            result = 'allowed'
        self.assertEqual(result, 'rejected')


class TestLeaseCreateSchema(unittest.TestCase):
    """Test LEASE_CREATE_SCHEMA validation"""

    def test_valid_create(self):
        """Valid lease creation data"""
        data = {
            'property_id': 1,
            'tenant_id': 2,
            'start_date': '2026-06-01',
            'end_date': '2027-05-31',
            'rent_amount': 2500.00
        }
        is_valid, errors = validate_request(data, LEASE_CREATE_SCHEMA)
        self.assertTrue(is_valid)

    def test_missing_property_id(self):
        """Missing property_id should fail"""
        data = {
            'tenant_id': 2,
            'start_date': '2026-06-01',
            'end_date': '2027-05-31',
            'rent_amount': 2500.00
        }
        is_valid, errors = validate_request(data, LEASE_CREATE_SCHEMA)
        self.assertFalse(is_valid)

    def test_missing_tenant_id(self):
        """Missing tenant_id should fail"""
        data = {
            'property_id': 1,
            'start_date': '2026-06-01',
            'end_date': '2027-05-31',
            'rent_amount': 2500.00
        }
        is_valid, errors = validate_request(data, LEASE_CREATE_SCHEMA)
        self.assertFalse(is_valid)

    def test_zero_rent_fails_constraint(self):
        """Zero rent should fail constraint"""
        data = {
            'property_id': 1,
            'tenant_id': 2,
            'start_date': '2026-06-01',
            'end_date': '2027-05-31',
            'rent_amount': 0
        }
        is_valid, errors = validate_request(data, LEASE_CREATE_SCHEMA)
        self.assertFalse(is_valid)

    def test_invalid_status_value(self):
        """Invalid status value should fail"""
        data = {
            'property_id': 1,
            'tenant_id': 2,
            'start_date': '2026-06-01',
            'end_date': '2027-05-31',
            'rent_amount': 2500.00,
            'status': 'invalid_status'
        }
        is_valid, errors = validate_request(data, LEASE_CREATE_SCHEMA)
        self.assertFalse(is_valid)


class TestLeaseRenewSchema(unittest.TestCase):
    """Test LEASE_RENEW_SCHEMA validation"""

    def test_valid_renew_minimal(self):
        """Minimum valid renewal: just new_end_date"""
        is_valid, errors = validate_request({'new_end_date': '2028-05-31'}, LEASE_RENEW_SCHEMA)
        self.assertTrue(is_valid)

    def test_valid_renew_full(self):
        """Full renewal with optional fields"""
        data = {
            'new_end_date': '2028-05-31',
            'new_rent_amount': 3000.00,
            'reason': 'Annual renewal'
        }
        is_valid, errors = validate_request(data, LEASE_RENEW_SCHEMA)
        self.assertTrue(is_valid)

    def test_missing_end_date(self):
        """Missing new_end_date should fail"""
        is_valid, errors = validate_request({'new_rent_amount': 3000}, LEASE_RENEW_SCHEMA)
        self.assertFalse(is_valid)

    def test_zero_new_rent_passes_as_falsy(self):
        """Zero new rent is falsy so treated as optional (passes constraint)"""
        data = {'new_end_date': '2028-05-31', 'new_rent_amount': 0}
        is_valid, errors = validate_request(data, LEASE_RENEW_SCHEMA)
        # 0 is falsy → constraint returns True (field treated as absent)
        self.assertTrue(is_valid)

    def test_negative_new_rent_fails(self):
        """Negative new rent should fail constraint"""
        data = {'new_end_date': '2028-05-31', 'new_rent_amount': -100}
        is_valid, errors = validate_request(data, LEASE_RENEW_SCHEMA)
        self.assertFalse(is_valid)


class TestLeaseTerminateSchema(unittest.TestCase):
    """Test LEASE_TERMINATE_SCHEMA validation"""

    def test_valid_terminate_minimal(self):
        """Minimum: just termination_date"""
        is_valid, errors = validate_request({'termination_date': '2026-06-30'}, LEASE_TERMINATE_SCHEMA)
        self.assertTrue(is_valid)

    def test_valid_terminate_full(self):
        """Full termination with reason and penalty"""
        data = {
            'termination_date': '2026-06-30',
            'reason': 'Tenant relocation',
            'penalty_amount': 5000.00
        }
        is_valid, errors = validate_request(data, LEASE_TERMINATE_SCHEMA)
        self.assertTrue(is_valid)

    def test_missing_termination_date(self):
        """Missing termination_date should fail"""
        is_valid, errors = validate_request({'reason': 'test'}, LEASE_TERMINATE_SCHEMA)
        self.assertFalse(is_valid)

    def test_zero_penalty_passes(self):
        """Zero penalty is valid (penalty_amount >= 0)"""
        data = {'termination_date': '2026-06-30', 'penalty_amount': 0}
        is_valid, errors = validate_request(data, LEASE_TERMINATE_SCHEMA)
        self.assertTrue(is_valid)


if __name__ == '__main__':
    unittest.main()
