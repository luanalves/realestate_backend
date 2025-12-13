from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class CompanyValidator:
    @staticmethod
    def validate_company_ids(company_ids):
        try:
            user = request.env.user
            if not user:
                _logger.error('No user in request context')
                return False, 'User context required'
            
            if user.has_group('base.group_system'):
                return True, None
            
            if not company_ids:
                return False, 'At least one company must be specified'
            
            user_company_ids = set(getattr(user, 'estate_company_ids', []).ids)
            requested_ids = set(company_ids)
            unauthorized = requested_ids - user_company_ids
            
            if unauthorized:
                _logger.warning(
                    f'User {user.login} (id={user.id}) attempted to access '
                    f'unauthorized companies: {list(unauthorized)}. '
                    f'Allowed: {list(user_company_ids)}'
                )
                return False, f'Access denied to companies: {list(unauthorized)}'
            
            return True, None
        except Exception as e:
            _logger.error(f'Error validating company IDs: {e}', exc_info=True)
            return False, 'Company validation error'
    
    @staticmethod
    def get_default_company_id():
        try:
            user = request.env.user
            if not user:
                _logger.error('No user in request context')
                return None
            
            # Check default company first
            default_company = getattr(user, 'estate_default_company_id', None)
            if default_company:
                return default_company.id
            
            # Fallback to first company in list
            company_ids = getattr(user, 'estate_company_ids', [])
            if company_ids:
                return company_ids[0].id
            
            _logger.warning(f'User {user.login} (id={user.id}) has no companies assigned')
            return None
        except Exception as e:
            _logger.error(f'Error getting default company ID: {e}', exc_info=True)
            return None
    
    @staticmethod
    def ensure_company_ids(data):
        try:
            if 'company_ids' not in data:
                default_id = CompanyValidator.get_default_company_id()
                if default_id:
                    data['company_ids'] = [(6, 0, [default_id])]
        except Exception as e:
            _logger.error(f'Error ensuring company IDs: {e}', exc_info=True)
        return data
