# -*- coding: utf-8 -*-
"""Unit tests for client_secret_plaintext field (temporary cache for E2E tests)."""
from odoo.tests.common import TransactionCase
import time


class TestOAuthApplicationPlaintext(TransactionCase):
    """Test client_secret_plaintext field caching."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.OAuthApplication = self.env['thedevkitchen.oauth.application']

    def test_plaintext_available_after_create(self):
        """Test that client_secret_plaintext is available immediately after creation."""
        app = self.OAuthApplication.create({
            'name': 'Test Plaintext App'
        })
        
        # Refresh to get computed field
        app.invalidate_recordset()
        
        # Plaintext should be available
        self.assertIsNotNone(app.client_secret_plaintext)
        self.assertIsInstance(app.client_secret_plaintext, str)
        self.assertEqual(len(app.client_secret_plaintext), 64)
        
        # Verify it matches the hash
        self.assertTrue(app.verify_secret(app.client_secret_plaintext))

    def test_plaintext_available_after_regenerate(self):
        """Test that client_secret_plaintext is available after secret regeneration."""
        app = self.OAuthApplication.create({
            'name': 'Test Regenerate Plaintext App'
        })
        
        # Get initial plaintext
        app.invalidate_recordset()
        initial_plaintext = app.client_secret_plaintext
        
        # Regenerate secret
        app.action_regenerate_secret()
        
        # Get new plaintext
        app.invalidate_recordset()
        new_plaintext = app.client_secret_plaintext
        
        # Should be different
        self.assertNotEqual(initial_plaintext, new_plaintext)
        
        # New plaintext should verify
        self.assertTrue(app.verify_secret(new_plaintext))

    def test_plaintext_not_stored_in_database(self):
        """Test that client_secret_plaintext is NOT stored in database."""
        app = self.OAuthApplication.create({
            'name': 'Test Not Stored App'
        })
        
        # Read from database directly
        app_data = self.OAuthApplication.browse(app.id).read(['client_secret'])[0]
        
        # Database should only have hash
        self.assertTrue(app_data['client_secret'].startswith('$2b$'))
        
        # No plaintext column should exist
        self.env.cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'oauth_application' 
            AND column_name = 'client_secret_plaintext'
        """)
        result = self.env.cr.fetchall()
        self.assertEqual(len(result), 0, "client_secret_plaintext should not exist in database")

    def test_multiple_apps_have_independent_cache(self):
        """Test that multiple applications have independent plaintext caches."""
        app1 = self.OAuthApplication.create({'name': 'App 1'})
        app2 = self.OAuthApplication.create({'name': 'App 2'})
        
        app1.invalidate_recordset()
        app2.invalidate_recordset()
        
        plaintext1 = app1.client_secret_plaintext
        plaintext2 = app2.client_secret_plaintext
        
        # Should be different
        self.assertNotEqual(plaintext1, plaintext2)
        
        # Each should verify its own hash
        self.assertTrue(app1.verify_secret(plaintext1))
        self.assertTrue(app2.verify_secret(plaintext2))
        
        # Should NOT cross-verify
        self.assertFalse(app1.verify_secret(plaintext2))
        self.assertFalse(app2.verify_secret(plaintext1))

    def test_plaintext_works_with_e2e_workflow(self):
        """Test complete E2E workflow: create app, get plaintext, generate token."""
        # Simulate E2E test workflow
        app = self.OAuthApplication.create({
            'name': 'E2E Workflow Test App',
            'description': 'Testing E2E workflow'
        })
        
        # Step 1: Get credentials immediately after creation
        app.invalidate_recordset()
        client_id = app.client_id
        client_secret = app.client_secret_plaintext
        
        # Verify we got valid credentials
        self.assertIsNotNone(client_id)
        self.assertIsNotNone(client_secret)
        self.assertEqual(len(client_secret), 64)
        
        # Step 2: Verify secret works for authentication
        self.assertTrue(app.verify_secret(client_secret))
        
        # Step 3: Simulate finding app by client_id (like auth_controller does)
        found_app = self.OAuthApplication.search([('client_id', '=', client_id)], limit=1)
        self.assertEqual(found_app.id, app.id)
        
        # Step 4: Verify the secret still works
        self.assertTrue(found_app.verify_secret(client_secret))
