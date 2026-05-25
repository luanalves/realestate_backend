# -*- coding: utf-8 -*-
from odoo import models, fields


class CmsPageContent(models.Model):
    _name = "thedevkitchen.cms.page.content"
    _description = "CMS Page Content"

    # ==================== CORE FIELDS ====================

    page_id = fields.Many2one(
        comodel_name="thedevkitchen.cms.page",
        string="Page",
        required=True,
        ondelete="cascade",
        index=True,
    )
    content = fields.Text(
        string="Content (Puck JSON)",
        help="Puck editor JSON payload. Validated for size (≤512KB) in the service layer.",
    )

    # ==================== SQL CONSTRAINTS ====================

    _sql_constraints = [
        (
            "unique_page",
            "UNIQUE(page_id)",
            "A page can have only one content record (1:1 relationship).",
        ),
    ]
