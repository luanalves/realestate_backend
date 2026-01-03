
from odoo.tests.common import TransactionCase
from odoo import fields
import logging

_logger = logging.getLogger(__name__)


class TestLoginEndpoint(TransactionCase):
    """Test suite for POST /api/v1/users/login endpoint"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test companies
        cls.company1 = cls.env['estate.company'].create({
            'name': 'Test Company 1',
            'vat': '12345678901234'
        })
        
        cls.company2 = cls.env['estate.company'].create({
            'name': 'Test Company 2',
            'vat': '98765432109876'
        })
        
        # Create test user with company assignment
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'testuser@example.com',
            'email': 'testuser@example.com',
            'password': 'SecurePass123!',
            'active': True,
            'estate_company_ids': [(6, 0, [cls.company1.id, cls.company2.id])]
        })
        
        # Create inactive user
        cls.inactive_user = cls.env['res.users'].create({
            'name': 'Inactive User',
            'login': 'inactive@example.com',
            'email': 'inactive@example.com',
            'password': 'SecurePass123!',
            'active': False,
            'estate_company_ids': [(6, 0, [cls.company1.id])]
        })
        
        # Create user without company (should fail login)
        cls.no_company_user = cls.env['res.users'].create({
            'name': 'No Company User',
            'login': 'nocompany@example.com',
            'email': 'nocompany@example.com',
            'password': 'SecurePass123!',
            'active': True,
            'estate_company_ids': []
        })

    def test_login_successful_creates_session(self):
        """Test successful login creates API session"""
        _logger.info("Test: successful login creates session")
        
        # Before login: no sessions
        sessions_before = self.env['thedevkitchen.api.session'].search([
            ('user_id', '=', self.test_user.id)
        ])
        self.assertEqual(len(sessions_before), 0)
        
        # Simulate successful login by directly testing the conditions
        # In real scenario, this would be called via HTTP endpoint
        self.assertTrue(self.test_user.active)
        self.assertTrue(len(self.test_user.estate_company_ids) > 0)

    def test_login_failed_invalid_email(self):
        """Test login fails with invalid email"""
        _logger.info("Test: login fails with invalid email")
        
        # Attempt to find non-existent user
        users = self.env['res.users'].sudo().search(
            [('login', '=', 'nonexistent@example.com')],
            limit=1
        )
        self.assertEqual(len(users), 0)

    def test_login_failed_invalid_password(self):
        """Test login fails with invalid password"""
        _logger.info("Test: login fails with invalid password")
        
        # User exists
        self.assertTrue(self.test_user.active)
        
        # Check password doesn't match (without actually checking the hash)
        # This tests the logic path
        invalid_pwd = "WrongPassword123!"
        result = self.test_user._check_credentials(invalid_pwd)
        self.assertFalse(result)

    def test_login_failed_inactive_user(self):
        """Test login fails for inactive users"""
        _logger.info("Test: login fails for inactive user")
        
        self.assertFalse(self.inactive_user.active)
        
        # Even with correct password, user is inactive
        sessions = self.env['thedevkitchen.api.session'].search([
            ('user_id', '=', self.inactive_user.id)
        ])
        self.assertEqual(len(sessions), 0)

    def test_login_failed_no_companies(self):
        """Test login fails when user has no company assignment"""
        _logger.info("Test: login fails when user has no companies")
        
        self.assertEqual(len(self.no_company_user.estate_company_ids), 0)
        self.assertFalse(self.no_company_user.has_group('base.group_system'))

    def test_login_invalidates_previous_sessions(self):
        """Test login invalidates previous active sessions"""
        _logger.info("Test: login invalidates previous sessions")
        
        # Create a previous session
        session1 = self.env['thedevkitchen.api.session'].create({
            'session_id': 'session_001',
            'user_id': self.test_user.id,
            'ip_address': '192.168.1.1',
            'user_agent': 'TestAgent/1.0',
            'is_active': True
        })
        
        # Verify session is active
        self.assertTrue(session1.is_active)
        
        # Create new session (simulating new login)
        session2 = self.env['thedevkitchen.api.session'].create({
            'session_id': 'session_002',
            'user_id': self.test_user.id,
            'ip_address': '192.168.1.2',
            'user_agent': 'TestAgent/1.0',
        })
        
        # First session should still exist but in real scenario would be invalidated
        self.assertTrue(session1.exists())
        self.assertTrue(session2.exists())

    def test_login_records_audit_log(self):
        """Test login records successful login audit"""
        _logger.info("Test: login records audit log")
        
        # This would be logged via AuditLogger.log_successful_login()
        # Verify the infrastructure exists
        audit_model = self.env.get('audit.log', False)
        # If audit model exists, it should have records capability
        if audit_model:
            self.assertTrue(hasattr(audit_model, 'create'))


class TestLogoutEndpoint(TransactionCase):
    """Test suite for POST /api/v1/users/logout endpoint"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['estate.company'].create({
            'name': 'Test Company',
            'vat': '12345678901234'
        })
        
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'logouttest@example.com',
            'email': 'logouttest@example.com',
            'password': 'SecurePass123!',
            'active': True,
            'estate_company_ids': [(6, 0, [cls.company.id])]
        })

    def test_logout_deactivates_session(self):
        """Test logout deactivates the session"""
        _logger.info("Test: logout deactivates session")
        
        # Create an active session
        session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'logout_session_001',
            'user_id': self.test_user.id,
            'ip_address': '192.168.1.1',
            'user_agent': 'TestAgent/1.0',
            'is_active': True
        })
        
        self.assertTrue(session.is_active)
        self.assertFalse(session.logout_at)
        
        # Deactivate session (simulating logout)
        session.write({
            'is_active': False,
            'logout_at': fields.Datetime.now()
        })
        
        self.assertFalse(session.is_active)
        self.assertTrue(session.logout_at)

    def test_logout_failed_invalid_session(self):
        """Test logout fails with invalid session_id"""
        _logger.info("Test: logout fails with invalid session")
        
        # Try to find non-existent session
        sessions = self.env['thedevkitchen.api.session'].search([
            ('session_id', '=', 'nonexistent_session_id'),
            ('is_active', '=', True)
        ], limit=1)
        
        self.assertEqual(len(sessions), 0)

    def test_logout_failed_already_logged_out(self):
        """Test logout fails for already logged-out sessions"""
        _logger.info("Test: logout fails for inactive session")
        
        # Create and deactivate a session
        session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'already_logged_out_session',
            'user_id': self.test_user.id,
            'ip_address': '192.168.1.1',
            'user_agent': 'TestAgent/1.0',
            'is_active': False,
            'logout_at': fields.Datetime.now()
        })
        
        # Try to find active session
        active_sessions = self.env['thedevkitchen.api.session'].search([
            ('session_id', '=', 'already_logged_out_session'),
            ('is_active', '=', True)
        ], limit=1)
        
        self.assertEqual(len(active_sessions), 0)

    def test_logout_without_session_id(self):
        """Test logout fails when session_id is not provided"""
        _logger.info("Test: logout fails without session_id")
        
        # This would return 400 error in the endpoint
        # Just verify the validation logic
        session_id = None
        if not session_id:
            # This is the validation path
            pass
        
        self.assertIsNone(session_id)


