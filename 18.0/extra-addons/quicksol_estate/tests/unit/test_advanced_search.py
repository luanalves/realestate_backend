# -*- coding: utf-8 -*-
"""
Unit tests for Advanced Search (Phase 6)

Tests budget filtering, location search, property type filtering, and sorting.

Author: Quicksol Technologies
Date: 2026-01-30
Branch: 006-lead-management
FRs: FR-039 to FR-047 (Advanced search and filtering)
"""

import unittest
from datetime import datetime, timedelta
from odoo.tests import common


class TestAdvancedSearch(common.TransactionCase):
    """Test advanced search and filtering functionality"""
    
    def setUp(self):
        """Set up test data"""
        super(TestAdvancedSearch, self).setUp()
        
        # Get models
        self.Lead = self.env['real.estate.lead']
        self.User = self.env['res.users']
        self.Company = self.env['res.company']
        self.PropertyType = self.env['real.estate.property.type']
        
        # Create test company
        self.company = self.Company.create({
            'name': 'Test Real Estate Company'
        })
        
        # Create test agent
        self.agent = self.User.create({
            'name': 'Test Agent',
            'login': 'agent@example.com',
            'email': 'agent@example.com',
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])]
        })
        
        # Create property type
        self.apt_type = self.PropertyType.create({
            'name': 'Apartment'
        })
        
        # Create test leads with varying budgets
        self.lead_low = self.Lead.with_user(self.agent).create({
            'name': 'Low Budget Lead',
            'agent_id': self.agent.id,
            'company_ids': [(6, 0, [self.company.id])],
            'budget_min': 100000,
            'budget_max': 200000,
            'location_preference': 'Centro',
            'bedrooms_needed': 2
        })
        
        self.lead_mid = self.Lead.with_user(self.agent).create({
            'name': 'Mid Budget Lead',
            'agent_id': self.agent.id,
            'company_ids': [(6, 0, [self.company.id])],
            'budget_min': 300000,
            'budget_max': 400000,
            'location_preference': 'Centro',
            'bedrooms_needed': 3,
            'property_type_interest': self.apt_type.id
        })
        
        self.lead_high = self.Lead.with_user(self.agent).create({
            'name': 'High Budget Lead',
            'agent_id': self.agent.id,
            'company_ids': [(6, 0, [self.company.id])],
            'budget_min': 500000,
            'budget_max': 800000,
            'location_preference': 'Vila Olímpia',
            'bedrooms_needed': 3,
            'property_type_interest': self.apt_type.id
        })
    
    def test_budget_min_filter(self):
        """Test filtering by minimum budget (FR-039)"""
        # Find leads with budget_max >= 250000
        domain = [('budget_max', '>=', 250000)]
        results = self.Lead.search(domain)
        
        # Should return mid and high budget leads
        self.assertIn(self.lead_mid.id, results.ids)
        self.assertIn(self.lead_high.id, results.ids)
        self.assertNotIn(self.lead_low.id, results.ids)
    
    def test_budget_max_filter(self):
        """Test filtering by maximum budget (FR-040)"""
        # Find leads with budget_min <= 350000
        domain = [('budget_min', '<=', 350000)]
        results = self.Lead.search(domain)
        
        # Should return low and mid budget leads
        self.assertIn(self.lead_low.id, results.ids)
        self.assertIn(self.lead_mid.id, results.ids)
        self.assertNotIn(self.lead_high.id, results.ids)
    
    def test_budget_range_filter(self):
        """Test filtering by budget range (both min and max)"""
        # Find leads in 250k-450k range
        domain = [
            ('budget_max', '>=', 250000),
            ('budget_min', '<=', 450000)
        ]
        results = self.Lead.search(domain)
        
        # Should only return mid budget lead
        self.assertIn(self.lead_mid.id, results.ids)
        self.assertNotIn(self.lead_low.id, results.ids)
        self.assertNotIn(self.lead_high.id, results.ids)
    
    def test_bedrooms_filter(self):
        """Test filtering by number of bedrooms (FR-041)"""
        domain = [('bedrooms_needed', '=', 3)]
        results = self.Lead.search(domain)
        
        # Should return mid and high budget leads (both have 3 bedrooms)
        self.assertIn(self.lead_mid.id, results.ids)
        self.assertIn(self.lead_high.id, results.ids)
        self.assertNotIn(self.lead_low.id, results.ids)
    
    def test_property_type_filter(self):
        """Test filtering by property type (FR-042)"""
        domain = [('property_type_interest', '=', self.apt_type.id)]
        results = self.Lead.search(domain)
        
        # Should return mid and high budget leads (both interested in apartments)
        self.assertIn(self.lead_mid.id, results.ids)
        self.assertIn(self.lead_high.id, results.ids)
        self.assertNotIn(self.lead_low.id, results.ids)
    
    def test_location_filter(self):
        """Test filtering by location preference (FR-043)"""
        domain = [('location_preference', 'ilike', 'Centro')]
        results = self.Lead.search(domain)
        
        # Should return low and mid budget leads (Centro location)
        self.assertIn(self.lead_low.id, results.ids)
        self.assertIn(self.lead_mid.id, results.ids)
        self.assertNotIn(self.lead_high.id, results.ids)
    
    def test_combined_filters(self):
        """Test combining multiple filters with AND logic"""
        # Find Centro leads with 3 bedrooms
        domain = [
            ('location_preference', 'ilike', 'Centro'),
            ('bedrooms_needed', '=', 3)
        ]
        results = self.Lead.search(domain)
        
        # Should only return mid budget lead
        self.assertEqual(len(results), 1)
        self.assertEqual(results.id, self.lead_mid.id)
    
    def test_sorting_by_budget(self):
        """Test sorting results by budget (FR-044)"""
        # Sort by budget_max ascending
        results_asc = self.Lead.search([], order='budget_max asc')
        
        # Low should be first, high should be last
        indices = [results_asc.ids.index(lead.id) for lead in [self.lead_low, self.lead_mid, self.lead_high]]
        self.assertTrue(indices[0] < indices[1] < indices[2])
        
        # Sort by budget_max descending
        results_desc = self.Lead.search([], order='budget_max desc')
        
        # High should be first, low should be last
        indices_desc = [results_desc.ids.index(lead.id) for lead in [self.lead_high, self.lead_mid, self.lead_low]]
        self.assertTrue(indices_desc[0] < indices_desc[1] < indices_desc[2])
    
    def test_sorting_by_create_date(self):
        """Test default sorting by create_date"""
        results = self.Lead.search([], order='create_date desc')
        
        # Most recent should be first
        self.assertEqual(results[0].id, self.lead_high.id)
    
    def test_empty_results(self):
        """Test that filters returning no results work correctly"""
        # Search for impossible budget range
        domain = [
            ('budget_min', '>', 1000000),
            ('budget_max', '<', 100000)
        ]
        results = self.Lead.search(domain)
        
        self.assertEqual(len(results), 0)
    
    def test_partial_location_match(self):
        """Test that location search supports partial matches"""
        # Search for "Vila" should match "Vila Olímpia"
        domain = [('location_preference', 'ilike', 'Vila')]
        results = self.Lead.search(domain)
        
        self.assertIn(self.lead_high.id, results.ids)
        self.assertNotIn(self.lead_low.id, results.ids)
        self.assertNotIn(self.lead_mid.id, results.ids)


if __name__ == '__main__':
    unittest.main()
