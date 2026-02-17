# -*- coding: utf-8 -*-
"""
Password Token Model

Stores hashed tokens for invite and password reset flows with SHA-256 hashing.
Tokens are never stored in plain text for security.

Author: TheDevKitchen
Date: 2026-02-16
ADRs: ADR-004 (Naming), ADR-008 (Anti-enumeration), ADR-015 (Soft Delete)
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PasswordToken(models.Model):
    _name = "thedevkitchen.password.token"
    _description = "Password Token"
    _order = "create_date desc"

    # ==================== CORE FIELDS ====================

    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        ondelete="cascade",
        index=True,
        help="User associated with this token",
    )

    token = fields.Char(
        string="Token Hash",
        size=64,
        required=True,
        index=True,
        help="SHA-256 hash of the raw token (64 hex characters)",
    )

    token_type = fields.Selection(
        [
            ("invite", "Invite"),
            ("reset", "Reset"),
        ],
        string="Token Type",
        required=True,
        help="Type of token: invite (first password) or reset (forgot password)",
    )

    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("used", "Used"),
            ("expired", "Expired"),
            ("invalidated", "Invalidated"),
        ],
        string="Status",
        required=True,
        default="pending",
        help="Token lifecycle status",
    )

    expires_at = fields.Datetime(
        string="Expires At", required=True, help="Token expiration timestamp"
    )

    used_at = fields.Datetime(string="Used At", help="When the token was consumed")

    ip_address = fields.Char(
        string="IP Address",
        size=45,  # IPv6 max length
        help="IP address used for token consumption (audit trail)",
    )

    user_agent = fields.Char(
        string="User Agent",
        size=255,
        help="Browser User Agent at consumption (audit trail)",
    )

    company_id = fields.Many2one(
        "thedevkitchen.estate.company",
        string="Company",
        index=True,
        help="Company context for multi-tenancy",
    )

    created_by = fields.Many2one(
        "res.users",
        string="Created By",
        help="Who created this invite token (audit trail)",
    )

    active = fields.Boolean(
        string="Active", default=True, help="Soft delete flag (ADR-015)"
    )

    # ==================== SQL CONSTRAINTS ====================

    _sql_constraints = [
        ("token_unique", "unique(token)", "Token must be unique"),
    ]

    # ==================== PYTHON CONSTRAINTS ====================

    @api.constrains("expires_at")
    def _check_expires_at(self):
        """Ensure expiration date is in the future"""
        for record in self:
            if record.expires_at and record.expires_at <= fields.Datetime.now():
                raise ValidationError(_("Expiration date must be in the future"))

    # ==================== INDEXES ====================

    def init(self):
        """Create composite index for fast token invalidation queries"""
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_password_token_user_type_status 
            ON thedevkitchen_password_token (user_id, token_type, status)
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_password_token_expires_at 
            ON thedevkitchen_password_token (expires_at)
        """)

    # ==================== CRON METHODS ====================

    @api.model
    def _cron_cleanup_expired_tokens(self):
        """
        Cron job to mark expired tokens.
        Called daily by ir.cron record.
        """
        now = fields.Datetime.now()
        expired_tokens = self.search(
            [
                ("status", "=", "pending"),
                ("expires_at", "<", now),
            ]
        )
        if expired_tokens:
            expired_tokens.write({"status": "expired"})
        return True
