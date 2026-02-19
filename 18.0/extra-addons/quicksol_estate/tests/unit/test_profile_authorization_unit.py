# -*- coding: utf-8 -*-
"""
Unit Tests for RBAC Authorization Matrix (Feature 010 - T15)

Tests the profile creation authorization matrix that limits which roles
can create which profile types.

Matrix (from profile_api.py):
- Owner: all 9 types (owner, director, manager, agent, prospector, receptionist, financial, legal, portal)
- Manager/Director: 5 operational types (agent, prospector, receptionist, financial, legal)
- Agent: 2 types (owner, portal) - for property owners and tenants

Run:
    docker compose exec odoo python3 /mnt/extra-addons/quicksol_estate/tests/unit/test_profile_authorization_unit.py
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the authorization matrix constant
try:
    from controllers.profile_api import PROFILE_CREATION_MATRIX
except ImportError:
    # Mock for standalone testing
    PROFILE_CREATION_MATRIX = {
        'quicksol_estate.group_real_estate_owner': [
            'owner', 'director', 'manager', 'agent', 'prospector', 
            'receptionist', 'financial', 'legal', 'portal'
        ],
        'quicksol_estate.group_real_estate_director': [
            'agent', 'prospector', 'receptionist', 'financial', 'legal'
        ],
        'quicksol_estate.group_real_estate_manager': [
            'agent', 'prospector', 'receptionist', 'financial', 'legal'
        ],
        'quicksol_estate.group_real_estate_agent': [
            'owner', 'portal'
        ],
    }


class TestOwnerProfileCreation(unittest.TestCase):
    """Test Owner role can create all 9 profile types"""
    
    def test_owner_can_create_all_types(self):
        """Owner has permission for all 9 profile types"""
        owner_group = 'quicksol_estate.group_real_estate_owner'
        allowed_types = PROFILE_CREATION_MATRIX[owner_group]
        
        # Owner should have all 9 types
        self.assertEqual(len(allowed_types), 9)
        self.assertIn('owner', allowed_types)
        self.assertIn('director', allowed_types)
        self.assertIn('manager', allowed_types)
        self.assertIn('agent', allowed_types)
        self.assertIn('prospector', allowed_types)
        self.assertIn('receptionist', allowed_types)
        self.assertIn('financial', allowed_types)
        self.assertIn('legal', allowed_types)
        self.assertIn('portal', allowed_types)
    
    def test_owner_can_create_owner_profile(self):
        """Owner can create another owner profile"""
        owner_group = 'quicksol_estate.group_real_estate_owner'
        allowed_types = PROFILE_CREATION_MATRIX[owner_group]
        
        self.assertIn('owner', allowed_types)
    
    def test_owner_can_create_portal_profile(self):
        """Owner can create portal (tenant) profiles"""
        owner_group = 'quicksol_estate.group_real_estate_owner'
        allowed_types = PROFILE_CREATION_MATRIX[owner_group]
        
        self.assertIn('portal', allowed_types)


class TestManagerProfileCreation(unittest.TestCase):
    """Test Manager role can create 5 operational profile types"""
    
    def test_manager_can_create_operational_types(self):
        """Manager can create 5 operational types"""
        manager_group = 'quicksol_estate.group_real_estate_manager'
        allowed_types = PROFILE_CREATION_MATRIX[manager_group]
        
        # Manager should have 5 operational types
        self.assertEqual(len(allowed_types), 5)
        self.assertIn('agent', allowed_types)
        self.assertIn('prospector', allowed_types)
        self.assertIn('receptionist', allowed_types)
        self.assertIn('financial', allowed_types)
        self.assertIn('legal', allowed_types)
    
    def test_manager_cannot_create_owner(self):
        """Manager cannot create owner profiles"""
        manager_group = 'quicksol_estate.group_real_estate_manager'
        allowed_types = PROFILE_CREATION_MATRIX[manager_group]
        
        self.assertNotIn('owner', allowed_types)
    
    def test_manager_cannot_create_director(self):
        """Manager cannot create director profiles"""
        manager_group = 'quicksol_estate.group_real_estate_manager'
        allowed_types = PROFILE_CREATION_MATRIX[manager_group]
        
        self.assertNotIn('director', allowed_types)
    
    def test_manager_cannot_create_manager(self):
        """Manager cannot create other manager profiles"""
        manager_group = 'quicksol_estate.group_real_estate_manager'
        allowed_types = PROFILE_CREATION_MATRIX[manager_group]
        
        self.assertNotIn('manager', allowed_types)
    
    def test_manager_cannot_create_portal(self):
        """Manager cannot create portal profiles"""
        manager_group = 'quicksol_estate.group_real_estate_manager'
        allowed_types = PROFILE_CREATION_MATRIX[manager_group]
        
        self.assertNotIn('portal', allowed_types)


class TestDirectorProfileCreation(unittest.TestCase):
    """Test Director role has same permissions as Manager"""
    
    def test_director_same_as_manager(self):
        """Director has same permissions as Manager (5 operational types)"""
        director_group = 'quicksol_estate.group_real_estate_director'
        manager_group = 'quicksol_estate.group_real_estate_manager'
        
        director_types = PROFILE_CREATION_MATRIX[director_group]
        manager_types = PROFILE_CREATION_MATRIX[manager_group]
        
        # Should be identical
        self.assertEqual(set(director_types), set(manager_types))
    
    def test_director_can_create_agent(self):
        """Director can create agent profiles"""
        director_group = 'quicksol_estate.group_real_estate_director'
        allowed_types = PROFILE_CREATION_MATRIX[director_group]
        
        self.assertIn('agent', allowed_types)


class TestAgentProfileCreation(unittest.TestCase):
    """Test Agent role can create only 2 types: owner and portal"""
    
    def test_agent_can_create_owner_and_portal(self):
        """Agent can create owner (property owner) and portal (tenant)"""
        agent_group = 'quicksol_estate.group_real_estate_agent'
        allowed_types = PROFILE_CREATION_MATRIX[agent_group]
        
        # Agent should have only 2 types
        self.assertEqual(len(allowed_types), 2)
        self.assertIn('owner', allowed_types)
        self.assertIn('portal', allowed_types)
    
    def test_agent_cannot_create_operational_types(self):
        """Agent cannot create operational profile types"""
        agent_group = 'quicksol_estate.group_real_estate_agent'
        allowed_types = PROFILE_CREATION_MATRIX[agent_group]
        
        # Should NOT have any operational types
        self.assertNotIn('agent', allowed_types)
        self.assertNotIn('prospector', allowed_types)
        self.assertNotIn('receptionist', allowed_types)
        self.assertNotIn('financial', allowed_types)
        self.assertNotIn('legal', allowed_types)
    
    def test_agent_cannot_create_admin_types(self):
        """Agent cannot create admin profile types"""
        agent_group = 'quicksol_estate.group_real_estate_agent'
        allowed_types = PROFILE_CREATION_MATRIX[agent_group]
        
        # Should NOT have any admin types
        self.assertNotIn('director', allowed_types)
        self.assertNotIn('manager', allowed_types)


class TestAuthorizationMatrixStructure(unittest.TestCase):
    """Test authorization matrix structure and completeness"""
    
    def test_all_groups_present(self):
        """All 4 creator roles are in matrix"""
        expected_groups = [
            'quicksol_estate.group_real_estate_owner',
            'quicksol_estate.group_real_estate_director',
            'quicksol_estate.group_real_estate_manager',
            'quicksol_estate.group_real_estate_agent',
        ]
        
        for group in expected_groups:
            self.assertIn(group, PROFILE_CREATION_MATRIX)
    
    def test_all_profile_types_covered(self):
        """All 9 profile types appear in at least one role"""
        all_types = {
            'owner', 'director', 'manager', 'agent', 'prospector',
            'receptionist', 'financial', 'legal', 'portal'
        }
        
        # Collect all types from all roles
        types_in_matrix = set()
        for types_list in PROFILE_CREATION_MATRIX.values():
            types_in_matrix.update(types_list)
        
        # All 9 types should be covered
        self.assertEqual(types_in_matrix, all_types)
    
    def test_matrix_values_are_lists(self):
        """All matrix values are lists"""
        for group, types in PROFILE_CREATION_MATRIX.items():
            self.assertIsInstance(types, list, f'{group} should have list value')
    
    def test_no_empty_permissions(self):
        """No role has empty permissions"""
        for group, types in PROFILE_CREATION_MATRIX.items():
            self.assertGreater(len(types), 0, f'{group} should have at least 1 permission')


class TestUnauthorizedCreation(unittest.TestCase):
    """Test negative cases: unauthorized profile type creation"""
    
    def test_manager_creating_owner_unauthorized(self):
        """Simulate: Manager tries to create owner, should be rejected"""
        manager_group = 'quicksol_estate.group_real_estate_manager'
        allowed_types = PROFILE_CREATION_MATRIX[manager_group]
        
        requested_type = 'owner'
        is_authorized = requested_type in allowed_types
        
        self.assertFalse(is_authorized, 'Manager should not create owner')
    
    def test_agent_creating_manager_unauthorized(self):
        """Simulate: Agent tries to create manager, should be rejected"""
        agent_group = 'quicksol_estate.group_real_estate_agent'
        allowed_types = PROFILE_CREATION_MATRIX[agent_group]
        
        requested_type = 'manager'
        is_authorized = requested_type in allowed_types
        
        self.assertFalse(is_authorized, 'Agent should not create manager')
    
    def test_unknown_profile_type_rejected(self):
        """Unknown profile type should not be in any matrix"""
        unknown_type = 'super_admin'
        
        for group, allowed_types in PROFILE_CREATION_MATRIX.items():
            self.assertNotIn(unknown_type, allowed_types,
                           f'{group} should not have unknown type {unknown_type}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
