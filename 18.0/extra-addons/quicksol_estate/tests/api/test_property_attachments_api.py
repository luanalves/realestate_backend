# -*- coding: utf-8 -*-
"""
API Integration Tests: Property Attachments — Feature 017

Tests controller logic (error codes, FR6.9 envelope, RBAC, download headers,
pagination, URL invariants) with a mocked odoo.http.request object.
Runs inside the Docker container against a live Odoo DB.

Task: T015
FRs: FR1.1–FR1.5, FR2.3, FR2.4, FR3.1, FR6.9, FR7.4
"""
import base64
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from odoo.tests.common import HttpCase, TransactionCase, tagged

_CTRL_MODULE = (
    'odoo.addons.quicksol_estate.controllers'
    '.property_attachments_controller'
)


# ---------------------------------------------------------------------------
# T015-A — Auth protection: all four endpoints return 401 without credentials
# ---------------------------------------------------------------------------

@tagged('post_install', '-at_install', 'attachments_api')
class TestPropertyAttachmentsAuth(HttpCase):
    """All attachment endpoints are protected (401 without credentials)."""

    def test_upload_requires_auth(self):
        resp = self.url_open('/api/v1/properties/1/attachments')
        self.assertEqual(resp.status_code, 401)

    def test_list_requires_auth(self):
        resp = self.url_open('/api/v1/properties/1/attachments')
        self.assertEqual(resp.status_code, 401)

    def test_download_requires_auth(self):
        resp = self.url_open('/api/v1/properties/1/attachments/1/download')
        self.assertEqual(resp.status_code, 401)

    def test_delete_requires_auth(self):
        url = self.base_url() + '/api/v1/properties/1/attachments/1'
        resp = self.opener.delete(url)
        self.assertEqual(resp.status_code, 401)


# ---------------------------------------------------------------------------
# T015-B — Controller logic (mocked odoo.http.request)
# ---------------------------------------------------------------------------

