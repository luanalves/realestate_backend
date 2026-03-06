# -*- coding: utf-8 -*-

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
        'res.company',
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
    
    # Note: SQL constraint with WHERE clause not supported in Odoo
    # Using Python constraint instead (see _check_duplicate_assignment below)
    _sql_constraints = []
    
    @api.constrains('agent_id', 'property_id', 'active')
    def _check_duplicate_assignment(self):
        """Prevent duplicate active assignments for the same agent-property pair"""
        for assignment in self:
            if assignment.active:
                duplicate = self.search([
                    ('id', '!=', assignment.id),
                    ('agent_id', '=', assignment.agent_id.id),
                    ('property_id', '=', assignment.property_id.id),
                    ('active', '=', True)
                ], limit=1)
                if duplicate:
                    raise ValidationError(_(
                        'Agent %s is already assigned to property %s'
                    ) % (assignment.agent_id.name, assignment.property_id.name))
    
    @api.constrains('agent_id', 'property_id', 'company_id')
    def _check_company_match(self):
        """Ensure agent and property belong to the same company"""
        for assignment in self:
            # Check if agent's company matches property's company (M2O)
            if assignment.agent_id.company_id != assignment.property_id.company_id:
                raise ValidationError(_(
                    'Agent and property must belong to the same company. '
                    'Agent company: %s, Property company: %s'
                ) % (
                    assignment.agent_id.company_id.name,
                    assignment.property_id.company_id.name
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
        
        # Try to get from user's current company (native res.users field)
        if self.env.user.company_id:
            return self.env.user.company_id
        
        # Fallback to first real estate company
        companies = self.env['res.company'].search([('is_real_estate', '=', True)], limit=1)
        return companies[0] if companies else False
    
    # ==================== CRUD OVERRIDES ====================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-set company from agent"""
        for vals in vals_list:
            if 'agent_id' in vals and 'company_id' not in vals:
                agent = self.env['real.estate.agent'].browse(vals['agent_id'])
                if agent.company_id:
                    vals['company_id'] = agent.company_id.id
        return super().create(vals_list)
    
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
