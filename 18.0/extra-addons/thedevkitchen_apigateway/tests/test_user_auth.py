from odoo.tests.common import TransactionCase
from ..services.session_validator import SessionValidator
from odoo import fields


class TestUserAuth(TransactionCase):

    def setUp(self):
        super().setUp()

        self.company = self.env['thedevkitchen.estate.company'].create({
            'name': 'Test Company',
            'cnpj': '11222333000181',
        })

        self.test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test@example.com',
            'email': 'test@example.com',
            'password': 'test123',
            'estate_company_ids': [(6, 0, [self.company.id])],
            'estate_default_company_id': self.company.id,
        })

    def test_api_session_model_created(self):
        session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'test-session-123',
            'user_id': self.test_user.id,
            'ip_address': '127.0.0.1',
        })

        self.assertTrue(session.id)
        self.assertEqual(session.session_id, 'test-session-123')
        self.assertEqual(session.user_id.id, self.test_user.id)
        self.assertTrue(session.is_active)

    def test_api_session_marks_inactive_on_logout(self):
        session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'test-session-456',
            'user_id': self.test_user.id,
        })

        session.write({'is_active': False})
        self.assertFalse(session.is_active)

    def test_api_session_tracks_user_activity(self):
        session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'test-session-789',
            'user_id': self.test_user.id,
        })

        self.assertIsNotNone(session.login_at)
        self.assertIsNone(session.logout_at)

    def test_session_validator_finds_valid_session(self):
        session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'valid-session-123',
            'user_id': self.test_user.id,
            'ip_address': '127.0.0.1',
        })

        valid, user, error = SessionValidator.validate('valid-session-123')
        self.assertTrue(valid, 'Valid session should pass validation')
        self.assertEqual(user.id, self.test_user.id)
        self.assertIsNone(error)

    def test_session_validator_rejects_invalid_session(self):
        valid, user, error = SessionValidator.validate('invalid-session')
        self.assertFalse(valid, 'Invalid session should fail validation')
        self.assertIsNone(user)
        self.assertIsNotNone(error)

    def test_session_validator_rejects_inactive_session(self):
        session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'inactive-session-123',
            'user_id': self.test_user.id,
            'is_active': False,
        })

        valid, user, error = SessionValidator.validate('inactive-session-123')
        self.assertFalse(valid, 'Inactive session should fail validation')

    def test_session_validator_rejects_inactive_user(self):
        self.test_user.active = False
        session = self.env['thedevkitchen.api.session'].create({
            'session_id': 'user-inactive-session',
            'user_id': self.test_user.id,
        })

        valid, user, error = SessionValidator.validate('user-inactive-session')
        self.assertFalse(valid, 'Session for inactive user should fail')

        session_after = self.env['thedevkitchen.api.session'].search([
            ('session_id', '=', 'user-inactive-session')
        ])
        self.assertFalse(session_after.is_active, 'Session should be marked inactive')
