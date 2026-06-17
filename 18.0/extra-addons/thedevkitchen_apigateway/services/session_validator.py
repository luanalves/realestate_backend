from datetime import datetime, timedelta
from odoo import fields
import logging

_logger = logging.getLogger(__name__)

try:
    from .redis_client import RedisClient
except ImportError:
    RedisClient = None


class SessionValidator:

    @staticmethod
    def validate(session_id, env=None):
        if not session_id:
            return False, None, None, 'No session ID provided'

        if env is None:
            from odoo.http import request
            env = request.env

        # --- Redis cache HIT path ---
        if RedisClient:
            cache_key = RedisClient.session_key(session_id)
            cached = RedisClient.get_json(cache_key)
            if cached:
                try:
                    if not cached.get('is_active'):
                        _logger.warning('[CACHE] session HIT inactive session:%s...', session_id[:10])
                        return False, None, None, 'Invalid or expired session'
                    if not cached.get('user_active'):
                        _logger.warning('[CACHE] session HIT inactive user session:%s...', session_id[:10])
                        return False, None, None, 'User inactive'
                    # Reject malformed payloads — missing security_token means we'd inject
                    # None into ORM cache, causing require_session to 401 on a valid session.
                    if not cached.get('security_token'):
                        raise KeyError('security_token missing or empty in cached payload')
                    # Lazy ORM records — zero SELECT via Odoo 18 field cache injection
                    APISession = env['thedevkitchen.api.session'].sudo()
                    Users = env['res.users'].sudo()
                    api_session = APISession.browse(cached['id'])
                    user = Users.browse(cached['user_id'])
                    try:
                        env.cache.set(api_session, APISession._fields['security_token'], cached.get('security_token'))
                        env.cache.set(api_session, APISession._fields['is_active'], True)
                        if cached.get('company_id') and 'company_id' in APISession._fields:
                            env.cache.set(api_session, APISession._fields['company_id'], cached.get('company_id'))
                        env.cache.set(user, Users._fields['active'], True)
                    except Exception:
                        pass  # Field cache injection is best-effort
                    _logger.info('[CACHE] session HIT session:%s...', session_id[:10])
                    return True, user, api_session, None
                except (KeyError, TypeError) as exc:
                    _logger.warning('[CACHE] session HIT malformed payload, falling back to DB: %s', exc)
            _logger.warning('[CACHE] session MISS session:%s...', session_id[:10])

        # --- Database path (MISS or Redis unavailable) ---
        APISession = env['thedevkitchen.api.session'].sudo()
        api_session = APISession.search([
            ('session_id', '=', session_id),
            ('is_active', '=', True)
        ], limit=1)

        if not api_session:
            _logger.warning(f'Invalid session attempt: {session_id[:10]}...')
            return False, None, None, 'Invalid or expired session'

        api_session.write({
            'last_activity': fields.Datetime.now()
        })

        user = api_session.user_id
        if not user.active:
            api_session.write({'is_active': False})
            _logger.warning(f'Session for inactive user: {user.login}')
            return False, None, None, 'User inactive'

        _logger.info(f'Valid session for user: {user.login}')

        # --- Populate Redis cache on MISS ---
        if RedisClient:
            try:
                settings = env['thedevkitchen.security.settings'].sudo().get_settings()
                ttl = settings.session_cache_ttl_seconds if settings else 300
            except Exception:
                ttl = 300
            RedisClient.set_json(
                RedisClient.session_key(session_id),
                {
                    'id': api_session.id,
                    'user_id': user.id,
                    'is_active': True,
                    'security_token': api_session.security_token,
                    'company_id': api_session.company_id.id if api_session.company_id else None,
                    'user_active': True,
                },
                ttl,
            )

        return True, user, api_session, None

    @staticmethod
    def cleanup_expired(env=None, days=None):
        if env is None:
            from odoo.http import request
            env = request.env

        if days is None:
            try:
                settings = env['thedevkitchen.security.settings'].sudo().get_settings()
                days = settings.session_inactivity_days or 7
            except Exception:
                days = 7

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
