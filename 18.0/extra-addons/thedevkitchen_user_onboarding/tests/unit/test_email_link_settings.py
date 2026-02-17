# -*- coding: utf-8 -*-
"""
Unit Tests: Email Link Settings

Tests validation rules for thedevkitchen.email.link.settings model.

Validation Rules:
- invite_link_ttl_hours: 1-720 hours range
- reset_link_ttl_hours: 1-720 hours range
- max_resend_attempts: positive integer
- rate_limit_forgot_per_hour: positive integer
- frontend_base_url: valid URL format
- Singleton pattern enforcement

Author: TheDevKitchen
Date: 2026-02-16
ADRs: ADR-003 (Testing Standards), ADR-018 (Validation)
"""

from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError


class TestEmailLinkSettings(TransactionCase):
    """Test email link settings model validation."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        # Get or create singleton settings
        self.settings_model = self.env['thedevkitchen.email.link.settings']
        
        # Clear existing settings for clean tests
        existing_settings = self.settings_model.sudo().search([])
        existing_settings.unlink()
    
    # ============================================================
    # TTL Validation Tests - invite_link_ttl_hours
    # ============================================================
    
    def test_invite_ttl_minimum_boundary_accepted(self):
        """invite_link_ttl_hours = 1 (minimum) is accepted."""
        settings = self.settings_model.create({
            'invite_link_ttl_hours': 1,
            'reset_link_ttl_hours': 24,
        })
        self.assertEqual(settings.invite_link_ttl_hours, 1)
    
    def test_invite_ttl_maximum_boundary_accepted(self):
        """invite_link_ttl_hours = 720 (maximum) is accepted."""
        settings = self.settings_model.create({
            'invite_link_ttl_hours': 720,
            'reset_link_ttl_hours': 24,
        })
        self.assertEqual(settings.invite_link_ttl_hours, 720)
    
    def test_invite_ttl_zero_rejected(self):
        """invite_link_ttl_hours = 0 is rejected."""
        with self.assertRaises(ValidationError) as context:
            self.settings_model.create({
                'invite_link_ttl_hours': 0,
                'reset_link_ttl_hours': 24,
            })
        
        error_message = str(context.exception).lower()
        self.assertTrue(
            'must be between 1' in error_message or 
            'positive' in error_message,
            f"Should reject zero TTL: {error_message}"
        )
    
    def test_invite_ttl_negative_rejected(self):
        """invite_link_ttl_hours < 0 is rejected."""
        with self.assertRaises(ValidationError):
            self.settings_model.create({
                'invite_link_ttl_hours': -5,
                'reset_link_ttl_hours': 24,
            })
    
    def test_invite_ttl_above_maximum_rejected(self):
        """invite_link_ttl_hours > 720 is rejected."""
        with self.assertRaises(ValidationError) as context:
            self.settings_model.create({
                'invite_link_ttl_hours': 721,
                'reset_link_ttl_hours': 24,
            })
        
        error_message = str(context.exception).lower()
        self.assertTrue(
            'must be between 1' in error_message or 
            '720' in error_message,
            f"Should reject TTL above 720: {error_message}"
        )
    
    # ============================================================
    # TTL Validation Tests - reset_link_ttl_hours
    # ============================================================
    
    def test_reset_ttl_minimum_boundary_accepted(self):
        """reset_link_ttl_hours = 1 (minimum) is accepted."""
        settings = self.settings_model.create({
            'invite_link_ttl_hours': 24,
            'reset_link_ttl_hours': 1,
        })
        self.assertEqual(settings.reset_link_ttl_hours, 1)
    
    def test_reset_ttl_maximum_boundary_accepted(self):
        """reset_link_ttl_hours = 720 (maximum) is accepted."""
        settings = self.settings_model.create({
            'invite_link_ttl_hours': 24,
            'reset_link_ttl_hours': 720,
        })
        self.assertEqual(settings.reset_link_ttl_hours, 720)
    
    def test_reset_ttl_zero_rejected(self):
        """reset_link_ttl_hours = 0 is rejected."""
        with self.assertRaises(ValidationError):
            self.settings_model.create({
                'invite_link_ttl_hours': 24,
                'reset_link_ttl_hours': 0,
            })
    
    def test_reset_ttl_negative_rejected(self):
        """reset_link_ttl_hours < 0 is rejected."""
        with self.assertRaises(ValidationError):
            self.settings_model.create({
                'invite_link_ttl_hours': 24,
                'reset_link_ttl_hours': -10,
            })
    
    def test_reset_ttl_above_maximum_rejected(self):
        """reset_link_ttl_hours > 720 is rejected."""
        with self.assertRaises(ValidationError):
            self.settings_model.create({
                'invite_link_ttl_hours': 24,
                'reset_link_ttl_hours': 1000,
            })
    
    # ============================================================
    # TTL Update Tests
    # ============================================================
    
    def test_invite_ttl_can_be_updated(self):
        """invite_link_ttl_hours can be updated within valid range."""
        settings = self.settings_model.create({
            'invite_link_ttl_hours': 24,
            'reset_link_ttl_hours': 48,
        })
        
        settings.write({'invite_link_ttl_hours': 48})
        self.assertEqual(settings.invite_link_ttl_hours, 48)
    
    def test_reset_ttl_can_be_updated(self):
        """reset_link_ttl_hours can be updated within valid range."""
        settings = self.settings_model.create({
            'invite_link_ttl_hours': 24,
            'reset_link_ttl_hours': 48,
        })
        
        settings.write({'reset_link_ttl_hours': 72})
        self.assertEqual(settings.reset_link_ttl_hours, 72)
    
    def test_update_invite_ttl_to_invalid_rejected(self):
        """Updating invite_link_ttl_hours to invalid value is rejected."""
        settings = self.settings_model.create({
            'invite_link_ttl_hours': 24,
            'reset_link_ttl_hours': 48,
        })
        
        with self.assertRaises(ValidationError):
            settings.write({'invite_link_ttl_hours': 800})
    
    def test_update_reset_ttl_to_invalid_rejected(self):
        """Updating reset_link_ttl_hours to invalid value is rejected."""
        settings = self.settings_model.create({
            'invite_link_ttl_hours': 24,
            'reset_link_ttl_hours': 48,
        })
        
        with self.assertRaises(ValidationError):
            settings.write({'reset_link_ttl_hours': -5})
    
    # ============================================================
    # Default Values Tests
    # ============================================================
    
    def test_default_values_are_set(self):
        """Default values are set correctly."""
        settings = self.settings_model.create({})
        
        self.assertEqual(settings.invite_link_ttl_hours, 24, "Default invite TTL should be 24")
        self.assertEqual(settings.reset_link_ttl_hours, 24, "Default reset TTL should be 24")
        self.assertEqual(settings.max_resend_attempts, 5, "Default max resend should be 5")
        self.assertEqual(settings.rate_limit_forgot_per_hour, 3, "Default rate limit should be 3")
        self.assertEqual(settings.frontend_base_url, 'http://localhost:3000', "Default frontend URL")
    
    # ============================================================
    # Frontend Base URL Tests
    # ============================================================
    
    def test_frontend_base_url_can_be_set(self):
        """frontend_base_url can be set to custom value."""
        settings = self.settings_model.create({
            'frontend_base_url': 'https://example.com',
        })
        
        self.assertEqual(settings.frontend_base_url, 'https://example.com')
    
    def test_frontend_base_url_with_port(self):
        """frontend_base_url accepts URL with port."""
        settings = self.settings_model.create({
            'frontend_base_url': 'http://localhost:8080',
        })
        
        self.assertEqual(settings.frontend_base_url, 'http://localhost:8080')
    
    def test_frontend_base_url_with_https(self):
        """frontend_base_url accepts HTTPS URLs."""
        settings = self.settings_model.create({
            'frontend_base_url': 'https://secure.example.com',
        })
        
        self.assertEqual(settings.frontend_base_url, 'https://secure.example.com')
    
    # ============================================================
    # Max Resend Attempts Tests
    # ============================================================
    
    def test_max_resend_attempts_positive(self):
        """max_resend_attempts accepts positive values."""
        settings = self.settings_model.create({
            'max_resend_attempts': 10,
        })
        
        self.assertEqual(settings.max_resend_attempts, 10)
    
    def test_max_resend_attempts_one_accepted(self):
        """max_resend_attempts = 1 is accepted."""
        settings = self.settings_model.create({
            'max_resend_attempts': 1,
        })
        
        self.assertEqual(settings.max_resend_attempts, 1)
    
    # ============================================================
    # Rate Limit Tests
    # ============================================================
    
    def test_rate_limit_forgot_per_hour_positive(self):
        """rate_limit_forgot_per_hour accepts positive values."""
        settings = self.settings_model.create({
            'rate_limit_forgot_per_hour': 5,
        })
        
        self.assertEqual(settings.rate_limit_forgot_per_hour, 5)
    
    def test_rate_limit_forgot_per_hour_one_accepted(self):
        """rate_limit_forgot_per_hour = 1 is accepted."""
        settings = self.settings_model.create({
            'rate_limit_forgot_per_hour': 1,
        })
        
        self.assertEqual(settings.rate_limit_forgot_per_hour, 1)
    
    # ============================================================
    # Singleton Pattern Tests
    # ============================================================
    
    def test_get_settings_returns_singleton(self):
        """get_settings() returns singleton instance."""
        # Create initial settings
        settings1 = self.settings_model.create({
            'invite_link_ttl_hours': 24,
        })
        
        # Get settings via get_settings()
        settings2 = self.settings_model.get_settings()
        
        # Should return the same record
        self.assertEqual(settings1.id, settings2.id, "get_settings() should return singleton")
    
    def test_get_settings_creates_default_if_missing(self):
        """get_settings() creates default settings if none exist."""
        # Ensure no settings exist
        self.settings_model.search([]).unlink()
        
        # Get settings (should create default)
        settings = self.settings_model.get_settings()
        
        self.assertTrue(settings, "get_settings() should create default settings")
        self.assertEqual(settings.invite_link_ttl_hours, 24, "Default invite TTL")
    
    # ============================================================
    # Common Values Tests
    # ============================================================
    
    def test_typical_invite_ttl_24_hours(self):
        """Typical invite_link_ttl_hours of 24 is accepted."""
        settings = self.settings_model.create({
            'invite_link_ttl_hours': 24,
        })
        self.assertEqual(settings.invite_link_ttl_hours, 24)
    
    def test_typical_reset_ttl_48_hours(self):
        """Typical reset_link_ttl_hours of 48 is accepted."""
        settings = self.settings_model.create({
            'reset_link_ttl_hours': 48,
        })
        self.assertEqual(settings.reset_link_ttl_hours, 48)
    
    def test_one_week_ttl_168_hours(self):
        """One week TTL (168 hours) is accepted."""
        settings = self.settings_model.create({
            'invite_link_ttl_hours': 168,
            'reset_link_ttl_hours': 168,
        })
        self.assertEqual(settings.invite_link_ttl_hours, 168)
        self.assertEqual(settings.reset_link_ttl_hours, 168)
    
    def test_one_month_ttl_720_hours(self):
        """One month TTL (720 hours = 30 days) is accepted."""
        settings = self.settings_model.create({
            'invite_link_ttl_hours': 720,
            'reset_link_ttl_hours': 720,
        })
        self.assertEqual(settings.invite_link_ttl_hours, 720)
        self.assertEqual(settings.reset_link_ttl_hours, 720)
    
    # ============================================================
    # Edge Cases
    # ============================================================
    
    def test_all_fields_can_be_set_together(self):
        """All fields can be set in a single create operation."""
        settings = self.settings_model.create({
            'invite_link_ttl_hours': 48,
            'reset_link_ttl_hours': 72,
            'frontend_base_url': 'https://app.example.com',
            'max_resend_attempts': 10,
            'rate_limit_forgot_per_hour': 5,
        })
        
        self.assertEqual(settings.invite_link_ttl_hours, 48)
        self.assertEqual(settings.reset_link_ttl_hours, 72)
        self.assertEqual(settings.frontend_base_url, 'https://app.example.com')
        self.assertEqual(settings.max_resend_attempts, 10)
        self.assertEqual(settings.rate_limit_forgot_per_hour, 5)
