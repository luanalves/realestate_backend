# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import date


class BaseAgentTest(unittest.TestCase):
    """
    Base class for Agent model unit tests.
    
    Provides:
    - Agent-specific test data and mocks
    - User synchronization test scenarios
    - Email validation utilities
    """
    
    def setUp(self):
        super().setUp()
        
        # Mock Odoo environment
        self.env = Mock()
        self.cr = Mock()
        self.uid = 1
        
        # Agent test data
        self.agent_data = {
            'id': 1,
            'name': 'Test Agent',
            'cpf': '444.555.666-77',
            'email': 'agent@test.com',
            'phone': '+55 11 99999-9999',
            'user_id': 1,
            'company_ids': [1],
            'agency_name': 'Top Real Estate',
            'years_experience': 5,
            'properties': [1, 2]
        }
        
        # User test data for synchronization
        self.user_with_companies = {
            'id': 1,
            'name': 'John Agent User',
            'email': 'john@agent.com',
            'estate_company_ids': [1, 2]
        }
        
        self.user_without_companies = {
            'id': 2,
            'name': 'Jane Agent User',
            'email': 'jane@agent.com'
            # No estate_company_ids
        }
        
        # Email test cases
        self.valid_emails = [
            'agent@company.com',
            'john.doe@realestate.com.br',
            'agent+tag@domain.org'
        ]
        
        self.invalid_emails = [
            'invalid-email',
            '@domain.com',
            'agent@',
            'agent@@domain.com'
        ]
    
    def create_agent_mock(self, data=None):
        """Create a mock agent record"""
        agent_data = data or self.agent_data
        agent = Mock()
        
        for key, value in agent_data.items():
            setattr(agent, key, value)
        
        agent._name = 'real.estate.agent'
        agent.exists = Mock(return_value=agent)
        agent.ensure_one = Mock(return_value=None)
        
        return agent
    
    def create_user_mock(self, data):
        """Create a mock user record"""
        user = Mock()
        
        for key, value in data.items():
            setattr(user, key, value)
        
        user._name = 'res.users'
        user.exists = Mock(return_value=user)
        
        return user
    
    def mock_user_company_sync(self, agent, user_data):
        """Mock user-agent company synchronization logic"""
        user = self.create_user_mock(user_data)
        
        if hasattr(user, 'estate_company_ids') and user.estate_company_ids:
            agent.company_ids = user.estate_company_ids
        
        return agent