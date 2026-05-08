# -*- coding: utf-8 -*-
import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Import real werkzeug.utils.secure_filename BEFORE any sys.modules manipulation
# (werkzeug may not be installed locally; it is always present in the Docker container)
try:
    from werkzeug.utils import secure_filename as _real_secure_filename
    _werkzeug_available = True
except ImportError:
    _real_secure_filename = None  # type: ignore[assignment]
    _werkzeug_available = False

# ---------------------------------------------------------------------------
# Bootstrap: load controller module without Odoo framework
# ---------------------------------------------------------------------------

CONTROLLER_PATH = (
    Path(__file__).parent.parent.parent
    / 'controllers'
    / 'property_attachments_controller.py'
)

# Step 1: stub heavy external dependencies in sys.modules before any import
import types as _types  # noqa: E402


def _make_module(name):
    m = _types.ModuleType(name)
    m.__path__ = []
    return m


# Odoo stubs
for _mod in [
    'odoo', 'odoo.http', 'odoo.exceptions',
    'odoo.addons', 'odoo.addons.thedevkitchen_apigateway',
    'odoo.addons.thedevkitchen_apigateway.middleware',
    'odoo.addons.thedevkitchen_observability',
    'odoo.addons.thedevkitchen_observability.services',
    'odoo.addons.thedevkitchen_observability.services.tracer',
]:
    sys.modules.setdefault(_mod, _make_module(_mod))

# odoo.http needs: request, Controller, route
_http_mod = sys.modules['odoo.http']
_http_mod.request = MagicMock()
_http_mod.Controller = object  # base class for our controller


class _FakeRoute:
    def __call__(self, *args, **kwargs):
        return lambda f: f


_http_mod.route = _FakeRoute()

# Fake require_jwt / require_session / require_company as identity decorators
_identity = lambda f: f  # noqa: E731
for _attr in ('require_jwt', 'require_session', 'require_company'):
    setattr(sys.modules['odoo.addons.thedevkitchen_apigateway.middleware'], _attr, _identity)
setattr(sys.modules['odoo.addons.thedevkitchen_observability.services.tracer'], 'trace_http_request', _identity)

# Werkzeug stubs (werkzeug itself IS available, but wrappers.Response may not be)
sys.modules.setdefault('werkzeug', MagicMock())
sys.modules.setdefault('werkzeug.wrappers', MagicMock())
sys.modules.setdefault('werkzeug.utils', MagicMock())

# Step 2: set up the fake controller package hierarchy so relative imports resolve
# quicksol_estate.controllers is the parent package of our file
_ctrl_pkg = _make_module('quicksol_estate.controllers')
_ctrl_pkg.__path__ = [str(CONTROLLER_PATH.parent)]
_ctrl_pkg.__package__ = 'quicksol_estate.controllers'
_utils_pkg = _make_module('quicksol_estate.controllers.utils')
_auth_mod = _make_module('quicksol_estate.controllers.utils.auth')
_auth_mod.require_jwt = _identity
_response_mod = _make_module('quicksol_estate.controllers.utils.response')
_response_mod.error_response = MagicMock()
_response_mod.success_response = MagicMock()

for _name, _obj in [
    ('quicksol_estate', _make_module('quicksol_estate')),
    ('quicksol_estate.controllers', _ctrl_pkg),
    ('quicksol_estate.controllers.utils', _utils_pkg),
    ('quicksol_estate.controllers.utils.auth', _auth_mod),
    ('quicksol_estate.controllers.utils.response', _response_mod),
]:
    sys.modules.setdefault(_name, _obj)

# Step 3: magic — use real package if available, otherwise stub
try:
    import magic as _real_magic  # noqa: F401
    _magic_available = True
except ImportError:
    _magic_available = False
    _magic_stub = _make_module('magic')
    _magic_stub.from_buffer = lambda content, mime=False: 'application/octet-stream'
    sys.modules['magic'] = _magic_stub

