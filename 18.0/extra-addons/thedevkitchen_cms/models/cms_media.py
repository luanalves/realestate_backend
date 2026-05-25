# -*- coding: utf-8 -*-
import logging
import os
import re
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CmsMedia(models.Model):
    _name = "thedevkitchen.cms.media"
    _description = "CMS Media"
    _order = "create_date desc"

    # ==================== CORE FIELDS (auto-populated from upload) ====================

    name = fields.Char(string="File Name")
    mime_type = fields.Char(string="MIME Type")
    media_type = fields.Selection(
        selection=[
            ("image", "Image"),
            ("video", "Video"),
            ("document", "Document"),
        ],
        string="Media Type",
    )
    file_size = fields.Integer(string="File Size (bytes)", default=0)
    url = fields.Char(string="File URL")
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Attachment",
        ondelete="restrict",
    )
    image_1920 = fields.Binary(
        string="Image Preview",
        related="attachment_id.datas",
        readonly=True,
        help="Binary preview loaded from the linked attachment. Available for images.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    # ==================== UPLOAD FIELDS ====================
    # Stored as regular fields so Odoo 18 OWL registers them in fields_get().
    # Values are consumed and cleared in create()/write() — DB columns stay NULL.

    file_upload = fields.Binary(string="Upload File")
    file_upload_filename = fields.Char(string="Upload Filename")

    # ==================== UPLOAD LOGIC ====================

    def _process_file_upload(self, vals):
        """Consume file_upload binary, create ir.attachment, and populate all
        metadata fields in vals. Pops file_upload so the stored column stays NULL."""
        file_data = vals.pop("file_upload", None)
        raw_filename = vals.pop("file_upload_filename", None) or "upload"
        # Sanitize: strip directory traversal, then keep only safe characters
        filename = os.path.basename(raw_filename)
        filename = re.sub(r"[^\w.\-]", "_", filename) or "upload"
        if not file_data:
            return

        # Respect company_id from vals if provided (multi-company safety)
        company_id = vals.get("company_id") or self.env.company.id
        attachment = self.env["ir.attachment"].sudo().create({
            "name": filename,
            "datas": file_data,
            "res_model": self._name,
            "company_id": company_id,
            # public=False (default) — files served via CMS API (JWT + company)
        })

        mime = attachment.mimetype or "application/octet-stream"
        if mime.startswith("image/"):
            media_type = "image"
        elif mime.startswith("video/"):
            media_type = "video"
        else:
            media_type = "document"

        vals.update({
            "attachment_id": attachment.id,
            "name": attachment.name,
            "mime_type": mime,
            "file_size": attachment.file_size or 0,
            # URL set to empty; updated after record creation with stable API route
            "url": "",
            "media_type": media_type,
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._process_file_upload(vals)
        records = super().create(vals_list)
        # Set stable API URL and link attachment to record for traceability
        for record in records:
            if record.attachment_id:
                record.attachment_id.sudo().write({"res_id": record.id})
                record.url = f"/api/v1/cms/media/{record.id}/file"
        return records

    def write(self, vals):
        file_data = vals.get("file_upload")
        if file_data and len(self) == 1:
            old_attachment = self.attachment_id
            self._process_file_upload(vals)
            res = super().write(vals)
            if old_attachment:
                try:
                    old_attachment.sudo().unlink()
                except Exception:
                    _logger.warning("Could not delete old CMS Media attachment on re-upload.")
            return res
        # No file upload — remove transient keys if present
        vals.pop("file_upload", None)
        vals.pop("file_upload_filename", None)
        return super().write(vals)

    def unlink(self):
        attachment_ids = self.mapped("attachment_id")
        result = super().unlink()
        if attachment_ids:
            try:
                attachment_ids.sudo().unlink()
            except Exception:
                _logger.warning(
                    "Could not delete ir.attachment records for CMS media. "
                    "Manual cleanup may be required."
                )
        return result
