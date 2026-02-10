# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestOAuthApplication(TransactionCase):
    """Test cases for OAuth Application model"""

    def setUp(self):
        super(TestOAuthApplication, self).setUp()
        self.Application = self.env['thedevkitchen.oauth.application']

    def test_create_application(self):
        """Test creating an OAuth application"""
        app = self.Application.create({
            'name': 'Test Application',
            'description': 'Test Description'
        })
        
        self.assertTrue(app.client_id, "Client ID should be generated")
        self.assertTrue(app.client_secret, "Client Secret should be generated")
        # Verify client_secret is hashed (bcrypt format)
        self.assertTrue(app.client_secret.startswith('$2b$'), "Client Secret should be bcrypt hashed")
        self.assertEqual(len(app.client_secret), 60, "Bcrypt hash should be 60 characters")
        self.assertTrue(app.active, "Application should be active by default")
        self.assertEqual(app.name, 'Test Application')

    def test_client_id_uniqueness(self):
        """Test that client_id is unique"""
        app1 = self.Application.create({
            'name': 'App 1',
        })
        
        # Try to create another app with same client_id (should fail)
        with self.assertRaises(Exception):
            self.Application.create({
                'name': 'App 2',
                'client_id': app1.client_id,
            })

    def test_regenerate_secret(self):
        """Test regenerating client secret"""
        app = self.Application.create({
            'name': 'Test App',
        })
        
        old_secret = app.client_secret
        # Verify it's a bcrypt hash
        self.assertTrue(old_secret.startswith('$2b$'))
        
        app.action_regenerate_secret()
        
        self.assertNotEqual(app.client_secret, old_secret, "Secret should be different after regeneration")
        self.assertTrue(app.client_secret, "New secret should be generated")
        # Verify new secret is also bcrypt hashed
        self.assertTrue(app.client_secret.startswith('$2b$'))
        self.assertEqual(len(app.client_secret), 60)

    def test_token_count(self):
        """Test token count computation"""
        app = self.Application.create({
            'name': 'Test App',
        })
        
        self.assertEqual(app.token_count, 0, "New app should have 0 tokens")
        
        # Create a token
        self.env['thedevkitchen.oauth.token'].create({
            'application_id': app.id,
            'access_token': 'test_token_123',
            'token_type': 'Bearer',
        })
        
        # Recompute
        app._compute_token_count()
        self.assertEqual(app.token_count, 1, "App should have 1 token")

    def test_action_view_tokens(self):
        """Test view tokens action"""
        app = self.Application.create({
            'name': 'Test App',
        })
        
        action = app.action_view_tokens()
        
        self.assertIn('domain', action, "Action should have domain")
        self.assertIn('res_model', action, "Action should have res_model")
        self.assertEqual(action['res_model'], 'thedevkitchen.oauth.token')

    def test_application_name_required(self):
        """Test that name has a default value"""
        # Criar aplicação sem nome - deve usar valor padrão
        app = self.Application.create({
            'description': 'No name provided'
        })
        
        # Verificar que o nome foi definido automaticamente
        self.assertTrue(app.name, "Name should have a default value")
        self.assertEqual(app.name, 'OAuth Application', "Name should be 'OAuth Application'")

    def test_deactivate_application(self):
        """Test deactivating an application"""
        app = self.Application.create({
            'name': 'Test App',
            'active': True
        })
        
        self.assertTrue(app.active)
        
        app.write({'active': False})
        
        self.assertFalse(app.active, "Application should be inactive")

    def test_multiple_applications(self):
        """Test creating multiple applications"""
        app1 = self.Application.create({'name': 'App 1'})
        app2 = self.Application.create({'name': 'App 2'})
        app3 = self.Application.create({'name': 'App 3'})
        
        self.assertNotEqual(app1.client_id, app2.client_id)
        self.assertNotEqual(app1.client_id, app3.client_id)
        self.assertNotEqual(app2.client_id, app3.client_id)
        
        apps = self.Application.search([('name', 'in', ['App 1', 'App 2', 'App 3'])])
        self.assertEqual(len(apps), 3)
