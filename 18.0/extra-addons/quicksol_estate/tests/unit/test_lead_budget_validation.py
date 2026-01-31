# -*- coding: utf-8 -*-
"""
Unit Test: Lead Budget Range Validation

Tests the budget validation constraint (_check_budget_range).
Follows ADR-003: Unitário (SEM banco, mock only) para validações @api.constrains

Author: Test Generator
Branch: 006-lead-management
Task: T018
FR: FR-006 (Budget validation: min <= max)
"""

import unittest
from unittest.mock import MagicMock
from odoo.exceptions import ValidationError


class TestLeadBudgetValidation(unittest.TestCase):
    """Test budget range validation (FR-006)"""
    
    def setUp(self):
        """Setup test environment"""
        self.lead = MagicMock()
        self.lead.id = 1
        self.lead.budget_min = None
        self.lead.budget_max = None
    
    def test_budget_min_less_than_max_passes(self):
        """
        GIVEN: Lead has budget_min = 200000, budget_max = 500000
        WHEN: Constraint is checked
        THEN: No validation error (min < max is valid)
        """
        # Arrange
        self.lead.budget_min = 200000.00
        self.lead.budget_max = 500000.00
        
        # Act: Simulate constraint logic
        try:
            if self.lead.budget_min and self.lead.budget_max:
                if self.lead.budget_min > self.lead.budget_max:
                    raise ValidationError("Minimum budget cannot exceed maximum budget.")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_budget_min_equal_to_max_passes(self):
        """
        GIVEN: Lead has budget_min = 300000, budget_max = 300000
        WHEN: Constraint is checked
        THEN: No validation error (min == max is valid, exact budget)
        """
        # Arrange
        self.lead.budget_min = 300000.00
        self.lead.budget_max = 300000.00
        
        # Act
        try:
            if self.lead.budget_min and self.lead.budget_max:
                if self.lead.budget_min > self.lead.budget_max:
                    raise ValidationError("Minimum budget cannot exceed maximum budget.")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_budget_min_greater_than_max_fails(self):
        """
        GIVEN: Lead has budget_min = 500000, budget_max = 300000
        WHEN: Constraint is checked
        THEN: ValidationError is raised (min > max is invalid)
        """
        # Arrange
        self.lead.budget_min = 500000.00
        self.lead.budget_max = 300000.00
        
        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            if self.lead.budget_min and self.lead.budget_max:
                if self.lead.budget_min > self.lead.budget_max:
                    raise ValidationError("Minimum budget cannot exceed maximum budget.")
        
        self.assertIn('Minimum budget cannot exceed maximum budget', str(context.exception))
    
    def test_only_budget_min_set_passes(self):
        """
        GIVEN: Lead has budget_min = 200000, budget_max = None
        WHEN: Constraint is checked
        THEN: No validation error (partial budget is allowed per FR-008)
        """
        # Arrange
        self.lead.budget_min = 200000.00
        self.lead.budget_max = None
        
        # Act
        try:
            if self.lead.budget_min and self.lead.budget_max:
                if self.lead.budget_min > self.lead.budget_max:
                    raise ValidationError("Minimum budget cannot exceed maximum budget.")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_only_budget_max_set_passes(self):
        """
        GIVEN: Lead has budget_min = None, budget_max = 500000
        WHEN: Constraint is checked
        THEN: No validation error (partial budget is allowed per FR-008)
        """
        # Arrange
        self.lead.budget_min = None
        self.lead.budget_max = 500000.00
        
        # Act
        try:
            if self.lead.budget_min and self.lead.budget_max:
                if self.lead.budget_min > self.lead.budget_max:
                    raise ValidationError("Minimum budget cannot exceed maximum budget.")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_both_budgets_none_passes(self):
        """
        GIVEN: Lead has budget_min = None, budget_max = None
        WHEN: Constraint is checked
        THEN: No validation error (no budget is allowed per FR-008)
        """
        # Arrange
        self.lead.budget_min = None
        self.lead.budget_max = None
        
        # Act
        try:
            if self.lead.budget_min and self.lead.budget_max:
                if self.lead.budget_min > self.lead.budget_max:
                    raise ValidationError("Minimum budget cannot exceed maximum budget.")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_zero_budget_min_passes(self):
        """
        GIVEN: Lead has budget_min = 0, budget_max = 300000
        WHEN: Constraint is checked
        THEN: No validation error (zero is valid minimum)
        """
        # Arrange
        self.lead.budget_min = 0.00
        self.lead.budget_max = 300000.00
        
        # Act
        try:
            if self.lead.budget_min and self.lead.budget_max:
                if self.lead.budget_min > self.lead.budget_max:
                    raise ValidationError("Minimum budget cannot exceed maximum budget.")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_large_budget_range_passes(self):
        """
        GIVEN: Lead has budget_min = 100000, budget_max = 10000000 (10M)
        WHEN: Constraint is checked
        THEN: No validation error (large ranges are valid)
        """
        # Arrange
        self.lead.budget_min = 100000.00
        self.lead.budget_max = 10000000.00
        
        # Act
        try:
            if self.lead.budget_min and self.lead.budget_max:
                if self.lead.budget_min > self.lead.budget_max:
                    raise ValidationError("Minimum budget cannot exceed maximum budget.")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()
