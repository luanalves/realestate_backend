# -*- coding: utf-8 -*-
"""
API Integration Tests for Company Management (Feature 007)

Tests:
- T028: TestCreateCompany - Create Company with auto-linkage to creator
"""

import json
from odoo.tests import tagged, HttpCase


@tagged('post_install', '-at_install', 'quicksol_estate', 'feature_007')
class TestCreateCompany(HttpCase):
    """
    Test Company creation via POST /api/v1/companies with auto-linkage.
    
    Business Rule (T028):
    - Owner can create Company with valid CNPJ
    - Company automatically links to creator's estate_company_ids
    - CNPJ must be unique (including soft-deleted)
    - Email and phone format validated
    - Returns 201 with HATEOAS links
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Get security groups
        cls.group_owner = cls.env.ref('quicksol_estate.group_real_estate_owner')
        cls.group_manager = cls.env.ref('quicksol_estate.group_real_estate_manager')
        
        # Create Owner user
        cls.owner_user = cls.env['res.users'].create({
            'name': 'Test Owner',
            'login': 'test_owner',
            'password': 'testpass123',
            'email': 'testowner@test.com',
            'groups_id': [(6, 0, [cls.group_owner.id])],
            'estate_company_ids': [],  # Initially no companies
        })
        
        # Create Manager user
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Test Manager',
            'login': 'test_manager',
            'password': 'testpass456',
            'email': 'testmanager@test.com',
            'groups_id': [(6, 0, [cls.group_manager.id])],
            'estate_company_ids': [],
        })

    def _get_jwt_token(self, login, password):
        """Helper to get JWT token for authentication"""
        response = self.url_open(
            '/api/auth/login',
            data=json.dumps({
                'login': login,
                'password': password,
                'db': self.env.cr.dbname,
            }),
            headers={'Content-Type': 'application/json'},
        )
        result = json.loads(response.content.decode('utf-8'))
        return result.get('access_token') or result.get('token')

    def test_01_owner_creates_company_auto_linkage(self):
        """Owner creates Company and is automatically linked via estate_company_ids"""
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        response = self.url_open(
            '/api/v1/companies',
            data=json.dumps({
                'name': 'Auto-Linked Company',
                'cnpj': '11.111.111/0001-81',
                'email': 'autolinked@test.com',
                'phone': '11987654321',
                'city': 'São Paulo',
                'state': 'SP',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(response.status_code, 201, "Should return 201 Created")
        
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('data', data)
        company_id = data['data']['id']
        
        # Verify Owner is auto-linked to the company
        self.owner_user.invalidate_recordset()
        self.assertIn(company_id, self.owner_user.estate_company_ids.ids,
                     "Owner should be auto-linked to created company")

    def test_02_company_with_valid_cnpj(self):
        """Company can be created with valid CNPJ (formatted or unformatted)"""
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        # Test with unformatted CNPJ
        response = self.url_open(
            '/api/v1/companies',
            data=json.dumps({
                'name': 'Unformatted CNPJ Company',
                'cnpj': '22222222000182',  # Unformatted
                'email': 'unformatted@test.com',
                'phone': '11888777666',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.content.decode('utf-8'))
        # CNPJ should be auto-formatted in response
        self.assertIn('/', data['data']['cnpj'], "CNPJ should be formatted")

    def test_03_duplicate_cnpj_rejected(self):
        """Cannot create Company with duplicate CNPJ"""
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        # Create first company
        self.url_open(
            '/api/v1/companies',
            data=json.dumps({
                'name': 'First Company',
                'cnpj': '33.333.333/0001-29',
                'email': 'first@test.com',
                'phone': '11777666555',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        # Try to create second company with same CNPJ
        response = self.url_open(
            '/api/v1/companies',
            data=json.dumps({
                'name': 'Duplicate Company',
                'cnpj': '33.333.333/0001-29',  # Same CNPJ
                'email': 'duplicate@test.com',
                'phone': '11666555444',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(response.status_code, 400,
                        "Should return 400 Bad Request for duplicate CNPJ")

    def test_04_invalid_cnpj_rejected(self):
        """Company creation fails with invalid CNPJ"""
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        response = self.url_open(
            '/api/v1/companies',
            data=json.dumps({
                'name': 'Invalid CNPJ Company',
                'cnpj': '11.111.111/0001-99',  # Invalid check digit
                'email': 'invalid@test.com',
                'phone': '11555444333',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(response.status_code, 400,
                        "Should return 400 Bad Request for invalid CNPJ")

    def test_05_invalid_email_rejected(self):
        """Company creation fails with invalid email format"""
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        response = self.url_open(
            '/api/v1/companies',
            data=json.dumps({
                'name': 'Invalid Email Company',
                'cnpj': '44.444.444/0001-53',
                'email': 'not-an-email',  # Invalid format
                'phone': '11444333222',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(response.status_code, 400,
                        "Should return 400 Bad Request for invalid email")

    def test_06_manager_cannot_create_company(self):
        """Manager without Owner role cannot create Companies"""
        token = self._get_jwt_token('test_manager', 'testpass456')
        
        response = self.url_open(
            '/api/v1/companies',
            data=json.dumps({
                'name': 'Manager Attempt',
                'cnpj': '55.555.555/0001-77',
                'email': 'manager@test.com',
                'phone': '11333222111',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(response.status_code, 403,
                        "Manager should get 403 Forbidden when creating Company")

    def test_07_hateoas_links_in_response(self):
        """Company creation response includes HATEOAS links"""
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        response = self.url_open(
            '/api/v1/companies',
            data=json.dumps({
                'name': 'HATEOAS Test Company',
                'cnpj': '66.666.666/0001-01',
                'email': 'hateoas@test.com',
                'phone': '11222111000',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('links', data, "Response should contain HATEOAS links")
        self.assertIn('self', data['links'], "Should have 'self' link")

    def test_08_company_list_multi_tenancy(self):
        """GET /companies returns only companies from user's estate_company_ids"""
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        # Create company (auto-linked to owner)
        create_response = self.url_open(
            '/api/v1/companies',
            data=json.dumps({
                'name': 'Owner Company',
                'cnpj': '77.777.777/0001-25',
                'email': 'ownercompany@test.com',
                'phone': '11111000999',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        company_id = json.loads(create_response.content.decode('utf-8'))['data']['id']
        
        # List companies
        list_response = self.url_open(
            '/api/v1/companies',
            headers={'Authorization': f'Bearer {token}'},
        )
        
        list_data = json.loads(list_response.content.decode('utf-8'))
        company_ids = [c['id'] for c in list_data['data']]
        
        self.assertIn(company_id, company_ids,
                     "Owner should see their own company in list")

    def test_09_company_get_by_id(self):
        """GET /companies/{id} returns company details with computed fields"""
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        # Create company
        create_response = self.url_open(
            '/api/v1/companies',
            data=json.dumps({
                'name': 'Detail Test Company',
                'cnpj': '88.888.888/0001-49',
                'email': 'detail@test.com',
                'phone': '11000999888',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        company_id = json.loads(create_response.content.decode('utf-8'))['data']['id']
        
        # Get company details
        get_response = self.url_open(
            f'/api/v1/companies/{company_id}',
            headers={'Authorization': f'Bearer {token}'},
        )
        
        self.assertEqual(get_response.status_code, 200)
        
        data = json.loads(get_response.content.decode('utf-8'))
        self.assertEqual(data['data']['name'], 'Detail Test Company')
        self.assertIn('agent_count', data['data'], "Should have computed field")
        self.assertIn('property_count', data['data'], "Should have computed field")

    def test_10_company_update(self):
        """PUT /companies/{id} updates company data"""
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        # Create company
        create_response = self.url_open(
            '/api/v1/companies',
            data=json.dumps({
                'name': 'Update Test Company',
                'cnpj': '99.999.999/0001-73',
                'email': 'update@test.com',
                'phone': '10999888777',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        company_id = json.loads(create_response.content.decode('utf-8'))['data']['id']
        
        # Update company
        update_response = self.url_open(
            f'/api/v1/companies/{company_id}',
            data=json.dumps({
                'name': 'Updated Company Name',
                'phone': '10888777666',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(update_response.status_code, 200)
        
        data = json.loads(update_response.content.decode('utf-8'))
        self.assertEqual(data['data']['name'], 'Updated Company Name')

    def test_11_company_soft_delete(self):
        """DELETE /companies/{id} performs soft delete (active=False)"""
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        # Create company
        create_response = self.url_open(
            '/api/v1/companies',
            data=json.dumps({
                'name': 'Delete Test Company',
                'cnpj': '10.101.010/0001-01',
                'email': 'delete@test.com',
                'phone': '10777666555',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        company_id = json.loads(create_response.content.decode('utf-8'))['data']['id']
        
        # Delete company
        delete_response = self.url_open(
            f'/api/v1/companies/{company_id}',
            headers={'Authorization': f'Bearer {token}'},
        )
        
        self.assertIn(delete_response.status_code, [200, 204],
                     "Should return 200 or 204 for successful delete")
        
        # Verify soft delete (active=False)
        company = self.env['thedevkitchen.estate.company'].browse(company_id)
        self.assertFalse(company.active, "Company should be soft-deleted (active=False)")
