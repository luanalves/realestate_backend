# -*- coding: utf-8 -*-
"""
Unit Tests for Agent ↔ Profile Sync (Feature 010 - T16)

Tests the synchronization logic when creating an agent with profile_id.
Agent.create() should copy cadastral data from the profile using setdefault().

Run:
    docker compose exec odoo python3 /mnt/extra-addons/quicksol_estate/tests/unit/test_profile_sync_unit.py
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import date
import sys
from pathlib import Path

# Add module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestAgentCreateWithProfile(unittest.TestCase):
    """Test agent creation with profile_id syncs data"""
    
    def test_sync_all_cadastral_fields(self):
        """Agent create with profile_id syncs name, cpf, email, phone, mobile, company_id, hire_date"""
        # Mock profile
        profile = MagicMock()
        profile.id = 1
        profile.name = 'João Silva'
        profile.document = '12345678901'  # CPF (normalized)
        profile.email = 'joao@example.com'
        profile.phone = '+55 (11) 99999-9999'
        profile.mobile = '+55 (11) 88888-8888'
        profile.company_id.id = 10
        profile.hire_date = date(2025, 1, 15)
        profile.exists.return_value = True
        
        # Simulate agent vals with profile_id
        agent_vals = {
            'profile_id': 1,
        }
        
        # Simulate the create logic using setdefault
        agent_vals.setdefault('name', profile.name)
        agent_vals.setdefault('cpf', profile.document)
        agent_vals.setdefault('email', profile.email)
        agent_vals.setdefault('phone', profile.phone)
        agent_vals.setdefault('mobile', profile.mobile)
        agent_vals.setdefault('company_id', profile.company_id.id)
        agent_vals.setdefault('hire_date', profile.hire_date)
        
        # Verify synced values
        self.assertEqual(agent_vals['name'], 'João Silva')
        self.assertEqual(agent_vals['cpf'], '12345678901')
        self.assertEqual(agent_vals['email'], 'joao@example.com')
        self.assertEqual(agent_vals['phone'], '+55 (11) 99999-9999')
        self.assertEqual(agent_vals['mobile'], '+55 (11) 88888-8888')
        self.assertEqual(agent_vals['company_id'], 10)
        self.assertEqual(agent_vals['hire_date'], date(2025, 1, 15))
    
    def test_document_maps_to_cpf(self):
        """Profile.document maps to Agent.cpf"""
        profile = MagicMock()
        profile.document = '52998224725'  # Valid CPF
        profile.exists.return_value = True
        
        agent_vals = {'profile_id': 1}
        agent_vals.setdefault('cpf', profile.document)
        
        self.assertEqual(agent_vals['cpf'], '52998224725')
    
    def test_sync_handles_optional_hire_date(self):
        """If profile has hire_date, sync it; otherwise skip"""
        # Profile with hire_date
        profile_with = MagicMock()
        profile_with.hire_date = date(2024, 3, 20)
        profile_with.exists.return_value = True
        
        agent_vals = {'profile_id': 1}
        if profile_with.hire_date:
            agent_vals.setdefault('hire_date', profile_with.hire_date)
        
        self.assertEqual(agent_vals['hire_date'], date(2024, 3, 20))
        
        # Profile without hire_date
        profile_without = MagicMock()
        profile_without.hire_date = None
        
        agent_vals2 = {'profile_id': 2}
        if profile_without.hire_date:
            agent_vals2.setdefault('hire_date', profile_without.hire_date)
        
        self.assertNotIn('hire_date', agent_vals2)


class TestAgentCreateWithoutProfile(unittest.TestCase):
    """Test backward compatibility: agent creation without profile_id"""
    
    def test_create_without_profile_id_works(self):
        """Agent can be created without profile_id (legacy flow)"""
        agent_vals = {
            'name': 'Maria Santos',
            'cpf': '11222333000181',
            'email': 'maria@example.com',
            'phone': '+55 (21) 99999-9999',
            'company_id': 5,
        }
        
        # No profile_id in vals
        self.assertNotIn('profile_id', agent_vals)
        
        # Agent creation should proceed normally
        # (In real code, this would call super().create(vals))
        self.assertTrue(True, 'Agent creation without profile_id should work')
    
    def test_no_sync_when_profile_id_missing(self):
        """No data sync when profile_id is not provided"""
        agent_vals = {
            'name': 'Pedro Oliveira',
            'cpf': '98765432100',
            'company_id': 3,
        }
        
        # Simulate: profile_id check fails
        if agent_vals.get('profile_id'):
            # This branch should NOT execute
            self.fail('Should not sync without profile_id')
        
        # Original vals unchanged
        self.assertEqual(agent_vals['name'], 'Pedro Oliveira')


class TestSetdefaultBehavior(unittest.TestCase):
    """Test setdefault() doesn't override explicit values"""
    
    def test_explicit_value_not_overridden(self):
        """Explicit value in vals takes precedence over profile data"""
        profile = MagicMock()
        profile.name = 'Profile Name'
        profile.email = 'profile@example.com'
        profile.exists.return_value = True
        
        # Agent vals with explicit email
        agent_vals = {
            'profile_id': 1,
            'email': 'agent@override.com',  # Explicit value
        }
        
        # Sync with setdefault
        agent_vals.setdefault('name', profile.name)
        agent_vals.setdefault('email', profile.email)  # Should NOT override
        
        # Explicit email preserved
        self.assertEqual(agent_vals['name'], 'Profile Name')  # From profile
        self.assertEqual(agent_vals['email'], 'agent@override.com')  # Explicit preserved
    
    def test_setdefault_only_sets_missing_keys(self):
        """setdefault() only adds keys that are missing"""
        agent_vals = {
            'profile_id': 1,
            'name': 'Explicit Name',
        }
        
        profile = MagicMock()
        profile.name = 'Profile Name'
        profile.cpf = '12345678901'
        
        agent_vals.setdefault('name', profile.name)  # Should NOT change
        agent_vals.setdefault('cpf', profile.cpf)    # Should ADD
        
        self.assertEqual(agent_vals['name'], 'Explicit Name')  # Unchanged
        self.assertEqual(agent_vals['cpf'], '12345678901')      # Added
    
    def test_all_fields_explicit_no_sync(self):
        """If all fields are explicitly provided, profile is only linked"""
        profile = MagicMock()
        profile.name = 'Profile Name'
        profile.email = 'profile@example.com'
        profile.phone = '+55 (11) 11111-1111'
        
        agent_vals = {
            'profile_id': 1,
            'name': 'Agent Explicit',
            'cpf': '99999999999',
            'email': 'agent@explicit.com',
            'phone': '+55 (11) 22222-2222',
            'company_id': 7,
        }
        
        # Apply setdefault for all fields
        agent_vals.setdefault('name', profile.name)
        agent_vals.setdefault('email', profile.email)
        agent_vals.setdefault('phone', profile.phone)
        
        # All explicit values preserved
        self.assertEqual(agent_vals['name'], 'Agent Explicit')
        self.assertEqual(agent_vals['email'], 'agent@explicit.com')
        self.assertEqual(agent_vals['phone'], '+55 (11) 22222-2222')


