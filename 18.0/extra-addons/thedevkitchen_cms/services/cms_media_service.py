# -*- coding: utf-8 -*-
import base64
import logging
import os
import re

_logger = logging.getLogger(__name__)


def _emit(event_name, attributes=None):
    """Emit an OpenTelemetry span event, silently ignoring unavailability."""
    try:
        from odoo.addons.thedevkitchen_observability.services.tracer import add_span_event
        add_span_event(event_name, attributes or {})
    except Exception:
        _logger.debug("Observability not available — event %s not emitted", event_name)

# ==================== WHITELISTS ====================

ALLOWED_MIMES = {
    "image": {"image/jpeg", "image/png", "image/gif", "image/webp"},
    "video": {"video/mp4", "video/webm"},
    "document": {"application/pdf", "text/plain"},
}

# Reverse lookup: mime → media_type
MEDIA_TYPE_BY_MIME = {
    mime: mtype
    for mtype, mimes in ALLOWED_MIMES.items()
    for mime in mimes
}

SIZE_LIMITS = {
    "image": 10 * 1024 * 1024,     # 10 MB
    "video": 100 * 1024 * 1024,    # 100 MB
    "document": 20 * 1024 * 1024,  # 20 MB
}


class CmsMediaService:
    """Business logic for media upload, validation, and storage."""

    # ==================== VALIDATE ====================

    @staticmethod
    def validate_upload(file_bytes, filename, claimed_mime=None):
        try:
            import magic
            detected_mime = magic.from_buffer(file_bytes[:2048], mime=True)
        except ImportError as exc:
            raise RuntimeError(
                "python-magic is required for file upload validation but is not installed. "
                "Run: pip install python-magic"
            ) from exc

        # 1. Whitelist check
        media_type = MEDIA_TYPE_BY_MIME.get(detected_mime)
        if not media_type:
            raise ValueError(f"unsupported_mime|{detected_mime}")

        # 2. Magic bytes must match claimed MIME
        if claimed_mime and claimed_mime != detected_mime:
            raise ValueError(f"mime_mismatch|{claimed_mime}|{detected_mime}")

        # 3. Size limit
        size = len(file_bytes)
        limit = SIZE_LIMITS[media_type]
        if size > limit:
            raise ValueError(f"file_too_large|{limit}|{size}")

        # 4. Sanitize filename (prevent path traversal)
        safe_name = os.path.basename(filename)
        safe_name = re.sub(r"[^\w.\-]", "_", safe_name)
        if not safe_name:
            safe_name = "upload"

        return {
            "media_type": media_type,
            "detected_mime": detected_mime,
            "filename": safe_name,
            "size": size,
        }

    # ==================== UPLOAD ====================

    @staticmethod
    def upload(env, file_bytes, filename, claimed_mime, company_id):
        info = CmsMediaService.validate_upload(file_bytes, filename, claimed_mime)

        # Store binary in ir.attachment (private by default — served via CMS API)
        attachment = env["ir.attachment"].sudo().create({
            "name": info["filename"],
            "datas": base64.b64encode(file_bytes).decode("utf-8"),
            "mimetype": info["detected_mime"],
            "res_model": "thedevkitchen.cms.media",
            "company_id": company_id,
        })

        media = env["thedevkitchen.cms.media"].sudo().create({
            "name": info["filename"],
            "mime_type": info["detected_mime"],
            "media_type": info["media_type"],
            "file_size": info["size"],
            "attachment_id": attachment.id,
            "company_id": company_id,
        })

        # Use stable API URL (enforces JWT + company auth, avoids /web/content/ bypass)
        media.sudo().write({"url": f"/api/v1/cms/media/{media.id}/file"})
        attachment.sudo().write({"res_id": media.id})

        # T042: increment counter cms_media_uploads_total
        _emit("cms_media_uploads_total", {
            "company_id": str(company_id),
            "mime_type": info["detected_mime"],
            "type": info["media_type"],
            "size": str(info["size"]),
        })

        return media

    # ==================== SERIALIZATION ====================

    @staticmethod
    def serialize(media):
        return {
            "id": media.id,
            "name": media.name,
            "mime_type": media.mime_type,
            "media_type": media.media_type,
            "file_size": media.file_size,
            "url": media.url,
            "company_id": media.company_id.id,
            "created_at": media.create_date.isoformat() if media.create_date else None,
            "updated_at": media.write_date.isoformat() if media.write_date else None,
        }
