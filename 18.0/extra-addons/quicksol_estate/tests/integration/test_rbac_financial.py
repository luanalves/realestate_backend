"""
Test suite for Financial RBAC profile.

Tests FR-021 to FR-025 (Financial profile requirements).
Coverage: Financial can CRUD commissions, read-only sales/leases.
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestRBACFinancial(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.Company = cls.env['thedevkitchen.estate.company']
        cls.Property = cls.env['real.estate.property']
        cls.CommissionRule = cls.env['real.estate.commission.rule']
        cls.CommissionTransaction = cls.env['real.estate.commission.transaction']
        cls.Sale = cls.env['real.estate.sale']
        cls.User = cls.env['res.users']
        
        cls.financial_group = cls.env.ref('quicksol_estate.group_real_estate_financial')
        
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
        
        cls.financial_user = cls.User.create({
            'name': 'Financial User',
            'login': 'financial@test.com',
            'email': 'financial@test.com',
            'groups_id': [(6, 0, [cls.financial_group.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        # Create agent for commission rule testing
        cls.test_agent = cls.env['real.estate.agent'].create({
            'user_id': cls.financial_user.id,
            'name': 'Test Agent',
            'cpf': '999.000.111-22',
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

    def test_financial_can_create_commission_rule(self):
        """T051.1: Financial can create commission rules."""
        rule = self.CommissionRule.with_user(self.financial_user).create({
            'agent_id': self.test_agent.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 6.0,
            'valid_from': '2024-01-01',
        })
        
        self.assertTrue(rule.id)
        self.assertEqual(rule.percentage, 6.0)
    
    def test_financial_can_update_commission_rule(self):
        """T051.2: Financial can update commission rules."""
        rule = self.CommissionRule.create({
            'agent_id': self.test_agent.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 8.0,
            'valid_from': '2024-01-01',
        })
        
        rule.with_user(self.financial_user).write({
            'percentage': 7.5
        })
        
        self.assertEqual(rule.percentage, 7.5)
    
    def test_financial_can_delete_commission_rule(self):
        """T051.3: Financial can delete commission rules."""
        rule = self.CommissionRule.create({
            'agent_id': self.test_agent.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 5.0,
            'valid_from': '2024-01-01',
        })
        
        rule.with_user(self.financial_user).unlink()
        
        self.assertFalse(rule.exists())
    
    def test_financial_can_create_commission_transaction(self):
        """T051.4: Financial can create commission transactions."""
        agent = self.env['real.estate.agent'].create({
            'name': 'Agent A1',
            'creci': 'CRECI-SP 99999',
            'company_ids': [(6, 0, [self.company_a.id])],
            'cpf': '555.666.777-48',
        })
        
        # Create commission rule first
        rule = self.CommissionRule.create({
            'agent_id': agent.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 5.0,
            'valid_from': '2024-01-01',
        })
        
        transaction = self.CommissionTransaction.with_user(self.financial_user).create({
            'agent_id': agent.id,
            'rule_id': rule.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'transaction_date': '2026-01-15',
            'transaction_amount': 300000.00,
            'commission_amount': 15000.00,
            'rule_snapshot': '{"percentage": 5.0, "structure_type": "percentage"}',
            'payment_status': 'paid',
            'payment_date': '2026-01-15',
        })
        
        self.assertTrue(transaction.id)
        self.assertEqual(transaction.commission_amount, 15000.00)
    
    def test_financial_can_read_sales(self):
        """T051.5: Financial can read sales (read-only)."""
        sale = self.Sale.create({
            'property_id': self.property_a.id,
            'sale_price': 500000.00,
            'company_ids': [(6, 0, [self.company_a.id])],
            'buyer_name': 'Test Buyer',
            'sale_date': '2026-01-15',
        })
        
        sales = self.Sale.with_user(self.financial_user).search([
            ('id', '=', sale.id)
        ])
        
        self.assertEqual(len(sales), 1)
        self.assertEqual(sales.sale_price, 500000.00)
    
    def test_financial_cannot_edit_sales(self):
        """T051.6: Financial cannot edit sales (read-only)."""
        sale = self.Sale.create({
            'property_id': self.property_a.id,
            'sale_price': 500000.00,
            'company_ids': [(6, 0, [self.company_a.id])],
            'buyer_name': 'Test Buyer',
            'sale_date': '2026-01-15',
        })
        
        with self.assertRaises(AccessError):
            sale.with_user(self.financial_user).write({
                'sale_price': 550000.00
            })
    
    def test_financial_cannot_create_sales(self):
        """T051.7: Financial cannot create sales."""
        with self.assertRaises(AccessError):
            self.Sale.with_user(self.financial_user).create({
                'property_id': self.property_a.id,
                'sale_price': 600000.00,
                'company_ids': [(6, 0, [self.company_a.id])],
                'buyer_name': 'Test Buyer',
                'sale_date': '2026-01-15',
            })
    
    def test_financial_views_all_commissions(self):
        """T112: Financial can view all company commission transactions."""
        agent_a = self.env['real.estate.agent'].create({
            'name': 'Agent A',
            'creci': 'CRECI-SP 11111',
            'company_ids': [(6, 0, [self.company_a.id])],
            'cpf': '444.555.666-37',
        })
        
        agent_b = self.env['real.estate.agent'].create({
            'name': 'Agent B',
            'creci': 'CRECI-SP 22222',
            'company_ids': [(6, 0, [self.company_a.id])],
            'cpf': '333.444.555-26',
        })
        
        # Create commission rules for both agents
        rule_a = self.CommissionRule.create({
            'agent_id': agent_a.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 5.0,
            'valid_from': '2024-01-01',
        })
        
        rule_b = self.CommissionRule.create({
            'agent_id': agent_b.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 6.0,
            'valid_from': '2024-01-01',
        })
        
        # Create 2 transactions for different agents
        txn1 = self.CommissionTransaction.create({
            'agent_id': agent_a.id,
            'rule_id': rule_a.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'transaction_date': '2026-01-15',
            'transaction_amount': 200000.00,
            'commission_amount': 10000.00,
            'rule_snapshot': '{"percentage": 5.0, "structure_type": "percentage"}',
        })
        
        txn2 = self.CommissionTransaction.create({
            'agent_id': agent_b.id,
            'rule_id': rule_b.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'transaction_date': '2026-01-15',
            'transaction_amount': 250000.00,
            'commission_amount': 15000.00,
            'rule_snapshot': '{"percentage": 6.0, "structure_type": "percentage"}',
        })
        
        # Financial should see both transactions
        transactions = self.CommissionTransaction.with_user(self.financial_user).search([
            ('company_id', '=', self.company_a.id)
        ])
        
        self.assertIn(txn1, transactions)
        self.assertIn(txn2, transactions)
        self.assertEqual(len(transactions), 2)
    
    def test_financial_marks_commission_as_paid(self):
        """T113: Financial can mark commission transaction as paid."""
        agent = self.env['real.estate.agent'].create({
            'name': 'Agent C',
            'creci': 'CRECI-SP 33333',
            'company_ids': [(6, 0, [self.company_a.id])],
            'cpf': '222.333.444-15',
        })
        
        rule = self.CommissionRule.create({
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
            'transaction_amount': 240000.00,
            'commission_amount': 12000.00,
            'rule_snapshot': '{"percentage": 5.0, "structure_type": "percentage"}',
            'payment_status': 'pending',
        })
        
        # Financial marks as paid (disable mail tracking to avoid company context issues)
        transaction.with_user(self.financial_user).with_context(tracking_disable=True).write({
            'payment_status': 'paid',
            'payment_date': '2026-01-20',
        })
        
        self.assertEqual(transaction.payment_status, 'paid')
        self.assertEqual(transaction.payment_date.isoformat(), '2026-01-20')
    
    def test_financial_generates_commission_report(self):
        """T114: Financial can generate commission reports (view all data)."""
        agent = self.env['real.estate.agent'].create({
            'name': 'Agent D',
            'creci': 'CRECI-SP 44444',
            'company_ids': [(6, 0, [self.company_a.id])],
            'cpf': '111.222.333-04',
        })
        
        rule = self.CommissionRule.create({
            'agent_id': agent.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 5.0,
            'valid_from': '2024-01-01',
        })
        
        # Create multiple transactions
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
                'payment_status': 'paid',
                'payment_date': '2026-01-15',
            })
        
        # Financial generates report by searching all paid commissions
        paid_commissions = self.CommissionTransaction.with_user(self.financial_user).search([
            ('company_id', '=', self.company_a.id),
            ('payment_status', '=', 'paid')
        ])
        
        self.assertEqual(len(paid_commissions), 3)
        total_amount = sum(paid_commissions.mapped('commission_amount'))
        self.assertEqual(total_amount, 30000.00)  # 5000 + 10000 + 15000
    
    def test_financial_cannot_edit_properties(self):
        """T115: Financial cannot edit property details (negative test)."""
        with self.assertRaises(AccessError):
            self.property_a.with_user(self.financial_user).write({
                'price': 999999.00
            })
