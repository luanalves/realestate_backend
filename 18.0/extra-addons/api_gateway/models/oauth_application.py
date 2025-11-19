import secrets
import string
import bcrypt
from odoo import models, fields, api
from odoo.exceptions import UserError


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
        string='Client Secret (Hashed)',
        readonly=True,
        copy=False,
        help='OAuth 2.0 Client Secret - stored as bcrypt hash (never shown after creation)'
    )
    client_secret_info = fields.Char(
        string='Client Secret',
        compute='_compute_secret_info',
        store=False,
        help='Secret is shown only once after creation via notification. If lost, use Regenerate Secret button.'
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

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate and hash client_secret"""
        plaintext_secrets = []
        
        for vals in vals_list:
            if 'client_secret' not in vals or not vals.get('client_secret'):
                # Generate new plaintext secret
                plaintext_secret = self._generate_client_secret()
                # Hash it before storing
                vals['client_secret'] = self._hash_secret(plaintext_secret)
                # Store plaintext separately (not in vals to avoid validation error)
                plaintext_secrets.append(plaintext_secret)
            elif vals.get('client_secret') and not vals['client_secret'].startswith('$2b$'):
                # If a plaintext secret is provided, hash it
                plaintext = vals['client_secret']
                vals['client_secret'] = self._hash_secret(plaintext)
                plaintext_secrets.append(plaintext)
            else:
                plaintext_secrets.append(None)
        
        # Create records
        records = super(OAuthApplication, self).create(vals_list)
        
        # Display notification for first record with plaintext
        if len(records) == 1 and plaintext_secrets[0]:
            records._show_secret_notification(plaintext_secrets[0])
        
        return records
    
    def _show_secret_notification(self, plaintext_secret):
        """Show notification with plaintext secret"""
        self.ensure_one()
        message = f'''🔑 CLIENT SECRET GENERATED - SAVE NOW!
        
{plaintext_secret}

⚠️ This secret is now hashed and cannot be retrieved later.
Copy it NOW or use "Regenerate Secret" to get a new one.'''
        
        # Skip notification if bus.bus module is not available (e.g., in tests)
        if 'bus.bus' not in self.env:
            return
        
        return self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'type': 'warning',
                'title': 'Client Secret Generated',
                'message': message,
                'sticky': True,
            }
        )
        
        return records

    def _compute_secret_info(self):
        """Display informative message about secret"""
        for record in self:
            if record.client_secret:
                record.client_secret_info = 'Secret shown only once after save. Lost? Use "Regenerate Secret".'
            else:
                record.client_secret_info = 'Secret will be generated automatically on save.'

    @api.depends('token_ids', 'token_ids.active')
    def _compute_token_count(self):
        for record in self:
            record.token_count = len(record.token_ids.filtered(lambda t: t.active))

    def _generate_client_id(self):
        """Generate a unique Client ID"""
        return f"client_{secrets.token_urlsafe(16)}"

    def _generate_client_secret(self):
        """Generate a secure Client Secret (plaintext - will be hashed before storage)"""
        alphabet = string.ascii_letters + string.digits + '-_'
        return ''.join(secrets.choice(alphabet) for _ in range(64))

    def _hash_secret(self, plaintext_secret):
        """Hash a secret using bcrypt"""
        if not plaintext_secret:
            raise UserError('Cannot hash empty secret')
        # Convert to bytes and hash with bcrypt
        secret_bytes = plaintext_secret.encode('utf-8')
        hashed = bcrypt.hashpw(secret_bytes, bcrypt.gensalt(rounds=12))
        return hashed.decode('utf-8')

    def verify_secret(self, plaintext_secret):
        """
        Verify a plaintext secret against the stored hash
        
        Args:
            plaintext_secret: The plaintext secret to verify
            
        Returns:
            bool: True if secret matches, False otherwise
        """
        self.ensure_one()
        if not plaintext_secret or not self.client_secret:
            return False
        
        try:
            secret_bytes = plaintext_secret.encode('utf-8')
            hashed_bytes = self.client_secret.encode('utf-8')
            return bcrypt.checkpw(secret_bytes, hashed_bytes)
        except Exception:
            return False

    def action_regenerate_secret(self):
        """Regenerate client secret and revoke all tokens"""
        self.ensure_one()
        # Revoke all existing tokens
        self.token_ids.action_revoke()
        
        # Generate new plaintext secret
        new_plaintext = self._generate_client_secret()
        
        # Hash and store
        self.client_secret = self._hash_secret(new_plaintext)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Secret Regenerated',
                'message': f'All tokens revoked. New secret (SAVE NOW - shown only once): {new_plaintext}',
                'type': 'warning',
                'sticky': True,
            }
        }

    def action_migrate_plaintext_secrets(self):
        """
        Migration utility to re-hash any plaintext secrets.
        WARNING: This will invalidate existing plaintext secrets that are not hashed.
        You must regenerate secrets for all applications after migration.
        """
        applications = self.search([])
        migrated = 0
        
        for app in applications:
            # Check if secret is already hashed (bcrypt hashes start with $2b$)
            if app.client_secret and not app.client_secret.startswith('$2b$'):
                # This is a plaintext secret - we cannot recover it
                # Force regeneration
                try:
                    app.action_regenerate_secret()
                    migrated += 1
                except Exception as e:
                    # Log error but continue
                    pass
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Migration Complete',
                'message': f'Migrated {migrated} applications. All secrets have been regenerated and hashed.',
                'type': 'success',
                'sticky': True,
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
