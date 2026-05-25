# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

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

    # ==================== UPLOAD FIELDS (non-stored, admin UI only) ====================

    file_upload = fields.Binary(string="Upload File", store=False)
    file_upload_filename = fields.Char(string="Upload Filename", store=False)

    # ==================== VALIDATION ====================

    @api.constrains("attachment_id")
    def _check_attachment_required(self):
        for rec in self:
            if not rec.attachment_id:
                raise ValidationError(_("An uploaded file is required. Please upload a file."))

    # ==================== UPLOAD LOGIC ====================

    def _process_file_upload(self, vals):
        """Auto-create ir.attachment from file_upload binary and populate all metadata."""
        file_data = vals.pop("file_upload", None)
        filename = vals.pop("file_upload_filename", None) or "upload"
        if not file_data:
            return

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

        vals.update({
            "attachment_id": attachment.id,
            "name": attachment.name,
            "mime_type": mime,
            "file_size": attachment.file_size or 0,
            "url": f"/web/content/{attachment.id}/{filename}",
            "media_type": media_type,
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._process_file_upload(vals)
        return super().create(vals_list)

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
