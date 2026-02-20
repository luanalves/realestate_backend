# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class AgentService: 
    def __init__(self, env):

        self.env = env
        self.Agent = env['real.estate.agent']
    
    def create_agent(self, values, company_id=None):
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
        domain = [('id', '=', agent_id)]
        
        if user_company_id:
            domain.append(('company_id', '=', user_company_id))
        
        if not include_inactive:
            domain.append(('active', '=', True))
        
        return self.Agent.search(domain, limit=1)
    
    def list_agents(self, company_id=None, include_inactive=False, limit=None, offset=None, filters=None):
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
        domain = []
        
        if company_id:
            domain.append(('company_id', '=', company_id))
        
        if not include_inactive:
            domain.append(('active', '=', True))
        
        return self.Agent.search_count(domain)
