"""
UserCompanyValidatorObserver - Enforces company assignment constraints.

ADR-020: Observer Pattern for Odoo Event-Driven Architecture
FR-007: Owner can only assign users to their own companies

Validation logic:
- Owner users can only assign users to companies they have access to
- Prevents cross-company user assignments (multi-tenant security)
- Raises ValidationError if constraint violated
"""
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
        """
        Validate that Owner users only assign to their own companies.
        
        Args:
            event_name (str): 'user.before_create' or 'user.before_write'
            data (dict): Must contain:
                - 'vals' (dict): User values being created/updated
                - 'user_id' (int, optional): Current user's ID (defaults to env.uid)
        
        Raises:
            ValidationError: If Owner tries to assign user to unauthorized company
        """
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
        
        allowed_company_ids = set(current_user.estate_company_ids.ids)
        
        unauthorized_companies = company_ids_in_vals - allowed_company_ids
        
        if unauthorized_companies:
            unauthorized_names = self.env['thedevkitchen.estate.company'].browse(list(unauthorized_companies)).mapped('name')
            raise ValidationError(_(
                "You cannot assign users to companies you don't have access to: %s"
            ) % ', '.join(unauthorized_names))
        
        _logger.info(f"UserCompanyValidator: Validation passed for user {current_user.name}")
    
    @api.model
    def _extract_company_ids(self, vals):
        """
        Extract company IDs from vals dict (handles multiple formats).
        
        Odoo formats:
        - [(6, 0, [1, 2, 3])] - Replace all
        - [(4, 1)] - Add link to ID 1
        - [(3, 2)] - Remove link to ID 2
        
        Args:
            vals (dict): User values
        
        Returns:
            set: Company IDs being assigned
        """
        company_ids = set()
        
        if 'company_ids' in vals:
            for command in vals.get('company_ids', []):
                if command[0] == 6:
                    company_ids.update(command[2])
                elif command[0] == 4:
                    company_ids.add(command[1])
        
        if 'estate_company_ids' in vals:
            for command in vals.get('estate_company_ids', []):
                if command[0] == 6:
                    company_ids.update(command[2])
                elif command[0] == 4:
                    company_ids.add(command[1])
        
        return company_ids