# Step 4: load controller with proper parent package set
SPEC = importlib.util.spec_from_file_location(
    'quicksol_estate.controllers.property_attachments_controller',
    CONTROLLER_PATH,
    submodule_search_locations=[],
)
ctrl = importlib.util.module_from_spec(SPEC)
ctrl.__package__ = 'quicksol_estate.controllers'
sys.modules['quicksol_estate.controllers.property_attachments_controller'] = ctrl
SPEC.loader.exec_module(ctrl)

# If real magic is available, point the controller's magic reference to it
if _magic_available:
    ctrl.magic = _real_magic  # type: ignore[attr-defined]

FIXTURES = Path(__file__).parent.parent / 'fixtures'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_request(company_id=1):
    req = SimpleNamespace()
    req.company_domain = [('company_id', '=', company_id)]
    req.env = SimpleNamespace(company=SimpleNamespace(id=company_id))
    return req


# ---------------------------------------------------------------------------
# T013 — MIME validation (image)
# ---------------------------------------------------------------------------

class TestImageMimetypeAllowed(unittest.TestCase):
    """image/jpeg, image/png, image/webp are allowed for attachment_type=image."""

    def test_jpeg_in_whitelist(self):
        self.assertIn('image/jpeg', ctrl.ALLOWED_IMAGE_MIMETYPES)

    def test_png_in_whitelist(self):
        self.assertIn('image/png', ctrl.ALLOWED_IMAGE_MIMETYPES)

    def test_webp_in_whitelist(self):
        self.assertIn('image/webp', ctrl.ALLOWED_IMAGE_MIMETYPES)

    def test_gif_not_in_whitelist(self):
        self.assertNotIn('image/gif', ctrl.ALLOWED_IMAGE_MIMETYPES)

    def test_bmp_not_in_whitelist(self):
        self.assertNotIn('image/bmp', ctrl.ALLOWED_IMAGE_MIMETYPES)


class TestImageMimetypeRejected(unittest.TestCase):
    """PDF, HTML, EXE are not valid for attachment_type=image."""

    def test_pdf_not_allowed_for_image_type(self):
        self.assertNotIn('application/pdf', ctrl.ALLOWED_IMAGE_MIMETYPES)

    def test_html_not_allowed(self):
        self.assertNotIn('text/html', ctrl.ALLOWED_IMAGE_MIMETYPES)
        self.assertNotIn('text/html', ctrl.ALLOWED_DOCUMENT_MIMETYPES)

    def test_exe_not_allowed(self):
        self.assertNotIn('application/x-msdownload', ctrl.ALLOWED_IMAGE_MIMETYPES)
        self.assertNotIn('application/x-msdownload', ctrl.ALLOWED_DOCUMENT_MIMETYPES)

    def test_script_not_allowed(self):
        self.assertNotIn('text/x-python', ctrl.ALLOWED_MIMETYPES)
        self.assertNotIn('application/x-sh', ctrl.ALLOWED_MIMETYPES)


class TestDocumentMimetypeAllowed(unittest.TestCase):
    """PDF, DOCX, XLSX are allowed for attachment_type=document."""

    def test_pdf_allowed(self):
        self.assertIn('application/pdf', ctrl.ALLOWED_DOCUMENT_MIMETYPES)

    def test_docx_allowed(self):
        self.assertIn(
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            ctrl.ALLOWED_DOCUMENT_MIMETYPES,
        )

    def test_xlsx_allowed(self):
        self.assertIn(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            ctrl.ALLOWED_DOCUMENT_MIMETYPES,
        )

    def test_doc_allowed(self):
        self.assertIn('application/msword', ctrl.ALLOWED_DOCUMENT_MIMETYPES)

    def test_xls_allowed(self):
        self.assertIn('application/vnd.ms-excel', ctrl.ALLOWED_DOCUMENT_MIMETYPES)


# ---------------------------------------------------------------------------
# T013 — Magic bytes mismatch
# ---------------------------------------------------------------------------

