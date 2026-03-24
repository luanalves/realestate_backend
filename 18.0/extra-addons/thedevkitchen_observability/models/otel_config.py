# -*- coding: utf-8 -*-
"""OpenTelemetry Configuration Helper

Provides methods to access OTEL configuration from templates and code.
Environment variables are read from the OS environment.
"""

import os
from odoo import api, models


class OtelConfigHelper(models.AbstractModel):
    """Helper model for accessing OpenTelemetry configuration in templates"""
    
    _name = 'otel.config.helper'
    _description = 'OpenTelemetry Configuration Helper'
    
    @api.model
    def get_deployment_environment(self):
        """Get OTEL_DEPLOYMENT_ENVIRONMENT from OS environment
        
        Returns:
            str: Deployment environment (development, staging, production)
        """
        return os.environ.get('OTEL_DEPLOYMENT_ENVIRONMENT', 'development')
    
    @api.model
    def get_browser_config(self):
        """Get complete browser-side OTEL configuration
        
        Returns:
            dict: Configuration dictionary with keys:
                - enabled (bool): Whether OTEL is enabled
                - service_name (str): Service name for browser traces
                - service_version (str): Service version
                - deployment_environment (str): Deployment environment
                - otlp_endpoint (str): OTLP endpoint URL (Odoo proxy)
        """
        return {
            'enabled': os.environ.get('OTEL_ENABLED', 'true').lower() == 'true',
            'service_name': os.environ.get('OTEL_BROWSER_SERVICE_NAME', 'odoo-browser'),
            'service_version': '18.0',
            'deployment_environment': self.get_deployment_environment(),
            'otlp_endpoint': '/api/otel/traces',  # Relative path (same-origin)
        }