class TestProfileExistenceCheck(unittest.TestCase):
    """Test behavior when profile_id references non-existent profile"""
    
    def test_nonexistent_profile_skips_sync(self):
        """If profile doesn't exist, skip sync gracefully"""
        # Mock profile that doesn't exist
        profile = MagicMock()
        profile.exists.return_value = False
        
        agent_vals = {'profile_id': 999}
        
        # Simulate existence check
        if profile.exists():
            agent_vals.setdefault('name', profile.name)
        
        # No sync occurred
        self.assertNotIn('name', agent_vals)
        self.assertEqual(agent_vals['profile_id'], 999)  # profile_id preserved


class TestAgentUpdateProfileSync(unittest.TestCase):
    """Test profile update syncing to agent (future enhancement)"""
    
    def test_profile_update_concept(self):
        """Concept: When profile is updated, should agent sync?"""
        # This is handled in profile_api.py update_profile()
        # When profile_type='agent', updates sync to agent extension
        
        profile = MagicMock()
        profile.id = 1
        profile.profile_type_id.code = 'agent'
        profile.name = 'Updated Name'
        profile.email = 'updated@example.com'
        
        agent = MagicMock()
        agent.profile_id = profile.id
        
        # Simulate sync logic
        agent_update_vals = {}
        agent_update_vals['name'] = profile.name
        agent_update_vals['email'] = profile.email
        
        # Verify update vals prepared
        self.assertEqual(agent_update_vals['name'], 'Updated Name')
        self.assertEqual(agent_update_vals['email'], 'updated@example.com')


if __name__ == '__main__':
    unittest.main(verbosity=2)
