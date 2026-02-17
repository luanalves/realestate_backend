# -*- coding: utf-8 -*-
"""
res.users Extension

Adds signup_pending field to track invite status.
Coexists with quicksol_estate extension of res.users.

Author: TheDevKitchen
Date: 2026-02-16
ADRs: ADR-004 (Naming)
"""

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    signup_pending = fields.Boolean(
        string='Signup Pending',
        default=False,
        help='Indicates user is waiting to create their password via invite link'
    )
