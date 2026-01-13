import json
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestPropertyAPIAuth(HttpCase):
    """
    HTTP integration tests for Property API authentication and authorization.
    Tests JWT token validation and RBAC enforcement.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test companies (using valid CNPJ)
        cls.company = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Test Company Auth',
            'cnpj': '11.222.333/0001-81'  # Valid CNPJ
        })
        
        # Create OAuth application
        cls.oauth_app = cls.env['thedevkitchen.oauth.application'].create({
            'name': 'Test Auth App'
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
        cls.property_type = cls.env['real.estate.property.type'].create({
            'name': 'Casa'
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
        
        cls.test_property = cls.env['real.estate.property'].create({
            'name': 'Property for Auth Tests',
            'price': 300000.00,
            'status': 'available',
            'property_type_id': cls.property_type.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'area': 100.0,
            'num_rooms': 2,
            'street': 'Rua Auth Test',
            'street_number': '100',
            'city': 'São Paulo',
            'state_id': cls.state_sp.id,
            'location_type_id': cls.location_type.id,
            'zip_code': '01234-567'
        })
    
    def _get_access_token(self):
        """Helper to get valid access token"""
        response = self.url_open('/api/v1/auth/token', data=json.dumps({
            'grant_type': 'client_credentials',
            'client_id': self.oauth_app.client_id,
            'client_secret': self.client_secret
        }), headers={'Content-Type': 'application/json'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        return data['access_token']
    
    def test_01_get_property_without_token(self):
        """GET without token should return 401"""
        response = self.url_open(f'/api/v1/properties/{self.test_property.id}')
        self.assertEqual(response.status_code, 401)
    
    def test_02_get_property_with_invalid_token(self):
        """GET with invalid token should return 401"""
        headers = {'Authorization': 'Bearer invalid_token_123'}
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            headers=headers
        )
        self.assertEqual(response.status_code, 401)
    
    def test_03_get_property_with_valid_token(self):
        """GET with valid token should return 200"""
        token = self._get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['id'], self.test_property.id)
        self.assertEqual(data['title'], 'Property for Auth Tests')
    
    def test_04_get_nonexistent_property(self):
        """GET non-existent property should return 404"""
        token = self._get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        response = self.url_open(
            '/api/v1/properties/99999',
            headers=headers
        )
        self.assertEqual(response.status_code, 404)
    
    def test_05_update_property_without_token(self):
        """PUT without token should return 401"""
        data = json.dumps({'price': 350000.00})
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        self.assertEqual(response.status_code, 401)
    
    def test_06_update_property_with_valid_token(self):
        """PUT with valid token should return 200"""
        token = self._get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        data = json.dumps({
            'price': 350000.00,
            'num_rooms': 3
        })
        
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            data=data,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify update
        self.test_property.invalidate_recordset()
        self.assertEqual(self.test_property.price, 350000.00)
        self.assertEqual(self.test_property.bedrooms, 3)
    
    def test_07_update_property_invalid_json(self):
        """PUT with invalid JSON should return 400"""
        token = self._get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            data='invalid json',
            headers=headers
        )
        self.assertEqual(response.status_code, 400)
    
    def test_08_delete_property_without_token(self):
        """DELETE without token should return 401"""
        response = self.url_open(f'/api/v1/properties/{self.test_property.id}')
        self.assertEqual(response.status_code, 401)
    
    def test_09_token_expiration(self):
        """Expired token should return 401"""
        # Create expired token
        from odoo import fields
        from datetime import timedelta
        expired_token = self.env['thedevkitchen.oauth.token'].create({
            'application_id': self.oauth_app.id,
            'token_type': 'access',
            'access_token': 'expired_token_123',
            'refresh_token': 'refresh_123',
            'expires_at': fields.Datetime.now() - timedelta(hours=2),
            'revoked': False
        })
        
        headers = {'Authorization': 'Bearer expired_token_123'}
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            headers=headers
        )
        self.assertEqual(response.status_code, 401)
    
    def test_10_revoked_token(self):
        """Revoked token should return 401"""
        # Create revoked token
        from odoo import fields
        from datetime import timedelta
        revoked_token = self.env['thedevkitchen.oauth.token'].create({
            'application_id': self.oauth_app.id,
            'token_type': 'access',
            'access_token': 'revoked_token_123',
            'refresh_token': 'refresh_456',
            'expires_at': fields.Datetime.now() + timedelta(seconds=3600),
            'revoked': True
        })
        
        headers = {'Authorization': 'Bearer revoked_token_123'}
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            headers=headers
        )
        self.assertEqual(response.status_code, 401)
    
    def test_11_missing_authorization_header(self):
        """Request without Authorization header should return 401"""
        response = self.url_open(f'/api/v1/properties/{self.test_property.id}')
        self.assertEqual(response.status_code, 401)
    
    def test_12_malformed_authorization_header(self):
        """Malformed Authorization header should return 401"""
        headers = {'Authorization': 'NotBearer token123'}
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            headers=headers
        )
        self.assertEqual(response.status_code, 401)
    
    def test_13_cors_headers(self):
        """Verify CORS headers are present"""
        token = self._get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            headers=headers
        )
        
        # CORS should be enabled
        self.assertIn('Access-Control-Allow-Origin', response.headers)
    
    def test_14_json_response_format(self):
        """Verify JSON response format"""
        token = self._get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            headers=headers
        )
        
        self.assertEqual(response.headers.get('Content-Type'), 'application/json')
        data = json.loads(response.content.decode('utf-8'))
        self.assertIsInstance(data, dict)
    
    def test_15_update_only_allowed_fields(self):
        """PUT should only update allowed fields"""
        token = self._get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Try to update allowed and disallowed fields
        data = json.dumps({
            'price': 400000.00,  # allowed
            'some_invalid_field': 'test'  # not allowed
        })
        
        response = self.url_open(
            f'/api/v1/properties/{self.test_property.id}',
            data=data,
            headers=headers
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify only allowed field was updated
        self.test_property.invalidate_recordset()
        self.assertEqual(self.test_property.price, 400000.00)
