"""
Test suite for Prospector RBAC profile.

Tests FR-054 to FR-060 (Prospector profile requirements).
Coverage: Prospector creates properties, prospector_id auto-assignment, isolation.
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestRBACProspector(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.Company = cls.env['thedevkitchen.estate.company']
        cls.Property = cls.env['real.estate.property']
        cls.Agent = cls.env['real.estate.agent']
        cls.User = cls.env['res.users']
        
        cls.prospector_group = cls.env.ref('quicksol_estate.group_real_estate_prospector')
        
        cls.company_a = cls.Company.create({
            'name': 'Company A',
            'cnpj': '11.222.333/0001-81',
            'creci': 'CRECI-SP 12345',
        })
        
        # Create prospector user and agent
        cls.prospector_user = cls.User.create({
            'name': 'Prospector User',
            'login': 'prospector@test.com',
            'email': 'prospector@test.com',
            'groups_id': [(6, 0, [cls.prospector_group.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        cls.prospector_agent = cls.Agent.create({
            'name': 'Prospector Agent',
            'creci': 'CRECI-SP 99999',
            'user_id': cls.prospector_user.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'cpf': '222.333.444-15',
        })
        
        # Create another prospector for isolation testing
        cls.prospector_user_b = cls.User.create({
            'name': 'Prospector User B',
            'login': 'prospector_b@test.com',
            'email': 'prospector_b@test.com',
            'groups_id': [(6, 0, [cls.prospector_group.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        cls.prospector_agent_b = cls.Agent.create({
            'name': 'Prospector Agent B',
            'creci': 'CRECI-SP 88888',
            'user_id': cls.prospector_user_b.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'cpf': '111.222.333-04',
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
    
    def test_prospector_can_create_property(self):
        """T090.1: Prospector can create properties."""
        property_obj = self.Property.with_user(self.prospector_user).create({
            'name': 'Property Created by Prospector',
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
        
        self.assertTrue(property_obj.id)
        self.assertEqual(property_obj.name, 'Property Created by Prospector')
    
    def test_prospector_id_auto_assigned_on_create(self):
        """T091.1: prospector_id is auto-assigned when Prospector creates property."""
        property_obj = self.Property.with_user(self.prospector_user).create({
            'name': 'Auto Prospector Assignment Test',
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
        
        self.assertEqual(property_obj.prospector_id.id, self.prospector_agent.id)
        self.assertEqual(property_obj.prospector_id.user_id.id, self.prospector_user.id)
    
    def test_prospector_sees_only_own_properties(self):
        """T092.1: Prospector sees only properties where prospector_id = their agent."""
        # Create property as Prospector A
        property_a = self.Property.with_user(self.prospector_user).create({
            'name': 'Property Prospector A',
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
        
        # Create property as Prospector B
        property_b = self.Property.with_user(self.prospector_user_b).create({
            'name': 'Property Prospector B',
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
        
        # Prospector A searches properties
        properties_seen_by_a = self.Property.with_user(self.prospector_user).search([
            ('id', 'in', [property_a.id, property_b.id])
        ])
        
        # Should only see property_a
        self.assertEqual(len(properties_seen_by_a), 1)
        self.assertEqual(properties_seen_by_a.id, property_a.id)
        self.assertNotIn(property_b.id, properties_seen_by_a.ids)
    
    def test_prospector_cannot_modify_other_prospector_property(self):
        """T092.2: Prospector cannot edit another prospector's property."""
        # Create property as Prospector B
        property_b = self.Property.with_user(self.prospector_user_b).create({
            'name': 'Property Prospector B',
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
        
        # Prospector A tries to modify Property B
        with self.assertRaises(AccessError):
            property_b.with_user(self.prospector_user).write({
                'name': 'Unauthorized Modification'
            })
    
    def test_prospector_can_read_properties(self):
        """T092.3: Prospector can read their own properties."""
        property_obj = self.Property.with_user(self.prospector_user).create({
            'name': 'Prospector Read Test',
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
        
        # Read property details
        read_property = self.Property.with_user(self.prospector_user).browse(property_obj.id)
        
        self.assertEqual(read_property.name, 'Prospector Read Test')
        self.assertEqual(read_property.prospector_id.id, self.prospector_agent.id)
    
    def test_prospector_cannot_delete_properties(self):
        """T092.4: Prospector cannot delete properties (perm_unlink=0)."""
        property_obj = self.Property.with_user(self.prospector_user).create({
            'name': 'Property No Delete',
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
        
        with self.assertRaises(AccessError):
            property_obj.with_user(self.prospector_user).unlink()
    
    def test_prospector_can_update_own_property(self):
        """T092.5: Prospector can update their own prospected properties."""
        property_obj = self.Property.with_user(self.prospector_user).create({
            'name': 'Property Update Test',
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
        
        property_obj.with_user(self.prospector_user).write({
            'name': 'Property Update Test (Modified)'
        })
        
        self.assertIn('Modified', property_obj.name)
    
    def test_prospector_id_not_assigned_for_non_prospector_users(self):
        """T091.2: prospector_id is NOT auto-assigned for non-Prospector users."""
        manager_user = self.User.create({
            'name': 'Manager User',
            'login': 'manager_prospector_test@test.com',
            'email': 'manager_prospector_test@test.com',
            'groups_id': [(6, 0, [self.env.ref('quicksol_estate.group_real_estate_manager').id])],
            'estate_company_ids': [(6, 0, [self.company_a.id])],
        })
        
        property_obj = self.Property.with_user(manager_user).create({
            'name': 'Property Manager Created',
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
        
        self.assertFalse(property_obj.prospector_id, "prospector_id should be empty for non-Prospector users")
