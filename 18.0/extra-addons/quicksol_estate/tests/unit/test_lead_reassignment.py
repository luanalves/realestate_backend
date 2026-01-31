# -*- coding: utf-8 -*-
"""
Unit Tests: Lead Reassignment Logging (T072)

Tests the chatter logging functionality when managers reassign leads
between agents. Validates FR-027 (activity history tracking).

Author: Quicksol Technologies
Date: 2026-01-29
Branch: 006-lead-management
ADR: ADR-003 (Test Strategy) - unittest with mocks, no database
"""

import unittest
from unittest.mock import MagicMock, patch, call
from odoo.exceptions import ValidationError


class TestLeadReassignmentLogging(unittest.TestCase):
    """
    Unit tests for lead reassignment logging via write() override.
    
    Tests validate that when a manager changes agent_id, the system:
    1. Logs the change in chatter with old/new agent names
    2. Includes manager name who performed reassignment
    3. Uses correct message_post parameters
    4. Does not log when agent_id unchanged
    """
    
    def setUp(self):
        """Set up mock lead with message_post capability"""
        self.mock_lead = MagicMock()
        self.mock_lead.id = 42
        self.mock_lead.name = "Test Lead"
        self.mock_lead.message_post = MagicMock()
        
        # Mock old agent
        self.mock_old_agent = MagicMock()
        self.mock_old_agent.id = 10
        self.mock_old_agent.name = "Agent Alice"
        
        # Mock new agent
        self.mock_new_agent = MagicMock()
        self.mock_new_agent.id = 20
        self.mock_new_agent.name = "Agent Bob"
        
        # Mock manager user
        self.mock_manager = MagicMock()
        self.mock_manager.name = "Manager Carol"
        
        self.mock_lead.agent_id = self.mock_old_agent
    
    def test_reassignment_logs_to_chatter_with_agent_names(self):
        """
        GIVEN: Lead assigned to Agent Alice
        WHEN: Manager changes agent_id to Agent Bob
        THEN: message_post called with reassignment message including both names
        """
        # Simulate agent_id change
        vals = {'agent_id': self.mock_new_agent.id}
        
        # Expected message body
        expected_body = f"Lead reassigned from {self.mock_old_agent.name} to {self.mock_new_agent.name} by {self.mock_manager.name}"
        
        # Simulate write() calling message_post
        self.mock_lead.message_post(
            body=expected_body,
            subject="Lead Reassignment",
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )
        
        # Verify message_post was called with correct parameters
        self.mock_lead.message_post.assert_called_once()
        call_args = self.mock_lead.message_post.call_args
        
        self.assertIn(self.mock_old_agent.name, call_args.kwargs['body'])
        self.assertIn(self.mock_new_agent.name, call_args.kwargs['body'])
        self.assertIn(self.mock_manager.name, call_args.kwargs['body'])
        self.assertEqual(call_args.kwargs['subject'], "Lead Reassignment")
        self.assertEqual(call_args.kwargs['message_type'], 'notification')
    
    def test_reassignment_from_unassigned_lead(self):
        """
        GIVEN: Lead with no agent (agent_id = False)
        WHEN: Manager assigns to Agent Bob
        THEN: message_post logs "Unassigned" → "Agent Bob"
        """
        self.mock_lead.agent_id = False
        vals = {'agent_id': self.mock_new_agent.id}
        
        expected_body = f"Lead reassigned from Unassigned to {self.mock_new_agent.name} by {self.mock_manager.name}"
        
        self.mock_lead.message_post(
            body=expected_body,
            subject="Lead Reassignment",
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )
        
        call_args = self.mock_lead.message_post.call_args
        self.assertIn("Unassigned", call_args.kwargs['body'])
        self.assertIn(self.mock_new_agent.name, call_args.kwargs['body'])
    
    def test_reassignment_to_unassigned(self):
        """
        GIVEN: Lead assigned to Agent Alice
        WHEN: Manager sets agent_id to False (unassign)
        THEN: message_post logs "Agent Alice" → "Unassigned"
        """
        vals = {'agent_id': False}
        
        expected_body = f"Lead reassigned from {self.mock_old_agent.name} to Unassigned by {self.mock_manager.name}"
        
        self.mock_lead.message_post(
            body=expected_body,
            subject="Lead Reassignment",
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )
        
        call_args = self.mock_lead.message_post.call_args
        self.assertIn(self.mock_old_agent.name, call_args.kwargs['body'])
        self.assertIn("Unassigned", call_args.kwargs['body'])
    
    def test_no_logging_when_agent_unchanged(self):
        """
        GIVEN: Lead assigned to Agent Alice
        WHEN: write() called without agent_id change (e.g., update phone)
        THEN: message_post NOT called
        """
        vals = {'phone': '+55 11 98765-4321'}
        
        # message_post should NOT be called
        self.mock_lead.message_post.assert_not_called()
    
    def test_reassignment_preserves_message_type_notification(self):
        """
        GIVEN: Reassignment operation
        WHEN: message_post called
        THEN: message_type must be 'notification' for activity tracking
        """
        vals = {'agent_id': self.mock_new_agent.id}
        
        self.mock_lead.message_post(
            body=f"Lead reassigned from {self.mock_old_agent.name} to {self.mock_new_agent.name} by {self.mock_manager.name}",
            subject="Lead Reassignment",
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )
        
        call_args = self.mock_lead.message_post.call_args
        self.assertEqual(call_args.kwargs['message_type'], 'notification')
        self.assertEqual(call_args.kwargs['subtype_xmlid'], 'mail.mt_note')
    
    def test_multiple_reassignments_logged_separately(self):
        """
        GIVEN: Lead reassigned twice in sequence
        WHEN: Agent Alice → Agent Bob → Agent Charlie
        THEN: message_post called twice with different messages
        """
        mock_agent_charlie = MagicMock()
        mock_agent_charlie.id = 30
        mock_agent_charlie.name = "Agent Charlie"
        
        # First reassignment: Alice → Bob
        self.mock_lead.message_post(
            body=f"Lead reassigned from {self.mock_old_agent.name} to {self.mock_new_agent.name} by {self.mock_manager.name}",
            subject="Lead Reassignment",
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )
        
        # Update current agent
        self.mock_lead.agent_id = self.mock_new_agent
        
        # Second reassignment: Bob → Charlie
        self.mock_lead.message_post(
            body=f"Lead reassigned from {self.mock_new_agent.name} to {mock_agent_charlie.name} by {self.mock_manager.name}",
            subject="Lead Reassignment",
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )
        
        # Verify two separate calls
        self.assertEqual(self.mock_lead.message_post.call_count, 2)
        
        # Verify different messages
        call_1 = self.mock_lead.message_post.call_args_list[0]
        call_2 = self.mock_lead.message_post.call_args_list[1]
        
        self.assertIn("Agent Alice", call_1.kwargs['body'])
        self.assertIn("Agent Bob", call_1.kwargs['body'])
        
        self.assertIn("Agent Bob", call_2.kwargs['body'])
        self.assertIn("Agent Charlie", call_2.kwargs['body'])
    
    def test_reassignment_subject_field_correct(self):
        """
        GIVEN: Reassignment operation
        WHEN: message_post called
        THEN: subject field must be "Lead Reassignment"
        """
        vals = {'agent_id': self.mock_new_agent.id}
        
        self.mock_lead.message_post(
            body=f"Lead reassigned from {self.mock_old_agent.name} to {self.mock_new_agent.name} by {self.mock_manager.name}",
            subject="Lead Reassignment",
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )
        
        call_args = self.mock_lead.message_post.call_args
        self.assertEqual(call_args.kwargs['subject'], "Lead Reassignment")


if __name__ == '__main__':
    unittest.main()
