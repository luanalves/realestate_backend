"""
ProspectorAutoAssignObserver - Auto-assign prospector_id when property is created

Listens to: property.before_create (sync)
Action: Auto-populate prospector_id field based on creating user

This observer ensures that when a Prospector user creates a property,
the prospector_id field is automatically set to their agent record.
This enables commission split tracking (FR-054 to FR-060).

Pattern: Observer with force_sync=True for validation/data mutation before create
"""
import logging
from odoo import api, models, fields

_logger = logging.getLogger(__name__)


class ProspectorAutoAssignObserver(models.AbstractModel):
    _name = 'quicksol.observer.prospector.auto.assign'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Observer: Auto-assign prospector_id on property creation'
    
    name = fields.Char(default='Prospector Auto Assign Observer', readonly=True)
    
    @api.model
    def can_handle(self, event_name):
        """Handle property.before_create events."""
        return event_name == 'property.before_create'
    
    @api.model
    def handle(self, event_name, data, **kwargs):
        """
        Auto-populate prospector_id for properties created by Prospector users.
        
        Args:
            event_name: 'property.before_create'
            data: vals dict for property creation
            force_sync: True (required for data mutation before create)
        
        Business Logic:
            - Check if creating user belongs to group_real_estate_prospector
            - Find agent record where user_id = creating user
            - Set prospector_id = agent.id
            - If no prospector_id and not a Prospector, leave blank (regular Agent flow)
        
        Commission Split:
            - prospector_id != agent_id → commission split applies
            - prospector_id == agent_id → no split (same agent)
            - prospector_id empty → no split (regular sale)
        """
        if event_name != 'property.before_create':
            return
        
        env = kwargs.get('env')
        if not env:
            return
        
        # Get current user and check if they're a Prospector
        current_user = env.user
        prospector_group = env.ref('quicksol_estate.group_real_estate_prospector', raise_if_not_found=False)
        
        if not prospector_group or prospector_group not in current_user.groups_id:
            # Not a Prospector user, skip auto-assignment
            return
        
        # Find agent record for current user
        Agent = env['real.estate.agent']
        agent = Agent.search([('user_id', '=', current_user.id)], limit=1)
        
        if not agent:
            # No agent record found for Prospector user
            # Log warning but don't fail (admin might create properties)
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(
                'Prospector user %s (ID: %d) has no linked agent record. '
                'prospector_id will not be auto-assigned.',
                current_user.name,
                current_user.id
            )
            return
        
        # Auto-assign prospector_id (only if not already set)
        if 'prospector_id' not in data or not data.get('prospector_id'):
            data['prospector_id'] = agent.id
