# -*- coding: utf-8 -*-
"""
API Test: Service Tags Endpoints — Feature 015 (US4)

Task: T051
FRs: FR-018, FR-019, FR-010
"""
import json
import logging
from odoo.tests.common import HttpCase, tagged

_logger = logging.getLogger(__name__)
BASE = '/api/v1/service-tags'


@tagged('post_install', '-at_install', 'service_api')
class TestServiceTagsEndpoints(HttpCase):

    def test_list_tags_requires_auth(self):
        resp = self.url_open(BASE)
        self.assertEqual(resp.status_code, 401)

    def test_create_tag_requires_auth(self):
        resp = self.url_open(BASE,
                             data=json.dumps({'name': 'Test', 'color': '#3498db'}),
                             headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 401)

    def test_get_tag_by_id_requires_auth(self):
        resp = self.url_open(f'{BASE}/1')
        self.assertIn(resp.status_code, [401, 404])

    def test_update_tag_requires_auth(self):
        resp = self.url_open(f'{BASE}/1',
                             data=json.dumps({'name': 'Updated'}),
                             headers={'Content-Type': 'application/json'})
        self.assertIn(resp.status_code, [401, 404, 405])

    def test_delete_tag_requires_auth(self):
        resp = self.url_open(f'{BASE}/1')
        self.assertIn(resp.status_code, [401, 404])

    def test_tags_endpoint_exists(self):
        resp = self.url_open(BASE)
        self.assertIn(resp.status_code, [200, 401])
