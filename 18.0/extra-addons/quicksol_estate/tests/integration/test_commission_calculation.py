# -*- coding: utf-8 -*-
"""
Test Suite: Commission Rule Calculation and Management

Tests commission rule creation, validation, calculation logic, and
non-retroactive application following ADR-003 test coverage requirements.

Author: Quicksol Technologies
Date: 2026-01-12
User Story: US4 - Configurar Comissões de Agentes (P4)
ADRs: ADR-003 (Test Coverage ≥80%), ADR-008 (Multi-tenancy)
"""

from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import json

# Import CommissionService
from odoo.addons.quicksol_estate.services.commission_service import CommissionService


class TestCommissionCalculation(TransactionCase):
    """Test commission rule creation, validation, and calculation"""
    
    def setUp(self):
        """Setup test data: companies, agents, commission rules"""
        super().setUp()
        
        # Create companies with valid CNPJs
        self.company_a = self.env['thedevkitchen.estate.company'].create({
            'name': 'Imobiliária Alpha',
            'cnpj': '12.345.678/0001-95',  # Valid CNPJ with check digits
            'street': 'Rua Alpha, 100',
            'city': 'São Paulo',
        })
        
        self.company_b = self.env['thedevkitchen.estate.company'].create({
            'name': 'Imobiliária Beta',
            'cnpj': '98.765.432/0001-98',  # Valid CNPJ with check digits
            'street': 'Rua Beta, 200',
            'city': 'Rio de Janeiro',
        })
        
        # Create agents
        self.agent_1 = self.env['real.estate.agent'].create({
            'name': 'João Silva',
            'cpf': '123.456.789-00',
            'email': 'joao@example.com',
            'phone': '+55 11 99999-9999',
            'creci': 'CRECI/SP 12345',
            'company_id': self.company_a.id,
            'active': True,
        })
        
        self.agent_2 = self.env['real.estate.agent'].create({
            'name': 'Maria Santos',
            'cpf': '987.654.321-00',
            'email': 'maria@example.com',
            'phone': '+55 21 98888-8888',
            'creci': 'CRECI/RJ 67890',
            'company_id': self.company_a.id,
            'active': True,
        })
        
        self.agent_3 = self.env['real.estate.agent'].create({
            'name': 'Pedro Costa',
            'cpf': '111.222.333-44',
            'email': 'pedro@example.com',
            'phone': '+55 21 97777-7777',
            'creci': 'CRECI/RJ 11111',
            'company_id': self.company_b.id,
            'active': True,
        })
    
    # ==================== T067: Test Create Commission Rule ====================
    
    def test_create_commission_rule(self):
        """Test: Should create commission rule with valid data"""
        # Arrange
        rule_data = {
            'agent_id': self.agent_1.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 3.0,  # 3% commission
            'fixed_amount': 0.0,
            'min_value': 100000.0,
            'max_value': 5000000.0,
            'valid_from': datetime.now().date(),
            'valid_until': (datetime.now() + timedelta(days=365)).date(),
            'active': True,
        }
        
        # Act
        rule = self.env['real.estate.commission.rule'].create(rule_data)
        
        # Assert
        self.assertTrue(rule.id, "Commission rule should be created")
        self.assertEqual(rule.agent_id.id, self.agent_1.id, "Agent should match")
        self.assertEqual(rule.company_id.id, self.company_a.id, "Company should match")
        self.assertEqual(rule.transaction_type, 'sale', "Transaction type should be 'sale'")
        self.assertEqual(rule.structure_type, 'percentage', "Structure should be 'percentage'")
        self.assertEqual(rule.percentage, 3.0, "Percentage should be 3.0")
        self.assertTrue(rule.is_active, "Rule should be active based on valid dates")
    
    # ==================== T068: Test Calculate Percentage Commission ====================
    
    def test_calculate_commission_percentage(self):
        """Test: Should calculate correct commission for percentage-based rule"""
        # Arrange - Create percentage-based commission rule (3%)
        rule = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_1.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 3.0,
            'fixed_amount': 0.0,
            'min_value': 100000.0,
            'max_value': 5000000.0,
            'valid_from': datetime.now().date(),
            'valid_until': (datetime.now() + timedelta(days=365)).date(),
        })
        
        # Act - Calculate commission for R$ 500.000,00 sale
        transaction_amount = 500000.00
        service = CommissionService(self.env)
        commission = service.calculate_commission(rule, transaction_amount)
        
        # Assert
        expected_commission = 500000.00 * 0.03  # 3% = R$ 15.000,00
        self.assertEqual(commission, expected_commission, 
                        f"Commission should be R$ {expected_commission:,.2f}")
        self.assertEqual(commission, 15000.00, "Commission should be R$ 15.000,00")
    
    # ==================== T069: Test Calculate Fixed Amount Commission ====================
    
    def test_calculate_commission_fixed_amount(self):
        """Test: Should return fixed amount regardless of transaction value"""
        # Arrange - Create fixed-amount commission rule (R$ 10.000,00)
        rule = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_1.id,
            'company_id': self.company_a.id,
            'transaction_type': 'rental',
            'structure_type': 'fixed',
            'percentage': 0.0,
            'fixed_amount': 10000.00,
            'min_value': 0.0,
            'max_value': 999999999.99,
            'valid_from': datetime.now().date(),
            'valid_until': (datetime.now() + timedelta(days=365)).date(),
        })
        
        # Act - Calculate commission for R$ 5.000,00/month rental
        transaction_amount = 5000.00
        service = CommissionService(self.env)
        commission = service.calculate_commission(rule, transaction_amount)
        
        # Assert
        self.assertEqual(commission, 10000.00, "Commission should be fixed R$ 10.000,00")
        
        # Verify it's same for different transaction amounts
        service = CommissionService(self.env)
        commission_high = service.calculate_commission(rule, 50000.00)
        self.assertEqual(commission_high, 10000.00, 
                        "Fixed commission should be same for high value")
    
    # ==================== T070: Test Non-Retroactive Rule Application ====================
    
    def test_commission_rule_non_retroactive(self):
        """Test: Should apply commission rules only to future transactions (non-retroactive)"""
        # Arrange - Create rule with future valid_from date
        future_date = datetime.now().date() + timedelta(days=30)
        past_date = datetime.now().date() - timedelta(days=30)
        
        # Create rule valid from 30 days in the future
        future_rule = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_1.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 5.0,
            'fixed_amount': 0.0,
            'min_value': 0.0,
            'max_value': 999999999.99,
            'valid_from': future_date,
            'valid_until': future_date + timedelta(days=365),
        })
        
        # Create rule that expired 30 days ago
        expired_rule = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_1.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 2.0,
            'fixed_amount': 0.0,
            'min_value': 0.0,
            'max_value': 999999999.99,
            'valid_from': past_date - timedelta(days=365),
            'valid_until': past_date,
        })
        
        # Create active rule for today
        current_rule = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_1.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 3.0,
            'fixed_amount': 0.0,
            'min_value': 0.0,
            'max_value': 999999999.99,
            'valid_from': datetime.now().date(),
            'valid_until': datetime.now().date() + timedelta(days=365),
        })
        
        # Act & Assert
        self.assertFalse(future_rule.is_active, "Future rule should not be active")
        self.assertFalse(expired_rule.is_active, "Expired rule should not be active")
        self.assertTrue(current_rule.is_active, "Current rule should be active")
        
        # Verify service returns only active rule
        service = CommissionService(self.env)
        active_rule = service.get_active_rule_for_agent(
            self.agent_1.id, 'sale'
        )
        
        self.assertEqual(active_rule.id, current_rule.id, 
                        "Should return only the currently active rule")
        self.assertEqual(active_rule.percentage, 3.0, 
                        "Active rule should have 3% commission")
    
    # ==================== T071: Test Multi-Agent Commission Split ====================
    
    def test_multi_agent_commission_split(self):
        """Test: Should handle commission split between multiple agents on same property"""
        # Arrange - Create commission rules for 2 agents
        rule_agent_1 = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_1.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 3.0,  # 3% commission
            'fixed_amount': 0.0,
            'min_value': 0.0,
            'max_value': 999999999.99,
            'valid_from': datetime.now().date(),
            'valid_until': datetime.now().date() + timedelta(days=365),
        })
        
        rule_agent_2 = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_2.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 2.0,  # 2% commission (secondary agent)
            'fixed_amount': 0.0,
            'min_value': 0.0,
            'max_value': 999999999.99,
            'valid_from': datetime.now().date(),
            'valid_until': datetime.now().date() + timedelta(days=365),
        })
        
        # Act - Calculate commissions for R$ 1.000.000,00 sale
        transaction_amount = 1000000.00
        service = CommissionService(self.env)
        
        commission_1 = service.calculate_commission(
            rule_agent_1, transaction_amount
        )
        
        commission_2 = service.calculate_commission(
            rule_agent_2, transaction_amount
        )
        
        # Assert
        self.assertEqual(commission_1, 30000.00, 
                        "Agent 1 commission should be R$ 30.000,00 (3%)")
        self.assertEqual(commission_2, 20000.00, 
                        "Agent 2 commission should be R$ 20.000,00 (2%)")
        
        total_commission = commission_1 + commission_2
        self.assertEqual(total_commission, 50000.00, 
                        "Total commission split should be R$ 50.000,00 (5%)")
        
        # Verify each agent has their own rule
        self.assertNotEqual(rule_agent_1.id, rule_agent_2.id, 
                           "Each agent should have separate rule")
        self.assertEqual(rule_agent_1.agent_id.id, self.agent_1.id, 
                        "Rule 1 should belong to Agent 1")
        self.assertEqual(rule_agent_2.agent_id.id, self.agent_2.id, 
                        "Rule 2 should belong to Agent 2")
    
    # ==================== Additional Validation Tests ====================
    
    def test_percentage_range_validation(self):
        """Test: Should reject commission percentage outside 0-100 range"""
        # Test percentage > 100
        with self.assertRaises(ValidationError, msg="Should reject percentage > 100"):
            self.env['real.estate.commission.rule'].create({
                'agent_id': self.agent_1.id,
                'company_id': self.company_a.id,
                'transaction_type': 'sale',
                'structure_type': 'percentage',
                'percentage': 150.0,  # Invalid: > 100%
                'fixed_amount': 0.0,
                'valid_from': datetime.now().date(),
                'valid_until': datetime.now().date() + timedelta(days=365),
            })
        
        # Test negative percentage - database constraint will raise psycopg2.IntegrityError
        from psycopg2 import IntegrityError
        with self.assertRaises(IntegrityError, msg="Should reject negative percentage"):
            with self.env.cr.savepoint():
                self.env['real.estate.commission.rule'].create({
                    'agent_id': self.agent_1.id,
                    'company_id': self.company_a.id,
                    'transaction_type': 'sale',
                    'structure_type': 'percentage',
                    'percentage': -5.0,  # Invalid: negative
                    'fixed_amount': 0.0,
                    'valid_from': datetime.now().date(),
                    'valid_until': datetime.now().date() + timedelta(days=365),
                })
    
    def test_company_isolation_commission_rules(self):
        """Test: Should isolate commission rules by company (multi-tenancy)"""
        # Arrange - Create rules for different companies
        rule_company_a = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_1.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 3.0,
            'valid_from': datetime.now().date(),
            'valid_until': datetime.now().date() + timedelta(days=365),
        })
        
        rule_company_b = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_3.id,
            'company_id': self.company_b.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 4.0,
            'valid_from': datetime.now().date(),
            'valid_until': datetime.now().date() + timedelta(days=365),
        })
        
        # Act - Search rules for Company A
        company_a_rules = self.env['real.estate.commission.rule'].search([
            ('company_id', '=', self.company_a.id)
        ])
        
        # Assert
        self.assertEqual(len(company_a_rules), 1, 
                        "Company A should have exactly 1 rule")
        self.assertEqual(company_a_rules[0].id, rule_company_a.id, 
                        "Should return Company A's rule")
        self.assertNotIn(rule_company_b.id, company_a_rules.ids, 
                        "Company A should NOT see Company B's rule")
    
    def test_transaction_snapshot_immutability(self):
        """Test: Should store immutable snapshot of rule at transaction time"""
        # Arrange - Create commission rule
        rule = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_1.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 3.0,
            'fixed_amount': 0.0,
            'valid_from': datetime.now().date(),
            'valid_until': datetime.now().date() + timedelta(days=365),
        })
        
        # Act - Create commission transaction with snapshot
        transaction = self.env['real.estate.commission.transaction'].create({
            'agent_id': self.agent_1.id,
            'company_id': self.company_a.id,
            'rule_id': rule.id,
            'transaction_type': 'sale',
            'transaction_amount': 500000.00,
            'commission_amount': 15000.00,
            'rule_snapshot': json.dumps({
                'percentage': rule.percentage,
                'structure_type': rule.structure_type,
                'transaction_type': rule.transaction_type,
                'valid_from': str(rule.valid_from),
                'valid_until': str(rule.valid_until),
            }),
            'calculated_at': datetime.now(),
        })
        
        # Modify original rule
        rule.write({'percentage': 5.0})
        
        # Assert - Snapshot should remain unchanged
        snapshot = json.loads(transaction.rule_snapshot)
        self.assertEqual(snapshot['percentage'], 3.0, 
                        "Snapshot should preserve original 3% percentage")
        self.assertNotEqual(snapshot['percentage'], rule.percentage, 
                           "Snapshot should differ from modified rule")
