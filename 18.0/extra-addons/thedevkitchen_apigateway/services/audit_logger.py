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

    @staticmethod
    def log_company_isolation_violation(user_id, user_login, unauthorized_companies, endpoint):
        """Log attempts to access data from unauthorized companies."""
        try:
            context = AuditLogger._get_log_context()
            user = request.env.user
            user_companies = user.estate_company_ids.ids if hasattr(user, 'estate_company_ids') else []
            
            request.env['ir.logging'].sudo().create({
                'name': 'security.company_isolation.violation',
                'type': 'server',
                'level': 'WARNING',
                'path': endpoint,
                'func': context['func'],
                'line': context['line'],
                'message': (
                    f'Company isolation violation: User {user_login} (ID: {user_id}) '
                    f'attempted to access unauthorized companies {unauthorized_companies}. '
                    f'User authorized companies: {user_companies}'
                ),
            })
            _logger.warning(
                f'[SECURITY] Company isolation violation by user {user_login} (ID: {user_id}): '
                f'Attempted companies={unauthorized_companies}, Authorized={user_companies}, '
                f'Endpoint={endpoint}'
            )
        except Exception as e:
            _logger.error(f'Failed to log company isolation violation: {str(e)}')

    @staticmethod
    def log_unauthorized_record_access(user_id, user_login, record_model, record_id, endpoint):
        """Log attempts to access specific records from unauthorized companies (404 responses)."""
        try:
            context = AuditLogger._get_log_context()
            request.env['ir.logging'].sudo().create({
                'name': 'security.unauthorized_record_access',
                'type': 'server',
                'level': 'WARNING',
                'path': endpoint,
                'func': context['func'],
                'line': context['line'],
                'message': (
                    f'Unauthorized record access: User {user_login} (ID: {user_id}) '
                    f'attempted to access {record_model} ID {record_id} via {endpoint}'
                ),
            })
            _logger.info(
                f'[SECURITY] Unauthorized record access attempt: User={user_login} (ID={user_id}), '
                f'Model={record_model}, RecordID={record_id}, Endpoint={endpoint}'
            )
        except Exception as e:
            _logger.error(f'Failed to log unauthorized record access: {str(e)}')
