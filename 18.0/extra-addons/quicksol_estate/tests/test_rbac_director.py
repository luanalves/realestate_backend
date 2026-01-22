"""
Test suite for Director RBAC profile.

Tests FR-011 to FR-015 (Director profile requirements).
Coverage: Director inherits Manager + financial reports access.
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestRBACDirector(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.Company = cls.env['thedevkitchen.estate.company']
        cls.Property = cls.env['real.estate.property']
        cls.CommissionRule = cls.env['real.estate.commission.rule']
        cls.CommissionTransaction = cls.env['real.estate.commission.transaction']
        cls.User = cls.env['res.users']
        
        cls.director_group = cls.env.ref('quicksol_estate.group_real_estate_director')
        cls.manager_group = cls.env.ref('quicksol_estate.group_real_estate_manager')
        
        cls.company_a = cls.Company.create({
            'name': 'Company A',
            'cnpj': '11.222.333/0001-81',
            'creci': 'CRECI-SP 12345',
        })
        
        # Create property type for testing
        cls.property_type = cls.env['real.estate.property.type'].search([('name', '=', 'House')], limit=1)
        if not cls.property_type:
            cls.property_type = cls.env['real.estate.property.type'].create({'name': 'House'})

        # Create location type for testing
        cls.location_type = cls.env['real.estate.location.type'].search([('name', '=', 'Urban')], limit=1)
        if not cls.location_type:
            cls.location_type = cls.env['real.estate.location.type'].create({'name': 'Urban', 'code': 'URB'})

        # Create geographic state for testing
        cls.country = cls.env['res.country'].search([('code', '=', 'BR')], limit=1)
        if not cls.country:
            cls.country = cls.env['res.country'].create({'name': 'Brazil', 'code': 'BR'})
        
        cls.state = cls.env['real.estate.state'].search([('code', '=', 'SP')], limit=1)
        if not cls.state:
            cls.state = cls.env['real.estate.state'].create({
                'name': 'São Paulo',
                'code': 'SP',
                'country_id': cls.country.id
            })
        
        cls.director_user = cls.User.create({
            'name': 'Director User',
            'login': 'director@test.com',
            'email': 'director@test.com',
            'groups_id': [(6, 0, [cls.director_group.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        # Create agent for commission rule testing
        cls.test_agent = cls.env['real.estate.agent'].create({
            'user_id': cls.director_user.id,
            'name': 'Test Agent',
            'cpf': '123.456.789-00',
            'creci': 'CRECI-SP 77777',
            'company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        cls.property_a = cls.Property.create({
            'name': 'Property A1',
            'company_ids': [(6, 0, [cls.company_a.id])],
            'property_type_id': cls.property_type.id,
            'state_id': cls.state.id,
            'location_type_id': cls.location_type.id,
            'zip_code': '01310-100',
            'city': 'São Paulo',
            'street': 'Av Paulista',
            'street_number': '1000',
            'area': 100.0,
        })

    def test_director_inherits_manager_group(self):
        """T049.1: Director group should imply Manager group."""
        self.assertTrue(self.director_user.has_group('quicksol_estate.group_real_estate_manager'))
    
    def test_director_can_read_properties(self):
        """T049.2: Director can read properties (inherited from Manager)."""
        properties = self.Property.with_user(self.director_user).search([
            ('id', '=', self.property_a.id)
        ])
        
        self.assertEqual(len(properties), 1)
        self.assertEqual(properties.name, 'Property A1')
    
    def test_director_can_create_properties(self):
        """T049.3: Director can create properties (inherited from Manager)."""
        new_property = self.Property.with_user(self.director_user).create({
            'name': 'Property A2',
            'company_ids': [(6, 0, [self.company_a.id])],
            'property_type_id': self.property_type.id,
            'state_id': self.state.id,
            'location_type_id': self.location_type.id,
            'zip_code': '01310-100',
            'city': 'São Paulo',
            'street': 'Av Paulista',
            'street_number': '1000',
            'area': 100.0,
        })
        
        self.assertTrue(new_property.id)
        self.assertEqual(new_property.name, 'Property A2')
    
    def test_director_can_read_commission_transactions(self):
        """T049.4: Director can read commission transactions (financial reports)."""
        agent = self.env['real.estate.agent'].create({
            'name': 'Agent A1',
            'creci': 'CRECI-SP 99999',
            'company_ids': [(6, 0, [self.company_a.id])],
            'cpf': '222.333.444-15',
        })
        
        # Create commission rule
        rule = self.env['real.estate.commission.rule'].create({
            'agent_id': agent.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 5.0,
            'valid_from': '2024-01-01',
        })
        
        transaction = self.CommissionTransaction.create({
            'agent_id': agent.id,
            'rule_id': rule.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'transaction_date': '2026-01-15',
            'transaction_amount': 200000.00,
            'commission_amount': 10000.00,
            'rule_snapshot': '{"percentage": 5.0, "structure_type": "percentage"}',
        })
        
        transactions = self.CommissionTransaction.with_user(self.director_user).search([
            ('id', '=', transaction.id)
        ])
        
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions.commission_amount, 10000.00)
    
    def test_director_cannot_delete_commission_rules(self):
        """T049.5: Director cannot delete commission rules (read-only on financial config)."""
        rule = self.CommissionRule.create({
            'agent_id': self.test_agent.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 6.0,
            'valid_from': '2024-01-01',
        })
        
        with self.assertRaises(AccessError):
            rule.with_user(self.director_user).unlink()
    
    def test_director_cannot_create_users(self):
        """T049.6: Director cannot create users (only Owner can)."""
        with self.assertRaises(AccessError):
            self.User.with_user(self.director_user).create({
                'name': 'New User',
                'login': 'new_user@test.com',
                'email': 'new_user@test.com',
                'estate_company_ids': [(6, 0, [self.company_a.id])],
            })
    
    def test_director_inherits_manager_permissions(self):
        """T121: Director inherits all Manager permissions (group inheritance)."""
        # Verify director has manager group via implied_ids
        self.assertTrue(self.director_user.has_group('quicksol_estate.group_real_estate_manager'))
        
        # Verify director can perform manager actions
        property_b = self.Property.with_user(self.director_user).create({
            'name': 'Property Executive',
            'company_ids': [(6, 0, [self.company_a.id])],
            'property_type_id': self.property_type.id,
            'state_id': self.state.id,
            'location_type_id': self.location_type.id,
            'zip_code': '01310-100',
            'city': 'São Paulo',
            'street': 'Av Paulista',
            'street_number': '1000',
            'area': 100.0,
        })
        
        self.assertTrue(property_b.id)
    
    def test_director_views_financial_reports(self):
        """T122: Director can view financial reports (commission data)."""
        agent = self.env['real.estate.agent'].create({
            'name': 'Agent B',
            'creci': 'CRECI-SP 88888',
            'company_ids': [(6, 0, [self.company_a.id])],
            'cpf': '111.222.333-04',
        })
        
        # Create commission rule
        rule = self.env['real.estate.commission.rule'].create({
            'agent_id': agent.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 5.0,
            'valid_from': '2024-01-01',
        })
        
        # Create multiple transactions for reporting
        for i in range(3):
            self.CommissionTransaction.create({
                'agent_id': agent.id,
                'rule_id': rule.id,
                'company_id': self.company_a.id,
                'transaction_type': 'sale',
                'transaction_date': '2026-01-15',
                'transaction_amount': 100000.00 * (i + 1),
                'commission_amount': 5000.00 * (i + 1),
                'rule_snapshot': '{"percentage": 5.0, "structure_type": "percentage"}',
            })
        
        # Director generates financial report
        transactions = self.CommissionTransaction.with_user(self.director_user).search([
            ('company_id', '=', self.company_a.id)
        ])
        
        self.assertEqual(len(transactions), 3)
        total = sum(transactions.mapped('commission_amount'))
        self.assertEqual(total, 30000.00)  # 5000 + 10000 + 15000
    
    def test_director_accesses_bi_dashboards(self):
        """T123: Director can access business intelligence dashboards (property metrics)."""
        # Create multiple properties for BI analysis
        for i in range(5):
            self.Property.create({
                'name': f'Property BI {i+1}',
                'company_ids': [(6, 0, [self.company_a.id])],
                'property_type_id': self.property_type.id,
                'state_id': self.state.id,
                'location_type_id': self.location_type.id,
                'zip_code': '01310-100',
                'city': 'São Paulo',
                'street': 'Av Paulista',
                'street_number': '1000',
                'area': 100.0,
            })
        
        # Director accesses dashboard data (property count, value aggregation)
        all_properties = self.Property.with_user(self.director_user).search([
            ('company_ids', 'in', [self.company_a.id])
        ])
        
        # Verify access to aggregated data
        self.assertGreaterEqual(len(all_properties), 6)  # 1 from setup + 5 new
        
        # Verify can access commission aggregations
        commission_rules = self.CommissionRule.with_user(self.director_user).search([
            ('company_id', '=', self.company_a.id)
        ])
        
        # Director should have read access to financial configuration
        self.assertIsNotNone(commission_rules)
