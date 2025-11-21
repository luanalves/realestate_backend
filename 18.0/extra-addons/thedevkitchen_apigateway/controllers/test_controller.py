# -*- coding: utf-8 -*-
"""
Test Controller for JWT Middleware

This controller demonstrates how to use the JWT middleware decorators
"""

import json
from odoo import http
from odoo.http import request
from ..middleware import require_jwt, require_jwt_with_scope, log_api_access


class TestController(http.Controller):
    """Test endpoints for JWT middleware"""

    @http.route('/api/v1/test/public', type='http', auth='none', methods=['GET'], csrf=False)
    def test_public(self, **kwargs):
        """Public endpoint (no authentication required)"""
        return request.make_json_response({
            'message': 'This is a public endpoint',
            'protected': False
        })

    @http.route('/api/v1/test/protected', type='http', auth='none', methods=['GET'], csrf=False)
    @require_jwt
    def test_protected(self, **kwargs):
        """Protected endpoint (JWT required)"""
        log_api_access('/api/v1/test/protected', 'GET', 200)
        
        return request.make_json_response({
            'message': 'You are authenticated!',
            'protected': True,
            'application': request.jwt_application.name,
            'client_id': request.jwt_application.client_id,
            'token_expires_at': request.jwt_token.expires_at.isoformat() if request.jwt_token.expires_at else None
        })

    @http.route('/api/v1/test/scoped', type='http', auth='none', methods=['GET'], csrf=False)
    @require_jwt_with_scope('admin', 'write')
    def test_scoped(self, **kwargs):
        """Endpoint with scope requirements (JWT + scopes required)"""
        log_api_access('/api/v1/test/scoped', 'GET', 200)
        
        return request.make_json_response({
            'message': 'You have admin and write scopes!',
            'protected': True,
            'scopes': request.jwt_token.scope.split() if request.jwt_token.scope else []
        })

    @http.route('/api/v1/test/echo', type='json', auth='none', methods=['POST'], csrf=False)
    @require_jwt
    def test_echo(self, **kwargs):
        """Echo endpoint that returns the JSON body sent"""
        log_api_access('/api/v1/test/echo', 'POST', 200)
        
        return {
            'message': 'Echo endpoint',
            'received': request.jsonrequest,
            'application': request.jwt_application.name
        }
