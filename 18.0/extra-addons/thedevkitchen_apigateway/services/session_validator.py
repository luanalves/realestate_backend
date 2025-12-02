from datetime import datetime, timedelta
from odoo import fields
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class SessionValidator:

    @staticmethod
    def validate(session_id):
        if not session_id:
            return False, None, 'No session ID provided'

        APISession = request.env['thedevkitchen.api.session'].sudo()
        api_session = APISession.search([
            ('session_id', '=', session_id),
            ('is_active', '=', True)
        ], limit=1)

        if not api_session:
            _logger.warning(f'Invalid session attempt: {session_id[:10]}...')
            return False, None, 'Invalid or expired session'

        api_session.write({
            'last_activity': fields.Datetime.now()
        })

        user = api_session.user_id
        if not user.active:
            api_session.write({'is_active': False})
            _logger.warning(f'Session for inactive user: {user.login}')
            return False, None, 'User inactive'

        _logger.info(f'Valid session for user: {user.login}')
        return True, user, None

    @staticmethod
    def cleanup_expired(days=7):
        cutoff = datetime.now() - timedelta(days=days)
        APISession = request.env['thedevkitchen.api.session'].sudo()

        expired = APISession.search([
            ('last_activity', '<', cutoff),
            ('is_active', '=', True)
        ])

        count = len(expired)
        if count > 0:
            expired.write({'is_active': False})
            _logger.info(f'Cleaned {count} expired sessions')

        return count
