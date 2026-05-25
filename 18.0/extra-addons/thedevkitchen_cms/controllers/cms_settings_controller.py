# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import ValidationError
from odoo.addons.thedevkitchen_apigateway.middleware import (
    require_jwt,
    require_session,
    require_company,
)
from ..services.cms_settings_service import CmsSettingsService
from ..services.cms_error_helpers import _cms_error

_logger = logging.getLogger(__name__)


class CmsSettingsController(http.Controller):

    # ==================== GET ====================

    @http.route(
        "/api/v1/cms/settings",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def get_settings(self, **kwargs):
        company_id = request.session.get("company_id") or request.env.company.id
        role = request.session.get("role", "")

        if role not in ("owner", "director", "manager", "agent"):
            return _cms_error(403, "forbidden", "Insufficient permissions")

        settings = CmsSettingsService.get_or_create(request.env, company_id)
        payload = CmsSettingsService.serialize_for_role(settings, role)
        return Response(json.dumps(payload), status=200, content_type="application/json")

    # ==================== UPDATE ====================

    @http.route(
        "/api/v1/cms/settings",
        type="http",
        auth="none",
        methods=["PUT"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def update_settings(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return _cms_error(400, "validation_error", "Invalid JSON in request body")

        company_id = request.session.get("company_id") or request.env.company.id
        role = request.session.get("role", "")

        if role not in ("owner", "director", "manager"):
            return _cms_error(403, "forbidden", "Insufficient permissions to update settings")

        try:
            settings = CmsSettingsService.update_settings(
                request.env, data, company_id, role
            )
        except ValueError as exc:
            err_str = str(exc)
            if err_str == "forbidden":
                return _cms_error(403, "forbidden", "Only owners can set custom_js")
            if err_str == "css_injection_detected":
                return _cms_error(
                    422, "css_injection_detected",
                    "CSS injection pattern detected in custom_css. Field rejected.",
                    field="custom_css",
                )
            if err_str == "css_too_large":
                return _cms_error(
                    422, "css_too_large",
                    "custom_css exceeds the maximum allowed size of 64KB.",
                )
            return _cms_error(422, "validation_error", err_str)
        except ValidationError as exc:
            return _cms_error(422, "validation_error", str(exc))
        except Exception as exc:
            _logger.exception("CMS update_settings unexpected error")
            return _cms_error(500, "server_error", str(exc))

        payload = CmsSettingsService.serialize_for_role(settings, role)
        return Response(json.dumps(payload), status=200, content_type="application/json")
