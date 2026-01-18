# -*- coding: utf-8 -*-
"""
Tests for Agent Performance Metrics (User Story 5)

This module tests:
- Computed performance fields (total_sales_count, total_commissions, active_properties_count)
- PerformanceService aggregation logic
- Date range filtering
- Multi-tenant isolation for performance metrics
- Performance ranking endpoint

Test Pattern: TDD - Tests written before implementation
Coverage Target: ≥80%
"""

import logging
from datetime import date, timedelta
from odoo.tests import TransactionCase
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class TestAgentPerformance(TransactionCase):
    """Test suite for agent performance metrics and ranking"""

    def setUp(self):
        super(TestAgentPerformance, self).setUp()
        
        # Create two companies for isolation testing
        self.company_a = self.env['thedevkitchen.estate.company'].create({
            'name': 'Imobiliária A Performance',
            'cnpj': '12.345.678/0001-95',
            'active': True,
        })
        
        self.company_b = self.env['thedevkitchen.estate.company'].create({
            'name': 'Imobiliária B Performance',
            'cnpj': '98.765.432/0001-98',
            'active': True,
        })
        
        # Create agents for company A
        self.agent_a1 = self.env['real.estate.agent'].create({
            'name': 'Agent A1 - Top Performer',
            'email': 'agent.a1@test.com',
            'company_id': self.company_a.id,
            'active': True,
        })
        
        self.agent_a2 = self.env['real.estate.agent'].create({
            'name': 'Agent A2 - Average',
            'email': 'agent.a2@test.com',
            'company_id': self.company_a.id,
            'active': True,
        })
        
        # Create agent for company B
        self.agent_b1 = self.env['real.estate.agent'].create({
            'name': 'Agent B1 - Company B',
            'email': 'agent.b1@test.com',
            'company_id': self.company_b.id,
            'active': True,
        })
        
        # Create commission rules for testing
        today = date.today()
        
        self.rule_a1 = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_a1.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 3.0,
            'valid_from': today - timedelta(days=30),
            'valid_until': today + timedelta(days=365),
        })
        
        self.rule_a2 = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_a2.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 2.5,
            'valid_from': today - timedelta(days=30),
            'valid_until': today + timedelta(days=365),
        })
    
    def test_get_agent_performance(self):
        """
        Test basic agent performance retrieval
        
        Scenario:
        - Agent A1 has 3 commission transactions totaling R$ 45,000
        - Performance should show total_sales_count=3, total_commissions=R$ 45,000
        """
        # Create 3 transactions for agent A1
        transactions = []
        for i in range(3):
            transaction = self.env['real.estate.commission.transaction'].create({
                'agent_id': self.agent_a1.id,
                'rule_id': self.rule_a1.id,
                'company_id': self.company_a.id,
                'transaction_type': 'sale',
                'transaction_amount': 500000.00,  # R$ 500k each
                'commission_amount': 15000.00,  # 3% = R$ 15k each
                'rule_snapshot': '{"percentage": 3.0, "structure_type": "percentage"}',
                'transaction_date': date.today(),
                'transaction_reference': f'SALE-TEST-{i}',
                'payment_status': 'pending',
            })
            transactions.append(transaction)
        
        # Force recompute of computed fields
        self.agent_a1.invalidate_recordset()
        
        # Verify computed fields (use set comparison since order may vary)
        self.assertEqual(set(self.agent_a1.commission_transaction_ids.ids), {t.id for t in transactions},
                        'Agent should have 3 commission transactions')
        
        # Note: total_sales_count and total_commissions will be tested after implementation
        # Expected: total_sales_count = 3, total_commissions = 45000.00
    
    def test_performance_metrics_calculation(self):
        """
        Test performance metrics calculation accuracy
        
        Scenario:
        - Agent A1: 5 sales, R$ 75,000 in commissions
        - Agent A2: 2 sales, R$ 20,000 in commissions
        - Verify accurate aggregation and average calculation
        """
        today = date.today()
        
        # Create 5 transactions for agent A1 (R$ 15k each = R$ 75k total)
        for i in range(5):
            self.env['real.estate.commission.transaction'].create({
                'agent_id': self.agent_a1.id,
                'rule_id': self.rule_a1.id,
                'company_id': self.company_a.id,
                'transaction_type': 'sale',
                'transaction_amount': 500000.00,
                'commission_amount': 15000.00,
                'rule_snapshot': '{"percentage": 3.0}',
                'transaction_date': today,
                'transaction_reference': f'A1-SALE-{i}',
                'payment_status': 'pending',
            })
        
        # Create 2 transactions for agent A2 (R$ 10k each = R$ 20k total)
        for i in range(2):
            self.env['real.estate.commission.transaction'].create({
                'agent_id': self.agent_a2.id,
                'rule_id': self.rule_a2.id,
                'company_id': self.company_a.id,
                'transaction_type': 'sale',
                'transaction_amount': 400000.00,
                'commission_amount': 10000.00,
                'rule_snapshot': '{"percentage": 2.5}',
                'transaction_date': today,
                'transaction_reference': f'A2-SALE-{i}',
                'payment_status': 'pending',
            })
        
        # Recompute
        self.agent_a1.invalidate_recordset()
        self.agent_a2.invalidate_recordset()
        
        # Expected after implementation:
        # Agent A1: total_sales_count=5, total_commissions=75000.00, avg_commission=15000.00
        # Agent A2: total_sales_count=2, total_commissions=20000.00, avg_commission=10000.00
    
    def test_performance_date_filtering(self):
        """
        Test performance metrics with date range filtering
        
        Scenario:
        - Create transactions across 3 months
        - Filter by date range
        - Verify only transactions within range are counted
        """
        today = date.today()
        
        # Month 1: 2 transactions (R$ 30k)
        for i in range(2):
            self.env['real.estate.commission.transaction'].create({
                'agent_id': self.agent_a1.id,
                'rule_id': self.rule_a1.id,
                'company_id': self.company_a.id,
                'transaction_type': 'sale',
                'transaction_amount': 500000.00,
                'commission_amount': 15000.00,
                'rule_snapshot': '{"percentage": 3.0}',
                'transaction_date': today - timedelta(days=60),  # 2 months ago
                'transaction_reference': f'MONTH1-{i}',
                'payment_status': 'paid',
                'payment_date': today - timedelta(days=60),
            })
        
        # Month 2: 3 transactions (R$ 45k)
        for i in range(3):
            self.env['real.estate.commission.transaction'].create({
                'agent_id': self.agent_a1.id,
                'rule_id': self.rule_a1.id,
                'company_id': self.company_a.id,
                'transaction_type': 'sale',
                'transaction_amount': 500000.00,
                'commission_amount': 15000.00,
                'rule_snapshot': '{"percentage": 3.0}',
                'transaction_date': today - timedelta(days=30),  # 1 month ago
                'transaction_reference': f'MONTH2-{i}',
                'payment_status': 'paid',
                'payment_date': today - timedelta(days=30),
            })
        
        # Month 3 (current): 1 transaction (R$ 15k)
        self.env['real.estate.commission.transaction'].create({
            'agent_id': self.agent_a1.id,
            'rule_id': self.rule_a1.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'transaction_amount': 500000.00,
            'commission_amount': 15000.00,
            'rule_snapshot': '{"percentage": 3.0}',
            'transaction_date': today,
            'transaction_reference': 'MONTH3-0',
            'payment_status': 'pending',
        })
        
        # Test PerformanceService with date filtering (after implementation)
        # Expected with date_from = today - 40 days, date_to = today - 20 days:
        # Should only count Month 2 transactions: 3 sales, R$ 45k
    
    def test_performance_multi_tenant_isolation(self):
        """
        Test multi-tenant isolation for performance metrics
        
        Scenario:
        - Agent A1 (Company A): 3 transactions, R$ 45k
        - Agent B1 (Company B): 5 transactions, R$ 100k
        - Verify Company A cannot see Company B metrics
        - Verify ranking is per-company only
        """
        today = date.today()
        
        # Create rule for agent B1
        rule_b1 = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_b1.id,
            'company_id': self.company_b.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 4.0,
            'valid_from': today - timedelta(days=30),
            'valid_until': today + timedelta(days=365),
        })
        
        # Agent A1: 3 transactions, R$ 45k total
        for i in range(3):
            self.env['real.estate.commission.transaction'].create({
                'agent_id': self.agent_a1.id,
                'rule_id': self.rule_a1.id,
                'company_id': self.company_a.id,
                'transaction_type': 'sale',
                'transaction_amount': 500000.00,
                'commission_amount': 15000.00,
                'rule_snapshot': '{"percentage": 3.0}',
                'transaction_date': today,
                'transaction_reference': f'A1-SALE-{i}',
                'payment_status': 'pending',
            })
        
        # Agent B1: 5 transactions, R$ 100k total (higher commission %, higher amount)
        for i in range(5):
            self.env['real.estate.commission.transaction'].create({
                'agent_id': self.agent_b1.id,
                'rule_id': rule_b1.id,
                'company_id': self.company_b.id,
                'transaction_type': 'sale',
                'transaction_amount': 500000.00,
                'commission_amount': 20000.00,  # 4% = R$ 20k each
                'rule_snapshot': '{"percentage": 4.0}',
                'transaction_date': today,
                'transaction_reference': f'B1-SALE-{i}',
                'payment_status': 'pending',
            })
        
        # Verify isolation via ORM search with company domain
        company_a_transactions = self.env['real.estate.commission.transaction'].search([
            ('company_id', '=', self.company_a.id)
        ])
        
        company_b_transactions = self.env['real.estate.commission.transaction'].search([
            ('company_id', '=', self.company_b.id)
        ])
        
        self.assertEqual(len(company_a_transactions), 3, 'Company A should have 3 transactions')
        self.assertEqual(len(company_b_transactions), 5, 'Company B should have 5 transactions')
        
        # Verify no cross-company contamination
        for transaction in company_a_transactions:
            self.assertEqual(transaction.company_id.id, self.company_a.id,
                           'Company A transactions should not leak to Company B')
        
        for transaction in company_b_transactions:
            self.assertEqual(transaction.company_id.id, self.company_b.id,
                           'Company B transactions should not leak to Company A')
        
        # Test PerformanceService ranking isolation (after implementation)
        # Expected: get_top_agents_ranking(company_id=company_a.id) should return only Agent A1, A2
        # Expected: get_top_agents_ranking(company_id=company_b.id) should return only Agent B1
    
    def test_active_properties_count(self):
        """
        Test active_properties_count computed field
        
        Scenario:
        - Agent A1 has 3 active property assignments
        - Agent A2 has 1 active assignment
        - Verify count is accurate
        """
        # Note: This test assumes property model exists from previous phases
        # Will implement after _compute_active_properties_count is created
        pass
    
    def test_performance_service_caching(self):
        """
        Test Redis caching for performance metrics
        
        Scenario:
        - Call get_agent_performance twice with same parameters
        - Second call should hit cache (verify via Redis TTL)
        - Verify cache invalidation after new transaction
        """
        # Note: Will implement after PerformanceService with Redis caching is created
        # Expected: Cache key format = "performance:agent:{agent_id}:{date_from}:{date_to}"
        # Expected: TTL = 300 seconds (5 minutes)
        pass
    
    def test_average_commission_calculation(self):
        """
        Test average commission per transaction calculation
        
        Scenario:
        - Agent A1: 4 transactions with varying commission amounts
        - Verify average = total_commissions / transaction_count
        """
        today = date.today()
        
        commission_amounts = [10000.00, 15000.00, 20000.00, 25000.00]  # Total = 70k, Avg = 17.5k
        
        for i, amount in enumerate(commission_amounts):
            self.env['real.estate.commission.transaction'].create({
                'agent_id': self.agent_a1.id,
                'rule_id': self.rule_a1.id,
                'company_id': self.company_a.id,
                'transaction_type': 'sale',
                'transaction_amount': amount / 0.03,  # Reverse calculate transaction amount
                'commission_amount': amount,
                'rule_snapshot': '{"percentage": 3.0}',
                'transaction_date': today,
                'transaction_reference': f'VAR-COMMISSION-{i}',
                'payment_status': 'pending',
            })
        
        # Expected after PerformanceService implementation:
        # total_commissions = 70000.00
        # transaction_count = 4
        # average_commission = 17500.00
