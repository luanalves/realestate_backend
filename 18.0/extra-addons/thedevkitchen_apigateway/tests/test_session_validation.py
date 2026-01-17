# -*- coding: utf-8 -*-
"""
Test session_id validation logic

Tests:
- T007: session_id too short (10 chars) → expect 401
- T008: session_id too long (150 chars) → expect 401
- T009: session_id valid length (80 chars) → expect success
- T009a: session_id extraction priority (kwargs > body > headers)
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from odoo.tests.common import TransactionCase
from odoo import http


class TestSessionValidation(TransactionCase):
    """Test session_id format validation in @require_session decorator"""

    def setUp(self):
        super().setUp()
        # Import middleware after Odoo env is ready
        from ..middleware import require_session
        self.require_session = require_session

    def test_session_id_too_short(self):
        """T007: Reject session_id shorter than 60 chars"""
        
        # Create a mock function decorated with @require_session
        @self.require_session
        def mock_endpoint(**kwargs):
            return {'success': True}
        
        # Mock request with short session_id (10 chars)
        short_session_id = "1234567890"
        
        with patch('odoo.http.request') as mock_request:
            mock_request.get_json_data.return_value = {}
            mock_request.httprequest = Mock()
            mock_request.httprequest.headers.get.return_value = None
            mock_request.httprequest.cookies.get.return_value = None
            mock_request.session = Mock(sid=None)
            
            # Call with short session_id in kwargs
            result = mock_endpoint(session_id=short_session_id)
            
            # Verify 401 error returned
            self.assertIn('error', result)
            self.assertEqual(result['error']['status'], 401)
            self.assertIn('Invalid session_id format', result['error']['message'])
            self.assertIn('60-100 characters', result['error']['message'])

    def test_session_id_too_long(self):
        """T008: Reject session_id longer than 100 chars"""
        
        @self.require_session
        def mock_endpoint(**kwargs):
            return {'success': True}
        
        # Mock request with long session_id (150 chars)
        long_session_id = "a" * 150
        
        with patch('odoo.http.request') as mock_request:
            mock_request.get_json_data.return_value = {}
            mock_request.httprequest = Mock()
            mock_request.httprequest.headers.get.return_value = None
            mock_request.httprequest.cookies.get.return_value = None
            mock_request.session = Mock(sid=None)
            
            # Call with long session_id in kwargs
            result = mock_endpoint(session_id=long_session_id)
            
            # Verify 401 error returned
            self.assertIn('error', result)
            self.assertEqual(result['error']['status'], 401)
            self.assertIn('Invalid session_id format', result['error']['message'])

    def test_session_id_valid_length(self):
        """T009: Accept session_id with valid length (60-100 chars)"""
        
        @self.require_session
        def mock_endpoint(**kwargs):
            return {'success': True}
        
        # Mock request with valid session_id (80 chars - typical length)
        valid_session_id = "a" * 80
        
        with patch('odoo.http.request') as mock_request:
            # Mock SessionValidator to return valid session
            with patch('odoo.addons.thedevkitchen_apigateway.services.session_validator.SessionValidator.validate') as mock_validate:
                mock_user = Mock(id=1)
                mock_api_session = Mock(security_token='fake_jwt_token')
                mock_validate.return_value = (True, mock_user, mock_api_session, None)
                
                # Mock JWT decode
                with patch('jwt.decode') as mock_jwt_decode:
                    mock_jwt_decode.return_value = {
                        'uid': 1,
                        'fingerprint': {
                            'ip': '127.0.0.1',
                            'ua': 'test-agent',
                            'lang': 'en-US'
                        }
                    }
                    
                    # Mock config
                    with patch('odoo.tools.config.get') as mock_config:
                        mock_config.return_value = 'test_secret'
                        
                        # Mock request details
                        mock_request.get_json_data.return_value = {}
                        mock_request.httprequest = Mock()
                        mock_request.httprequest.remote_addr = '127.0.0.1'
                        mock_request.httprequest.headers.get = lambda key, default='': {
                            'User-Agent': 'test-agent',
                            'Accept-Language': 'en-US'
                        }.get(key, default)
                        mock_request.httprequest.cookies.get.return_value = None
                        mock_request.session = Mock(sid=None)
                        mock_request.env = Mock()
                        
                        # Call with valid session_id in kwargs
                        result = mock_endpoint(session_id=valid_session_id)
                        
                        # Verify success (no error)
                        self.assertEqual(result, {'success': True})

    def test_session_id_extraction_priority(self):
        """T009a: Verify kwargs > body > headers extraction priority"""
        
        @self.require_session
        def mock_endpoint(**kwargs):
            return {'session_id': kwargs.get('session_id', 'none')}
        
        session_from_kwargs = "k" * 80
        session_from_body = "b" * 80
        session_from_headers = "h" * 80
        
        # Test 1: kwargs takes priority over body and headers
        with patch('odoo.http.request') as mock_request:
            mock_request.get_json_data.return_value = {'session_id': session_from_body}
            mock_request.httprequest = Mock()
            mock_request.httprequest.headers.get = lambda key, default=None: session_from_headers if key == 'X-Openerp-Session-Id' else default
            mock_request.httprequest.cookies.get.return_value = None
            mock_request.session = Mock(sid=None)
            
            # Mock SessionValidator - will be called with kwargs session_id
            with patch('odoo.addons.thedevkitchen_apigateway.services.session_validator.SessionValidator.validate') as mock_validate:
                mock_user = Mock(id=1)
                mock_api_session = Mock(security_token='fake_jwt')
                
                # Verify the session_id passed to validator is from kwargs
                def validate_side_effect(session_id):
                    self.assertEqual(session_id, session_from_kwargs, "Should use kwargs session_id")
                    return (True, mock_user, mock_api_session, None)
                
                mock_validate.side_effect = validate_side_effect
                
                with patch('jwt.decode') as mock_jwt:
                    mock_jwt.return_value = {'uid': 1, 'fingerprint': {'ip': '127.0.0.1', 'ua': 'test', 'lang': 'en'}}
                    with patch('odoo.tools.config.get') as mock_config:
                        mock_config.return_value = 'secret'
                        mock_request.httprequest.remote_addr = '127.0.0.1'
                        mock_request.httprequest.headers.get = lambda k, d='': {'User-Agent': 'test', 'Accept-Language': 'en'}.get(k, d)
                        mock_request.env = Mock()
                        
                        # This should use session_from_kwargs
                        result = mock_endpoint(session_id=session_from_kwargs)
        
        # Test 2: body takes priority over headers when kwargs is missing
        with patch('odoo.http.request') as mock_request:
            mock_request.get_json_data.return_value = {'session_id': session_from_body}
            mock_request.httprequest = Mock()
            mock_request.httprequest.headers.get = lambda key, default=None: session_from_headers if key == 'X-Openerp-Session-Id' else default
            mock_request.httprequest.cookies.get.return_value = None
            mock_request.session = Mock(sid=None)
            
            with patch('odoo.addons.thedevkitchen_apigateway.services.session_validator.SessionValidator.validate') as mock_validate:
                mock_user = Mock(id=1)
                mock_api_session = Mock(security_token='fake_jwt')
                
                def validate_side_effect(session_id):
                    self.assertEqual(session_id, session_from_body, "Should use body session_id when kwargs is missing")
                    return (True, mock_user, mock_api_session, None)
                
                mock_validate.side_effect = validate_side_effect
                
                with patch('jwt.decode') as mock_jwt:
                    mock_jwt.return_value = {'uid': 1, 'fingerprint': {'ip': '127.0.0.1', 'ua': 'test', 'lang': 'en'}}
                    with patch('odoo.tools.config.get') as mock_config:
                        mock_config.return_value = 'secret'
                        mock_request.httprequest.remote_addr = '127.0.0.1'
                        mock_request.httprequest.headers.get = lambda k, d='': {'User-Agent': 'test', 'Accept-Language': 'en', 'X-Openerp-Session-Id': session_from_headers}.get(k, d)
                        mock_request.env = Mock()
                        
                        # Call WITHOUT session_id in kwargs - should use body
                        result = mock_endpoint()
