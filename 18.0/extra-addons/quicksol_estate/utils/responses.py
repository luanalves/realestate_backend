# -*- coding: utf-8 -*-

from odoo.http import request


def success_response(data, message=None, links=None, status_code=200):

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

    response = {
        'success': False,
        'message': message
    }
    
    if errors:
        response['errors'] = errors
    
    return response, status_code


def paginated_response(items, total, page, page_size, links=None):

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

    if request:
        return request.httprequest.url_root.rstrip('/')
    return ''


def build_pagination_links(base_url, page, total_pages, query_params=None):

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
