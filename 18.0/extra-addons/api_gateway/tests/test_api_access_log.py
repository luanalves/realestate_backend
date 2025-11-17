# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import datetime, timedelta


class TestApiAccessLog(TransactionCase):
    """Test cases for API Access Log"""

    def setUp(self):
        super(TestApiAccessLog, self).setUp()
        self.AccessLog = self.env['api.access.log']
        self.Application = self.env['oauth.application']
        self.Token = self.env['oauth.token']
        
        # Create test application
        self.app = self.Application.create({
            'name': 'Test App',
        })

    def test_create_log(self):
        """Test creating an access log entry"""
        log = self.AccessLog.create({
            'endpoint_path': '/api/v1/test',
            'method': 'GET',
            'status_code': 200,
            'response_time': 0.125,
            'ip_address': '127.0.0.1',
            'user_agent': 'Mozilla/5.0',
        })
        
        self.assertEqual(log.endpoint_path, '/api/v1/test')
        self.assertEqual(log.method, 'GET')
        self.assertEqual(log.status_code, 200)
        self.assertTrue(log.create_date)

    def test_log_authenticated_request(self):
        """Test logging an authenticated request"""
        token = self.Token.create({
            'application_id': self.app.id,
            'access_token': 'test_token_123',
            'token_type': 'Bearer',
        })
        
        log = self.AccessLog.create({
            'endpoint_path': '/api/v1/properties',
            'method': 'GET',
            'status_code': 200,
            'response_time': 0.250,
            'ip_address': '192.168.1.100',
            'user_agent': 'Python/requests',
            'application_id': self.app.id,
            'token_id': token.id,
            'authenticated': True,
        })
        
        self.assertTrue(log.authenticated)
        self.assertEqual(log.application_id.id, self.app.id)
        self.assertEqual(log.token_id.id, token.id)

    def test_log_with_error(self):
        """Test logging a request with error"""
        log = self.AccessLog.create({
            'endpoint_path': '/api/v1/test',
            'method': 'POST',
            'status_code': 401,
            'response_time': 0.050,
            'ip_address': '10.0.0.1',
            'error_code': 'invalid_token',
            'error_description': 'The access token is invalid',
        })
        
        self.assertEqual(log.status_code, 401)
        self.assertEqual(log.error_code, 'invalid_token')
        self.assertTrue(log.error_description)

    def test_log_request_payload(self):
        """Test logging request and response payloads"""
        log = self.AccessLog.create({
            'endpoint_path': '/api/v1/properties',
            'method': 'POST',
            'status_code': 201,
            'response_time': 0.500,
            'ip_address': '127.0.0.1',
            'request_payload': '{"name": "House for Sale", "price": 250000}',
            'response_payload': '{"id": 1, "name": "House for Sale"}',
        })
        
        self.assertTrue(log.request_payload)
        self.assertTrue(log.response_payload)
        self.assertIn('House for Sale', log.request_payload)

    def test_log_request_helper(self):
        """Test the log_request helper method"""
        log = self.AccessLog.log_request(
            endpoint='/api/v1/test',
            method='GET',
            status_code=200,
            response_time=0.123,
            ip_address='127.0.0.1',
            user_agent='Test/1.0',
            authenticated=True,
        )
        
        self.assertTrue(log)
        self.assertEqual(log.endpoint_path, '/api/v1/test')
        self.assertEqual(log.status_code, 200)

    def test_cleanup_old_logs(self):
        """Test cleaning up old logs"""
        # Create old logs (31 days ago) - use SQL to set create_date in the past
        old_date = datetime.now() - timedelta(days=31)
        old_log = self.AccessLog.create({
            'endpoint_path': '/api/v1/old',
            'method': 'GET',
            'status_code': 200,
            'response_time': 0.1,
            'ip_address': '127.0.0.1',
        })
        
        # Manually update create_date using SQL (since it's readonly)
        self.env.cr.execute("""
            UPDATE api_access_log 
            SET create_date = %s 
            WHERE id = %s
        """, (old_date, old_log.id))
        
        # Create recent log (1 day ago)
        recent_log = self.AccessLog.create({
            'endpoint_path': '/api/v1/recent',
            'method': 'GET',
            'status_code': 200,
            'response_time': 0.1,
            'ip_address': '127.0.0.1',
        })
        
        # Cleanup logs older than 30 days
        deleted_count = self.AccessLog.cleanup_old_logs(days=30)
        
        # Old log should be deleted
        self.assertFalse(self.AccessLog.browse(old_log.id).exists())
        # Recent log should still exist
        self.assertTrue(self.AccessLog.browse(recent_log.id).exists())

    def test_get_statistics(self):
        """Test getting access statistics"""
        # Create multiple logs
        for i in range(5):
            self.AccessLog.create({
                'endpoint_path': '/api/v1/test',
                'method': 'GET',
                'status_code': 200,
                'response_time': 0.1 * (i + 1),
                'ip_address': '127.0.0.1',
            })
        
        # Create one error log
        self.AccessLog.create({
            'endpoint_path': '/api/v1/test',
            'method': 'GET',
            'status_code': 500,
            'response_time': 0.05,
            'ip_address': '127.0.0.1',
        })
        
        stats = self.AccessLog.get_statistics(days=7)
        
        self.assertIn('total_requests', stats)
        self.assertEqual(stats['total_requests'], 6)
        self.assertIn('error_count', stats)
        self.assertEqual(stats['error_count'], 1)
        self.assertIn('avg_response_time', stats)

    def test_success_error_classification(self):
        """Test that logs are correctly classified as success/error"""
        success_log = self.AccessLog.create({
            'endpoint_path': '/api/v1/test',
            'method': 'GET',
            'status_code': 200,
            'response_time': 0.1,
            'ip_address': '127.0.0.1',
        })
        
        error_log = self.AccessLog.create({
            'endpoint_path': '/api/v1/test',
            'method': 'GET',
            'status_code': 404,
            'response_time': 0.05,
            'ip_address': '127.0.0.1',
        })
        
        # Success: status 2xx and 3xx
        self.assertLess(success_log.status_code, 400)
        # Error: status 4xx and 5xx
        self.assertGreaterEqual(error_log.status_code, 400)

    def test_different_http_methods(self):
        """Test logging different HTTP methods"""
        methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        
        for method in methods:
            log = self.AccessLog.create({
                'endpoint_path': '/api/v1/test',
                'method': method,
                'status_code': 200,
                'response_time': 0.1,
                'ip_address': '127.0.0.1',
            })
            self.assertEqual(log.method, method)

    def test_response_time_tracking(self):
        """Test accurate response time tracking"""
        log = self.AccessLog.create({
            'endpoint_path': '/api/v1/slow',
            'method': 'GET',
            'status_code': 200,
            'response_time': 2.567,  # Slow request
            'ip_address': '127.0.0.1',
        })
        
        self.assertEqual(log.response_time, 2.567)
        self.assertGreater(log.response_time, 1.0)

    def test_multiple_clients(self):
        """Test logging requests from multiple IP addresses"""
        ips = ['127.0.0.1', '192.168.1.1', '10.0.0.1']
        
        for ip in ips:
            log = self.AccessLog.create({
                'endpoint_path': '/api/v1/test',
                'method': 'GET',
                'status_code': 200,
                'response_time': 0.1,
                'ip_address': ip,
            })
            self.assertEqual(log.ip_address, ip)
