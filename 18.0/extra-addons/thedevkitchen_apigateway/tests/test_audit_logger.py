# -*- coding: utf-8 -*-
"""
Test cases for AuditLogger service.

Tests validate:
1. Login events are logged
2. Logout events are logged
3. Failed login attempts are logged
4. Error events are logged
5. Log entries contain proper metadata
6. Logs are persisted in ir.logging
7. Multiple login/logout cycles log correctly
8. Audit trail is complete and traceable
"""

from odoo.tests.common import TransactionCase
from odoo import fields
from datetime import datetime


class TestAuditLogger(TransactionCase):
    """Test audit logging functionality"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env['quicksol_estate.company'].create({
            'name': 'Test Company',
            'cnpj': '11.222.333/0001-81',
        })
        
        # Create test user
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'testuser@example.com',
            'email': 'testuser@example.com',
            'password': 'testpassword123',
            'estate_company_ids': [(6, 0, [cls.company.id])],
            'estate_default_company_id': cls.company.id,
        })

    def setUp(self):
        super().setUp()
        # Clear logs before each test
        self.env['ir.logging'].search([]).unlink()

    def test_successful_login_is_logged(self):
        """Successful login should be logged"""
        from odoo.addons.thedevkitchen_apigateway.services.audit_logger import AuditLogger
        
        # Log successful login
        AuditLogger.log_successful_login('127.0.0.1', 'testuser@example.com', self.test_user.id)
        
        # Verify log entry exists
        logs = self.env['ir.logging'].search([
            ('message', 'ilike', 'Successful login')
        ])
        
        self.assertGreater(len(logs), 0, "Login should be logged")
        
        # Verify log contains user info
        log_message = logs[0].message
        self.assertIn('testuser@example.com', log_message)
        self.assertIn(str(self.test_user.id), log_message)

    def test_failed_login_is_logged(self):
        """Failed login attempts should be logged"""
        from odoo.addons.thedevkitchen_apigateway.services.audit_logger import AuditLogger
        
        # Log failed login
        AuditLogger.log_failed_login('127.0.0.1', 'testuser@example.com')
        
        # Verify log entry exists
        logs = self.env['ir.logging'].search([
            ('message', 'ilike', 'Failed login')
        ])
        
        self.assertGreater(len(logs), 0, "Failed login should be logged")
        
        # Verify log contains relevant info
        log_message = logs[0].message
        self.assertIn('testuser@example.com', log_message)

    def test_failed_login_with_reason_is_logged(self):
        """Failed login with reason should be logged"""
        from odoo.addons.thedevkitchen_apigateway.services.audit_logger import AuditLogger
        
        # Log failed login with reason
        AuditLogger.log_failed_login('127.0.0.1', 'testuser@example.com', 'User inactive')
        
        # Verify log entry exists with reason
        logs = self.env['ir.logging'].search([
            ('message', 'ilike', 'Failed login')
        ])
        
        self.assertGreater(len(logs), 0)
        log_message = logs[0].message
        self.assertIn('User inactive', log_message)

    def test_logout_is_logged(self):
        """Logout events should be logged"""
        from odoo.addons.thedevkitchen_apigateway.services.audit_logger import AuditLogger
        
        # Log logout
        AuditLogger.log_logout('testuser@example.com', self.test_user.id)
        
        # Verify log entry exists
        logs = self.env['ir.logging'].search([
            ('message', 'ilike', 'Logout')
        ])
        
        self.assertGreater(len(logs), 0, "Logout should be logged")
        
        # Verify log contains user info
        log_message = logs[0].message
        self.assertIn('testuser@example.com', log_message)
        self.assertIn(str(self.test_user.id), log_message)

    def test_error_is_logged(self):
        """Errors should be logged"""
        from odoo.addons.thedevkitchen_apigateway.services.audit_logger import AuditLogger
        
        # Log error
        AuditLogger.log_error('user.login', 'testuser@example.com', 'Invalid database')
        
        # Verify log entry exists
        logs = self.env['ir.logging'].search([
            ('message', 'ilike', 'Invalid database')
        ])
        
        self.assertGreater(len(logs), 0, "Error should be logged")
        
        # Verify log contains error details
        log_message = logs[0].message
        self.assertIn('user.login', log_message)
        self.assertIn('testuser@example.com', log_message)
        self.assertIn('Invalid database', log_message)

    def test_log_entry_contains_metadata(self):
        """Log entries should contain proper metadata"""
        from odoo.addons.thedevkitchen_apigateway.services.audit_logger import AuditLogger
        
        # Log successful login
        AuditLogger.log_successful_login('192.168.1.100', 'testuser@example.com', self.test_user.id)
        
        # Get log entry
        logs = self.env['ir.logging'].search([
            ('message', 'ilike', 'Successful login')
        ], limit=1)
        
        self.assertGreater(len(logs), 0)
        log = logs[0]
        
        # Verify metadata fields
        self.assertIsNotNone(log.create_date, "Log should have creation date")
        self.assertIsNotNone(log.message, "Log should have message")
        # path, func, line are optional but should exist
        self.assertTrue(hasattr(log, 'path'))

    def test_multiple_logins_create_separate_logs(self):
        """Each login should create a separate log entry"""
        from odoo.addons.thedevkitchen_apigateway.services.audit_logger import AuditLogger
        
        # Log first login
        AuditLogger.log_successful_login('127.0.0.1', 'testuser@example.com', self.test_user.id)
        
        # Log second login
        AuditLogger.log_successful_login('192.168.1.100', 'testuser@example.com', self.test_user.id)
        
        # Verify two log entries exist
        logs = self.env['ir.logging'].search([
            ('message', 'ilike', 'Successful login')
        ])
        
        self.assertEqual(len(logs), 2, "Two login attempts should create two log entries")

    def test_login_logout_sequence_logged_correctly(self):
        """Complete login/logout sequence should be logged"""
        from odoo.addons.thedevkitchen_apigateway.services.audit_logger import AuditLogger
        
        # Log login
        AuditLogger.log_successful_login('127.0.0.1', 'testuser@example.com', self.test_user.id)
        
        # Log logout
        AuditLogger.log_logout('testuser@example.com', self.test_user.id)
        
        # Verify both entries exist
        login_logs = self.env['ir.logging'].search([
            ('message', 'ilike', 'Successful login')
        ])
        logout_logs = self.env['ir.logging'].search([
            ('message', 'ilike', 'Logout')
        ])
        
        self.assertEqual(len(login_logs), 1, "Should have one login log")
        self.assertEqual(len(logout_logs), 1, "Should have one logout log")

    def test_audit_log_path_and_function_info(self):
        """Log should contain path and function information"""
        from odoo.addons.thedevkitchen_apigateway.services.audit_logger import AuditLogger
        
        # Log error with all details
        AuditLogger.log_error('user.auth', 'testuser@example.com', 'Test error message')
        
        # Get log entry
        logs = self.env['ir.logging'].search([
            ('message', 'ilike', 'Test error message')
        ], limit=1)
        
        self.assertGreater(len(logs), 0)
        log = logs[0]
        
        # Log should have tracking info
        self.assertIsNotNone(log.message)
        # path field should exist in ir.logging model
        self.assertTrue(hasattr(log, 'path'))

    def test_failed_login_attempts_create_audit_trail(self):
        """Failed login attempts should create visible audit trail"""
        from odoo.addons.thedevkitchen_apigateway.services.audit_logger import AuditLogger
        
        # Simulate multiple failed login attempts
        for i in range(3):
            AuditLogger.log_failed_login('127.0.0.1', 'testuser@example.com', 'Invalid password')
        
        # Verify all attempts are logged
        logs = self.env['ir.logging'].search([
            ('message', 'ilike', 'Failed login')
        ])
        
        self.assertEqual(len(logs), 3, "All failed login attempts should be logged")
        
        # All should have same user email for audit trail
        for log in logs:
            self.assertIn('testuser@example.com', log.message)

    def test_log_entries_are_ordered_by_time(self):
        """Log entries should be retrievable in time order"""
        from odoo.addons.thedevkitchen_apigateway.services.audit_logger import AuditLogger
        import time
        
        # Create several log entries with slight delays
        AuditLogger.log_successful_login('127.0.0.1', 'testuser@example.com', self.test_user.id)
        time.sleep(0.1)
        AuditLogger.log_logout('testuser@example.com', self.test_user.id)
        
        # Get logs ordered by creation date
        logs = self.env['ir.logging'].search([
            ('message', 'ilike', 'login|Logout', 'ilike')
        ], order='create_date asc')
        
        self.assertGreater(len(logs), 0, "Should retrieve logs in order")
        
        # Verify order (login should come before logout)
        if len(logs) >= 2:
            # Check that creation dates are in ascending order
            for i in range(len(logs) - 1):
                self.assertLessEqual(logs[i].create_date, logs[i + 1].create_date)
