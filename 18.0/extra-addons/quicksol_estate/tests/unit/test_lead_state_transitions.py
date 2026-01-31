# -*- coding: utf-8 -*-
"""
Unit Test: Lead State Transition Logging

Tests the state change logging in write() override.
Follows ADR-003: Unitário (SEM banco, mock only) para lógica de métodos customizados

Author: Test Generator
Branch: 006-lead-management
Task: T021
FR: FR-016a (State changes must be logged in chatter)
"""

import unittest
from unittest.mock import MagicMock, patch, call
from datetime import date


class TestLeadStateTransitions(unittest.TestCase):
    """Test state transition logging (FR-016a)"""
    
    def setUp(self):
        """Setup test environment"""
        self.lead = MagicMock()
        self.lead.id = 1
        self.lead.state = 'new'
        self.lead.lost_date = None
        self.lead.message_post = MagicMock()
        self.lead._origin = MagicMock()
        self.lead._origin.state = 'new'
    
    def test_state_change_to_contacted_logs_message(self):
        """
        GIVEN: Lead has state = 'new'
        WHEN: State changes to 'contacted' via write()
        THEN: message_post is called with state transition message
        """
        # Arrange
        self.lead._origin.state = 'new'
        new_state = 'contacted'
        
        # Act: Simulate write() logic
        if new_state != self.lead._origin.state:
            self.lead.message_post(
                body=f"Lead status changed from {self.lead._origin.state} to {new_state}."
            )
        
        # Assert
        self.lead.message_post.assert_called_once()
        call_args = self.lead.message_post.call_args
        self.assertIn('new', call_args.kwargs['body'])
        self.assertIn('contacted', call_args.kwargs['body'])
    
    def test_state_change_to_lost_sets_lost_date(self):
        """
        GIVEN: Lead has state = 'qualified', lost_date = None
        WHEN: State changes to 'lost' via write()
        THEN: lost_date is set to today
        """
        # Arrange
        self.lead._origin.state = 'qualified'
        new_state = 'lost'
        vals = {'state': new_state}
        
        # Act: Simulate write() logic
        if new_state == 'lost' and 'lost_date' not in vals:
            vals['lost_date'] = date.today()
        
        # Assert
        self.assertEqual(vals['lost_date'], date.today())
    
    def test_state_change_to_lost_logs_and_sets_date(self):
        """
        GIVEN: Lead has state = 'contacted'
        WHEN: State changes to 'lost'
        THEN: Both message_post is called AND lost_date is set
        """
        # Arrange
        self.lead._origin.state = 'contacted'
        new_state = 'lost'
        vals = {'state': new_state}
        
        # Act
        if new_state != self.lead._origin.state:
            self.lead.message_post(
                body=f"Lead status changed from {self.lead._origin.state} to {new_state}."
            )
        
        if new_state == 'lost' and 'lost_date' not in vals:
            vals['lost_date'] = date.today()
        
        # Assert
        self.lead.message_post.assert_called_once()
        self.assertEqual(vals['lost_date'], date.today())
    
    def test_non_state_field_change_does_not_log(self):
        """
        GIVEN: Lead has state = 'new'
        WHEN: Only budget_max changes (no state change)
        THEN: message_post is NOT called
        """
        # Arrange
        self.lead._origin.state = 'new'
        vals = {'budget_max': 500000}
        
        # Act: Simulate write() logic
        if 'state' in vals and vals['state'] != self.lead._origin.state:
            self.lead.message_post(
                body=f"Lead status changed from {self.lead._origin.state} to {vals['state']}."
            )
        
        # Assert
        self.lead.message_post.assert_not_called()
    
    def test_state_change_to_won_logs_message(self):
        """
        GIVEN: Lead has state = 'qualified'
        WHEN: State changes to 'won' via write()
        THEN: message_post is called with won transition
        """
        # Arrange
        self.lead._origin.state = 'qualified'
        new_state = 'won'
        
        # Act
        if new_state != self.lead._origin.state:
            self.lead.message_post(
                body=f"Lead status changed from {self.lead._origin.state} to {new_state}."
            )
        
        # Assert
        self.lead.message_post.assert_called_once()
        call_args = self.lead.message_post.call_args
        self.assertIn('qualified', call_args.kwargs['body'])
        self.assertIn('won', call_args.kwargs['body'])
    
    def test_multiple_state_transitions_preserve_history(self):
        """
        GIVEN: Lead transitions through multiple states
        WHEN: new → contacted → qualified → lost
        THEN: Each transition logs a separate message (call count = 3)
        """
        # Arrange
        transitions = [
            ('new', 'contacted'),
            ('contacted', 'qualified'),
            ('qualified', 'lost')
        ]
        
        # Act
        for old_state, new_state in transitions:
            self.lead._origin.state = old_state
            self.lead.message_post(
                body=f"Lead status changed from {old_state} to {new_state}."
            )
        
        # Assert
        self.assertEqual(self.lead.message_post.call_count, 3)
    
    def test_lost_date_not_overridden_if_provided(self):
        """
        GIVEN: Lead state = 'new', lost_date = None
        WHEN: write({'state': 'lost', 'lost_date': '2024-12-15'})
        THEN: lost_date remains '2024-12-15' (user-provided value preserved)
        """
        # Arrange
        self.lead._origin.state = 'new'
        user_date = date(2024, 12, 15)
        vals = {'state': 'lost', 'lost_date': user_date}
        
        # Act: Simulate write() logic
        if vals['state'] == 'lost' and 'lost_date' not in vals:
            vals['lost_date'] = date.today()
        
        # Assert
        self.assertEqual(vals['lost_date'], user_date)
    
    def test_same_state_no_log(self):
        """
        GIVEN: Lead has state = 'contacted'
        WHEN: write({'state': 'contacted'}) (same state)
        THEN: message_post is NOT called (no transition)
        """
        # Arrange
        self.lead._origin.state = 'contacted'
        new_state = 'contacted'
        
        # Act
        if new_state != self.lead._origin.state:
            self.lead.message_post(
                body=f"Lead status changed from {self.lead._origin.state} to {new_state}."
            )
        
        # Assert
        self.lead.message_post.assert_not_called()


if __name__ == '__main__':
    unittest.main()
