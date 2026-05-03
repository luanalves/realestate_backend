# -*- coding: utf-8 -*-

import json
import logging

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError, ValidationError

from .utils.auth import require_jwt
from .utils.response import error_response, success_response
from odoo.addons.thedevkitchen_apigateway.middleware import require_session, require_company
from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request

_logger = logging.getLogger(__name__)

_MANAGER_GROUPS = (
    'quicksol_estate.group_real_estate_owner',
    'quicksol_estate.group_real_estate_manager',
)


def _is_manager_or_owner(env):
    return any(env.user.has_group(g) for g in _MANAGER_GROUPS)


def _serialize_source(source):
    return {
        'id': source.id,
        'name': source.name,
        'code': source.code,
        'active': source.active,
        'links': [
            {'rel': 'self', 'href': f'/api/v1/service-sources/{source.id}', 'method': 'GET'},
            {'rel': 'update', 'href': f'/api/v1/service-sources/{source.id}', 'method': 'PUT'},
            {'rel': 'delete', 'href': f'/api/v1/service-sources/{source.id}', 'method': 'DELETE'},
        ],
    }


class ServiceSourceController(http.Controller):

    @http.route('/api/v1/service-sources', type='http', auth='none', methods=['GET'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def list_sources(self, **kwargs):
        try:
            sources = request.env['real.estate.service.source'].search([])
            return success_response([_serialize_source(s) for s in sources])
        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except Exception:
            _logger.exception('Unexpected error in list_sources')
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    @http.route('/api/v1/service-sources', type='http', auth='none', methods=['POST'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def create_source(self, **kwargs):
        try:
            if not _is_manager_or_owner(request.env):
                return error_response('FORBIDDEN', 'Only Owner/Manager can create sources.', 403)
            body = json.loads(request.httprequest.data or '{}')
            if not body.get('name') or not body.get('code'):
                return error_response('VALIDATION_ERROR', 'name and code are required.', 400)
            vals = {
                'name': body['name'],
                'code': body['code'].lower().strip(),
                'company_id': request.env.company.id,
            }
            source = request.env['real.estate.service.source'].create(vals)
            return success_response(_serialize_source(source), status_code=201)
        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except (ValidationError, UserError) as exc:
            return error_response('VALIDATION_ERROR', str(exc), 422)
        except Exception:
            _logger.exception('Unexpected error in create_source')
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    @http.route('/api/v1/service-sources/<int:source_id>', type='http', auth='none', methods=['GET'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def get_source(self, source_id, **kwargs):
        try:
            source = request.env['real.estate.service.source'].browse(source_id)
            if not source.exists():
                return error_response('NOT_FOUND', 'Source not found.', 404)
            return success_response(_serialize_source(source))
        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except Exception:
            _logger.exception('Unexpected error in get_source id=%d', source_id)
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    @http.route('/api/v1/service-sources/<int:source_id>', type='http', auth='none', methods=['PUT'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def update_source(self, source_id, **kwargs):
        try:
            if not _is_manager_or_owner(request.env):
                return error_response('FORBIDDEN', 'Only Owner/Manager can update sources.', 403)
            source = request.env['real.estate.service.source'].browse(source_id)
            if not source.exists():
                return error_response('NOT_FOUND', 'Source not found.', 404)
            body = json.loads(request.httprequest.data or '{}')
            vals = {}
            if 'name' in body:
                vals['name'] = body['name']
            if 'code' in body:
                vals['code'] = body['code'].lower().strip()
            source.write(vals)
            return success_response(_serialize_source(source))
        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except (ValidationError, UserError) as exc:
            return error_response('VALIDATION_ERROR', str(exc), 422)
        except Exception:
            _logger.exception('Unexpected error in update_source id=%d', source_id)
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    @http.route('/api/v1/service-sources/<int:source_id>', type='http', auth='none', methods=['DELETE'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def delete_source(self, source_id, **kwargs):
        try:
            if not _is_manager_or_owner(request.env):
                return error_response('FORBIDDEN', 'Only Owner/Manager can delete sources.', 403)
            source = request.env['real.estate.service.source'].browse(source_id)
            if not source.exists():
                return error_response('NOT_FOUND', 'Source not found.', 404)
            source.write({'active': False})  # soft delete
            return success_response(_serialize_source(source))
        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except (ValidationError, UserError) as exc:
            return error_response('VALIDATION_ERROR', str(exc), 422)
        except Exception:
            _logger.exception('Unexpected error in delete_source id=%d', source_id)
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)
