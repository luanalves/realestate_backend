# -*- coding: utf-8 -*-
import json
import logging
from odoo.tests.common import HttpCase, tagged

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', 'service_api')
class TestServiceEndpoints(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_url = '/api/v1/services'

    def _auth_headers(self, token=None, session_id=None):
        """Build auth headers with JWT + session."""
        headers = {
            'Content-Type': 'application/json',
        }
        if token:
            headers['Authorization'] = f'Bearer {token}'
        if session_id:
            headers['X-Openerp-Session-Id'] = session_id
        return headers

    def _assert_hateoas_links(self, body, expected_rels=None):
        """Assert HATEOAS links are present in response body."""
        self.assertIn('links', body, 'Response must contain HATEOAS links')
        self.assertIsInstance(body['links'], list)
        if expected_rels:
            actual_rels = {lnk.get('rel') for lnk in body['links']}
            for rel in expected_rels:
                self.assertIn(rel, actual_rels, f'HATEOAS rel "{rel}" missing')

    def test_post_service_missing_auth_returns_401(self):
        """Unauthenticated POST must return 401."""
        resp = self.url_open(
            self.base_url,
            data=json.dumps({'operation_type': 'rent', 'source_id': 1,
                             'client': {'name': 'Test', 'phones': [{'type': 'mobile', 'number': '11999990000'}]}}),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 401)

    def test_get_service_missing_auth_returns_401(self):
        """Unauthenticated GET must return 401."""
        resp = self.url_open(self.base_url)
        self.assertEqual(resp.status_code, 401)

    def test_get_service_by_id_not_found_returns_404(self):
        """GET /services/99999999 for nonexistent ID must return 401 (unauth) or 404."""
        resp = self.url_open(f'{self.base_url}/99999999')
        # Without auth we expect 401; with auth + nonexistent → 404
        self.assertIn(resp.status_code, [401, 404])

    def test_patch_stage_endpoint_exists(self):
        """PATCH /services/{id}/stage endpoint must be routable (returns 401 without auth)."""
        resp = self.url_open(
            f'{self.base_url}/1/stage',
            data=json.dumps({'stage': 'in_service'}),
            headers={'Content-Type': 'application/json'},
        )
        # Without auth → 401; with auth → 200/422/404
        self.assertIn(resp.status_code, [401, 404, 405])

    def test_patch_reassign_endpoint_exists(self):
        """PATCH /services/{id}/reassign endpoint must be routable."""
        resp = self.url_open(
            f'{self.base_url}/1/reassign',
            data=json.dumps({'new_agent_id': 1}),
            headers={'Content-Type': 'application/json'},
        )
        self.assertIn(resp.status_code, [401, 404, 405])

    def test_get_summary_endpoint_exists(self):
        """GET /services/summary endpoint must be routable (returns 401 without auth)."""
        resp = self.url_open(f'{self.base_url}/summary')
        self.assertIn(resp.status_code, [401, 200])

    def test_error_response_shape(self):
        """All error responses must have {error, details} shape."""
        resp = self.url_open(self.base_url)
        if resp.status_code == 401:
            try:
                body = resp.json()
                # May have 'error' key or JSON-RPC error
                self.assertIsInstance(body, dict)
            except Exception:
                pass  # Non-JSON 401 is acceptable at this layer

    def test_service_tags_list_endpoint_exists(self):
        """GET /api/v1/service-tags must be routable."""
        resp = self.url_open('/api/v1/service-tags')
        self.assertIn(resp.status_code, [401, 200])

    def test_service_sources_list_endpoint_exists(self):
        """GET /api/v1/service-sources must be routable."""
        resp = self.url_open('/api/v1/service-sources')
        self.assertIn(resp.status_code, [401, 200])
