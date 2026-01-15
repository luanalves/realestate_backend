# -*- coding: utf-8 -*-
"""
Swagger/OpenAPI Controller

Provides Swagger UI and OpenAPI specification dynamically generated from database
"""

import json
from odoo import http
from odoo.http import request
from odoo.modules.module import get_module_resource


class SwaggerController(http.Controller):
    """Swagger UI and OpenAPI specification endpoints"""

    @http.route('/api/docs', type='http', auth='none', methods=['GET'], csrf=False)
    def swagger_ui(self, **kwargs):
        """Serve Swagger UI"""
        swagger_path = get_module_resource('thedevkitchen_apigateway', 'static', 'src', 'swagger.html')
        with open(swagger_path, 'r') as f:
            content = f.read()
        return request.make_response(content, headers=[('Content-Type', 'text/html')])

    @http.route('/api/v1/openapi.json', type='http', auth='none', methods=['GET'], csrf=False)
    def openapi_spec(self, **kwargs):
        """
        Generate OpenAPI 3.0 specification from registered endpoints in database
        
        GET /api/v1/openapi.json
        
        Returns:
            OpenAPI 3.0 specification in JSON format
        """
        # Get all registered endpoints from database
        Endpoint = request.env['thedevkitchen.api.endpoint'].sudo()
        endpoints = Endpoint.search([('active', '=', True)])
        
        # Build OpenAPI spec base structure
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Quicksol Real Estate API",
                "description": "REST API for Real Estate Management System with OAuth 2.0 authentication",
                "version": "2.0.0"
            },
            "servers": [
                {
                    "url": f"{request.httprequest.host_url.rstrip('/')}",
                    "description": "Current server"
                }
            ],
            "security": [
                {"BearerAuth": []}
            ],
            "components": {
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                        "description": "JWT token obtained from /api/v1/auth/token or /api/v1/users/login"
                    },
                    "OAuth2": {
                        "type": "oauth2",
                        "flows": {
                            "clientCredentials": {
                                "tokenUrl": "/api/v1/auth/token",
                                "refreshUrl": "/api/v1/auth/refresh",
                                "scopes": {
                                    "read": "Read access",
                                    "write": "Write access",
                                    "admin": "Admin access"
                                }
                            }
                        }
                    }
                },
                "schemas": {
                    "Error": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string"},
                            "error_description": {"type": "string"}
                        }
                    }
                }
            },
            "paths": {}
        }
        
        # Add registered endpoints from database
        for endpoint in endpoints:
            path = endpoint.path
            method = endpoint.method.lower()
            
            if path not in spec["paths"]:
                spec["paths"][path] = {}
            
            # Build operation spec
            operation = {
                "tags": endpoint.tags.split(',') if endpoint.tags else [endpoint.module_name],
                "summary": endpoint.summary or endpoint.name,
                "description": endpoint.description or "",
                "operationId": f"{method}_{path.replace('/', '_').strip('_')}",
                "responses": {
                    "200": {
                        "description": "Successful response"
                    },
                    "401": {
                        "description": "Unauthorized"
                    },
                    "404": {
                        "description": "Not found"
                    }
                }
            }
            
            # Add security if protected
            if not endpoint.protected:
                operation["security"] = []
            
            spec["paths"][path][method] = operation
        
        return request.make_json_response(spec)
