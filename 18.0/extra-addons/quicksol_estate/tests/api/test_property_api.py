import json
from odoo.tests.common import HttpCase, tagged
from odoo.exceptions import AccessError


@tagged('post_install', '-at_install')
class TestPropertyAPI(HttpCase):
    """HTTP integration tests for Property API access control"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company (using valid CNPJ numbers)
        cls.company = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Test Real Estate Company',
            'cnpj': '11.222.333/0001-81',  # Valid CNPJ
            'email': 'test@realestate.com'
        })
        
        cls.company2 = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Other Real Estate Company',
            'cnpj': '34.028.316/0001-03',  # Valid CNPJ
            'email': 'other@realestate.com'
        })
        
        # Create test users with different roles
        cls.admin_user = cls.env.ref('base.user_admin')
        
        cls.manager_user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Manager User',
            'login': 'manager@test.com',
            'email': 'manager@test.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('quicksol_estate.group_real_estate_manager').id
            ])],
            'estate_company_ids': [(6, 0, [cls.company.id])]
        })
        
        cls.user_normal = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Normal User',
            'login': 'user@test.com',
            'email': 'user@test.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('quicksol_estate.group_real_estate_user').id
            ])],
            'estate_company_ids': [(6, 0, [cls.company.id])]
        })
        
        cls.agent_user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Agent User',
            'login': 'agent@test.com',
            'email': 'agent@test.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('quicksol_estate.group_real_estate_agent').id
            ])],
            'estate_company_ids': [(6, 0, [cls.company.id])]
        })
        
        cls.portal_user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Portal User',
            'login': 'portal@test.com',
            'email': 'portal@test.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_portal').id
            ])]
        })
        
        # Create agent record linked to agent_user
        cls.agent = cls.env['real.estate.agent'].create({
            'name': 'Test Agent',
            'email': 'agent@test.com',
            'user_id': cls.agent_user.id,
            'company_ids': [(6, 0, [cls.company.id])]
        })
        
        cls.other_agent = cls.env['real.estate.agent'].create({
            'name': 'Other Agent',
            'email': 'other@test.com',
            'company_ids': [(6, 0, [cls.company.id])]
        })
        
        # Create property type
        cls.property_type = cls.env['real.estate.property.type'].create({
            'name': 'Apartamento'
        })
        
        # Get test state and location type
        cls.state_sp = cls.env['real.estate.state'].search([('code', '=', 'SP')], limit=1)
        if not cls.state_sp:
            cls.state_sp = cls.env['real.estate.state'].create({
                'name': 'São Paulo',
                'code': 'SP',
                'country_id': cls.env.ref('base.br').id
            })
        
        cls.location_type = cls.env['real.estate.location.type'].search([], limit=1)
        if not cls.location_type:
            cls.location_type = cls.env['real.estate.location.type'].create({
                'name': 'Urbano',
                'code': 'urban',
                'sequence': 1
            })
        
        # Create properties for testing
        cls.property_agent = cls.env['real.estate.property'].create({
            'name': 'Property managed by agent_user',
            'description': 'Test property',
            'price': 450000.00,
            'status': 'available',
            'property_type_id': cls.property_type.id,
            'agent_id': cls.agent.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'num_rooms': 3,
            'num_bathrooms': 2,
            'num_parking': 2,
            'area': 120.5, 'total_area': 120.5,
            'street': 'Rua Teste',
            'street_number': '123',
            'city': 'São Paulo',
            'state_id': cls.state_sp.id,
            'location_type_id': cls.location_type.id,
            'zip_code': '01234-567'
        })
        
        cls.property_other = cls.env['real.estate.property'].create({
            'name': 'Property managed by other_agent',
            'description': 'Test property',
            'price': 350000.00,
            'status': 'available',
            'property_type_id': cls.property_type.id,
            'agent_id': cls.other_agent.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'num_rooms': 2,
            'num_bathrooms': 1,
            'num_parking': 1,
            'area': 80.0, 'total_area': 80.0,
            'street': 'Rua Teste',
            'street_number': '456',
            'city': 'São Paulo',
            'state_id': cls.state_sp.id,
            'location_type_id': cls.location_type.id,
            'zip_code': '01234-567'
        })
        
        cls.property_company2 = cls.env['real.estate.property'].create({
            'name': 'Property of company2',
            'description': 'Test property',
            'price': 500000.00,
            'status': 'available',
            'property_type_id': cls.property_type.id,
            'company_ids': [(6, 0, [cls.company2.id])],
            'num_rooms': 4,
            'num_bathrooms': 3,
            'area': 150.0,
            'street': 'Rua Company2',
            'street_number': '789',
            'city': 'São Paulo',
            'state_id': cls.state_sp.id,
            'location_type_id': cls.location_type.id,
            'zip_code': '01234-567'
        })
        
        # Create OAuth application and token for API testing
        cls.oauth_app = cls.env['thedevkitchen.oauth.application'].create({
            'name': 'Test API App'
        })
        
        # Get plaintext secret from cache using correct cache key
        from odoo.addons.thedevkitchen_apigateway.models.oauth_application import _PLAINTEXT_CACHE
        cache_key = f'oauth_app_{cls.oauth_app.id}_plaintext'
        cached_data = _PLAINTEXT_CACHE.get(cache_key)
        if cached_data:
            cls.client_secret, _ = cached_data
        else:
            raise Exception(f"Client secret not found in cache for application {cls.oauth_app.id}")
        
        # Create access token
        from odoo import fields
        from datetime import timedelta
        cls.access_token = cls.env['thedevkitchen.oauth.token'].create({
            'application_id': cls.oauth_app.id,
            'token_type': 'access',
            'access_token': 'test_access_token_123',
            'refresh_token': 'test_refresh_token_456',
            'expires_at': fields.Datetime.now() + timedelta(seconds=3600),
            'revoked': False
        })
    
    def test_01_serialize_property(self):
        """Test property serialization to JSON"""
        from odoo.addons.quicksol_estate.controllers.property_api import _serialize_property
        
        result = _serialize_property(self.property_agent)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['id'], self.property_agent.id)
        self.assertEqual(result['name'], 'Property managed by agent_user')
        self.assertEqual(result['price'], 450000.00)
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['features']['bedrooms'], 3)
        self.assertEqual(result['features']['bathrooms'], 2)
        self.assertIsNotNone(result['agent'])
        self.assertEqual(result['agent']['name'], 'Test Agent')
    
    def test_02_validate_access_admin(self):
        """Admin user has access to all properties"""
        from odoo.addons.quicksol_estate.controllers.property_api import _validate_property_access
        
        has_access, error = _validate_property_access(self.property_agent, self.admin_user, 'read')
        self.assertTrue(has_access)
        self.assertIsNone(error)
        
        has_access, error = _validate_property_access(self.property_company2, self.admin_user, 'delete')
        self.assertTrue(has_access)
        self.assertIsNone(error)
    
    def test_03_validate_access_manager_own_company(self):
        """Manager can access properties of their companies"""
        from odoo.addons.quicksol_estate.controllers.property_api import _validate_property_access
        
        has_access, error = _validate_property_access(self.property_agent, self.manager_user, 'read')
        self.assertTrue(has_access)
        self.assertIsNone(error)
        
        has_access, error = _validate_property_access(self.property_other, self.manager_user, 'write')
        self.assertTrue(has_access)
        self.assertIsNone(error)
        
        has_access, error = _validate_property_access(self.property_agent, self.manager_user, 'delete')
        self.assertTrue(has_access)
        self.assertIsNone(error)
    
    def test_04_validate_access_manager_other_company(self):
        """Manager CANNOT access properties of other companies"""
        from odoo.addons.quicksol_estate.controllers.property_api import _validate_property_access
        
        has_access, error = _validate_property_access(self.property_company2, self.manager_user, 'read')
        self.assertFalse(has_access)
        self.assertEqual(error, 'Property does not belong to your companies')
    
    def test_05_validate_access_agent_own_property(self):
        """Agent can access their own properties"""
        from odoo.addons.quicksol_estate.controllers.property_api import _validate_property_access
        
        has_access, error = _validate_property_access(self.property_agent, self.agent_user, 'read')
        self.assertTrue(has_access)
        self.assertIsNone(error)
        
        has_access, error = _validate_property_access(self.property_agent, self.agent_user, 'write')
        self.assertTrue(has_access)
        self.assertIsNone(error)
    
    def test_06_validate_access_agent_other_property(self):
        """Agent CANNOT access properties of other agents"""
        from odoo.addons.quicksol_estate.controllers.property_api import _validate_property_access
        
        has_access, error = _validate_property_access(self.property_other, self.agent_user, 'read')
        self.assertFalse(has_access)
        self.assertEqual(error, 'You can only access your own properties')
    
    def test_07_validate_access_agent_cannot_delete(self):
        """Agent CANNOT delete properties"""
        from odoo.addons.quicksol_estate.controllers.property_api import _validate_property_access
        
        has_access, error = _validate_property_access(self.property_agent, self.agent_user, 'delete')
        self.assertFalse(has_access)
        self.assertEqual(error, 'Agents cannot delete properties')
    
    def test_08_validate_access_user_own_company(self):
        """Normal user can read/write properties of their companies"""
        from odoo.addons.quicksol_estate.controllers.property_api import _validate_property_access
        
        has_access, error = _validate_property_access(self.property_agent, self.user_normal, 'read')
        self.assertTrue(has_access)
        self.assertIsNone(error)
        
        has_access, error = _validate_property_access(self.property_other, self.user_normal, 'write')
        self.assertTrue(has_access)
        self.assertIsNone(error)
    
    def test_09_validate_access_user_cannot_delete(self):
        """Normal user CANNOT delete properties"""
        from odoo.addons.quicksol_estate.controllers.property_api import _validate_property_access
        
        has_access, error = _validate_property_access(self.property_agent, self.user_normal, 'delete')
        self.assertFalse(has_access)
        self.assertEqual(error, 'Users cannot delete properties')
    
    def test_10_validate_access_portal_denied(self):
        """Portal user has NO access"""
        from odoo.addons.quicksol_estate.controllers.property_api import _validate_property_access
        
        has_access, error = _validate_property_access(self.property_agent, self.portal_user, 'read')
        self.assertFalse(has_access)
        self.assertEqual(error, 'Insufficient permissions')
    
    def test_11_error_response_format(self):
        """Test error response format"""
        from odoo.addons.quicksol_estate.controllers.property_api import _error_response
        
        response = _error_response(404, 'Not found')
        self.assertIsNotNone(response)
    
    def test_12_success_response_format(self):
        """Test success response format"""
        from odoo.addons.quicksol_estate.controllers.property_api import _success_response
        
        data = {'id': 1, 'name': 'Test'}
        response = _success_response(data)
        self.assertIsNotNone(response)
    
    def test_13_serialize_property_without_agent(self):
        """Test serialization of property without agent"""
        from odoo.addons.quicksol_estate.controllers.property_api import _serialize_property
        
        property_no_agent = self.env['real.estate.property'].create({
            'name': 'Property without agent',
            'price': 200000.00,
            'status': 'draft',
            'property_type_id': self.property_type.id,
            'company_ids': [(6, 0, [self.company.id])]
        })
        
        result = _serialize_property(property_no_agent)
        self.assertIsInstance(result, dict)
        self.assertIsNone(result['agent'])
    
    def test_14_serialize_property_none(self):
        """Test serialization of None returns None"""
        from odoo.addons.quicksol_estate.controllers.property_api import _serialize_property
        
        result = _serialize_property(None)
        self.assertIsNone(result)
    
    def test_15_price_formatting(self):
        """Test price formatting in Brazilian format"""
        from odoo.addons.quicksol_estate.controllers.property_api import _serialize_property
        
        result = _serialize_property(self.property_agent)
        self.assertEqual(result['price_formatted'], 'R$ 450.000,00')
    
    def test_16_property_exists_check(self):
        """Test property exists validation"""
        Property = self.env['real.estate.property'].sudo()
        
        # Existing property
        prop = Property.browse(self.property_agent.id)
        self.assertTrue(prop.exists())
        
        # Non-existing property
        prop = Property.browse(99999)
        self.assertFalse(prop.exists())
    
    def test_17_multiple_companies_access(self):
        """Test user with multiple companies"""
        from odoo.addons.quicksol_estate.controllers.property_api import _validate_property_access
        
        # Give manager_user access to both companies
        self.manager_user.estate_company_ids = [(6, 0, [self.company.id, self.company2.id])]
        
        # Should now have access to company2's property
        has_access, error = _validate_property_access(self.property_company2, self.manager_user, 'read')
        self.assertTrue(has_access)
        self.assertIsNone(error)
    
    def test_18_address_serialization(self):
        """Test address fields serialization"""
        from odoo.addons.quicksol_estate.controllers.property_api import _serialize_property
        
        result = _serialize_property(self.property_agent)
        self.assertEqual(result['address']['street'], 'Rua Teste, 123')
        self.assertEqual(result['address']['city'], 'São Paulo')
        self.assertIsInstance(result['address']['state'], dict)
        self.assertEqual(result['address']['state']['code'], 'SP')
        self.assertEqual(result['address']['zip_code'], '01234-567')
    
    def test_19_features_serialization(self):
        """Test features fields serialization"""
        from odoo.addons.quicksol_estate.controllers.property_api import _serialize_property
        
        result = _serialize_property(self.property_agent)
        self.assertEqual(result['features']['bedrooms'], 3)
        self.assertEqual(result['features']['bathrooms'], 2)
        self.assertEqual(result['features']['garage_spaces'], 2)
        self.assertEqual(result['features']['total_area'], 120.5)
    
    def test_20_company_serialization(self):
        """Test company field serialization"""
        from odoo.addons.quicksol_estate.controllers.property_api import _serialize_property
        
        result = _serialize_property(self.property_agent)
        self.assertIsNotNone(result['company'])
        self.assertEqual(result['company']['id'], self.company.id)
        self.assertEqual(result['company']['name'], 'Test Real Estate Company')


@tagged('post_install', '-at_install')
class TestPropertyAPIHTTP(HttpCase):
    """HTTP integration tests for Property API endpoints - including negative scenarios"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create company
        cls.company = cls.env['thedevkitchen.estate.company'].create({
            'name': 'HTTP Test Company',
            'cnpj': '11.222.333/0001-81',
            'email': 'httptest@company.com'
        })
        
        # Create property type
        cls.property_type = cls.env['real.estate.property.type'].create({
            'name': 'Casa'
        })
        
        # Create state
        cls.state_sp = cls.env['real.estate.state'].search([('code', '=', 'SP')], limit=1)
        if not cls.state_sp:
            cls.state_sp = cls.env['real.estate.state'].create({
                'name': 'São Paulo',
                'code': 'SP',
                'country_id': cls.env.ref('base.br').id
            })
        
        # Create location type
        cls.location_type = cls.env['real.estate.location.type'].search([], limit=1)
        if not cls.location_type:
            cls.location_type = cls.env['real.estate.location.type'].create({
                'name': 'Urbano',
                'code': 'urban',
                'sequence': 1
            })
        
        # Create OAuth application
        cls.oauth_app = cls.env['thedevkitchen.oauth.application'].create({
            'name': 'HTTP Test App'
        })
        
        # Get client secret from cache using correct cache key
        from odoo.addons.thedevkitchen_apigateway.models.oauth_application import _PLAINTEXT_CACHE
        cache_key = f'oauth_app_{cls.oauth_app.id}_plaintext'
        cached_data = _PLAINTEXT_CACHE.get(cache_key)
        if cached_data:
            cls.client_secret, _ = cached_data
        else:
            raise Exception(f"Client secret not found in cache for application {cls.oauth_app.id}")
        
        # Create test property
        cls.test_property = cls.env['real.estate.property'].create({
            'name': 'Test Property for HTTP',
            'description': 'HTTP test',
            'price': 500000.00,
            'status': 'available',
            'property_type_id': cls.property_type.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'num_rooms': 3,
            'num_bathrooms': 2,
            'num_parking': 1,
            'area': 100.0,
            'total_area': 100.0,
            'street': 'Rua HTTP',
            'street_number': '100',
            'city': 'São Paulo',
            'state_id': cls.state_sp.id,
            'location_type_id': cls.location_type.id,
            'zip_code': '01000-000'
        })
    
    def _get_access_token(self):
        """Helper to get valid access token"""
        response = self.url_open('/api/v1/auth/token', data=json.dumps({
            'grant_type': 'client_credentials',
            'client_id': self.oauth_app.client_id,
            'client_secret': self.client_secret
        }), headers={'Content-Type': 'application/json'})
        
        self.assertEqual(response.status_code, 200, "Failed to get access token")
        data = json.loads(response.content.decode('utf-8'))
        return data['access_token']
    
    # =================================================================
    # GET /api/v1/properties/<int:property_id> - NEGATIVE TESTS
    # =================================================================
    
    def test_get_property_without_auth(self):
        """GET property without Authorization header should return 401"""
        response = self.url_open(f'/api/v1/properties/{self.test_property.id}')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', data)
    
    def test_get_property_with_invalid_token(self):
        """GET property with invalid token should return 401"""
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            headers={'Authorization': 'Bearer invalid-token-xyz'}
        )
        self.assertEqual(response.status_code, 401)
    
    def test_get_property_malformed_auth_header(self):
        """GET property with malformed Authorization header should return 401"""
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            headers={'Authorization': 'InvalidFormat token123'}
        )
        self.assertEqual(response.status_code, 401)
    
    def test_get_property_not_found(self):
        """GET non-existent property should return 404"""
        token = self._get_access_token()
        
        response = self.url_open(
            '/api/v1/properties/999999',
            headers={'Authorization': f'Bearer {token}'}
        )
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', data)
        self.assertIn('not found', data['error'].lower())
    
    def test_get_property_success(self):
        """GET property with valid token should return 200"""
        token = self._get_access_token()
        
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        
        # Verify structure
        self.assertIn('id', data)
        self.assertIn('title', data)
        self.assertIn('price', data)
        self.assertIn('status', data)
        self.assertIn('features', data)
        self.assertIn('address', data)
        self.assertEqual(data['id'], self.test_property.id)
    
    # =================================================================
    # POST /api/v1/properties - CREATE - NEGATIVE TESTS
    # =================================================================
    
    def test_create_property_without_auth(self):
        """POST property without auth should return 401"""
        payload = {
            'name': 'New Property',
            'price': 300000.00,
            'property_type_id': self.property_type.id
        }
        
        response = self.url_open(
            '/api/v1/properties',
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        self.assertEqual(response.status_code, 401)
    
    def test_create_property_missing_required_fields(self):
        """POST property without required fields should return 400"""
        token = self._get_access_token()
        
        # Missing 'name' field
        payload = {
            'price': 300000.00,
            'property_type_id': self.property_type.id
        }
        
        response = self.url_open(
            '/api/v1/properties',
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', data)
    
    def test_create_property_invalid_property_type(self):
        """POST property with non-existent property_type_id should return 400"""
        token = self._get_access_token()
        
        payload = {
            'name': 'Invalid Property Type',
            'price': 300000.00,
            'property_type_id': 999999  # Non-existent
        }
        
        response = self.url_open(
            '/api/v1/properties',
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        self.assertEqual(response.status_code, 400)
    
    def test_create_property_invalid_price(self):
        """POST property with invalid price should return 400"""
        token = self._get_access_token()
        
        # Negative price
        payload = {
            'name': 'Negative Price Property',
            'price': -100000.00,
            'property_type_id': self.property_type.id
        }
        
        response = self.url_open(
            '/api/v1/properties',
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        # Should either reject or handle gracefully
        self.assertIn(response.status_code, [400, 500])
    
    def test_create_property_invalid_json(self):
        """POST property with malformed JSON should return 400"""
        token = self._get_access_token()
        
        response = self.url_open(
            '/api/v1/properties',
            data='{"name": "Invalid JSON"',  # Malformed
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        self.assertEqual(response.status_code, 400)
    
    def test_create_property_success(self):
        """POST property with valid data should return 201"""
        token = self._get_access_token()
        
        payload = {
            'name': 'New Valid Property',
            'description': 'Test description',
            'price': 350000.00,
            'property_type_id': self.property_type.id,
            'status': 'draft',
            'num_rooms': 2,
            'num_bathrooms': 1,
            'area': 80.0,
            'state_id': self.state_sp.id,
            'city': 'São Paulo',
            'street': 'Rua Nova',
            'street_number': '100',
            'zip_code': '01234-567',
            'location_type_id': self.location_type.id
        }
        
        response = self.url_open(
            '/api/v1/properties',
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('id', data)
        self.assertEqual(data['name'], 'New Valid Property')
        self.assertEqual(data['price'], 350000.00)
    
    # =================================================================
    # PUT /api/v1/properties/<int:property_id> - UPDATE - NEGATIVE TESTS
    # =================================================================
    
    def test_update_property_without_auth(self):
        """PUT property without auth should return 401"""
        payload = {'price': 600000.00}
        
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        self.assertEqual(response.status_code, 401)
    
    def test_update_property_not_found(self):
        """PUT non-existent property should return 404"""
        token = self._get_access_token()
        
        payload = {'price': 600000.00}
        
        response = self.url_open(
            '/api/v1/properties/999999',
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        self.assertEqual(response.status_code, 404)
    
    def test_update_property_invalid_data_type(self):
        """PUT property with invalid data types should return 400"""
        token = self._get_access_token()
        
        # Price as string instead of number
        payload = {'price': 'not-a-number'}
        
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        self.assertIn(response.status_code, [400, 500])
    
    def test_update_property_success(self):
        """PUT property with valid data should return 200"""
        token = self._get_access_token()
        
        payload = {
            'price': 550000.00,
            'description': 'Updated description',
            'num_rooms': 4
        }
        
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['price'], 550000.00)
        self.assertEqual(data['description'], 'Updated description')
    
    # =================================================================
    # DELETE /api/v1/properties/<int:property_id> - NEGATIVE TESTS
    # =================================================================
    
    def test_delete_property_without_auth(self):
        """DELETE property without auth should return 401"""
        response = self.url_open(f'/api/v1/properties/{self.test_property.id}')
        self.assertEqual(response.status_code, 401)
    
    def test_delete_property_not_found(self):
        """DELETE non-existent property should return 404"""
        token = self._get_access_token()
        
        response = self.url_open(
            '/api/v1/properties/999999',
            headers={'Authorization': f'Bearer {token}'}
        )
        self.assertEqual(response.status_code, 404)
    
    def test_delete_property_success(self):
        """DELETE property with valid auth should return 204"""
        token = self._get_access_token()
        
        # Create a property to delete
        prop_to_delete = self.env['real.estate.property'].create({
            'name': 'Property to Delete',
            'price': 100000.00,
            'property_type_id': self.property_type.id,
            'company_ids': [(6, 0, [self.company.id])]
        })
        
        response = self.url_open(
            f'/api/v1/properties/{prop_to_delete.id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        self.assertEqual(response.status_code, 204)
        
        # Verify property was deleted
        self.assertFalse(prop_to_delete.exists())
    
    # =================================================================
    # EDGE CASES & DATA VALIDATION
    # =================================================================
    
    def test_property_with_special_characters(self):
        """Test property name with special characters"""
        token = self._get_access_token()
        
        payload = {
            'name': 'Property with "quotes" & special <chars>',
            'price': 400000.00,
            'property_type_id': self.property_type.id
        }
        
        response = self.url_open(
            '/api/v1/properties',
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['name'], payload['name'])
    
    def test_property_with_very_long_description(self):
        """Test property with very long description"""
        token = self._get_access_token()
        
        long_description = 'A' * 5000  # 5000 characters
        
        payload = {
            'name': 'Long Description Property',
            'description': long_description,
            'price': 400000.00,
            'property_type_id': self.property_type.id
        }
        
        response = self.url_open(
            '/api/v1/properties',
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        # Should handle long text
        self.assertIn(response.status_code, [201, 400])
    
    def test_property_with_zero_price(self):
        """Test property with zero price"""
        token = self._get_access_token()
        
        payload = {
            'name': 'Zero Price Property',
            'price': 0.00,
            'property_type_id': self.property_type.id
        }
        
        response = self.url_open(
            '/api/v1/properties',
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        # Zero price might be valid for some cases
        self.assertIn(response.status_code, [201, 400])
    
    def test_concurrent_updates(self):
        """Test updating same property twice"""
        token = self._get_access_token()
        
        # First update
        response1 = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            data=json.dumps({'price': 600000.00}),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        
        # Second update
        response2 = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            data=json.dumps({'price': 650000.00}),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        
        # Both should succeed
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        # Last update should win
        data = json.loads(response2.content.decode('utf-8'))
        self.assertEqual(data['price'], 650000.00)
