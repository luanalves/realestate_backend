# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestApiEndpoint(TransactionCase):
    """Test cases for API Endpoint Registry"""

    def setUp(self):
        super(TestApiEndpoint, self).setUp()
        self.Endpoint = self.env['thedevkitchen.api.endpoint']
        # Clean existing endpoints to avoid unique constraint violations
        self.Endpoint.search([]).unlink()

    def test_create_endpoint(self):
        """Test creating an API endpoint"""
        endpoint = self.Endpoint.create({
            'name': 'List Properties',
            'path': '/api/v1/properties',
            'method': 'GET',
            'module_name': 'quicksol_estate',
            'description': 'Get all properties',
        })
        
        self.assertEqual(endpoint.path, '/api/v1/properties')
        self.assertEqual(endpoint.method, 'GET')
        self.assertTrue(endpoint.protected, "Endpoint should be protected by default")
        self.assertTrue(endpoint.active, "Endpoint should be active by default")

    def test_path_validation(self):
        """Test that path must start with /"""
        with self.assertRaises(ValidationError):
            self.Endpoint.create({
                'name': 'Invalid Endpoint',
                'path': 'api/v1/test',  # Missing leading /
                'method': 'GET',
                'module_name': 'test',
            })

    def test_unique_path_method(self):
        """Test that path+method combination is unique"""
        self.Endpoint.create({
            'name': 'Endpoint 1',
            'path': '/api/v1/test',
            'method': 'GET',
            'module_name': 'test',
        })
        
        # Creating another endpoint with same path+method should fail
        with self.assertRaises(Exception):
            self.Endpoint.create({
                'name': 'Endpoint 2',
                'path': '/api/v1/test',
                'method': 'GET',
                'module_name': 'test',
            })

    def test_different_methods_same_path(self):
        """Test that same path with different methods is allowed"""
        endpoint1 = self.Endpoint.create({
            'name': 'GET Endpoint',
            'path': '/api/v1/test',
            'method': 'GET',
            'module_name': 'test',
        })
        
        endpoint2 = self.Endpoint.create({
            'name': 'POST Endpoint',
            'path': '/api/v1/test',
            'method': 'POST',
            'module_name': 'test',
        })
        
        self.assertNotEqual(endpoint1.id, endpoint2.id)

    def test_increment_call_count(self):
        """Test incrementing call counter"""
        endpoint = self.Endpoint.create({
            'name': 'Test Endpoint',
            'path': '/api/v1/test',
            'method': 'GET',
            'module_name': 'test',
        })
        
        self.assertEqual(endpoint.call_count, 0)
        
        endpoint.increment_call_count()
        self.assertEqual(endpoint.call_count, 1)
        self.assertTrue(endpoint.last_called)
        
        endpoint.increment_call_count()
        self.assertEqual(endpoint.call_count, 2)

    def test_get_full_info(self):
        """Test getting full endpoint information"""
        endpoint = self.Endpoint.create({
            'name': 'Test Endpoint',
            'path': '/api/v1/test',
            'method': 'GET',
            'module_name': 'test_module',
            'description': 'Test description',
            'summary': 'Test summary',
            'tags': 'Test,API',
        })
        
        info = endpoint.get_full_info()
        
        self.assertIn('name', info)
        self.assertIn('path', info)
        self.assertIn('method', info)
        self.assertIn('module', info)
        self.assertEqual(info['path'], '/api/v1/test')
        self.assertEqual(len(info['tags']), 2)

    def test_register_endpoint(self):
        """Test register_endpoint helper method"""
        # Register new endpoint
        endpoint = self.Endpoint.register_endpoint({
            'name': 'New Endpoint',
            'path': '/api/v1/new',
            'method': 'POST',
            'module_name': 'new_module',
        })
        
        self.assertTrue(endpoint)
        self.assertEqual(endpoint.path, '/api/v1/new')
        
        # Register again (should update)
        endpoint2 = self.Endpoint.register_endpoint({
            'name': 'Updated Endpoint',
            'path': '/api/v1/new',
            'method': 'POST',
            'module_name': 'new_module',
            'description': 'Updated description',
        })
        
        self.assertEqual(endpoint.id, endpoint2.id, "Should update existing endpoint")
        self.assertEqual(endpoint2.description, 'Updated description')

    def test_public_endpoint(self):
        """Test creating a public (non-protected) endpoint"""
        endpoint = self.Endpoint.create({
            'name': 'Public Endpoint',
            'path': '/api/v1/public',
            'method': 'GET',
            'module_name': 'test',
            'protected': False,
        })
        
        self.assertFalse(endpoint.protected)

    def test_swagger_fields(self):
        """Test Swagger-related fields"""
        endpoint = self.Endpoint.create({
            'name': 'Swagger Test',
            'path': '/api/v1/swagger-test',
            'method': 'GET',
            'module_name': 'test',
            'summary': 'Short summary',
            'tags': 'Tag1,Tag2,Tag3',
            'request_schema': '{"type": "object"}',
            'response_schema': '{"type": "array"}',
        })
        
        self.assertEqual(endpoint.summary, 'Short summary')
        self.assertIn('Tag1', endpoint.tags)
        self.assertTrue(endpoint.request_schema)
        self.assertTrue(endpoint.response_schema)

    def test_deactivate_endpoint(self):
        """Test deactivating an endpoint"""
        endpoint = self.Endpoint.create({
            'name': 'Test Endpoint',
            'path': '/api/v1/test',
            'method': 'GET',
            'module_name': 'test',
        })
        
        self.assertTrue(endpoint.active)
        
        endpoint.write({'active': False})
        
        self.assertFalse(endpoint.active)
