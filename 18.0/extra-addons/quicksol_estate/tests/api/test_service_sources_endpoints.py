# -*- coding: utf-8 -*-
"""
API Test: Service Sources Endpoints — Feature 015 (US4)

Task: T052
FRs: FR-010
"""
import json
import logging
from odoo.tests.common import HttpCase, tagged

_logger = logging.getLogger(__name__)
BASE = '/api/v1/service-sources'


@tagged('post_install', '-at_install', 'service_api')
class TestServiceSourcesEndpoints(HttpCase):

    def test_list_sources_requires_auth(self):
        resp = self.url_open(BASE)
        self.assertEqual(resp.status_code, 401)

    def test_create_source_requires_auth(self):
        resp = self.url_open(BASE,
                             data=json.dumps({'name': 'Website', 'code': 'site'}),
                             headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 401)

    def test_get_source_by_id_requires_auth(self):
        resp = self.url_open(f'{BASE}/1')
        self.assertIn(resp.status_code, [401, 404])

    def test_sources_endpoint_exists(self):
        resp = self.url_open(BASE)
        self.assertIn(resp.status_code, [200, 401])
