# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SecuritySettings(models.Model):
    _name = 'thedevkitchen.security.settings'
    _description = 'Security Settings for Session Fingerprint'
    
    name = fields.Char(
        string='Configuration Name',
        default='Security Configuration',
        readonly=True,
    )
    
    use_ip_in_fingerprint = fields.Boolean(
        string='Validate IP Address',
        default=True,
        help='Include IP in fingerprint. Disable if users have dynamic IPs (VPN/mobile).'
    )
    
    use_user_agent = fields.Boolean(
        string='Validate Browser (User-Agent)',
        default=True,
        help='Include browser information in fingerprint.'
    )
    
    use_accept_language = fields.Boolean(
        string='Validate Browser Language',
        default=True,
        help='Include browser language in fingerprint.'
    )
    
    @api.model
    def get_settings(self):
        settings = self.sudo().search([], limit=1)
        if not settings:
            _logger.info('Creating default security settings')
            settings = self.sudo().create({'name': 'Security Configuration'})
        return settings
