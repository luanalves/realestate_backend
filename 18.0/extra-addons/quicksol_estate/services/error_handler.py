# -*- coding: utf-8 -*-

from odoo import _
from odoo.http import request
import logging
import traceback

_logger = logging.getLogger(__name__)


class ErrorHandler:

    @staticmethod
    def validation_error(message, field=None, details=None):

        error_response = {
            'error': 'validation_error',
            'message': str(message),
            'status': 400
        }
        
        if field:
            error_response['field'] = field
            
        if details:
            error_response['details'] = details
            
        _logger.warning(f"Validation error: {message} (field: {field})")
        return request.make_json_response(error_response, status=400)
    
    @staticmethod
    def not_found(resource, resource_id=None):

        message = _("%(resource)s not found") % {'resource': resource.capitalize()}
        if resource_id:
            message = _("%(resource)s with ID %(id)s not found") % {
                'resource': resource.capitalize(),
                'id': resource_id
            }
            
        error_response = {
            'error': 'not_found',
            'message': message,
            'status': 404
        }
        
        _logger.info(f"Resource not found: {resource} (ID: {resource_id})")
        return request.make_json_response(error_response, status=404)
    
    @staticmethod
    def unauthorized(message=None):

        error_response = {
            'error': 'unauthorized',
            'message': message or _("Authentication required"),
            'status': 401
        }
        
        _logger.warning(f"Unauthorized access: {message}")
        return request.make_json_response(error_response, status=401)
    
    @staticmethod
    def forbidden(message=None, reason=None):

        error_response = {
            'error': 'forbidden',
            'message': message or _("Access denied"),
            'status': 403
        }
        
        if reason:
            error_response['reason'] = reason
            
        _logger.warning(f"Forbidden access: {message} (reason: {reason})")
        return request.make_json_response(error_response, status=403)
    
    @staticmethod
    def conflict(message, resource=None):

        error_response = {
            'error': 'conflict',
            'message': str(message),
            'status': 409
        }
        
        if resource:
            error_response['resource'] = resource
            
        _logger.warning(f"Conflict: {message}")
        return request.make_json_response(error_response, status=409)
    
    @staticmethod
    def server_error(message=None, exception=None, include_trace=False):

        error_response = {
            'error': 'internal_server_error',
            'message': message or _("An unexpected error occurred"),
            'status': 500
        }
        
        if exception:
            _logger.error(f"Server error: {message}", exc_info=exception)
            
            if include_trace:
                error_response['exception'] = str(exception)
                error_response['trace'] = traceback.format_exc()
        else:
            _logger.error(f"Server error: {message}")
            
        return request.make_json_response(error_response, status=500)
    
    @staticmethod
    def method_not_allowed(method, allowed_methods=None):

        message = _("Method %(method)s not allowed") % {'method': method}
        
        error_response = {
            'error': 'method_not_allowed',
            'message': message,
            'status': 405
        }
        
        if allowed_methods:
            error_response['allowed_methods'] = allowed_methods
            
        _logger.warning(f"Method not allowed: {method}")
        return request.make_json_response(error_response, status=405)
    
    @staticmethod
    def bad_request(message, error_code=None):

        error_response = {
            'error': error_code or 'bad_request',
            'message': str(message),
            'status': 400
        }
        
        _logger.warning(f"Bad request: {message}")
        return request.make_json_response(error_response, status=400)
    
    @staticmethod
    def too_many_requests(message=None, retry_after=None):

        error_response = {
            'error': 'too_many_requests',
            'message': message or _("Rate limit exceeded"),
            'status': 429
        }
        
        if retry_after:
            error_response['retry_after'] = retry_after
            
        _logger.warning(f"Rate limit exceeded: {message}")
        return request.make_json_response(error_response, status=429)


# Convenience function for handling exceptions in controllers
def handle_exception(func):

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return ErrorHandler.validation_error(str(e))
        except KeyError as e:
            return ErrorHandler.bad_request(f"Missing required field: {str(e)}")
        except Exception as e:
            return ErrorHandler.server_error(exception=e)
    return wrapper
