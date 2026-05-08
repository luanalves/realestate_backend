# -*- coding: utf-8 -*-
import base64
import logging

import magic
from werkzeug.utils import secure_filename
from werkzeug.wrappers import Response

from odoo import http
from odoo.http import request

from .utils.auth import require_jwt
from .utils.response import success_response
from odoo.addons.thedevkitchen_apigateway.middleware import require_session, require_company
from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_IMAGES_PER_PROPERTY = 50
MAX_DOCUMENTS_PER_PROPERTY = 20

TYPE_IMAGE = 'image'
TYPE_DOCUMENT = 'document'

ALLOWED_IMAGE_MIMETYPES = frozenset({
    'image/jpeg',
    'image/png',
    'image/webp',
})

ALLOWED_DOCUMENT_MIMETYPES = frozenset({
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
})

ALLOWED_MIMETYPES = ALLOWED_IMAGE_MIMETYPES | ALLOWED_DOCUMENT_MIMETYPES

DEFAULT_MAX_FILE_BYTES = 134_217_728  # 128 MB
CONFIG_PARAM_MAX_SIZE = 'web.max_file_upload_size'


# ---------------------------------------------------------------------------
# Module-level helpers (T004, T005, T006, T007)
# ---------------------------------------------------------------------------

def _fetch_property_for_company(property_id):
    domain = [('id', '=', property_id)] + request.company_domain
    return request.env['real.estate.property'].sudo().search(domain, limit=1) or None


def _get_max_upload_bytes():
    IrConfig = request.env['ir.config_parameter'].sudo()
    try:
        return int(IrConfig.get_param(CONFIG_PARAM_MAX_SIZE, default=DEFAULT_MAX_FILE_BYTES))
    except (ValueError, TypeError):
        return DEFAULT_MAX_FILE_BYTES


def _att_error(status_code, error_code, detail, **extras):
    """Build FR6.9-compliant error envelope: {error, detail, ...extras}."""
    body = {'error': error_code, 'detail': detail}
    body.update(extras)
    return request.make_json_response(body, status=status_code)


def _detect_mime(content):
    return magic.from_buffer(content[:2048], mime=True)


def _serialize_attachment(att, property_id, include_self_link=False):
    download_url = f'/api/v1/properties/{property_id}/attachments/{att.id}/download'
    links = {'download': download_url}
    if include_self_link:
        links['self'] = f'/api/v1/properties/{property_id}/attachments/{att.id}'

    uploaded_at = att.create_date.strftime('%Y-%m-%dT%H:%M:%SZ') if att.create_date else None

    return {
        'id': att.id,
        'name': att.name,
        'mimetype': att.mimetype,
        'size': att.file_size or 0,
        'attachment_type': att.description,
        'uploaded_at': uploaded_at,
        'links': links,
    }


def _fetch_attachment(attachment_id, property_id):
    att = request.env['ir.attachment'].sudo().browse(attachment_id)
    if not att.exists():
        return None
    # Feature 017 attachments: stored directly on real.estate.property
    if att.res_model == 'real.estate.property' and att.res_id == property_id:
        return att
    # Legacy attachments: stored on real.estate.property.photo / real.estate.property.document
    # Verify the parent record belongs to this property (T021)
    if att.res_model in ('real.estate.property.photo', 'real.estate.property.document'):
        legacy_record = request.env[att.res_model].sudo().browse(att.res_id)
        if legacy_record.exists() and legacy_record.property_id.id == property_id:
            return att
    return None


