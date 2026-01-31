# -*- coding: utf-8 -*-
"""
Unit tests for Activity Tracking (Phase 5)

Tests activity logging, listing, scheduled activities, and recent activities.

Author: Quicksol Technologies
Date: 2026-01-30
Branch: 006-lead-management
FRs: FR-033, FR-034, FR-035, FR-036, FR-037
"""

import unittest
from datetime import datetime, timedelta
from odoo.tests import common


class TestActivityTracking(common.TransactionCase):
    """Test activity tracking functionality for leads"""
    
    def setUp(self):
        """Set up test data"""
        super(TestActivityTracking, self).setUp()
        
        # Get models
        self.Lead = self.env['real.estate.lead']
        self.User = self.env['res.users']
        self.Company = self.env['res.company']
        self.ActivityType = self.env['mail.activity.type']
        
        # Create test company
        self.company = self.Company.create({
            'name': 'Test Real Estate Company'
        })
        
        # Create test agent
        self.agent = self.User.create({
            'name': 'Agent Test',
            'login': 'agent_test@example.com',
            'email': 'agent_test@example.com',
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])]
        })
        
        # Create test lead
        self.lead = self.Lead.with_user(self.agent).create({
            'name': 'Test Lead for Activities',
            'phone': '1122334455',
            'email': 'testlead@example.com',
            'agent_id': self.agent.id,
            'company_ids': [(6, 0, [self.company.id])],
            'state': 'new'
        })
    
    def test_activity_logging_via_message_post(self):
        """Test that activity logging via message_post works (FR-033)"""
        # Log an activity
        activity_body = "📞 <strong>CALL</strong><br/>Called client to discuss property options"
        
        message = self.lead.with_user(self.agent).message_post(
            body=activity_body,
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )
        
        # Verify message was created
        self.assertTrue(message, "Activity message should be created")
        self.assertEqual(message.model, 'real.estate.lead')
        self.assertEqual(message.res_id, self.lead.id)
        self.assertEqual(message.message_type, 'comment')
        self.assertIn('CALL', message.body)
    
    def test_multiple_activity_types(self):
        """Test logging different activity types (call, email, meeting, note)"""
        activity_types = [
            ('📞 <strong>CALL</strong><br/>Phone conversation', 'CALL'),
            ('📧 <strong>EMAIL</strong><br/>Sent property brochure', 'EMAIL'),
            ('🤝 <strong>MEETING</strong><br/>Property viewing scheduled', 'MEETING'),
            ('📝 <strong>NOTE</strong><br/>Client prefers modern apartments', 'NOTE')
        ]
        
        for body, expected_type in activity_types:
            message = self.lead.with_user(self.agent).message_post(
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_note'
            )
            
            self.assertIn(expected_type, message.body)
    
    def test_activity_author_tracking(self):
        """Test that activity author is correctly tracked"""
        message = self.lead.with_user(self.agent).message_post(
            body="📝 <strong>NOTE</strong><br/>First contact made",
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )
        
        # Verify author
        self.assertEqual(message.author_id.id, self.agent.partner_id.id)
    
    def test_activity_chronological_order(self):
        """Test that activities are stored in chronological order"""
        # Create multiple activities
        for i in range(3):
            self.lead.with_user(self.agent).message_post(
                body=f"📝 <strong>NOTE</strong><br/>Activity {i+1}",
                message_type='comment',
                subtype_xmlid='mail.mt_note'
            )
        
        # Get messages
        messages = self.env['mail.message'].search([
            ('model', '=', 'real.estate.lead'),
            ('res_id', '=', self.lead.id),
            ('message_type', '=', 'comment')
        ], order='date desc')
        
        # Verify order (newest first)
        self.assertGreaterEqual(len(messages), 3)
        self.assertIn('Activity 3', messages[0].body)
    
    def test_scheduled_activity_creation(self):
        """Test creating scheduled activities with deadlines (FR-036)"""
        # Get or create activity type
        activity_type = self.ActivityType.search([('name', '=', 'To Do')], limit=1)
        if not activity_type:
            activity_type = self.ActivityType.create({
                'name': 'To Do',
                'summary': 'To Do'
            })
        
        # Create scheduled activity
        deadline = datetime.now().date() + timedelta(days=7)
        
        activity_vals = {
            'res_id': self.lead.id,
            'res_model_id': self.env['ir.model'].search([('model', '=', 'real.estate.lead')], limit=1).id,
            'activity_type_id': activity_type.id,
            'summary': 'Follow up call scheduled',
            'note': 'Call client to check if they viewed the properties',
            'date_deadline': deadline,
            'user_id': self.agent.id
        }
        
        activity = self.env['mail.activity'].create(activity_vals)
        
        # Verify activity
        self.assertTrue(activity, "Scheduled activity should be created")
        self.assertEqual(activity.res_id, self.lead.id)
        self.assertEqual(activity.summary, 'Follow up call scheduled')
        self.assertEqual(activity.date_deadline, deadline)
        self.assertEqual(activity.user_id.id, self.agent.id)
    
    def test_activity_assignment(self):
        """Test assigning scheduled activities to different users"""
        # Create second agent
        agent2 = self.User.create({
            'name': 'Agent Two',
            'login': 'agent2@example.com',
            'email': 'agent2@example.com',
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])]
        })
        
        # Get activity type
        activity_type = self.ActivityType.search([], limit=1)
        if not activity_type:
            activity_type = self.ActivityType.create({
                'name': 'To Do',
                'summary': 'To Do'
            })
        
        # Create activity assigned to agent2
        deadline = datetime.now().date() + timedelta(days=3)
        
        activity = self.env['mail.activity'].create({
            'res_id': self.lead.id,
            'res_model_id': self.env['ir.model'].search([('model', '=', 'real.estate.lead')], limit=1).id,
            'activity_type_id': activity_type.id,
            'summary': 'Manager review required',
            'date_deadline': deadline,
            'user_id': agent2.id
        })
        
        # Verify assignment
        self.assertEqual(activity.user_id.id, agent2.id)
    
    def test_multiple_activities_on_lead(self):
        """Test that leads can have multiple activities"""
        # Log 3 different activities
        self.lead.message_post(
            body="📞 <strong>CALL</strong><br/>Initial contact",
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )
        
        self.lead.message_post(
            body="📧 <strong>EMAIL</strong><br/>Sent brochure",
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )
        
        self.lead.message_post(
            body="🤝 <strong>MEETING</strong><br/>Scheduled viewing",
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )
        
        # Count messages
        message_count = self.env['mail.message'].search_count([
            ('model', '=', 'real.estate.lead'),
            ('res_id', '=', self.lead.id),
            ('message_type', '=', 'comment')
        ])
        
        self.assertGreaterEqual(message_count, 3)
    
    def test_mail_thread_inheritance(self):
        """Test that lead model correctly inherits mail.thread"""
        # Verify lead has mail.thread methods
        self.assertTrue(hasattr(self.lead, 'message_post'))
        self.assertTrue(hasattr(self.lead, 'message_ids'))
        self.assertTrue(hasattr(self.lead, 'message_follower_ids'))
    
    def test_mail_activity_mixin_inheritance(self):
        """Test that lead model correctly inherits mail.activity.mixin"""
        # Verify lead has mail.activity.mixin fields
        self.assertTrue(hasattr(self.lead, 'activity_ids'))
        self.assertTrue(hasattr(self.lead, 'activity_state'))


if __name__ == '__main__':
    unittest.main()
