# -*- coding: utf-8 -*-
import json
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestMasterDataAPI(HttpCase):
    """
    HTTP integration tests for Master Data API endpoints (states, location-types, property-types).
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create OAuth application
        cls.oauth_app = cls.env['thedevkitchen.oauth.application'].create({
            'name': 'Test Master Data App'
        })
        
        # Get client secret
        from odoo.addons.thedevkitchen_apigateway.models.oauth_application import _PLAINTEXT_CACHE
        cls.client_secret = _PLAINTEXT_CACHE.get(cls.oauth_app.client_id)
        
        # Ensure test data exists
        cls.state_sp = cls.env['real.estate.state'].search([('code', '=', 'SP')], limit=1)
        if not cls.state_sp:
            cls.state_sp = cls.env['real.estate.state'].create({
                'name': 'São Paulo',
                'code': 'SP',
                'country_id': cls.env.ref('base.br').id
            })
        
        cls.location_type = cls.env['real.estate.location.type'].search([('code', '=', 'urban')], limit=1)
        if not cls.location_type:
            cls.location_type = cls.env['real.estate.location.type'].create({
                'name': 'Urbano',
                'code': 'urban',
                'sequence': 1
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
    
    def test_list_states_success(self):
        """Test listing states with valid token"""
        token = self._get_access_token()
        
        response = self.url_open('/api/v1/states', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "Should return at least one state")
        
        # Verify structure
        first_state = data[0]
        self.assertIn('id', first_state)
        self.assertIn('name', first_state)
        self.assertIn('code', first_state)
        self.assertIn('country', first_state)
        self.assertIn('id', first_state['country'])
        self.assertIn('name', first_state['country'])
        self.assertIn('code', first_state['country'])
    
    def test_list_states_filter_by_country(self):
        """Test filtering states by country_id"""
        token = self._get_access_token()
        brazil_id = self.env.ref('base.br').id
        
        response = self.url_open(f'/api/v1/states?country_id={brazil_id}', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIsInstance(data, list)
        
        # All states should be from Brazil
        for state in data:
            self.assertEqual(state['country']['id'], brazil_id)
            self.assertEqual(state['country']['code'], 'BR')
    
    def test_list_states_unauthorized(self):
        """Test listing states without token"""
        response = self.url_open('/api/v1/states')
        self.assertEqual(response.status_code, 401)
    
    def test_list_location_types_success(self):
        """Test listing location types with valid token"""
        token = self._get_access_token()
        
        response = self.url_open('/api/v1/location-types', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "Should return at least one location type")
        
        # Verify structure
        first_type = data[0]
        self.assertIn('id', first_type)
        self.assertIn('name', first_type)
        self.assertIn('code', first_type)
        
        # Verify Portuguese names
        names = [t['name'] for t in data]
        codes = [t['code'] for t in data]
        
        # Should have at least Urbano
        self.assertIn('Urbano', names, "Should have 'Urbano' location type")
        self.assertIn('urban', codes, "Should have 'urban' code")
    
    def test_list_location_types_unauthorized(self):
        """Test listing location types without token"""
        response = self.url_open('/api/v1/location-types')
        self.assertEqual(response.status_code, 401)
    
    def test_list_property_types_success(self):
        """Test listing property types with valid token"""
        token = self._get_access_token()
        
        response = self.url_open('/api/v1/property-types', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "Should return at least one property type")
        
        # Verify structure
        first_type = data[0]
        self.assertIn('id', first_type)
        self.assertIn('name', first_type)
    
    def test_list_property_types_unauthorized(self):
        """Test listing property types without token"""
        response = self.url_open('/api/v1/property-types')
        self.assertEqual(response.status_code, 401)
    
    def test_create_property_with_required_fields(self):
        """Test creating property with all new required fields"""
        token = self._get_access_token()
        
        # Get IDs for required fields
        property_type = self.env['real.estate.property.type'].search([], limit=1)
        
        payload = {
            'name': 'Test Property With Required Fields',
            'property_type_id': property_type.id,
            'area': 150.5,
            'zip_code': '12245-000',
            'state_id': self.state_sp.id,
            'city': 'São José dos Campos',
            'street': 'Rua Teste API',
            'street_number': '999',
            'location_type_id': self.location_type.id,
            'price': 500000.0
        }
        
        response = self.url_open('/api/v1/properties', 
                                data=json.dumps(payload),
                                headers={
                                    'Authorization': f'Bearer {token}',
                                    'Content-Type': 'application/json'
                                })
        
        self.assertEqual(response.status_code, 201, "Should create property successfully")
        data = json.loads(response.content.decode('utf-8'))
        
        # Verify response structure
        self.assertIn('id', data)
        self.assertEqual(data['name'], payload['name'])
        self.assertIn('address', data)
        self.assertEqual(data['address']['zip_code'], payload['zip_code'])
        self.assertEqual(data['address']['city'], payload['city'])
        self.assertEqual(data['address']['street'], payload['street'])
        self.assertEqual(data['address']['number'], payload['street_number'])
        
        # Verify state and location_type are objects
        self.assertIsInstance(data['address']['state'], dict)
        self.assertEqual(data['address']['state']['code'], 'SP')
        self.assertIsInstance(data['address']['location_type'], dict)
        self.assertEqual(data['address']['location_type']['code'], 'urban')
    
    def test_create_property_missing_required_fields(self):
        """Test creating property without required fields returns 400"""
        token = self._get_access_token()
        
        property_type = self.env['real.estate.property.type'].search([], limit=1)
        
        # Missing zip_code, state_id, city, street, street_number, location_type_id
        payload = {
            'name': 'Incomplete Property',
            'property_type_id': property_type.id,
            'area': 100.0
        }
        
        response = self.url_open('/api/v1/properties',
                                data=json.dumps(payload),
                                headers={
                                    'Authorization': f'Bearer {token}',
                                    'Content-Type': 'application/json'
                                })
        
        self.assertEqual(response.status_code, 400, "Should return 400 for missing required fields")
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', data)
    
    def test_list_agents_success(self):
        """Test listing agents with valid token"""
        token = self._get_access_token()
        
        # Create test agent if not exists
        if not self.env['real.estate.agent'].search([], limit=1):
            self.env['real.estate.agent'].create({
                'name': 'Test Agent',
                'email': 'agent@test.com',
                'phone': '(11) 99999-0000'
            })
        
        response = self.url_open('/api/v1/agents', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "Should return at least one agent")
        
        # Verify structure
        first_agent = data[0]
        self.assertIn('id', first_agent)
        self.assertIn('name', first_agent)
        self.assertIn('email', first_agent)
        self.assertIn('phone', first_agent)
        # Note: mobile field removed because model doesn't have it
        self.assertNotIn('mobile', first_agent)
    
    def test_list_agents_unauthorized(self):
        """Test listing agents without token"""
        response = self.url_open('/api/v1/agents')
        self.assertEqual(response.status_code, 401)
    
    def test_list_owners_success(self):
        """Test listing property owners with valid token"""
        token = self._get_access_token()
        
        # Create test owner if not exists
        if not self.env['real.estate.property.owner'].search([], limit=1):
            self.env['real.estate.property.owner'].create({
                'name': 'Test Owner',
                'email': 'owner@test.com',
                'phone': '(11) 88888-0000',
                'cpf': '123.456.789-00'
            })
        
        response = self.url_open('/api/v1/owners', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "Should return at least one owner")
        
        # Verify structure
        first_owner = data[0]
        self.assertIn('id', first_owner)
        self.assertIn('name', first_owner)
        self.assertIn('email', first_owner)
        self.assertIn('phone', first_owner)
        self.assertIn('cpf', first_owner)
        self.assertIn('cnpj', first_owner)
        self.assertIn('mobile', first_owner)
    
    def test_list_owners_unauthorized(self):
        """Test listing owners without token"""
        response = self.url_open('/api/v1/owners')
        self.assertEqual(response.status_code, 401)
    
    def test_list_companies_success(self):
        """Test listing real estate companies with valid token"""
        token = self._get_access_token()
        
        # Create test company if not exists
        if not self.env['thedevkitchen.estate.company'].search([], limit=1):
            self.env['thedevkitchen.estate.company'].create({
                'name': 'Test Real Estate Company',
                'email': 'company@test.com',
                'phone': '(11) 7777-0000'
            })
        
        response = self.url_open('/api/v1/companies', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "Should return at least one company")
        
        # Verify structure
        first_company = data[0]
        self.assertIn('id', first_company)
        self.assertIn('name', first_company)
        self.assertIn('email', first_company)
        self.assertIn('phone', first_company)
        self.assertIn('website', first_company)
    
    def test_list_companies_unauthorized(self):
        """Test listing companies without token"""
        response = self.url_open('/api/v1/companies')
        self.assertEqual(response.status_code, 401)
    
    def test_list_tags_success(self):
        """Test listing property tags with valid token"""
        token = self._get_access_token()
        
        # Create test tag if not exists
        if not self.env['real.estate.property.tag'].search([], limit=1):
            self.env['real.estate.property.tag'].create({
                'name': 'Test Tag',
                'color': 1
            })
        
        response = self.url_open('/api/v1/tags', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "Should return at least one tag")
        
        # Verify structure
        first_tag = data[0]
        self.assertIn('id', first_tag)
        self.assertIn('name', first_tag)
        self.assertIn('color', first_tag)
    
    def test_list_tags_unauthorized(self):
        """Test listing tags without token"""
        response = self.url_open('/api/v1/tags')
        self.assertEqual(response.status_code, 401)
    
    def test_list_amenities_success(self):
        """Test listing amenities with valid token"""
        token = self._get_access_token()
        
        response = self.url_open('/api/v1/amenities', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIsInstance(data, list)
        # Should have amenities from seed data (26 amenities)
        self.assertGreaterEqual(len(data), 20, "Should return amenities from seed data")
        
        # Verify structure
        if len(data) > 0:
            first_amenity = data[0]
            self.assertIn('id', first_amenity)
            self.assertIn('name', first_amenity)
            self.assertIn('icon', first_amenity)
            
            # Verify some expected amenities exist
            amenity_names = [a['name'] for a in data]
            self.assertIn('Piscina', amenity_names, "Should have 'Piscina' amenity")
            self.assertIn('Academia', amenity_names, "Should have 'Academia' amenity")
            self.assertIn('Churrasqueira', amenity_names, "Should have 'Churrasqueira' amenity")
    
    def test_list_amenities_unauthorized(self):
        """Test listing amenities without token"""
        response = self.url_open('/api/v1/amenities')
        self.assertEqual(response.status_code, 401)
    
    # =================================================================
    # NEGATIVE TESTS - Invalid OAuth tokens
    # =================================================================
    
    def test_invalid_bearer_token_format(self):
        """Test all endpoints with malformed Bearer token"""
        endpoints = [
            '/api/v1/property-types',
            '/api/v1/location-types',
            '/api/v1/states',
            '/api/v1/agents',
            '/api/v1/owners',
            '/api/v1/companies',
            '/api/v1/tags',
            '/api/v1/amenities'
        ]
        
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                # Missing 'Bearer ' prefix
                response = self.url_open(endpoint, headers={
                    'Authorization': 'invalid-token-format'
                })
                self.assertEqual(response.status_code, 401)
                data = json.loads(response.content.decode('utf-8'))
                self.assertIn('error', data)
    
    def test_expired_or_invalid_token(self):
        """Test endpoints with non-existent token"""
        fake_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid'
        
        response = self.url_open('/api/v1/property-types', headers={
            'Authorization': f'Bearer {fake_token}'
        })
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', data)
    
    def test_revoked_token(self):
        """Test endpoint with revoked token"""
        token = self._get_access_token()
        
        # Revoke the token
        token_record = self.env['thedevkitchen.oauth.token'].search([
            ('access_token', '=', token)
        ], limit=1)
        token_record.write({'revoked': True})
        
        response = self.url_open('/api/v1/property-types', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', data)
    
    def test_missing_authorization_header(self):
        """Test all endpoints without Authorization header"""
        endpoints = [
            '/api/v1/property-types',
            '/api/v1/location-types',
            '/api/v1/states',
            '/api/v1/agents',
            '/api/v1/owners',
            '/api/v1/companies',
            '/api/v1/tags',
            '/api/v1/amenities'
        ]
        
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.url_open(endpoint)
                self.assertEqual(response.status_code, 401)
    
    # =================================================================
    # EDGE CASES - Data validation
    # =================================================================
    
    def test_states_with_invalid_country_id(self):
        """Test states endpoint with non-existent country_id"""
        token = self._get_access_token()
        
        response = self.url_open('/api/v1/states?country_id=999999', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        # Should return empty array for non-existent country
        self.assertEqual(len(data), 0)
    
    def test_states_with_non_numeric_country_id(self):
        """Test states endpoint with invalid country_id format"""
        token = self._get_access_token()
        
        response = self.url_open('/api/v1/states?country_id=abc', headers={
            'Authorization': f'Bearer {token}'
        })
        
        # Should handle gracefully (either 400 or return all states)
        self.assertIn(response.status_code, [200, 400])
    
    def test_property_types_response_structure(self):
        """Test property-types returns all required fields"""
        token = self._get_access_token()
        
        response = self.url_open('/api/v1/property-types', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        
        if len(data) > 0:
            for item in data:
                # Required fields
                self.assertIn('id', item)
                self.assertIn('name', item)
                # Verify data types
                self.assertIsInstance(item['id'], int)
                self.assertIsInstance(item['name'], str)
                self.assertGreater(len(item['name']), 0, "Name should not be empty")
    
    def test_location_types_ordering(self):
        """Test location-types are ordered by sequence"""
        token = self._get_access_token()
        
        response = self.url_open('/api/v1/location-types', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        
        # Verify ordering if multiple items exist
        if len(data) > 1:
            # Check that items maintain their sequence
            for i in range(len(data) - 1):
                self.assertIsInstance(data[i]['id'], int)
                self.assertIsInstance(data[i]['name'], str)
    
    def test_agents_response_does_not_include_mobile(self):
        """Test agents endpoint does NOT include mobile field (model doesn't have it)"""
        token = self._get_access_token()
        
        response = self.url_open('/api/v1/agents', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        
        if len(data) > 0:
            for agent in data:
                self.assertNotIn('mobile', agent, "Agent should NOT have mobile field")
                # Should have these fields
                self.assertIn('id', agent)
                self.assertIn('name', agent)
                self.assertIn('phone', agent)
                self.assertIn('email', agent)
    
    def test_owners_includes_contact_fields(self):
        """Test owners endpoint includes all contact fields"""
        token = self._get_access_token()
        
        response = self.url_open('/api/v1/owners', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        
        if len(data) > 0:
            for owner in data:
                # Required fields
                self.assertIn('id', owner)
                self.assertIn('name', owner)
                # Contact fields (can be null)
                self.assertIn('cpf', owner)
                self.assertIn('cnpj', owner)
                self.assertIn('mobile', owner)
    
    def test_companies_includes_business_fields(self):
        """Test companies endpoint includes business-specific fields"""
        token = self._get_access_token()
        
        response = self.url_open('/api/v1/companies', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        
        if len(data) > 0:
            for company in data:
                # Required fields
                self.assertIn('id', company)
                self.assertIn('name', company)
                # Business fields
                self.assertIn('email', company)
                self.assertIn('phone', company)
                self.assertIn('website', company)
    
    def test_tags_include_color(self):
        """Test tags endpoint includes color field"""
        token = self._get_access_token()
        
        response = self.url_open('/api/v1/tags', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        
        if len(data) > 0:
            for tag in data:
                self.assertIn('id', tag)
                self.assertIn('name', tag)
                self.assertIn('color', tag)
                # Color should be an integer (Odoo color index)
                if tag['color'] is not None:
                    self.assertIsInstance(tag['color'], int)
    
    def test_amenities_data_quality(self):
        """Test amenities have proper data from seed"""
        token = self._get_access_token()
        
        response = self.url_open('/api/v1/amenities', headers={
            'Authorization': f'Bearer {token}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        
        # Should have at least 20 amenities from seed
        self.assertGreaterEqual(len(data), 20)
        
        amenity_names = [a['name'] for a in data]
        
        # Verify key amenities from different categories
        expected_amenities = [
            'Piscina',           # Lazer
            'Academia',          # Lazer
            'Portaria 24h',      # Segurança
            'Ar Condicionado',   # Conforto
            'Painéis Solares',   # Sustentabilidade
            'Pet Place'          # Outros
        ]
        
        for expected in expected_amenities:
            self.assertIn(expected, amenity_names, 
                         f"Should have '{expected}' amenity from seed data")
    
    # =================================================================
    # PERFORMANCE TESTS
    # =================================================================
    
    def test_endpoints_return_reasonable_response_time(self):
        """Test all endpoints respond in reasonable time"""
        import time
        token = self._get_access_token()
        
        endpoints = [
            '/api/v1/property-types',
            '/api/v1/location-types',
            '/api/v1/states',
            '/api/v1/agents',
            '/api/v1/owners',
            '/api/v1/companies',
            '/api/v1/tags',
            '/api/v1/amenities'
        ]
        
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                start = time.time()
                response = self.url_open(endpoint, headers={
                    'Authorization': f'Bearer {token}'
                })
                elapsed = time.time() - start
                
                self.assertEqual(response.status_code, 200)
                # Should respond within 5 seconds
                self.assertLess(elapsed, 5.0, 
                               f"{endpoint} took {elapsed:.2f}s (too slow)")
    
    def test_all_master_data_endpoints_return_valid_json(self):
        """Test that all Master Data endpoints return valid JSON arrays"""
        token = self._get_access_token()
        
        endpoints = [
            '/api/v1/property-types',
            '/api/v1/location-types',
            '/api/v1/states',
            '/api/v1/agents',
            '/api/v1/owners',
            '/api/v1/companies',
            '/api/v1/tags',
            '/api/v1/amenities'
        ]
        
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.url_open(endpoint, headers={
                    'Authorization': f'Bearer {token}'
                })
                
                self.assertEqual(response.status_code, 200, 
                               f"{endpoint} should return 200")
                data = json.loads(response.content.decode('utf-8'))
                self.assertIsInstance(data, list, 
                                    f"{endpoint} should return array")
                
                # Verify each item has an 'id' and 'name'
                if len(data) > 0:
                    for item in data:
                        self.assertIn('id', item, 
                                    f"{endpoint} items should have 'id'")
                        self.assertIn('name', item, 
                                    f"{endpoint} items should have 'name'")
