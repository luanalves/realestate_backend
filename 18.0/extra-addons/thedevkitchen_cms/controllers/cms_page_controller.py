# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request, Response
from odoo.addons.quicksol_estate.services.role_resolver import resolve_role
from odoo.exceptions import ValidationError
from odoo.addons.thedevkitchen_apigateway.middleware import (
    require_jwt,
    require_session,
    require_company,
)
from ..services.cms_page_service import CmsPageService
from ..services.cms_error_helpers import _cms_error

_logger = logging.getLogger(__name__)

_PAGE_LIST_LIMIT = 50


class CmsPageController(http.Controller):

    # ==================== CREATE ====================

    @http.route(
        "/api/v1/cms/pages",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def create_page(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return _cms_error(400, "validation_error", "Invalid JSON in request body")

        company_id = request.env.company.id
        role = resolve_role(request.env.user) or ""

        # RBAC: only owner/director/manager may create pages
        if role not in ("owner", "director", "manager"):
            return _cms_error(403, "forbidden", "Insufficient permissions to create CMS pages")

        try:
            template_id = data.pop("template_id", None)
            page = CmsPageService.create_page(
                request.env, data, company_id, template_id=template_id
            )
        except (ValidationError, ValueError) as exc:
            return _cms_error(422, "validation_error", str(exc))
        except Exception as exc:
            _logger.exception("CMS create_page unexpected error")
            return _cms_error(500, "server_error", "An unexpected error occurred")

        payload = CmsPageService.serialize(page)
        payload["links"] = {
            "self": f"/api/v1/cms/pages/{page.id}",
            "update": f"/api/v1/cms/pages/{page.id}",
            "delete": f"/api/v1/cms/pages/{page.id}",
            "duplicate": f"/api/v1/cms/pages/{page.id}/duplicate",
        }
        return Response(json.dumps(payload), status=201, content_type="application/json")

    # ==================== LIST ====================

    @http.route(
        "/api/v1/cms/pages",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def list_pages(self, **kwargs):
        company_id = request.env.company.id
        role = resolve_role(request.env.user) or ""

        if role not in ("owner", "director", "manager", "agent"):
            return _cms_error(403, "forbidden", "Insufficient permissions")

        try:
            offset = int(request.httprequest.args.get("offset", 0))
            limit = min(int(request.httprequest.args.get("limit", _PAGE_LIST_LIMIT)), _PAGE_LIST_LIMIT)
            status_filter = request.httprequest.args.get("status")
        except (ValueError, TypeError):
            return _cms_error(400, "validation_error", "Invalid pagination parameters")

        domain = [("company_id", "=", company_id)]
        if status_filter:
            domain.append(("status", "=", status_filter))

        pages = request.env["thedevkitchen.cms.page"].sudo().search(
            domain, limit=limit, offset=offset, order="create_date desc"
        )
        total = request.env["thedevkitchen.cms.page"].sudo().search_count(domain)

        items = [CmsPageService.serialize(p, include_content=False) for p in pages]
        payload = {"items": items, "total": total, "offset": offset, "limit": limit}
        return Response(json.dumps(payload), status=200, content_type="application/json")

    # ==================== GET BY ID ====================

    @http.route(
        "/api/v1/cms/pages/<int:page_id>",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def get_page(self, page_id, **kwargs):
        company_id = request.env.company.id
        role = resolve_role(request.env.user) or ""

        if role not in ("owner", "director", "manager", "agent"):
            return _cms_error(403, "forbidden", "Insufficient permissions")

        page = request.env["thedevkitchen.cms.page"].sudo().search(
            [("id", "=", page_id), ("company_id", "=", company_id)], limit=1
        )
        if not page:
            return _cms_error(404, "not_found", f"Page {page_id} not found")

        payload = CmsPageService.serialize(page, include_content=True)
        return Response(json.dumps(payload), status=200, content_type="application/json")

    # ==================== UPDATE ====================

    @http.route(
        "/api/v1/cms/pages/<int:page_id>",
        type="http",
        auth="none",
        methods=["PUT"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def update_page(self, page_id, **kwargs):
        try:
            data = json.loads(request.httprequest.data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return _cms_error(400, "validation_error", "Invalid JSON in request body")

        company_id = request.env.company.id
        role = resolve_role(request.env.user) or ""

        if role not in ("owner", "director", "manager"):
            return _cms_error(403, "forbidden", "Insufficient permissions to update CMS pages")

        try:
            page = CmsPageService.update_page(
                request.env, page_id, data, company_id
            )
        except LookupError:
            return _cms_error(404, "not_found", f"Page {page_id} not found")
        except ValueError as exc:
            err_str = str(exc)
            if err_str.startswith("invalid_status_transition|"):
                _, from_s, to_s, allowed_str = err_str.split("|", 3)
                return _cms_error(
                    422,
                    "invalid_status_transition",
                    f"Cannot transition from '{from_s}' to '{to_s}'.",
                    from_status=from_s,
                    to_status=to_s,
                    allowed=allowed_str.split(","),
                )
            if err_str.startswith("invalid_status_value|"):
                _, bad_val = err_str.split("|", 1)
                return _cms_error(
                    422, "invalid_status_value",
                    f"'{bad_val}' is not a valid status.",
                    allowed=["draft", "pending_review", "published", "archived"],
                )
            return _cms_error(422, "validation_error", err_str)
        except (ValidationError, Exception) as exc:
            _logger.exception("CMS update_page unexpected error")
            return _cms_error(500, "server_error", str(exc))

        payload = CmsPageService.serialize(page, include_content=True)
        return Response(json.dumps(payload), status=200, content_type="application/json")

    # ==================== DELETE (soft) ====================

    @http.route(
        "/api/v1/cms/pages/<int:page_id>",
        type="http",
        auth="none",
        methods=["DELETE"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def delete_page(self, page_id, **kwargs):
        company_id = request.env.company.id
        role = resolve_role(request.env.user) or ""

        if role not in ("owner", "director", "manager"):
            return _cms_error(403, "forbidden", "Insufficient permissions to delete CMS pages")

        page = request.env["thedevkitchen.cms.page"].sudo().search(
            [("id", "=", page_id), ("company_id", "=", company_id)], limit=1
        )
        if not page:
            return _cms_error(404, "not_found", f"Page {page_id} not found")

        page.write({"active": False})
        return Response(
            json.dumps({"success": True, "id": page_id}),
            status=200,
            content_type="application/json",
        )

    # ==================== DUPLICATE ====================

    @http.route(
        "/api/v1/cms/pages/<int:page_id>/duplicate",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def duplicate_page(self, page_id, **kwargs):
        company_id = request.env.company.id
        role = resolve_role(request.env.user) or ""

        if role not in ("owner", "director", "manager"):
            return _cms_error(403, "forbidden", "Insufficient permissions")

        try:
            new_page = CmsPageService.duplicate_page(request.env, page_id, company_id)
        except LookupError:
            return _cms_error(404, "not_found", f"Page {page_id} not found")
        except Exception as exc:
            _logger.exception("CMS duplicate_page unexpected error")
            return _cms_error(500, "server_error", str(exc))

        payload = CmsPageService.serialize(new_page)
        payload["links"] = {"self": f"/api/v1/cms/pages/{new_page.id}"}
        return Response(json.dumps(payload), status=201, content_type="application/json")
