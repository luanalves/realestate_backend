# -*- coding: utf-8 -*-
import logging
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
    # In Odoo 18/OWL, store=False fields require compute+inverse to be
    # registered in the frontend field registry (fields_get).

    file_upload = fields.Binary(
        string="Upload File",
        compute="_compute_upload_fields",
        inverse="_inverse_upload_fields",
        store=False,
    )
    file_upload_filename = fields.Char(
        string="Upload Filename",
        compute="_compute_upload_fields",
        inverse="_inverse_upload_fields",
        store=False,
    )

    def _compute_upload_fields(self):
        for rec in self:
            rec.file_upload = False
            rec.file_upload_filename = False

    def _inverse_upload_fields(self):
        """Called by the ORM after create/write when file_upload is set via the form.
        Auto-creates ir.attachment and populates all metadata fields."""
        for rec in self:
            if not rec.file_upload:
                continue

            filename = rec.file_upload_filename or "upload"
            file_data = rec.file_upload

            old_attachment = rec.attachment_id
            attachment = self.env["ir.attachment"].sudo().create({
                "name": filename,
                "datas": file_data,
                "public": True,
                "res_model": self._name,
            })

            mime = attachment.mimetype or "application/octet-stream"
            if mime.startswith("image/"):
                media_type = "image"
            elif mime.startswith("video/"):
                media_type = "video"
            else:
                media_type = "document"

            rec.write({
                "attachment_id": attachment.id,
                "name": attachment.name,
                "mime_type": mime,
                "file_size": attachment.file_size or 0,
                "url": f"/web/content/{attachment.id}/{filename}",
                "media_type": media_type,
            })

            if old_attachment:
                try:
                    old_attachment.sudo().unlink()
                except Exception:
                    _logger.warning("Could not delete old CMS Media attachment on re-upload.")

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
