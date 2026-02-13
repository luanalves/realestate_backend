# -*- coding: utf-8 -*-
"""
Schema Validation Utilities

Provides request/response schema validation for API endpoints.
Ensures API contracts are enforced per ADR-005 (OpenAPI 3.0).

Author: Quicksol Technologies
Date: 2026-01-15
"""

from odoo import _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class SchemaValidator:
    """
    Validates request and response data against schema definitions.
    Ensures API contracts are maintained and data integrity is preserved.
    """
    
    # Agent creation schema
    AGENT_CREATE_SCHEMA = {
        'required': ['name', 'cpf', 'company_id', 'email'],
        'optional': ['phone', 'mobile', 'creci', 'hire_date', 'bank_name', 'bank_account', 'pix_key'],
        'types': {
            'name': str,
            'cpf': str,
            'email': str,
            'phone': str,
            'mobile': str,
            'creci': str,
            'hire_date': str,
            'bank_name': str,
            'bank_account': str,
            'pix_key': str,
            'company_id': int,
        },
        'constraints': {
            'name': lambda v: len(v) >= 3 and len(v) <= 255,
            'cpf': lambda v: len(v.replace('.', '').replace('-', '')) == 11,
            'email': lambda v: '@' in v and '.' in v,
            'creci': lambda v: len(v) >= 4,
        }
    }
    
    # Agent update schema
    AGENT_UPDATE_SCHEMA = {
        'required': [],
        'optional': ['name', 'email', 'phone', 'mobile', 'creci', 'bank_name', 'bank_account', 'pix_key'],
        'types': {
            'name': str,
            'email': str,
            'phone': str,
            'mobile': str,
            'creci': str,
            'bank_name': str,
            'bank_account': str,
            'pix_key': str,
        },
        'constraints': {
            'name': lambda v: len(v) >= 3 if v else True,
            'cpf': lambda v: len(v.replace('.', '').replace('-', '')) == 11 if v else True,
            'email': lambda v: '@' in v and '.' in v if v else True,
        }
    }
    
    # Assignment schema
    ASSIGNMENT_CREATE_SCHEMA = {
        'required': ['agent_id', 'property_id'],
        'optional': ['responsibility_type', 'notes'],
        'types': {
            'agent_id': int,
            'property_id': int,
            'responsibility_type': str,
            'notes': str,
        },
        'constraints': {
            'agent_id': lambda v: v > 0,
            'property_id': lambda v: v > 0,
            'responsibility_type': lambda v: v in ['primary', 'secondary', 'support'] if v else True,
        }
    }
    
    # Performance metrics schema
    PERFORMANCE_SCHEMA = {
        'required': ['agent_id'],
        'optional': ['start_date', 'end_date', 'metric'],
        'types': {
            'agent_id': int,
            'start_date': str,
            'end_date': str,
            'metric': str,
        },
        'constraints': {
            'agent_id': lambda v: v > 0,
            'metric': lambda v: v in ['sales', 'commission', 'properties'] if v else True,
        }
    }
    
    @staticmethod
    def validate_request(data, schema):
        """
        Validate request data against a schema.
        
        Args:
            data (dict): Request data to validate
            schema (dict): Schema definition with required, optional, types, constraints
            
        Returns:
            tuple: (is_valid: bool, errors: list of error messages)
        """
        errors = []
        
        # Check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Check field types
        types_def = schema.get('types', {})
        for field, field_type in types_def.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], field_type):
                    errors.append(f"Field '{field}' must be {field_type.__name__}, got {type(data[field]).__name__}")
        
        # Check constraints
        constraints = schema.get('constraints', {})
        for field, constraint in constraints.items():
            if field in data and data[field] is not None:
                try:
                    if not constraint(data[field]):
                        errors.append(f"Field '{field}' value '{data[field]}' violates constraint")
                except Exception as e:
                    errors.append(f"Field '{field}' validation error: {str(e)}")
        
        # Check for extra fields
        allowed_fields = set(schema.get('required', []) + schema.get('optional', []))
        extra_fields = set(data.keys()) - allowed_fields
        if extra_fields:
            _logger.debug(f"Extra fields in request (ignored): {', '.join(extra_fields)}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_agent_create(data):
        """Validate agent creation request."""
        return SchemaValidator.validate_request(data, SchemaValidator.AGENT_CREATE_SCHEMA)
    
    @staticmethod
    def validate_agent_update(data):
        """Validate agent update request."""
        return SchemaValidator.validate_request(data, SchemaValidator.AGENT_UPDATE_SCHEMA)
    
    @staticmethod
    def validate_assignment_create(data):
        """Validate assignment creation request."""
        return SchemaValidator.validate_request(data, SchemaValidator.ASSIGNMENT_CREATE_SCHEMA)
    
    @staticmethod
    def validate_performance_request(data):
        """Validate performance metrics request."""
        return SchemaValidator.validate_request(data, SchemaValidator.PERFORMANCE_SCHEMA)
    
    @staticmethod
    def build_response_schema(data, schema_type='agent'):
        """
        Build normalized response data according to schema.
        
        Args:
            data (dict or object): Data to normalize
            schema_type (str): Type of schema ('agent', 'assignment', 'performance')
            
        Returns:
            dict: Normalized response data
        """
        # This is where response transformation would happen
        # For now, just return the data as-is
        return data
