#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Validators — Email, Phone & Schema Constraint Lambdas

Tests email format validation, phone validation, and all new schema constraint
lambdas (rent > 0, price > 0, email format) per SC-010.

Feature: 008-tenant-lease-sale-api
Task: T034
ADR-003: Unit test WITHOUT database (with mocks)

Run: docker compose exec odoo python3 /mnt/extra-addons/quicksol_estate/tests/utils/test_validators.py
"""

import unittest
import re


# ===== Email validation from tenant.py =====

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'


def is_valid_email_regex(email):
    """Tenant model's regex-based email validation"""
    if not email:
        return True  # empty is skipped
    return bool(re.match(EMAIL_REGEX, email))


# ===== Schema constraint lambdas (from schema.py) =====

# Tenant constraints
tenant_create_name = lambda v: len(v.strip()) > 0
tenant_create_email = lambda v: '@' in v and '.' in v.split('@')[-1] if v else True
tenant_update_name = lambda v: len(v.strip()) > 0 if v else True
tenant_update_email = lambda v: '@' in v and '.' in v.split('@')[-1] if v else True

# Lease constraints
lease_property_id = lambda v: v > 0
lease_tenant_id = lambda v: v > 0
lease_rent_amount = lambda v: v > 0
lease_update_rent = lambda v: v > 0 if v else True
lease_status = lambda v: v in ('draft', 'active') if v else True
lease_renew_rent = lambda v: v > 0 if v else True
lease_penalty = lambda v: v >= 0 if v is not None else True

# Sale constraints
sale_property_id = lambda v: v > 0
sale_company_id = lambda v: v > 0
sale_buyer_name = lambda v: len(v.strip()) > 0
sale_price = lambda v: v > 0
sale_buyer_email = lambda v: '@' in v and '.' in v.split('@')[-1] if v else True
sale_update_name = lambda v: len(v.strip()) > 0 if v else True
sale_update_price = lambda v: v > 0 if v else True
sale_cancel_reason = lambda v: len(v.strip()) > 0


# ===== Test Classes =====

class TestEmailRegexValidation(unittest.TestCase):
    """Test the regex-based email validation from tenant model"""

    def test_valid_standard_email(self):
        self.assertTrue(is_valid_email_regex('user@example.com'))

    def test_valid_subdomain_email(self):
        self.assertTrue(is_valid_email_regex('user@mail.example.com'))

    def test_valid_email_with_dots(self):
        self.assertTrue(is_valid_email_regex('first.last@example.com'))

    def test_valid_email_with_plus(self):
        self.assertTrue(is_valid_email_regex('user+tag@example.com'))

    def test_valid_email_with_numbers(self):
        self.assertTrue(is_valid_email_regex('user123@example.com'))

    def test_invalid_no_at(self):
        self.assertFalse(is_valid_email_regex('userexample.com'))

    def test_invalid_no_domain(self):
        self.assertFalse(is_valid_email_regex('user@'))

    def test_invalid_short_tld(self):
        self.assertFalse(is_valid_email_regex('user@example.c'))

    def test_invalid_spaces(self):
        self.assertFalse(is_valid_email_regex('user @example.com'))

    def test_invalid_double_at(self):
        self.assertFalse(is_valid_email_regex('user@@example.com'))

    def test_empty_string_skips(self):
        self.assertTrue(is_valid_email_regex(''))

    def test_none_skips(self):
        self.assertTrue(is_valid_email_regex(None))


class TestSchemaEmailConstraint(unittest.TestCase):
    """Test the schema-level email constraint lambdas"""

    def test_valid_email(self):
        self.assertTrue(tenant_create_email('user@example.com'))

    def test_invalid_email_no_at(self):
        self.assertFalse(tenant_create_email('userexample.com'))

    def test_invalid_email_no_dot_in_domain(self):
        self.assertFalse(tenant_create_email('user@examplecom'))

    def test_empty_passes(self):
        """Empty/falsy value should return True (skip validation)"""
        self.assertTrue(tenant_create_email(''))
        self.assertTrue(tenant_create_email(None))

    def test_buyer_email_valid(self):
        self.assertTrue(sale_buyer_email('buyer@example.com'))

    def test_buyer_email_invalid(self):
        self.assertFalse(sale_buyer_email('not-valid'))

    def test_buyer_email_empty(self):
        self.assertTrue(sale_buyer_email(''))


