# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestUtilsAuth(TransactionCase):
    """Unit tests for authentication utilities"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create OAuth application for testing
        cls.oauth_app = cls.env['thedevkitchen.oauth.application'].create({
            'name': 'Test Utils App'
        })
        
        # Create token
        cls.token = cls.env['thedevkitchen.oauth.token'].create({
            'application_id': cls.oauth_app.id,
            'access_token': 'test_token_12345',
            'revoked': False
        })
    
    def test_require_jwt_decorator_imports(self):
        """Test that require_jwt decorator can be imported"""
        from odoo.addons.quicksol_estate.controllers.utils.auth import require_jwt
        self.assertIsNotNone(require_jwt)
        self.assertTrue(callable(require_jwt))
    
    def test_require_jwt_decorator_structure(self):
        """Test require_jwt decorator returns a wrapper function"""
        from odoo.addons.quicksol_estate.controllers.utils.auth import require_jwt
        
        def dummy_endpoint():
            return "test"
        
        wrapped = require_jwt(dummy_endpoint)
        self.assertTrue(callable(wrapped))
        self.assertEqual(wrapped.__name__, 'wrapper')


@tagged('post_install', '-at_install')
class TestUtilsResponse(TransactionCase):
    """Unit tests for response utilities"""
    
    def test_error_response_import(self):
        """Test that error_response can be imported"""
        from odoo.addons.quicksol_estate.controllers.utils.response import error_response
        self.assertIsNotNone(error_response)
        self.assertTrue(callable(error_response))
    
    def test_success_response_import(self):
        """Test that success_response can be imported"""
        from odoo.addons.quicksol_estate.controllers.utils.response import success_response
        self.assertIsNotNone(success_response)
        self.assertTrue(callable(success_response))


@tagged('post_install', '-at_install')
class TestUtilsSerializers(TransactionCase):
    """Unit tests for serialization utilities"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test data
        cls.property_type = cls.env['real.estate.property.type'].create({
            'name': 'Test Type'
        })
        
        cls.state = cls.env['real.estate.state'].create({
            'name': 'Test State',
            'code': 'TS',
            'country_id': cls.env.ref('base.br').id
        })
        
        cls.location_type = cls.env['real.estate.location.type'].create({
            'name': 'Test Location',
            'code': 'test_loc',
            'sequence': 1
        })
        
        cls.property = cls.env['real.estate.property'].create({
            'name': 'Test Property for Serialization',
            'property_type_id': cls.property_type.id,
            'state_id': cls.state.id,
            'location_type_id': cls.location_type.id,
            'price': 250000.0,
            'area': 100.0,
            'num_rooms': 3,
            'num_bathrooms': 2,
            'num_parking': 1
        })
    
    def test_serialize_property_import(self):
        """Test that serialize_property can be imported"""
        from odoo.addons.quicksol_estate.controllers.utils.serializers import serialize_property
        self.assertIsNotNone(serialize_property)
        self.assertTrue(callable(serialize_property))
    
    def test_serialize_property_basic_fields(self):
        """Test serialize_property returns correct basic fields"""
        from odoo.addons.quicksol_estate.controllers.utils.serializers import serialize_property
        
        result = serialize_property(self.property)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['id'], self.property.id)
        self.assertEqual(result['name'], 'Test Property for Serialization')
        self.assertEqual(result['price'], 250000.0)
        self.assertIn('price_formatted', result)
        self.assertIn('R$', result['price_formatted'])
    
    def test_serialize_property_nested_objects(self):
        """Test serialize_property returns nested objects correctly"""
        from odoo.addons.quicksol_estate.controllers.utils.serializers import serialize_property
        
        result = serialize_property(self.property)
        
        # Property type
        self.assertIn('property_type', result)
        self.assertIsInstance(result['property_type'], dict)
        self.assertEqual(result['property_type']['name'], 'Test Type')
        
        # Address with state and location_type
        self.assertIn('address', result)
        self.assertIsInstance(result['address'], dict)
        self.assertIn('state', result['address'])
        self.assertEqual(result['address']['state']['code'], 'TS')
        self.assertIn('location_type', result['address'])
        self.assertEqual(result['address']['location_type']['code'], 'test_loc')
    
    def test_serialize_property_features(self):
        """Test serialize_property returns features object"""
        from odoo.addons.quicksol_estate.controllers.utils.serializers import serialize_property
        
        result = serialize_property(self.property)
        
        self.assertIn('features', result)
        self.assertIsInstance(result['features'], dict)
        self.assertEqual(result['features']['bedrooms'], 3)
        self.assertEqual(result['features']['bathrooms'], 2)
        self.assertEqual(result['features']['parking_spaces'], 1)
        self.assertEqual(result['features']['area'], 100.0)
    
    def test_serialize_property_null_input(self):
        """Test serialize_property handles None input"""
        from odoo.addons.quicksol_estate.controllers.utils.serializers import serialize_property
        
        result = serialize_property(None)
        self.assertIsNone(result)
    
    def test_validate_property_access_import(self):
        """Test that validate_property_access can be imported"""
        from odoo.addons.quicksol_estate.controllers.utils.serializers import validate_property_access
        self.assertIsNotNone(validate_property_access)
        self.assertTrue(callable(validate_property_access))
    
    def test_validate_property_access_admin(self):
        """Test validate_property_access for admin user"""
        from odoo.addons.quicksol_estate.controllers.utils.serializers import validate_property_access
        
        admin = self.env.ref('base.user_admin')
        has_access, error = validate_property_access(self.property, admin, 'read')
        
        self.assertTrue(has_access)
        self.assertIsNone(error)
    
    def test_validate_property_access_operations(self):
        """Test validate_property_access for different operations"""
        from odoo.addons.quicksol_estate.controllers.utils.serializers import validate_property_access
        
        admin = self.env.ref('base.user_admin')
        
        # Test read
        has_access, _ = validate_property_access(self.property, admin, 'read')
        self.assertTrue(has_access)
        
        # Test write
        has_access, _ = validate_property_access(self.property, admin, 'write')
        self.assertTrue(has_access)
        
        # Test delete
        has_access, _ = validate_property_access(self.property, admin, 'delete')
        self.assertTrue(has_access)
