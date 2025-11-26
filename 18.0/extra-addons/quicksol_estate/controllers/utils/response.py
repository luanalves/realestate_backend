# -*- coding: utf-8 -*-
from odoo.http import request


def error_response(status_code, message, error_type='error'):
    """
    Helper to return standardized JSON error response.
    
    Args:
        status_code: HTTP status code (400, 401, 404, 500, etc.)
        message: Error message to display
        error_type: Type of error (default: 'error')
        
    Returns:
        JSON response with error details
        
    Example:
        return error_response(404, 'Property not found')
    """
    return request.make_json_response({
        'error': error_type,
        'message': message,
        'code': status_code
    }, status=status_code)


def success_response(data, status_code=200):
    """
    Helper to return standardized JSON success response.
    
    Args:
        data: Data to return (dict, list, etc.)
        status_code: HTTP status code (default: 200)
        
    Returns:
        JSON response with data
        
    Example:
        return success_response({'id': 1, 'name': 'Property'}, 201)
    """
    return request.make_json_response(data, status=status_code)
