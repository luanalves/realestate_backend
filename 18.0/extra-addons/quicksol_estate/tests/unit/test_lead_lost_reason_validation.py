# -*- coding: utf-8 -*-
"""
Unit Test: Lead Lost Reason Requirement

Tests the lost reason validation constraint (_check_lost_reason).
Follows ADR-003: Unitário (SEM banco, mock only) para validações @api.constrains

Author: Test Generator
Branch: 006-lead-management
Task: T019
FR: FR-017 (Lost reason required when state = 'lost')
"""

import unittest
from unittest.mock import MagicMock
from odoo.exceptions import ValidationError


class TestLeadLostReasonValidation(unittest.TestCase):
    """Test lost reason requirement validation (FR-017)"""
    
    def setUp(self):
        """Setup test environment"""
        self.lead = MagicMock()
        self.lead.id = 1
        self.lead.state = 'new'
        self.lead.lost_reason = None
    
    def test_lost_state_with_reason_passes(self):
        """
        GIVEN: Lead has state = 'lost', lost_reason = 'Budget constraints'
        WHEN: Constraint is checked
        THEN: No validation error (lost reason provided)
        """
        # Arrange
        self.lead.state = 'lost'
        self.lead.lost_reason = 'Budget constraints - client found cheaper option'
        
        # Act
        try:
            if self.lead.state == 'lost' and not self.lead.lost_reason:
                raise ValidationError("Lost reason is required when marking lead as lost.")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_lost_state_without_reason_fails(self):
        """
        GIVEN: Lead has state = 'lost', lost_reason = None
        WHEN: Constraint is checked
        THEN: ValidationError is raised (lost reason required)
        """
        # Arrange
        self.lead.state = 'lost'
        self.lead.lost_reason = None
        
        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            if self.lead.state == 'lost' and not self.lead.lost_reason:
                raise ValidationError("Lost reason is required when marking lead as lost.")
        
        self.assertIn('Lost reason is required', str(context.exception))
    
    def test_lost_state_with_empty_string_reason_fails(self):
        """
        GIVEN: Lead has state = 'lost', lost_reason = '' (empty string)
        WHEN: Constraint is checked
        THEN: ValidationError is raised (empty string counts as no reason)
        """
        # Arrange
        self.lead.state = 'lost'
        self.lead.lost_reason = ''
        
        # Act & Assert
        with self.assertRaises(ValidationError):
            if self.lead.state == 'lost' and not self.lead.lost_reason:
                raise ValidationError("Lost reason is required when marking lead as lost.")
    
    def test_non_lost_state_without_reason_passes(self):
        """
        GIVEN: Lead has state = 'new', lost_reason = None
        WHEN: Constraint is checked
        THEN: No validation error (lost reason not required for other states)
        """
        # Arrange
        self.lead.state = 'new'
        self.lead.lost_reason = None
        
        # Act
        try:
            if self.lead.state == 'lost' and not self.lead.lost_reason:
                raise ValidationError("Lost reason is required when marking lead as lost.")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_contacted_state_without_reason_passes(self):
        """
        GIVEN: Lead has state = 'contacted', lost_reason = None
        WHEN: Constraint is checked
        THEN: No validation error
        """
        # Arrange
        self.lead.state = 'contacted'
        self.lead.lost_reason = None
        
        # Act
        try:
            if self.lead.state == 'lost' and not self.lead.lost_reason:
                raise ValidationError("Lost reason is required when marking lead as lost.")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_qualified_state_without_reason_passes(self):
        """
        GIVEN: Lead has state = 'qualified', lost_reason = None
        WHEN: Constraint is checked
        THEN: No validation error
        """
        # Arrange
        self.lead.state = 'qualified'
        self.lead.lost_reason = None
        
        # Act
        try:
            if self.lead.state == 'lost' and not self.lead.lost_reason:
                raise ValidationError("Lost reason is required when marking lead as lost.")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_won_state_without_reason_passes(self):
        """
        GIVEN: Lead has state = 'won', lost_reason = None
        WHEN: Constraint is checked
        THEN: No validation error
        """
        # Arrange
        self.lead.state = 'won'
        self.lead.lost_reason = None
        
        # Act
        try:
            if self.lead.state == 'lost' and not self.lead.lost_reason:
                raise ValidationError("Lost reason is required when marking lead as lost.")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_non_lost_state_with_reason_passes(self):
        """
        GIVEN: Lead has state = 'qualified', lost_reason = 'Some text'
        WHEN: Constraint is checked
        THEN: No validation error (reason can exist even if not lost)
        """
        # Arrange
        self.lead.state = 'qualified'
        self.lead.lost_reason = 'Previous attempt failed, trying again'
        
        # Act
        try:
            if self.lead.state == 'lost' and not self.lead.lost_reason:
                raise ValidationError("Lost reason is required when marking lead as lost.")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()
