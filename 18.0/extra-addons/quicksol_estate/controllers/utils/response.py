# -*- coding: utf-8 -*-
from odoo.http import request


def error_response(arg1, arg2=None, arg3='error'):

    # Detect argument order by finding which arg is an int
    if isinstance(arg1, int):
        status_code, message, error_type = arg1, str(arg2), str(arg3)
    elif isinstance(arg2, int):
        status_code, message, error_type = arg2, str(arg1), str(arg3)
    elif isinstance(arg3, int):
        status_code, message, error_type = arg3, str(arg2), str(arg1)
    else:
        # Fallback: arg1=status_code (might be numeric string), arg2=message
        try:
            status_code = int(arg1)
            message, error_type = str(arg2), str(arg3)
        except (ValueError, TypeError):
            status_code, message, error_type = 500, str(arg1), str(arg2 or 'error')

    return request.make_json_response({
        'error': error_type,
        'message': message,
        'code': status_code
    }, status=status_code)


def success_response(data, status_code=200):

    return request.make_json_response(data, status=status_code)
