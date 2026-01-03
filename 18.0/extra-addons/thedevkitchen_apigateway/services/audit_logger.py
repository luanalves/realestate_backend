from odoo.http import request
import logging
import traceback
import inspect

_logger = logging.getLogger(__name__)


class AuditLogger:

    @staticmethod
    def _get_log_context():
        frame = inspect.currentframe().f_back.f_back
        return {
            'func': frame.f_code.co_name,
            'line': frame.f_lineno,
        }

    @staticmethod
    def log_failed_login(ip, email, reason='Invalid credentials'):
        try:
            context = AuditLogger._get_log_context()
            request.env['ir.logging'].sudo().create({
                'name': 'auth.login.failed',
                'type': 'server',
                'level': 'WARNING',
                'path': '/api/v1/users/login',
                'func': context['func'],
                'line': context['line'],
                'message': f'Failed login: {email} from {ip} - {reason}',
            })
        except Exception as e:
            _logger.error(f'Failed to log login attempt: {str(e)}')

    @staticmethod
    def log_successful_login(ip, email, user_id):
        try:
            context = AuditLogger._get_log_context()
            request.env['ir.logging'].sudo().create({
                'name': 'auth.login.success',
                'type': 'server',
                'level': 'INFO',
                'path': '/api/v1/users/login',
                'func': context['func'],
                'line': context['line'],
                'message': f'Successful login: {email} (ID: {user_id}) from {ip}',
            })
        except Exception as e:
            _logger.error(f'Failed to log successful login: {str(e)}')

    @staticmethod
    def log_logout(ip, email, user_id):
        try:
            context = AuditLogger._get_log_context()
            request.env['ir.logging'].sudo().create({
                'name': 'auth.logout',
                'type': 'server',
                'level': 'INFO',
                'path': '/api/v1/users/logout',
                'func': context['func'],
                'line': context['line'],
                'message': f'User logout: {email} (ID: {user_id}) from {ip}',
            })
        except Exception as e:
            _logger.error(f'Failed to log logout: {str(e)}')

    @staticmethod
    def log_error(context, email, error):
        try:
            frame_context = AuditLogger._get_log_context()
            request.env['ir.logging'].sudo().create({
                'name': f'{context}.error',
                'type': 'server',
                'level': 'ERROR',
                'path': '/api/v1/users/login',
                'func': frame_context['func'],
                'line': frame_context['line'],
                'message': f'Error for {email}: {error}',
            })
        except Exception as e:
            _logger.error(f'Failed to log error: {str(e)}')
