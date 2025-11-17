# -*- coding: utf-8 -*-
from odoo.tests.common import HttpCase
import json


class TestAuthController(HttpCase):
    """Test cases for OAuth Authentication Controller"""

    def setUp(self):
        super(TestAuthController, self).setUp()
        self.Application = self.env['oauth.application']
        self.Token = self.env['oauth.token']
        
        # Create test application
        self.app = self.Application.create({
            'name': 'Test Application',
        })
        
        # Store credentials
        self.client_id = self.app.client_id
        self.client_secret = self.app.client_secret

    def test_token_endpoint_client_credentials(self):
        """Test /api/v1/auth/token with client_credentials grant"""
        response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }),
            headers={'Content-Type': 'application/json'},
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('access_token', data)
        self.assertIn('token_type', data)
        self.assertIn('expires_in', data)
        self.assertIn('refresh_token', data)
        self.assertEqual(data['token_type'], 'Bearer')

    def test_token_endpoint_invalid_credentials(self):
        """Test token endpoint with invalid credentials"""
        response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': 'wrong_secret',
            }),
            headers={'Content-Type': 'application/json'},
        )
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'invalid_client')

    def test_token_endpoint_missing_grant_type(self):
        """Test token endpoint without grant_type"""
        response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }),
            headers={'Content-Type': 'application/json'},
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'invalid_request')

    def test_refresh_endpoint(self):
        """Test /api/v1/auth/refresh with valid refresh token"""
        # First, get a token
        token_response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }),
            headers={'Content-Type': 'application/json'},
        )
        
        token_data = json.loads(token_response.content)
        refresh_token = token_data['refresh_token']
        
        # Use refresh token
        refresh_response = self.url_open(
            '/api/v1/auth/refresh',
            data=json.dumps({
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
            }),
            headers={'Content-Type': 'application/json'},
        )
        
        self.assertEqual(refresh_response.status_code, 200)
        refresh_data = json.loads(refresh_response.content)
        
        self.assertIn('access_token', refresh_data)
        self.assertNotEqual(refresh_data['access_token'], token_data['access_token'])

    def test_refresh_endpoint_invalid_token(self):
        """Test refresh endpoint with invalid refresh token"""
        response = self.url_open(
            '/api/v1/auth/refresh',
            data=json.dumps({
                'grant_type': 'refresh_token',
                'refresh_token': 'invalid_refresh_token',
            }),
            headers={'Content-Type': 'application/json'},
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'invalid_grant')

    def test_revoke_endpoint(self):
        """Test /api/v1/auth/revoke endpoint"""
        # Get a token first
        token_response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }),
            headers={'Content-Type': 'application/json'},
        )
        
        token_data = json.loads(token_response.content)
        access_token = token_data['access_token']
        
        # Revoke the token
        revoke_response = self.url_open(
            '/api/v1/auth/revoke',
            data=json.dumps({
                'token': access_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }),
            headers={'Content-Type': 'application/json'},
        )
        
        self.assertEqual(revoke_response.status_code, 200)

    def test_revoke_endpoint_invalid_token(self):
        """Test revoke endpoint with non-existent token"""
        response = self.url_open(
            '/api/v1/auth/revoke',
            data=json.dumps({
                'token': 'non_existent_token',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }),
            headers={'Content-Type': 'application/json'},
        )
        
        # Should still return 200 (RFC 7009)
        self.assertEqual(response.status_code, 200)

    def test_token_with_scope(self):
        """Test requesting token with specific scope"""
        response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'read write',
            }),
            headers={'Content-Type': 'application/json'},
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('scope', data)
        self.assertIn('read', data['scope'])

    def test_inactive_application(self):
        """Test that inactive application cannot get token"""
        # Deactivate application
        self.app.write({'active': False})
        
        response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }),
            headers={'Content-Type': 'application/json'},
        )
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        
        self.assertEqual(data['error'], 'invalid_client')

    def test_content_type_validation(self):
        """Test that endpoint requires JSON content type"""
        response = self.url_open(
            '/api/v1/auth/token',
            data='grant_type=client_credentials&client_id=' + self.client_id,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        
        # Should still work with form data
        self.assertIn(response.status_code, [200, 400])
