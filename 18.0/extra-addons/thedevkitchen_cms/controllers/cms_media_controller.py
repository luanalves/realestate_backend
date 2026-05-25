# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request, Response
from odoo.addons.thedevkitchen_apigateway.middleware import (
    require_jwt,
    require_session,
    require_company,
)
from ..services.cms_media_service import CmsMediaService
from ..services.cms_error_helpers import _cms_error
import json

_logger = logging.getLogger(__name__)

_MEDIA_LIST_LIMIT = 50


class CmsMediaController(http.Controller):

    # ==================== UPLOAD ====================

    @http.route(
        "/api/v1/cms/media/upload",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def upload_media(self, **kwargs):
        company_id = request.session.get("company_id") or request.env.company.id
        role = request.session.get("role", "")

        if role not in ("owner", "director", "manager"):
            return _cms_error(403, "forbidden", "Insufficient permissions to upload media")

        file_obj = request.httprequest.files.get("file")
        if not file_obj:
            return _cms_error(400, "validation_error", "Missing 'file' in multipart form data")

        filename = file_obj.filename or "upload"
        claimed_mime = file_obj.content_type or None
        file_bytes = file_obj.read()

        try:
            media = CmsMediaService.upload(
                request.env, file_bytes, filename, claimed_mime, company_id
            )
        except ValueError as exc:
            err_str = str(exc)
            if err_str.startswith("unsupported_mime|"):
                _, detected = err_str.split("|", 1)
                return _cms_error(415, "unsupported_mime", f"MIME '{detected}' is not allowed")
            if err_str.startswith("mime_mismatch|"):
                _, claimed, detected = err_str.split("|", 2)
                return _cms_error(
                    415, "mime_mismatch",
                    "File content does not match declared MIME type.",
                    claimed=claimed,
                    detected=detected,
                )
            if err_str.startswith("file_too_large|"):
                _, limit, size = err_str.split("|", 2)
                return _cms_error(
                    413, "file_too_large",
                    "File exceeds the maximum allowed size.",
                    max_size_bytes=int(limit),
                    actual_size_bytes=int(size),
                )
            return _cms_error(422, "validation_error", err_str)
        except Exception:
            _logger.exception("CMS upload_media unexpected error")
            return _cms_error(500, "server_error", "An unexpected error occurred")

        return Response(
            json.dumps(CmsMediaService.serialize(media)),
            status=201,
            content_type="application/json",
        )

    # ==================== LIST ====================

    @http.route(
        "/api/v1/cms/media",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def list_media(self, **kwargs):
        company_id = request.session.get("company_id") or request.env.company.id
        role = request.session.get("role", "")

        if role not in ("owner", "director", "manager", "agent"):
            return _cms_error(403, "forbidden", "Insufficient permissions")

        try:
            offset = int(request.httprequest.args.get("offset", 0))
            limit = min(int(request.httprequest.args.get("limit", _MEDIA_LIST_LIMIT)), _MEDIA_LIST_LIMIT)
        except (ValueError, TypeError):
            return _cms_error(400, "validation_error", "Invalid pagination parameters")

        domain = [("company_id", "=", company_id)]
        items = request.env["thedevkitchen.cms.media"].sudo().search(
            domain, limit=limit, offset=offset, order="create_date desc"
        )
        total = request.env["thedevkitchen.cms.media"].sudo().search_count(domain)
        payload = {
            "items": [CmsMediaService.serialize(m) for m in items],
            "total": total,
            "offset": offset,
            "limit": limit,
        }
        return Response(json.dumps(payload), status=200, content_type="application/json")

    # ==================== GET METADATA ====================

    @http.route(
        "/api/v1/cms/media/<int:media_id>",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def get_media(self, media_id, **kwargs):
        company_id = request.session.get("company_id") or request.env.company.id
        role = request.session.get("role", "")

        if role not in ("owner", "director", "manager", "agent"):
            return _cms_error(403, "forbidden", "Insufficient permissions")

        media = request.env["thedevkitchen.cms.media"].sudo().search(
            [("id", "=", media_id), ("company_id", "=", company_id)], limit=1
        )
        if not media:
            return _cms_error(404, "not_found", f"Media {media_id} not found")

        return Response(
            json.dumps(CmsMediaService.serialize(media)),
            status=200,
            content_type="application/json",
        )

    # ==================== GET FILE (binary) ====================

    @http.route(
        "/api/v1/cms/media/<int:media_id>/file",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def get_media_file(self, media_id, **kwargs):
        company_id = request.session.get("company_id") or request.env.company.id
        role = request.session.get("role", "")

        if role not in ("owner", "director", "manager", "agent"):
            return _cms_error(403, "forbidden", "Insufficient permissions")

        media = request.env["thedevkitchen.cms.media"].sudo().search(
            [("id", "=", media_id), ("company_id", "=", company_id)], limit=1
        )
        if not media:
            return _cms_error(404, "not_found", f"Media {media_id} not found")

        attachment = media.attachment_id
        if not attachment or not attachment.datas:
            return _cms_error(404, "not_found", "File binary not found")

        import base64
        file_bytes = base64.b64decode(attachment.datas)
        return Response(
            file_bytes,
            status=200,
            content_type=media.mime_type,
            headers=[
                ("Content-Disposition", f'inline; filename="{media.name}"'),
                ("Content-Length", str(len(file_bytes))),
            ],
        )

    # ==================== DELETE (hard) ====================

    @http.route(
        "/api/v1/cms/media/<int:media_id>",
        type="http",
        auth="none",
        methods=["DELETE"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def delete_media(self, media_id, **kwargs):
        company_id = request.session.get("company_id") or request.env.company.id
        role = request.session.get("role", "")

        if role not in ("owner", "director", "manager"):
            return _cms_error(403, "forbidden", "Insufficient permissions to delete media")

        media = request.env["thedevkitchen.cms.media"].sudo().search(
            [("id", "=", media_id), ("company_id", "=", company_id)], limit=1
        )
        if not media:
            return _cms_error(404, "not_found", f"Media {media_id} not found")

        # Hard delete via model override (removes ir.attachment too)
        media.unlink()
        return Response(
            json.dumps({"success": True, "id": media_id}),
            status=200,
            content_type="application/json",
        )
