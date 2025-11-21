# -*- coding: utf-8 -*-
"""
Swagger/OpenAPI Controller

Provides Swagger UI and OpenAPI specification
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
        swagger_path = get_module_resource('api_gateway', 'static', 'src', 'swagger.html')
        with open(swagger_path, 'r') as f:
            content = f.read()
        return request.make_response(content, headers=[('Content-Type', 'text/html')])

    @http.route('/api/v1/openapi.json', type='http', auth='none', methods=['GET'], csrf=False)
    def openapi_spec(self, **kwargs):
        """
        Generate OpenAPI 3.0 specification from registered endpoints
        
        GET /api/v1/openapi.json
        
        Returns:
            OpenAPI 3.0 specification in JSON format
        """
        # Get all registered endpoints
        Endpoint = request.env['thedevkitchen.api.endpoint'].sudo()
        endpoints = Endpoint.search([('active', '=', True)])
        
        # Build OpenAPI spec
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Odoo API Gateway",
                "description": "REST API with OAuth 2.0 authentication for Odoo",
                "version": "1.0.0",
                "contact": {
                    "name": "API Support",
                    "email": "support@example.com"
                }
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
                        "description": "JWT token obtained from /api/v1/auth/token"
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
                "schemas": {}
            },
            "paths": {}
        }
        
        # Add authentication endpoints (always present)
        spec["paths"]["/api/v1/auth/token"] = {
            "post": {
                "tags": ["Authentication"],
                "summary": "Get access token",
                "description": "OAuth 2.0 Client Credentials Grant. Accepts both JSON and form-urlencoded.",
                "operationId": "getToken",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["grant_type", "client_id", "client_secret"],
                                "properties": {
                                    "grant_type": {
                                        "type": "string",
                                        "enum": ["client_credentials"],
                                        "description": "OAuth 2.0 grant type"
                                    },
                                    "client_id": {
                                        "type": "string",
                                        "description": "OAuth client ID"
                                    },
                                    "client_secret": {
                                        "type": "string",
                                        "description": "OAuth client secret"
                                    }
                                }
                            }
                        },
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "type": "object",
                                "required": ["grant_type", "client_id", "client_secret"],
                                "properties": {
                                    "grant_type": {
                                        "type": "string",
                                        "enum": ["client_credentials"],
                                        "description": "OAuth 2.0 grant type"
                                    },
                                    "client_id": {
                                        "type": "string",
                                        "description": "OAuth client ID"
                                    },
                                    "client_secret": {
                                        "type": "string",
                                        "description": "OAuth client secret"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Successful authentication",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "access_token": {"type": "string"},
                                        "token_type": {"type": "string", "example": "Bearer"},
                                        "expires_in": {"type": "integer", "example": 3600},
                                        "refresh_token": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid request",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Error"
                                }
                            }
                        }
                    }
                },
                "security": []
            }
        }
        
        spec["paths"]["/api/v1/auth/refresh"] = {
            "post": {
                "tags": ["Authentication"],
                "summary": "Refresh access token",
                "description": "Get new access token using refresh token. Accepts both JSON and form-urlencoded. grant_type is optional (defaults to 'refresh_token').",
                "operationId": "refreshToken",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["refresh_token"],
                                "properties": {
                                    "refresh_token": {
                                        "type": "string",
                                        "description": "Refresh token from initial authentication"
                                    },
                                    "grant_type": {
                                        "type": "string",
                                        "enum": ["refresh_token"],
                                        "description": "Optional - defaults to 'refresh_token'"
                                    },
                                    "client_id": {
                                        "type": "string",
                                        "description": "Optional - OAuth client ID for validation"
                                    },
                                    "client_secret": {
                                        "type": "string",
                                        "description": "Optional - OAuth client secret for validation"
                                    }
                                }
                            }
                        },
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "type": "object",
                                "required": ["refresh_token"],
                                "properties": {
                                    "refresh_token": {
                                        "type": "string",
                                        "description": "Refresh token from initial authentication"
                                    },
                                    "grant_type": {
                                        "type": "string",
                                        "enum": ["refresh_token"],
                                        "description": "Optional - defaults to 'refresh_token'"
                                    },
                                    "client_id": {
                                        "type": "string",
                                        "description": "Optional - OAuth client ID for validation"
                                    },
                                    "client_secret": {
                                        "type": "string",
                                        "description": "Optional - OAuth client secret for validation"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Token refreshed successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "access_token": {"type": "string"},
                                        "token_type": {"type": "string"},
                                        "expires_in": {"type": "integer"},
                                        "refresh_token": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                },
                "security": []
            }
        }
        
        spec["paths"]["/api/v1/auth/revoke"] = {
            "post": {
                "tags": ["Authentication"],
                "summary": "Revoke token",
                "description": "Revoke an access token. Token can be sent in Authorization header (Bearer) OR in request body.",
                "operationId": "revokeToken",
                "parameters": [
                    {
                        "name": "Authorization",
                        "in": "header",
                        "description": "Bearer token to revoke (alternative to body parameter)",
                        "required": False,
                        "schema": {
                            "type": "string",
                            "example": "Bearer eyJhbGc..."
                        }
                    }
                ],
                "requestBody": {
                    "required": False,
                    "description": "Token in body (alternative to Authorization header)",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "token": {
                                        "type": "string",
                                        "description": "Access token to revoke"
                                    },
                                    "token_type_hint": {
                                        "type": "string",
                                        "enum": ["access_token"],
                                        "description": "Optional hint about token type"
                                    }
                                }
                            }
                        },
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "token": {
                                        "type": "string",
                                        "description": "Access token to revoke"
                                    },
                                    "token_type_hint": {
                                        "type": "string",
                                        "enum": ["access_token"],
                                        "description": "Optional hint about token type"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Token revoked successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {
                                            "type": "boolean",
                                            "example": True
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "security": []
            }
        }
        
        # Add registered endpoints
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
        
        # Add error schema
        spec["components"]["schemas"]["Error"] = {
            "type": "object",
            "properties": {
                "error": {"type": "string"},
                "error_description": {"type": "string"}
            }
        }
        
        return request.make_json_response(spec)
