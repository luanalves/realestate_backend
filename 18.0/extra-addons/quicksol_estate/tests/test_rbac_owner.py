"""
Test suite for Owner RBAC profile.

Tests FR-001 to FR-010 (Owner profile requirements).
Coverage: Owner full CRUD access, multi-tenant isolation, user management.
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, ValidationError


class TestRBACOwner(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.Company = cls.env['thedevkitchen.estate.company']
        cls.Property = cls.env['real.estate.property']
        cls.Agent = cls.env['real.estate.agent']
        cls.User = cls.env['res.users']
        cls.CommissionRule = cls.env['real.estate.commission.rule']
        
        cls.owner_group = cls.env.ref('quicksol_estate.group_real_estate_owner')
        
        cls.company_a = cls.Company.create({
            'name': 'Real Estate Company A',
            'cnpj': '11.222.333/0001-81',
            'creci': 'CRECI-SP 12345',
        })
        
        cls.company_b = cls.Company.create({
            'name': 'Real Estate Company B',
            'cnpj': '60.746.948/0001-12',
            'creci': 'CRECI-RJ 54321',
        })
        
        # Create property type for testing (moved before properties)
        cls.property_type = cls.env['real.estate.property.type'].search([('name', '=', 'House')], limit=1)
        if not cls.property_type:
            cls.property_type = cls.env['real.estate.property.type'].create({'name': 'House'})

        # Create location type for testing (moved before properties)
        cls.location_type = cls.env['real.estate.location.type'].search([('name', '=', 'Urban')], limit=1)
        if not cls.location_type:
            cls.location_type = cls.env['real.estate.location.type'].create({'name': 'Urban', 'code': 'URB'})

        # Create geographic state for testing (moved before properties)
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
        
        cls.owner_user = cls.User.create({
            'name': 'Owner User A',
            'login': 'owner_a@test.com',
            'email': 'owner_a@test.com',
            'groups_id': [(6, 0, [
                cls.owner_group.id,
                cls.env.ref('base.group_partner_manager').id,  # Allow contact creation
                cls.env.ref('base.group_erp_manager').id,  # Settings - required to create users
            ])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        # Create agent for commission rule testing
        cls.test_agent = cls.env['real.estate.agent'].create({
            'user_id': cls.owner_user.id,
            'name': 'Test Agent',
            'cpf': '000.111.222-33',
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
        
        cls.property_b = cls.Property.create({
            'name': 'Property B1',
            'company_ids': [(6, 0, [cls.company_b.id])],
            'property_type_id': cls.property_type.id,
            'state_id': cls.state.id,
            'location_type_id': cls.location_type.id,
'zip_code': '01310-100',
            'city': 'São Paulo',
            'street': 'Av Paulista',
            'street_number': '1000',
            'area': 100.0,
        })

    def test_owner_can_read_own_company_properties(self):
        """T031.1: Owner can read properties in their companies (FR-002)."""
        properties = self.Property.with_user(self.owner_user).search([
            ('id', '=', self.property_a.id)
        ])
        
        self.assertEqual(len(properties), 1)
        self.assertEqual(properties.name, 'Property A1')
    
    def test_owner_cannot_read_other_company_properties(self):
        """T031.2: Owner cannot read properties from other companies (FR-008 multi-tenant)."""
        properties = self.Property.with_user(self.owner_user).search([
            ('id', '=', self.property_b.id)
        ])
        
        self.assertEqual(len(properties), 0, "Owner should not see properties from Company B")
    
    def test_owner_can_create_property_in_own_company(self):
        """T031.3: Owner can create properties in their companies (FR-003)."""
        new_property = self.Property.with_user(self.owner_user).create({
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
    
    def test_owner_can_update_property_in_own_company(self):
        """T031.4: Owner can update properties in their companies (FR-004)."""
        self.property_a.with_user(self.owner_user).write({
            'name': 'Property A1 Updated'
        })
        
        self.assertEqual(self.property_a.name, 'Property A1 Updated')
    
    def test_owner_can_delete_property_in_own_company(self):
        """T031.5: Owner can delete properties in their companies (FR-005)."""
        property_to_delete = self.Property.create({
            'name': 'Property A Temp',
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
        
        property_to_delete.with_user(self.owner_user).unlink()
        
        self.assertFalse(property_to_delete.exists())
    
    def test_owner_can_read_agents(self):
        """T031.6: Owner can read agents in their companies (FR-002)."""
        agent = self.Agent.create({
            'name': 'Agent A1',
            'creci': 'CRECI-SP 99999',
            'company_ids': [(6, 0, [self.company_a.id])],
            'cpf': '222.333.444-15',
        })
        
        agents = self.Agent.with_user(self.owner_user).search([('id', '=', agent.id)])
        
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents.name, 'Agent A1')
    
    def test_owner_can_create_commission_rule(self):
        """T031.7: Owner can create commission rules (FR-003)."""
        rule = self.CommissionRule.with_user(self.owner_user).create({
            'agent_id': self.test_agent.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 6.0,
            'valid_from': '2024-01-01',
        })
        
        self.assertTrue(rule.id)
        self.assertEqual(rule.percentage, 6.0)
    
    def test_owner_can_create_user_in_own_company(self):
        """T032.1: Owner can create users assigned to their companies (FR-007)."""
        new_user = self.User.with_user(self.owner_user).with_context(tracking_disable=True, mail_create_nosubscribe=True).create({
            'name': 'New Agent User',
            'login': 'agent_new@test.com',
            'email': 'agent_new@test.com',
            'estate_company_ids': [(6, 0, [self.company_a.id])],
        })
        
        self.assertTrue(new_user.id)
        self.assertIn(self.company_a.id, new_user.estate_company_ids.ids)
    
    def test_owner_cannot_assign_user_to_other_company(self):
        """T033.1: Owner cannot assign users to companies they don't have access to (FR-008)."""
        with self.assertRaises(ValidationError) as ctx:
            self.User.with_user(self.owner_user).with_context(tracking_disable=True, mail_create_nosubscribe=True).create({
                'name': 'Invalid User',
                'login': 'invalid@test.com',
                'email': 'invalid@test.com',
                'estate_company_ids': [(6, 0, [self.company_b.id])],
            })
        
        self.assertIn("cannot assign users to companies", str(ctx.exception).lower())
    
    def test_owner_can_read_commission_transactions(self):
        """T031.8: Owner can read commission transactions (FR-002)."""
        CommissionTransaction = self.env['real.estate.commission.transaction']
        
        agent = self.Agent.create({
            'name': 'Agent for Transaction',
            'creci': 'CRECI-SP 88888',
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
        
        transaction = CommissionTransaction.create({
            'agent_id': agent.id,
            'rule_id': rule.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'transaction_date': '2026-01-15',
            'transaction_amount': 100000.00,
            'commission_amount': 5000.00,
            'rule_snapshot': '{"percentage": 5.0, "structure_type": "percentage"}',
        })
        
        transactions = CommissionTransaction.with_user(self.owner_user).search([
            ('id', '=', transaction.id)
        ])
        
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions.commission_amount, 5000.00)
