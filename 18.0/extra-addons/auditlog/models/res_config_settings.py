# Copyright 2015 ABF OSIELL <https://osiell.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    auditlog_auto_log = fields.Boolean(
        string="Auto-create Audit Rules",
        config_parameter="auditlog.auto_log",
        help="Automatically create and subscribe audit rules for all business models. "
        "Technical and system models are excluded by default.",
    )
    
    auditlog_auto_log_read = fields.Boolean(
        string="Auto-log Read Operations",
        config_parameter="auditlog.auto_log_read",
        default=False,
        help="Enable audit logging for read operations. "
        "Warning: This may impact performance on high-traffic models.",
    )
    
    auditlog_auto_log_write = fields.Boolean(
        string="Auto-log Write Operations",
        config_parameter="auditlog.auto_log_write",
        default=True,
        help="Enable audit logging for write operations.",
    )
    
    auditlog_auto_log_create = fields.Boolean(
        string="Auto-log Create Operations",
        config_parameter="auditlog.auto_log_create",
        default=True,
        help="Enable audit logging for create operations.",
    )
    
    auditlog_auto_log_unlink = fields.Boolean(
        string="Auto-log Delete Operations",
        config_parameter="auditlog.auto_log_unlink",
        default=True,
        help="Enable audit logging for delete operations.",
    )
    
    auditlog_excluded_models = fields.Char(
        string="Excluded Model Patterns",
        config_parameter="auditlog.excluded_models",
        default="ir.%,base.%,mail.%,bus.%,web.%,report.%",
        help="Comma-separated list of model patterns to exclude from auto-logging. "
        "Use % as wildcard (e.g., 'ir.%' excludes all ir.* models).",
    )