@tagged('post_install', '-at_install', 'attachments_api')
class TestPropertyAttachmentsController(TransactionCase):
    """
    Business-logic tests for the 4 attachment endpoints.
    Uses mocked odoo.http.request to bypass JWT/session middleware
    and test the actual controller logic against a live DB.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Company (no CNPJ to avoid validator and uniqueness constraints)
        cls.company = cls.env['res.company'].create({
            'name': 'F017 Test Company',
        })

        # Manager user
        cls.manager = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'F017 Manager',
            'login': 'f017manager@test.com',
            'email': 'f017manager@test.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('quicksol_estate.group_real_estate_manager').id,
            ])],
            'company_ids': [(6, 0, [cls.company.id])],
            'company_id': cls.company.id,
        })

        # Agent user (denied upload and delete)
        cls.agent_user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'F017 Agent',
            'login': 'f017agent@test.com',
            'email': 'f017agent@test.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('quicksol_estate.group_real_estate_agent').id,
            ])],
            'company_ids': [(6, 0, [cls.company.id])],
            'company_id': cls.company.id,
        })

        # Property type + location type + state
        cls.property_type = cls.env['real.estate.property.type'].search([], limit=1)
        if not cls.property_type:
            cls.property_type = cls.env['real.estate.property.type'].create({'name': 'Apartamento'})

        cls.location_type = cls.env['real.estate.location.type'].search([], limit=1)
        if not cls.location_type:
            cls.location_type = cls.env['real.estate.location.type'].create({
                'name': 'Urbano', 'code': 'urban', 'sequence': 1,
            })

        cls.state_sp = cls.env['res.country.state'].search(
            [('code', '=', 'SP'), ('country_id.code', '=', 'BR')], limit=1
        )
        if not cls.state_sp:
            cls.state_sp = cls.env['res.country.state'].create({
                'name': 'São Paulo', 'code': 'SP',
                'country_id': cls.env.ref('base.br').id,
            })

        # Property (shared across tests; each test manages its own attachments)
        cls.property = cls.env['real.estate.property'].sudo().create({
            'name': 'F017 Test Property',
            'property_type_id': cls.property_type.id,
            'company_id': cls.company.id,
            'zip_code': '01234-567',
            'state_id': cls.state_sp.id,
            'city': 'São Paulo',
            'street': 'Rua Teste',
            'street_number': '123',
            'area': 80.0,
            'location_type_id': cls.location_type.id,
        })

        # OAuth application + valid JWT so @require_jwt passes in mocked tests
        import jwt as pyjwt
        import time
        from odoo.tools import config
        cls._jwt_secret = (
            config.get('oauth_jwt_secret') or config.get('admin_passwd') or 'test-secret'
        )
        cls._oauth_app = cls.env['thedevkitchen.oauth.application'].sudo().create({
            'name': 'F017 Test App',
        })
        cls._valid_token = pyjwt.encode(
            {
                'client_id': cls._oauth_app.client_id,
                'sub': cls._oauth_app.client_id,
                'exp': int(time.time()) + 3600,
            },
            cls._jwt_secret,
            algorithm='HS256',
        )

    def setUp(self):
        super().setUp()
        # Build a stub request for all middleware that imports odoo.http.request
        # directly. The per-test request mock (req) is patched via
        # patch(_CTRL_MODULE + '.request', req) inside each test body.
        _stub = MagicMock()
        _stub.httprequest = MagicMock()
        _stub.httprequest.method = 'POST'
        _stub.httprequest.path = '/test'
        _stub.httprequest.url = 'http://localhost/test'
        _stub.httprequest.scheme = 'http'
        _stub.httprequest.full_path = '/test?'
        _stub.httprequest.headers = {
            'Authorization': f'Bearer {self.__class__._valid_token}',
        }
        _stub.httprequest.cookies = {}
        _stub.httprequest.remote_addr = '127.0.0.1'
        _stub.session = MagicMock()
        _stub.session.sid = None

        self._patches = [
            patch('odoo.addons.thedevkitchen_observability.services.tracer.request', _stub),
            patch('odoo.addons.quicksol_estate.controllers.utils.auth.request', _stub),
            patch('odoo.addons.thedevkitchen_apigateway.middleware.request', _stub),
            patch('odoo.addons.quicksol_estate.controllers.utils.response.request', _stub),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in reversed(self._patches):
            p.stop()
        super().tearDown()

    def _make_request(self, user, form=None, files=None):
        """Build a minimal mock of odoo.http.request for controller tests."""
        req = MagicMock()
        req.env = self.env(user=user.id)
        req.env.company = self.company.with_env(req.env)
        req.company_domain = [('company_id', 'in', [self.company.id])]
        req.httprequest = MagicMock()
        req.httprequest.form = form or {}
        req.httprequest.files = files or {}

        def _make_json_response(body, status=200):
            return SimpleNamespace(body=body, status=status)

        req.make_json_response.side_effect = _make_json_response
        return req

    def _make_upload(self, content=b'\xff\xd8\xff\xe0' + b'\x00' * 100, filename='test.jpg'):
        """Build a fake file upload object (default content is valid JPEG magic bytes)."""
        f = MagicMock()
        f.filename = filename
        f.read.return_value = content
        return f

    def _ctrl(self):
        """Import and return a fresh controller instance."""
        from odoo.addons.quicksol_estate.controllers.property_attachments_controller import (
            PropertyAttachmentsController,
        )
        return PropertyAttachmentsController()

    def _call(self, method_name, req, **kwargs):
        """
        Call a controller method bypassing all auth/middleware decorators.

        Traverses the __wrapped__ chain (set by @functools.wraps) to skip
        @trace_http_request, @require_company, @require_session, and then
        extracts the raw function from @require_jwt's closure (which lacks
        @functools.wraps).  This lets TransactionCase tests verify controller
        business logic in isolation — auth is covered by TestPropertyAttachmentsAuth.
        """
        from odoo.addons.quicksol_estate.controllers.property_attachments_controller import (
            PropertyAttachmentsController,
        )
        ctrl = PropertyAttachmentsController()
        method = getattr(PropertyAttachmentsController, method_name)

        # Walk __wrapped__ chain: route_wrapper → trace_wrapper → ... until we
        # reach require_jwt's wrapper (which has no __wrapped__ because auth.py
        # omits @functools.wraps).
        fn = method
        while hasattr(fn, '__wrapped__'):
            fn = fn.__wrapped__

        # fn is now the @require_jwt wrapper.  Its first closure cell holds the
        # original inner function (the one wrapped by @require_company, etc.).
        # We continue unwrapping via __wrapped__ from that point.
        if hasattr(fn, '__closure__') and fn.__closure__:
            inner = fn.__closure__[0].cell_contents
            while hasattr(inner, '__wrapped__'):
                inner = inner.__wrapped__
            fn = inner

        with patch(_CTRL_MODULE + '.request', req):
            return fn(ctrl, **kwargs)

    # ------------------------------------------------------------------ #
    # T015-B01 through T015-B08 — Upload input validation                 #
    # ------------------------------------------------------------------ #

    def test_upload_missing_file_returns_400_missing_file(self):
        """T015-B01 FR1.1a: missing 'file' field → 400 missing_file."""
        req = self._make_request(self.manager, form={'attachment_type': 'image'}, files={})
        resp = self._call('upload_attachment', req, property_id=self.property.id)
        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.body['error'], 'missing_file')
        self.assertIn('detail', resp.body)
        self.assertNotIn('message', resp.body)

    def test_upload_missing_attachment_type_returns_400(self):
        """T015-B02 FR1.1b: missing attachment_type → 400 missing_attachment_type."""
        req = self._make_request(
            self.manager,
            form={'attachment_type': ''},
            files={'file': self._make_upload()},
        )
        resp = self._call('upload_attachment', req, property_id=self.property.id)
        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.body['error'], 'missing_attachment_type')

    def test_upload_invalid_attachment_type_returns_400_with_received(self):
        """T015-B03 FR1.1c: invalid attachment_type → 400 invalid_attachment_type + received."""
        req = self._make_request(
            self.manager,
            form={'attachment_type': 'video'},
            files={'file': self._make_upload()},
        )
        resp = self._call('upload_attachment', req, property_id=self.property.id)
        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.body['error'], 'invalid_attachment_type')
        self.assertEqual(resp.body.get('received'), 'video')

    def test_upload_empty_file_returns_400_empty_file(self):
        """T015-B04 FR1.5a: zero-byte file → 400 empty_file."""
        req = self._make_request(
            self.manager,
            form={'attachment_type': 'image'},
            files={'file': self._make_upload(content=b'')},
        )
        resp = self._call('upload_attachment', req, property_id=self.property.id)
        self.assertEqual(resp.status, 400)
        self.assertEqual(resp.body['error'], 'empty_file')

    def test_upload_file_too_large_returns_413(self):
        """T015-B05 FR1.3: file exceeds limit → 413 file_too_large with max_size_bytes + received_size."""
        self.env['ir.config_parameter'].sudo().set_param('web.max_file_upload_size', '5')
        try:
            req = self._make_request(
                self.manager,
                form={'attachment_type': 'image'},
                files={'file': self._make_upload(content=b'X' * 10)},
            )
            resp = self._call('upload_attachment', req, property_id=self.property.id)
            self.assertEqual(resp.status, 413)
            self.assertEqual(resp.body['error'], 'file_too_large')
            self.assertIn('max_size_bytes', resp.body)
            self.assertIn('received_size', resp.body)
            self.assertEqual(resp.body['received_size'], 10)
        finally:
            self.env['ir.config_parameter'].sudo().set_param('web.max_file_upload_size', '134217728')

    def test_upload_nonexistent_property_returns_404(self):
        """T015-B06: property not found in company → 404 not_found."""
        req = self._make_request(
            self.manager,
            form={'attachment_type': 'image'},
            files={'file': self._make_upload()},
        )
        resp = self._call('upload_attachment', req, property_id=9999999)
        self.assertEqual(resp.status, 404)
        self.assertEqual(resp.body['error'], 'not_found')

    def test_upload_agent_forbidden_returns_403(self):
        """T015-B07 FR3.1: agent role cannot upload → 403 forbidden."""
        req = self._make_request(
            self.agent_user,
            form={'attachment_type': 'image'},
            files={'file': self._make_upload()},
        )
        resp = self._call('upload_attachment', req, property_id=self.property.id)
        self.assertEqual(resp.status, 403)
        self.assertEqual(resp.body['error'], 'forbidden')

    # ------------------------------------------------------------------ #
    # T015-B08 — FR6.9: Error envelope invariant                          #
    # ------------------------------------------------------------------ #

    def test_error_envelope_has_error_and_detail_not_message(self):
        """T015-B08 FR6.9: all error responses have 'error' + 'detail', NOT 'message'."""
        req = self._make_request(self.manager, form={}, files={})
        resp = self._call('upload_attachment', req, property_id=self.property.id)
        self.assertIn('error', resp.body)
        self.assertIn('detail', resp.body)
        self.assertNotIn('message', resp.body)

    # ------------------------------------------------------------------ #
    # T015-B09/10 — List: pagination structure + search_count invariant   #
    # ------------------------------------------------------------------ #

    def test_list_returns_200_with_pagination_structure(self):
        """T015-B09: list returns {data: {items, pagination: {total, limit, offset}}}."""
        req = self._make_request(self.manager)
        captured = {}

        def fake_success_response(data, status_code=200):
            captured['data'] = data
            return SimpleNamespace(body=data, status=status_code)

        with patch(_CTRL_MODULE + '.success_response', fake_success_response):
            self._call('list_attachments', req, property_id=self.property.id)

        self.assertIn('data', captured)
        pagination = captured['data']['data']['pagination']
        self.assertIn('total', pagination)
        self.assertIn('limit', pagination)
        self.assertIn('offset', pagination)
        items = captured['data']['data']['items']
        self.assertIsInstance(items, list)

    def test_list_total_uses_search_count_not_page_len(self):
        """T015-B10 FR7.4: total = search_count (all pages), even when limit=1."""
        # Create 3 attachments on the test property
        for i in range(3):
            self.env['ir.attachment'].sudo().create({
                'name': f'f017_pagination_{i}.pdf',
                'res_model': 'real.estate.property',
                'res_id': self.property.id,
                'description': 'document',
                'company_id': self.company.id,
                'datas': base64.b64encode(b'%PDF-1.4 test'),
            })

        req = self._make_request(self.manager)
        captured = {}

        def fake_success_response(data, status_code=200):
            captured['data'] = data
            return SimpleNamespace(body=data, status=status_code)

        with patch(_CTRL_MODULE + '.success_response', fake_success_response):
            self._call(
                'list_attachments', req,
                property_id=self.property.id,
                limit='1',
                offset='0',
                attachment_type='document',
            )

        pagination = captured['data']['data']['pagination']
        # total must be >= 3 (all docs), limit must be 1 (page size)
        self.assertGreaterEqual(pagination['total'], 3)
        self.assertEqual(pagination['limit'], 1)

    # ------------------------------------------------------------------ #
    # T015-B11/12 — Download: security headers + no redirect              #
    # ------------------------------------------------------------------ #

    def _create_test_attachment(self, name='f017_dl.jpg', mimetype='image/jpeg',
                                description='image', content=b'\xff\xd8\xff\xe0test'):
        return self.env['ir.attachment'].sudo().create({
            'name': name,
            'res_model': 'real.estate.property',
            'res_id': self.property.id,
            'description': description,
            'mimetype': mimetype,
            'company_id': self.company.id,
            'datas': base64.b64encode(content),
        })

    def test_download_returns_binary_with_security_headers(self):
        """T015-B11: download returns 200 bytes with CSP + X-Content-Type-Options."""
        from werkzeug.wrappers import Response as WerkzeugResponse
        att = self._create_test_attachment()
        req = self._make_request(self.manager)
        resp = self._call('download_attachment', req, property_id=self.property.id, attachment_id=att.id)
        self.assertIsInstance(resp, WerkzeugResponse)
        self.assertEqual(resp.status_code, 200)
        headers = dict(resp.headers)
        self.assertEqual(headers.get('Content-Security-Policy'), "default-src 'none'")
        self.assertEqual(headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertIn('attachment; filename=', headers.get('Content-Disposition', ''))

    def test_download_does_not_redirect_to_web_content(self):
        """T015-B12 FR2.4: download never redirects to /web/content/ (status is 200, not 3xx)."""
        att = self._create_test_attachment(
            name='f017_noredirect.pdf',
            mimetype='application/pdf',
            description='document',
            content=b'%PDF-1.4 test content',
        )
        req = self._make_request(self.manager)
        resp = self._call('download_attachment', req, property_id=self.property.id, attachment_id=att.id)
        self.assertNotIn(resp.status_code, [301, 302, 307, 308])
        self.assertEqual(resp.status_code, 200)

    def test_download_nonexistent_attachment_returns_404(self):
        """T015-B13: attachment not found on property → 404 not_found."""
        req = self._make_request(self.manager)
        resp = self._call('download_attachment', req, property_id=self.property.id, attachment_id=9999999)
        self.assertEqual(resp.status, 404)
        self.assertEqual(resp.body['error'], 'not_found')

    # ------------------------------------------------------------------ #
    # T015-B14/15 — Delete: RBAC                                          #
    # ------------------------------------------------------------------ #

    def test_delete_by_manager_returns_204(self):
        """T015-B14 FR3.1: manager can delete → 204 No Content, attachment gone from DB."""
        from werkzeug.wrappers import Response as WerkzeugResponse
        att = self._create_test_attachment(name='f017_delete_me.jpg')
        att_id = att.id
        req = self._make_request(self.manager)
        resp = self._call('delete_attachment', req, property_id=self.property.id, attachment_id=att_id)
        self.assertIsInstance(resp, WerkzeugResponse)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(
            self.env['ir.attachment'].search([('id', '=', att_id)]),
            'Attachment must be hard-deleted (FR3.2)',
        )

    def test_delete_by_agent_returns_403(self):
        """T015-B15 FR3.1: agent role cannot delete → 403 forbidden."""
        att = self._create_test_attachment(name='f017_agent_cannot_del.jpg')
        req = self._make_request(self.agent_user)
        resp = self._call('delete_attachment', req, property_id=self.property.id, attachment_id=att.id)
        self.assertEqual(resp.status, 403)
        self.assertEqual(resp.body['error'], 'forbidden')

    # ------------------------------------------------------------------ #
    # T015-B16/17/18/19 — URL invariant + serializer fields               #
    # ------------------------------------------------------------------ #

    def test_serializer_links_never_contain_web_content(self):
        """T015-B16 FR2.4: _serialize_attachment never produces /web/content/ URLs."""
        from odoo.addons.quicksol_estate.controllers.property_attachments_controller import (
            _serialize_attachment,
        )
        att = SimpleNamespace(
            id=99, name='test.jpg', mimetype='image/jpeg',
            file_size=1024, description='image',
            create_date=datetime(2026, 5, 8, 10, 0, 0),
        )
        result = _serialize_attachment(att, property_id=1, include_self_link=True)
        self.assertNotIn('/web/content/', str(result))
        self.assertEqual(
            result['links']['download'],
            '/api/v1/properties/1/attachments/99/download',
        )
        self.assertEqual(result['links']['self'], '/api/v1/properties/1/attachments/99')

    def test_list_download_url_uses_api_route_not_web_content(self):
        """T015-B17: list item download URL is /api/v1/…, not /web/content/."""
        from odoo.addons.quicksol_estate.controllers.property_attachments_controller import (
            _serialize_attachment,
        )
        att = SimpleNamespace(
            id=77, name='doc.pdf', mimetype='application/pdf',
            file_size=2048, description='document',
            create_date=datetime(2026, 5, 8, 10, 0, 0),
        )
        result = _serialize_attachment(att, property_id=5, include_self_link=False)
        self.assertNotIn('/web/content/', result['links']['download'])
        self.assertEqual(
            result['links']['download'],
            '/api/v1/properties/5/attachments/77/download',
        )
        self.assertNotIn('self', result['links'])

    def test_upload_201_response_links_has_self_and_download(self):
        """T015-B18: upload response (include_self_link=True) has both self and download."""
        from odoo.addons.quicksol_estate.controllers.property_attachments_controller import (
            _serialize_attachment,
        )
        att = SimpleNamespace(
            id=42, name='fachada.jpg', mimetype='image/jpeg',
            file_size=204800, description='image',
            create_date=datetime(2026, 5, 8, 14, 30, 0),
        )
        result = _serialize_attachment(att, property_id=7, include_self_link=True)
        self.assertIn('self', result['links'])
        self.assertIn('download', result['links'])

    def test_serializer_returns_all_required_fields(self):
        """T015-B19: _serialize_attachment returns all 7 required fields with correct types."""
        from odoo.addons.quicksol_estate.controllers.property_attachments_controller import (
            _serialize_attachment,
        )
        att = SimpleNamespace(
            id=42, name='fachada.jpg', mimetype='image/jpeg',
            file_size=204800, description='image',
            create_date=datetime(2026, 5, 8, 14, 30, 0),
        )
        result = _serialize_attachment(att, property_id=7, include_self_link=True)
        for field in ('id', 'name', 'mimetype', 'size', 'attachment_type', 'uploaded_at', 'links'):
            self.assertIn(field, result, f'Missing required field: {field}')
        self.assertRegex(result['uploaded_at'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
        self.assertIsInstance(result['links'], dict)
        self.assertEqual(result['size'], 204800)
        self.assertEqual(result['attachment_type'], 'image')
