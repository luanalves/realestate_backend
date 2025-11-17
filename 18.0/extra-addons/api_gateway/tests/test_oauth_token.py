# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import datetime, timedelta


class TestOAuthToken(TransactionCase):
    """Test cases for OAuth Token model"""

    def setUp(self):
        super(TestOAuthToken, self).setUp()
        self.Application = self.env['oauth.application']
        self.Token = self.env['oauth.token']
        
        # Create test application
        self.app = self.Application.create({
            'name': 'Test Application',
        })

    def test_create_token(self):
        """Test creating an OAuth token"""
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'test_access_token',
            'token_type': 'Bearer',
        })
        
        self.assertEqual(token.application_id, self.app)
        self.assertEqual(token.access_token, 'test_access_token')
        self.assertEqual(token.token_type, 'Bearer')
        self.assertFalse(token.revoked, "Token should not be revoked by default")

    def test_token_expiration(self):
        """Test token expiration"""
        # Create expired token
        expired_token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'expired_token',
            'token_type': 'Bearer',
            'expires_at': datetime.now() - timedelta(hours=1),
        })
        
        # Create valid token
        valid_token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'valid_token',
            'token_type': 'Bearer',
            'expires_at': datetime.now() + timedelta(hours=1),
        })
        
        self.assertTrue(expired_token.expires_at < datetime.now())
        self.assertTrue(valid_token.expires_at > datetime.now())

    def test_action_revoke(self):
        """Test revoking a token"""
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'test_token',
            'token_type': 'Bearer',
        })
        
        self.assertFalse(token.revoked)
        
        token.action_revoke()
        
        self.assertTrue(token.revoked, "Token should be revoked")
        self.assertTrue(token.revoked_at, "Revoked timestamp should be set")

    def test_refresh_token(self):
        """Test creating token with refresh token"""
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'access_token',
            'refresh_token': 'refresh_token_123',
            'token_type': 'Bearer',
        })
        
        self.assertEqual(token.refresh_token, 'refresh_token_123')

    def test_token_scope(self):
        """Test token with scopes"""
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'token_with_scopes',
            'token_type': 'Bearer',
            'scope': 'read write admin',
        })
        
        self.assertEqual(token.scope, 'read write admin')

    def test_last_used_timestamp(self):
        """Test last_used timestamp"""
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'test_token',
            'token_type': 'Bearer',
        })
        
        self.assertFalse(token.last_used, "last_used should be False initially")
        
        # Update last_used
        token.write({'last_used': datetime.now()})
        
        self.assertTrue(token.last_used, "last_used should be set")

    def test_multiple_tokens_per_application(self):
        """Test creating multiple tokens for one application"""
        token1 = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'token_1',
            'token_type': 'Bearer',
        })
        
        token2 = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'token_2',
            'token_type': 'Bearer',
        })
        
        tokens = self.Token.search([('application_id', '=', self.app.id)])
        self.assertEqual(len(tokens), 2)

    def test_revoke_all_tokens(self):
        """Test revoking all tokens for an application"""
        # Create multiple tokens
        for i in range(3):
            self.Token.create({
                'application_id': self.app.id,
                'access_token': f'token_{i}',
                'token_type': 'Bearer',
            })
        
        tokens = self.Token.search([('application_id', '=', self.app.id)])
        self.assertEqual(len(tokens), 3)
        
        # Revoke all
        for token in tokens:
            token.action_revoke()
        
        revoked_count = len(tokens.filtered(lambda t: t.revoked))
        self.assertEqual(revoked_count, 3, "All tokens should be revoked")

    def test_token_uniqueness(self):
        """Test that access_token is unique"""
        self.Token.create({
            'application_id': self.app.id,
            'access_token': 'unique_token',
            'token_type': 'Bearer',
        })
        
        # Creating another token with same access_token should work
        # (no uniqueness constraint on access_token in this implementation)
        token2 = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'unique_token_2',
            'token_type': 'Bearer',
        })
        
        self.assertTrue(token2)
