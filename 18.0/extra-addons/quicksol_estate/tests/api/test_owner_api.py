# -*- coding: utf-8 -*-
"""
API Integration Tests for Owner Management (Feature 007)

Tests:
- T012: TestCreateOwnerIndependent - Create Owner without Company via API
- T013: TestLinkOwnerToCompany - Link/unlink Owner to/from Company via API
"""

import json
from odoo.tests import tagged, HttpCase


@tagged('post_install', '-at_install', 'quicksol_estate', 'feature_007')
class TestCreateOwnerIndependent(HttpCase):
    """
    Test independent Owner creation via POST /api/v1/owners (without company).
    
    Business Rule (T012):
    - Owner can be created WITHOUT a company
    - Owner automatically gets group_real_estate_owner assigned
    - estate_company_ids starts empty []
    - Only Owner or Admin can create Owners
    - Returns 201 with HATEOAS links
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company for creator
        cls.company_a = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Creator Company',
            'cnpj': '12.345.678/0001-90',
            'email': 'creator@test.com',
            'phone': '11987654321',
        })
        
        # Get security groups
        cls.group_owner = cls.env.ref('quicksol_estate.group_real_estate_owner')
        cls.group_manager = cls.env.ref('quicksol_estate.group_real_estate_manager')
        
        # Create Owner user (creator)
        cls.owner_creator = cls.env['res.users'].create({
            'name': 'Owner Creator',
            'login': 'owner_creator',
            'password': 'testpass123',
            'email': 'ownercreator@test.com',
            'groups_id': [(6, 0, [cls.group_owner.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        # Create Manager user (non-owner)
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Manager User',
            'login': 'manager_user',
            'password': 'testpass456',
            'email': 'manager@test.com',
            'groups_id': [(6, 0, [cls.group_manager.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
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

    def test_01_create_owner_without_company(self):
        """Owner can create another Owner without specifying a company"""
        token = self._get_jwt_token('owner_creator', 'testpass123')
        
        response = self.url_open(
            '/api/v1/owners',
            data=json.dumps({
                'name': 'New Independent Owner',
                'email': 'independent@test.com',
                'phone': '11999998888',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(response.status_code, 201, "Should return 201 Created")
        
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('data', data, "Response should contain 'data' key")
        self.assertIn('id', data['data'], "Response should contain owner ID")
        self.assertEqual(data['data']['name'], 'New Independent Owner')
        self.assertEqual(data['data']['email'], 'independent@test.com')
        self.assertEqual(len(data['data']['estate_company_ids']), 0,
                        "New owner should have empty estate_company_ids")
        
        # Verify HATEOAS links
        self.assertIn('links', data, "Response should contain HATEOAS links")
        self.assertIn('self', data['links'])
        self.assertIn('companies', data['links'])

    def test_02_created_owner_has_group_assigned(self):
        """Created Owner automatically gets group_real_estate_owner"""
        token = self._get_jwt_token('owner_creator', 'testpass123')
        
        response = self.url_open(
            '/api/v1/owners',
            data=json.dumps({
                'name': 'Owner With Group',
                'email': 'withgroup@test.com',
                'phone': '11888887777',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        data = json.loads(response.content.decode('utf-8'))
        owner_id = data['data']['id']
        
        # Verify in database that group was assigned
        owner_user = self.env['res.users'].browse(owner_id)
        self.assertIn(self.group_owner, owner_user.groups_id,
                     "Owner should have group_real_estate_owner assigned")

    def test_03_manager_cannot_create_owner(self):
        """Manager without Owner role cannot create Owners"""
        token = self._get_jwt_token('manager_user', 'testpass456')
        
        response = self.url_open(
            '/api/v1/owners',
            data=json.dumps({
                'name': 'Should Fail',
                'email': 'shouldfail@test.com',
                'phone': '11777776666',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(response.status_code, 403,
                        "Manager should get 403 Forbidden when creating Owner")

    def test_04_validation_phone_format(self):
        """API validates Brazilian phone format (10-11 digits)"""
        token = self._get_jwt_token('owner_creator', 'testpass123')
        
        # Invalid phone (too short)
        response = self.url_open(
            '/api/v1/owners',
            data=json.dumps({
                'name': 'Invalid Phone',
                'email': 'invalidphone@test.com',
                'phone': '123',  # Too short
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(response.status_code, 400,
                        "Should return 400 Bad Request for invalid phone")
        
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', data, "Response should contain error details")

    def test_05_validation_email_format(self):
        """API validates email format (RFC 5322)"""
        token = self._get_jwt_token('owner_creator', 'testpass123')
        
        # Invalid email
        response = self.url_open(
            '/api/v1/owners',
            data=json.dumps({
                'name': 'Invalid Email',
                'email': 'not-an-email',  # Invalid format
                'phone': '11666665555',
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(response.status_code, 400,
                        "Should return 400 Bad Request for invalid email")


@tagged('post_install', '-at_install', 'quicksol_estate', 'feature_007')
class TestLinkOwnerToCompany(HttpCase):
    """
    Test linking/unlinking Owner to/from Company via API.
    
    Business Rule (T013):
    - POST /api/v1/owners/{id}/companies links Owner to Company
    - DELETE /api/v1/owners/{id}/companies/{cid} unlinks Owner from Company
    - Cannot unlink if Owner is last active Owner of that Company
    - Returns appropriate HTTP codes and HATEOAS links
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test companies
        cls.company_a = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Company A',
            'cnpj': '11.111.111/0001-11',
            'email': 'companya@test.com',
            'phone': '11111111111',
        })
        
        cls.company_b = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Company B',
            'cnpj': '22.222.222/0001-22',
            'email': 'companyb@test.com',
            'phone': '22222222222',
        })
        
        # Get Owner group
        cls.group_owner = cls.env.ref('quicksol_estate.group_real_estate_owner')
        
        # Create Owner (initially without companies)
        cls.owner_user = cls.env['res.users'].create({
            'name': 'Test Owner',
            'login': 'test_owner',
            'password': 'testpass123',
            'email': 'testowner@test.com',
            'groups_id': [(6, 0, [cls.group_owner.id])],
            'estate_company_ids': [],  # Initially no companies
        })
        
        # Create another Owner for Company B
        cls.owner2 = cls.env['res.users'].create({
            'name': 'Owner 2',
            'login': 'owner2',
            'password': 'testpass456',
            'email': 'owner2@test.com',
            'groups_id': [(6, 0, [cls.group_owner.id])],
            'estate_company_ids': [(6, 0, [cls.company_b.id])],
        })

    def _get_jwt_token(self, login, password):
        """Helper to get JWT token"""
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

    def test_01_link_owner_to_company(self):
        """Owner can be linked to a Company via POST /owners/{id}/companies"""
        # First, link owner_user to Company A to get access
        self.owner_user.write({'estate_company_ids': [(4, self.company_a.id)]})
        
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        # Link to Company B
        response = self.url_open(
            f'/api/v1/owners/{self.owner_user.id}/companies',
            data=json.dumps({
                'company_id': self.company_b.id,
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(response.status_code, 200, "Should return 200 OK")
        
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('data', data)
        self.assertIn(self.company_b.id, data['data']['estate_company_ids'],
                     "Owner should now be linked to Company B")

    def test_02_unlink_owner_from_company(self):
        """Owner can be unlinked from Company if not the last active Owner"""
        # Link owner_user to both companies
        self.owner_user.write({
            'estate_company_ids': [(6, 0, [self.company_a.id, self.company_b.id])]
        })
        
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        # Unlink from Company B (owner2 is also in Company B, so allowed)
        response = self.url_open(
            f'/api/v1/owners/{self.owner_user.id}/companies/{self.company_b.id}',
            headers={
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(response.status_code, 200, "Should return 200 OK")
        
        # Verify owner_user no longer in Company B
        self.owner_user.invalidate_recordset()
        self.assertNotIn(self.company_b, self.owner_user.estate_company_ids,
                        "Owner should be unlinked from Company B")

    def test_03_cannot_unlink_last_owner(self):
        """Cannot unlink Owner if they are the last active Owner of that Company"""
        # Make owner_user the ONLY owner of Company A
        self.owner_user.write({
            'estate_company_ids': [(6, 0, [self.company_a.id])]
        })
        
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        # Try to unlink from Company A (should fail - last owner)
        response = self.url_open(
            f'/api/v1/owners/{self.owner_user.id}/companies/{self.company_a.id}',
            headers={
                'Authorization': f'Bearer {token}',
            },
        )
        
        self.assertEqual(response.status_code, 400,
                        "Should return 400 Bad Request when unlinking last owner")
        
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', data, "Response should contain error details")

    def test_04_link_returns_hateoas_links(self):
        """Link operation returns HATEOAS links for navigation"""
        self.owner_user.write({'estate_company_ids': [(4, self.company_a.id)]})
        
        token = self._get_jwt_token('test_owner', 'testpass123')
        
        response = self.url_open(
            f'/api/v1/owners/{self.owner_user.id}/companies',
            data=json.dumps({
                'company_id': self.company_b.id,
            }),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        
        data = json.loads(response.content.decode('utf-8'))
        self.assertIn('links', data, "Response should contain HATEOAS links")
        self.assertIn('self', data['links'], "Should have 'self' link")
        self.assertIn('companies', data['links'], "Should have 'companies' link")


@tagged('post_install', '-at_install', 'quicksol_estate', 'feature_007')
class TestNewOwnerWithoutCompany(HttpCase):
    """
    Test T049: New Owner without company can use API gracefully.
    
    Business Rule:
    - Owner can create first company → auto-linked
    - No errors when owner has no companies yet
    
    Note: Owner listing removed from API. Use GET /api/v1/companies/{id} to see company owners.
    Owner profile operations moved to /api/v1/users/profile endpoint.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.group_owner = cls.env.ref('quicksol_estate.group_real_estate_owner')
        
        # Create Owner without any company
        cls.new_owner = cls.env['res.users'].create({
            'name': 'New Owner No Company',
            'login': 'newowner@nocompany.com',
            'password': 'newowner123',
            'email': 'newowner@nocompany.com',
            'groups_id': [(6, 0, [cls.group_owner.id])],
            'estate_company_ids': [],  # No companies initially
        })

    def test_owner_without_company_can_create_company(self):
        """Owner without companies can create first company (auto-linked)."""
        self.authenticate('newowner@nocompany.com', 'newowner123')
        
        response = self.url_open(
            '/api/v1/companies',
            data=json.dumps({
                'name': 'First Company',
                'cnpj': '60606060000606',
                'email': 'first@company.com',
                'phone': '11888777666',
            }),
            headers={'Content-Type': 'application/json'},
        )
        
        self.assertEqual(response.status_code, 201,
                        "Owner should be able to create first company")
        
        # Verify owner is now linked to company
        self.new_owner.invalidate_recordset()
        self.assertGreater(len(self.new_owner.estate_company_ids), 0,
                          "Owner should be auto-linked to created company")

