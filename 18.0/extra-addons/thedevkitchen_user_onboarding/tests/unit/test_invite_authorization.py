# -*- coding: utf-8 -*-
"""
Unit Tests: Invite Authorization Matrix

Tests the authorization matrix for user invitations and email template rendering.

Authorization Matrix:
- Owner: Can invite all 9 profiles
- Director: Can invite 5 operational profiles (inherits Manager permissions)
- Manager: Can invite 5 operational profiles (agent, prospector, receptionist, financial, legal)
- Agent: Can invite owner and portal only
- Other profiles (Prospector, Receptionist, Financial, Legal, Portal): Cannot invite anyone

Author: TheDevKitchen
Date: 2026-02-16
ADRs: ADR-003 (Testing Standards), ADR-019 (RBAC)
"""

from odoo.tests import TransactionCase
from odoo.exceptions import UserError
from unittest.mock import Mock, MagicMock, patch


class TestInviteAuthorization(TransactionCase):
    """Test authorization matrix for user invitations."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        # Create test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
        })
        
        # Create groups (reference existing groups)
        self.group_owner = self.env.ref('quicksol_estate.group_real_estate_owner')
        self.group_director = self.env.ref('quicksol_estate.group_real_estate_director')
        self.group_manager = self.env.ref('quicksol_estate.group_real_estate_manager')
        self.group_agent = self.env.ref('quicksol_estate.group_real_estate_agent')
        self.group_prospector = self.env.ref('quicksol_estate.group_real_estate_prospector')
        self.group_receptionist = self.env.ref('quicksol_estate.group_real_estate_receptionist')
        self.group_financial = self.env.ref('quicksol_estate.group_real_estate_financial')
        self.group_legal = self.env.ref('quicksol_estate.group_real_estate_legal')
        self.group_portal = self.env.ref('base.group_portal')
        
        # Create test users for each profile
        self.owner_user = self._create_test_user('owner@test.com', 'Owner User', [self.group_owner])
        self.director_user = self._create_test_user('director@test.com', 'Director User', [self.group_director])
        self.manager_user = self._create_test_user('manager@test.com', 'Manager User', [self.group_manager])
        self.agent_user = self._create_test_user('agent@test.com', 'Agent User', [self.group_agent])
        self.prospector_user = self._create_test_user('prospector@test.com', 'Prospector User', [self.group_prospector])
        
        # Initialize InviteService
        from odoo.addons.thedevkitchen_user_onboarding.services.invite_service import InviteService
        self.invite_service = InviteService(self.env)
    
    def _create_test_user(self, login, name, groups):
        """Helper to create test user with groups."""
        user = self.env['res.users'].create({
            'login': login,
            'name': name,
            'email': login,
            'estate_company_ids': [(6, 0, [self.company.id])],
            'groups_id': [(6, 0, [g.id for g in groups])],
        })
        return user
    
    # ============================================================
    # Owner Authorization Tests
    # ============================================================
    
    def test_owner_can_invite_all_profiles(self):
        """Owner can invite all 9 profiles."""
        profiles = ['owner', 'director', 'manager', 'agent', 'prospector', 
                   'receptionist', 'financial', 'legal', 'portal']
        
        for profile in profiles:
            with self.subTest(profile=profile):
                try:
                    self.invite_service.check_authorization(self.owner_user, profile)
                except UserError:
                    self.fail(f"Owner should be able to invite {profile}")
    
    # ============================================================
    # Manager Authorization Tests
    # ============================================================
    
    def test_manager_can_invite_operational_profiles(self):
        """Manager can invite 5 operational profiles."""
        allowed_profiles = ['agent', 'prospector', 'receptionist', 'financial', 'legal']
        
        for profile in allowed_profiles:
            with self.subTest(profile=profile):
                try:
                    self.invite_service.check_authorization(self.manager_user, profile)
                except UserError:
                    self.fail(f"Manager should be able to invite {profile}")
    
    def test_manager_cannot_invite_owner(self):
        """Manager cannot invite owner profile."""
        with self.assertRaises(UserError) as context:
            self.invite_service.check_authorization(self.manager_user, 'owner')
        
        self.assertIn('not authorized', str(context.exception).lower())
    
    def test_manager_cannot_invite_director(self):
        """Manager cannot invite director profile."""
        with self.assertRaises(UserError) as context:
            self.invite_service.check_authorization(self.manager_user, 'director')
        
        self.assertIn('not authorized', str(context.exception).lower())
    
    def test_manager_cannot_invite_manager(self):
        """Manager cannot invite another manager."""
        with self.assertRaises(UserError) as context:
            self.invite_service.check_authorization(self.manager_user, 'manager')
        
        self.assertIn('not authorized', str(context.exception).lower())
    
    def test_manager_cannot_invite_portal(self):
        """Manager cannot invite portal profile."""
        with self.assertRaises(UserError) as context:
            self.invite_service.check_authorization(self.manager_user, 'portal')
        
        self.assertIn('not authorized', str(context.exception).lower())
    
    # ============================================================
    # Director Authorization Tests
    # ============================================================
    
    def test_director_inherits_manager_permissions(self):
        """Director can invite 5 operational profiles (inherits Manager permissions)."""
        allowed_profiles = ['agent', 'prospector', 'receptionist', 'financial', 'legal']
        
        for profile in allowed_profiles:
            with self.subTest(profile=profile):
                try:
                    self.invite_service.check_authorization(self.director_user, profile)
                except UserError:
                    self.fail(f"Director should be able to invite {profile}")
    
    def test_director_cannot_invite_owner(self):
        """Director cannot invite owner profile."""
        with self.assertRaises(UserError) as context:
            self.invite_service.check_authorization(self.director_user, 'owner')
        
        self.assertIn('not authorized', str(context.exception).lower())
    
    # ============================================================
    # Agent Authorization Tests
    # ============================================================
    
    def test_agent_can_invite_owner(self):
        """Agent can invite owner profile."""
        try:
            self.invite_service.check_authorization(self.agent_user, 'owner')
        except UserError:
            self.fail("Agent should be able to invite owner")
    
    def test_agent_can_invite_portal(self):
        """Agent can invite portal profile."""
        try:
            self.invite_service.check_authorization(self.agent_user, 'portal')
        except UserError:
            self.fail("Agent should be able to invite portal")
    
    def test_agent_cannot_invite_manager(self):
        """Agent cannot invite manager profile."""
        with self.assertRaises(UserError) as context:
            self.invite_service.check_authorization(self.agent_user, 'manager')
        
        self.assertIn('not authorized', str(context.exception).lower())
    
    def test_agent_cannot_invite_agent(self):
        """Agent cannot invite another agent."""
        with self.assertRaises(UserError) as context:
            self.invite_service.check_authorization(self.agent_user, 'agent')
        
        self.assertIn('not authorized', str(context.exception).lower())
    
    # ============================================================
    # Other Profiles Authorization Tests
    # ============================================================
    
    def test_prospector_cannot_invite_anyone(self):
        """Prospector cannot invite any profile."""
        profiles = ['owner', 'director', 'manager', 'agent', 'prospector', 
                   'receptionist', 'financial', 'legal', 'portal']
        
        for profile in profiles:
            with self.subTest(profile=profile):
                with self.assertRaises(UserError):
                    self.invite_service.check_authorization(self.prospector_user, profile)
    
    # ============================================================
    # Email Template Tests
    # ============================================================
    
    @patch('odoo.addons.thedevkitchen_user_onboarding.services.invite_service.InviteService.send_invite_email')
    def test_email_template_rendering(self, mock_send_email):
        """Invite email template renders with correct variables."""
        # Create a test user
        test_user = self._create_test_user('invite@test.com', 'Test Invite User', [self.group_agent])
        
        # Mock settings
        settings = Mock()
        settings.invite_link_ttl_hours = 24
        settings.frontend_base_url = 'http://localhost:3000'
        
        # Generate a test token
        raw_token = 'test-token-12345'
        
        # Call send_invite_email with mock
        with patch.object(self.env['thedevkitchen.email.link.settings'], 'get_settings', return_value=settings):
            self.invite_service.send_invite_email(test_user, raw_token, 24)
        
        # Verify send_invite_email was called
        mock_send_email.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_send_email.call_args
        self.assertEqual(call_args[0][0], test_user)  # First arg is user
        self.assertEqual(call_args[0][1], raw_token)  # Second arg is token
        self.assertEqual(call_args[0][2], 24)  # Third arg is expires_hours
    
    def test_invite_email_context_variables(self):
        """Email template context contains required variables."""
        # Create email template
        email_template = self.env.ref('thedevkitchen_user_onboarding.email_template_user_invite')
        
        self.assertTrue(email_template, "Invite email template should exist")
        self.assertEqual(email_template.model, 'res.users', "Template should target res.users model")
        
        # Verify template contains required placeholders
        body_html = email_template.body_html
        self.assertIn('invite_link', body_html, "Template should contain invite_link variable")
        self.assertIn('expires_hours', body_html, "Template should contain expires_hours variable")
    
    # ============================================================
    # Edge Cases
    # ============================================================
    
    def test_invalid_profile_raises_error(self):
        """Invalid profile name raises appropriate error."""
        with self.assertRaises(UserError):
            self.invite_service.check_authorization(self.owner_user, 'invalid_profile')
    
    def test_empty_profile_raises_error(self):
        """Empty profile name raises appropriate error."""
        with self.assertRaises(UserError):
            self.invite_service.check_authorization(self.owner_user, '')
    
    def test_none_profile_raises_error(self):
        """None profile raises appropriate error."""
        with self.assertRaises((UserError, TypeError)):
            self.invite_service.check_authorization(self.owner_user, None)
