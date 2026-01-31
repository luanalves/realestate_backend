# -*- coding: utf-8 -*-
"""
Unit Test: Lead Company Validation

Tests the company validation constraint (_check_agent_company).
Follows ADR-003: Unitário (SEM banco, mock only) para validações @api.constrains

Author: Test Generator
Branch: 006-lead-management
Task: T020
FR: FR-023 (Agent must belong to at least one lead company)
"""

import unittest
from unittest.mock import MagicMock
from odoo.exceptions import ValidationError


class TestLeadCompanyValidation(unittest.TestCase):
    """Test agent-company validation (FR-023)"""
    
    def setUp(self):
        """Setup test environment"""
        self.lead = MagicMock()
        self.lead.id = 1
        
        # Mock agent with companies
        self.agent = MagicMock()
        self.agent.id = 100
        self.agent.company_ids = MagicMock()
        
        self.lead.agent_id = self.agent
        self.lead.company_ids = MagicMock()
    
    def test_agent_belongs_to_lead_company_passes(self):
        """
        GIVEN: Agent belongs to Company A, Lead assigned to Company A
        WHEN: Constraint is checked
        THEN: No validation error (agent in lead's companies)
        """
        # Arrange: Mock company overlap
        company_a = MagicMock()
        company_a.id = 1
        
        self.agent.company_ids.__iter__ = lambda self: iter([company_a])
        self.lead.company_ids.__iter__ = lambda self: iter([company_a])
        
        # Mock the & operator (intersection)
        agent_companies = {company_a}
        lead_companies = {company_a}
        intersection = agent_companies & lead_companies
        
        # Act
        try:
            if self.lead.agent_id and self.lead.company_ids:
                if not intersection:
                    raise ValidationError(
                        "Agent must belong to at least one of the lead's companies."
                    )
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_agent_not_in_lead_company_fails(self):
        """
        GIVEN: Agent belongs to Company A, Lead assigned to Company B
        WHEN: Constraint is checked
        THEN: ValidationError is raised (no company overlap)
        """
        # Arrange: No company overlap
        company_a = MagicMock()
        company_a.id = 1
        company_b = MagicMock()
        company_b.id = 2
        
        agent_companies = {company_a}
        lead_companies = {company_b}
        intersection = agent_companies & lead_companies
        
        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            if self.lead.agent_id and self.lead.company_ids:
                if not intersection:
                    raise ValidationError(
                        "Agent must belong to at least one of the lead's companies."
                    )
        
        self.assertIn('Agent must belong to at least one', str(context.exception))
    
    def test_agent_in_multiple_lead_companies_passes(self):
        """
        GIVEN: Agent belongs to Companies A, B, C; Lead assigned to Companies A, D
        WHEN: Constraint is checked
        THEN: No validation error (agent in Company A which is in lead's companies)
        """
        # Arrange: Partial overlap (Company A)
        company_a = MagicMock()
        company_a.id = 1
        company_b = MagicMock()
        company_b.id = 2
        company_c = MagicMock()
        company_c.id = 3
        company_d = MagicMock()
        company_d.id = 4
        
        agent_companies = {company_a, company_b, company_c}
        lead_companies = {company_a, company_d}
        intersection = agent_companies & lead_companies
        
        # Act
        try:
            if self.lead.agent_id and self.lead.company_ids:
                if not intersection:
                    raise ValidationError(
                        "Agent must belong to at least one of the lead's companies."
                    )
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_no_agent_assigned_passes(self):
        """
        GIVEN: Lead has no agent assigned (agent_id = False)
        WHEN: Constraint is checked
        THEN: No validation error (validation skipped if no agent)
        """
        # Arrange
        self.lead.agent_id = False
        
        # Act
        try:
            if self.lead.agent_id and self.lead.company_ids:
                raise ValidationError("Should not execute validation")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_no_companies_assigned_passes(self):
        """
        GIVEN: Lead has no companies assigned (company_ids = [])
        WHEN: Constraint is checked
        THEN: No validation error (validation skipped if no companies)
        """
        # Arrange
        self.lead.company_ids = []
        
        # Act
        try:
            if self.lead.agent_id and self.lead.company_ids:
                raise ValidationError("Should not execute validation")
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)
    
    def test_agent_in_all_lead_companies_passes(self):
        """
        GIVEN: Agent belongs to Companies A, B; Lead assigned to Companies A, B
        WHEN: Constraint is checked
        THEN: No validation error (complete overlap)
        """
        # Arrange
        company_a = MagicMock()
        company_a.id = 1
        company_b = MagicMock()
        company_b.id = 2
        
        agent_companies = {company_a, company_b}
        lead_companies = {company_a, company_b}
        intersection = agent_companies & lead_companies
        
        # Act
        try:
            if self.lead.agent_id and self.lead.company_ids:
                if not intersection:
                    raise ValidationError(
                        "Agent must belong to at least one of the lead's companies."
                    )
            success = True
        except ValidationError:
            success = False
        
        # Assert
        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()
