from odoo import models, fields


class APISession(models.Model):
    _name = 'thedevkitchen.api.session'
    _description = 'API Session Management'
    _order = 'create_date desc'

    session_id = fields.Char(
        string='Session ID',
        required=True,
        index=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        index=True,
        ondelete='cascade',
    )
    ip_address = fields.Char(
        string='IP Address',
    )
    user_agent = fields.Char(
        string='User Agent',
    )
    is_active = fields.Boolean(
        string='Active',
        default=True,
        index=True,
    )
    last_activity = fields.Datetime(
        string='Last Activity',
        default=fields.Datetime.now,
    )
    login_at = fields.Datetime(
        string='Login At',
        default=fields.Datetime.now,
    )
    logout_at = fields.Datetime(
        string='Logout At',
    )
