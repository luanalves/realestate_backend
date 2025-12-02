from odoo.tests.common import TransactionCase


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
