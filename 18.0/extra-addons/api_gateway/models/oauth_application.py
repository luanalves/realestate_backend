import secrets
import string
from odoo import models, fields, api


class OAuthApplication(models.Model):
    _name = 'oauth.application'
    _description = 'OAuth 2.0 Application'
    _order = 'name'

    name = fields.Char(
        string='Application Name',
        default='OAuth Application',
        help='Name of the OAuth application'
    )
    client_id = fields.Char(
        string='Client ID',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: self._generate_client_id(),
        help='OAuth 2.0 Client ID (public identifier)'
    )
    client_secret = fields.Char(
        string='Client Secret',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: self._generate_client_secret(),
        help='OAuth 2.0 Client Secret (keep this secure!)'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Disable to revoke all tokens and prevent new ones'
    )
    description = fields.Text(
        string='Description',
        help='Description of the application purpose'
    )
    token_ids = fields.One2many(
        'oauth.token',
        'application_id',
        string='Tokens',
        help='All tokens issued for this application'
    )
    token_count = fields.Integer(
        string='Active Tokens',
        compute='_compute_token_count',
        store=False,
        help='Number of active tokens'
    )
    created_date = fields.Datetime(
        string='Created On',
        default=fields.Datetime.now,
        readonly=True
    )

    _sql_constraints = [
        ('client_id_unique', 'unique(client_id)', 'Client ID must be unique!'),
    ]

    @api.depends('token_ids', 'token_ids.active')
    def _compute_token_count(self):
        for record in self:
            record.token_count = len(record.token_ids.filtered(lambda t: t.active))

    def _generate_client_id(self):
        """Generate a unique Client ID"""
        return f"client_{secrets.token_urlsafe(16)}"

    def _generate_client_secret(self):
        """Generate a secure Client Secret"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(64))

    def action_regenerate_secret(self):
        """Regenerate client secret and revoke all tokens"""
        self.ensure_one()
        # Revoke all existing tokens
        self.token_ids.action_revoke()
        # Generate new secret
        self.client_secret = self._generate_client_secret()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Secret Regenerated',
                'message': 'All existing tokens have been revoked. New secret generated.',
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_view_tokens(self):
        """View all tokens for this application"""
        self.ensure_one()
        return {
            'name': f'Tokens - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'oauth.token',
            'view_mode': 'list,form',
            'domain': [('application_id', '=', self.id)],
            'context': {'default_application_id': self.id},
        }
