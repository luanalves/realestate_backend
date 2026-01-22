"""
Test suite for Multi-Tenancy RBAC isolation.

Tests FR-037 to FR-039 (Cross-company data isolation).
Coverage: Company A users cannot see Company B data, multi-company users see combined data.
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestRBACMultiTenancy(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.Company = cls.env['thedevkitchen.estate.company']
        cls.Property = cls.env['real.estate.property']
        cls.Sale = cls.env['real.estate.sale']
        cls.Agent = cls.env['real.estate.agent']
        cls.User = cls.env['res.users']
        
        # Create two separate companies for isolation testing
        cls.company_a = cls.Company.create({
            'name': 'Company A - São Paulo',
            'cnpj': '11.111.111/0001-11',
            'creci': 'CRECI-SP 11111',
        })
        
        cls.company_b = cls.Company.create({
            'name': 'Company B - Rio de Janeiro',
            'cnpj': '22.222.222/0001-22',
            'creci': 'CRECI-RJ 22222',
        })
        
        # Get groups
        cls.agent_group = cls.env.ref('quicksol_estate.group_real_estate_agent')
        cls.manager_group = cls.env.ref('quicksol_estate.group_real_estate_manager')
        
        # Create users for each company
        cls.user_company_a = cls.User.create({
            'name': 'User Company A',
            'login': 'user_company_a@test.com',
            'email': 'user_company_a@test.com',
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
            'groups_id': [(6, 0, [cls.agent_group.id])],
        })
        
        cls.user_company_b = cls.User.create({
            'name': 'User Company B',
            'login': 'user_company_b@test.com',
            'email': 'user_company_b@test.com',
            'estate_company_ids': [(6, 0, [cls.company_b.id])],
            'groups_id': [(6, 0, [cls.agent_group.id])],
        })
        
        # Create multi-company user (has access to both)
        cls.user_multi_company = cls.User.create({
            'name': 'User Multi-Company',
            'login': 'user_multi@test.com',
            'email': 'user_multi@test.com',
            'estate_company_ids': [(6, 0, [cls.company_a.id, cls.company_b.id])],
            'groups_id': [(6, 0, [cls.manager_group.id])],
        })
        
        # Create property types and states (required fields)
        cls.property_type = cls.env['real.estate.property.type'].create({
            'name': 'Apartment',
        })
        cls.state = cls.env['real.estate.state'].create({
            'name': 'São Paulo',
            'code': 'SP',
        })
        
        # Create properties for Company A
        cls.property_a1 = cls.Property.create({
            'name': 'Property A1 - SP',
            'property_type_id': cls.property_type.id,
            'zip_code': '01310-100',
            'state_id': cls.state.id,
            'city': 'São Paulo',
            'street': 'Avenida Paulista',
            'street_number': '1000',
            'company_ids': [(6, 0, [cls.company_a.id])],
            'location_type_id': self.location_type.id,
            'area': 100.0,
        })
        
        cls.property_a2 = cls.Property.create({
            'name': 'Property A2 - SP',
            'property_type_id': cls.property_type.id,
            'zip_code': '01310-200',
            'state_id': cls.state.id,
            'city': 'São Paulo',
            'street': 'Rua Augusta',
            'street_number': '2000',
            'company_ids': [(6, 0, [cls.company_a.id])],
            'location_type_id': self.location_type.id,
            'area': 100.0,
        })
        
        # Create properties for Company B
        cls.property_b1 = cls.Property.create({
            'name': 'Property B1 - RJ',
            'property_type_id': cls.property_type.id,
            'zip_code': '20040-000',
            'state_id': cls.state.id,
            'city': 'Rio de Janeiro',
            'street': 'Avenida Rio Branco',
            'street_number': '3000',
            'company_ids': [(6, 0, [cls.company_b.id])],
            'location_type_id': self.location_type.id,
            'area': 100.0,
        })
        
        cls.property_b2 = cls.Property.create({
            'name': 'Property B2 - RJ',
            'property_type_id': cls.property_type.id,
            'zip_code': '20040-100',
            'state_id': cls.state.id,
            'city': 'Rio de Janeiro',
            'street': 'Avenida Presidente Vargas',
            'street_number': '4000',
            'company_ids': [(6, 0, [cls.company_b.id])],
            'location_type_id': self.location_type.id,
            'area': 100.0,
        })
    
    def test_company_a_user_cannot_see_company_b_properties(self):
        """T139.1: Company A user cannot view Company B properties (strict isolation)."""
        # User from Company A searches for properties
        properties_a = self.Property.with_user(self.user_company_a).search([])
        
        # Should see only Company A properties
        self.assertIn(self.property_a1, properties_a)
        self.assertIn(self.property_a2, properties_a)
        self.assertNotIn(self.property_b1, properties_a)
        self.assertNotIn(self.property_b2, properties_a)
        self.assertEqual(len(properties_a), 2)
    
    def test_company_b_user_cannot_see_company_a_properties(self):
        """T139.2: Company B user cannot view Company A properties (bidirectional isolation)."""
        properties_b = self.Property.with_user(self.user_company_b).search([])
        
        # Should see only Company B properties
        self.assertIn(self.property_b1, properties_b)
        self.assertIn(self.property_b2, properties_b)
        self.assertNotIn(self.property_a1, properties_b)
        self.assertNotIn(self.property_a2, properties_b)
        self.assertEqual(len(properties_b), 2)
    
    def test_company_a_user_cannot_modify_company_b_data(self):
        """T139.3: Company A user cannot write to Company B properties (negative test)."""
        # User from Company A tries to modify Company B property
        with self.assertRaises(AccessError):
            self.property_b1.with_user(self.user_company_a).write({
                'name': 'Hacked Property',
            })
    
    def test_multi_company_user_sees_all_assigned_companies(self):
        """T140.1: Multi-company user sees data from all assigned companies."""
        properties_multi = self.Property.with_user(self.user_multi_company).search([])
        
        # Should see properties from both companies
        self.assertIn(self.property_a1, properties_multi)
        self.assertIn(self.property_a2, properties_multi)
        self.assertIn(self.property_b1, properties_multi)
        self.assertIn(self.property_b2, properties_multi)
        self.assertEqual(len(properties_multi), 4)
    
    def test_multi_company_user_can_create_in_any_company(self):
        """T140.2: Multi-company user can create records for any assigned company."""
        # Multi-company user creates property in Company A
        new_property_a = self.Property.with_user(self.user_multi_company).create({
            'name': 'New Property for Company A',
            'property_type_id': self.property_type.id,
            'zip_code': '01310-300',
            'state_id': self.state.id,
            'city': 'São Paulo',
            'street': 'Rua da Consolação',
            'street_number': '5000',
            'company_ids': [(6, 0, [self.company_a.id])],
            'location_type_id': self.location_type.id,
            'area': 100.0,
        })
        
        # Multi-company user creates property in Company B
        new_property_b = self.Property.with_user(self.user_multi_company).create({
            'name': 'New Property for Company B',
            'property_type_id': self.property_type.id,
            'zip_code': '20040-200',
            'state_id': self.state.id,
            'city': 'Rio de Janeiro',
            'street': 'Avenida Atlântica',
            'street_number': '6000',
            'company_ids': [(6, 0, [self.company_b.id])],
            'location_type_id': self.location_type.id,
            'area': 100.0,
        })
        
        self.assertTrue(new_property_a.id)
        self.assertTrue(new_property_b.id)
        self.assertIn(self.company_a, new_property_a.company_ids)
        self.assertIn(self.company_b, new_property_b.company_ids)
    
    def test_sales_isolation_between_companies(self):
        """T139.4: Sales records are isolated by company (multi-tenancy for transactions)."""
        # Create sales for each company
        sale_a = self.Sale.create({
            'property_id': self.property_a1.id,
            'buyer_name': 'Buyer A',
            'sale_price': 500000.00,
            'sale_date': '2026-01-10',
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        sale_b = self.Sale.create({
            'property_id': self.property_b1.id,
            'buyer_name': 'Buyer B',
            'sale_price': 600000.00,
            'sale_date': '2026-01-11',
            'company_ids': [(6, 0, [self.company_b.id])],
        })
        
        # Company A user should see only Company A sales
        sales_a = self.Sale.with_user(self.user_company_a).search([])
        self.assertIn(sale_a, sales_a)
        self.assertNotIn(sale_b, sales_a)
        
        # Company B user should see only Company B sales
        sales_b = self.Sale.with_user(self.user_company_b).search([])
        self.assertIn(sale_b, sales_b)
        self.assertNotIn(sale_a, sales_b)
    
    def test_agent_isolation_between_companies(self):
        """T139.5: Agents are isolated by company (staff cannot see other companies' agents)."""
        # Create agents for each company
        agent_a = self.Agent.create({
            'name': 'Agent Company A',
            'cpf': '111.111.111-11',
            'creci': 'CRECI-SP 11111-A',
            'user_id': self.user_company_a.id,
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        agent_b = self.Agent.create({
            'name': 'Agent Company B',
            'cpf': '222.222.222-22',
            'creci': 'CRECI-RJ 22222-B',
            'user_id': self.user_company_b.id,
            'company_ids': [(6, 0, [self.company_b.id])],
        })
        
        # Company A user should see only Company A agents
        agents_a = self.Agent.with_user(self.user_company_a).search([])
        self.assertIn(agent_a, agents_a)
        self.assertNotIn(agent_b, agents_a)
        
        # Company B user should see only Company B agents
        agents_b = self.Agent.with_user(self.user_company_b).search([])
        self.assertIn(agent_b, agents_b)
        self.assertNotIn(agent_a, agents_b)
    
    def test_removing_company_access_removes_data_visibility(self):
        """T140.3: Removing company from user's estate_company_ids removes data access."""
        # Multi-company user initially sees all properties
        properties_before = self.Property.with_user(self.user_multi_company).search([])
        self.assertEqual(len(properties_before), 4)
        
        # Remove Company B from user's companies
        self.user_multi_company.write({
            'estate_company_ids': [(6, 0, [self.company_a.id])],
        })
        
        # User should now see only Company A properties
        properties_after = self.Property.with_user(self.user_multi_company).search([])
        self.assertIn(self.property_a1, properties_after)
        self.assertIn(self.property_a2, properties_after)
        self.assertNotIn(self.property_b1, properties_after)
        self.assertNotIn(self.property_b2, properties_after)
        self.assertEqual(len(properties_after), 2)
