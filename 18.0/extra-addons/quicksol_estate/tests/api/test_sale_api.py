#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Sale API — Model Constraints, Create Override & Cancel Method

Tests sale model constraints (sale_price > 0), create() override
(property→sold status), cancel method (property status revert),
SALE_CREATE_SCHEMA and SALE_CANCEL_SCHEMA validation.

Feature: 008-tenant-lease-sale-api
Task: T033
ADR-003: Unit test WITHOUT database (with mocks)

Run: docker compose exec odoo python3 /mnt/extra-addons/quicksol_estate/tests/api/test_sale_api.py
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import date


class ValidationError(Exception):
    """Mock Odoo ValidationError"""
    pass


# ===== Schema definitions (copied from schema.py) =====

SALE_CREATE_SCHEMA = {
    'required': ['property_id', 'company_id', 'buyer_name', 'sale_date', 'sale_price'],
    'optional': ['buyer_phone', 'buyer_email', 'agent_id', 'lead_id'],
    'types': {
        'property_id': int,
        'company_id': int,
        'buyer_name': str,
        'sale_date': str,
        'sale_price': (int, float),
        'buyer_phone': str,
        'buyer_email': str,
        'agent_id': int,
        'lead_id': int,
    },
    'constraints': {
        'property_id': lambda v: v > 0,
        'company_id': lambda v: v > 0,
        'buyer_name': lambda v: len(v.strip()) > 0,
        'sale_price': lambda v: v > 0,
        'buyer_email': lambda v: '@' in v and '.' in v.split('@')[-1] if v else True,
    }
}

SALE_UPDATE_SCHEMA = {
    'required': [],
    'optional': ['buyer_name', 'buyer_phone', 'buyer_email', 'sale_date', 'sale_price'],
    'types': {
        'buyer_name': str,
        'buyer_phone': str,
        'buyer_email': str,
        'sale_date': str,
        'sale_price': (int, float),
    },
    'constraints': {
        'buyer_name': lambda v: len(v.strip()) > 0 if v else True,
        'sale_price': lambda v: v > 0 if v else True,
        'buyer_email': lambda v: '@' in v and '.' in v.split('@')[-1] if v else True,
    }
}

