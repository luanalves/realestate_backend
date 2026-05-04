# -*- coding: utf-8 -*-
"""
API Test: Multi-Tenant Isolation — Feature 015 (US2)

Verifies that unauthenticated cross-company access is denied for all
service endpoints (isolation enforced via @require_company decorator).

Task: T034
FR: FR-011
"""
import logging
from odoo.tests.common import HttpCase, tagged

_logger = logging.getLogger(__name__)

BASE_URL = '/api/v1/services'


@tagged('post_install', '-at_install', 'service_api')
class TestServiceIsolation(HttpCase):
    """Company isolation: unauthenticated requests are always 401."""

    def _assert_isolated(self, url, method='GET', data=None):
        if method == 'GET':
            resp = self.url_open(url)
        else:
            import json
            resp = self.url_open(url,
                                 data=json.dumps(data or {}),
                                 headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 401,
                         f'{method} {url} should return 401 without auth')

    def test_list_isolated(self):
        self._assert_isolated(BASE_URL)

    def test_summary_isolated(self):
        self._assert_isolated(f'{BASE_URL}/summary')

    def test_get_by_id_isolated(self):
        self._assert_isolated(f'{BASE_URL}/99999')

    def test_create_isolated(self):
        self._assert_isolated(BASE_URL, method='POST',
                              data={'operation_type': 'rent', 'client': {'name': 'X'}})

    def test_tags_isolated(self):
        self._assert_isolated('/api/v1/service-tags')

    def test_sources_isolated(self):
        self._assert_isolated('/api/v1/service-sources')
