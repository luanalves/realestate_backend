from datetime import datetime, timedelta
from odoo import fields
import logging

_logger = logging.getLogger(__name__)


class SessionValidator:

    @staticmethod
    def validate(session_id, env=None):
        if not session_id:
            return False, None, 'No session ID provided'

        if env is None:
            from odoo.http import request
            env = request.env

        APISession = env['thedevkitchen.api.session'].sudo()
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
    def cleanup_expired(env=None, days=7):
        if env is None:
            from odoo.http import request
            env = request.env

        cutoff = datetime.now() - timedelta(days=days)
        APISession = env['thedevkitchen.api.session'].sudo()

        expired = APISession.search([
            ('last_activity', '<', cutoff),
            ('is_active', '=', True)
        ])

        count = len(expired)
        if count > 0:
            expired.write({'is_active': False})
            _logger.info(f'Cleaned {count} expired sessions')

        return count
