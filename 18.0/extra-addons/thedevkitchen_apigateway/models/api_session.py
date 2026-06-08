from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

try:
    from ..services.redis_client import RedisClient
except ImportError:
    RedisClient = None


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
    security_token = fields.Text(
        string='Security Token (JWT)',
        help='JWT token for session security and hijacking prevention',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Active Company',
        ondelete='set null',
        index=True,
        help='The real estate company context for this session. '
             'Set automatically at login from the user\'s first real estate company. '
             'Updated via POST /api/v1/users/switch-company.',
    )

    def write(self, vals):
        """Override: invalidate Redis cache when session state or company changes."""
        if RedisClient and ('is_active' in vals or 'company_id' in vals):
            for record in self:
                if record.session_id:
                    try:
                        key = RedisClient.session_key(record.session_id)
                        RedisClient.delete(key)
                        _logger.info('[CACHE] session invalidated session:%s...', record.session_id[:10])
                    except Exception as exc:
                        _logger.warning('[CACHE] session invalidation failed: %s', exc)
        return super().write(vals)
