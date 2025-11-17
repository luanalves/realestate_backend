# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ApiEndpoint(models.Model):
    _name = 'api.endpoint'
    _description = 'API Endpoint Registry'
    _order = 'module_name, path, method'

    name = fields.Char(
        string='Endpoint Name',
        required=True,
        help='Human-readable name for this endpoint'
    )
    
    path = fields.Char(
        string='Path',
        required=True,
        help='API path (e.g., /api/v1/properties)'
    )
    
    method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
    ], string='HTTP Method', required=True, default='GET')
    
    module_name = fields.Char(
        string='Module',
        required=True,
        help='Module that provides this endpoint'
    )
    
    description = fields.Text(
        string='Description',
        help='Description of what this endpoint does'
    )
    
    protected = fields.Boolean(
        string='Protected',
        default=True,
        help='If True, requires OAuth 2.0 authentication'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If False, endpoint is disabled'
    )
    
    request_schema = fields.Text(
        string='Request Schema',
        help='JSON Schema for request validation (optional)'
    )
    
    response_schema = fields.Text(
        string='Response Schema',
        help='JSON Schema for response documentation (optional)'
    )
    
    # OpenAPI/Swagger fields
    summary = fields.Char(
        string='Summary',
        help='Short summary for Swagger UI'
    )
    
    tags = fields.Char(
        string='Tags',
        help='Comma-separated tags for Swagger grouping (e.g., "Properties, Real Estate")'
    )
    
    # Usage statistics
    call_count = fields.Integer(
        string='Call Count',
        default=0,
        readonly=True,
        help='Number of times this endpoint has been called'
    )
    
    last_called = fields.Datetime(
        string='Last Called',
        readonly=True,
        help='Last time this endpoint was called'
    )
    
    # Constraints
    _sql_constraints = [
        ('unique_path_method', 'unique(path, method)', 
         'An endpoint with this path and method already exists!'),
    ]
    
    @api.constrains('path')
    def _check_path(self):
        """Validate that path starts with /"""
        for record in self:
            if not record.path.startswith('/'):
                raise ValidationError(_('Path must start with /'))
    
    def increment_call_count(self):
        """Increment the call counter and update last_called timestamp"""
        self.sudo().write({
            'call_count': self.call_count + 1,
            'last_called': fields.Datetime.now()
        })
    
    def get_full_info(self):
        """Return complete endpoint information for Swagger documentation"""
        self.ensure_one()
        return {
            'name': self.name,
            'path': self.path,
            'method': self.method,
            'module': self.module_name,
            'description': self.description,
            'protected': self.protected,
            'summary': self.summary,
            'tags': self.tags.split(',') if self.tags else [],
            'request_schema': self.request_schema,
            'response_schema': self.response_schema,
        }
    
    @api.model
    def register_endpoint(self, values):
        """
        Helper method for modules to register their endpoints
        
        Usage in other modules:
            self.env['api.endpoint'].register_endpoint({
                'name': 'List Properties',
                'path': '/api/v1/properties',
                'method': 'GET',
                'module_name': 'quicksol_estate',
                'description': 'Get list of all properties',
                'summary': 'List all properties',
                'tags': 'Properties',
            })
        """
        existing = self.search([
            ('path', '=', values.get('path')),
            ('method', '=', values.get('method'))
        ], limit=1)
        
        if existing:
            # Update existing endpoint
            existing.write(values)
            return existing
        else:
            # Create new endpoint
            return self.create(values)
