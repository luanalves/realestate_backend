# -*- coding: utf-8 -*-
"""
Response helper functions for REST API endpoints

Provides consistent response formatting with HATEOAS links following ADR-007.
All API responses follow the same structure for consistency.
"""
from odoo.http import request


def success_response(data, message=None, links=None, status_code=200):
    """
    Generate standardized success response with HAT EOAS links.
    
    Args:
        data (dict): Response payload data
        message (str, optional): Success message
        links (dict, optional): HATEOAS links {'rel': 'url'}
        status_code (int): HTTP status code (default: 200)
        
    Returns:
        tuple: (response_dict, status_code)
        
    Example:
        >>> success_response(
        ...     data={'id': 1, 'name': 'Test Company'},
        ...     message='Company created successfully',
        ...     links={'self': '/api/v1/companies/1', 'owners': '/api/v1/companies/1/owners'},
        ...     status_code=201
        ... )
    """
    response = {
        'success': True,
        'data': data
    }
    
    if message:
        response['message'] = message
    
    if links:
        response['_links'] = links
    
    return response, status_code


def error_response(message, errors=None, status_code=400):
    """
    Generate standardized error response.
    
    Args:
        message (str): Error message
        errors (dict, optional): Detailed error breakdown {'field': 'error description'}
        status_code (int): HTTP status code (default: 400)
        
    Returns:
        tuple: (response_dict, status_code)
        
    Example:
        >>> error_response(
        ...     message='Validation failed',
        ...     errors={'cnpj': 'Invalid CNPJ format', 'email': 'Email already exists'},
        ...     status_code=400
        ... )
    """
    response = {
        'success': False,
        'message': message
    }
    
    if errors:
        response['errors'] = errors
    
    return response, status_code


def paginated_response(items, total, page, page_size, links=None):
    """
    Generate paginated response with metadata.
    
    Args:
        items (list): List of items for current page
        total (int): Total number of items
        page (int): Current page number (1-indexed)
        page_size (int): Number of items per page
        links (dict, optional): HATEOAS pagination links
        
    Returns:
        tuple: (response_dict, status_code)
        
    Example:
        >>> paginated_response(
        ...     items=[{'id': 1}, {'id': 2}],
        ...     total=50,
        ...     page=1,
        ...     page_size=20,
        ...     links={'next': '/api/v1/owners?page=2', 'self': '/api/v1/owners?page=1'}
        ... )
    """
    total_pages = (total + page_size - 1) // page_size  # Ceiling division
    
    response = {
        'success': True,
        'data': items,
        'meta': {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        }
    }
    
    if links:
        response['_links'] = links
    
    return response, 200


def build_hateoas_links(base_url, resource_id=None, relations=None):
    """
    Build HATEOAS links for a resource.
    
    Args:
        base_url (str): Base URL of the resource (e.g., '/api/v1/companies')
        resource_id (int, optional): Resource ID for 'self' link
        relations (dict, optional): Additional relations {'rel_name': 'url_suffix'}
        
    Returns:
        dict: HATEOAS links dictionary
        
    Example:
        >>> build_hateoas_links(
        ...     base_url='/api/v1/companies',
        ...     resource_id=1,
        ...     relations={'owners': '/owners', 'properties': '/properties'}
        ... )
        {
            'self': '/api/v1/companies/1',
            'owners': '/api/v1/companies/1/owners',
            'properties': '/api/v1/companies/1/properties'
        }
    """
    links = {}
    
    if resource_id:
        links['self'] = f"{base_url}/{resource_id}"
    else:
        links['self'] = base_url
    
    if relations and resource_id:
        for rel_name, url_suffix in relations.items():
            links[rel_name] = f"{base_url}/{resource_id}{url_suffix}"
    
    return links


def get_base_url():
    """
    Get base URL from current request.
    
    Returns:
        str: Base URL (e.g., 'http://localhost:8069')
    """
    if request:
        return request.httprequest.url_root.rstrip('/')
    return ''


def build_pagination_links(base_url, page, total_pages, query_params=None):
    """
    Build pagination HATEOAS links.
    
    Args:
        base_url (str): Base URL without query parameters
        page (int): Current page number
        total_pages (int): Total number of pages
        query_params (dict, optional): Additional query parameters
        
    Returns:
        dict: Pagination links (self, first, last, next, prev)
        
    Example:
        >>> build_pagination_links('/api/v1/owners', page=2, total_pages=5)
        {
            'self': '/api/v1/owners?page=2',
            'first': '/api/v1/owners?page=1',
            'last': '/api/v1/owners?page=5',
            'next': '/api/v1/owners?page=3',
            'prev': '/api/v1/owners?page=1'
        }
    """
    def build_url(page_num):
        params = query_params.copy() if query_params else {}
        params['page'] = page_num
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    links = {
        'self': build_url(page),
        'first': build_url(1),
        'last': build_url(total_pages)
    }
    
    if page < total_pages:
        links['next'] = build_url(page + 1)
    
    if page > 1:
        links['prev'] = build_url(page - 1)
    
    return links
