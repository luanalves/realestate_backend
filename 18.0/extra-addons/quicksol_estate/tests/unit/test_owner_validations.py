# -*- coding: utf-8 -*-
"""
Unit Tests for Owner Validations (Feature 007)

Tests:
- T010: TestCreatorValidation - Only Owner or Admin can create Owners
- T011: TestLastOwnerProtection - Cannot delete/unlink last Owner of a Company
"""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError, ValidationError


@tagged('post_install', '-at_install', 'quicksol_estate', 'feature_007')
class TestCreatorValidation(TransactionCase):
    """
    Test that only users with Owner role or Admin can create Owners.
    
    Business Rule (T010):
    - Owner (with group_real_estate_owner) can create Owners
    - Admin (with base.group_system) can create Owners
    - Manager/Director/Agent cannot create Owners
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company_a = cls.env['thedevkitchen.estate.company'].create({
            'name': 'Test Company A',
            'cnpj': '12.345.678/0001-90',
            'email': 'companya@test.com',
            'phone': '11987654321',
        })
        
        # Get security groups
        cls.group_owner = cls.env.ref('quicksol_estate.group_real_estate_owner')
        cls.group_manager = cls.env.ref('quicksol_estate.group_real_estate_manager')
        cls.group_admin = cls.env.ref('base.group_system')
        
        # Create Owner user (linked to Company A)
        cls.owner_user = cls.env['res.users'].create({
            'name': 'Test Owner',
            'login': 'test_owner',
            'email': 'owner@test.com',
            'groups_id': [(6, 0, [cls.group_owner.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        # Create Manager user (no Owner group)
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Test Manager',
            'login': 'test_manager',
            'email': 'manager@test.com',
            'groups_id': [(6, 0, [cls.group_manager.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        # Create Admin user
        cls.admin_user = cls.env['res.users'].create({
            'name': 'Test Admin',
            'login': 'test_admin',
            'email': 'admin@test.com',
            'groups_id': [(6, 0, [cls.group_admin.id])],
        })

    def test_01_owner_can_create_owner(self):
        """Owner with group_real_estate_owner can create new Owners"""
        # Switch to Owner user context
        new_owner = self.env['res.users'].with_user(self.owner_user).create({
            'name': 'New Owner Created by Owner',
            'login': 'new_owner_by_owner',
            'email': 'newowner@test.com',
            'groups_id': [(6, 0, [self.group_owner.id])],
            'estate_company_ids': [(6, 0, [self.company_a.id])],
        })
        
        self.assertTrue(new_owner.exists(), "Owner should be able to create new Owner users")
        self.assertIn(self.group_owner, new_owner.groups_id, "New user should have Owner group")

    def test_02_admin_can_create_owner(self):
        """Admin with base.group_system can create new Owners"""
        new_owner = self.env['res.users'].with_user(self.admin_user).create({
            'name': 'New Owner Created by Admin',
            'login': 'new_owner_by_admin',
            'email': 'newowner2@test.com',
            'groups_id': [(6, 0, [self.group_owner.id])],
            'estate_company_ids': [(6, 0, [self.company_a.id])],
        })
        
        self.assertTrue(new_owner.exists(), "Admin should be able to create new Owner users")
        self.assertIn(self.group_owner, new_owner.groups_id, "New user should have Owner group")

    def test_03_manager_cannot_create_owner(self):
        """Manager without Owner group cannot create Owners"""
        with self.assertRaises(AccessError, msg="Manager should not be able to create Owner users"):
            self.env['res.users'].with_user(self.manager_user).create({
                'name': 'Should Fail',
                'login': 'should_fail',
                'email': 'fail@test.com',
                'groups_id': [(6, 0, [self.group_owner.id])],
                'estate_company_ids': [(6, 0, [self.company_a.id])],
            })


@tagged('post_install', '-at_install', 'quicksol_estate', 'feature_007')
class TestLastOwnerProtection(TransactionCase):
    """
    Test that the last active Owner of a Company cannot be deleted or unlinked.
    
    Business Rule (T011):
    - If Owner is the ONLY active Owner of ANY company, cannot soft-delete
    - If Owner is the ONLY active Owner of a company, cannot unlink from that company
    - If Owner has multiple companies and is last Owner of one, cannot unlink from that one
    - If Owner is not the last Owner, deletion/unlinking is allowed
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
        
        # Create Owner 1 (linked to both companies)
        cls.owner1 = cls.env['res.users'].create({
            'name': 'Owner 1',
            'login': 'owner1',
            'email': 'owner1@test.com',
            'groups_id': [(6, 0, [cls.group_owner.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id, cls.company_b.id])],
        })
        
        # Create Owner 2 (linked only to Company B)
        cls.owner2 = cls.env['res.users'].create({
            'name': 'Owner 2',
            'login': 'owner2',
            'email': 'owner2@test.com',
            'groups_id': [(6, 0, [cls.group_owner.id])],
            'estate_company_ids': [(6, 0, [cls.company_b.id])],
        })

    def test_01_cannot_delete_last_owner_of_any_company(self):
        """Cannot delete Owner if they are the only active Owner of ANY company"""
        # Owner1 is the ONLY owner of Company A
        # Even though Owner1 is also in Company B (with Owner2), cannot delete
        
        # Try to soft-delete Owner1 (active=False)
        with self.assertRaises(ValidationError, msg="Should not delete last owner of Company A"):
            self.owner1.write({'active': False})

    def test_02_can_delete_non_last_owner(self):
        """Can delete Owner if they are NOT the last owner of any company"""
        # Owner2 is in Company B alongside Owner1, so deletion is allowed
        self.owner2.write({'active': False})
        
        self.assertFalse(self.owner2.active, "Owner2 should be soft-deleted successfully")
        
        # Verify Company B still has at least one active owner
        active_owners = self.env['res.users'].search([
            ('estate_company_ids', 'in', [self.company_b.id]),
            ('groups_id', 'in', [self.group_owner.id]),
            ('active', '=', True),
        ])
        self.assertTrue(len(active_owners) >= 1, "Company B should still have active owners")

    def test_03_cannot_unlink_last_owner_from_company(self):
        """Cannot unlink Owner from Company if they are the last active Owner"""
        # Owner1 is the ONLY owner of Company A
        with self.assertRaises(ValidationError, msg="Should not unlink last owner from Company A"):
            self.owner1.write({
                'estate_company_ids': [(3, self.company_a.id)]  # Unlink from Company A
            })

    def test_04_can_unlink_non_last_owner_from_company(self):
        """Can unlink Owner from Company if they are NOT the last active Owner"""
        # Owner2 can be unlinked from Company B because Owner1 is also there
        original_companies = self.owner2.estate_company_ids
        self.assertIn(self.company_b, original_companies, "Owner2 should initially be in Company B")
        
        self.owner2.write({
            'estate_company_ids': [(3, self.company_b.id)]  # Unlink from Company B
        })
        
        self.assertNotIn(self.company_b, self.owner2.estate_company_ids,
                        "Owner2 should be unlinked from Company B")
        
        # Verify Company B still has active owners
        active_owners = self.env['res.users'].search([
            ('estate_company_ids', 'in', [self.company_b.id]),
            ('groups_id', 'in', [self.group_owner.id]),
            ('active', '=', True),
        ])
        self.assertTrue(len(active_owners) >= 1, "Company B should still have active owners")

    def test_05_last_owner_check_ignores_inactive_owners(self):
        """Last-owner check should only count ACTIVE owners"""
        # Create an inactive owner for Company A
        inactive_owner = self.env['res.users'].create({
            'name': 'Inactive Owner',
            'login': 'inactive_owner',
            'email': 'inactive@test.com',
            'groups_id': [(6, 0, [self.group_owner.id])],
            'estate_company_ids': [(6, 0, [self.company_a.id])],
            'active': False,
        })
        
        # Owner1 should still be considered the last ACTIVE owner of Company A
        with self.assertRaises(ValidationError, msg="Should not delete last ACTIVE owner"):
            self.owner1.write({'active': False})
