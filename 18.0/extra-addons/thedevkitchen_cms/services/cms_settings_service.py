# -*- coding: utf-8 -*-
import logging
import re
from datetime import datetime

_logger = logging.getLogger(__name__)

# ---- CSS injection patterns (service layer — not ORM) ----
_CSS_INJECTION_PATTERNS = [
    re.compile(r"expression\s*\(", re.IGNORECASE),
    re.compile(r"behavior\s*:", re.IGNORECASE),
    re.compile(r"url\s*\(\s*javascript:", re.IGNORECASE),
    re.compile(r"@import", re.IGNORECASE),
    re.compile(r"-moz-binding", re.IGNORECASE),
]

_CSS_MAX_BYTES = 64 * 1024  # 64 KB


def _detect_css_injection(css_text):
    for pattern in _CSS_INJECTION_PATTERNS:
        if pattern.search(css_text):
            return pattern.pattern
    return None


class CmsSettingsService:
    # ==================== GET / CREATE ====================
    @staticmethod
    def get_or_create(env, company_id):
        """Return the singleton CMS settings for the given company_id."""
        return env["thedevkitchen.cms.settings"].get_or_create(env, company_id)

    # ==================== UPDATE ====================

    @staticmethod
    def update_settings(env, vals, company_id, user_role):
        settings = CmsSettingsService.get_or_create(env, company_id)

        # 1. custom_js restricted to owner
        if "custom_js" in vals and user_role != "owner":
            raise ValueError("forbidden")

        # 2. CSS injection check (emit event first, then raise)
        custom_css = vals.get("custom_css")
        if custom_css:
            if len(custom_css.encode("utf-8")) > _CSS_MAX_BYTES:
                raise ValueError("css_too_large")
            matched_pattern = _detect_css_injection(custom_css)
            if matched_pattern:
                # Emit observability event BEFORE raising the error
                try:
                    env["thedevkitchen.observability.event"].sudo().emit(
                        "cms.css_injection_blocked",
                        {
                            "company_id": company_id,
                            "field": "custom_css",
                            "pattern": matched_pattern,
                        },
                    )
                except Exception:
                    _logger.warning(
                        "Could not emit cms.css_injection_blocked event",
                        exc_info=True,
                    )
                raise ValueError("css_injection_detected")

        # 3. Audit fields for custom_js
        if "custom_js" in vals:
            vals["custom_js_last_modified_by"] = env.uid
            vals["custom_js_last_modified_at"] = datetime.utcnow()

        settings.write(vals)
        return settings

    # ==================== SERIALIZATION ====================

    @staticmethod
    def serialize_for_role(settings, user_role):
        data = {
            "id": settings.id,
            "company_slug": settings.company_slug or None,
            "og_default_title": settings.og_default_title or None,
            "og_default_description": settings.og_default_description or None,
            "custom_css": settings.custom_css or None,
            "company_id": settings.company_id.id,
            "created_at": settings.create_date.isoformat() if settings.create_date else None,
            "updated_at": settings.write_date.isoformat() if settings.write_date else None,
        }
        if user_role == "owner":
            data["custom_js"] = settings.custom_js or None
            data["custom_js_last_modified_by"] = (
                settings.custom_js_last_modified_by.id
                if settings.custom_js_last_modified_by
                else None
            )
            data["custom_js_last_modified_at"] = (
                settings.custom_js_last_modified_at.isoformat()
                if settings.custom_js_last_modified_at
                else None
            )
        return data
