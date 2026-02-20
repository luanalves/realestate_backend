# -*- coding: utf-8 -*-

from odoo import _
from odoo.exceptions import ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)


class AssignmentService:

    def __init__(self, env):
        """
        Initialize service with Odoo environment.
        
        Args:
            env: Odoo environment (request.env)
        """
        self.env = env
        self.Assignment = env['real.estate.agent.property.assignment'].sudo()
        self.Agent = env['real.estate.agent'].sudo()
        self.Property = env['real.estate.property'].sudo()
    
    def assign_agent_to_property(self, agent_id, property_id, responsibility_type='primary', notes='', company_id=None):

        # Validate agent exists
        agent = self.Agent.browse(agent_id)
        if not agent.exists():
            raise ValidationError(_('Agent with ID %s not found') % agent_id)
        
        # Validate property exists
        property_obj = self.Property.browse(property_id)
        if not property_obj.exists():
            raise ValidationError(_('Property with ID %s not found') % property_id)
        
        # Validate responsibility type
        valid_types = ['primary', 'secondary', 'support']
        if responsibility_type not in valid_types:
            raise ValidationError(_(
                'Invalid responsibility type: %s. Must be one of: %s'
            ) % (responsibility_type, ', '.join(valid_types)))
        
        # Validate company match (agent company must be in property companies)
        if agent.company_id not in property_obj.company_ids:
            raise ValidationError(_(
                'Cannot assign agent to property from different company. '
                'Agent company: %s, Property companies: %s'
            ) % (
                agent.company_id.name,
                ', '.join(property_obj.company_ids.mapped('name'))
            ))
        
        # Additional company validation if provided
        if company_id:
            Company = self.env['thedevkitchen.estate.company'].sudo()
            company = Company.browse(company_id)
            if not company.exists():
                raise ValidationError(_('Company with ID %s not found') % company_id)
            
            if agent.company_id != company:
                raise AccessError(_(
                    'Cannot assign agent from company %s using company %s context'
                ) % (agent.company_id.name, company.name))
        
        # Check if assignment already exists
        existing_assignment = self.Assignment.search([
            ('agent_id', '=', agent_id),
            ('property_id', '=', property_id),
            ('active', '=', True)
        ], limit=1)
        
        if existing_assignment:
            _logger.info(
                f'Agent {agent_id} already assigned to property {property_id} '
                f'(assignment {existing_assignment.id})'
            )
            # Update existing assignment instead of creating duplicate
            existing_assignment.write({
                'responsibility_type': responsibility_type,
                'notes': notes,
            })
            return (existing_assignment, False)  # Returns tuple: (assignment, created=False)
        
        # Create new assignment
        assignment = self.Assignment.create({
            'agent_id': agent_id,
            'property_id': property_id,
            'responsibility_type': responsibility_type,
            'notes': notes,
        })
        
        _logger.info(
            f'Created assignment {assignment.id}: Agent {agent_id} -> Property {property_id} '
            f'(type: {responsibility_type})'
        )
        
        return (assignment, True)  # Returns tuple: (assignment, created=True)
    
    def unassign_agent_from_property(self, assignment_id, company_id=None):

        assignment = self.Assignment.browse(assignment_id)
        
        if not assignment.exists():
            raise ValidationError(_('Assignment with ID %s not found') % assignment_id)
        
        # Company validation
        if company_id:
            Company = self.env['thedevkitchen.estate.company'].sudo()
            company = Company.browse(company_id)
            if not company.exists():
                raise ValidationError(_('Company with ID %s not found') % company_id)
            
            if assignment.company_id != company:
                raise AccessError(_(
                    'Cannot delete assignment from company %s using company %s context'
                ) % (assignment.company_id.name, company.name))
        
        # Soft delete (deactivate)
        assignment.write({'active': False})
        
        _logger.info(
            f'Deactivated assignment {assignment_id}: '
            f'Agent {assignment.agent_id.id} -> Property {assignment.property_id.id}'
        )
        
        return True
    
    def get_agent_properties(self, agent_id, active_only=True, company_id=None):

        agent = self.Agent.browse(agent_id)
        if not agent.exists():
            raise ValidationError(_('Agent with ID %s not found') % agent_id)
        
        # Company validation
        if company_id:
            Company = self.env['thedevkitchen.estate.company'].sudo()
            company = Company.browse(company_id)
            if not company.exists():
                raise ValidationError(_('Company with ID %s not found') % company_id)
            
            if agent.company_id != company:
                raise AccessError(_(
                    'Cannot access agent from company %s using company %s context'
                ) % (agent.company_id.name, company.name))
        
        # Build domain
        domain = [('agent_id', '=', agent_id)]
        if active_only:
            domain.append(('active', '=', True))
        
        assignments = self.Assignment.search(domain, order='assignment_date desc')
        
        return assignments
    
    def get_property_agents(self, property_id, active_only=True, company_id=None):

        property_obj = self.Property.browse(property_id)
        if not property_obj.exists():
            raise ValidationError(_('Property with ID %s not found') % property_id)
        
        # Company validation
        if company_id:
            Company = self.env['thedevkitchen.estate.company'].sudo()
            company = Company.browse(company_id)
            if not company.exists():
                raise ValidationError(_('Company with ID %s not found') % company_id)
            
            if company not in property_obj.company_ids:
                raise AccessError(_(
                    'Cannot access property from companies %s using company %s context'
                ) % (', '.join(property_obj.company_ids.mapped('name')), company.name))
        
        # Build domain
        domain = [('property_id', '=', property_id)]
        if active_only:
            domain.append(('active', '=', True))
        
        assignments = self.Assignment.search(domain, order='assignment_date desc')
        
        return assignments
    
    def bulk_assign_agent(self, agent_id, property_ids, responsibility_type='primary', company_id=None):

        results = {
            'created': [],
            'updated': [],
            'errors': []
        }
        
        for property_id in property_ids:
            try:
                assignment, created = self.assign_agent_to_property(
                    agent_id=agent_id,
                    property_id=property_id,
                    responsibility_type=responsibility_type,
                    company_id=company_id
                )
                
                if created:
                    results['created'].append(assignment.id)
                else:
                    results['updated'].append(assignment.id)
                    
            except (ValidationError, AccessError) as e:
                results['errors'].append({
                    'property_id': property_id,
                    'error': str(e)
                })
                _logger.warning(
                    f'Failed to assign agent {agent_id} to property {property_id}: {e}'
                )
        
        return results
