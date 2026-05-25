# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CmsMedia(models.Model):
    _name = "thedevkitchen.cms.media"
    _description = "CMS Media"
    _order = "create_date desc"

    # ==================== CORE FIELDS ====================

    name = fields.Char(string="File Name", required=True)
    mime_type = fields.Char(string="MIME Type", required=True)
    media_type = fields.Selection(
        selection=[
            ("image", "Image"),
            ("video", "Video"),
            ("document", "Document"),
        ],
        string="Media Type",
        required=True,
    )
    file_size = fields.Integer(string="File Size (bytes)", required=True)
    url = fields.Char(string="File URL", required=True)
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Attachment",
        required=True,
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