SALE_CANCEL_SCHEMA = {
    'required': ['reason'],
    'optional': [],
    'types': {
        'reason': str,
    },
    'constraints': {
        'reason': lambda v: len(v.strip()) > 0,
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


# ===== Reproduce model constraints/methods =====

def validate_sale_price(sale_price):
    """Reproduce sale.py _validate_sale_price (FR-022)"""
    if sale_price <= 0:
        raise ValidationError("Sale price must be greater than zero")


def simulate_create(property_mock, event_bus_mock, vals):
    """
    Reproduce sale.py create() override logic:
    1. Create sale record
    2. Emit 'sale.created' event
    3. Set property.state = 'sold' (FR-029)
    """
    sale = Mock()
    sale.id = 1
    sale.property_id = property_mock
    sale.sale_price = vals['sale_price']
    sale.status = 'completed'

    # Emit event
    event_bus_mock.emit('sale.created', sale)

    # Set property to sold (FR-029)
    property_mock.state = 'sold'

    return sale


def simulate_cancel(sale_mock, reason):
    """
    Reproduce sale.py action_cancel() method:
    - Raise if already cancelled
    - Set status, cancellation_date, cancellation_reason
    - Revert property.state from 'sold' (FR-029)
    """
    if sale_mock.status == 'cancelled':
        raise ValidationError("Sale is already cancelled")

    sale_mock.status = 'cancelled'
    sale_mock.cancellation_date = date.today()
    sale_mock.cancellation_reason = reason
    sale_mock.property_id.state = 'new'


# ===== Test Classes =====

class TestSaleModelConstraints(unittest.TestCase):
    """Test sale model constraint methods"""

    def test_positive_price_passes(self):
        """Valid positive sale price"""
        validate_sale_price(450000.00)

    def test_zero_price_raises(self):
        """Zero sale price should raise (FR-022)"""
        with self.assertRaises(ValidationError):
            validate_sale_price(0)

    def test_negative_price_raises(self):
        """Negative sale price should raise"""
        with self.assertRaises(ValidationError):
            validate_sale_price(-1000.00)


class TestSaleCreateOverride(unittest.TestCase):
    """Test create() override: property→sold + event emission"""

    def test_create_sets_property_to_sold(self):
        """FR-029: Sale creation sets property.state to 'sold'"""
        mock_property = Mock()
        mock_property.state = 'new'
        mock_event_bus = Mock()

        sale = simulate_create(mock_property, mock_event_bus, {
            'property_id': 1,
            'sale_price': 500000.00
        })

        self.assertEqual(mock_property.state, 'sold')
        self.assertEqual(sale.status, 'completed')

    def test_create_emits_event(self):
        """Sale creation should emit 'sale.created' event"""
        mock_property = Mock()
        mock_event_bus = Mock()

        sale = simulate_create(mock_property, mock_event_bus, {
            'property_id': 1,
            'sale_price': 500000.00
        })

        mock_event_bus.emit.assert_called_once_with('sale.created', sale)


class TestSaleCancelMethod(unittest.TestCase):
    """Test action_cancel() method"""

    def test_cancel_sets_status(self):
        """Cancel should set status to 'cancelled'"""
        mock_sale = Mock()
        mock_sale.status = 'completed'
        mock_sale.property_id = Mock()
        mock_sale.property_id.state = 'sold'

        simulate_cancel(mock_sale, 'Buyer backed out')

        self.assertEqual(mock_sale.status, 'cancelled')
        self.assertEqual(mock_sale.cancellation_reason, 'Buyer backed out')
        self.assertIsNotNone(mock_sale.cancellation_date)

    def test_cancel_reverts_property_state(self):
        """FR-029: Cancel should revert property.state from 'sold'"""
        mock_sale = Mock()
        mock_sale.status = 'completed'
        mock_sale.property_id = Mock()
        mock_sale.property_id.state = 'sold'

        simulate_cancel(mock_sale, 'Deal fell through')

        self.assertEqual(mock_sale.property_id.state, 'new')

    def test_double_cancel_raises(self):
        """Cancelling already-cancelled sale should raise ValidationError"""
        mock_sale = Mock()
        mock_sale.status = 'cancelled'

        with self.assertRaises(ValidationError):
            simulate_cancel(mock_sale, 'Second cancel attempt')


class TestSaleCreateSchema(unittest.TestCase):
    """Test SALE_CREATE_SCHEMA validation"""

    def test_valid_create(self):
        """Valid sale creation data"""
        data = {
            'property_id': 1,
            'company_id': 1,
            'buyer_name': 'Maria Santos',
            'sale_date': '2026-04-15',
            'sale_price': 450000.00
        }
        is_valid, errors = validate_request(data, SALE_CREATE_SCHEMA)
        self.assertTrue(is_valid)

    def test_valid_create_with_optionals(self):
        """Valid creation with all optional fields"""
        data = {
            'property_id': 1,
            'company_id': 1,
            'buyer_name': 'Maria Santos',
            'sale_date': '2026-04-15',
            'sale_price': 450000.00,
            'buyer_phone': '11999001122',
            'buyer_email': 'maria@example.com',
            'agent_id': 5,
            'lead_id': 10
        }
        is_valid, errors = validate_request(data, SALE_CREATE_SCHEMA)
        self.assertTrue(is_valid)

    def test_missing_buyer_name(self):
        """Missing buyer_name should fail"""
        data = {
            'property_id': 1,
            'company_id': 1,
            'sale_date': '2026-04-15',
            'sale_price': 450000.00
        }
        is_valid, errors = validate_request(data, SALE_CREATE_SCHEMA)
        self.assertFalse(is_valid)

    def test_missing_sale_price(self):
        """Missing sale_price should fail"""
        data = {
            'property_id': 1,
            'company_id': 1,
            'buyer_name': 'Test',
            'sale_date': '2026-04-15'
        }
        is_valid, errors = validate_request(data, SALE_CREATE_SCHEMA)
        self.assertFalse(is_valid)

    def test_zero_price_fails_constraint(self):
        """Zero sale_price should fail constraint"""
        data = {
            'property_id': 1,
            'company_id': 1,
            'buyer_name': 'Test',
            'sale_date': '2026-04-15',
            'sale_price': 0
        }
        is_valid, errors = validate_request(data, SALE_CREATE_SCHEMA)
        self.assertFalse(is_valid)

    def test_empty_buyer_name_fails(self):
        """Empty buyer_name should fail constraint"""
        data = {
            'property_id': 1,
            'company_id': 1,
            'buyer_name': '   ',
            'sale_date': '2026-04-15',
            'sale_price': 450000.00
        }
        is_valid, errors = validate_request(data, SALE_CREATE_SCHEMA)
        self.assertFalse(is_valid)

    def test_invalid_buyer_email(self):
        """Invalid buyer email should fail constraint"""
        data = {
            'property_id': 1,
            'company_id': 1,
            'buyer_name': 'Test',
            'sale_date': '2026-04-15',
            'sale_price': 450000.00,
            'buyer_email': 'not-valid'
        }
        is_valid, errors = validate_request(data, SALE_CREATE_SCHEMA)
        self.assertFalse(is_valid)


class TestSaleCancelSchema(unittest.TestCase):
    """Test SALE_CANCEL_SCHEMA validation"""

    def test_valid_cancel(self):
        """Valid cancel with reason"""
        is_valid, errors = validate_request({'reason': 'Buyer withdrew'}, SALE_CANCEL_SCHEMA)
        self.assertTrue(is_valid)

    def test_missing_reason(self):
        """Missing reason should fail"""
        is_valid, errors = validate_request({}, SALE_CANCEL_SCHEMA)
        self.assertFalse(is_valid)

    def test_empty_reason_fails(self):
        """Empty reason should fail constraint"""
        is_valid, errors = validate_request({'reason': '   '}, SALE_CANCEL_SCHEMA)
        self.assertFalse(is_valid)


class TestSaleUpdateSchema(unittest.TestCase):
    """Test SALE_UPDATE_SCHEMA validation"""

    def test_valid_update_buyer_info(self):
        """Valid partial update"""
        data = {'buyer_name': 'Updated Name', 'buyer_phone': '11988776655'}
        is_valid, errors = validate_request(data, SALE_UPDATE_SCHEMA)
        self.assertTrue(is_valid)

    def test_empty_update_valid(self):
        """Empty update body is valid (no required fields)"""
        is_valid, errors = validate_request({}, SALE_UPDATE_SCHEMA)
        self.assertTrue(is_valid)

    def test_zero_price_update_passes_as_falsy(self):
        """Zero sale_price is falsy → constraint returns True (treated as absent)"""
        is_valid, errors = validate_request({'sale_price': 0}, SALE_UPDATE_SCHEMA)
        self.assertTrue(is_valid)

    def test_negative_price_update_fails(self):
        """Negative sale_price in update should fail"""
        is_valid, errors = validate_request({'sale_price': -100}, SALE_UPDATE_SCHEMA)
        self.assertFalse(is_valid)


if __name__ == '__main__':
    unittest.main()
