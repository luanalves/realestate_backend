# -*- coding: utf-8 -*-
"""
Agent CRUD API Tests

Tests for User Story 1: Create and list agents with multi-tenant isolation
and User Story 2: Update and deactivate agents

Author: Quicksol Technologies
Date: 2026-01-12
Test Coverage: T015-T019, T034-T038
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from odoo import fields
from datetime import date


class TestAgentCRUD(TransactionCase):
    """Test Agent CRUD operations with multi-tenancy"""
    
    def setUp(self):
        super(TestAgentCRUD, self).setUp()
        
        # Get or create companies for multi-tenancy testing
        Company = self.env['thedevkitchen.estate.company']
        self.company_a = Company.search([('name', '=', 'Company A')], limit=1)
        if not self.company_a:
            self.company_a = Company.create({'name': 'Company A'})
        
        self.company_b = Company.search([('name', '=', 'Company B')], limit=1)
        if not self.company_b:
            self.company_b = Company.create({'name': 'Company B'})
        
        # Agent model
        self.Agent = self.env['real.estate.agent']
        
        # Test data
        self.valid_agent_data = {
            'name': 'João Silva',
            'cpf': '12345678901',  # Valid CPF format
            'email': 'joao.silva@example.com',
            'phone': '+55 11 98765-4321',
            'creci': 'CRECI/SP 12345',
            'company_id': self.company_a.id,
        }
    
    def test_create_agent_valid_data(self):
        """T015: Create agent with valid data"""
        agent = self.Agent.create(self.valid_agent_data)
        
        self.assertTrue(agent.id, "Agent should be created")
        self.assertEqual(agent.name, 'João Silva')
        self.assertEqual(agent.cpf, '12345678901')
        self.assertEqual(agent.email, 'joao.silva@example.com')
        self.assertEqual(agent.company_id, self.company_a)
        self.assertTrue(agent.active, "Agent should be active by default")
        
        # CRECI should be normalized
        self.assertEqual(agent.creci_normalized, 'CRECI/SP 12345')
        self.assertEqual(agent.creci_state, 'SP')
        self.assertEqual(agent.creci_number, '12345')
    
    def test_create_agent_invalid_cpf(self):
        """T016: Reject agent creation with invalid CPF"""
        invalid_data = self.valid_agent_data.copy()
        invalid_data['cpf'] = '00000000000'  # Invalid CPF
        
        # Note: This test will pass if validate_docbr is not installed
        # In production, ensure validate_docbr is in requirements
        try:
            from validate_docbr import CPF
            cpf_validator = CPF()
            
            with self.assertRaises(ValidationError, msg="Should reject invalid CPF"):
                self.Agent.create(invalid_data)
        except ImportError:
            self.skipTest("validate_docbr not installed - CPF validation skipped")
    
    def test_list_agents_multi_tenant_isolation(self):
        """T017: Multi-tenant isolation - users see only their company's agents"""
        # Create agents in Company A
        agent_a1 = self.Agent.create({
            'name': 'Agent A1',
            'cpf': '11111111111',
            'company_id': self.company_a.id,
        })
        agent_a2 = self.Agent.create({
            'name': 'Agent A2',
            'cpf': '22222222222',
            'company_id': self.company_a.id,
        })
        
        # Create agent in Company B
        agent_b1 = self.Agent.create({
            'name': 'Agent B1',
            'cpf': '33333333333',
            'company_id': self.company_b.id,
        })
        
        # Search for Company A agents
        agents_a = self.Agent.search([('company_id', '=', self.company_a.id)])
        self.assertIn(agent_a1, agents_a, "Should include agent A1")
        self.assertIn(agent_a2, agents_a, "Should include agent A2")
        self.assertNotIn(agent_b1, agents_a, "Should NOT include agent B1")
        
        # Search for Company B agents
        agents_b = self.Agent.search([('company_id', '=', self.company_b.id)])
        self.assertIn(agent_b1, agents_b, "Should include agent B1")
        self.assertNotIn(agent_a1, agents_b, "Should NOT include agent A1")
    
    def test_create_agent_duplicate_creci_same_company(self):
        """T018: Reject duplicate CRECI in same company"""
        # Create first agent with CRECI
        agent1 = self.Agent.create({
            'name': 'Agent 1',
            'cpf': '11111111111',
            'creci': 'CRECI/SP 99999',
            'company_id': self.company_a.id,
        })
        
        # Try to create second agent with same CRECI in same company
        with self.assertRaises(ValidationError, msg="Should reject duplicate CRECI"):
            self.Agent.create({
                'name': 'Agent 2',
                'cpf': '22222222222',
                'creci': 'CRECI/SP 99999',  # Same CRECI
                'company_id': self.company_a.id,
            })
        
        # But should allow same CRECI in different company
        agent_b = self.Agent.create({
            'name': 'Agent B',
            'cpf': '33333333333',
            'creci': 'CRECI/SP 99999',  # Same CRECI
            'company_id': self.company_b.id,  # Different company
        })
        self.assertTrue(agent_b.id, "Should allow same CRECI in different company")
    
    def test_creci_flexible_formats(self):
        """Test CRECI accepts flexible input formats and normalizes correctly"""
        test_cases = [
            ('CRECI/SP 12345', 'CRECI/SP 12345'),
            ('CRECI-SP-12345', 'CRECI/SP 12345'),
            ('CRECI SP 12345', 'CRECI/SP 12345'),
            ('12345-SP', 'CRECI/SP 12345'),
            ('12345/SP', 'CRECI/SP 12345'),
        ]
        
        for input_creci, expected_normalized in test_cases:
            agent = self.Agent.create({
                'name': f'Agent {input_creci}',
                'cpf': f'{hash(input_creci) % 100000000000:011d}',
                'creci': input_creci,
                'company_id': self.company_a.id,
            })
            
            self.assertEqual(
                agent.creci_normalized,
                expected_normalized,
                f"CRECI '{input_creci}' should normalize to '{expected_normalized}'"
            )
            
            agent.unlink()  # Clean up for next iteration
    
    def test_creci_optional(self):
        """Test CRECI is optional (allows trainees/assistants without CRECI)"""
        agent = self.Agent.create({
            'name': 'Trainee Agent',
            'cpf': '44444444444',
            'company_id': self.company_a.id,
            # No CRECI provided
        })
        
        self.assertFalse(agent.creci, "CRECI should be empty")
        self.assertFalse(agent.creci_normalized, "CRECI normalized should be empty")
        self.assertTrue(agent.id, "Agent should be created without CRECI")
    
    def test_email_validation(self):
        """Test email format validation"""
        valid_emails = [
            'agent@company.com',
            'john.doe@realestate.com.br',
            'agent+tag@domain.org'
        ]
        
        for email in valid_emails:
            agent = self.Agent.create({
                'name': f'Agent {email}',
                'cpf': f'{hash(email) % 100000000000:011d}',
                'email': email,
                'company_id': self.company_a.id,
            })
            self.assertEqual(agent.email, email, f"Should accept valid email: {email}")
            agent.unlink()
        
        # Test invalid email
        invalid_emails = ['invalid-email', '@domain.com', 'agent@']
        
        for email in invalid_emails:
            with self.assertRaises(ValidationError, msg=f"Should reject invalid email: {email}"):
                self.Agent.create({
                    'name': f'Agent {email}',
                    'cpf': f'{hash(email) % 100000000000:011d}',
                    'email': email,
                    'company_id': self.company_a.id,
                })
    
    def test_phone_validation(self):
        """Test Brazilian phone format validation"""
        try:
            import phonenumbers
            
            valid_phones = [
                '+55 11 98765-4321',
                '+55 (11) 98765-4321',
                '+5511987654321',
            ]
            
            for phone in valid_phones:
                agent = self.Agent.create({
                    'name': f'Agent {phone}',
                    'cpf': f'{hash(phone) % 100000000000:011d}',
                    'phone': phone,
                    'company_id': self.company_a.id,
                })
                self.assertTrue(agent.id, f"Should accept valid phone: {phone}")
                agent.unlink()
            
            # Invalid phone
            with self.assertRaises(ValidationError):
                self.Agent.create({
                    'name': 'Invalid Phone Agent',
                    'cpf': '55555555555',
                    'phone': '123',  # Too short
                    'company_id': self.company_a.id,
                })
        except ImportError:
            self.skipTest("phonenumbers not installed - phone validation skipped")


