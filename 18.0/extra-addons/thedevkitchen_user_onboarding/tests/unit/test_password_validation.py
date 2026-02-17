# -*- coding: utf-8 -*-
"""
Unit Tests: Password Validation

Tests password validation rules in PasswordService.

Validation Rules:
- Password minimum 8 characters
- Password must equal confirm_password
- Password and confirm_password cannot be empty

Author: TheDevKitchen
Date: 2026-02-16
ADRs: ADR-003 (Testing Standards), ADR-018 (Validation)
"""

from odoo.tests import TransactionCase
from odoo.exceptions import UserError, ValidationError
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestPasswordValidation(TransactionCase):
    """Test password validation in PasswordService."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create test company
        self.company = self.env["res.company"].create(
            {
                "name": "Test Company",
            }
        )

        # Create test user
        self.test_user = self.env["res.users"].create(
            {
                "login": "test@password.com",
                "name": "Test Password User",
                "email": "test@password.com",
                "signup_pending": True,
                "estate_company_ids": [(6, 0, [self.company.id])],
            }
        )

        # Create valid token
        self.valid_token = self.env["thedevkitchen.password.token"].create(
            {
                "user_id": self.test_user.id,
                "token": "a" * 64,  # SHA-256 hash is 64 chars
                "token_type": "invite",
                "status": "pending",
                "expires_at": datetime.now() + timedelta(hours=24),
                "company_id": self.company.id,
            }
        )

        # Initialize PasswordService
        from odoo.addons.thedevkitchen_user_onboarding.services.password_service import (
            PasswordService,
        )

        self.password_service = PasswordService(self.env)

        # Initialize TokenService
        from odoo.addons.thedevkitchen_user_onboarding.services.token_service import (
            PasswordTokenService,
        )

        self.token_service = PasswordTokenService(self.env)

    # ============================================================
    # Valid Password Tests
    # ============================================================

    @patch(
        "odoo.addons.thedevkitchen_user_onboarding.services.token_service.PasswordTokenService.validate_token"
    )
    def test_valid_password_accepted(self, mock_validate):
        """Valid password (8+ chars, matching confirmation) is accepted."""
        # Mock token validation to return valid token
        mock_validate.return_value = {
            "valid": True,
            "user": self.test_user,
            "token_record": self.valid_token,
            "error": None,
        }

        # Should not raise any exception
        try:
            self.password_service.set_password(
                raw_token="test-token-123",
                password="ValidPass123",
                confirm_password="ValidPass123",
                ip_address="127.0.0.1",
                user_agent="TestAgent",
            )
        except Exception as e:
            self.fail(f"Valid password should be accepted, but got: {e}")

    @patch(
        "odoo.addons.thedevkitchen_user_onboarding.services.token_service.PasswordTokenService.validate_token"
    )
    def test_exactly_8_chars_accepted(self, mock_validate):
        """Password with exactly 8 characters is accepted."""
        # Mock token validation
        mock_validate.return_value = {
            "valid": True,
            "user": self.test_user,
            "token_record": self.valid_token,
            "error": None,
        }

        try:
            self.password_service.set_password(
                raw_token="test-token-123",
                password="12345678",
                confirm_password="12345678",
                ip_address="127.0.0.1",
                user_agent="TestAgent",
            )
        except Exception as e:
            self.fail(f"8 character password should be accepted, but got: {e}")

    # ============================================================
    # Password Length Tests
    # ============================================================

    @patch(
        "odoo.addons.thedevkitchen_user_onboarding.services.token_service.PasswordTokenService.validate_token"
    )
    def test_password_less_than_8_chars_rejected(self, mock_validate):
        """Password with less than 8 characters is rejected."""
        # Mock token validation
        mock_validate.return_value = {
            "valid": True,
            "user": self.test_user,
            "token_record": self.valid_token,
            "error": None,
        }

        with self.assertRaises((ValidationError, UserError)) as context:
            self.password_service.set_password(
                raw_token="test-token-123",
                password="short",  # Only 5 characters
                confirm_password="short",
                ip_address="127.0.0.1",
                user_agent="TestAgent",
            )

        error_message = str(context.exception).lower()
        self.assertTrue(
            "password must be at least" in error_message
            or "minimum" in error_message
            or "8" in error_message,
            f"Error should mention minimum length: {error_message}",
        )

    @patch(
        "odoo.addons.thedevkitchen_user_onboarding.services.token_service.PasswordTokenService.validate_token"
    )
    def test_password_7_chars_rejected(self, mock_validate):
        """Password with exactly 7 characters is rejected."""
        # Mock token validation
        mock_validate.return_value = {
            "valid": True,
            "user": self.test_user,
            "token_record": self.valid_token,
            "error": None,
        }

        with self.assertRaises((ValidationError, UserError)):
            self.password_service.set_password(
                raw_token="test-token-123",
                password="1234567",  # 7 characters
                confirm_password="1234567",
                ip_address="127.0.0.1",
                user_agent="TestAgent",
            )

    # ============================================================
    # Password Confirmation Tests
    # ============================================================

    @patch(
        "odoo.addons.thedevkitchen_user_onboarding.services.token_service.PasswordTokenService.validate_token"
    )
    def test_password_not_equal_confirm_rejected(self, mock_validate):
        """Password and confirm_password mismatch is rejected."""
        # Mock token validation
        mock_validate.return_value = {
            "valid": True,
            "user": self.test_user,
            "token_record": self.valid_token,
            "error": None,
        }

        with self.assertRaises((ValidationError, UserError)) as context:
            self.password_service.set_password(
                raw_token="test-token-123",
                password="ValidPass123",
                confirm_password="DifferentPass123",
                ip_address="127.0.0.1",
                user_agent="TestAgent",
            )

        error_message = str(context.exception).lower()
        self.assertTrue(
            "match" in error_message
            or "mismatch" in error_message
            or "do not match" in error_message,
            f"Error should mention password mismatch: {error_message}",
        )

    @patch(
        "odoo.addons.thedevkitchen_user_onboarding.services.token_service.PasswordTokenService.validate_token"
    )
    def test_password_equals_confirm_passes(self, mock_validate):
        """Password matching confirm_password passes validation."""
        # Mock token validation
        mock_validate.return_value = {
            "valid": True,
            "user": self.test_user,
            "token_record": self.valid_token,
            "error": None,
        }

        try:
            self.password_service.set_password(
                raw_token="test-token-123",
                password="MatchingPass123",
                confirm_password="MatchingPass123",
                ip_address="127.0.0.1",
                user_agent="TestAgent",
            )
        except Exception as e:
            self.fail(f"Matching passwords should pass validation, but got: {e}")

    # ============================================================
    # Empty Password Tests
    # ============================================================

    @patch(
        "odoo.addons.thedevkitchen_user_onboarding.services.token_service.PasswordTokenService.validate_token"
    )
    def test_empty_password_rejected(self, mock_validate):
        """Empty password is rejected."""
        # Mock token validation
        mock_validate.return_value = {
            "valid": True,
            "user": self.test_user,
            "token_record": self.valid_token,
            "error": None,
        }

        with self.assertRaises((ValidationError, UserError)) as context:
            self.password_service.set_password(
                raw_token="test-token-123",
                password="",
                confirm_password="",
                ip_address="127.0.0.1",
                user_agent="TestAgent",
            )

        error_message = str(context.exception).lower()
        self.assertTrue(
            "required" in error_message
            or "empty" in error_message
            or "password" in error_message,
            f"Error should mention required password: {error_message}",
        )

    @patch(
        "odoo.addons.thedevkitchen_user_onboarding.services.token_service.PasswordTokenService.validate_token"
    )
    def test_empty_confirm_password_rejected(self, mock_validate):
        """Empty confirm_password is rejected."""
        # Mock token validation
        mock_validate.return_value = {
            "valid": True,
            "user": self.test_user,
            "token_record": self.valid_token,
            "error": None,
        }

        with self.assertRaises((ValidationError, UserError)) as context:
            self.password_service.set_password(
                raw_token="test-token-123",
                password="ValidPass123",
                confirm_password="",
                ip_address="127.0.0.1",
                user_agent="TestAgent",
            )

        error_message = str(context.exception).lower()
        self.assertTrue(
            "required" in error_message
            or "match" in error_message
            or "confirmation" in error_message,
            f"Error should mention confirmation requirement: {error_message}",
        )

    # ============================================================
    # Whitespace Tests
    # ============================================================

    @patch(
        "odoo.addons.thedevkitchen_user_onboarding.services.token_service.PasswordTokenService.validate_token"
    )
    def test_password_with_leading_trailing_spaces_accepted(self, mock_validate):
        """Password with leading/trailing spaces is accepted (8+ chars total)."""
        # Mock token validation
        mock_validate.return_value = {
            "valid": True,
            "user": self.test_user,
            "token_record": self.valid_token,
            "error": None,
        }

        # Note: Most systems don't trim passwords - spaces are part of the password
        try:
            self.password_service.set_password(
                raw_token="test-token-123",
                password=" Valid123 ",  # 10 chars total
                confirm_password=" Valid123 ",
                ip_address="127.0.0.1",
                user_agent="TestAgent",
            )
        except Exception as e:
            self.fail(f"Password with spaces should be accepted if 8+ chars: {e}")

    # ============================================================
    # Special Characters Tests
    # ============================================================

    @patch(
        "odoo.addons.thedevkitchen_user_onboarding.services.token_service.PasswordTokenService.validate_token"
    )
    def test_password_with_special_chars_accepted(self, mock_validate):
        """Password with special characters is accepted."""
        # Mock token validation
        mock_validate.return_value = {
            "valid": True,
            "user": self.test_user,
            "token_record": self.valid_token,
            "error": None,
        }

        try:
            self.password_service.set_password(
                raw_token="test-token-123",
                password="P@ssw0rd!#$",
                confirm_password="P@ssw0rd!#$",
                ip_address="127.0.0.1",
                user_agent="TestAgent",
            )
        except Exception as e:
            self.fail(f"Password with special characters should be accepted: {e}")

    @patch(
        "odoo.addons.thedevkitchen_user_onboarding.services.token_service.PasswordTokenService.validate_token"
    )
    def test_password_with_unicode_accepted(self, mock_validate):
        """Password with unicode characters is accepted."""
        # Mock token validation
        mock_validate.return_value = {
            "valid": True,
            "user": self.test_user,
            "token_record": self.valid_token,
            "error": None,
        }

        try:
            self.password_service.set_password(
                raw_token="test-token-123",
                password="Sênha123",  # 8 chars with unicode
                confirm_password="Sênha123",
                ip_address="127.0.0.1",
                user_agent="TestAgent",
            )
        except Exception as e:
            self.fail(f"Password with unicode should be accepted: {e}")
