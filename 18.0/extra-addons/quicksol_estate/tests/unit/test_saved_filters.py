# -*- coding: utf-8 -*-
"""
Unit tests for Saved Filters (Phase 6)

Tests saved filter creation, listing, deletion, and application.

Author: Quicksol Technologies
Date: 2026-01-30
Branch: 006-lead-management
FRs: FR-048 (Saved search filters)
"""

import unittest
import json
from odoo.tests import common
from odoo.exceptions import ValidationError


class TestSavedFilters(common.TransactionCase):
    """Test saved search filter functionality"""
    
    def setUp(self):
        """Set up test data"""
        super(TestSavedFilters, self).setUp()
        
        # Get models
        self.Filter = self.env['real.estate.lead.filter']
        self.User = self.env['res.users']
        self.Company = self.env['res.company']
        
        # Create test company
        self.company = self.Company.create({
            'name': 'Test Real Estate Company'
        })
        
        # Create test users
        self.user1 = self.User.create({
            'name': 'User One',
            'login': 'user1@example.com',
            'email': 'user1@example.com',
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])]
        })
        
        self.user2 = self.User.create({
            'name': 'User Two',
            'login': 'user2@example.com',
            'email': 'user2@example.com',
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])]
        })
    
    def test_create_saved_filter(self):
        """Test creating a saved filter (T148)"""
        filter_params = {
            'state': 'qualified',
            'budget_min': 300000,
            'budget_max': 500000,
            'bedrooms': 3,
            'location': 'Centro'
        }
        
        saved_filter = self.Filter.with_user(self.user1).create({
            'name': 'High-value Centro leads',
            'user_id': self.user1.id,
            'filter_domain': json.dumps(filter_params)
        })
        
        self.assertTrue(saved_filter, "Saved filter should be created")
        self.assertEqual(saved_filter.name, 'High-value Centro leads')
        self.assertEqual(saved_filter.user_id.id, self.user1.id)
        self.assertFalse(saved_filter.is_shared)
    
    def test_filter_domain_validation(self):
        """Test that invalid JSON in filter_domain raises error"""
        with self.assertRaises(ValidationError):
            self.Filter.create({
                'name': 'Invalid Filter',
                'user_id': self.user1.id,
                'filter_domain': 'not valid json'
            })
    
    def test_unique_name_per_user(self):
        """Test that filter names must be unique per user"""
        filter_params = json.dumps({'state': 'new'})
        
        # Create first filter
        self.Filter.create({
            'name': 'My Filter',
            'user_id': self.user1.id,
            'filter_domain': filter_params
        })
        
        # Try to create duplicate for same user
        with self.assertRaises(ValidationError):
            self.Filter.create({
                'name': 'My Filter',
                'user_id': self.user1.id,
                'filter_domain': filter_params
            })
    
    def test_same_name_different_users(self):
        """Test that different users can have filters with same name"""
        filter_params = json.dumps({'state': 'contacted'})
        
        # User1 creates filter
        filter1 = self.Filter.create({
            'name': 'My Leads',
            'user_id': self.user1.id,
            'filter_domain': filter_params
        })
        
        # User2 creates filter with same name - should succeed
        filter2 = self.Filter.create({
            'name': 'My Leads',
            'user_id': self.user2.id,
            'filter_domain': filter_params
        })
        
        self.assertNotEqual(filter1.id, filter2.id)
        self.assertEqual(filter1.name, filter2.name)
    
    def test_shared_filter(self):
        """Test creating and sharing filters"""
        filter_params = json.dumps({'state': 'won'})
        
        shared_filter = self.Filter.create({
            'name': 'Team Filter',
            'user_id': self.user1.id,
            'filter_domain': filter_params,
            'is_shared': True
        })
        
        self.assertTrue(shared_filter.is_shared)
    
    def test_get_filter_params(self):
        """Test parsing filter parameters from JSON"""
        filter_params = {
            'state': 'qualified',
            'budget_min': 200000,
            'location': 'São Paulo'
        }
        
        saved_filter = self.Filter.create({
            'name': 'SP Qualified',
            'user_id': self.user1.id,
            'filter_domain': json.dumps(filter_params)
        })
        
        parsed_params = saved_filter.get_filter_params()
        
        self.assertEqual(parsed_params['state'], 'qualified')
        self.assertEqual(parsed_params['budget_min'], 200000)
        self.assertEqual(parsed_params['location'], 'São Paulo')
    
    def test_filter_deletion(self):
        """Test deleting saved filter"""
        saved_filter = self.Filter.create({
            'name': 'Temporary Filter',
            'user_id': self.user1.id,
            'filter_domain': json.dumps({'state': 'new'})
        })
        
        filter_id = saved_filter.id
        saved_filter.unlink()
        
        # Verify filter is deleted
        deleted_filter = self.Filter.browse(filter_id)
        self.assertFalse(deleted_filter.exists())
    
    def test_multiple_filters_per_user(self):
        """Test that users can create multiple filters"""
        filter1 = self.Filter.create({
            'name': 'New Leads',
            'user_id': self.user1.id,
            'filter_domain': json.dumps({'state': 'new'})
        })
        
        filter2 = self.Filter.create({
            'name': 'Qualified Leads',
            'user_id': self.user1.id,
            'filter_domain': json.dumps({'state': 'qualified'})
        })
        
        filter3 = self.Filter.create({
            'name': 'High Budget',
            'user_id': self.user1.id,
            'filter_domain': json.dumps({'budget_min': 500000})
        })
        
        # Count user1's filters
        user_filters = self.Filter.search([('user_id', '=', self.user1.id)])
        self.assertEqual(len(user_filters), 3)
    
    def test_apply_filter_action(self):
        """Test applying a saved filter returns correct action"""
        filter_params = {
            'state': 'qualified',
            'budget_min': 300000
        }
        
        saved_filter = self.Filter.create({
            'name': 'Qualified High Value',
            'user_id': self.user1.id,
            'filter_domain': json.dumps(filter_params)
        })
        
        action = saved_filter.apply_filter()
        
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'real.estate.lead')
        self.assertIn(('state', '=', 'qualified'), action['domain'])
        self.assertIn(('budget_max', '>=', 300000), action['domain'])


if __name__ == '__main__':
    unittest.main()