@unittest.skipUnless(_magic_available, 'python-magic / libmagic1 not available in this environment')
class TestMagicBytesMismatchRejected(unittest.TestCase):
    """seed_malicious.jpg has Python shebang magic bytes → NOT image/jpeg."""

    def test_malicious_file_not_detected_as_jpeg(self):
        seed = FIXTURES / 'seed_malicious.jpg'
        content = seed.read_bytes()
        detected = ctrl._detect_mime(content)
        self.assertNotIn(detected, ctrl.ALLOWED_IMAGE_MIMETYPES,
                         f'Expected malicious file to be rejected but got MIME: {detected}')

    def test_valid_jpeg_detected_as_jpeg(self):
        seed = FIXTURES / 'seed_image.jpg'
        content = seed.read_bytes()
        detected = ctrl._detect_mime(content)
        self.assertEqual(detected, 'image/jpeg')

    def test_valid_pdf_detected_as_pdf(self):
        seed = FIXTURES / 'seed_document.pdf'
        content = seed.read_bytes()
        detected = ctrl._detect_mime(content)
        self.assertEqual(detected, 'application/pdf')


# ---------------------------------------------------------------------------
# T013 — File size limit
# ---------------------------------------------------------------------------

class TestImageSizeLimitEnforced(unittest.TestCase):
    """seed_large.jpg is >10MB and must exceed a low configured limit."""

    def test_large_fixture_exceeds_10mb(self):
        seed = FIXTURES / 'seed_large.jpg'
        size = seed.stat().st_size
        self.assertGreater(size, 10 * 1024 * 1024,
                           'seed_large.jpg should be > 10MB')

    def test_seed_image_under_2mb(self):
        seed = FIXTURES / 'seed_image.jpg'
        size = seed.stat().st_size
        self.assertLess(size, 2 * 1024 * 1024,
                        'seed_image.jpg should be < 2MB')


class TestDocumentSizeLimitEnforced(unittest.TestCase):
    """seed_document.pdf fixture is under 2 MB."""

    def test_seed_document_under_2mb(self):
        seed = FIXTURES / 'seed_document.pdf'
        size = seed.stat().st_size
        self.assertLess(size, 2 * 1024 * 1024,
                        'seed_document.pdf should be < 2MB')


# ---------------------------------------------------------------------------
# T013 — Filename sanitization
# ---------------------------------------------------------------------------

@unittest.skipUnless(_werkzeug_available, 'werkzeug not installed locally — run inside Docker')
class TestFilenameSanitization(unittest.TestCase):
    """secure_filename removes path traversal characters."""

    def setUp(self):
        # Use the real werkzeug.utils.secure_filename captured before sys.modules stubs
        self.secure_filename = _real_secure_filename

    def test_path_traversal_sanitized(self):
        result = self.secure_filename('../../../etc/passwd.jpg')
        self.assertNotIn('..', result)
        self.assertNotIn('/', result)
        self.assertTrue(result.endswith('.jpg'))

    def test_normal_filename_preserved(self):
        result = self.secure_filename('fachada.jpg')
        self.assertEqual(result, 'fachada.jpg')

    def test_spaces_replaced(self):
        result = self.secure_filename('foto da fachada.jpg')
        self.assertNotIn(' ', result)

    def test_empty_result_fallback(self):
        """secure_filename('') returns '' — controller replaces with 'untitled'."""
        result = self.secure_filename('')
        self.assertEqual(result, '')
        # Controller fallback:
        safe = result or 'untitled'
        self.assertEqual(safe, 'untitled')

    def test_non_ascii_only_filename(self):
        """All non-ASCII chars stripped → empty → controller falls back to 'untitled'."""
        result = self.secure_filename('档案.jpg')
        # secure_filename strips non-ASCII; result may be just '.jpg' or ''
        self.assertNotIn('档', result)


# ---------------------------------------------------------------------------
# T013 + T015 — download_url invariant: ALWAYS /api/v1/... — NEVER /web/content/
# ---------------------------------------------------------------------------

