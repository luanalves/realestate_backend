# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from odoo.modules.module import get_module_resource
from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request


class SwaggerController(http.Controller):
    @http.route('/api/docs', type='http', auth='none', methods=['GET'], csrf=False)
    @trace_http_request
    def swagger_ui(self, **kwargs):
        """Serve Swagger UI"""
        swagger_path = get_module_resource('thedevkitchen_apigateway', 'static', 'src', 'swagger.html')
        with open(swagger_path, 'r') as f:
            content = f.read()
        return request.make_response(content, headers=[('Content-Type', 'text/html')])

    @http.route('/api/v1/openapi.json', type='http', auth='none', methods=['GET'], csrf=False)
    @trace_http_request
    def openapi_spec(self, **kwargs):
        # Get all registered endpoints from database
        Endpoint = request.env['thedevkitchen.api.endpoint'].sudo()
        endpoints = Endpoint.search([('active', '=', True)], order='path asc, method asc')
        
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
        
        # Top-level tag descriptions (shown in Swagger UI section headers)
        TAG_DESCRIPTIONS = {
            "Lead Filters": (
                "Filtros de busca salvos para leads. "
                "Um agente aplica uma combinação complexa de filtros (ex: budget R$300k-500k, "
                "2-3 quartos, bairro Centro) com frequência — em vez de reconfigurar esses filtros "
                "toda vez, ele salva como \"High-value Centro leads\" e reutiliza posteriormente. "
                "Útil para clientes externos (app mobile, integrações) que precisam persistir e "
                "reaplicar filtros complexos sem depender das views nativas do Odoo."
            ),
        }

        # Collect all unique tags from endpoints and build the tags array
        all_tags = {}
        for endpoint in endpoints:
            for tag in (endpoint.tags.split(',') if endpoint.tags else [endpoint.module_name]):
                tag = tag.strip()
                if tag not in all_tags:
                    all_tags[tag] = TAG_DESCRIPTIONS.get(tag, "")

        spec["tags"] = [
            {"name": name, "description": desc} if desc else {"name": name}
            for name, desc in sorted(all_tags.items(), key=lambda x: x[0].lower())
        ]

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
            
            # Add request body schema if defined (for POST, PUT, PATCH)
            if endpoint.request_schema and method in ['post', 'put', 'patch']:
                try:
                    request_schema_obj = json.loads(endpoint.request_schema)
                    operation["requestBody"] = {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": request_schema_obj
                            }
                        }
                    }
                except json.JSONDecodeError:
                    pass  # Ignore invalid JSON
            
            # Add response schema if defined
            if endpoint.response_schema:
                try:
                    response_schema_obj = json.loads(endpoint.response_schema)
                    operation["responses"]["200"]["content"] = {
                        "application/json": {
                            "schema": response_schema_obj
                        }
                    }
                except json.JSONDecodeError:
                    pass  # Ignore invalid JSON
            
            # Add security if protected
            if not endpoint.protected:
                operation["security"] = []
            
            spec["paths"][path][method] = operation
        
        spec["paths"] = dict(sorted(spec["paths"].items(), key=lambda x: x[0].lower()))
        return request.make_json_response(spec)
