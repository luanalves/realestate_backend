# -*- coding: utf-8 -*-
"""
Agent-Property Assignment Model

Manages the relationship between agents and properties with multi-tenant validation.

Author: Quicksol Technologies
Date: 2026-01-12
ADRs: ADR-004 (Nomenclatura), ADR-008 (Multi-tenancy)
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AgentPropertyAssignment(models.Model):
    _name = 'real.estate.agent.property.assignment'
    _description = 'Agent Property Assignment'
    _order = 'assignment_date desc, id desc'
    _rec_name = 'id'
    
    # ==================== CORE FIELDS ====================
    
    agent_id = fields.Many2one(
        'real.estate.agent',
        string='Agent',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    property_id = fields.Many2one(
        'real.estate.property',
        string='Property',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    company_id = fields.Many2one(
        'thedevkitchen.estate.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self._get_default_company()
    )
    
    assignment_date = fields.Date(
        string='Assignment Date',
        default=fields.Date.today,
        required=True
    )
    
    responsibility_type = fields.Selection([
        ('primary', 'Primary Agent'),
        ('secondary', 'Secondary Agent'),
        ('support', 'Support Agent')
    ], string='Responsibility Type', default='primary', required=True)
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Deactivate to end assignment without deleting history'
    )
    
    notes = fields.Text(string='Notes')
    
    # ==================== CONSTRAINTS ====================
    
    _sql_constraints = [
        ('agent_property_unique',
         'UNIQUE(agent_id, property_id, active) WHERE active = TRUE',
         'This agent is already assigned to this property')
    ]
    
    @api.constrains('agent_id', 'property_id', 'company_id')
    def _check_company_match(self):
        """Ensure agent and property belong to the same company"""
        for assignment in self:
            # Check if agent's company is in property's companies
            if assignment.agent_id.company_id not in assignment.property_id.company_ids:
                raise ValidationError(_(
                    'Agent and property must share at least one company. '
                    'Agent company: %s, Property companies: %s'
                ) % (
                    assignment.agent_id.company_id.name,
                    ', '.join(assignment.property_id.company_ids.mapped('name'))
                ))
            
            # Ensure assignment company matches agent company
            if assignment.company_id != assignment.agent_id.company_id:
                raise ValidationError(_(
                    'Assignment company must match agent company'
                ))
    
    # ==================== COMPUTED FIELDS ====================
    
    @api.depends('agent_id', 'agent_id.company_id')
    def _compute_company_id(self):
        """Auto-set company from agent"""
        for assignment in self:
            if assignment.agent_id:
                assignment.company_id = assignment.agent_id.company_id
    
    # ==================== DEFAULTS ====================
    
    def _get_default_company(self):
        """Get default company from context or user"""
        company_id = self.env.context.get('default_company_id')
        if company_id:
            return company_id
        
        # Try to get from user's estate companies
        if hasattr(self.env.user, 'estate_default_company_id'):
            return self.env.user.estate_default_company_id
        
        # Fallback to first company
        companies = self.env['thedevkitchen.estate.company'].search([], limit=1)
        return companies[0] if companies else False
    
    # ==================== CRUD OVERRIDES ====================
    
    @api.model
    def create(self, vals):
        """Override create to auto-set company from agent"""
        if 'agent_id' in vals and 'company_id' not in vals:
            agent = self.env['real.estate.agent'].browse(vals['agent_id'])
            if agent.company_id:
                vals['company_id'] = agent.company_id.id
        
        return super().create(vals)
    
    def write(self, vals):
        """Prevent changing agent or property after creation"""
        if 'agent_id' in vals or 'property_id' in vals:
            raise ValidationError(_(
                'Cannot change agent or property after assignment is created. '
                'Delete this assignment and create a new one instead.'
            ))
        
        return super().write(vals)
    
    # ==================== BUSINESS METHODS ====================
    
    def action_deactivate(self):
        """Deactivate assignment (soft-delete)"""
        self.ensure_one()
        self.write({'active': False})
        return True
    
    def action_reactivate(self):
        """Reactivate assignment"""
        self.ensure_one()
        self.write({'active': True})
        return True
