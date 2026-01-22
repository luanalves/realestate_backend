"""
Test suite for CommissionSplitObserver.

Tests observer pattern for automatic commission transaction creation on sale.
Coverage: event handling, split calculation, transaction creation, edge cases.
"""
from odoo.tests.common import TransactionCase
from odoo.addons.quicksol_estate.models.event_bus import EventBus
from odoo.addons.quicksol_estate.models.observers.commission_split_observer import CommissionSplitObserver


class TestCommissionSplitObserver(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.Company = cls.env['thedevkitchen.estate.company']
        cls.Property = cls.env['real.estate.property']
        cls.Agent = cls.env['real.estate.agent']
        cls.Sale = cls.env['real.estate.sale']
        cls.CommissionRule = cls.env['real.estate.commission.rule']
        cls.CommissionTransaction = cls.env['real.estate.commission_transaction']
        
        cls.company_a = cls.Company.create({
            'name': 'Company A',
            'cnpj': '12.345.678/0001-90',
            'creci': 'CRECI-SP 12345',
        })
        
        # Create prospector agent
        cls.prospector_agent = cls.Agent.create({
            'name': 'Prospector Agent',
            'creci': 'CRECI-SP 99999',
            'company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        # Create selling agent
        cls.selling_agent = cls.Agent.create({
            'name': 'Selling Agent',
            'creci': 'CRECI-SP 88888',
            'company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        # Create commission rule for selling agent
        cls.commission_rule = cls.CommissionRule.create({
            'agent_id': cls.selling_agent.id,
            'company_id': cls.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 6.0,
            'valid_from': '2024-01-01',
        })
        
        # Create property with both prospector and agent
        cls.property_with_split = cls.Property.create({
            'name': 'Property with Split',
            'prospector_id': cls.prospector_agent.id,
            'agent_id': cls.selling_agent.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        cls.observer = CommissionSplitObserver()
        cls.event_bus = cls.env['quicksol.event.bus']
    
    def test_observer_creates_commission_transactions_on_sale(self):
        """T099.1: Observer creates 2 commission transactions when sale is created."""
        # Create sale (triggers observer via EventBus)
        sale = self.Sale.create({
            'property_id': self.property_with_split.id,
            'buyer_name': 'Test Buyer',
            'sale_date': '2024-06-15',
            'sale_price': 500000.00,
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        # Search for commission transactions
        prospector_transaction = self.CommissionTransaction.search([
            ('agent_id', '=', self.prospector_agent.id),
            ('property_id', '=', self.property_with_split.id),
        ])
        
        agent_transaction = self.CommissionTransaction.search([
            ('agent_id', '=', self.selling_agent.id),
            ('property_id', '=', self.property_with_split.id),
        ])
        
        # Both transactions should exist
        self.assertEqual(len(prospector_transaction), 1)
        self.assertEqual(len(agent_transaction), 1)
        
        # Verify amounts (6% of R$ 500,000 = R$ 30,000, split 30/70)
        self.assertAlmostEqual(prospector_transaction.amount, 9000.00, places=2)
        self.assertAlmostEqual(agent_transaction.amount, 21000.00, places=2)
    
    def test_observer_skips_sale_without_prospector(self):
        """T099.2: Observer does NOT create split transactions when property has no prospector."""
        property_no_prospector = self.Property.create({
            'name': 'Property No Prospector',
            'agent_id': self.selling_agent.id,
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        # Create sale
        sale = self.Sale.create({
            'property_id': property_no_prospector.id,
            'buyer_name': 'Test Buyer',
            'sale_date': '2024-06-15',
            'sale_price': 500000.00,
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        # Search for prospector transaction (should not exist)
        prospector_transaction = self.CommissionTransaction.search([
            ('agent_id', '=', self.prospector_agent.id),
            ('property_id', '=', property_no_prospector.id),
        ])
        
        self.assertEqual(len(prospector_transaction), 0, "No split transaction should be created")
    
    def test_observer_skips_sale_when_prospector_equals_agent(self):
        """T099.3: Observer does NOT create split when prospector_id == agent_id."""
        property_same_agent = self.Property.create({
            'name': 'Property Same Agent',
            'prospector_id': self.selling_agent.id,
            'agent_id': self.selling_agent.id,
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        # Create sale
        sale = self.Sale.create({
            'property_id': property_same_agent.id,
            'buyer_name': 'Test Buyer',
            'sale_date': '2024-06-15',
            'sale_price': 500000.00,
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        # Search for commission transactions
        transactions = self.CommissionTransaction.search([
            ('property_id', '=', property_same_agent.id),
        ])
        
        # No split transactions should be created
        self.assertEqual(len(transactions), 0, "No split when prospector == agent")
    
    def test_observer_uses_correct_split_percentage(self):
        """T099.4: Observer uses system parameter for split percentage."""
        # Change split percentage to 40%
        self.env['ir.config_parameter'].sudo().set_param(
            'quicksol_estate.prospector_commission_percentage',
            '0.40'
        )
        
        # Create sale
        sale = self.Sale.create({
            'property_id': self.property_with_split.id,
            'buyer_name': 'Test Buyer',
            'sale_date': '2024-06-15',
            'sale_price': 500000.00,
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        # Search transactions
        prospector_transaction = self.CommissionTransaction.search([
            ('agent_id', '=', self.prospector_agent.id),
            ('property_id', '=', self.property_with_split.id),
        ], order='create_date desc', limit=1)
        
        agent_transaction = self.CommissionTransaction.search([
            ('agent_id', '=', self.selling_agent.id),
            ('property_id', '=', self.property_with_split.id),
        ], order='create_date desc', limit=1)
        
        # Verify amounts (6% of R$ 500,000 = R$ 30,000, split 40/60)
        self.assertAlmostEqual(prospector_transaction.amount, 12000.00, places=2)
        self.assertAlmostEqual(agent_transaction.amount, 18000.00, places=2)
        
        # Reset to default
        self.env['ir.config_parameter'].sudo().set_param(
            'quicksol_estate.prospector_commission_percentage',
            '0.30'
        )
    
    def test_observer_handles_sale_without_commission_rule(self):
        """T099.5: Observer handles sale gracefully when no commission rule exists."""
        # Create property with prospector/agent but no commission rule
        agent_no_rule = self.Agent.create({
            'name': 'Agent No Rule',
            'cpf': '777.888.999-00',
            'creci': 'CRECI-SP 77777',
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        property_no_rule = self.Property.create({
            'name': 'Property No Rule',
            'prospector_id': self.prospector_agent.id,
            'agent_id': agent_no_rule.id,
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        # Create sale (should not raise exception)
        sale = self.Sale.create({
            'property_id': property_no_rule.id,
            'buyer_name': 'Test Buyer',
            'sale_date': '2024-06-15',
            'sale_price': 500000.00,
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        # No transactions should be created
        transactions = self.CommissionTransaction.search([
            ('property_id', '=', property_no_rule.id),
        ])
        
        self.assertEqual(len(transactions), 0)
    
    def test_observer_ignores_other_events(self):
        """T099.6: Observer ignores events other than sale.created."""
        # Manually call observer with wrong event
        self.observer.handle('property.created', self.property_with_split, env=self.env)
        
        # No transactions should be created
        transactions = self.CommissionTransaction.search([
            ('property_id', '=', self.property_with_split.id),
        ])
        
        self.assertEqual(len(transactions), 0)
    
    def test_observer_transaction_has_correct_metadata(self):
        """T099.7: Commission transactions have correct metadata (date, type, notes)."""
        sale = self.Sale.create({
            'property_id': self.property_with_split.id,
            'buyer_name': 'Test Buyer',
            'sale_date': '2024-06-15',
            'sale_price': 500000.00,
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        prospector_transaction = self.CommissionTransaction.search([
            ('agent_id', '=', self.prospector_agent.id),
            ('property_id', '=', self.property_with_split.id),
        ])
        
        # Verify metadata
        self.assertEqual(prospector_transaction.transaction_type, 'sale')
        self.assertEqual(str(prospector_transaction.transaction_date), '2024-06-15')
        self.assertIn('Prospector commission split', prospector_transaction.notes)
        self.assertIn(str(sale.id), prospector_transaction.notes)