class TestNameConstraints(unittest.TestCase):
    """Test name constraint lambdas across schemas"""

    def test_tenant_name_valid(self):
        self.assertTrue(tenant_create_name('João Silva'))

    def test_tenant_name_whitespace_only(self):
        self.assertFalse(tenant_create_name('   '))

    def test_tenant_name_single_char(self):
        self.assertTrue(tenant_create_name('A'))

    def test_tenant_update_name_none(self):
        """None/empty in update should pass (optional field)"""
        self.assertTrue(tenant_update_name(None))
        self.assertTrue(tenant_update_name(''))

    def test_sale_buyer_name_valid(self):
        self.assertTrue(sale_buyer_name('Maria Santos'))

    def test_sale_buyer_name_empty(self):
        self.assertFalse(sale_buyer_name('   '))

    def test_sale_update_name_none(self):
        self.assertTrue(sale_update_name(None))

    def test_cancel_reason_valid(self):
        self.assertTrue(sale_cancel_reason('Buyer withdrew'))

    def test_cancel_reason_empty(self):
        self.assertFalse(sale_cancel_reason('   '))


class TestNumericConstraints(unittest.TestCase):
    """Test numeric constraint lambdas (rent, price, IDs, penalty)"""

    # --- IDs > 0 ---
    def test_property_id_positive(self):
        self.assertTrue(lease_property_id(1))

    def test_property_id_zero(self):
        self.assertFalse(lease_property_id(0))

    def test_property_id_negative(self):
        self.assertFalse(lease_property_id(-1))

    def test_tenant_id_positive(self):
        self.assertTrue(lease_tenant_id(5))

    def test_company_id_positive(self):
        self.assertTrue(sale_company_id(1))

    # --- Rent amount > 0 ---
    def test_rent_positive(self):
        self.assertTrue(lease_rent_amount(2500.00))

    def test_rent_zero(self):
        self.assertFalse(lease_rent_amount(0))

    def test_rent_negative(self):
        self.assertFalse(lease_rent_amount(-100))

    def test_rent_update_positive(self):
        self.assertTrue(lease_update_rent(3000.00))

    def test_rent_update_zero_is_falsy(self):
        """0 is falsy → constraint returns True (treated as absent)"""
        self.assertTrue(lease_update_rent(0))

    def test_rent_update_negative_fails(self):
        self.assertFalse(lease_update_rent(-100))

    def test_rent_update_none(self):
        """None/falsy in update should pass"""
        self.assertTrue(lease_update_rent(None))

    # --- Sale price > 0 ---
    def test_sale_price_positive(self):
        self.assertTrue(sale_price(450000.00))

    def test_sale_price_zero(self):
        self.assertFalse(sale_price(0))

    def test_sale_price_negative(self):
        self.assertFalse(sale_price(-5000))

    def test_update_price_positive(self):
        self.assertTrue(sale_update_price(500000.00))

    def test_update_price_none(self):
        self.assertTrue(sale_update_price(None))

    # --- Renewal rent > 0 ---
    def test_renew_rent_positive(self):
        self.assertTrue(lease_renew_rent(3000.00))

    def test_renew_rent_zero(self):
        """0 is falsy so returns True (optional)"""
        self.assertTrue(lease_renew_rent(0))

    # --- Penalty >= 0 ---
    def test_penalty_positive(self):
        self.assertTrue(lease_penalty(5000.00))

    def test_penalty_zero(self):
        self.assertTrue(lease_penalty(0))

    def test_penalty_none(self):
        self.assertTrue(lease_penalty(None))

    def test_penalty_negative(self):
        self.assertFalse(lease_penalty(-100))


class TestStatusConstraints(unittest.TestCase):
    """Test status constraint lambda for lease creation"""

    def test_draft_valid(self):
        self.assertTrue(lease_status('draft'))

    def test_active_valid(self):
        self.assertTrue(lease_status('active'))

    def test_terminated_invalid(self):
        """'terminated' is not allowed in create schema"""
        self.assertFalse(lease_status('terminated'))

    def test_invalid_value(self):
        self.assertFalse(lease_status('random'))

    def test_none_passes(self):
        """None/falsy should pass (optional default)"""
        self.assertTrue(lease_status(None))
        self.assertTrue(lease_status(''))


if __name__ == '__main__':
    unittest.main()
