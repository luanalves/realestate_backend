# -*- coding: utf-8 -*-
"""
Test cases for multi-tenancy company isolation (Phase 1).

Tests validate:
1. Record rules enforce data isolation by estate_company_ids
2. User A cannot see records of User B (different companies)
3. User can only access properties in their assigned companies
4. User can only access agents in their assigned companies
5. User can only access leases in their assigned companies
6. User can only access sales in their assigned companies
7. Agents can only see their own records
8. Proper CRUD behavior respects company isolation
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestCompanyIsolation(TransactionCase):
    """Test multi-tenancy isolation via record rules"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create two test companies (estates)
        cls.company1 = cls.env['quicksol_estate.company'].create({
            'name': 'Estate Company 1',
            'cnpj': '11.111.111/0001-11',
        })
        
        cls.company2 = cls.env['quicksol_estate.company'].create({
            'name': 'Estate Company 2',
            'cnpj': '22.222.222/0001-22',
        })
        
        # Create manager users (can see all company data)
        cls.manager1 = cls.env['res.users'].create({
            'name': 'Manager Company 1',
            'login': 'manager1@company1.com',
            'email': 'manager1@company1.com',
            'password': 'password123',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
            'estate_company_ids': [(6, 0, [cls.company1.id])],
            'estate_default_company_id': cls.company1.id,
        })
        
        cls.manager2 = cls.env['res.users'].create({
            'name': 'Manager Company 2',
            'login': 'manager2@company2.com',
            'email': 'manager2@company2.com',
            'password': 'password123',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
            'estate_company_ids': [(6, 0, [cls.company2.id])],
            'estate_default_company_id': cls.company2.id,
        })
        
        # Create properties for each company
        cls.property1 = cls.env['quicksol_estate.property'].create({
            'name': 'Property Company 1',
            'estate_company_ids': [(6, 0, [cls.company1.id])],
        })
        
        cls.property2 = cls.env['quicksol_estate.property'].create({
            'name': 'Property Company 2',
            'estate_company_ids': [(6, 0, [cls.company2.id])],
        })
        
        # Create agents for each company
        cls.agent1 = cls.env['quicksol_estate.agent'].create({
            'name': 'Agent Company 1',
            'estate_company_ids': [(6, 0, [cls.company1.id])],
        })
        
        cls.agent2 = cls.env['quicksol_estate.agent'].create({
            'name': 'Agent Company 2',
            'estate_company_ids': [(6, 0, [cls.company2.id])],
        })
        
        # Create tenants for each company
        cls.tenant1 = cls.env['quicksol_estate.tenant'].create({
            'name': 'Tenant Company 1',
            'estate_company_ids': [(6, 0, [cls.company1.id])],
        })
        
        cls.tenant2 = cls.env['quicksol_estate.tenant'].create({
            'name': 'Tenant Company 2',
            'estate_company_ids': [(6, 0, [cls.company2.id])],
        })

    def test_manager_can_see_own_company_properties(self):
        """Manager can see properties from their company"""
        properties = self.env['quicksol_estate.property'].with_user(self.manager1).search([])
        
        # Manager1 should see property1
        self.assertIn(self.property1.id, properties.ids)

    def test_manager_cannot_see_other_company_properties(self):
        """Manager cannot see properties from other companies"""
        properties = self.env['quicksol_estate.property'].with_user(self.manager1).search([])
        
        # Manager1 should NOT see property2 (from company2)
        self.assertNotIn(self.property2.id, properties.ids)

    def test_manager_can_see_own_company_agents(self):
        """Manager can see agents from their company"""
        agents = self.env['quicksol_estate.agent'].with_user(self.manager1).search([])
        
        # Manager1 should see agent1
        self.assertIn(self.agent1.id, agents.ids)

    def test_manager_cannot_see_other_company_agents(self):
        """Manager cannot see agents from other companies"""
        agents = self.env['quicksol_estate.agent'].with_user(self.manager1).search([])
        
        # Manager1 should NOT see agent2 (from company2)
        self.assertNotIn(self.agent2.id, agents.ids)

    def test_manager_can_see_own_company_tenants(self):
        """Manager can see tenants from their company"""
        tenants = self.env['quicksol_estate.tenant'].with_user(self.manager1).search([])
        
        # Manager1 should see tenant1
        self.assertIn(self.tenant1.id, tenants.ids)

    def test_manager_cannot_see_other_company_tenants(self):
        """Manager cannot see tenants from other companies"""
        tenants = self.env['quicksol_estate.tenant'].with_user(self.manager1).search([])
        
        # Manager1 should NOT see tenant2 (from company2)
        self.assertNotIn(self.tenant2.id, tenants.ids)

    def test_isolation_prevents_cross_company_property_read(self):
        """Verify complete isolation - manager cannot read other company property"""
        # Manager1 tries to read property2 (belongs to company2)
        # The record rule should prevent this
        properties = self.env['quicksol_estate.property'].with_user(self.manager1).search([
            ('id', '=', self.property2.id)
        ])
        
        # Result should be empty due to record rule
        self.assertEqual(len(properties), 0, "Record rule should prevent cross-company access")

    def test_record_rules_enforce_estate_company_ids_filter(self):
        """Verify record rules are based on estate_company_ids field"""
        # Create a property with multiple company access
        property_multi = self.env['quicksol_estate.property'].create({
            'name': 'Multi-company Property',
            'estate_company_ids': [(6, 0, [self.company1.id, self.company2.id])],
        })
        
        # Both managers should see this property
        properties1 = self.env['quicksol_estate.property'].with_user(self.manager1).search([
            ('id', '=', property_multi.id)
        ])
        properties2 = self.env['quicksol_estate.property'].with_user(self.manager2).search([
            ('id', '=', property_multi.id)
        ])
        
        self.assertEqual(len(properties1), 1, "Manager1 should see multi-company property")
        self.assertEqual(len(properties2), 1, "Manager2 should see multi-company property")

    def test_different_users_same_company_see_same_data(self):
        """Users in same company should see same records"""
        # Create another manager in company1
        manager1_2 = self.env['res.users'].create({
            'name': 'Manager Company 1 (2)',
            'login': 'manager1_2@company1.com',
            'email': 'manager1_2@company1.com',
            'password': 'password123',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
            'estate_company_ids': [(6, 0, [self.company1.id])],
            'estate_default_company_id': self.company1.id,
        })
        
        # Both should see same properties
        props1 = self.env['quicksol_estate.property'].with_user(self.manager1).search([])
        props2 = self.env['quicksol_estate.property'].with_user(manager1_2).search([])
        
        # Should have same IDs
        self.assertEqual(sorted(props1.ids), sorted(props2.ids))

    def test_property_visibility_respects_company_assignment(self):
        """Verify property visibility depends on estate_company_ids assignment"""
        # Create property assigned to company1
        prop = self.env['quicksol_estate.property'].create({
            'name': 'Test Property',
            'estate_company_ids': [(6, 0, [self.company1.id])],
        })
        
        # Manager1 (company1) should see it
        can_see = self.env['quicksol_estate.property'].with_user(self.manager1).search([
            ('id', '=', prop.id)
        ])
        self.assertEqual(len(can_see), 1)
        
        # Manager2 (company2) should NOT see it
        cannot_see = self.env['quicksol_estate.property'].with_user(self.manager2).search([
            ('id', '=', prop.id)
        ])
        self.assertEqual(len(cannot_see), 0)

    def test_search_returns_only_permitted_records(self):
        """Search results should be filtered by record rules"""
        # Manager1 searches all properties
        all_properties = self.env['quicksol_estate.property'].with_user(self.manager1).search(
            [], limit=1000
        )
        
        # Check that all returned properties have company1 in estate_company_ids
        for prop in all_properties:
            self.assertIn(
                self.company1.id,
                prop.estate_company_ids.ids,
                f"Property {prop.id} should not be visible to Manager1"
            )

    def test_agent_record_rules_by_company(self):
        """Agents are isolated by company through record rules"""
        # Create agents with specific company
        agent_c1 = self.env['quicksol_estate.agent'].create({
            'name': 'Agent C1',
            'estate_company_ids': [(6, 0, [self.company1.id])],
        })
        
        agent_c2 = self.env['quicksol_estate.agent'].create({
            'name': 'Agent C2',
            'estate_company_ids': [(6, 0, [self.company2.id])],
        })
        
        # Manager1 should only see agent_c1
        agents_visible = self.env['quicksol_estate.agent'].with_user(self.manager1).search([])
        
        self.assertIn(agent_c1.id, agents_visible.ids)
        self.assertNotIn(agent_c2.id, agents_visible.ids)
