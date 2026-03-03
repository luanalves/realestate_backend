
import logging
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class UserCompanyValidatorObserver(models.AbstractModel):
    _name = 'quicksol.observer.user.company.validator'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Observer: Validate user-company assignments'
    
    name = fields.Char(default='User Company Validator Observer', readonly=True)
    
    @api.model
    def can_handle(self, event_name):
        """Handle user creation/update events."""
        return event_name in ['user.before_create', 'user.before_write']
    
    @api.model
    def handle(self, event_name, data):

        self._validate_data(data, ['vals'])
        
        vals = data['vals']
        current_user_id = data.get('user_id', self.env.uid)
        # Use sudo() to bypass access control checks for observer validation logic
        current_user = self.env['res.users'].sudo().browse(current_user_id)
        
        is_owner = current_user.has_group('quicksol_estate.group_real_estate_owner')
        is_system = current_user.has_group('base.group_system')
        
        if not is_owner or is_system:
            _logger.debug(f"UserCompanyValidator: Skipping (user is not Owner or is System Admin)")
            return
        
        company_ids_in_vals = self._extract_company_ids(vals)
        
        if not company_ids_in_vals:
            _logger.debug(f"UserCompanyValidator: No company_ids in vals, skipping")
            return
        
        allowed_company_ids = set(current_user.company_ids.ids)
        
        unauthorized_companies = company_ids_in_vals - allowed_company_ids
        
        if unauthorized_companies:
            unauthorized_names = self.env['res.company'].browse(list(unauthorized_companies)).mapped('name')
            raise ValidationError(_(
                "You cannot assign users to companies you don't have access to: %s"
            ) % ', '.join(unauthorized_names))
        
        _logger.info(f"UserCompanyValidator: Validation passed for user {current_user.name}")
    
    @api.model
    def _extract_company_ids(self, vals):

        company_ids = set()
        
        if 'company_ids' in vals:
            for command in vals.get('company_ids', []):
                if command[0] == 6:
                    company_ids.update(command[2])
                elif command[0] == 4:
                    company_ids.add(command[1])
        
        return company_ids
