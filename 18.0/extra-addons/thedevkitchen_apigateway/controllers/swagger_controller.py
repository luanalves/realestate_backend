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
        swagger_path = get_module_resource('thedevkitchen_apigateway', 'static', 'src', 'swagger.html')
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
        
        # User Authentication endpoints
        spec["paths"]["/api/v1/users/login"] = {
            "post": {
                "tags": ["User Authentication"],
                "summary": "User login",
                "description": "Authenticate user with email and password. Requires valid OAuth 2.0 Bearer token (app must be registered).",
                "operationId": "userLogin",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["email", "password"],
                                "properties": {
                                    "email": {
                                        "type": "string",
                                        "format": "email",
                                        "description": "User email",
                                        "example": "joao@imobiliaria.com"
                                    },
                                    "password": {
                                        "type": "string",
                                        "format": "password",
                                        "description": "User password",
                                        "example": "joao123"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Login successful",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "session_id": {
                                            "type": "string",
                                            "description": "Session ID for subsequent API requests"
                                        },
                                        "user": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer", "description": "User ID"},
                                                "name": {"type": "string", "description": "User full name"},
                                                "email": {"type": "string", "description": "User email"},
                                                "companies": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "id": {"type": "integer"},
                                                            "name": {"type": "string"},
                                                            "cnpj": {"type": "string"}
                                                        }
                                                    },
                                                    "description": "List of companies assigned to user"
                                                },
                                                "default_company_id": {
                                                    "type": "integer",
                                                    "description": "Default company ID"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid input",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    },
                    "401": {
                        "description": "Unauthorized - Invalid credentials or missing Bearer token",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    },
                    "403": {
                        "description": "Forbidden - User inactive or no companies assigned",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    },
                    "429": {
                        "description": "Too Many Requests - Rate limit exceeded (5 attempts per 15 minutes)",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        }
        
        spec["paths"]["/api/v1/users/logout"] = {
            "post": {
                "tags": ["User Authentication"],
                "summary": "User logout",
                "description": "Logout user and invalidate session. Requires valid OAuth 2.0 Bearer token (app must be registered).",
                "operationId": "userLogout",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["session_id"],
                                "properties": {
                                    "session_id": {
                                        "type": "string",
                                        "description": "Session ID from login response",
                                        "example": "HP_Z_RlS6Y4APZWM99gWfq53aezjyBCSwW46UDVC5Wn2xlzruc6cU0bpgJzHCRH0Z8"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Logout successful",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "message": {
                                            "type": "string",
                                            "example": "Logged out successfully"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid input - Missing session_id",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    },
                    "401": {
                        "description": "Unauthorized - Invalid session or missing Bearer token",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        }
        
        # Add /me endpoint
        spec["paths"]["/api/v1/me"] = {
            "get": {
                "tags": ["User Authentication"],
                "summary": "Get current user profile",
                "description": "Returns authenticated user information including companies. Requires valid session and Bearer token.",
                "operationId": "getCurrentUser",
                "responses": {
                    "200": {
                        "description": "User profile retrieved successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "user": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer", "example": 8},
                                                "name": {"type": "string", "example": "João Silva"},
                                                "email": {"type": "string", "example": "joao@imobiliaria.com"},
                                                "login": {"type": "string", "example": "joao@imobiliaria.com"},
                                                "phone": {"type": "string", "example": "11999998888"},
                                                "mobile": {"type": "string", "example": "11988887777"},
                                                "companies": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "id": {"type": "integer", "example": 1},
                                                            "name": {"type": "string", "example": "Imobiliária A"},
                                                            "cnpj": {"type": "string", "example": "12.345.678/0001-90"},
                                                            "email": {"type": "string"},
                                                            "phone": {"type": "string"},
                                                            "website": {"type": "string"}
                                                        }
                                                    }
                                                },
                                                "default_company_id": {"type": "integer", "example": 1},
                                                "is_admin": {"type": "boolean", "example": False},
                                                "active": {"type": "boolean", "example": True}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "401": {
                        "description": "Unauthorized - Invalid or missing session/token",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    },
                    "500": {
                        "description": "Internal server error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
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
        
        # Add schemas
        spec["components"]["schemas"]["Error"] = {
            "type": "object",
            "properties": {
                "error": {"type": "string"},
                "error_description": {"type": "string"}
            }
        }
        
        # Add Property schemas
        spec["components"]["schemas"]["PropertyCreate"] = {
            "type": "object",
            "required": ["name", "property_type_id", "area", "zip_code", "state_id", "city", "street", "street_number", "location_type_id"],
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nome da propriedade",
                    "example": "Apartamento Moderno no Centro"
                },
                "description": {
                    "type": "string",
                    "description": "Descrição detalhada da propriedade",
                    "example": "Lindo apartamento de 3 quartos com vista para o mar, próximo a todos os serviços"
                },
                "property_type_id": {
                    "type": "integer",
                    "description": "ID do tipo de propriedade (1=Casa, 2=Apartamento, 3=Terreno, etc)",
                    "example": 2
                },
                "property_status": {
                    "type": "string",
                    "enum": ["available", "occupied", "rented", "reserved", "sold", "under_construction", "maintenance"],
                    "description": "Status da propriedade",
                    "example": "available"
                },
                "property_purpose": {
                    "type": "string",
                    "enum": ["residential", "commercial", "industrial", "rural", "vacation", "corporate"],
                    "description": "Finalidade da propriedade (tipo de uso)",
                    "example": "residential"
                },
                "price": {
                    "type": "number",
                    "format": "float",
                    "description": "Preço de venda em reais",
                    "example": 450000.00
                },
                "rent_price": {
                    "type": "number",
                    "format": "float",
                    "description": "Preço de aluguel mensal em reais",
                    "example": 2500.00
                },
                "area": {
                    "type": "number",
                    "format": "float",
                    "description": "Área útil em metros quadrados (obrigatório)",
                    "example": 85.50
                },
                "total_area": {
                    "type": "number",
                    "format": "float",
                    "description": "Área total em metros quadrados",
                    "example": 120.00
                },
                "num_rooms": {
                    "type": "integer",
                    "description": "Número de quartos",
                    "example": 3
                },
                "num_suites": {
                    "type": "integer",
                    "description": "Número de suítes",
                    "example": 1
                },
                "num_bathrooms": {
                    "type": "integer",
                    "description": "Número de banheiros",
                    "example": 2
                },
                "num_parking": {
                    "type": "integer",
                    "description": "Número de vagas de garagem",
                    "example": 2
                },
                "zip_code": {
                    "type": "string",
                    "description": "CEP (obrigatório)",
                    "example": "88015-901"
                },
                "state_id": {
                    "type": "integer",
                    "description": "ID do estado (obrigatório) - res.country.state",
                    "example": 24
                },
                "city": {
                    "type": "string",
                    "description": "Cidade (obrigatório)",
                    "example": "Florianópolis"
                },
                "neighborhood": {
                    "type": "string",
                    "description": "Bairro",
                    "example": "Centro"
                },
                "street": {
                    "type": "string",
                    "description": "Rua (obrigatório)",
                    "example": "Rua Felipe Schmidt"
                },
                "street_number": {
                    "type": "string",
                    "description": "Número (obrigatório)",
                    "example": "515"
                },
                "complement": {
                    "type": "string",
                    "description": "Complemento",
                    "example": "Apto 301"
                },
                "location_type_id": {
                    "type": "integer",
                    "description": "ID do tipo de localização (obrigatório) - real.estate.location.type",
                    "example": 1
                },
                "latitude": {
                    "type": "number",
                    "format": "float",
                    "description": "Latitude para geolocalização",
                    "example": -27.5969
                },
                "longitude": {
                    "type": "number",
                    "format": "float",
                    "description": "Longitude para geolocalização",
                    "example": -48.5495
                },
                "condition": {
                    "type": "string",
                    "enum": ["new", "excellent", "good", "fair", "needs_renovation", "under_construction"],
                    "description": "Condição do imóvel",
                    "example": "good"
                },
                "construction_year": {
                    "type": "integer",
                    "description": "Ano de construção",
                    "example": 2018
                },
                "for_sale": {
                    "type": "boolean",
                    "description": "Disponível para venda",
                    "example": True
                },
                "for_rent": {
                    "type": "boolean",
                    "description": "Disponível para locação",
                    "example": True
                },
                "accepts_financing": {
                    "type": "boolean",
                    "description": "Aceita financiamento",
                    "example": True
                },
                "accepts_fgts": {
                    "type": "boolean",
                    "description": "Aceita FGTS",
                    "example": True
                },
                "agent_id": {
                    "type": "integer",
                    "description": "ID do corretor responsável - res.users",
                    "example": 2
                },
                "owner_id": {
                    "type": "integer",
                    "description": "ID do proprietário - real.estate.property.owner (opcional)",
                    "example": 1
                },
                "company_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "IDs das empresas vinculadas",
                    "example": [1]
                },
                "building_id": {
                    "type": "integer",
                    "description": "ID do edifício/condomínio - real.estate.property.building"
                },
                "floor_number": {
                    "type": "integer",
                    "description": "Número do andar",
                    "example": 5
                },
                "unit_number": {
                    "type": "string",
                    "description": "Número da unidade",
                    "example": "501"
                },
                "num_floors": {
                    "type": "integer",
                    "description": "Número de andares do imóvel",
                    "example": 2
                },
                "private_area": {
                    "type": "number",
                    "format": "float",
                    "description": "Área privativa em m²",
                    "example": 75.00
                },
                "land_area": {
                    "type": "number",
                    "format": "float",
                    "description": "Área do terreno em m²",
                    "example": 300.00
                },
                "iptu_annual": {
                    "type": "number",
                    "format": "float",
                    "description": "IPTU anual",
                    "example": 1200.00
                },
                "insurance_value": {
                    "type": "number",
                    "format": "float",
                    "description": "Valor do seguro",
                    "example": 500.00
                },
                "condominium_fee": {
                    "type": "number",
                    "format": "float",
                    "description": "Taxa de condomínio mensal",
                    "example": 350.00
                },
                "authorization_start_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Data de início da autorização",
                    "example": "2025-01-01"
                },
                "authorization_end_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Data de término da autorização",
                    "example": "2025-12-31"
                },
                "reform_year": {
                    "type": "integer",
                    "description": "Ano da reforma",
                    "example": 2020
                },
                "zoning_type": {
                    "type": "string",
                    "enum": ["residential", "commercial", "mixed", "industrial", "agricultural"],
                    "description": "Tipo de zoneamento"
                },
                "zoning_restrictions": {
                    "type": "string",
                    "description": "Restrições de zoneamento"
                },
                "tag_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "IDs das tags - real.estate.property.tag (opcional - use apenas IDs existentes)",
                    "example": []
                },
                "amenities": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "IDs das amenidades - real.estate.amenity (opcional - use apenas IDs existentes)",
                    "example": []
                },
                "publish_website": {
                    "type": "boolean",
                    "description": "Publicar no site",
                    "example": True
                },
                "publish_featured": {
                    "type": "boolean",
                    "description": "Imóvel em destaque",
                    "example": False
                },
                "publish_super_featured": {
                    "type": "boolean",
                    "description": "Imóvel super destaque",
                    "example": False
                },
                "youtube_video_url": {
                    "type": "string",
                    "description": "URL do vídeo no YouTube",
                    "example": "https://youtube.com/watch?v=..."
                },
                "virtual_tour_url": {
                    "type": "string",
                    "description": "URL do tour virtual",
                    "example": "https://..."
                },
                "meta_title": {
                    "type": "string",
                    "description": "Título SEO (máx 60 caracteres)",
                    "example": "Apartamento 3 quartos no Centro"
                },
                "meta_description": {
                    "type": "string",
                    "description": "Descrição SEO (máx 160 caracteres)",
                    "example": "Lindo apartamento com vista mar"
                },
                "meta_keywords": {
                    "type": "string",
                    "description": "Palavras-chave SEO",
                    "example": "apartamento, centro, vista mar"
                },
                "description_short": {
                    "type": "string",
                    "description": "Descrição curta (máx 250 caracteres)",
                    "example": "Apartamento moderno em localização privilegiada"
                },
                "internal_notes": {
                    "type": "string",
                    "description": "Notas internas (confidencial)"
                },
                "has_sign": {
                    "type": "boolean",
                    "description": "Possui placa/faixa",
                    "example": True
                },
                "sign_type": {
                    "type": "string",
                    "enum": ["sale", "rent", "sold", "rented"],
                    "description": "Tipo de placa"
                },
                "sign_installation_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Data de instalação da placa",
                    "example": "2025-01-15"
                },
                "sign_removal_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Data de remoção da placa"
                },
                "sign_notes": {
                    "type": "string",
                    "description": "Notas sobre a placa"
                },
                "matricula_number": {
                    "type": "string",
                    "description": "Número da matrícula",
                    "example": "12345"
                },
                "iptu_code": {
                    "type": "string",
                    "description": "Código do IPTU",
                    "example": "123.456.789-0"
                },
                "origin_media": {
                    "type": "string",
                    "enum": ["website", "social_media", "referral", "walk_in", "phone", "email", "partner", "other"],
                    "description": "Mídia de origem",
                    "example": "website"
                }
            }
        }
        
        spec["components"]["schemas"]["PropertyResponse"] = {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "example": 42},
                "name": {"type": "string", "example": "Apartamento Moderno no Centro"},
                "description": {"type": "string"},
                "price": {"type": "number", "example": 450000.00},
                "price_formatted": {"type": "string", "example": "R$ 450.000,00"},
                "status": {"type": "string", "example": "available"},
                "property_type": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"}
                    }
                },
                "agent": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string"}
                    }
                },
                "area": {"type": "number"},
                "num_rooms": {"type": "integer"},
                "num_bathrooms": {"type": "integer"},
                "created_at": {"type": "string", "format": "date-time"},
                "updated_at": {"type": "string", "format": "date-time"}
            }
        }
        
        # Override /api/v1/properties POST endpoint with detailed schema
        if "/api/v1/properties" in spec["paths"]:
            if "post" in spec["paths"]["/api/v1/properties"]:
                spec["paths"]["/api/v1/properties"]["post"]["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/PropertyCreate"}
                        }
                    }
                }
                spec["paths"]["/api/v1/properties"]["post"]["responses"]["201"] = {
                    "description": "Propriedade criada com sucesso",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/PropertyResponse"}
                        }
                    }
                }
        
        # Add Master Data endpoints documentation
        master_data_endpoints = {
            "/api/v1/agents": {
                "get": {
                    "tags": ["Master Data"],
                    "summary": "List all agents",
                    "description": "Get list of all active real estate agents",
                    "responses": {
                        "200": {
                            "description": "List of agents",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                                "email": {"type": "string"},
                                                "phone": {"type": "string"},
                                                "mobile": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/owners": {
                "get": {
                    "tags": ["Master Data"],
                    "summary": "List all property owners",
                    "description": "Get list of all active property owners",
                    "responses": {
                        "200": {
                            "description": "List of owners",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                                "cpf": {"type": "string"},
                                                "cnpj": {"type": "string"},
                                                "email": {"type": "string"},
                                                "phone": {"type": "string"},
                                                "mobile": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/companies": {
                "get": {
                    "tags": ["Master Data"],
                    "summary": "List all real estate companies",
                    "description": "Get list of all active real estate companies",
                    "responses": {
                        "200": {
                            "description": "List of companies",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                                "email": {"type": "string"},
                                                "phone": {"type": "string"},
                                                "website": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/tags": {
                "get": {
                    "tags": ["Master Data"],
                    "summary": "List all property tags",
                    "description": "Get list of all active property tags",
                    "responses": {
                        "200": {
                            "description": "List of tags",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                                "color": {"type": "integer"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/amenities": {
                "get": {
                    "tags": ["Master Data"],
                    "summary": "List all amenities",
                    "description": "Get list of all active property amenities",
                    "responses": {
                        "200": {
                            "description": "List of amenities",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                                "icon": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        spec["paths"]["/api/v1/users/profile"] = {
            "patch": {
                "tags": ["User Authentication"],
                "summary": "Update user profile",
                "description": "Partially update logged-in user profile (email, phone, mobile). Requires Bearer token. Only own profile can be updated.",
                "operationId": "patchUserProfile",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "email": {
                                        "type": "string",
                                        "format": "email",
                                        "description": "User email (must be unique)",
                                        "example": "joao.silva@example.com"
                                    },
                                    "phone": {
                                        "type": "string",
                                        "description": "User phone number",
                                        "example": "1133334444"
                                    },
                                    "mobile": {
                                        "type": "string",
                                        "description": "User mobile number",
                                        "example": "11999998888"
                                    }
                                },
                                "description": "At least one field must be provided"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Profile updated successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "user": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                                "email": {"type": "string"},
                                                "phone": {"type": "string"},
                                                "mobile": {"type": "string"},
                                                "companies": {"type": "array"},
                                                "default_company_id": {"type": "integer"}
                                            }
                                        },
                                        "message": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid input",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}
                    },
                    "401": {
                        "description": "Unauthorized",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}
                    },
                    "409": {
                        "description": "Conflict - Email already in use",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}
                    }
                }
            }
        }
        
        spec["paths"]["/api/v1/users/change-password"] = {
            "post": {
                "tags": ["User Authentication"],
                "summary": "Change user password",
                "description": "Change logged-in user password. Requires current password and new password confirmation. Min 8 characters.",
                "operationId": "changeUserPassword",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["current_password", "new_password", "confirm_password"],
                                "properties": {
                                    "current_password": {
                                        "type": "string",
                                        "format": "password",
                                        "description": "Current user password",
                                        "example": "OldPass123!@"
                                    },
                                    "new_password": {
                                        "type": "string",
                                        "format": "password",
                                        "description": "New password (min 8 characters)",
                                        "example": "NewPass123!@"
                                    },
                                    "confirm_password": {
                                        "type": "string",
                                        "format": "password",
                                        "description": "Confirm new password (must match new_password)",
                                        "example": "NewPass123!@"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Password changed successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "message": {"type": "string", "example": "Password changed successfully"}
                                    }
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid input - Missing fields, passwords don't match, or too short",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}
                    },
                    "401": {
                        "description": "Unauthorized - Current password incorrect or invalid token",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}
                    },
                    "500": {
                        "description": "Internal server error",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}
                    }
                }
            }
        }
        
        # Merge master data endpoints into spec
        for path, methods in master_data_endpoints.items():
            if path not in spec["paths"]:
                spec["paths"][path] = {}
            spec["paths"][path].update(methods)
        
        return request.make_json_response(spec)