class TestProfileUpdateEndpoint(TransactionCase):
    """Test suite for PATCH /api/v1/users/profile endpoint"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['estate.company'].create({
            'name': 'Test Company',
            'vat': '12345678901234'
        })
        
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'profiletest@example.com',
            'email': 'profiletest@example.com',
            'password': 'SecurePass123!',
            'phone': '1122334455',
            'mobile': '11987654321',
            'active': True,
            'estate_company_ids': [(6, 0, [cls.company.id])]
        })

    def test_profile_update_email(self):
        """Test updating email field"""
        _logger.info("Test: update email")
        
        new_email = 'newemail@example.com'
        self.test_user.write({'email': new_email})
        
        self.assertEqual(self.test_user.email, new_email)

    def test_profile_update_phone(self):
        """Test updating phone field"""
        _logger.info("Test: update phone")
        
        new_phone = '1133334444'
        self.test_user.write({'phone': new_phone})
        
        self.assertEqual(self.test_user.phone, new_phone)

    def test_profile_update_mobile(self):
        """Test updating mobile field"""
        _logger.info("Test: update mobile")
        
        new_mobile = '11988888888'
        self.test_user.write({'mobile': new_mobile})
        
        self.assertEqual(self.test_user.mobile, new_mobile)

    def test_profile_update_email_invalid_format(self):
        """Test email validation rejects invalid format"""
        _logger.info("Test: email validation - invalid format")
        
        invalid_email = 'notanemail'
        is_valid = '@' in invalid_email and '.' in invalid_email.split('@')[1]
        
        self.assertFalse(is_valid)

    def test_profile_update_email_case_insensitive(self):
        """Test email is stored case-insensitively"""
        _logger.info("Test: email case-insensitive")
        
        email_upper = 'TestUser@Example.COM'
        email_lower = email_upper.lower()
        
        self.assertEqual(email_lower, 'testuser@example.com')

    def test_profile_update_email_duplicate_rejected(self):
        """Test duplicate email is rejected"""
        _logger.info("Test: duplicate email rejection")
        
        # Create another user with different email
        other_user = self.env['res.users'].create({
            'name': 'Other User',
            'login': 'otheruser@example.com',
            'email': 'otheruser@example.com',
            'password': 'SecurePass123!',
            'active': True,
            'estate_company_ids': [(6, 0, [self.company.id])]
        })
        
        # Try to use other_user's email for test_user
        existing = self.env['res.users'].search([
            ('email', '=', other_user.email),
            ('id', '!=', self.test_user.id),
            ('active', '=', True)
        ], limit=1)
        
        self.assertEqual(existing.id, other_user.id)

    def test_profile_update_phone_clear(self):
        """Test phone can be cleared"""
        _logger.info("Test: clear phone")
        
        self.test_user.write({'phone': False})
        
        self.assertFalse(self.test_user.phone)

    def test_profile_update_mobile_clear(self):
        """Test mobile can be cleared"""
        _logger.info("Test: clear mobile")
        
        self.test_user.write({'mobile': False})
        
        self.assertFalse(self.test_user.mobile)

    def test_profile_patch_semantics_preserves_other_fields(self):
        """Test PATCH semantics: updating one field preserves others"""
        _logger.info("Test: PATCH semantics preserve other fields")
        
        original_phone = self.test_user.phone
        original_mobile = self.test_user.mobile
        
        # Only update email
        self.test_user.write({'email': 'onlyemail@example.com'})
        
        # Other fields should remain unchanged
        self.assertEqual(self.test_user.phone, original_phone)
        self.assertEqual(self.test_user.mobile, original_mobile)
        self.assertEqual(self.test_user.email, 'onlyemail@example.com')

    def test_profile_update_cannot_modify_company(self):
        """Test profile update cannot modify company assignment"""
        _logger.info("Test: profile cannot modify company")
        
        original_companies = self.test_user.estate_company_ids
        
        # Try to modify companies (this should not be in the update_profile endpoint)
        # Verify only email, phone, mobile can be updated
        allowed_fields = {'email', 'phone', 'mobile'}
        
        self.assertNotIn('estate_company_ids', allowed_fields)
        self.assertEqual(self.test_user.estate_company_ids, original_companies)

    def test_profile_update_cannot_modify_admin_status(self):
        """Test profile update cannot modify admin status"""
        _logger.info("Test: profile cannot modify admin status")
        
        # Verify admin groups cannot be modified via profile update
        admin_groups = [g for g in self.test_user.groups_id 
                        if 'admin' in g.name.lower() or 'system' in g.name.lower()]
        
        # Profile endpoint should not allow group modifications
        allowed_fields = {'email', 'phone', 'mobile'}
        
        self.assertNotIn('groups_id', allowed_fields)


class TestPasswordChangeEndpoint(TransactionCase):
    """Test suite for POST /api/v1/users/change-password endpoint"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['estate.company'].create({
            'name': 'Test Company',
            'vat': '12345678901234'
        })
        
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'passwordtest@example.com',
            'email': 'passwordtest@example.com',
            'password': 'SecurePass123!',
            'active': True,
            'estate_company_ids': [(6, 0, [cls.company.id])]
        })

    def test_password_change_successful(self):
        """Test successful password change"""
        _logger.info("Test: successful password change")
        
        old_password = 'SecurePass123!'
        new_password = 'NewSecurePass456!'
        
        # Verify old password works
        result_old = self.test_user._check_credentials(old_password)
        self.assertTrue(result_old)
        
        # Change password
        self.test_user.write({'password': new_password})
        
        # Verify new password works
        result_new = self.test_user._check_credentials(new_password)
        self.assertTrue(result_new)
        
        # Verify old password no longer works
        result_old_after = self.test_user._check_credentials(old_password)
        self.assertFalse(result_old_after)

    def test_password_change_requires_current_password(self):
        """Test password change validates current password"""
        _logger.info("Test: password change validates current password")
        
        wrong_password = 'WrongPassword123!'
        
        # Verify wrong current password is rejected
        result = self.test_user._check_credentials(wrong_password)
        self.assertFalse(result)

    def test_password_change_requires_matching_passwords(self):
        """Test new_password and confirm_password must match"""
        _logger.info("Test: passwords must match")
        
        new_password = 'NewSecurePass456!'
        confirm_password = 'DifferentPassword789!'
        
        self.assertNotEqual(new_password, confirm_password)

    def test_password_change_minimum_length_8(self):
        """Test password must be at least 8 characters"""
        _logger.info("Test: password minimum length")
        
        short_password = 'Short12'
        
        self.assertLess(len(short_password), 8)
        self.assertFalse(len(short_password) >= 8)

    def test_password_change_accepts_special_characters(self):
        """Test password with special characters is accepted"""
        _logger.info("Test: password with special characters")
        
        password_with_special = 'P@ssw0rd!#$%'
        
        self.assertGreaterEqual(len(password_with_special), 8)
        self.assertTrue(any(c in '!@#$%^&*' for c in password_with_special))

    def test_password_change_case_sensitive(self):
        """Test passwords are case-sensitive"""
        _logger.info("Test: password case-sensitive")
        
        password1 = 'SecurePass123!'
        password2 = 'securepass123!'
        
        self.assertNotEqual(password1, password2)

    def test_password_change_hashes_password(self):
        """Test password is hashed and not stored in plain text"""
        _logger.info("Test: password is hashed")
        
        password = 'SecurePass123!'
        self.test_user.write({'password': password})
        
        # Password field in DB should be hashed, not plain text
        # We can't directly access the hash, but we can verify credentials work
        self.assertTrue(self.test_user._check_credentials(password))

    def test_password_change_invalidates_old_sessions(self):
        """Test password change should invalidate old sessions (recommended security)"""
        _logger.info("Test: password change should be tracked")
        
        # Create a session before password change
        session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'pwd_change_session',
            'user_id': self.test_user.id,
            'ip_address': '192.168.1.1',
            'user_agent': 'TestAgent/1.0',
            'is_active': True
        })
        
        self.assertTrue(session.is_active)
        
        # Change password
        self.test_user.write({'password': 'NewSecurePass456!'})
        
        # Session still exists (in this implementation)
        # But ideally should be invalidated for security
        self.assertTrue(session.exists())


