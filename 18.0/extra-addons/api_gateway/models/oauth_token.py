import secrets
from datetime import datetime, timedelta
from odoo import models, fields, api


class OAuthToken(models.Model):
    _name = 'oauth.token'
    _description = 'OAuth 2.0 Token'
    _order = 'create_date desc'

    application_id = fields.Many2one(
        'oauth.application',
        string='Application',
        required=True,
        ondelete='cascade',
        help='OAuth application that owns this token'
    )
    access_token = fields.Char(
        string='Access Token',
        required=True,
        readonly=True,
        index=True,
        help='JWT access token'
    )
    refresh_token = fields.Char(
        string='Refresh Token',
        readonly=True,
        index=True,
        help='Token used to refresh the access token'
    )
    token_type = fields.Char(
        string='Token Type',
        default='Bearer',
        readonly=True,
        help='Type of token (always Bearer for OAuth 2.0)'
    )
    expires_at = fields.Datetime(
        string='Expires At',
        readonly=True,
        default=lambda self: datetime.now() + timedelta(hours=1),
        help='When the access token expires (default: 1 hour)'
    )
    scope = fields.Char(
        string='Scope',
        help='Token scope/permissions'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether the token is still valid'
    )
    revoked = fields.Boolean(
        string='Revoked',
        default=False,
        readonly=True,
        help='Whether the token has been revoked'
    )
    revoked_at = fields.Datetime(
        string='Revoked At',
        readonly=True,
        help='When the token was revoked'
    )
    last_used = fields.Datetime(
        string='Last Used',
        readonly=True,
        help='Last time this token was used'
    )
    is_expired = fields.Boolean(
        string='Expired',
        compute='_compute_is_expired',
        store=True,
        help='Whether the token has expired'
    )

    _sql_constraints = [
        ('access_token_unique', 'unique(access_token)', 'Access token must be unique!'),
    ]

    @api.depends('expires_at')
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_expired = record.expires_at < now if record.expires_at else False

    def action_revoke(self):
        """Revoke the token"""
        for record in self:
            record.write({
                'active': False,
                'revoked': True,
                'revoked_at': fields.Datetime.now(),
            })
        return True

    @api.model
    def cleanup_expired_tokens(self):
        """Cron job to cleanup expired tokens"""
        expired_tokens = self.search([
            ('expires_at', '<', fields.Datetime.now()),
            ('active', '=', True),
        ])
        expired_tokens.write({'active': False})
        return True

    def update_last_used(self):
        """Update last used timestamp"""
        self.ensure_one()
        self.sudo().write({'last_used': fields.Datetime.now()})
