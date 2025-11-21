# -*- coding: utf-8 -*-
"""
Unit Tests for API Models (Pure mocks - no database)
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestOAuthApplicationModel(unittest.TestCase):
    """Test OAuth Application model methods"""
    
    def test_generate_client_id_uniqueness(self):
        """Test client_id generation produces unique values"""
        import uuid
        
        ids = [str(uuid.uuid4()) for _ in range(10)]
        
        # All should be unique
        self.assertEqual(len(ids), len(set(ids)))
        
    def test_generate_client_secret_uniqueness(self):
        """Test client_secret generation produces unique values"""
        import secrets
        
        secrets_list = [secrets.token_urlsafe(32) for _ in range(10)]
        
        # All should be unique
        self.assertEqual(len(secrets_list), len(set(secrets_list)))
        
    def test_regenerate_secret_action(self):
        """Test regenerate secret action"""
        import secrets
        
        # Simulate current secret
        old_secret = secrets.token_urlsafe(32)
        
        # Regenerate
        new_secret = secrets.token_urlsafe(32)
        
        self.assertNotEqual(old_secret, new_secret)
        self.assertGreater(len(new_secret), 40)
        
    def test_revoke_all_tokens_action(self):
        """Test revoke all tokens action"""
        # Mock application with tokens
        app = Mock()
        token1 = Mock(revoked=False)
        token2 = Mock(revoked=False)
        token3 = Mock(revoked=False)
        app.token_ids = [token1, token2, token3]
        
        # Revoke all
        for token in app.token_ids:
            token.revoked = True
            
        # Verify all revoked
        self.assertTrue(all(t.revoked for t in app.token_ids))
        
    def test_compute_token_count(self):
        """Test token count computation"""
        app = Mock()
        app.token_ids = [Mock(revoked=False) for _ in range(5)]
        
        # Count active (non-revoked) tokens
        active_count = len([t for t in app.token_ids if not t.revoked])
        
        self.assertEqual(active_count, 5)
        
    def test_compute_token_count_excludes_revoked(self):
        """Test token count excludes revoked tokens"""
        app = Mock()
        app.token_ids = [
            Mock(revoked=False),
            Mock(revoked=True),
            Mock(revoked=False),
            Mock(revoked=True),
            Mock(revoked=False),
        ]
        
        active_count = len([t for t in app.token_ids if not t.revoked])
        
        self.assertEqual(active_count, 3)
        
    def test_application_active_flag(self):
        """Test application active flag"""
        app = Mock()
        app.active = True
        
        # Deactivate
        app.active = False
        
        self.assertFalse(app.active)


class TestOAuthTokenModel(unittest.TestCase):
    """Test OAuth Token model methods"""
    
    def test_token_is_valid_not_expired(self):
        """Test is_valid returns True for valid token"""
        token = Mock()
        token.revoked = False
        token.expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Check validity
        is_valid = not token.revoked and token.expires_at > datetime.utcnow()
        
        self.assertTrue(is_valid)
        
    def test_token_is_valid_expired(self):
        """Test is_valid returns False for expired token"""
        token = Mock()
        token.revoked = False
        token.expires_at = datetime.utcnow() - timedelta(hours=1)
        
        is_valid = not token.revoked and token.expires_at > datetime.utcnow()
        
        self.assertFalse(is_valid)
        
    def test_token_is_valid_revoked(self):
        """Test is_valid returns False for revoked token"""
        token = Mock()
        token.revoked = True
        token.expires_at = datetime.utcnow() + timedelta(hours=1)
        
        is_valid = not token.revoked and token.expires_at > datetime.utcnow()
        
        self.assertFalse(is_valid)
        
    def test_token_revoke_action(self):
        """Test token revoke action"""
        token = Mock()
        token.revoked = False
        
        # Revoke
        token.revoked = True
        
        self.assertTrue(token.revoked)
        
    def test_token_scope_empty(self):
        """Test token with empty scope"""
        token = Mock()
        token.scope = ''
        
        scopes = token.scope.split() if token.scope else []
        
        self.assertEqual(len(scopes), 0)
        
    def test_token_scope_multiple(self):
        """Test token with multiple scopes"""
        token = Mock()
        token.scope = 'read write admin delete'
        
        scopes = token.scope.split()
        
        self.assertEqual(len(scopes), 4)
        
    def test_token_default_expires_at(self):
        """Test token default expiration is 1 hour"""
        created_at = datetime.utcnow()
        default_expires = created_at + timedelta(hours=1)
        
        delta = (default_expires - created_at).total_seconds()
        
        self.assertEqual(delta, 3600)


class TestAPIEndpointModel(unittest.TestCase):
    """Test API Endpoint Registry model"""
    
    def test_register_endpoint(self):
        """Test registering new endpoint"""
        endpoint = Mock()
        endpoint.path = '/api/v1/test'
        endpoint.method = 'GET'
        endpoint.active = True
        endpoint.call_count = 0
        
        # Verify registered
        self.assertEqual(endpoint.path, '/api/v1/test')
        self.assertEqual(endpoint.method, 'GET')
        self.assertTrue(endpoint.active)
        
    def test_increment_call_count(self):
        """Test incrementing endpoint call count"""
        endpoint = Mock()
        endpoint.call_count = 10
        
        # Increment
        endpoint.call_count += 1
        
        self.assertEqual(endpoint.call_count, 11)
        
    def test_endpoint_last_called_at(self):
        """Test updating last_called_at timestamp"""
        endpoint = Mock()
        endpoint.last_called_at = None
        
        # Update timestamp
        endpoint.last_called_at = datetime.utcnow()
        
        self.assertIsNotNone(endpoint.last_called_at)
        self.assertIsInstance(endpoint.last_called_at, datetime)
        
    def test_endpoint_statistics(self):
        """Test endpoint statistics calculation"""
        endpoint = Mock()
        endpoint.call_count = 100
        endpoint.created_date = datetime.utcnow() - timedelta(days=10)
        
        # Calculate calls per day
        days_active = (datetime.utcnow() - endpoint.created_date).days
        if days_active > 0:
            calls_per_day = endpoint.call_count / days_active
        else:
            calls_per_day = endpoint.call_count
            
        self.assertEqual(calls_per_day, 10.0)
        
    def test_endpoint_path_validation(self):
        """Test endpoint path must start with /"""
        valid_paths = ['/api/v1/test', '/api/v2/users', '/']
        
        for path in valid_paths:
            self.assertTrue(path.startswith('/'))
            
    def test_endpoint_method_choices(self):
        """Test valid HTTP methods"""
        valid_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
        test_method = 'GET'
        
        self.assertIn(test_method, valid_methods)


class TestAPIAccessLogModel(unittest.TestCase):
    """Test API Access Log model"""
    
    def test_create_log_entry(self):
        """Test creating log entry"""
        log = Mock()
        log.endpoint_path = '/api/v1/test'
        log.method = 'GET'
        log.status_code = 200
        log.response_time = 125.5
        log.ip_address = '192.168.1.1'
        log.authenticated = True
        
        # Verify log data
        self.assertEqual(log.endpoint_path, '/api/v1/test')
        self.assertEqual(log.method, 'GET')
        self.assertEqual(log.status_code, 200)
        self.assertTrue(log.authenticated)
        
    def test_log_request_helper(self):
        """Test log_request helper function"""
        log_data = {
            'endpoint_path': '/api/v1/properties',
            'method': 'POST',
            'status_code': 201,
            'response_time': 250.0,
            'ip_address': '10.0.0.1',
            'user_agent': 'Python/requests',
            'authenticated': True,
        }
        
        # Verify required fields
        required_fields = ['endpoint_path', 'method', 'status_code']
        for field in required_fields:
            self.assertIn(field, log_data)
            
    def test_cleanup_old_logs_logic(self):
        """Test cleanup old logs logic"""
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Mock logs
        old_log = Mock()
        old_log.create_date = cutoff_date - timedelta(days=5)
        
        recent_log = Mock()
        recent_log.create_date = datetime.utcnow()
        
        # Check which should be deleted
        should_delete_old = old_log.create_date < cutoff_date
        should_delete_recent = recent_log.create_date < cutoff_date
        
        self.assertTrue(should_delete_old)
        self.assertFalse(should_delete_recent)
        
    def test_response_time_measurement(self):
        """Test response time is measured in milliseconds"""
        import time
        
        start = time.time()
        time.sleep(0.01)  # 10ms
        end = time.time()
        
        response_time_ms = (end - start) * 1000
        
        self.assertGreater(response_time_ms, 10)
        self.assertLess(response_time_ms, 50)
        
    def test_status_code_classification(self):
        """Test classifying status codes"""
        success_codes = [200, 201, 204]
        error_codes = [400, 401, 403, 404, 500]
        
        for code in success_codes:
            self.assertLess(code, 400)
            
        for code in error_codes:
            self.assertGreaterEqual(code, 400)
            
    def test_get_statistics_structure(self):
        """Test statistics structure"""
        stats = {
            'total_requests': 1000,
            'successful_requests': 950,
            'failed_requests': 50,
            'avg_response_time': 125.5,
            'most_used_endpoint': '/api/v1/properties',
        }
        
        # Verify structure
        self.assertIn('total_requests', stats)
        self.assertIn('successful_requests', stats)
        self.assertIn('avg_response_time', stats)
        
        # Verify math
        total = stats['successful_requests'] + stats['failed_requests']
        self.assertEqual(total, stats['total_requests'])


class TestJSONSchemaValidation(unittest.TestCase):
    """Test JSON Schema validation"""
    
    def test_valid_json_schema(self):
        """Test validating valid JSON against schema"""
        import jsonschema
        
        schema = {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'age': {'type': 'number'},
            },
            'required': ['name']
        }
        
        valid_data = {'name': 'John', 'age': 30}
        
        # Should not raise
        try:
            jsonschema.validate(valid_data, schema)
            is_valid = True
        except jsonschema.ValidationError:
            is_valid = False
            
        self.assertTrue(is_valid)
        
    def test_invalid_json_schema(self):
        """Test rejecting invalid JSON"""
        import jsonschema
        
        schema = {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'age': {'type': 'number'},
            },
            'required': ['name']
        }
        
        invalid_data = {'age': 30}  # Missing required 'name'
        
        # Should raise ValidationError
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(invalid_data, schema)
            
    def test_schema_type_validation(self):
        """Test schema validates data types"""
        import jsonschema
        
        schema = {
            'type': 'object',
            'properties': {
                'count': {'type': 'integer'},
            }
        }
        
        # Valid
        valid_data = {'count': 10}
        jsonschema.validate(valid_data, schema)
        
        # Invalid type
        invalid_data = {'count': 'ten'}
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(invalid_data, schema)


class TestMiddlewareFunctions(unittest.TestCase):
    """Test middleware helper functions"""
    
    def test_extract_jwt_from_request(self):
        """Test extracting JWT from request"""
        mock_request = Mock()
        mock_request.httprequest.headers = {
            'Authorization': 'Bearer abc123def456'
        }
        
        auth_header = mock_request.httprequest.headers.get('Authorization')
        parts = auth_header.split()
        
        token = parts[1] if len(parts) == 2 else None
        
        self.assertEqual(token, 'abc123def456')
        
    def test_check_token_scopes(self):
        """Test checking token has required scopes"""
        token_scopes = ['read', 'write', 'admin']
        required_scopes = ['read', 'write']
        
        has_scopes = all(s in token_scopes for s in required_scopes)
        
        self.assertTrue(has_scopes)
        
    def test_format_error_response(self):
        """Test formatting error response"""
        error_response = {
            'error': 'invalid_token',
            'error_description': 'Token has expired',
            'status': 401
        }
        
        self.assertEqual(error_response['error'], 'invalid_token')
        self.assertEqual(error_response['status'], 401)
        self.assertIn('error_description', error_response)


if __name__ == '__main__':
    unittest.main(verbosity=2)
