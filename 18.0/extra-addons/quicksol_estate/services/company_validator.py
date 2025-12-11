from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class CompanyValidator:
    @staticmethod
    def validate_company_ids(company_ids):
        user = request.env.user
        
        if user.has_group('base.group_system'):
            return True, None
        
        if not company_ids:
            return False, 'At least one company must be specified'
        
        user_company_ids = set(user.estate_company_ids.ids)
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
    
    @staticmethod
    def get_default_company_id():
        user = request.env.user
        
        if user.estate_default_company_id:
            return user.estate_default_company_id.id
        
        if user.estate_company_ids:
            return user.estate_company_ids[0].id
        
        return None
    
    @staticmethod
    def ensure_company_ids(data):
        if 'company_ids' not in data:
            default_id = CompanyValidator.get_default_company_id()
            if default_id:
                data['company_ids'] = [(6, 0, [default_id])]
        
        return data
