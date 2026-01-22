"""
SecurityGroupAuditObserver - LGPD compliance audit logging for user group changes.

ADR-020: Observer Pattern for Security Audit Trail
FR-036: Security group changes must be logged for LGPD compliance

This observer listens to user.groups_changed events and creates audit log entries
in the auditlog module (or mail.message) to track who changed what permissions when.
"""
import logging
from odoo import api, models, fields
from odoo.addons.quicksol_estate.models.abstract_observer import AbstractObserver

_logger = logging.getLogger(__name__)


class SecurityGroupAuditObserver(AbstractObserver):
    _name = 'quicksol.security.group.audit.observer'
    _description = 'Security Group Audit Observer - LGPD Compliance'
    _inherit = 'quicksol.abstract.observer'
    
    # Flag to indicate this observer can run asynchronously via Celery
    _async_capable = True
    
    @api.model
    def can_handle(self, event_name):
        """Handle user.groups_changed events for audit logging."""
        return event_name == 'user.groups_changed'
    
    @api.model
    def handle(self, event_name, data):
        """
        Log security group changes to audit trail.
        
        Args:
            event_name (str): Should be 'user.groups_changed'
            data (dict): {
                'user': res.users record,
                'added_groups': list of group names,
                'removed_groups': list of group names,
                'changed_by': user who made the change (from env.user)
            }
        
        Returns:
            dict: {'audit_log_id': int, 'logged': bool}
        """
        if not self.can_handle(event_name):
            return {'logged': False, 'reason': 'Event not handled'}
        
        user = data.get('user')
        added_groups = data.get('added_groups', [])
        removed_groups = data.get('removed_groups', [])
        changed_by = data.get('changed_by')
        
        if not user:
            _logger.warning("SecurityGroupAuditObserver: No user provided in event data")
            return {'logged': False, 'reason': 'No user provided'}
        
        # Build audit message
        message_parts = []
        
        if added_groups:
            message_parts.append(f"Added groups: {', '.join(added_groups)}")
        
        if removed_groups:
            message_parts.append(f"Removed groups: {', '.join(removed_groups)}")
        
        if not message_parts:
            return {'logged': False, 'reason': 'No group changes detected'}
        
        audit_message = " | ".join(message_parts)
        changed_by_info = f"by {changed_by.name} (ID: {changed_by.id})" if changed_by else "by system"
        
        # Log to Odoo's audit trail using mail.message (works without auditlog module)
        # This creates a persistent record in the database for LGPD compliance
        try:
            message = self.env['mail.message'].sudo().create({
                'subject': f'Security Groups Changed for {user.name}',
                'body': f"<p><strong>LGPD Audit Log - Security Group Change</strong></p>"
                        f"<p>User: {user.name} (ID: {user.id}, Login: {user.login})</p>"
                        f"<p>Changes: {audit_message}</p>"
                        f"<p>Changed {changed_by_info}</p>"
                        f"<p>Timestamp: {fields.Datetime.now()}</p>",
                'message_type': 'notification',
                'model': 'res.users',
                'res_id': user.id,
                'subtype_id': self.env.ref('mail.mt_note').id,
            })
            
            _logger.info(
                f"LGPD Audit: Security groups changed for user {user.login} (ID: {user.id}) "
                f"{changed_by_info}. Changes: {audit_message}"
            )
            
            return {
                'logged': True,
                'audit_log_id': message.id,
                'user_id': user.id,
                'changes': audit_message,
            }
            
        except Exception as e:
            _logger.error(
                f"SecurityGroupAuditObserver: Failed to create audit log for user {user.id}: {str(e)}"
            )
            return {
                'logged': False,
                'reason': f'Exception: {str(e)}',
                'user_id': user.id if user else None,
            }
    
    @api.model
    def _register_hook(self):
        """Register this observer with EventBus on module load."""
        super()._register_hook()
        _logger.info("SecurityGroupAuditObserver registered for user.groups_changed events")
