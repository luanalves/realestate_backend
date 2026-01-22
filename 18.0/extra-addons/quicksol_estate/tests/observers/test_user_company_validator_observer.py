"""
Test suite for UserCompanyValidatorObserver.

Tests observer validation logic with force_sync=True.
Coverage: FR-007, FR-008 (Owner user assignment constraints)
"""
from unittest.mock import patch
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestUserCompanyValidatorObserver(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.Company = cls.env['thedevkitchen.estate.company']
        cls.User = cls.env['res.users']
        cls.EventBus = cls.env['quicksol.event.bus']
        cls.Observer = cls.env['quicksol.observer.user.company.validator']
        
        cls.owner_group = cls.env.ref('quicksol_estate.group_real_estate_owner')
        
        cls.company_a = cls.Company.create({
            'name': 'Company A',
            'cnpj': '11.111.111/0001-11',
            'creci': 'CRECI-SP 11111',
        })
        
        cls.company_b = cls.Company.create({
            'name': 'Company B',
            'cnpj': '22.222.222/0001-22',
            'creci': 'CRECI-RJ 22222',
        })
        
        cls.owner_a = cls.User.create({
            'name': 'Owner A',
            'login': 'owner_a@observer.test',
            'email': 'owner_a@observer.test',
            'groups_id': [(6, 0, [cls.owner_group.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
    
    def test_observer_can_handle_user_before_create(self):
        """T034.1: Observer handles user.before_create events."""
        self.assertTrue(self.Observer.can_handle('user.before_create'))
    
    def test_observer_can_handle_user_before_write(self):
        """T034.2: Observer handles user.before_write events."""
        self.assertTrue(self.Observer.can_handle('user.before_write'))
    
    def test_observer_ignores_other_events(self):
        """T034.3: Observer ignores events it doesn't handle."""
        self.assertFalse(self.Observer.can_handle('property.created'))
        self.assertFalse(self.Observer.can_handle('commission.split.calculated'))
    
    def test_observer_allows_owner_assign_to_own_company(self):
        """T035.1: Observer allows Owner to assign users to their companies."""
        vals = {
            'name': 'Test User',
            'login': 'test@test.com',
            'estate_company_ids': [(6, 0, [self.company_a.id])],
        }
        
        data = {
            'vals': vals,
            'user_id': self.owner_a.id,
        }
        
        self.Observer.handle('user.before_create', data)
    
    def test_observer_raises_on_unauthorized_company_assignment(self):
        """T035.2: Observer raises ValidationError if Owner assigns to unauthorized company."""
        vals = {
            'name': 'Invalid User',
            'login': 'invalid@test.com',
            'estate_company_ids': [(6, 0, [self.company_b.id])],
        }
        
        data = {
            'vals': vals,
            'user_id': self.owner_a.id,
        }
        
        with self.assertRaises(ValidationError) as ctx:
            self.Observer.handle('user.before_create', data)
        
        self.assertIn('Company B', str(ctx.exception))
    
    def test_observer_allows_system_admin_assign_to_any_company(self):
        """T035.3: Observer skips validation for System Admin users."""
        admin_user = self.env.ref('base.user_admin')
        
        vals = {
            'name': 'Admin Created User',
            'login': 'admin_user@test.com',
            'estate_company_ids': [(6, 0, [self.company_b.id])],
        }
        
        data = {
            'vals': vals,
            'user_id': admin_user.id,
        }
        
        self.Observer.handle('user.before_create', data)
    
    def test_observer_handles_odoo_many2many_command_format_6(self):
        """T035.4: Observer correctly extracts company IDs from [(6, 0, [...])] format."""
        vals = {
            'estate_company_ids': [(6, 0, [self.company_a.id, self.company_b.id])],
        }
        
        company_ids = self.Observer._extract_company_ids(vals)
        
        self.assertEqual(company_ids, {self.company_a.id, self.company_b.id})
    
    def test_observer_handles_odoo_many2many_command_format_4(self):
        """T035.5: Observer correctly extracts company IDs from [(4, id)] format."""
        vals = {
            'estate_company_ids': [(4, self.company_a.id)],
        }
        
        company_ids = self.Observer._extract_company_ids(vals)
        
        self.assertEqual(company_ids, {self.company_a.id})
    
    def test_event_bus_emits_user_before_create_sync(self):
        """T035.6: EventBus emits user.before_create synchronously (force_sync validation)."""
        with patch.object(type(self.EventBus), '_emit_sync') as mock_sync:
            mock_sync.return_value = None
            
            self.EventBus.emit('user.before_create', {'vals': {}})
            
            mock_sync.assert_called_once_with('user.before_create', {'vals': {}})
    
    def test_integration_user_create_triggers_observer(self):
        """T035.7: Creating user via res.users.create() triggers observer validation."""
        with self.assertRaises(ValidationError):
            self.User.with_user(self.owner_a).create({
                'name': 'Should Fail',
                'login': 'fail@test.com',
                'email': 'fail@test.com',
                'estate_company_ids': [(6, 0, [self.company_b.id])],
            })