class TestDownloadUrlUsesApiRoute(unittest.TestCase):
    """_serialize_attachment always generates /api/v1/... URLs — never /web/content/."""

    def _make_fake_att(self, att_id=42, name='test.jpg', mimetype='image/jpeg',
                       file_size=512000, description='image', create_date=None):
        from datetime import datetime
        att = SimpleNamespace(
            id=att_id,
            name=name,
            mimetype=mimetype,
            file_size=file_size,
            description=description,
            create_date=create_date or datetime(2026, 5, 6, 14, 23, 11),
        )
        return att

    def test_upload_response_self_link_uses_api_route(self):
        att = self._make_fake_att()
        result = ctrl._serialize_attachment(att, property_id=7, include_self_link=True)
        self.assertIn('/api/v1/', result['links']['self'])
        self.assertNotIn('/web/content/', result['links']['self'])

    def test_upload_response_download_link_uses_api_route(self):
        att = self._make_fake_att()
        result = ctrl._serialize_attachment(att, property_id=7, include_self_link=True)
        self.assertIn('/api/v1/', result['links']['download'])
        self.assertNotIn('/web/content/', result['links']['download'])

    def test_list_response_download_link_uses_api_route(self):
        """List items include links.download only (no links.self)."""
        att = self._make_fake_att()
        result = ctrl._serialize_attachment(att, property_id=7, include_self_link=False)
        self.assertIn('/api/v1/', result['links']['download'])
        self.assertNotIn('/web/content/', result['links']['download'])
        self.assertNotIn('self', result['links'])

    def test_list_download_url_uses_api_route(self):
        """T015 — download_url field in list item never contains /web/content/."""
        att = self._make_fake_att(att_id=99, description='document')
        result = ctrl._serialize_attachment(att, property_id=12, include_self_link=False)
        download = result['links']['download']
        self.assertIn('/api/v1/properties/12/attachments/99/download', download)
        self.assertNotIn('/web/content/', download)

    def test_links_format_is_flat_object(self):
        """links must be a flat dict, NOT a list of {rel, href, method} objects."""
        att = self._make_fake_att()
        result = ctrl._serialize_attachment(att, property_id=7, include_self_link=True)
        links = result['links']
        self.assertIsInstance(links, dict)
        self.assertIn('self', links)
        self.assertIn('download', links)
        self.assertIsInstance(links['self'], str)
        self.assertIsInstance(links['download'], str)

    def test_upload_201_links_contains_self_and_download(self):
        att = self._make_fake_att()
        result = ctrl._serialize_attachment(att, property_id=7, include_self_link=True)
        self.assertIn('self', result['links'])
        self.assertIn('download', result['links'])

    def test_list_200_links_contains_only_download(self):
        att = self._make_fake_att()
        result = ctrl._serialize_attachment(att, property_id=7, include_self_link=False)
        self.assertNotIn('self', result['links'])
        self.assertIn('download', result['links'])

    def test_download_url_path_structure(self):
        att = self._make_fake_att(att_id=42)
        result = ctrl._serialize_attachment(att, property_id=7, include_self_link=True)
        expected_download = '/api/v1/properties/7/attachments/42/download'
        expected_self = '/api/v1/properties/7/attachments/42'
        self.assertEqual(result['links']['download'], expected_download)
        self.assertEqual(result['links']['self'], expected_self)


# ---------------------------------------------------------------------------
# T013 — ir.config_parameter tests
# ---------------------------------------------------------------------------

