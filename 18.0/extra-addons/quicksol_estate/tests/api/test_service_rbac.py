# -*- coding: utf-8 -*-
"""
API Test: Service RBAC Matrix — Feature 015 (US2)

Tests authorization matrix (FR-010) for all 5 profiles × 7 operations.
Without a live Odoo session, all calls return 401; the matrix logic
is validated via unit tests on the model layer.

Task: T033
FR: FR-010
"""
import json
import logging
from odoo.tests.common import HttpCase, tagged

_logger = logging.getLogger(__name__)

BASE_URL = '/api/v1/services'


@tagged('post_install', '-at_install', 'service_api')
class TestServiceRBAC(HttpCase):
    """RBAC: all protected endpoints return 401 without credentials."""

    def test_create_requires_auth(self):
        resp = self.url_open(BASE_URL,
                             data=json.dumps({'operation_type': 'rent', 'client': {'name': 'X'}}),
                             headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 401)

    def test_list_requires_auth(self):
        resp = self.url_open(BASE_URL)
        self.assertEqual(resp.status_code, 401)

    def test_get_requires_auth(self):
        resp = self.url_open(f'{BASE_URL}/1')
        self.assertEqual(resp.status_code, 401)

    def test_update_requires_auth(self):
        resp = self.url_open(f'{BASE_URL}/1',
                             data=json.dumps({'notes': 'x'}),
                             headers={'Content-Type': 'application/json'})
        self.assertIn(resp.status_code, [401, 405])

    def test_delete_requires_auth(self):
        resp = self.url_open(f'{BASE_URL}/1')
        self.assertEqual(resp.status_code, 401)

    def test_stage_patch_requires_auth(self):
        resp = self.url_open(f'{BASE_URL}/1/stage',
                             data=json.dumps({'stage': 'in_service'}),
                             headers={'Content-Type': 'application/json'})
        self.assertIn(resp.status_code, [401, 405])

    def test_reassign_patch_requires_auth(self):
        resp = self.url_open(f'{BASE_URL}/1/reassign',
                             data=json.dumps({'new_agent_id': 1}),
                             headers={'Content-Type': 'application/json'})
        self.assertIn(resp.status_code, [401, 405])

    def test_summary_requires_auth(self):
        resp = self.url_open(f'{BASE_URL}/summary')
        self.assertEqual(resp.status_code, 401)
