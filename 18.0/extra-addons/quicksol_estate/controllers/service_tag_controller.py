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


def _serialize_tag(tag):
    return {
        'id': tag.id,
        'name': tag.name,
        'color': tag.color,
        'is_system': tag.is_system,
        'active': tag.active,
        'links': [
            {'rel': 'self', 'href': f'/api/v1/service-tags/{tag.id}', 'method': 'GET'},
            {'rel': 'update', 'href': f'/api/v1/service-tags/{tag.id}', 'method': 'PUT'},
            {'rel': 'delete', 'href': f'/api/v1/service-tags/{tag.id}', 'method': 'DELETE'},
        ],
    }


class ServiceTagController(http.Controller):

    @http.route('/api/v1/service-tags', type='http', auth='none', methods=['GET'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def list_tags(self, **kwargs):
        try:
            tags = request.env['real.estate.service.tag'].search([])
            return success_response([_serialize_tag(t) for t in tags])
        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except Exception:
            _logger.exception('Unexpected error in list_tags')
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    @http.route('/api/v1/service-tags', type='http', auth='none', methods=['POST'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def create_tag(self, **kwargs):
        try:
            if not _is_manager_or_owner(request.env):
                return error_response('FORBIDDEN', 'Only Owner/Manager can create tags.', 403)
            body = json.loads(request.httprequest.data or '{}')
            if not body.get('name'):
                return error_response('VALIDATION_ERROR', 'name is required.', 400)
            vals = {
                'name': body['name'],
                'company_id': request.env.company.id,
            }
            if body.get('color'):
                vals['color'] = body['color']
            tag = request.env['real.estate.service.tag'].create(vals)
            return success_response(_serialize_tag(tag), status_code=201)
        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except (ValidationError, UserError) as exc:
            return error_response('VALIDATION_ERROR', str(exc), 422)
        except Exception:
            _logger.exception('Unexpected error in create_tag')
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    @http.route('/api/v1/service-tags/<int:tag_id>', type='http', auth='none', methods=['GET'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def get_tag(self, tag_id, **kwargs):
        try:
            tag = request.env['real.estate.service.tag'].browse(tag_id)
            if not tag.exists():
                return error_response('NOT_FOUND', 'Tag not found.', 404)
            return success_response(_serialize_tag(tag))
        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except Exception:
            _logger.exception('Unexpected error in get_tag id=%d', tag_id)
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    @http.route('/api/v1/service-tags/<int:tag_id>', type='http', auth='none', methods=['PUT'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def update_tag(self, tag_id, **kwargs):
        try:
            if not _is_manager_or_owner(request.env):
                return error_response('FORBIDDEN', 'Only Owner/Manager can update tags.', 403)
            tag = request.env['real.estate.service.tag'].browse(tag_id)
            if not tag.exists():
                return error_response('NOT_FOUND', 'Tag not found.', 404)
            if tag.is_system:
                return error_response('FORBIDDEN', 'System tags are immutable.', 403)
            body = json.loads(request.httprequest.data or '{}')
            vals = {}
            if 'name' in body:
                vals['name'] = body['name']
            if 'color' in body:
                vals['color'] = body['color']
            tag.write(vals)
            return success_response(_serialize_tag(tag))
        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except (ValidationError, UserError) as exc:
            return error_response('VALIDATION_ERROR', str(exc), 422)
        except Exception:
            _logger.exception('Unexpected error in update_tag id=%d', tag_id)
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    @http.route('/api/v1/service-tags/<int:tag_id>', type='http', auth='none', methods=['DELETE'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def delete_tag(self, tag_id, **kwargs):
        try:
            if not _is_manager_or_owner(request.env):
                return error_response('FORBIDDEN', 'Only Owner/Manager can delete tags.', 403)
            tag = request.env['real.estate.service.tag'].browse(tag_id)
            if not tag.exists():
                return error_response('NOT_FOUND', 'Tag not found.', 404)
            if tag.is_system:
                return error_response('FORBIDDEN', 'System tags cannot be deleted.', 403)
            tag.write({'active': False})  # FR-019: soft delete
            return success_response(_serialize_tag(tag))
        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except (ValidationError, UserError) as exc:
            return error_response('VALIDATION_ERROR', str(exc), 422)
        except Exception:
            _logger.exception('Unexpected error in delete_tag id=%d', tag_id)
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)
