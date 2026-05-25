# -*- coding: utf-8 -*-
import json
import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CmsPage(models.Model):
    _name = "thedevkitchen.cms.page"
    _description = "CMS Page"
    _inherit = ["mail.thread"]
    _order = "create_date desc"

    # ==================== CORE FIELDS ====================

    name = fields.Char(
        string="Page Name",
        required=True,
        tracking=True,
    )
    slug = fields.Char(
        string="URL Slug",
        required=True,
        tracking=True,
        help="URL-friendly identifier, e.g. 'about-us'. Must be lowercase with hyphens only.",
    )
    status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("pending_review", "Pending Review"),
            ("published", "Published"),
            ("archived", "Archived"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )

    # ==================== SEO FIELDS ====================

    title = fields.Char(string="SEO Title")
    meta_description = fields.Text(string="Meta Description")
    og_title = fields.Char(string="Open Graph Title")
    og_description = fields.Text(string="Open Graph Description")
    og_image_id = fields.Many2one(
        comodel_name="thedevkitchen.cms.media",
        string="Open Graph Image",
        ondelete="set null",
    )
    canonical_url = fields.Char(string="Canonical URL")
    robots_meta = fields.Selection(
        selection=[
            ("index,follow", "Index, Follow"),
            ("noindex,follow", "No Index, Follow"),
            ("index,nofollow", "Index, No Follow"),
            ("noindex,nofollow", "No Index, No Follow"),
        ],
        string="Robots Meta",
        default="index,follow",
    )
    structured_data = fields.Text(
        string="Structured Data (JSON-LD)",
        help="Valid JSON-LD structured data for SEO.",
    )
    published_at = fields.Datetime(string="Published At", readonly=True)

    # ==================== SYSTEM FIELDS ====================

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    # ==================== BACK-REFERENCES ====================

    content_ids = fields.One2many(
        comodel_name="thedevkitchen.cms.page.content",
        inverse_name="page_id",
        string="Page Content",
    )
    html_content = fields.Html(
        string="HTML Content",
        sanitize=False,
        help="Rich text content for editing in the Odoo admin UI. The API uses the Puck JSON (content_ids).",
    )

    # ==================== SQL CONSTRAINTS ====================

    _sql_constraints = [
        (
            "unique_slug_company",
            "UNIQUE(slug, company_id)",
            "A page with this slug already exists for this company.",
        ),
    ]

    # ==================== PYTHON CONSTRAINTS ====================

    @api.constrains("slug")
    def _check_slug_format(self):
        slug_pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        for rec in self:
            if rec.slug and not slug_pattern.match(rec.slug):
                raise ValidationError(
                    f"Invalid slug format: '{rec.slug}'. "
                    "Use only lowercase letters, digits and hyphens (no leading/trailing hyphens)."
                )

    @api.constrains("structured_data")
    def _check_structured_data_json(self):
        for rec in self:
            if rec.structured_data:
                try:
                    json.loads(rec.structured_data)
                except (ValueError, TypeError):
                    raise ValidationError(
                        "structured_data must be valid JSON."
                    )

    @api.constrains("og_image_id", "company_id")
    def _check_og_image_company(self):
        for rec in self:
            if (
                rec.og_image_id
                and rec.og_image_id.company_id
                and rec.og_image_id.company_id != rec.company_id
            ):
                raise ValidationError(
                    "The Open Graph image must belong to the same company as the page."
                )

    # ==================== STATUS TRANSITIONS ====================

    def action_submit_review(self):
        for rec in self:
            rec.status = "pending_review"

    def action_publish(self):
        for rec in self:
            rec.write({
                "status": "published",
                "published_at": fields.Datetime.now(),
            })

    def action_archive_page(self):
        for rec in self:
            rec.status = "archived"

    def action_reset_draft(self):
        for rec in self:
            rec.status = "draft"