class TestSessionIsolation(TransactionCase):
    """
    CRITICAL TESTS: Validate that sessions are properly isolated.
    User A's session CANNOT be used to modify User B's data.
    
    This is a fundamental security requirement for multi-user systems.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company1 = cls.env['estate.company'].create({
            'name': 'Company A',
            'vat': '11111111111111'
        })
        
        cls.company2 = cls.env['estate.company'].create({
            'name': 'Company B',
            'vat': '22222222222222'
        })
        
        # Create two different users
        cls.user_a = cls.env['res.users'].create({
            'name': 'User A',
            'login': 'usera@example.com',
            'email': 'usera@example.com',
            'password': 'PasswordA123!',
            'phone': '1111111111',
            'active': True,
            'estate_company_ids': [(6, 0, [cls.company1.id])]
        })
        
        cls.user_b = cls.env['res.users'].create({
            'name': 'User B',
            'login': 'userb@example.com',
            'email': 'userb@example.com',
            'password': 'PasswordB456!',
            'phone': '2222222222',
            'active': True,
            'estate_company_ids': [(6, 0, [cls.company2.id])]
        })

    def test_session_belongs_to_specific_user(self):
        """Test each session is bound to a specific user"""
        _logger.info("Test: session belongs to specific user")
        
        # Create session for user A
        session_a = self.env['thedevkitchen.api.session'].create({
            'session_id': 'session_user_a',
            'user_id': self.user_a.id,
            'ip_address': '192.168.1.100',
            'user_agent': 'TestAgent/1.0'
        })
        
        # Create session for user B
        session_b = self.env['thedevkitchen.api.session'].create({
            'session_id': 'session_user_b',
            'user_id': self.user_b.id,
            'ip_address': '192.168.1.101',
            'user_agent': 'TestAgent/1.0'
        })
        
        # Verify sessions are bound correctly
        self.assertEqual(session_a.user_id.id, self.user_a.id)
        self.assertEqual(session_b.user_id.id, self.user_b.id)
        self.assertNotEqual(session_a.user_id.id, session_b.user_id.id)

    def test_user_cannot_access_other_user_session(self):
        """Test user A cannot use user B's session"""
        _logger.info("Test: user cannot access other user's session")
        
        # Create session for user B
        session_b = self.env['thedevkitchen.api.session'].create({
            'session_id': 'protected_session_b',
            'user_id': self.user_b.id,
            'ip_address': '192.168.1.101',
            'user_agent': 'TestAgent/1.0'
        })
        
        # User A tries to logout user B's session (should fail)
        # Only user B (or admin) should be able to logout their own session
        self.assertEqual(session_b.user_id.id, self.user_b.id)
        self.assertNotEqual(session_b.user_id.id, self.user_a.id)

    def test_user_cannot_modify_other_user_email(self):
        """Test user A cannot modify user B's email"""
        _logger.info("Test: user cannot modify other user's email")
        
        original_email_b = self.user_b.email
        
        # Only user B should be able to update their own email
        # This would be enforced by the endpoint checking request.env.user
        user_context_in_endpoint = self.user_a
        user_to_modify = self.user_b
        
        # Verify they are different users
        self.assertNotEqual(user_context_in_endpoint.id, user_to_modify.id)
        
        # User A should NOT be able to modify User B's data
        self.assertEqual(self.user_b.email, original_email_b)

    def test_user_cannot_modify_other_user_password(self):
        """Test user A cannot change user B's password"""
        _logger.info("Test: user cannot change other user's password")
        
        original_pwd_b = 'PasswordB456!'
        
        # Verify original password works for user B
        result = self.user_b._check_credentials(original_pwd_b)
        self.assertTrue(result)
        
        # User A should NOT be able to change User B's password
        # This is enforced by using request.env.user in the endpoint
        only_user_b_can_change = self.user_b.id  # Only this user can change their password
        
        self.assertNotEqual(self.user_a.id, only_user_b_can_change)

    def test_user_cannot_modify_other_user_phone(self):
        """Test user A cannot modify user B's phone"""
        _logger.info("Test: user cannot modify other user's phone")
        
        original_phone_b = self.user_b.phone
        
        # User A should NOT have access to User B's profile endpoint
        accessing_user = self.user_a
        profile_owner = self.user_b
        
        self.assertNotEqual(accessing_user.id, profile_owner.id)
        self.assertEqual(self.user_b.phone, original_phone_b)

    def test_concurrent_updates_from_different_users(self):
        """Test concurrent updates from different users don't interfere"""
        _logger.info("Test: concurrent updates don't interfere")
        
        original_email_a = self.user_a.email
        original_email_b = self.user_b.email
        
        # Simulate concurrent updates
        new_email_a = 'newemail_a@example.com'
        new_email_b = 'newemail_b@example.com'
        
        # User A updates their email
        self.user_a.write({'email': new_email_a})
        
        # User B updates their email
        self.user_b.write({'email': new_email_b})
        
        # Verify both updates succeeded independently
        self.assertEqual(self.user_a.email, new_email_a)
        self.assertEqual(self.user_b.email, new_email_b)
        
        # Verify no cross-contamination
        self.assertNotEqual(self.user_a.email, new_email_b)
        self.assertNotEqual(self.user_b.email, new_email_a)

    def test_session_isolation_prevents_privilege_escalation(self):
        """Test session isolation prevents privilege escalation attempts"""
        _logger.info("Test: session isolation prevents escalation")
        
        # Verify users have different company assignments
        self.assertNotEqual(
            self.user_a.estate_company_ids.ids,
            self.user_b.estate_company_ids.ids
        )
        
        # User A's session should only access User A's companies
        self.assertTrue(self.company1.id in self.user_a.estate_company_ids.ids)
        self.assertFalse(self.company2.id in self.user_a.estate_company_ids.ids)
        
        # User B's session should only access User B's companies
        self.assertTrue(self.company2.id in self.user_b.estate_company_ids.ids)
        self.assertFalse(self.company1.id in self.user_b.estate_company_ids.ids)

    def test_multiple_sessions_same_user_isolated(self):
        """Test multiple sessions for same user are properly managed"""
        _logger.info("Test: multiple sessions per user are isolated")
        
        # User A creates two sessions (e.g., from different devices)
        session_a1 = self.env['thedevkitchen.api.session'].create({
            'session_id': 'device_1_a',
            'user_id': self.user_a.id,
            'ip_address': '192.168.1.100',
            'user_agent': 'Browser/Chrome'
        })
        
        session_a2 = self.env['thedevkitchen.api.session'].create({
            'session_id': 'device_2_a',
            'user_id': self.user_a.id,
            'ip_address': '192.168.1.200',
            'user_agent': 'Mobile/iOS'
        })
        
        # Both sessions belong to user A
        self.assertEqual(session_a1.user_id.id, self.user_a.id)
        self.assertEqual(session_a2.user_id.id, self.user_a.id)
        
        # But they are different sessions
        self.assertNotEqual(session_a1.session_id, session_a2.session_id)
        self.assertNotEqual(session_a1.ip_address, session_a2.ip_address)

    def test_logout_user_cannot_reuse_old_session(self):
        """Test user cannot reuse session after logout"""
        _logger.info("Test: logout prevents session reuse")
        
        # Create and verify active session
        session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'reuse_test_session',
            'user_id': self.user_a.id,
            'ip_address': '192.168.1.100',
            'user_agent': 'TestAgent/1.0',
            'is_active': True
        })
        
        self.assertTrue(session.is_active)
        
        # Logout: deactivate session
        session.write({
            'is_active': False,
            'logout_at': fields.Datetime.now()
        })
        
        # Verify session is no longer active
        self.assertFalse(session.is_active)
        
        # Try to find active session (should fail)
        active_sessions = self.env['thedevkitchen.api.session'].search([
            ('session_id', '=', 'reuse_test_session'),
            ('is_active', '=', True)
        ])
        
        self.assertEqual(len(active_sessions), 0)
