# -*- coding: utf-8 -*-
from odoo import models, fields


class CmsTemplateContent(models.Model):
    _name = "thedevkitchen.cms.template.content"
    _description = "CMS Template Content"

    # ==================== CORE FIELDS ====================

    template_id = fields.Many2one(
        comodel_name="thedevkitchen.cms.template",
        string="Template",
        required=True,
        ondelete="cascade",
        index=True,
    )
    content = fields.Text(
        string="Content (Puck JSON)",
        help="Puck editor JSON payload for this template.",
    )

    # ==================== SQL CONSTRAINTS ====================

    _sql_constraints = [
        (
            "unique_template",
            "UNIQUE(template_id)",
            "A template can have only one content record (1:1 relationship).",
        ),
    ]