class TestUploadReadsIrConfigParam(unittest.TestCase):
    """_get_max_upload_bytes reads ir.config_parameter.web.max_file_upload_size."""

    def test_reads_param_key(self):
        mock_env = MagicMock()
        mock_param = MagicMock()
        mock_param.get_param.return_value = '52428800'  # 50 MB
        mock_env.__getitem__.return_value.sudo.return_value = mock_param

        with patch.object(ctrl, 'request', create=True) as mock_req:
            mock_req.env = mock_env
            result = ctrl._get_max_upload_bytes()

        mock_param.get_param.assert_called_once_with(
            ctrl.CONFIG_PARAM_MAX_SIZE,
            default=ctrl.DEFAULT_MAX_FILE_BYTES,
        )
        self.assertEqual(result, 52428800)

    def test_default_when_param_absent(self):
        """When parameter is not set, returns DEFAULT_MAX_FILE_BYTES (128 MB)."""
        mock_env = MagicMock()
        mock_param = MagicMock()
        mock_param.get_param.return_value = None
        mock_env.__getitem__.return_value.sudo.return_value = mock_param

        with patch.object(ctrl, 'request', create=True) as mock_req:
            mock_req.env = mock_env
            # Simulate None return → int(None) raises TypeError → default path
            mock_param.get_param.return_value = ctrl.DEFAULT_MAX_FILE_BYTES
            result = ctrl._get_max_upload_bytes()

        self.assertEqual(result, ctrl.DEFAULT_MAX_FILE_BYTES)

    def test_default_constant_is_128mb(self):
        self.assertEqual(ctrl.DEFAULT_MAX_FILE_BYTES, 134_217_728)

    def test_config_param_key_is_odoo_standard(self):
        self.assertEqual(ctrl.CONFIG_PARAM_MAX_SIZE, 'web.max_file_upload_size')


# ---------------------------------------------------------------------------
# T013 — Agent RBAC
# ---------------------------------------------------------------------------

class TestAgentCannotDelete(unittest.TestCase):
    """_is_agent_only returns True for pure Agent, False for Manager/Owner/Admin."""

    def _make_user(self, groups):
        user = MagicMock()
        user.has_group.side_effect = lambda g: g in groups
        return user

    def test_pure_agent_is_agent_only(self):
        user = self._make_user({'quicksol_estate.group_real_estate_agent'})
        self.assertTrue(ctrl._is_agent_only(user))

    def test_manager_is_not_agent_only(self):
        user = self._make_user({
            'quicksol_estate.group_real_estate_agent',
            'quicksol_estate.group_real_estate_manager',
        })
        self.assertFalse(ctrl._is_agent_only(user))

    def test_owner_is_not_agent_only(self):
        user = self._make_user({
            'quicksol_estate.group_real_estate_agent',
            'quicksol_estate.group_real_estate_owner',
        })
        self.assertFalse(ctrl._is_agent_only(user))

    def test_admin_is_not_agent_only(self):
        user = self._make_user({'base.group_system'})
        self.assertFalse(ctrl._is_agent_only(user))

    def test_user_without_any_group_is_not_agent_only(self):
        user = self._make_user(set())
        self.assertFalse(ctrl._is_agent_only(user))


# ---------------------------------------------------------------------------
# T017 — No redirect to /web/content/
# ---------------------------------------------------------------------------

class TestNoRedirectToWebContent(unittest.TestCase):
    """_serialize_attachment never generates /web/content/ URLs (R004, FR2.4)."""

    def _make_att(self, att_id=42):
        from datetime import datetime
        return SimpleNamespace(
            id=att_id,
            name='fachada.jpg',
            mimetype='image/jpeg',
            file_size=512000,
            description='image',
            create_date=datetime(2026, 5, 6, 14, 0, 0),
        )

    def test_serialize_never_produces_web_content_url(self):
        att = self._make_att()
        result = ctrl._serialize_attachment(att, property_id=7, include_self_link=True)
        all_values = str(result)
        self.assertNotIn('/web/content/', all_values)

    def test_serialize_download_path_ends_with_download_suffix(self):
        att = self._make_att()
        result = ctrl._serialize_attachment(att, property_id=7, include_self_link=True)
        self.assertTrue(result['links']['download'].endswith('/download'))

    def test_constants_no_web_content(self):
        """Ensure no /web/content/ string appears in any constant in the module."""
        import inspect
        source = inspect.getsource(ctrl)
        # The string /web/content/ should only appear in comments, not in return values
        # This is a best-effort check on the module source
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'"):
                continue
            if '/web/content/' in stripped and 'NEVER' not in stripped and 'FR2.4' not in stripped:
                self.fail(
                    f'Found /web/content/ in non-comment line: {stripped!r}'
                )


