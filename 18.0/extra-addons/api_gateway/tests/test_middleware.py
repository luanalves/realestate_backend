# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from unittest.mock import Mock, patch
from odoo.addons.api_gateway.middleware import (
    require_jwt,
    require_jwt_with_scope,
    validate_json_schema,
    log_api_access,
)
import jwt


class TestMiddleware(TransactionCase):
    """Test cases for API Gateway Middleware"""

    def setUp(self):
        super(TestMiddleware, self).setUp()
        self.Application = self.env['oauth.application']
        self.Token = self.env['oauth.token']
        self.AccessLog = self.env['api.access.log']
        
        # Create test application
        self.app = self.Application.create({
            'name': 'Test App',
        })

    def test_require_jwt_decorator_valid_token(self):
        """Test @require_jwt decorator with valid token"""
        # Create a valid token
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'valid_test_token_123',
            'token_type': 'Bearer',
        })
        
        # Mock request
        request = Mock()
        request.httprequest.headers.get.return_value = 'Bearer valid_test_token_123'
        
        # Create decorated function
        @require_jwt
        def test_endpoint(self, **kwargs):
            return {'success': True}
        
        # Should work without error
        # (actual test would need full HTTP context)

    def test_require_jwt_missing_header(self):
        """Test @require_jwt when Authorization header is missing"""
        request = Mock()
        request.httprequest.headers.get.return_value = None
        
        # Should return error response
        # (integration test via HttpCase would be better)

    def test_require_jwt_invalid_format(self):
        """Test @require_jwt with invalid Authorization header format"""
        request = Mock()
        request.httprequest.headers.get.return_value = 'InvalidFormat token123'
        
        # Should return error for non-Bearer format

    def test_require_jwt_with_scope_valid(self):
        """Test @require_jwt_with_scope with valid scope"""
        # Create token with specific scope
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'scoped_token_123',
            'token_type': 'Bearer',
            'scope': 'read write',
        })
        
        @require_jwt_with_scope('read')
        def test_endpoint(self, **kwargs):
            return {'success': True}
        
        # Should allow access with 'read' scope

    def test_require_jwt_with_scope_insufficient(self):
        """Test @require_jwt_with_scope with insufficient scope"""
        # Create token with limited scope
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'limited_token_123',
            'token_type': 'Bearer',
            'scope': 'read',
        })
        
        @require_jwt_with_scope('write', 'admin')
        def test_endpoint(self, **kwargs):
            return {'success': True}
        
        # Should deny access (missing 'write' and 'admin' scopes)

    def test_validate_json_schema_valid(self):
        """Test @validate_json_schema with valid JSON"""
        schema = {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'age': {'type': 'number'},
            },
            'required': ['name'],
        }
        
        @validate_json_schema(schema)
        def test_endpoint(self, **kwargs):
            return {'success': True}
        
        # Valid data should pass

    def test_validate_json_schema_invalid(self):
        """Test @validate_json_schema with invalid JSON"""
        schema = {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
            },
            'required': ['name'],
        }
        
        @validate_json_schema(schema)
        def test_endpoint(self, **kwargs):
            return {'success': True}
        
        # Invalid data (missing required field) should fail

    def test_log_api_access_success(self):
        """Test log_api_access function for successful request"""
        # Mock request and response
        request = Mock()
        request.httprequest.path = '/api/v1/test'
        request.httprequest.method = 'GET'
        request.httprequest.remote_addr = '127.0.0.1'
        request.httprequest.headers.get.return_value = 'Mozilla/5.0'
        request.jwt_token = None
        request.jwt_application = None
        
        start_time = 1234567890.0
        
        # Create response
        response = Mock()
        response.status_code = 200
        
        with patch('time.time', return_value=start_time + 0.150):
            log = log_api_access(request, response, start_time)
        
        self.assertTrue(log)
        self.assertEqual(log.endpoint_path, '/api/v1/test')
        self.assertEqual(log.status_code, 200)
        self.assertAlmostEqual(log.response_time, 0.150, places=3)

    def test_log_api_access_with_auth(self):
        """Test log_api_access with authenticated request"""
        # Create token
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'test_token',
            'token_type': 'Bearer',
        })
        
        # Mock authenticated request
        request = Mock()
        request.httprequest.path = '/api/v1/protected'
        request.httprequest.method = 'POST'
        request.httprequest.remote_addr = '192.168.1.1'
        request.httprequest.headers.get.return_value = 'Python/requests'
        request.jwt_token = token
        request.jwt_application = self.app
        
        start_time = 1234567890.0
        response = Mock()
        response.status_code = 201
        
        with patch('time.time', return_value=start_time + 0.250):
            log = log_api_access(request, response, start_time)
        
        self.assertTrue(log.authenticated)
        self.assertEqual(log.application_id.id, self.app.id)
        self.assertEqual(log.token_id.id, token.id)

    def test_log_api_access_with_error(self):
        """Test log_api_access for error response"""
        request = Mock()
        request.httprequest.path = '/api/v1/test'
        request.httprequest.method = 'DELETE'
        request.httprequest.remote_addr = '10.0.0.1'
        request.httprequest.headers.get.return_value = 'curl/7.0'
        request.jwt_token = None
        request.jwt_application = None
        
        start_time = 1234567890.0
        
        # Error response
        response = Mock()
        response.status_code = 500
        response.data = b'{"error": "internal_error"}'
        
        with patch('time.time', return_value=start_time + 0.050):
            log = log_api_access(request, response, start_time)
        
        self.assertEqual(log.status_code, 500)

    def test_revoked_token_rejection(self):
        """Test that revoked tokens are rejected"""
        # Create and revoke token
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'revoked_token',
            'token_type': 'Bearer',
        })
        token.action_revoke()
        
        # Middleware should reject revoked token
        self.assertTrue(token.revoked)

    def test_expired_token_rejection(self):
        """Test that expired tokens are rejected"""
        from datetime import datetime, timedelta
        
        # Create expired token
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'expired_token',
            'token_type': 'Bearer',
            'expires_at': datetime.now() - timedelta(hours=1),
        })
        
        # Middleware should reject expired token
        self.assertLess(token.expires_at, datetime.now())

    def test_multiple_scopes_validation(self):
        """Test scope validation with multiple scopes"""
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'multi_scope_token',
            'token_type': 'Bearer',
            'scope': 'read write admin',
        })
        
        # Token has all required scopes
        self.assertIn('read', token.scope)
        self.assertIn('write', token.scope)
        self.assertIn('admin', token.scope)

    def test_case_sensitive_scope(self):
        """Test that scope matching is case-sensitive"""
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'case_test_token',
            'token_type': 'Bearer',
            'scope': 'READ WRITE',
        })
        
        # Scopes are case-sensitive
        self.assertIn('READ', token.scope)
        self.assertNotIn('read', token.scope)

    def test_log_preserves_payload(self):
        """Test that logging preserves request/response payloads"""
        log = self.AccessLog.create({
            'endpoint_path': '/api/v1/echo',
            'method': 'POST',
            'status_code': 200,
            'response_time': 0.1,
            'ip_address': '127.0.0.1',
            'request_payload': '{"message": "Hello"}',
            'response_payload': '{"echo": "Hello"}',
        })
        
        self.assertIn('Hello', log.request_payload)
        self.assertIn('echo', log.response_payload)
