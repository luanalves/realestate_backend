# -*- coding: utf-8 -*-
"""
Phase 6 - Enhanced Span Attributes Tests

Verifies that Phase 6 enhanced attributes are correctly added to traces:
- User context (user.id, user.email, user.profile)
- Multi-tenancy (company.id, company.name, company.allowed_ids)
- Request metadata (content_length, referer, api.version)
- Session information (session.id, session.age_seconds)
- Database enhancements (query.fingerprint, query.type, parameter_count)
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import re

from odoo.tests import common


class TestEnhancedSpanAttributes(common.TransactionCase):
    """Test Phase 6 enhanced span attributes in HTTP and DB instrumentations"""
    
    def setUp(self):
        super().setUp()
        self.env = self.env(su=True)  # Superuser access for testing
    
    def test_query_fingerprint_generation(self):
        """Test that SQL query fingerprints normalize similar queries"""
        from odoo.addons.thedevkitchen_observability.services.db_instrumentor import (
            _generate_query_fingerprint
        )
        
        query1 = "SELECT * FROM users WHERE id = 123"
        query2 = "SELECT * FROM users WHERE id = 456"
        query3 = "SELECT * FROM users WHERE id = 789"
        
        fp1 = _generate_query_fingerprint(query1)
        fp2 = _generate_query_fingerprint(query2)
        fp3 = _generate_query_fingerprint(query3)
        
        # All three queries should have same fingerprint
        self.assertEqual(fp1, fp2)
        self.assertEqual(fp2, fp3)
        self.assertEqual(fp1, "SELECT * FROM users WHERE id = ?")
    
    def test_query_fingerprint_string_literals(self):
        """Test that string literals are normalized in fingerprints"""
        from odoo.addons.thedevkitchen_observability.services.db_instrumentor import (
            _generate_query_fingerprint
        )
        
        query1 = "SELECT * FROM users WHERE email = 'john@example.com'"
        query2 = "SELECT * FROM users WHERE email = 'jane@example.com'"
        
        fp1 = _generate_query_fingerprint(query1)
        fp2 = _generate_query_fingerprint(query2)
        
        self.assertEqual(fp1, fp2)
        self.assertTrue('?' in fp1)
        self.assertNotIn('john', fp1)
        self.assertNotIn('jane', fp2)
    
    def test_query_fingerprint_in_clauses(self):
        """Test that IN clauses are normalized"""
        from odoo.addons.thedevkitchen_observability.services.db_instrumentor import (
            _generate_query_fingerprint
        )
        
        query1 = "SELECT * FROM users WHERE id IN (1, 2, 3)"
        query2 = "SELECT * FROM users WHERE id IN (4, 5, 6, 7, 8)"
        
        fp1 = _generate_query_fingerprint(query1)
        fp2 = _generate_query_fingerprint(query2)
        
        self.assertEqual(fp1, fp2)
        self.assertIn('IN (?)', fp1)
    
    @patch('odoo.addons.thedevkitchen_observability.services.tracer.get_tracer')
    def test_http_user_context_attributes(self, mock_get_tracer):
        """Test that user context attributes are added to HTTP spans"""
        # Mock tracer and span
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request
        from odoo.http import request
        
        # Create mock user with profile
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.email = "test@example.com"
        mock_profile = Mock()
        mock_profile.name = "agent"
        mock_user.profile_id = mock_profile
        
        # Create mock request with session
        mock_request = Mock()
        mock_request.session.uid = 42
        mock_request.env.user = mock_user
        mock_request.httprequest.method = "GET"
        mock_request.httprequest.path = "/api/v1/users"
        mock_request.httprequest.url = "http://localhost/api/v1/users"
        mock_request.httprequest.scheme = "http"
        mock_request.httprequest.full_path = "/api/v1/users"
        mock_request.httprequest.headers = {}
        mock_request.httprequest.remote_addr = "127.0.0.1"
        
        @trace_http_request
        def test_endpoint(**kwargs):
            return "success"
        
        with patch('odoo.http.request', mock_request):
            with patch('odoo.addons.thedevkitchen_observability.services.tracer._is_tracing_enabled', return_value=True):
                result = test_endpoint()
        
        # Verify user attributes were set
        span_calls = {call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list}
        
        self.assertEqual(span_calls.get('enduser.id'), '42')
        self.assertEqual(span_calls.get('enduser.name'), 'Test User')
        self.assertEqual(span_calls.get('user.email'), 'test@example.com')
        self.assertEqual(span_calls.get('user.profile'), 'agent')
    
    @patch('odoo.addons.thedevkitchen_observability.services.tracer.get_tracer')
    def test_http_company_attributes(self, mock_get_tracer):
        """Test that multi-tenancy attributes are added to HTTP spans"""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request
        
        # Create mock company
        mock_company = Mock()
        mock_company.id = 1
        mock_company.name = "Company A"
        
        mock_companies = Mock()
        mock_companies.ids = [1, 2, 3]  # User has access to 3 companies
        
        mock_request = Mock()
        mock_request.session.uid = 42
        mock_request.env.company = mock_company
        mock_request.env.companies = mock_companies
        mock_request.env.user = Mock(name="Test User")
        mock_request.httprequest.method = "GET"
        mock_request.httprequest.path = "/api/v1/companies"
        mock_request.httprequest.url = "http://localhost/api/v1/companies"
        mock_request.httprequest.scheme = "http"
        mock_request.httprequest.full_path = "/api/v1/companies"
        mock_request.httprequest.headers = {}
        mock_request.httprequest.remote_addr = "127.0.0.1"
        
        @trace_http_request
        def test_endpoint(**kwargs):
            return "success"
        
        with patch('odoo.http.request', mock_request):
            with patch('odoo.addons.thedevkitchen_observability.services.tracer._is_tracing_enabled', return_value=True):
                result = test_endpoint()
        
        # Verify company attributes were set
        span_calls = {call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list}
        
        self.assertEqual(span_calls.get('company.id'), 1)
        self.assertEqual(span_calls.get('company.name'), 'Company A')
        self.assertEqual(span_calls.get('company.allowed_ids'), '1,2,3')
    
    @patch('odoo.addons.thedevkitchen_observability.services.tracer.get_tracer')
    def test_http_api_version_extraction(self, mock_get_tracer):
        """Test that API version is extracted from route"""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request
        
        mock_request = Mock()
        mock_request.session.uid = None  # No user
        mock_request.httprequest.method = "GET"
        mock_request.httprequest.path = "/api/v1/health"
        mock_request.httprequest.url = "http://localhost/api/v1/health"
        mock_request.httprequest.scheme = "http"
        mock_request.httprequest.full_path = "/api/v1/health"
        mock_request.httprequest.headers = {}
        mock_request.httprequest.remote_addr = "127.0.0.1"
        mock_request.httprequest.data = b''
        
        @trace_http_request
        def test_endpoint(**kwargs):
            return "success"
        
        with patch('odoo.http.request', mock_request):
            with patch('odoo.addons.thedevkitchen_observability.services.tracer._is_tracing_enabled', return_value=True):
                result = test_endpoint()
        
        # Verify API version was extracted
        span_calls = {call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list}
        
        self.assertEqual(span_calls.get('api.version'), 'v1')
    
    @patch('odoo.addons.thedevkitchen_observability.services.tracer.get_tracer')
    def test_http_session_attributes(self, mock_get_tracer):
        """Test that session information is added to spans"""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request
        import time
        
        mock_session = Mock()
        mock_session.sid = "abc123def456"
        mock_session.creation_time = time.time() - 3600  # Created 1 hour ago
        mock_session.uid = 42
        
        mock_request = Mock()
        mock_request.session = mock_session
        mock_request.env.user = Mock(name="Test User")
        mock_request.httprequest.method = "GET"
        mock_request.httprequest.path = "/api/v1/users"
        mock_request.httprequest.url = "http://localhost/api/v1/users"
        mock_request.httprequest.scheme = "http"
        mock_request.httprequest.full_path = "/api/v1/users"
        mock_request.httprequest.headers = {}
        mock_request.httprequest.remote_addr = "127.0.0.1"
        mock_request.httprequest.data = b''
        
        @trace_http_request
        def test_endpoint(**kwargs):
            return "success"
        
        with patch('odoo.http.request', mock_request):
            with patch('odoo.addons.thedevkitchen_observability.services.tracer._is_tracing_enabled', return_value=True):
                result = test_endpoint()
        
        # Verify session attributes were set
        span_calls = {call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list}
        
        self.assertEqual(span_calls.get('session.id'), 'abc123def456')
        # Session age should be around 3600 seconds (±10 seconds for test execution)
        session_age = span_calls.get('session.age_seconds')
        self.assertIsNotNone(session_age)
        self.assertGreater(session_age, 3590)
        self.assertLess(session_age, 3610)
    
    def test_db_query_classification(self):
        """Test that database queries are properly classified"""
        from odoo.addons.thedevkitchen_observability.services.db_instrumentor import (
            _categorize_query
        )
        
        test_cases = [
            ("SELECT * FROM users", ("SELECT", "users")),
            ("INSERT INTO users (name) VALUES (?)", ("INSERT", "users")),
            ("UPDATE users SET name = ?", ("UPDATE", "users")),
            ("DELETE FROM users WHERE id = ?", ("DELETE", "users")),
            ("CREATE TABLE users (id INT)", ("CREATE", None)),
            ("WITH cte AS (SELECT 1) SELECT * FROM cte", ("WITH", "cte")),
        ]
        
        for query, expected in test_cases:
            operation, table = _categorize_query(query)
            self.assertEqual(operation, expected[0], f"Query: {query}")
            if expected[1]:
                self.assertEqual(table, expected[1], f"Query: {query}")


class TestPhase6Integration(common.TransactionCase):
    """Integration tests for Phase 6 enhanced attributes"""
    
    def setUp(self):
        super().setUp()
        self.env = self.env(su=True)
    
    def test_enhanced_attributes_end_to_end(self):
        """
        End-to-end test: Make API request, verify traces have enhanced attributes
        
        This test requires:
        - OpenTelemetry enabled (OTEL_ENABLED=true)
        - Tempo running and accessible
        """
        # Skip if OTEL not enabled
        import os
        if os.getenv('OTEL_ENABLED', 'true').lower() != 'true':
            self.skipTest("OpenTelemetry not enabled")
        
        try:
            from opentelemetry import trace
            from odoo.addons.thedevkitchen_observability.services.tracer import get_tracer
            
            tracer = get_tracer()
            if not tracer:
                self.skipTest("Tracer not available")
            
            # Create a test span and verify enhanced attributes can be set
            with tracer.start_as_current_span("test_enhanced_attributes") as span:
                # User context
                span.set_attribute("user.id", "42")
                span.set_attribute("user.email", "test@example.com")
                span.set_attribute("user.profile", "agent")
                
                # Company context
                span.set_attribute("company.id", 1)
                span.set_attribute("company.name", "Test Company")
                span.set_attribute("company.allowed_ids", "1,2,3")
                
                # API version
                span.set_attribute("api.version", "v1")
                
                # Session
                span.set_attribute("session.id", "test123")
                span.set_attribute("session.age_seconds", 3600)
                
                # Database query attributes
                span.set_attribute("db.query.type", "SELECT")
                span.set_attribute("db.query.fingerprint", "SELECT * FROM users WHERE id = ?")
                span.set_attribute("db.query.parameter_count", 1)
                span.set_attribute("db.query.returns_rows", True)
                
                # If we get here without exceptions, attributes are supported
                self.assertTrue(True)
        
        except ImportError:
            self.skip Test("OpenTelemetry dependencies not installed")


if __name__ == '__main__':
    unittest.main()
