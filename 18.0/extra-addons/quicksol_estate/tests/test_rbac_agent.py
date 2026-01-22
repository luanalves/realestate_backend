"""
Test suite for Agent RBAC profile.

Tests FR-031 to FR-040 (Agent profile requirements).
Coverage: Agent CRUD on own properties, sees only own records, isolation from other agents.
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestRBACAgent(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.Company = cls.env['thedevkitchen.estate.company']
        cls.Property = cls.env['real.estate.property']
        cls.Agent = cls.env['real.estate.agent']
        cls.Assignment = cls.env['real.estate.agent.property.assignment']
        cls.User = cls.env['res.users']
        
        cls.agent_group = cls.env.ref('quicksol_estate.group_real_estate_agent')
        
        cls.company_a = cls.Company.create({
            'name': 'Company A',
            'cnpj': '11.222.333/0001-81',
            'creci': 'CRECI-SP 12345',
        })
        
        cls.agent_user_a = cls.User.create({
            'name': 'Agent User A',
            'login': 'agent_a@test.com',
            'email': 'agent_a@test.com',
            'groups_id': [(6, 0, [cls.agent_group.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        cls.agent_user_b = cls.User.create({
            'name': 'Agent User B',
            'login': 'agent_b@test.com',
            'email': 'agent_b@test.com',
            'groups_id': [(6, 0, [cls.agent_group.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
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
    
    def test_agent_can_create_property(self):
        """T061.1: Agent can create properties (auto-assigned to them)."""
        property_new = self.Property.with_user(self.agent_user_a).create({
            'name': 'Property by Agent A',
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
        
        self.assertTrue(property_new.id)
        self.assertEqual(property_new.agent_id.id, self.agent_record_a.id)
    
    def test_agent_sees_only_own_properties(self):
        """T062.1: Agent sees only properties where agent_id.user_id = user.id."""
        property_a = self.Property.create({
            'name': 'Property A1',
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
        
        property_b = self.Property.create({
            'name': 'Property B1',
            'agent_id': self.agent_record_b.id,
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
        
        properties_seen_by_a = self.Property.with_user(self.agent_user_a).search([
            ('id', 'in', [property_a.id, property_b.id])
        ])
        
        self.assertEqual(len(properties_seen_by_a), 1)
        self.assertEqual(properties_seen_by_a.id, property_a.id)
    
    def test_agent_cannot_modify_other_agent_property(self):
        """T063.1: Agent cannot modify other agent's property (negative test)."""
        property_b = self.Property.create({
            'name': 'Property B2',
            'agent_id': self.agent_record_b.id,
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
            property_b.with_user(self.agent_user_a).write({
                'name': 'Property B2 (Hacked by Agent A)'
            })
    
    def test_agent_sees_assigned_properties(self):
        """T062.2: Agent sees properties in their assignments (assignment_ids)."""
        property_unassigned = self.Property.create({
            'name': 'Property Unassigned',
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
        
        assignment = self.Assignment.create({
            'property_id': property_unassigned.id,
            'agent_id': self.agent_record_a.id,
            'responsibility_type': 'primary',
        })
        
        properties_seen_by_a = self.Property.with_user(self.agent_user_a).search([
            ('id', '=', property_unassigned.id)
        ])
        
        self.assertEqual(len(properties_seen_by_a), 1)
        self.assertEqual(properties_seen_by_a.id, property_unassigned.id)
    
    def test_agent_can_update_own_property(self):
        """T061.2: Agent can update their own properties."""
        property_a = self.Property.create({
            'name': 'Property A Original',
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
        
        property_a.with_user(self.agent_user_a).write({
            'name': 'Property A Updated'
        })
        
        self.assertEqual(property_a.name, 'Property A Updated')
    
    def test_agent_cannot_delete_property(self):
        """T061.3: Agent cannot delete properties (ACL perm_unlink = 0)."""
        property_a = self.Property.create({
            'name': 'Property A Temp',
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
        
        with self.assertRaises(AccessError):
            property_a.with_user(self.agent_user_a).unlink()
    
    def test_agent_sees_own_assignments(self):
        """T064.1: Agent sees their own assignments."""
        property_a = self.Property.create({
            'name': 'Property A1',
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
        
        assignment_a = self.Assignment.create({
            'property_id': property_a.id,
            'agent_id': self.agent_record_a.id,
            'responsibility_type': 'primary',
        })
        
        assignment_b = self.Assignment.create({
            'property_id': property_a.id,
            'agent_id': self.agent_record_b.id,
            'responsibility_type': 'secondary',
        })
        
        assignments_seen_by_a = self.Assignment.with_user(self.agent_user_a).search([
            ('id', 'in', [assignment_a.id, assignment_b.id])
        ])
        
        self.assertEqual(len(assignments_seen_by_a), 1)
        self.assertEqual(assignments_seen_by_a.id, assignment_a.id)
    
    def test_agent_isolation_multi_agent_same_company(self):
        """T063.2: Agent A cannot see Agent B's properties in same company."""
        property_b = self.Property.create({
            'name': 'Property B Confidential',
            'agent_id': self.agent_record_b.id,
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
        
        properties_seen_by_a = self.Property.with_user(self.agent_user_a).search([
            ('name', '=', 'Property B Confidential')
        ])
        
        self.assertEqual(len(properties_seen_by_a), 0, 
                        "Agent A should NOT see Agent B's property")
