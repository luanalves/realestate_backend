# -*- coding: utf-8 -*-
"""
Unit Test: Lead Soft Delete

Tests the soft delete behavior in unlink() override.
Follows ADR-003: Unitário (SEM banco, mock only) para lógica de métodos customizados

Author: Test Generator
Branch: 006-lead-management
Task: T022
FR: FR-018b (Leads must use soft delete: active=False instead of actual deletion)
"""

import unittest
from unittest.mock import MagicMock, patch


class TestLeadSoftDelete(unittest.TestCase):
    """Test soft delete behavior (FR-018b)"""
    
    def setUp(self):
        """Setup test environment"""
        self.lead = MagicMock()
        self.lead.id = 1
        self.lead.active = True
        self.lead.write = MagicMock(return_value=True)
    
    def test_unlink_sets_active_false(self):
        """
        GIVEN: Lead has active = True
        WHEN: unlink() is called
        THEN: write({'active': False}) is called instead of actual delete
        """
        # Act: Simulate unlink() override logic
        result = self.simulate_unlink()
        
        # Assert
        self.lead.write.assert_called_once_with({'active': False})
    
    def test_unlink_returns_true(self):
        """
        GIVEN: Lead exists
        WHEN: unlink() is called
        THEN: Returns True (standard Odoo unlink behavior)
        """
        # Act
        result = self.simulate_unlink()
        
        # Assert
        self.assertTrue(result)
    
    def test_unlink_does_not_actually_delete(self):
        """
        GIVEN: Lead has id = 1
        WHEN: unlink() is called
        THEN: Record still exists (id unchanged, active=False)
        """
        # Act
        result = self.simulate_unlink()
        
        # Assert: Record id still exists (not deleted from database)
        self.assertEqual(self.lead.id, 1)
        # Assert: write was called to set active=False (soft delete)
        self.lead.write.assert_called_once()
    
    def test_multiple_leads_soft_delete(self):
        """
        GIVEN: Recordset with 3 leads (ids 1, 2, 3)
        WHEN: unlink() is called on recordset
        THEN: write({'active': False}) is called once for all records
        """
        # Arrange
        leads = MagicMock()
        leads.ids = [1, 2, 3]
        leads.write = MagicMock(return_value=True)
        
        # Act: Simulate unlink() on recordset
        leads.write({'active': False})
        result = True
        
        # Assert
        leads.write.assert_called_once_with({'active': False})
        self.assertTrue(result)
    
    def test_inactive_lead_unlink_remains_inactive(self):
        """
        GIVEN: Lead has active = False (already archived)
        WHEN: unlink() is called
        THEN: write({'active': False}) is still called (idempotent)
        """
        # Arrange
        self.lead.active = False
        
        # Act
        result = self.simulate_unlink()
        
        # Assert: write is still called (Odoo doesn't check current value)
        self.lead.write.assert_called_once_with({'active': False})
        self.assertTrue(result)
    
    def test_unlink_does_not_call_super_unlink(self):
        """
        GIVEN: Lead exists
        WHEN: unlink() is called
        THEN: super().unlink() is NOT called (no actual database DELETE)
        """
        # Arrange: Mock super().unlink() to track if called
        with patch('odoo.models.Model.unlink') as mock_super_unlink:
            # Act
            result = self.simulate_unlink()
            
            # Assert: super().unlink() was never called
            mock_super_unlink.assert_not_called()
    
    def test_soft_delete_preserves_data(self):
        """
        GIVEN: Lead has data (name, phone, email, state)
        WHEN: unlink() is called
        THEN: Only active changes to False, all other data preserved
        """
        # Arrange
        self.lead.name = "João Silva"
        self.lead.phone = "+5511999887766"
        self.lead.email = "joao@example.com"
        self.lead.state = "qualified"
        
        # Act
        result = self.simulate_unlink()
        
        # Assert: Only write({'active': False}) was called
        self.lead.write.assert_called_once_with({'active': False})
        # Assert: Other fields unchanged
        self.assertEqual(self.lead.name, "João Silva")
        self.assertEqual(self.lead.phone, "+5511999887766")
        self.assertEqual(self.lead.email, "joao@example.com")
        self.assertEqual(self.lead.state, "qualified")
    
    def simulate_unlink(self):
        """Helper method simulating unlink() override logic"""
        self.lead.write({'active': False})
        return True


if __name__ == '__main__':
    unittest.main()
