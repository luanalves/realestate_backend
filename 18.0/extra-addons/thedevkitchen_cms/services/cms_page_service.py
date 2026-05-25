# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


def _emit(event_name, attributes=None):
    """Emit an OpenTelemetry span event, silently ignoring unavailability."""
    try:
        from odoo.addons.thedevkitchen_observability.services.tracer import add_span_event
        add_span_event(event_name, attributes or {})
    except Exception:
        _logger.debug("Observability not available — event %s not emitted", event_name)

# ---- State machine ----
VALID_TRANSITIONS = {
    "draft": ["pending_review", "published"],
    "pending_review": ["published", "draft"],
    "published": ["archived"],
    "archived": ["draft"],
}

ALL_STATUSES = list(VALID_TRANSITIONS.keys())

# ---- Content size limit ----
MAX_CONTENT_BYTES = 512 * 1024  # 512 KB


class CmsPageService:
    """Business logic for CMS pages and state machine."""

    # ==================== CREATE ====================

    @staticmethod
    def create_page(env, vals, company_id, template_id=None):
        vals = dict(vals)
        vals["company_id"] = company_id
        # Remove content from page vals — stored in cms.page.content
        content = vals.pop("content", None)

        # Resolve template content
        if template_id:
            template = env["thedevkitchen.cms.template"].sudo().search(
                [("id", "=", int(template_id)), ("company_id", "=", company_id)],
                limit=1,
            )
            if not template:
                raise ValueError("template_not_found")
            if template.content_ids:
                content = template.content_ids[0].content

        page = env["thedevkitchen.cms.page"].sudo().create(vals)

        # Always create a content record (may be null)
        env["thedevkitchen.cms.page.content"].sudo().create(
            {"page_id": page.id, "content": content}
        )
        return page

    # ==================== UPDATE ====================

    @staticmethod
    def update_page(env, page_id, vals, company_id):
        page = env["thedevkitchen.cms.page"].sudo().search(
            [("id", "=", page_id), ("company_id", "=", company_id)], limit=1
        )
        if not page:
            raise LookupError("page_not_found")

        vals = dict(vals)
        content = vals.pop("content", None)

        # Handle status change separately
        new_status = vals.pop("status", None)

        if vals:
            page.write(vals)

        if new_status:
            CmsPageService.change_status(env, page_id, new_status, company_id)
            # Refresh record after status change
            page = env["thedevkitchen.cms.page"].sudo().browse(page_id)

        if content is not None:
            CmsPageService._update_content(env, page, content)

        return page

    @staticmethod
    def _update_content(env, page, content):
        if content:
            if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
                raise ValueError("content_too_large")
            try:
                json.loads(content)
            except (ValueError, TypeError):
                raise ValueError("content_invalid_json")

        content_record = page.content_ids[:1]
        if content_record:
            content_record.write({"content": content})
        else:
            env["thedevkitchen.cms.page.content"].sudo().create(
                {"page_id": page.id, "content": content}
            )

    # ==================== DUPLICATE ====================

    @staticmethod
    def duplicate_page(env, page_id, company_id):
        page = env["thedevkitchen.cms.page"].sudo().search(
            [("id", "=", page_id), ("company_id", "=", company_id)], limit=1
        )
        if not page:
            raise LookupError("page_not_found")

        # Generate unique slug
        base_slug = page.slug + "-copy"
        new_slug = CmsPageService._unique_slug(env, base_slug, company_id)

        new_vals = {
            "name": page.name + " (Cópia)",
            "slug": new_slug,
            "title": page.title,
            "meta_description": page.meta_description,
            "og_title": page.og_title,
            "og_description": page.og_description,
            "canonical_url": page.canonical_url,
            "robots_meta": page.robots_meta,
            "structured_data": page.structured_data,
            "company_id": company_id,
            # Duplicated pages always start as draft
            "status": "draft",
        }

        original_content = page.content_ids[0].content if page.content_ids else None
        return CmsPageService.create_page(env, new_vals, company_id, template_id=None)

    @staticmethod
    def _unique_slug(env, base_slug, company_id):
        candidate = base_slug
        counter = 2
        while env["thedevkitchen.cms.page"].sudo().search_count(
            [("slug", "=", candidate), ("company_id", "=", company_id)]
        ):
            candidate = f"{base_slug}-{counter}"
            counter += 1
        return candidate

    # ==================== STATE MACHINE ====================

    @staticmethod
    def change_status(env, page_id, new_status, company_id):
        if new_status not in ALL_STATUSES:
            raise ValueError(f"invalid_status_value|{new_status}")

        page = env["thedevkitchen.cms.page"].sudo().search(
            [("id", "=", page_id), ("company_id", "=", company_id)], limit=1
        )
        if not page:
            raise LookupError("page_not_found")

        current_status = page.status
        allowed = VALID_TRANSITIONS.get(current_status, [])

        if new_status not in allowed:
            raise ValueError(
                f"invalid_status_transition|{current_status}|{new_status}|{','.join(allowed)}"
            )

        write_vals = {"status": new_status}
        published_at = None
        if new_status == "published" and not page.published_at:
            published_at = datetime.utcnow()
            write_vals["published_at"] = published_at

        page.write(write_vals)

        # T041: emit observability events
        _emit("cms.page.status_changed", {
            "company_id": str(company_id),
            "page_id": str(page_id),
            "slug": page.slug or "",
            "from_status": current_status,
            "to_status": new_status,
            "author_id": str(env.uid),
        })
        if new_status == "published":
            _emit("cms.page.published", {
                "published_at": (published_at or page.published_at).isoformat()
                if (published_at or page.published_at)
                else "",
            })

        # T044: update gauge cms_pages_by_status (all 4 buckets)
        try:
            counts = {
                row["status"]: row["count"]
                for row in env["thedevkitchen.cms.page"]
                .sudo()
                .read_group(
                    [("company_id", "=", company_id)],
                    ["status"],
                    ["status"],
                )
                if row.get("status")
                for row in [{"status": row["status"], "count": row["status_count"]}]
            }
            _emit("cms.pages_by_status", {
                "company_id": str(company_id),
                "draft": str(counts.get("draft", 0)),
                "pending_review": str(counts.get("pending_review", 0)),
                "published": str(counts.get("published", 0)),
                "archived": str(counts.get("archived", 0)),
            })
        except Exception:
            _logger.debug("cms_pages_by_status gauge update failed", exc_info=True)

        return page

    # ==================== SERIALIZATION ====================

    @staticmethod
    def serialize(page, include_content=False):
        data = {
            "id": page.id,
            "name": page.name,
            "slug": page.slug,
            "status": page.status,
            "title": page.title or None,
            "meta_description": page.meta_description or None,
            "og_title": page.og_title or None,
            "og_description": page.og_description or None,
            "og_image_id": page.og_image_id.id if page.og_image_id else None,
            "canonical_url": page.canonical_url or None,
            "robots_meta": page.robots_meta or None,
            "structured_data": page.structured_data or None,
            "published_at": page.published_at.isoformat() if page.published_at else None,
            "active": page.active,
            "company_id": page.company_id.id,
            "created_at": page.create_date.isoformat() if page.create_date else None,
            "updated_at": page.write_date.isoformat() if page.write_date else None,
        }
        if include_content:
            data["content"] = page.content_ids[0].content if page.content_ids else None
        return data
