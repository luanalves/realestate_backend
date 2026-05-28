# -*- coding: utf-8 -*-
"""Health Controller - public endpoint # public endpoint"""

from odoo import http
from odoo.http import request, Response
import json

_STATUS_OK = json.dumps({"status": "ok"})


class HealthController(http.Controller):

    # public endpoint
    @http.route('/api/v1/health', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    def health(self, **kwargs):
        return Response(
            _STATUS_OK,
            status=200,
            headers={"Content-Type": "application/json"},
        )
