# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CmsSettings(models.Model):
    _name = "thedevkitchen.cms.settings"
    _description = "CMS Settings"

    # ==================== CORE FIELDS ====================

    company_slug = fields.Char(
        string="Company Slug",
        help="URL-friendly identifier for this company, used in the public CMS route.",
    )
    og_default_title = fields.Char(string="Default OG Title")
    og_default_description = fields.Text(string="Default OG Description")

    custom_css = fields.Text(string="Custom CSS")
    custom_js = fields.Text(string="Custom JavaScript")
    custom_js_last_modified_by = fields.Many2one(
        comodel_name="res.users",
        string="Custom JS Last Modified By",
        readonly=True,
    )
    custom_js_last_modified_at = fields.Datetime(
        string="Custom JS Last Modified At",
        readonly=True,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    # ==================== SQL CONSTRAINTS ====================

    _sql_constraints = [
        (
            "unique_company",
            "UNIQUE(company_id)",
            "CMS Settings is a singleton — only one record per company is allowed.",
        ),
        (
            "unique_company_slug",
            "UNIQUE(company_slug)",
            "This company slug is already in use by another company.",
        ),
    ]

    # ==================== FORMAT CONSTRAINTS ====================

    @api.constrains("company_slug")
    def _check_company_slug_format(self):
        """Validate company_slug format (lowercase + hyphens only).
        CSS injection is NOT validated here — see cms_settings_service.update_settings().
        """
        slug_pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        for rec in self:
            if rec.company_slug and not slug_pattern.match(rec.company_slug):
                raise ValidationError(
                    f"Invalid company_slug format: '{rec.company_slug}'. "
                    "Use only lowercase letters, digits and hyphens."
                )

    # ==================== SINGLETON HELPER ====================

    @classmethod
    def get_or_create(cls, env, company_id):
        """Return existing singleton for company_id or create a new one."""
        record = env["thedevkitchen.cms.settings"].sudo().search(
            [("company_id", "=", company_id)], limit=1
        )
        if not record:
            record = env["thedevkitchen.cms.settings"].sudo().create(
                {"company_id": company_id}
            )
        return record
