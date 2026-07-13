# -*- coding: utf-8 -*-
import jwt
import time
import logging
import odoo
from odoo import api, models
from odoo.http import request
from odoo.tools import config

_logger = logging.getLogger(__name__)


class IrHttpSessionFingerprint(models.AbstractModel):
    _name = 'ir.http'
    _inherit = 'ir.http'

    # ---------------------------------------------------------------- #
    #  Pure helpers - no dependency on odoo.http.request, so they can  #
    #  be unit-tested with plain arguments and no mocking of framework #
    #  internals (ADR-003 unit-test style).                            #
    # ---------------------------------------------------------------- #

    @api.model
    def _build_fingerprint_components(self, settings, ip=None, user_agent=None,
                                       accept_language=None):
        """Build the fingerprint dict from already-extracted request values."""
        components = {}
        if settings.use_ip_in_fingerprint:
            components['ip'] = ip
        if settings.use_user_agent:
            components['ua'] = user_agent
        if settings.use_accept_language:
            components['lang'] = accept_language
        return components

    @api.model
    def _build_session_token(self, uid, components, secret):
        """Encode a JWT session token."""
        current_time = int(time.time())
        payload = {
            'uid': uid,
            'fingerprint': components,
            'iat': current_time,
            'exp': current_time + 86400,
            'iss': 'odoo-session-security',
        }
        return jwt.encode(payload, secret, algorithm='HS256')

    @api.model
    def _check_session_token(self, stored_token, expected_uid, current_components, secret):
        """Decode and validate a JWT session token. Returns (is_valid, reason)."""
        if not stored_token:
            return False, "Token not found"
        try:
            payload = jwt.decode(stored_token, secret, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return False, "Token expired"
        except jwt.InvalidTokenError as e:
            return False, f"Invalid token: {str(e)}"

        if payload.get('uid') != expected_uid:
            return False, "UID mismatch"

        token_fingerprint = payload.get('fingerprint', {})
        for key, value in current_components.items():
            if token_fingerprint.get(key) != value:
                return False, f"Fingerprint mismatch ({key})"

        return True, "Valid"

    # ---------------------------------------------------------------- #
    #  Thin request-bound wrappers.                                    #
    # ---------------------------------------------------------------- #

    def _generate_fingerprint_components(self):
        try:
            settings = request.env['thedevkitchen.security.settings'].get_settings()
            return self._build_fingerprint_components(
                settings,
                ip=request.httprequest.remote_addr,
                user_agent=request.httprequest.headers.get('User-Agent', ''),
                accept_language=request.httprequest.headers.get('Accept-Language', ''),
            )
        except Exception as e:
            _logger.error(f'Error generating fingerprint components: {e}')
            return {}

    def _generate_session_token(self, uid):
        try:
            components = self._generate_fingerprint_components()

            secret = config.get('database_secret') or config.get('admin_passwd')
            if not secret:
                _logger.error("No secret configured for session tokens (database_secret or admin_passwd required)")
                return None
            token = self._build_session_token(uid, components, secret)

            _logger.info(f"[SESSION TOKEN] Generated for UID {uid}, session {request.session.sid[:16]}...")
            return token
        except Exception as e:
            _logger.error(f'Error generating session token: {e}')
            return None

    def _validate_session_token(self, expected_uid):
        try:
            stored_token = request.session.get('_security_token')

            if not stored_token:
                return False, "Token not found"

            secret = config.get('database_secret') or config.get('admin_passwd')
            if not secret:
                _logger.critical("No secret configured for session token validation (database_secret or admin_passwd required)")
                return False, "Server configuration error: missing secret key"

            current_components = self._generate_fingerprint_components()
            is_valid, reason = self._check_session_token(
                stored_token, expected_uid, current_components, secret
            )

            if not is_valid and reason == "UID mismatch":
                _logger.warning(
                    f"[SESSION HIJACKING DETECTED - UID MISMATCH]\n"
                    f"Session: {request.session.sid[:16]}...\n"
                    f"Expected UID: {expected_uid}"
                )
            elif not is_valid and reason.startswith("Fingerprint mismatch"):
                _logger.warning(
                    f"[SESSION HIJACKING DETECTED - FINGERPRINT MISMATCH]\n"
                    f"Session: {request.session.sid[:16]}...\n"
                    f"UID: {expected_uid}\n"
                    f"Reason: {reason}"
                )

            return is_valid, reason
        except Exception as e:
            _logger.error(f'Error validating session token: {e}')
            return False, f"Validation error: {str(e)}"

    def session_info(self):
        result = super(IrHttpSessionFingerprint, self).session_info()

        uid = result.get('uid')

        if uid:
            # Skip fingerprint validation for API endpoints (already protected by OAuth + Session)
            is_api_endpoint = request.httprequest.path.startswith('/api/v1/')

            if not request.session.get('_security_token'):
                token = self._generate_session_token(uid)
                if token:
                    request.session['_security_token'] = token
                    _logger.info(f"[SESSION TOKEN] Stored new token for UID {uid}")
            elif not is_api_endpoint:
                is_valid, reason = self._validate_session_token(uid)

                if not is_valid:
                    _logger.warning(
                        f"[SESSION INVALIDATED]\n"
                        f"Session: {request.session.sid[:16]}...\n"
                        f"UID: {uid}\n"
                        f"Reason: {reason}"
                    )
                    request.session.logout(keep_db=True)
                    return {
                        'uid': False,
                        'is_admin': False,
                        'is_system': False,
                        'user_context': {},
                        'db': request.session.db,
                        'server_version': odoo.service.common.exp_version()['server_version'],
                        'server_version_info': odoo.service.common.exp_version()['server_version_info'],
                    }

        return result
