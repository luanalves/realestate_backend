"""
Test suite for SecurityGroupAuditObserver.

Tests FR-036 (LGPD compliance: security group changes must be logged).
Coverage: Audit logging for user group changes.
"""
from odoo.tests.common import TransactionCase
from odoo.addons.quicksol_estate.models.event_bus import EventBus


class TestSecurityGroupAuditObserver(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.User = cls.env['res.users']
        cls.Group = cls.env['res.groups']
        cls.Observer = cls.env['quicksol.security.group.audit.observer']
        cls.MailMessage = cls.env['mail.message']
        
        # Get existing groups for testing
        cls.agent_group = cls.env.ref('quicksol_estate.group_real_estate_agent')
        cls.manager_group = cls.env.ref('quicksol_estate.group_real_estate_manager')
        cls.user_group = cls.env.ref('quicksol_estate.group_real_estate_user')
        
        # Create test user
        cls.test_user = cls.User.create({
            'name': 'Test Audit User',
            'login': 'test_audit_user@test.com',
            'email': 'test_audit_user@test.com',
            'groups_id': [(6, 0, [cls.user_group.id])],
        })
    
    def test_observer_can_handle_groups_changed_event(self):
        """T137.1: Observer correctly identifies user.groups_changed events."""
        observer = self.Observer.create({'name': 'Test Audit Observer'})
        
        self.assertTrue(observer.can_handle('user.groups_changed'))
        self.assertFalse(observer.can_handle('user.created'))
        self.assertFalse(observer.can_handle('property.created'))
    
    def test_audit_log_created_when_groups_added(self):
        """T137.2: Audit log entry created when security groups are added to user."""
        # Count mail messages before
        messages_before = self.MailMessage.search_count([
            ('model', '=', 'res.users'),
            ('res_id', '=', self.test_user.id),
        ])
        
        # Trigger observer directly with event data
        observer = self.Observer.create({'name': 'Test Audit Observer'})
        result = observer.handle('user.groups_changed', {
            'user': self.test_user,
            'added_groups': ['Real Estate Agent'],
            'removed_groups': [],
            'changed_by': self.env.user,
        })
        
        # Verify audit log was created
        self.assertTrue(result['logged'])
        self.assertIn('audit_log_id', result)
        self.assertEqual(result['user_id'], self.test_user.id)
        
        # Verify mail.message was created
        messages_after = self.MailMessage.search_count([
            ('model', '=', 'res.users'),
            ('res_id', '=', self.test_user.id),
        ])
        self.assertEqual(messages_after, messages_before + 1)
        
        # Verify message content
        audit_message = self.MailMessage.search([
            ('model', '=', 'res.users'),
            ('res_id', '=', self.test_user.id),
            ('id', '=', result['audit_log_id']),
        ], limit=1)
        
        self.assertIn('Security Groups Changed', audit_message.subject)
        self.assertIn('Real Estate Agent', audit_message.body)
        self.assertIn('Added groups', audit_message.body)
    
    def test_audit_log_created_when_groups_removed(self):
        """T137.3: Audit log entry created when security groups are removed from user."""
        messages_before = self.MailMessage.search_count([
            ('model', '=', 'res.users'),
            ('res_id', '=', self.test_user.id),
        ])
        
        observer = self.Observer.create({'name': 'Test Audit Observer'})
        result = observer.handle('user.groups_changed', {
            'user': self.test_user,
            'added_groups': [],
            'removed_groups': ['Real Estate User'],
            'changed_by': self.env.user,
        })
        
        self.assertTrue(result['logged'])
        
        messages_after = self.MailMessage.search_count([
            ('model', '=', 'res.users'),
            ('res_id', '=', self.test_user.id),
        ])
        self.assertEqual(messages_after, messages_before + 1)
        
        # Verify message content includes removal
        audit_message = self.MailMessage.browse(result['audit_log_id'])
        self.assertIn('Removed groups', audit_message.body)
        self.assertIn('Real Estate User', audit_message.body)
    
    def test_audit_log_tracks_who_made_change(self):
        """T137.4: Audit log records which user made the permission change."""
        observer = self.Observer.create({'name': 'Test Audit Observer'})
        
        # Create admin user who makes the change
        admin_user = self.User.create({
            'name': 'Admin Test',
            'login': 'admin_test@test.com',
            'email': 'admin_test@test.com',
        })
        
        result = observer.handle('user.groups_changed', {
            'user': self.test_user,
            'added_groups': ['Real Estate Manager'],
            'removed_groups': [],
            'changed_by': admin_user,
        })
        
        audit_message = self.MailMessage.browse(result['audit_log_id'])
        self.assertIn(f'by {admin_user.name}', audit_message.body)
        self.assertIn(f'ID: {admin_user.id}', audit_message.body)
    
    def test_no_audit_log_when_no_changes(self):
        """T137.5: No audit log created if groups list doesn't actually change."""
        observer = self.Observer.create({'name': 'Test Audit Observer'})
        
        result = observer.handle('user.groups_changed', {
            'user': self.test_user,
            'added_groups': [],
            'removed_groups': [],
            'changed_by': self.env.user,
        })
        
        self.assertFalse(result['logged'])
        self.assertEqual(result['reason'], 'No group changes detected')
    
    def test_integration_groups_changed_via_write(self):
        """T137.6: Integration test - audit log created when user.write() changes groups."""
        messages_before = self.MailMessage.search_count([
            ('model', '=', 'res.users'),
            ('res_id', '=', self.test_user.id),
        ])
        
        # Add agent group to user (triggers event in res_users.write)
        self.test_user.write({
            'groups_id': [(4, self.agent_group.id)],
        })
        
        # Verify audit log was created via event system
        messages_after = self.MailMessage.search_count([
            ('model', '=', 'res.users'),
            ('res_id', '=', self.test_user.id),
        ])
        
        # Should have created at least one audit message
        self.assertGreater(messages_after, messages_before)
        
        # Find the latest audit message
        latest_message = self.MailMessage.search([
            ('model', '=', 'res.users'),
            ('res_id', '=', self.test_user.id),
        ], order='id desc', limit=1)
        
        self.assertIn('Security Groups Changed', latest_message.subject)
        self.assertIn(self.agent_group.name, latest_message.body)
    
    def test_audit_log_includes_timestamp(self):
        """T137.7: Audit log includes precise timestamp for LGPD compliance."""
        observer = self.Observer.create({'name': 'Test Audit Observer'})
        
        result = observer.handle('user.groups_changed', {
            'user': self.test_user,
            'added_groups': ['Real Estate Financial'],
            'removed_groups': [],
            'changed_by': self.env.user,
        })
        
        audit_message = self.MailMessage.browse(result['audit_log_id'])
        self.assertIn('Timestamp:', audit_message.body)
        # Message should contain current date
        self.assertIn('2026', audit_message.body)
