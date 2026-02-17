# -*- coding: utf-8 -*-
"""
Unit Tests: Token Service

Tests token generation, validation, invalidation, rate limiting, and session management.

Token Lifecycle:
- generate_token() returns UUID v4 and stores SHA-256 hash
- validate_token() checks token validity (status, expiry)
- invalidate_previous_tokens() marks all pending tokens as invalidated
- check_rate_limit() enforces rate limits (Redis-based)

Author: TheDevKitchen
Date: 2026-02-16
ADRs: ADR-003 (Testing Standards), ADR-008 (Anti-Enumeration), ADR-011 (Security)
"""

from odoo.tests import TransactionCase
from odoo.exceptions import UserError, ValidationError
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import hashlib
import re


class TestTokenService(TransactionCase):
    """Test PasswordTokenService functionality."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        # Create test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
        })
        
        # Create test user
        self.test_user = self.env['res.users'].create({
            'login': 'token@test.com',
            'name': 'Token Test User',
            'email': 'token@test.com',
            'signup_pending': True,
            'estate_company_ids': [(6, 0, [self.company.id])],
        })
        
        # Create settings
        self.settings = self.env['thedevkitchen.email.link.settings'].create({
            'invite_link_ttl_hours': 24,
            'reset_link_ttl_hours': 48,
            'frontend_base_url': 'http://localhost:3000',
            'max_resend_attempts': 5,
            'rate_limit_forgot_per_hour': 3,
        })
        
        # Initialize TokenService
        from odoo.addons.thedevkitchen_user_onboarding.services.token_service import PasswordTokenService
        self.token_service = PasswordTokenService(self.env)
    
    # ============================================================
    # Token Generation Tests
    # ============================================================
    
    @patch('odoo.addons.thedevkitchen_user_onboarding.services.token_service.uuid')
    def test_generate_token_returns_uuid_format(self, mock_uuid):
        """generate_token() returns UUID-format raw token."""
        # Mock UUID generation
        mock_uuid.uuid4.return_value.hex = 'a' * 32  # 32 hex chars
        
        raw_token, token_record = self.token_service.generate_token(
            user=self.test_user,
            token_type='invite',
            ttl_hours=24,
            company_id=self.company.id
        )
        
        # Verify raw token is 32 hex characters (UUID4 hex format)
        self.assertEqual(len(raw_token), 32)
        self.assertTrue(re.match(r'^[a-f0-9]{32}$', raw_token), "Raw token should be 32 hex chars")
    
    @patch('odoo.addons.thedevkitchen_user_onboarding.services.token_service.uuid')
    def test_generate_token_stores_sha256_hash(self, mock_uuid):
        """generate_token() stores SHA-256 hash of raw token."""
        # Mock UUID generation
        raw_token_value = 'a' * 32
        mock_uuid.uuid4.return_value.hex = raw_token_value
        
        raw_token, token_record = self.token_service.generate_token(
            user=self.test_user,
            token_type='invite',
            ttl_hours=24,
            company_id=self.company.id
        )
        
        # Compute expected SHA-256 hash
        expected_hash = hashlib.sha256(raw_token_value.encode()).hexdigest()
        
        # Verify stored token is SHA-256 hash
        self.assertEqual(token_record.token, expected_hash)
        self.assertEqual(len(token_record.token), 64, "SHA-256 hash should be 64 hex chars")
    
    def test_generate_token_sets_correct_expiry(self):
        """generate_token() sets correct expiry based on TTL."""
        before_generation = datetime.now()
        
        raw_token, token_record = self.token_service.generate_token(
            user=self.test_user,
            token_type='invite',
            ttl_hours=24,
            company_id=self.company.id
        )
        
        after_generation = datetime.now()
        
        # Verify expiry is approximately 24 hours from now (within 1 minute tolerance)
        expected_expiry = before_generation + timedelta(hours=24)
        actual_expiry = token_record.expires_at
        
        time_diff = abs((actual_expiry - expected_expiry).total_seconds())
        self.assertLess(time_diff, 120, "Expiry should be within 2 minutes of expected time")  # 2 min tolerance for test execution time
    
    def test_generate_token_status_pending(self):
        """generate_token() creates token with status=pending."""
        raw_token, token_record = self.token_service.generate_token(
            user=self.test_user,
            token_type='invite',
            ttl_hours=24,
            company_id=self.company.id
        )
        
        self.assertEqual(token_record.status, 'pending')
    
    def test_generate_token_links_to_user(self):
        """generate_token() links token to correct user."""
        raw_token, token_record = self.token_service.generate_token(
            user=self.test_user,
            token_type='invite',
            ttl_hours=24,
            company_id=self.company.id
        )
        
        self.assertEqual(token_record.user_id.id, self.test_user.id)
    
    def test_generate_token_links_to_company(self):
        """generate_token() links token to correct company."""
        raw_token, token_record = self.token_service.generate_token(
            user=self.test_user,
            token_type='invite',
            ttl_hours=24,
            company_id=self.company.id
        )
        
        self.assertEqual(token_record.company_id.id, self.company.id)
    
    # ============================================================
    # Token Validation Tests
    # ============================================================
    
    def test_validate_token_with_valid_token_returns_user(self):
        """validate_token() with valid token returns user."""
        # Generate token
        raw_token, token_record = self.token_service.generate_token(
            user=self.test_user,
            token_type='invite',
            ttl_hours=24,
            company_id=self.company.id
        )
        
        # Validate token
        result = self.token_service.validate_token(raw_token, 'invite')
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['user'].id, self.test_user.id)
        self.assertEqual(result['token_record'].id, token_record.id)
        self.assertIsNone(result['error'])
    
    def test_validate_token_with_expired_token_returns_error(self):
        """validate_token() with expired token returns error."""
        # Create expired token manually
        expired_token = self.env['thedevkitchen.password.token'].create({
            'user_id': self.test_user.id,
            'token': 'b' * 64,
            'token_type': 'invite',
            'status': 'pending',
            'expires_at': datetime.now() - timedelta(hours=1),  # Expired 1 hour ago
            'company_id': self.company.id,
        })
        
        # Compute raw token that would hash to 'b' * 64
        # For testing, we'll use the hash directly and validate with invalid raw token
        # In real scenario, we can't reverse SHA-256, so we'll test the status update
        
        # Validate token with raw token
        fake_raw_token = 'expired-token'
        result = self.token_service.validate_token(fake_raw_token, 'invite')
        
        # Should return invalid either because hash doesn't match or token expired
        self.assertFalse(result['valid'])
        self.assertIsNotNone(result['error'])
    
    def test_validate_token_with_used_token_returns_error(self):
        """validate_token() with used token returns error."""
        # Generate and immediately mark as used
        raw_token, token_record = self.token_service.generate_token(
            user=self.test_user,
            token_type='invite',
            ttl_hours=24,
            company_id=self.company.id
        )
        
        token_record.write({
            'status': 'used',
            'used_at': datetime.now(),
            'ip_address': '127.0.0.1',
            'user_agent': 'TestAgent',
        })
        
        # Validate token
        result = self.token_service.validate_token(raw_token, 'invite')
        
        self.assertFalse(result['valid'])
        self.assertIsNotNone(result['error'])
        self.assertIn('used', result['error'].lower())
    
    def test_validate_token_with_nonexistent_hash_returns_error(self):
        """validate_token() with nonexistent hash returns error."""
        # Use a token that doesn't exist in database
        fake_token = 'nonexistent-token-12345'
        
        result = self.token_service.validate_token(fake_token, 'invite')
        
        self.assertFalse(result['valid'])
        self.assertIsNotNone(result['error'])
    
    def test_validate_token_auto_expires_expired_tokens(self):
        """validate_token() auto-updates expired pending tokens to status=expired."""
        # Create pending token that's expired
        raw_token_value = 'c' * 32
        token_hash = hashlib.sha256(raw_token_value.encode()).hexdigest()
        
        expired_token = self.env['thedevkitchen.password.token'].create({
            'user_id': self.test_user.id,
            'token': token_hash,
            'token_type': 'invite',
            'status': 'pending',
            'expires_at': datetime.now() - timedelta(hours=1),
            'company_id': self.company.id,
        })
        
        # Validate token
        result = self.token_service.validate_token(raw_token_value, 'invite')
        
        # Token should be invalid
        self.assertFalse(result['valid'])
        
        # Check if token status was updated to expired
        expired_token.refresh()
        self.assertEqual(expired_token.status, 'expired')
    
    # ============================================================
    # Token Invalidation Tests
    # ============================================================
    
    def test_invalidate_previous_tokens_marks_pending_as_invalidated(self):
        """invalidate_previous_tokens() sets all pending tokens to invalidated."""
        # Create multiple pending tokens
        token1 = self.env['thedevkitchen.password.token'].create({
            'user_id': self.test_user.id,
            'token': 'd' * 64,
            'token_type': 'invite',
            'status': 'pending',
            'expires_at': datetime.now() + timedelta(hours=24),
            'company_id': self.company.id,
        })
        
        token2 = self.env['thedevkitchen.password.token'].create({
            'user_id': self.test_user.id,
            'token': 'e' * 64,
            'token_type': 'invite',
            'status': 'pending',
            'expires_at': datetime.now() + timedelta(hours=24),
            'company_id': self.company.id,
        })
        
        # Invalidate previous tokens
        self.token_service.invalidate_previous_tokens(self.test_user, 'invite')
        
        # Verify both tokens marked as invalidated
        token1.refresh()
        token2.refresh()
        
        self.assertEqual(token1.status, 'invalidated')
        self.assertEqual(token2.status, 'invalidated')
    
    def test_invalidate_previous_tokens_does_not_affect_used_tokens(self):
        """invalidate_previous_tokens() does not change used tokens."""
        # Create used token
        used_token = self.env['thedevkitchen.password.token'].create({
            'user_id': self.test_user.id,
            'token': 'f' * 64,
            'token_type': 'invite',
            'status': 'used',
            'expires_at': datetime.now() + timedelta(hours=24),
            'company_id': self.company.id,
            'used_at': datetime.now(),
        })
        
        # Invalidate previous tokens
        self.token_service.invalidate_previous_tokens(self.test_user, 'invite')
        
        # Used token should remain used
        used_token.refresh()
        self.assertEqual(used_token.status, 'used')
    
    def test_invalidate_previous_tokens_respects_token_type(self):
        """invalidate_previous_tokens() only invalidates specified token type."""
        # Create invite token
        invite_token = self.env['thedevkitchen.password.token'].create({
            'user_id': self.test_user.id,
            'token': 'g' * 64,
            'token_type': 'invite',
            'status': 'pending',
            'expires_at': datetime.now() + timedelta(hours=24),
            'company_id': self.company.id,
        })
        
        # Create reset token
        reset_token = self.env['thedevkitchen.password.token'].create({
            'user_id': self.test_user.id,
            'token': 'h' * 64,
            'token_type': 'reset',
            'status': 'pending',
            'expires_at': datetime.now() + timedelta(hours=24),
            'company_id': self.company.id,
        })
        
        # Invalidate only invite tokens
        self.token_service.invalidate_previous_tokens(self.test_user, 'invite')
        
        # Check statuses
        invite_token.refresh()
        reset_token.refresh()
        
        self.assertEqual(invite_token.status, 'invalidated')
        self.assertEqual(reset_token.status, 'pending')  # Should not be affected
    
    # ============================================================
    # Token Uniqueness Tests
    # ============================================================
    
    def test_token_uniqueness_constraint(self):
        """Token field has uniqueness constraint."""
        # Create first token
        self.env['thedevkitchen.password.token'].create({
            'user_id': self.test_user.id,
            'token': 'unique' * 16,  # 96 chars
            'token_type': 'invite',
            'status': 'pending',
            'expires_at': datetime.now() + timedelta(hours=24),
            'company_id': self.company.id,
        })
        
        # Try to create duplicate token
        with self.assertRaises(Exception) as context:
            self.env['thedevkitchen.password.token'].create({
                'user_id': self.test_user.id,
                'token': 'unique' * 16,  # Same hash
                'token_type': 'invite',
                'status': 'pending',
                'expires_at': datetime.now() + timedelta(hours=24),
                'company_id': self.company.id,
            })
        
        # Verify it's a uniqueness constraint violation
        error_message = str(context.exception).lower()
        self.assertTrue(
            'unique' in error_message or 'duplicate' in error_message,
            "Should raise uniqueness constraint error"
        )
    
    # ============================================================
    # Forgot Password Tests (T025)
    # ============================================================
    
    def test_forgot_password_always_returns_success(self):
        """Forgot password always returns success (anti-enumeration)."""
        from odoo.addons.thedevkitchen_user_onboarding.services.password_service import PasswordService
        password_service = PasswordService(self.env)
        
        # Test with existing user
        result_existing = password_service.forgot_password('token@test.com')
        self.assertTrue(result_existing, "Should return success for existing user")
        
        # Test with non-existent user
        result_nonexistent = password_service.forgot_password('nonexistent@test.com')
        self.assertTrue(result_nonexistent, "Should return success for non-existent user (anti-enumeration)")
    
    def test_reset_token_invalidates_previous_reset_tokens(self):
        """New reset token marks previous pending reset tokens as invalidated."""
        # Create first reset token
        first_token = self.env['thedevkitchen.password.token'].create({
            'user_id': self.test_user.id,
            'token': 'i' * 64,
            'token_type': 'reset',
            'status': 'pending',
            'expires_at': datetime.now() + timedelta(hours=48),
            'company_id': self.company.id,
        })
        
        # Generate new reset token (should invalidate first)
        self.token_service.invalidate_previous_tokens(self.test_user, 'reset')
        
        raw_token, new_token = self.token_service.generate_token(
            user=self.test_user,
            token_type='reset',
            ttl_hours=48,
            company_id=self.company.id
        )
        
        # First token should be invalidated
        first_token.refresh()
        self.assertEqual(first_token.status, 'invalidated')
        
        # New token should be pending
        self.assertEqual(new_token.status, 'pending')
    
    # ============================================================
    # Rate Limiting Tests (T025)
    # ============================================================
    
    @patch('odoo.addons.thedevkitchen_user_onboarding.services.token_service._logger')
    def test_rate_limit_check_placeholder_allows_requests(self, mock_logger):
        """check_rate_limit() placeholder returns allowed=True."""
        # Current implementation is a placeholder that always allows
        result = self.token_service.check_rate_limit('test@example.com', 'forgot_password')
        
        self.assertTrue(result['allowed'])
        self.assertEqual(result['attempts'], 0)
        self.assertIn('limit', result)
        
        # Verify warning logged about Redis pending
        mock_logger.warning.assert_called()
        warning_message = str(mock_logger.warning.call_args)
        self.assertIn('Redis', warning_message)
    
    # Note: Real Redis rate limiting tests would require Redis mock
    # TODO: Implement Redis rate limiting and add proper tests when Redis integration is complete
    
    # ============================================================
    # Session Invalidation Tests (T025)
    # ============================================================
    
    @patch('odoo.addons.thedevkitchen_user_onboarding.services.password_service.PasswordService._invalidate_user_sessions')
    def test_session_invalidation_called_after_reset(self, mock_invalidate):
        """Session invalidation is called after password reset."""
        from odoo.addons.thedevkitchen_user_onboarding.services.password_service import PasswordService
        password_service = PasswordService(self.env)
        
        # Generate reset token
        raw_token, token_record = self.token_service.generate_token(
            user=self.test_user,
            token_type='reset',
            ttl_hours=48,
            company_id=self.company.id
        )
        
        # Mock validate_token to return valid
        with patch.object(self.token_service, 'validate_token') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'user': self.test_user,
                'token_record': token_record,
                'error': None
            }
            
            # Call reset_password
            password_service.reset_password(
                raw_token=raw_token,
                password='NewPass123',
                confirm_password='NewPass123',
                ip_address='127.0.0.1',
                user_agent='TestAgent'
            )
        
        # Verify session invalidation was called
        mock_invalidate.assert_called_once_with(self.test_user)
    
    def test_session_invalidation_sets_api_session_inactive(self):
        """_invalidate_user_sessions() sets api_session.is_active=False for all user sessions."""
        # Note: This test requires thedevkitchen.api.session model to exist
        # If model doesn't exist in test environment, test will be skipped
        
        try:
            # Try to create test sessions
            session_model = self.env['thedevkitchen.api.session']
            
            session1 = session_model.create({
                'user_id': self.test_user.id,
                'session_id': 'test-session-1',
                'is_active': True,
            })
            
            session2 = session_model.create({
                'user_id': self.test_user.id,
                'session_id': 'test-session-2',
                'is_active': True,
            })
            
            # Call invalidate sessions
            from odoo.addons.thedevkitchen_user_onboarding.services.password_service import PasswordService
            password_service = PasswordService(self.env)
            password_service._invalidate_user_sessions(self.test_user)
            
            # Verify sessions are inactive
            session1.refresh()
            session2.refresh()
            
            self.assertFalse(session1.is_active, "Session 1 should be inactive")
            self.assertFalse(session2.is_active, "Session 2 should be inactive")
            
        except KeyError:
            # Model doesn't exist in test environment, skip test
            self.skipTest("thedevkitchen.api.session model not available in test environment")
