# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EmailLinkSettings(models.Model):
    _name = "thedevkitchen.email.link.settings"
    _description = "Email Link Settings"

    # ==================== CORE FIELDS ====================

    name = fields.Char(
        string="Configuration Name",
        size=100,
        required=True,
        default="Email Link Configuration",
        help="Settings record name",
    )

    invite_link_ttl_hours = fields.Integer(
        string="Invite Link Validity (hours)",
        required=True,
        default=24,
        help="Time-to-live for invite links (1-720 hours)",
    )

    reset_link_ttl_hours = fields.Integer(
        string="Reset Link Validity (hours)",
        required=True,
        default=24,
        help="Time-to-live for password reset links (1-720 hours)",
    )

    frontend_base_url = fields.Char(
        string="Frontend Base URL",
        size=255,
        required=True,
        default="http://localhost:3000",
        help="Frontend base URL for constructing email links",
    )

    max_resend_attempts = fields.Integer(
        string="Max Resend Attempts",
        required=True,
        default=5,
        help="Maximum invite resend attempts per user",
    )

    rate_limit_forgot_per_hour = fields.Integer(
        string="Forgot Password Rate Limit",
        required=True,
        default=3,
        help="Maximum forgot-password requests per email per hour",
    )

    # ==================== PYTHON CONSTRAINTS ====================

    @api.constrains("invite_link_ttl_hours", "reset_link_ttl_hours")
    def _check_link_ttl_positive(self):
        """Validate TTL values are within acceptable range"""
        for record in self:
            if record.invite_link_ttl_hours <= 0 or record.invite_link_ttl_hours > 720:
                raise ValidationError(
                    _("Invite link validity must be between 1 and 720 hours")
                )
            if record.reset_link_ttl_hours <= 0 or record.reset_link_ttl_hours > 720:
                raise ValidationError(
                    _("Reset link validity must be between 1 and 720 hours")
                )

    # ==================== SINGLETON PATTERN ====================

    @api.model
    def get_settings(self):
        settings_model = self.sudo()
        settings = settings_model.search([], limit=1)
        if not settings:
            settings = settings_model.create({"name": "Email Link Configuration"})
        return settings
