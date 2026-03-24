# -*- coding: utf-8 -*-
"""Test controller to verify SQL query tracing."""

from odoo import http
from odoo.http import request
from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request
import json


class TestTracingController(http.Controller):
    """Test controller for database instrumentation."""

    @http.route('/api/v1/test-db-trace', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @trace_http_request
    def test_db_tracing(self, **kwargs):
        """
        Test endpoint that executes SQL queries within HTTP span.
        
        This will help verify if SQL spans are correctly linked to HTTP parent span.
        """
        # Execute some SQL queries directly
        request.env.cr.execute("SELECT 1 as test_value")
        result1 = request.env.cr.fetchone()
        
        request.env.cr.execute("SELECT count(*) FROM res_users")
        result2 = request.env.cr.fetchone()
        
        request.env.cr.execute("SELECT id, name FROM res_company LIMIT 3")
        companies = request.env.cr.fetchall()
        
        # Also test ORM queries (which use psycopg2 under the hood)
        users = request.env['res.users'].sudo().search([], limit=5)
        
        return request.make_json_response({
            'status': 'success',
            'test_value': result1[0] if result1 else None,
            'user_count': result2[0] if result2 else 0,
            'companies_count': len(companies),
            'users_found': len(users),
            'message': 'Check Tempo for SQL child spans in this trace'
        })
