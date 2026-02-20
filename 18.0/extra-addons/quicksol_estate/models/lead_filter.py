# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json


class RealEstateLeadFilter(models.Model):
    _name = 'real.estate.lead.filter'
    _description = 'Saved Lead Search Filter'
    _order = 'name'
    
    name = fields.Char(
        'Filter Name',
        required=True,
        size=100,
        help='Descriptive name for this saved filter (e.g., "High-value Centro leads")'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        ondelete='cascade',
        help='User who owns this saved filter'
    )
    
    filter_domain = fields.Text(
        'Filter Criteria',
        required=True,
        help='JSON-encoded filter parameters'
    )
    
    is_shared = fields.Boolean(
        'Shared',
        default=False,
        help='If true, filter is visible to all users in the same company'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Company this filter belongs to'
    )
    
    @api.constrains('filter_domain')
    def _check_filter_domain(self):
        """Validate that filter_domain is valid JSON"""
        for record in self:
            try:
                json.loads(record.filter_domain)
            except (ValueError, TypeError):
                raise ValidationError(_('Filter criteria must be valid JSON'))
    
    @api.constrains('name', 'user_id')
    def _check_unique_name_per_user(self):
        """Ensure filter names are unique per user"""
        for record in self:
            existing = self.search([
                ('name', '=', record.name),
                ('user_id', '=', record.user_id.id),
                ('id', '!=', record.id)
            ], limit=1)
            if existing:
                raise ValidationError(_('You already have a saved filter with this name'))
    
    def get_filter_params(self):
        """Parse and return filter parameters as dict"""
        self.ensure_one()
        try:
            return json.loads(self.filter_domain)
        except (ValueError, TypeError):
            return {}
    
    def apply_filter(self):
        """Apply this filter to lead search"""
        self.ensure_one()
        params = self.get_filter_params()
        
        # Build domain from params
        domain = []
        
        if params.get('state'):
            domain.append(('state', '=', params['state']))
        
        if params.get('agent_id'):
            domain.append(('agent_id', '=', int(params['agent_id'])))
        
        if params.get('budget_min'):
            domain.append(('budget_max', '>=', float(params['budget_min'])))
        
        if params.get('budget_max'):
            domain.append(('budget_min', '<=', float(params['budget_max'])))
        
        if params.get('bedrooms'):
            domain.append(('bedrooms_needed', '=', int(params['bedrooms'])))
        
        if params.get('property_type_id'):
            domain.append(('property_type_interest', '=', int(params['property_type_id'])))
        
        if params.get('location'):
            domain.append(('location_preference', 'ilike', params['location']))
        
        # Return action with domain
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'real.estate.lead',
            'view_mode': 'kanban,list,form',
            'domain': domain,
            'context': {'search_default_active': 1}
        }
