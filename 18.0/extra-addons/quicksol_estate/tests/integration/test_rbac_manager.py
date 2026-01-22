"""
Test suite for Manager RBAC profile.

Tests FR-041 to FR-050 (Manager profile requirements).
Coverage: Manager sees all company data, can reassign leads, cannot create users, multi-tenant isolation.
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestRBACManager(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.Company = cls.env['thedevkitchen.estate.company']
        cls.Property = cls.env['real.estate.property']
        cls.Agent = cls.env['real.estate.agent']
        cls.Assignment = cls.env['real.estate.agent.property.assignment']
        cls.Sale = cls.env['real.estate.sale']
        cls.User = cls.env['res.users']
        
        cls.manager_group = cls.env.ref('quicksol_estate.group_real_estate_manager')
        cls.agent_group = cls.env.ref('quicksol_estate.group_real_estate_agent')
        
        cls.company_a = cls.Company.create({
            'name': 'Company A',
            'cnpj': '11.222.333/0001-81',
            'creci': 'CRECI-SP 12345',
        })
        
        cls.company_b = cls.Company.create({
            'name': 'Company B',
            'cnpj': '34.028.316/0001-03',
            'creci': 'CRECI-RJ 54321',
        })
        
        cls.manager_user = cls.User.create({
            'name': 'Manager User',
            'login': 'manager@test.com',
            'email': 'manager@test.com',
            'groups_id': [(6, 0, [cls.manager_group.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        cls.agent_user_a = cls.User.create({
            'name': 'Agent User A',
            'login': 'agent_a_mgr@test.com',
            'email': 'agent_a_mgr@test.com',
            'groups_id': [(6, 0, [cls.agent_group.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        cls.agent_user_b = cls.User.create({
            'name': 'Agent User B',
            'login': 'agent_b_mgr@test.com',
            'email': 'agent_b_mgr@test.com',
            'groups_id': [(6, 0, [cls.agent_group.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
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
        
        cls.agent_record_a = cls.Agent.create({
            'name': 'Agent A',
            'creci': 'CRECI-SP 11111',
            'user_id': cls.agent_user_a.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'cpf': '222.333.444-15',
        })
        
        cls.agent_record_b = cls.Agent.create({
            'name': 'Agent B',
            'creci': 'CRECI-SP 22222',
            'user_id': cls.agent_user_b.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'cpf': '111.222.333-04',
        })
        
        cls.property_agent_a = cls.Property.create({
            'name': 'Property Agent A',
            'agent_id': cls.agent_record_a.id,
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
        
        cls.property_agent_b = cls.Property.create({
            'name': 'Property Agent B',
            'agent_id': cls.agent_record_b.id,
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

    def test_manager_sees_all_company_properties(self):
        """T073.1: Manager can see all properties in their company."""
        properties = self.Property.with_user(self.manager_user).search([
            ('id', 'in', [self.property_agent_a.id, self.property_agent_b.id])
        ])
        
        self.assertEqual(len(properties), 2)
        property_ids = properties.ids
        self.assertIn(self.property_agent_a.id, property_ids)
        self.assertIn(self.property_agent_b.id, property_ids)
    
    def test_manager_sees_all_company_agents(self):
        """T073.2: Manager can see all agents in their company."""
        agents = self.Agent.with_user(self.manager_user).search([
            ('id', 'in', [self.agent_record_a.id, self.agent_record_b.id])
        ])
        
        self.assertEqual(len(agents), 2)
    
    def test_manager_can_create_property(self):
        """T073.3: Manager can create properties for any agent."""
        new_property = self.Property.with_user(self.manager_user).create({
            'name': 'Property Created by Manager',
            'agent_id': self.agent_record_a.id,
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
        self.assertEqual(new_property.agent_id.id, self.agent_record_a.id)
    
    def test_manager_can_update_any_property(self):
        """T073.4: Manager can update any property in their company."""
        self.property_agent_b.with_user(self.manager_user).write({
            'name': 'Property Agent B (Updated by Manager)'
        })
        
        self.assertIn('Updated by Manager', self.property_agent_b.name)
    
    def test_manager_can_delete_properties(self):
        """T073.5: Manager can delete properties."""
        temp_property = self.Property.create({
            'name': 'Temp Property',
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
        
        temp_property.with_user(self.manager_user).unlink()
        
        self.assertFalse(temp_property.exists())
    
    def test_manager_can_reassign_property_to_different_agent(self):
        """T074.1: Manager can reassign properties between agents."""
        original_agent = self.property_agent_a.agent_id.id
        
        self.property_agent_a.with_user(self.manager_user).write({
            'agent_id': self.agent_record_b.id
        })
        
        self.assertEqual(self.property_agent_a.agent_id.id, self.agent_record_b.id)
        self.assertNotEqual(self.property_agent_a.agent_id.id, original_agent)
    
    def test_manager_can_create_assignments(self):
        """T074.2: Manager can create property assignments (lead distribution)."""
        assignment = self.Assignment.with_user(self.manager_user).create({
            'property_id': self.property_agent_a.id,
            'agent_id': self.agent_record_b.id,
            'responsibility_type': 'primary',
        })
        
        self.assertTrue(assignment.id)
        self.assertEqual(assignment.agent_id.id, self.agent_record_b.id)
    
    def test_manager_cannot_create_users(self):
        """T075.1: Manager cannot create users (negative test - only Owner can)."""
        with self.assertRaises(AccessError):
            self.User.with_user(self.manager_user).create({
                'name': 'Unauthorized User',
                'login': 'unauthorized@test.com',
                'email': 'unauthorized@test.com',
                'estate_company_ids': [(6, 0, [self.company_a.id])],
            })
    
    def test_manager_cannot_see_other_company_properties(self):
        """T076.1: Manager cannot see properties from other companies (multi-tenant isolation)."""
        property_b_company = self.Property.create({
            'name': 'Property Company B',
            'company_ids': [(6, 0, [self.company_b.id])],
            'property_type_id': self.property_type.id,
            'state_id': self.state.id,
            'location_type_id': self.location_type.id,
'zip_code': '01310-100',
            'city': 'São Paulo',
            'street': 'Av Paulista',
            'street_number': '1000',
            'area': 100.0,
        })
        
        properties = self.Property.with_user(self.manager_user).search([
            ('id', '=', property_b_company.id)
        ])
        
        self.assertEqual(len(properties), 0, "Manager should not see properties from Company B")
    
    def test_manager_can_read_all_sales(self):
        """T073.6: Manager can read all sales in their company."""
        sale = self.Sale.create({
            'property_id': self.property_agent_a.id,
            'sale_price': 500000.00,
            'company_ids': [(6, 0, [self.company_a.id])],
            'buyer_name': 'Test Buyer',
            'sale_date': '2026-01-15',
        })
        
        sales = self.Sale.with_user(self.manager_user).search([
            ('id', '=', sale.id)
        ])
        
        self.assertEqual(len(sales), 1)
        self.assertEqual(sales.sale_price, 500000.00)
    
    def test_manager_can_read_commission_transactions(self):
        """T073.7: Manager can view commission transactions (read-only)."""
        CommissionTransaction = self.env['real.estate.commission.transaction']
        
        rule = self.env['real.estate.commission.rule'].create({
            'agent_id': self.agent_record_a.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 5.0,
            'valid_from': '2024-01-01',
        })
        
        transaction = CommissionTransaction.create({
            'agent_id': self.agent_record_a.id,
            'rule_id': rule.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'transaction_date': '2026-01-15',
            'transaction_amount': 200000.00,
            'commission_amount': 10000.00,
            'rule_snapshot': '{"percentage": 5.0, "structure_type": "percentage"}',
        })
        
        transactions = CommissionTransaction.with_user(self.manager_user).search([
            ('id', '=', transaction.id)
        ])
        
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions.commission_amount, 10000.00)