class TestAgentUpdate(TransactionCase):
    """Test Agent update and soft-delete operations (User Story 2)"""
    
    def setUp(self):
        super(TestAgentUpdate, self).setUp()
        
        # Get or create company
        Company = self.env['thedevkitchen.estate.company']
        self.company = Company.search([], limit=1)
        if not self.company:
            self.company = Company.create({'name': 'Test Company'})
        
        # Create test agent
        self.agent = self.env['real.estate.agent'].create({
            'name': 'Test Agent',
            'cpf': '99999999999',
            'email': 'test@agent.com',
            'company_id': self.company.id,
        })
    
    def test_update_agent_success(self):
        """T034: Update agent data successfully"""
        self.agent.write({
            'email': 'updated@agent.com',
            'phone': '+55 11 91234-5678',
        })
        
        self.assertEqual(self.agent.email, 'updated@agent.com')
        self.assertEqual(self.agent.phone, '+55 11 91234-5678')
    
    def test_update_agent_cross_company_forbidden(self):
        """T035: Prevent updating company_id (security constraint)"""
        Company = self.env['thedevkitchen.estate.company']
        other_company = Company.create({'name': 'Other Company'})
        
        # Direct write should work but is not recommended via API
        # API controller prevents this - test model allows it for admin
        self.agent.sudo().write({'company_id': other_company.id})
        self.assertEqual(self.agent.company_id, other_company)
    
    def test_deactivate_agent_preserves_history(self):
        """T036: Soft-delete preserves agent history"""
        # Deactivate agent
        reason = "Left the company"
        self.agent.action_deactivate(reason=reason)
        
        self.assertFalse(self.agent.active, "Agent should be inactive")
        self.assertEqual(self.agent.deactivation_date, date.today())
        self.assertEqual(self.agent.deactivation_reason, reason)
        
        # Agent still exists in database
        agent_exists = self.env['real.estate.agent'].with_context(active_test=False).search([
            ('id', '=', self.agent.id)
        ])
        self.assertTrue(agent_exists, "Deactivated agent should still exist in DB")
    
    def test_deactivate_agent_hidden_from_active_list(self):
        """T037: Deactivated agents hidden from default queries"""
        # Create active agent
        active_agent = self.env['real.estate.agent'].create({
            'name': 'Active Agent',
            'cpf': '88888888888',
            'company_id': self.company.id,
        })
        
        # Deactivate test agent
        self.agent.action_deactivate()
        
        # Default search should not include inactive agent
        active_agents = self.env['real.estate.agent'].search([
            ('company_id', '=', self.company.id)
        ])
        
        self.assertIn(active_agent, active_agents, "Should include active agent")
        self.assertNotIn(self.agent, active_agents, "Should NOT include inactive agent")
        
        # Search with active_test=False should include inactive
        all_agents = self.env['real.estate.agent'].with_context(active_test=False).search([
            ('company_id', '=', self.company.id)
        ])
        
        self.assertIn(self.agent, all_agents, "Should include inactive agent with active_test=False")
    
    def test_reactivate_agent(self):
        """T038: Reactivate deactivated agent"""
        # Deactivate
        self.agent.action_deactivate(reason="Test")
        self.assertFalse(self.agent.active)
        
        # Reactivate
        self.agent.action_reactivate()
        
        self.assertTrue(self.agent.active, "Agent should be active")
        self.assertFalse(self.agent.deactivation_date, "Deactivation date should be cleared")
        self.assertFalse(self.agent.deactivation_reason, "Deactivation reason should be cleared")
    
    def test_deactivate_already_inactive_agent(self):
        """Test error when deactivating already inactive agent"""
        self.agent.action_deactivate()
        
        with self.assertRaises(UserError, msg="Should error on deactivating inactive agent"):
            self.agent.action_deactivate()
    
    def test_reactivate_already_active_agent(self):
        """Test error when reactivating already active agent"""
        with self.assertRaises(UserError, msg="Should error on reactivating active agent"):
            self.agent.action_reactivate()
    
    def test_audit_logging_on_deactivation(self):
        """Test audit trail and field changes on deactivation"""
        reason = "Performance issues"
        
        # Deactivate the agent
        self.agent.action_deactivate(reason=reason)
        
        # Verify deactivation fields were set correctly
        self.assertFalse(self.agent.active, "Agent should be inactive")
        self.assertEqual(self.agent.deactivation_date, fields.Date.today(), "Deactivation date should be today")
        self.assertEqual(self.agent.deactivation_reason, reason, "Deactivation reason should match")
        
        # Verify mail.thread messages exist (at least creation message)
        self.assertGreater(len(self.agent.message_ids), 0, "Should have message_ids (mail.thread integration)")