def _is_agent_only(user):
    return (
        user.has_group('quicksol_estate.group_real_estate_agent')
        and not user.has_group('quicksol_estate.group_real_estate_manager')
        and not user.has_group('quicksol_estate.group_real_estate_owner')
        and not user.has_group('base.group_system')
    )


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class PropertyAttachmentsController(http.Controller):

    # ------------------------------------------------------------------ #
    # POST /api/v1/properties/<id>/attachments  (US1 + US2)              #
    # ------------------------------------------------------------------ #

    @http.route(
        '/api/v1/properties/<int:property_id>/attachments',
        type='http', auth='none', methods=['POST'], csrf=False, cors='*',
    )
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def upload_attachment(self, property_id, **kwargs):
        try:
            user = request.env.user

            # RBAC: Agents cannot upload (FR3.1)
            if _is_agent_only(user):
                _logger.warning(
                    'upload_attachment: Agent %s attempted upload on property %s — denied (403)',
                    user.id, property_id,
                )
                return _att_error(403, 'forbidden', 'Agents cannot upload attachments.')

            # Property lookup (company-scoped, anti-enumeration)
            prop = _fetch_property_for_company(property_id)
            if not prop:
                _logger.warning(
                    'upload_attachment: property %s not found for company %s',
                    property_id, request.env.company.id,
                )
                return _att_error(404, 'not_found', 'Property not found.')

            # Form field validation
            upload = request.httprequest.files.get('file')
            attachment_type = request.httprequest.form.get('attachment_type', '').strip()

            if not upload:
                return _att_error(400, 'missing_file', 'A file is required.')
            if not attachment_type:
                return _att_error(400, 'missing_attachment_type', 'attachment_type is required (image or document).')
            if attachment_type not in (TYPE_IMAGE, TYPE_DOCUMENT):
                _logger.warning(
                    'upload_attachment: invalid attachment_type "%s" on property %s',
                    attachment_type, property_id,
                )
                return _att_error(
                    400, 'invalid_attachment_type',
                    f"Invalid attachment_type '{attachment_type}'. Allowed values: image, document.",
                    received=attachment_type,
                )

            # Read bytes once
            content = upload.read()

            # Zero-byte validation (FR1.5a) — 400
            if len(content) == 0:
                return _att_error(400, 'empty_file', 'File content cannot be empty.')

            # Size check (FR1.3) — 413
            max_bytes = _get_max_upload_bytes()
            if len(content) > max_bytes:
                _logger.warning(
                    'upload_attachment: file too large (%d bytes > %d) on property %s (user=%s, company=%s)',
                    len(content), max_bytes, property_id,
                    request.env.user.id, request.env.company.id,
                )
                return _att_error(
                    413, 'file_too_large',
                    'File size exceeds the configured limit.',
                    max_size_bytes=max_bytes,
                    received_size=len(content),
                )

            # Quantity limit (FR1.4) — 422
            max_count = MAX_IMAGES_PER_PROPERTY if attachment_type == TYPE_IMAGE else MAX_DOCUMENTS_PER_PROPERTY
            current_count = request.env['ir.attachment'].sudo().search_count([
                ('res_model', '=', 'real.estate.property'),
                ('res_id', '=', property_id),
                ('description', '=', attachment_type),
            ])
            if current_count >= max_count:
                _logger.warning(
                    'upload_attachment: quantity limit %d reached for type "%s" on property %s (user=%s, company=%s)',
                    max_count, attachment_type, property_id,
                    request.env.user.id, request.env.company.id,
                )
                return _att_error(
                    422, 'attachment_limit_exceeded',
                    f'Maximum number of {attachment_type} attachments has been reached for this property.',
                    attachment_type=attachment_type,
                    limit=max_count,
                    current=current_count,
                )

            # MIME validation via magic bytes (R002) — 415
            detected_mime = _detect_mime(content)
            allowed_for_type = ALLOWED_IMAGE_MIMETYPES if attachment_type == TYPE_IMAGE else ALLOWED_DOCUMENT_MIMETYPES

            if detected_mime not in ALLOWED_MIMETYPES:
                _logger.warning(
                    'upload_attachment: MIME "%s" not in global whitelist on property %s (user=%s, company=%s)',
                    detected_mime, property_id,
                    request.env.user.id, request.env.company.id,
                )
                return _att_error(
                    415, 'unsupported_mime',
                    f'MIME type {detected_mime} is not allowed for attachment_type={attachment_type}.',
                )

            if detected_mime not in allowed_for_type:
                _logger.warning(
                    'upload_attachment: MIME "%s" not valid for attachment_type "%s" on property %s (user=%s, company=%s)',
                    detected_mime, attachment_type, property_id,
                    request.env.user.id, request.env.company.id,
                )
                return _att_error(
                    415, 'mime_mismatch',
                    f'MIME type {detected_mime} is not valid for attachment_type={attachment_type}.',
                )

            # Sanitize filename (R007)
            safe_name = secure_filename(upload.filename or '') or 'untitled'

            # Persist as ir.attachment (R003)
            att = request.env['ir.attachment'].sudo().create({
                'name': safe_name,
                'datas': base64.b64encode(content),
                'res_model': 'real.estate.property',
                'res_id': property_id,
                'mimetype': detected_mime,
                'description': attachment_type,
                'company_id': request.env.company.id,
            })

            return success_response(
                {'status': 'success', 'data': _serialize_attachment(att, property_id, include_self_link=True)},
                status_code=201,
            )

        except Exception:
            _logger.exception('upload_attachment: unexpected error for property %s', property_id)
            return _att_error(500, 'internal_error', 'An unexpected error occurred.')

    # ------------------------------------------------------------------ #
    # GET /api/v1/properties/<id>/attachments  (US6)                     #
    # ------------------------------------------------------------------ #

    @http.route(
        '/api/v1/properties/<int:property_id>/attachments',
        type='http', auth='none', methods=['GET'], csrf=False, cors='*',
    )
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def list_attachments(self, property_id, **kwargs):
        try:
            prop = _fetch_property_for_company(property_id)
            if not prop:
                return _att_error(404, 'not_found', 'Property not found.')

            # Query params
            attachment_type = kwargs.get('attachment_type', '').strip() or None
            try:
                limit = min(int(kwargs.get('limit', 50)), 100)
                offset = int(kwargs.get('offset', 0))
            except (ValueError, TypeError):
                return _att_error(400, 'invalid_pagination', 'Invalid limit or offset value.')

            if attachment_type and attachment_type not in (TYPE_IMAGE, TYPE_DOCUMENT):
                return _att_error(
                    400, 'invalid_attachment_type',
                    f"Invalid attachment_type '{attachment_type}'. Allowed values: image, document.",
                    received=attachment_type,
                )

            # Build domain
            domain = [
                ('res_model', '=', 'real.estate.property'),
                ('res_id', '=', property_id),
                ('description', 'in', [TYPE_IMAGE, TYPE_DOCUMENT]),
            ]
            if attachment_type:
                domain.append(('description', '=', attachment_type))

            Attachment = request.env['ir.attachment'].sudo()
            total = Attachment.search_count(domain)
            items = Attachment.search(domain, order='create_date desc', limit=limit, offset=offset)

            return success_response({
                'status': 'success',
                'data': {
                    'items': [_serialize_attachment(a, property_id, include_self_link=False) for a in items],
                    'pagination': {
                        'total': total,
                        'limit': limit,
                        'offset': offset,
                    },
                },
            })

        except Exception:
            _logger.exception('list_attachments: unexpected error for property %s', property_id)
            return _att_error(500, 'internal_error', 'An unexpected error occurred.')

    # ------------------------------------------------------------------ #
    # GET /api/v1/properties/<id>/attachments/<aid>/download  (US3)      #
    # ------------------------------------------------------------------ #

    @http.route(
        '/api/v1/properties/<int:property_id>/attachments/<int:attachment_id>/download',
        type='http', auth='none', methods=['GET'], csrf=False, cors='*',
    )
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def download_attachment(self, property_id, attachment_id, **kwargs):
        try:
            prop = _fetch_property_for_company(property_id)
            if not prop:
                return _att_error(404, 'not_found', 'Property not found.')

            att = _fetch_attachment(attachment_id, property_id)
            if not att:
                _logger.warning(
                    'download_attachment: attachment %s not found or not on property %s',
                    attachment_id, property_id,
                )
                return _att_error(404, 'not_found', 'Attachment not found.')

            content = att.raw  # bytes directly from filestore (FR2.3)

            # NEVER redirect to /web/content/ (FR2.4)
            return Response(
                content,
                status=200,
                headers={
                    'Content-Type': att.mimetype or 'application/octet-stream',
                    'Content-Disposition': f'attachment; filename="{att.name}"',
                    'Content-Security-Policy': "default-src 'none'",
                    'X-Content-Type-Options': 'nosniff',
                },
            )

        except Exception:
            _logger.exception(
                'download_attachment: unexpected error for property %s attachment %s',
                property_id, attachment_id,
            )
            return _att_error(500, 'internal_error', 'An unexpected error occurred.')

    # ------------------------------------------------------------------ #
    # DELETE /api/v1/properties/<id>/attachments/<aid>  (US4)            #
    # ------------------------------------------------------------------ #

    @http.route(
        '/api/v1/properties/<int:property_id>/attachments/<int:attachment_id>',
        type='http', auth='none', methods=['DELETE'], csrf=False, cors='*',
    )
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def delete_attachment(self, property_id, attachment_id, **kwargs):
        try:
            prop = _fetch_property_for_company(property_id)
            if not prop:
                return _att_error(404, 'not_found', 'Property not found.')

            # RBAC: only Owner/Manager can delete (FR3.1)
            user = request.env.user
            if _is_agent_only(user):
                _logger.warning(
                    'delete_attachment: Agent %s attempted DELETE on property %s attachment %s — denied (403)',
                    user.id, property_id, attachment_id,
                )
                return _att_error(403, 'forbidden', 'Agents cannot delete attachments.')

            att = _fetch_attachment(attachment_id, property_id)
            if not att:
                _logger.warning(
                    'delete_attachment: attachment %s not found or not on property %s',
                    attachment_id, property_id,
                )
                return _att_error(404, 'not_found', 'Attachment not found.')

            # Hard delete — documented exception to ADR-015 (FR3.2); ir.attachment is not a domain entity
            att.unlink()

            return Response('', status=204)

        except Exception:
            _logger.exception(
                'delete_attachment: unexpected error for property %s attachment %s',
                property_id, attachment_id,
            )
            return _att_error(500, 'internal_error', 'An unexpected error occurred.')
