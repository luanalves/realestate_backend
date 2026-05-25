# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request, Response
from odoo.addons.thedevkitchen_apigateway.middleware import require_jwt
from ..services.cms_error_helpers import _cms_error

_logger = logging.getLogger(__name__)

# Fields excluded from the public payload (operational/internal data)
_EXCLUDED_FIELDS = frozenset({
    "status", "active", "company_id", "custom_js", "custom_css",
    "create_date", "write_date", "created_at", "updated_at",
})


class CmsPublicController(http.Controller):

    # public endpoint
    @http.route(
        "/api/v1/public/cms/<string:company_slug>/pages/<string:page_slug>",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    def get_public_page(self, company_slug, page_slug, **kwargs):
        # 1. Resolve company from slug
        settings = request.env["thedevkitchen.cms.settings"].sudo().search(
            [("company_slug", "=", company_slug)], limit=1
        )
        if not settings:
            return _cms_error(404, "not_found", f"Company '{company_slug}' not found")

        company_id = settings.company_id.id

        # 2. Fetch published, active page
        page = request.env["thedevkitchen.cms.page"].sudo().search(
            [
                ("slug", "=", page_slug),
                ("company_id", "=", company_id),
                ("status", "=", "published"),
                ("active", "=", True),
            ],
            limit=1,
        )
        if not page:
            return _cms_error(
                404, "not_found",
                f"Page '{page_slug}' not found or not published"
            )

        # 3. Build public payload — operational fields excluded
        payload = {
            "slug": page.slug,
            "name": page.name,
            "title": page.title or None,
            "meta_description": page.meta_description or None,
            "og_title": page.og_title or settings.og_default_title or None,
            "og_description": page.og_description or settings.og_default_description or None,
            "og_image_url": (
                page.og_image_id.url if page.og_image_id else None
            ),
            "canonical_url": page.canonical_url or None,
            "robots_meta": page.robots_meta or "index,follow",
            "structured_data": page.structured_data or None,
            "published_at": page.published_at.isoformat() if page.published_at else None,
            "content": page.content_ids[0].content if page.content_ids else None,
        }

        return Response(json.dumps(payload), status=200, content_type="application/json")
