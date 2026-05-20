# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request
from odoo.addons.thedevkitchen_apigateway.middleware import (
    require_company,
    require_jwt,
    require_session,
)
from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request

from ..services.capability_service import CapabilityService
from ..services.role_resolver import resolve_role

_logger = logging.getLogger(__name__)


class CapabilitiesController(http.Controller):
    @http.route(
        "/api/v1/me/capabilities",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    @trace_http_request
    def get_capabilities(self, **kwargs):
        try:
            user = request.env.user
            if not user or user.id == 4:
                _logger.warning("Unauthorized /api/v1/me/capabilities access attempt")
                return request.make_json_response({"error": "unauthorized"}, status=401)

            requested_company_id = request.httprequest.headers.get(
                "X-Company-ID"
            ) or request.httprequest.headers.get("X-Company-Id")
            company_id = user.company_id.id if user.company_id else None

            if requested_company_id:
                try:
                    company_id = int(requested_company_id)
                except (TypeError, ValueError):
                    return request.make_json_response(
                        {"error": "forbidden"}, status=403
                    )

                if (
                    request.user_company_ids
                    and company_id not in request.user_company_ids
                ):
                    return request.make_json_response(
                        {"error": "forbidden"}, status=403
                    )

            role = resolve_role(user)
            payload = CapabilityService(request.env).build_payload(
                user, role, company_id
            )
            return request.make_json_response(payload)

        except Exception as exc:
            _logger.error("Error in /api/v1/me/capabilities: %s", exc, exc_info=True)
            return request.make_json_response(
                {"error": "internal_server_error"}, status=500
            )
