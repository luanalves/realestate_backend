"""
Test suite for Receptionist RBAC profile.

Tests FR-016 to FR-020 (Receptionist profile requirements).
Coverage: Receptionist can read properties, CRUD leases/keys, cannot edit properties.
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestRBACReceptionist(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.Company = cls.env['thedevkitchen.estate.company']
        cls.Property = cls.env['real.estate.property']
        cls.Lease = cls.env['real.estate.lease']
        cls.Tenant = cls.env['real.estate.tenant']
        cls.User = cls.env['res.users']
        
        cls.receptionist_group = cls.env.ref('quicksol_estate.group_real_estate_receptionist')
        
        cls.company_a = cls.Company.create({
            'name': 'Company A',
            'cnpj': '11.222.333/0001-81',
            'creci': 'CRECI-SP 12345',
        })
        
        cls.receptionist_user = cls.User.create({
            'name': 'Receptionist User',
            'login': 'receptionist@test.com',
            'email': 'receptionist@test.com',
            'groups_id': [(6, 0, [cls.receptionist_group.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
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
    
    def test_receptionist_can_read_properties(self):
        """T050.1: Receptionist can read properties."""
        properties = self.Property.with_user(self.receptionist_user).search([
            ('id', '=', self.property_a.id)
        ])
        
        self.assertEqual(len(properties), 1)
        self.assertEqual(properties.name, 'Property A1')
    
    def test_receptionist_cannot_edit_properties(self):
        """T053.1: Receptionist cannot edit properties (negative test)."""
        with self.assertRaises(AccessError):
            self.property_a.with_user(self.receptionist_user).write({
                'name': 'Property A1 (Modified)'
            })
    
    def test_receptionist_cannot_create_properties(self):
        """T053.2: Receptionist cannot create properties."""
        with self.assertRaises(AccessError):
            self.Property.with_user(self.receptionist_user).create({
                'name': 'Unauthorized Property',
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
    
    def test_receptionist_can_create_lease(self):
        """T050.2: Receptionist can create leases."""
        tenant = self.Tenant.create({
            'name': 'Tenant A1',
            'email': 'tenant_a1@test.com',
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        lease = self.Lease.with_user(self.receptionist_user).create({
            'property_id': self.property_a.id,
            'tenant_id': tenant.id,
            'start_date': '2026-02-01',
            'end_date': '2027-01-31',
            'rent_amount': 2000.00,
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        self.assertTrue(lease.id)
        self.assertEqual(lease.rent_amount, 2000.00)
    
    def test_receptionist_can_update_lease(self):
        """T050.3: Receptionist can update leases."""
        tenant = self.Tenant.create({
            'name': 'Tenant A2',
            'email': 'tenant_a2@test.com',
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        lease = self.Lease.create({
            'property_id': self.property_a.id,
            'tenant_id': tenant.id,
            'start_date': '2026-02-01',
            'end_date': '2027-01-31',
            'rent_amount': 1500.00,
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        lease.with_user(self.receptionist_user).write({
            'rent_amount': 1600.00
        })
        
        self.assertEqual(lease.rent_amount, 1600.00)
    
    def test_receptionist_can_delete_lease(self):
        """T050.4: Receptionist can delete leases."""
        tenant = self.Tenant.create({
            'name': 'Tenant Temp',
            'email': 'temp@test.com',
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        lease = self.Lease.create({
            'property_id': self.property_a.id,
            'tenant_id': tenant.id,
            'start_date': '2026-02-01',
            'end_date': '2027-01-31',
            'rent_amount': 1000.00,
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        lease.with_user(self.receptionist_user).unlink()
        
        self.assertFalse(lease.exists())
    
    def test_receptionist_can_create_tenant(self):
        """T050.5: Receptionist can create tenants."""
        tenant = self.Tenant.with_user(self.receptionist_user).create({
            'name': 'New Tenant',
            'email': 'new_tenant@test.com',
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        self.assertTrue(tenant.id)
        self.assertEqual(tenant.name, 'New Tenant')
    
    def test_receptionist_views_all_company_properties_readonly(self):
        """T107: Receptionist can view all company properties (read-only)."""
        property_b = self.Property.create({
            'name': 'Property B',
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
        
        properties = self.Property.with_user(self.receptionist_user).search([
            ('company_ids', 'in', self.company_a.ids)
        ])
        
        self.assertIn(self.property_a.id, properties.ids)
        self.assertIn(property_b.id, properties.ids)
        self.assertGreaterEqual(len(properties), 2)
    
    def test_receptionist_cannot_edit_property_details(self):
        """T108: Receptionist cannot edit property details (negative test)."""
        with self.assertRaises(AccessError):
            self.property_a.with_user(self.receptionist_user).write({
                'property_type_id': self.property_type.id,
                'num_rooms': 4,
            })
    
    def test_receptionist_cannot_modify_commissions(self):
        """T109: Receptionist cannot modify commissions (negative test)."""
        CommissionRule = self.env['real.estate.commission.rule']
        
        # Need to create agent first for commission rule
        agent = self.env['real.estate.agent'].create({
            'name': 'Test Agent',
            'cpf': '222.333.444-55',
            'creci': 'CRECI-SP 88888',
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        with self.assertRaises(AccessError):
            CommissionRule.with_user(self.receptionist_user).create({
                'agent_id': agent.id,
                'company_id': self.company_a.id,
                'transaction_type': 'sale',
                'structure_type': 'percentage',
                'percentage': 5.0,
                'valid_from': '2024-01-01',
            })