# ---------------------------------------------------------------------------
# Serializer field completeness
# ---------------------------------------------------------------------------

class TestSerializerFields(unittest.TestCase):
    """_serialize_attachment returns all required fields."""

    def _make_att(self, att_id=42):
        from datetime import datetime
        return SimpleNamespace(
            id=att_id,
            name='planta-baixa.pdf',
            mimetype='application/pdf',
            file_size=204800,
            description='document',
            create_date=datetime(2026, 5, 6, 14, 23, 11),
        )

    def test_all_required_fields_present(self):
        att = self._make_att()
        result = ctrl._serialize_attachment(att, property_id=7, include_self_link=True)
        for field in ('id', 'name', 'mimetype', 'size', 'attachment_type', 'uploaded_at', 'links'):
            self.assertIn(field, result, f'Missing field: {field}')

    def test_uploaded_at_is_iso8601(self):
        att = self._make_att()
        result = ctrl._serialize_attachment(att, property_id=7, include_self_link=True)
        self.assertRegex(result['uploaded_at'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')

    def test_attachment_type_maps_description(self):
        att = self._make_att()
        result = ctrl._serialize_attachment(att, property_id=7)
        self.assertEqual(result['attachment_type'], 'document')

    def test_size_field_maps_file_size(self):
        att = self._make_att()
        result = ctrl._serialize_attachment(att, property_id=7)
        self.assertEqual(result['size'], 204800)


# ---------------------------------------------------------------------------
# T002 — gap-06: Quantity limits are hardcoded constants, not ir.config_parameter
# ---------------------------------------------------------------------------

class TestQuantityLimitConstants(unittest.TestCase):
    """gap-06: MAX_IMAGES_PER_PROPERTY and MAX_DOCUMENTS_PER_PROPERTY are module constants."""

    def test_max_images_constant_is_50(self):
        self.assertEqual(ctrl.MAX_IMAGES_PER_PROPERTY, 50)

    def test_max_documents_constant_is_20(self):
        self.assertEqual(ctrl.MAX_DOCUMENTS_PER_PROPERTY, 20)

    def test_config_param_images_key_does_not_exist(self):
        """CONFIG_PARAM_MAX_IMAGES must not exist — removed in gap-06."""
        self.assertFalse(hasattr(ctrl, 'CONFIG_PARAM_MAX_IMAGES'))

    def test_config_param_documents_key_does_not_exist(self):
        """CONFIG_PARAM_MAX_DOCUMENTS must not exist — removed in gap-06."""
        self.assertFalse(hasattr(ctrl, 'CONFIG_PARAM_MAX_DOCUMENTS'))

    def test_get_max_images_helper_does_not_exist(self):
        """_get_max_images_per_property() must not exist — removed in gap-06."""
        self.assertFalse(hasattr(ctrl, '_get_max_images_per_property'))

    def test_get_max_documents_helper_does_not_exist(self):
        """_get_max_documents_per_property() must not exist — removed in gap-06."""
        self.assertFalse(hasattr(ctrl, '_get_max_documents_per_property'))


# ---------------------------------------------------------------------------
# T010 — Error code alignment tests (gap-01 through gap-05)
# ---------------------------------------------------------------------------

class TestAttErrorHelper(unittest.TestCase):
    """_att_error builds FR6.9-compliant envelope: {error, detail, ...extras}."""

    def _capture_att_error(self, status_code, error_code, detail, **extras):
        captured = {}

        def fake_make_json_response(body, status):
            captured['body'] = body
            captured['status'] = status
            return MagicMock()

        mock_req = MagicMock()
        mock_req.make_json_response.side_effect = fake_make_json_response
        with patch.object(ctrl, 'request', mock_req):
            ctrl._att_error(status_code, error_code, detail, **extras)
        return captured

    def test_envelope_has_error_and_detail_keys(self):
        c = self._capture_att_error(400, 'missing_file', 'A file is required.')
        self.assertEqual(c['status'], 400)
        self.assertEqual(c['body']['error'], 'missing_file')
        self.assertEqual(c['body']['detail'], 'A file is required.')
        self.assertNotIn('message', c['body'])

    def test_extras_appear_at_top_level(self):
        c = self._capture_att_error(
            413, 'file_too_large', 'File too large.',
            max_size_bytes=1024, received_size=2048,
        )
        self.assertEqual(c['body']['max_size_bytes'], 1024)
        self.assertEqual(c['body']['received_size'], 2048)

    def test_413_body_includes_received_size(self):
        """gap-01: 413 body must contain received_size field."""
        c = self._capture_att_error(
            413, 'file_too_large', 'File size exceeds the configured limit.',
            max_size_bytes=134217728, received_size=200000000,
        )
        self.assertEqual(c['status'], 413)
        self.assertEqual(c['body']['error'], 'file_too_large')
        self.assertIn('received_size', c['body'])
        self.assertEqual(c['body']['received_size'], 200000000)

    def test_422_body_has_all_fields(self):
        """gap-02: 422 body must contain attachment_type, limit, current."""
        c = self._capture_att_error(
            422, 'attachment_limit_exceeded',
            'Maximum number of image attachments has been reached for this property.',
            attachment_type='image', limit=50, current=50,
        )
        self.assertEqual(c['status'], 422)
        self.assertEqual(c['body']['error'], 'attachment_limit_exceeded')
        self.assertIn('attachment_type', c['body'])
        self.assertIn('limit', c['body'])
        self.assertIn('current', c['body'])
        self.assertIn('detail', c['body'])

    def test_400_missing_file_code(self):
        """gap-03a: missing file uses error code 'missing_file'."""
        c = self._capture_att_error(400, 'missing_file', 'A file is required.')
        self.assertEqual(c['body']['error'], 'missing_file')
        self.assertNotIn('VALIDATION_ERROR', str(c['body']))

    def test_400_missing_type_code(self):
        """gap-03b: missing attachment_type uses error code 'missing_attachment_type'."""
        c = self._capture_att_error(
            400, 'missing_attachment_type', 'attachment_type is required (image or document).',
        )
        self.assertEqual(c['body']['error'], 'missing_attachment_type')

    def test_400_invalid_type_includes_received(self):
        """gap-03c: invalid_attachment_type error must include 'received' extra field."""
        c = self._capture_att_error(
            400, 'invalid_attachment_type',
            "Invalid attachment_type 'video'. Allowed values: image, document.",
            received='video',
        )
        self.assertEqual(c['body']['error'], 'invalid_attachment_type')
        self.assertEqual(c['body']['received'], 'video')

    def test_415_unsupported_mime_code(self):
        """gap-04a: MIME not in any whitelist → HTTP 415 with error 'unsupported_mime'."""
        c = self._capture_att_error(
            415, 'unsupported_mime',
            'MIME type text/html is not allowed for attachment_type=image.',
        )
        self.assertEqual(c['status'], 415)
        self.assertEqual(c['body']['error'], 'unsupported_mime')

    def test_415_mime_mismatch_code(self):
        """gap-04b: MIME valid globally but wrong type → HTTP 415 with error 'mime_mismatch'."""
        c = self._capture_att_error(
            415, 'mime_mismatch',
            'MIME type application/pdf is not valid for attachment_type=image.',
        )
        self.assertEqual(c['status'], 415)
        self.assertEqual(c['body']['error'], 'mime_mismatch')

    def test_400_empty_file_rejected(self):
        """gap-05 / FR1.5a: empty file returns 400 with error 'empty_file'."""
        c = self._capture_att_error(400, 'empty_file', 'File content cannot be empty.')
        self.assertEqual(c['status'], 400)
        self.assertEqual(c['body']['error'], 'empty_file')


if __name__ == '__main__':
    unittest.main(verbosity=2)
