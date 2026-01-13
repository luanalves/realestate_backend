# -*- coding: utf-8 -*-
"""
Agent Service

Business logic layer for agent management operations.
Handles agent creation, updates, validation, and business rules.

Per ADR-008: All business logic must be in service layer, not controllers.
Per ADR-011: Services provide company-aware operations for multi-tenancy.
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class AgentService:
    """
    Service layer for agent management business logic.
    
    Provides high-level operations for agent CRUD while enforcing
    business rules, validation, and multi-tenant isolation.
    """
    
    def __init__(self, env):
        """
        Initialize agent service with Odoo environment.
        
        Args:
            env: Odoo environment context
        """
        self.env = env
        self.Agent = env['real.estate.agent']
    
    def create_agent(self, values, company_id=None):
        """
        Create a new agent with validation and business rules.
        
        Args:
            values (dict): Agent field values
            company_id (int, optional): Company ID (defaults to current user's company)
            
        Returns:
            real.estate.agent: Created agent record
            
        Raises:
            ValidationError: If validation fails
            UserError: If business rules violated
        """
        # Ensure company_id is set (multi-tenancy requirement)
        if not company_id:
            company_id = self.env.company.id
            
        values['company_id'] = company_id
        
        # Validate required fields
        required_fields = ['name', 'cpf', 'creci', 'email']
        missing_fields = [field for field in required_fields if not values.get(field)]
        
        if missing_fields:
            raise ValidationError(
                _("Missing required fields: %s") % ', '.join(missing_fields)
            )
        
        # Check for duplicate CRECI in same company
        existing_agent = self.Agent.search([
            ('creci', '=', values['creci']),
            ('company_id', '=', company_id),
            ('active', '=', True)
        ], limit=1)
        
        if existing_agent:
            raise ValidationError(
                _("An agent with CRECI %s already exists in this company") % values['creci']
            )
        
        # CPF validation is handled by model constraint _check_cpf
        # CRECI validation is handled by model constraint _check_creci_format
        # Email validation is handled by model constraint _check_email
        
        try:
            agent = self.Agent.create(values)
            _logger.info(f"Created agent {agent.name} (ID: {agent.id}) for company {company_id}")
            return agent
            
        except Exception as e:
            _logger.error(f"Failed to create agent: {str(e)}")
            raise
    
    def update_agent(self, agent_id, values, user_company_id=None):
        """
        Update an existing agent with validation.
        
        Args:
            agent_id (int): Agent ID to update
            values (dict): Fields to update
            user_company_id (int, optional): User's company ID for authorization check
            
        Returns:
            real.estate.agent: Updated agent record
            
        Raises:
            ValidationError: If validation fails
            UserError: If unauthorized or agent not found
        """
        agent = self.Agent.browse(agent_id)
        
        if not agent.exists():
            raise UserError(_("Agent with ID %s not found") % agent_id)
        
        # Multi-tenant security: Prevent cross-company updates
        if user_company_id and agent.company_id.id != user_company_id:
            raise UserError(_("Cannot update agent from another company"))
        
        # Prevent company_id changes (security requirement)
        if 'company_id' in values and values['company_id'] != agent.company_id.id:
            raise ValidationError(_("Cannot change agent's company"))
        
        # Validate CRECI uniqueness if changing CRECI
        if 'creci' in values and values['creci'] != agent.creci:
            existing = self.Agent.search([
                ('creci', '=', values['creci']),
                ('company_id', '=', agent.company_id.id),
                ('id', '!=', agent_id),
                ('active', '=', True)
            ], limit=1)
            
            if existing:
                raise ValidationError(
                    _("Another agent with CRECI %s already exists") % values['creci']
                )
        
        try:
            agent.write(values)
            _logger.info(f"Updated agent {agent.name} (ID: {agent.id})")
            return agent
            
        except Exception as e:
            _logger.error(f"Failed to update agent {agent_id}: {str(e)}")
            raise
    
    def deactivate_agent(self, agent_id, reason=None, user_company_id=None):
        """
        Soft-delete an agent (set active=False) with reason logging.
        
        Args:
            agent_id (int): Agent ID to deactivate
            reason (str, optional): Reason for deactivation
            user_company_id (int, optional): User's company ID for authorization
            
        Returns:
            real.estate.agent: Deactivated agent record
            
        Raises:
            UserError: If unauthorized or agent not found
        """
        agent = self.Agent.browse(agent_id)
        
        if not agent.exists():
            raise UserError(_("Agent with ID %s not found") % agent_id)
        
        if user_company_id and agent.company_id.id != user_company_id:
            raise UserError(_("Cannot deactivate agent from another company"))
        
        if not agent.active:
            raise UserError(_("Agent is already inactive"))
        
        try:
            agent.action_deactivate(reason=reason)
            _logger.info(f"Deactivated agent {agent.name} (ID: {agent.id}) - Reason: {reason}")
            return agent
            
        except Exception as e:
            _logger.error(f"Failed to deactivate agent {agent_id}: {str(e)}")
            raise
    
    def reactivate_agent(self, agent_id, user_company_id=None):
        """
        Reactivate a previously deactivated agent.
        
        Args:
            agent_id (int): Agent ID to reactivate
            user_company_id (int, optional): User's company ID for authorization
            
        Returns:
            real.estate.agent: Reactivated agent record
            
        Raises:
            UserError: If unauthorized or agent not found
        """
        agent = self.Agent.browse(agent_id).sudo()
        
        if not agent.exists():
            raise UserError(_("Agent with ID %s not found") % agent_id)
        
        if user_company_id and agent.company_id.id != user_company_id:
            raise UserError(_("Cannot reactivate agent from another company"))
        
        if agent.active:
            raise UserError(_("Agent is already active"))
        
        try:
            agent.action_reactivate()
            _logger.info(f"Reactivated agent {agent.name} (ID: {agent.id})")
            return agent
            
        except Exception as e:
            _logger.error(f"Failed to reactivate agent {agent_id}: {str(e)}")
            raise
    
    def get_agent(self, agent_id, user_company_id=None, include_inactive=False):
        """
        Retrieve an agent by ID with company isolation.
        
        Args:
            agent_id (int): Agent ID
            user_company_id (int, optional): User's company ID for filtering
            include_inactive (bool): Whether to include inactive agents
            
        Returns:
            real.estate.agent: Agent record or empty recordset
        """
        domain = [('id', '=', agent_id)]
        
        if user_company_id:
            domain.append(('company_id', '=', user_company_id))
        
        if not include_inactive:
            domain.append(('active', '=', True))
        
        return self.Agent.search(domain, limit=1)
    
    def list_agents(self, company_id=None, include_inactive=False, limit=None, offset=None, filters=None):
        """
        List agents with filtering, pagination, and company isolation.
        
        Args:
            company_id (int, optional): Filter by company ID
            include_inactive (bool): Whether to include inactive agents
            limit (int, optional): Maximum records to return
            offset (int, optional): Records to skip (pagination)
            filters (dict, optional): Additional search filters (e.g., {'creci_state': 'SP'})
            
        Returns:
            real.estate.agent: Agent recordset
        """
        domain = []
        
        if company_id:
            domain.append(('company_id', '=', company_id))
        
        if not include_inactive:
            domain.append(('active', '=', True))
        
        # Apply additional filters
        if filters:
            if 'creci_state' in filters:
                domain.append(('creci_state', '=', filters['creci_state']))
            if 'search' in filters:
                # Search in name, CPF, or email
                search_term = filters['search']
                domain.append('|', '|', 
                             ('name', 'ilike', search_term),
                             ('cpf', 'ilike', search_term),
                             ('email', 'ilike', search_term))
        
        return self.Agent.search(domain, limit=limit, offset=offset, order='name')
    
    def count_agents(self, company_id=None, include_inactive=False):
        """
        Count agents with company isolation.
        
        Args:
            company_id (int, optional): Filter by company ID
            include_inactive (bool): Whether to count inactive agents
            
        Returns:
            int: Number of agents
        """
        domain = []
        
        if company_id:
            domain.append(('company_id', '=', company_id))
        
        if not include_inactive:
            domain.append(('active', '=', True))
        
        return self.Agent.search_count(domain)
