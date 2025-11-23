# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ApiAccessLog(models.Model):
    _name = 'thedevkitchen.api.access.log'
    _description = 'API Access Log'
    _order = 'create_date desc'
    _rec_name = 'endpoint_path'

    # Request Info
    endpoint_id = fields.Many2one(
        'thedevkitchen.api.endpoint',
        string='Endpoint',
        ondelete='set null',
        help='Registered endpoint (if any)'
    )
    
    endpoint_path = fields.Char(
        string='Path',
        required=True,
        index=True,
        help='API endpoint path (e.g., /api/v1/properties)'
    )
    
    method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
        ('OPTIONS', 'OPTIONS'),
    ], string='HTTP Method', required=True, index=True)
    
    # Authentication Info
    application_id = fields.Many2one(
        'thedevkitchen.oauth.application',
        string='OAuth Application',
        ondelete='set null',
        help='Application that made the request'
    )
    
    token_id = fields.Many2one(
        'thedevkitchen.oauth.token',
        string='Token',
        ondelete='set null',
        help='Token used for authentication'
    )
    
    authenticated = fields.Boolean(
        string='Authenticated',
        default=False,
        index=True,
        help='Whether request was authenticated'
    )
    
    # Response Info
    status_code = fields.Integer(
        string='Status Code',
        required=True,
        index=True,
        help='HTTP status code (200, 401, 404, etc.)'
    )
    
    response_time = fields.Float(
        string='Response Time (ms)',
        help='Time taken to process request in milliseconds'
    )
    
    # Request Details
    ip_address = fields.Char(
        string='IP Address',
        help='Client IP address'
    )
    
    user_agent = fields.Char(
        string='User Agent',
        help='Client user agent string'
    )
    
    request_body = fields.Text(
        string='Request Body',
        help='Request body (JSON)'
    )
    
    response_body = fields.Text(
        string='Response Body',
        help='Response body (JSON) - only for errors'
    )
    
    query_params = fields.Text(
        string='Query Parameters',
        help='URL query parameters'
    )
    
    # Error Info
    error_code = fields.Char(
        string='Error Code',
        help='OAuth error code (if any)'
    )
    
    error_description = fields.Text(
        string='Error Description',
        help='Error description (if any)'
    )
    
    # Computed Fields
    success = fields.Boolean(
        string='Success',
        compute='_compute_success',
        store=True,
        help='Whether request was successful (2xx status)'
    )
    
    @api.depends('status_code')
    def _compute_success(self):
        for record in self:
            record.success = 200 <= record.status_code < 300
    
    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.method} {record.endpoint_path} ({record.status_code})"
            result.append((record.id, name))
        return result
    
    @api.model
    def log_request(self, values):
        """
        Helper method to create a log entry
        
        Usage:
            self.env['api.access.log'].log_request({
                'endpoint_path': '/api/v1/properties',
                'method': 'GET',
                'status_code': 200,
                'response_time': 45.2,
                'authenticated': True,
                'application_id': app_id,
                'token_id': token_id,
            })
        """
        return self.sudo().create(values)
    
    @api.model
    def cleanup_old_logs(self, days=30):
        """
        Delete logs older than specified days
        Called by scheduled action
        
        Args:
            days: Number of days to keep logs (default: 30)
        
        Returns:
            Number of deleted records
        """
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_logs = self.search([('create_date', '<', cutoff_date)])
        count = len(old_logs)
        old_logs.unlink()
        return count
    
    @api.model
    def get_statistics(self, days=7):
        """
        Get API usage statistics
        
        Args:
            days: Number of days to analyze (default: 7)
        
        Returns:
            Dictionary with statistics
        """
        from_date = fields.Datetime.now() - timedelta(days=days)
        
        logs = self.search([('create_date', '>=', from_date)])
        
        total_requests = len(logs)
        successful_requests = len(logs.filtered(lambda l: l.success))
        failed_requests = total_requests - successful_requests
        
        avg_response_time = sum(logs.mapped('response_time')) / total_requests if total_requests > 0 else 0
        
        # Top endpoints
        endpoint_counts = {}
        for log in logs:
            key = f"{log.method} {log.endpoint_path}"
            endpoint_counts[key] = endpoint_counts.get(key, 0) + 1
        
        top_endpoints = sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Top applications
        app_counts = {}
        for log in logs.filtered(lambda l: l.application_id):
            app_name = log.application_id.name
            app_counts[app_name] = app_counts.get(app_name, 0) + 1
        
        top_apps = sorted(app_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'period_days': days,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            'avg_response_time_ms': round(avg_response_time, 2),
            'top_endpoints': top_endpoints,
            'top_applications': top_apps,
        }


# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import timedelta
