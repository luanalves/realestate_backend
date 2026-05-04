# -*- coding: utf-8 -*-

import json
import logging
import math

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError, ValidationError

from .utils.auth import require_jwt
from .utils.response import error_response, success_response
from odoo.addons.thedevkitchen_apigateway.middleware import require_session, require_company
from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request

from ..services.partner_dedup_service import (
    find_or_create_partner, PartnerDeduplicationConflict
)
from ..services import service_pipeline_service as pipeline_svc

_logger = logging.getLogger(__name__)

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Ordering map (contract param → ORM order string)
ORDERING_MAP = {
    'pendency': 'last_activity_date asc, id asc',
    'recent': 'write_date desc, id desc',
    'oldest': 'create_date asc, id asc',
    'stage': 'stage asc, id asc',
}
DEFAULT_ORDERING = 'recent'

# Valid filter fields that map directly to ORM domain atoms
_DIRECT_FILTERS = {
    'stage': ('stage', '='),
    'operation_type': ('operation_type', '='),
    'agent_id': ('agent_id', '='),
    'source_id': ('source_id', '='),
    'is_pending': ('is_pending', '='),
    'is_orphan_agent': ('is_orphan_agent', '='),
}


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _load_schema(name):
    import os
    path = os.path.join(
        os.path.dirname(__file__),
        '..', 'schemas', f'{name}.json',
    )
    with open(os.path.realpath(path)) as f:
        return json.load(f)


def _validate_body(body, schema_name):
    """Validate request body against a JSON Schema file. Returns list of errors."""
    try:
        import jsonschema
        schema = _load_schema(schema_name)
        validator = jsonschema.Draft7Validator(schema)
        errors = sorted(validator.iter_errors(body), key=lambda e: e.path)
        return [
            {
                'field': '.'.join(str(p) for p in e.absolute_path) or str(e.schema_path[-1]),
                'message': e.message,
            }
            for e in errors
        ]
    except ImportError:
        _logger.warning('jsonschema not installed — skipping schema validation')
        return []


def _build_hateoas_links(service):
    base = f'/api/v1/services/{service.id}'
    return [
        {'rel': 'self', 'href': base, 'method': 'GET'},
        {'rel': 'update', 'href': base, 'method': 'PUT'},
        {'rel': 'delete', 'href': base, 'method': 'DELETE'},
        {'rel': 'stage', 'href': f'{base}/stage', 'method': 'PATCH'},
        {'rel': 'reassign', 'href': f'{base}/reassign', 'method': 'PATCH'},
    ]


def _serialize_service(service, include_messages=False):
    """Serialize a real.estate.service record to dict per openapi.yaml."""
    data = {
        'id': service.id,
        'name': service.name,
        'stage': service.stage,
        'operation_type': service.operation_type,
        'is_pending': service.is_pending,
        'is_orphan_agent': service.is_orphan_agent,
        'lost_reason': service.lost_reason or None,
        'won_date': service.won_date.isoformat() if service.won_date else None,
        'notes': service.notes or None,
        'client': {
            'id': service.client_partner_id.id,
            'name': service.client_partner_id.name,
            'email': service.client_partner_id.email or None,
            'phones': [
                {
                    'type': ph.phone_type,
                    'number': ph.number,
                    'is_primary': ph.is_primary,
                }
                for ph in service.client_partner_id.phone_ids
            ],
        },
        'agent': {
            'id': service.agent_id.id,
            'name': service.agent_id.name,
        } if service.agent_id else None,
        'lead_id': service.lead_id.id if service.lead_id else None,
        'source': {
            'id': service.source_id.id,
            'name': service.source_id.name,
            'code': service.source_id.code,
        } if service.source_id else None,
        'tags': [
            {'id': t.id, 'name': t.name, 'color': t.color, 'is_system': t.is_system}
            for t in service.tag_ids
        ],
        'properties': [
            {'id': p.id, 'name': p.name}
            for p in service.property_ids
        ],
        'last_activity_date': (
            service.last_activity_date.isoformat() if service.last_activity_date else None
        ),
        'created_at': service.create_date.isoformat() if service.create_date else None,
        'updated_at': service.write_date.isoformat() if service.write_date else None,
        'links': _build_hateoas_links(service),
    }
    return data


def _build_domain(params):
    """Build Odoo domain from query parameters."""
    domain = []

    for param, (field, operator) in _DIRECT_FILTERS.items():
        val = params.get(param)
        if val is not None:
            if isinstance(val, str) and val.lower() in ('true', 'false'):
                val = val.lower() == 'true'
            elif isinstance(val, str) and val.isdigit():
                val = int(val)
            domain.append((field, operator, val))

    # Multi-value filter: tag_ids
    tag_ids_raw = params.get('tag_ids')
    if tag_ids_raw:
        try:
            tag_ids = [int(t) for t in tag_ids_raw.split(',') if t.strip()]
            if tag_ids:
                domain += [('tag_ids', 'in', tag_ids)]
        except (ValueError, AttributeError):
            pass

    # archived filter
    archived = params.get('archived')
    if archived is not None and archived.lower() in ('true', '1'):
        domain.append(('active', '=', False))

    # Free-text search
    q = params.get('q', '').strip()
    if q:
        like = f'%{q}%'
        domain += ['|', '|', '|',
                   ('client_partner_id.name', 'ilike', q),
                   ('client_partner_id.email', 'ilike', q),
                   ('client_partner_id.phone_ids.number', 'ilike', q),
                   ('property_ids.name', 'ilike', q)]

    return domain


_MANAGER_GROUPS = (
    'quicksol_estate.group_real_estate_owner',
    'quicksol_estate.group_real_estate_manager',
)


def _is_manager_or_owner(env):
    user = env.user
    return any(user.has_group(g) for g in _MANAGER_GROUPS)


# --------------------------------------------------------------------------- #
# Controller                                                                   #
# --------------------------------------------------------------------------- #

class ServiceController(http.Controller):

    # ---------------------------------------------------------------------- #
    # POST /api/v1/services                                                   #
    # ---------------------------------------------------------------------- #
    @http.route('/api/v1/services', type='http', auth='none', methods=['POST'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def create_service(self, **kwargs):
        try:
            body = json.loads(request.httprequest.data or '{}')
            errors = _validate_body(body, 'service_create')
            if errors:
                return error_response('VALIDATION_ERROR', 'Validation failed.', 400,
                                      details=errors)

            env = request.env
            client_data = body['client']

            # Use sudo env for partner creation to allow agents without contact-creation rights
            sudo_env = request.env(su=True)
            try:
                partner, divergence = find_or_create_partner(
                    sudo_env,
                    name=client_data['name'],
                    email=client_data.get('email'),
                    phones=client_data.get('phones', []),
                )
            except PartnerDeduplicationConflict as exc:
                return error_response(
                    'CONFLICT',
                    str(exc),
                    409,
                    details={'candidate_partner_ids': exc.candidate_ids},
                )

            vals = {
                'client_partner_id': partner.id,
                'operation_type': body['operation_type'],
                'company_id': env.company.id,
            }
            if body.get('source_id'):
                vals['source_id'] = body['source_id']
            if body.get('notes'):
                vals['notes'] = body['notes']
            if body.get('property_ids'):
                vals['property_ids'] = [(6, 0, body['property_ids'])]
            if body.get('tag_ids'):
                vals['tag_ids'] = [(6, 0, body['tag_ids'])]
            if body.get('agent_id'):
                vals['agent_id'] = body['agent_id']
            else:
                # Auto-assign agent_id to current user (agent_id is Many2one to res.users)
                vals['agent_id'] = env.user.id

            service = env['real.estate.service'].create(vals)

            response_data = _serialize_service(service)
            if divergence:
                response_data['_warnings'] = [{'code': 'PARTNER_DEDUP_DIVERGENCE',
                                                'message': divergence}]

            return success_response(response_data, status_code=201)

        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except (ValidationError, UserError) as exc:
            return error_response('VALIDATION_ERROR', str(exc), 422)
        except Exception:
            _logger.exception('Unexpected error in create_service')
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    # ---------------------------------------------------------------------- #
    # GET /api/v1/services/summary  (must be registered before /{id})        #
    # ---------------------------------------------------------------------- #
    @http.route('/api/v1/services/summary', type='http', auth='none', methods=['GET'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def get_service_summary(self, **kwargs):
        try:
            env = request.env
            sudo_env = env(su=True)
            company_id = env.company.id
            agent_id = None if _is_manager_or_owner(env) else env.user.id
            summary = pipeline_svc.compute_summary(sudo_env, company_id=company_id, agent_id=agent_id)
            data = {
                'total': summary['total'],
                'orphan_agent': summary['orphan_agent'],
                'by_stage': summary['by_stage'],
                'links': [
                    {'rel': 'list', 'href': '/api/v1/services', 'method': 'GET'},
                ],
            }
            return success_response(data)
        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except Exception:
            _logger.exception('Unexpected error in get_service_summary')
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    # ---------------------------------------------------------------------- #
    # GET /api/v1/services                                                    #
    # ---------------------------------------------------------------------- #
    @http.route('/api/v1/services', type='http', auth='none', methods=['GET'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def list_services(self, **kwargs):
        try:
            params = request.httprequest.args

            domain = _build_domain(params)

            ordering = ORDERING_MAP.get(params.get('ordering', DEFAULT_ORDERING),
                                        ORDERING_MAP[DEFAULT_ORDERING])

            try:
                page = max(1, int(params.get('page', 1)))
                per_page = min(MAX_PAGE_SIZE, max(1, int(params.get('per_page', DEFAULT_PAGE_SIZE))))
            except (ValueError, TypeError):
                page, per_page = 1, DEFAULT_PAGE_SIZE

            offset = (page - 1) * per_page

            # Use sudo + explicit access domain (record rules not reliable in Odoo 18)
            env = request.env
            access_domain = [('company_id', 'in', request.user_company_ids)]
            if not _is_manager_or_owner(env):
                access_domain.append(('agent_id', '=', env.user.id))
            full_domain = domain + access_domain
            Service = env['real.estate.service'].sudo()
            total = Service.search_count(full_domain)
            services = Service.search(full_domain, order=ordering, limit=per_page, offset=offset)

            total_pages = math.ceil(total / per_page) if per_page else 1
            base_url = '/api/v1/services'

            links = [
                {'rel': 'self', 'href': f'{base_url}?page={page}&per_page={per_page}',
                 'method': 'GET'},
            ]
            if page > 1:
                links.append({'rel': 'prev', 'href': f'{base_url}?page={page - 1}&per_page={per_page}',
                               'method': 'GET'})
            if page < total_pages:
                links.append({'rel': 'next', 'href': f'{base_url}?page={page + 1}&per_page={per_page}',
                               'method': 'GET'})

            data = {
                'data': [_serialize_service(s) for s in services],
                'meta': {
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': total_pages,
                },
                'links': links,
            }
            return success_response(data)

        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except Exception:
            _logger.exception('Unexpected error in list_services')
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    # ---------------------------------------------------------------------- #
    # GET /api/v1/services/{id}                                               #
    # ---------------------------------------------------------------------- #
    @http.route('/api/v1/services/<int:service_id>', type='http', auth='none', methods=['GET'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def get_service(self, service_id, **kwargs):
        try:
            env = request.env
            service = env['real.estate.service'].sudo().browse(service_id)
            if not service.exists() or service.company_id.id not in request.user_company_ids:
                return error_response('NOT_FOUND', 'Service not found.', 404)
            if not _is_manager_or_owner(env) and service.agent_id.id != env.user.id:
                return error_response('NOT_FOUND', 'Service not found.', 404)
            return success_response(_serialize_service(service))
        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except Exception:
            _logger.exception('Unexpected error in get_service id=%d', service_id)
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    # ---------------------------------------------------------------------- #
    # PUT /api/v1/services/{id}                                               #
    # ---------------------------------------------------------------------- #
    @http.route('/api/v1/services/<int:service_id>', type='http', auth='none', methods=['PUT'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def update_service(self, service_id, **kwargs):
        try:
            body = json.loads(request.httprequest.data or '{}')
            errors = _validate_body(body, 'service_update')
            if errors:
                return error_response('VALIDATION_ERROR', 'Validation failed.', 400,
                                      details=errors)

            env = request.env
            service = env['real.estate.service'].sudo().browse(service_id)
            if not service.exists() or service.company_id.id not in request.user_company_ids:
                return error_response('NOT_FOUND', 'Service not found.', 404)
            if not _is_manager_or_owner(env) and service.agent_id.id != env.user.id:
                return error_response('FORBIDDEN', 'Agents can only update their own services.', 403)

            vals = {}
            if 'operation_type' in body:
                vals['operation_type'] = body['operation_type']
            if 'source_id' in body:
                vals['source_id'] = body['source_id']
            if 'notes' in body:
                vals['notes'] = body['notes']
            if 'property_ids' in body:
                vals['property_ids'] = [(6, 0, body['property_ids'])]
            if 'tag_ids' in body:
                vals['tag_ids'] = [(6, 0, body['tag_ids'])]

            service.write(vals)
            return success_response(_serialize_service(service))

        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except (ValidationError, UserError) as exc:
            return error_response('VALIDATION_ERROR', str(exc), 422)
        except Exception:
            _logger.exception('Unexpected error in update_service id=%d', service_id)
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    # ---------------------------------------------------------------------- #
    # DELETE /api/v1/services/{id}                                            #
    # ---------------------------------------------------------------------- #
    @http.route('/api/v1/services/<int:service_id>', type='http', auth='none', methods=['DELETE'],
                csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def delete_service(self, service_id, **kwargs):
        try:
            if not _is_manager_or_owner(request.env):
                return error_response('FORBIDDEN', 'Only Owner/Manager can delete services.', 403)
            service = request.env['real.estate.service'].sudo().browse(service_id)
            if not service.exists() or service.company_id.id not in request.user_company_ids:
                return error_response('NOT_FOUND', 'Service not found.', 404)
            service.unlink()
            return success_response(None, status_code=204)
        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except (ValidationError, UserError) as exc:
            return error_response('VALIDATION_ERROR', str(exc), 422)
        except Exception:
            _logger.exception('Unexpected error in delete_service id=%d', service_id)
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    # ---------------------------------------------------------------------- #
    # PATCH /api/v1/services/{id}/stage                                       #
    # ---------------------------------------------------------------------- #
    @http.route('/api/v1/services/<int:service_id>/stage', type='http', auth='none',
                methods=['PATCH'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def change_service_stage(self, service_id, **kwargs):
        try:
            body = json.loads(request.httprequest.data or '{}')
            errors = _validate_body(body, 'stage_change')
            if errors:
                return error_response('VALIDATION_ERROR', 'Validation failed.', 400,
                                      details=errors)

            env = request.env
            service = env['real.estate.service'].sudo().browse(service_id)
            if not service.exists() or service.company_id.id not in request.user_company_ids:
                return error_response('NOT_FOUND', 'Service not found.', 404)
            if not _is_manager_or_owner(env) and service.agent_id.id != env.user.id:
                return error_response('FORBIDDEN', 'Agents can only change stage of their own services.', 403)

            pipeline_svc.change_stage(
                service,
                target_stage=body['stage'],
                comment=body.get('comment'),
                lost_reason=body.get('lost_reason'),
            )

            return success_response(_serialize_service(service))

        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except (ValidationError, UserError) as exc:
            # 422 for business-rule violations (stage gates), 423 for locks
            msg = str(exc)
            # Detect lock condition (closed tag / terminal without reopen / orphan agent)
            lock_keywords = ('locked', 'closed tag', 'terminal', 'orphan', 'reopen')
            status_code = 423 if any(k in msg.lower() for k in lock_keywords) else 422
            return error_response('BUSINESS_RULE_VIOLATION', msg, status_code)
        except Exception:
            _logger.exception('Unexpected error in change_service_stage id=%d', service_id)
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    # ---------------------------------------------------------------------- #
    # PATCH /api/v1/services/{id}/reassign                                    #
    # ---------------------------------------------------------------------- #
    @http.route('/api/v1/services/<int:service_id>/reassign', type='http', auth='none',
                methods=['PATCH'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def reassign_service(self, service_id, **kwargs):
        try:
            if not _is_manager_or_owner(request.env):
                return error_response('FORBIDDEN', 'Only Owner/Manager can reassign services.', 403)

            body = json.loads(request.httprequest.data or '{}')
            errors = _validate_body(body, 'reassign')
            if errors:
                return error_response('VALIDATION_ERROR', 'Validation failed.', 400,
                                      details=errors)

            service = request.env['real.estate.service'].sudo().browse(service_id)
            if not service.exists() or service.company_id.id not in request.user_company_ids:
                return error_response('NOT_FOUND', 'Service not found.', 404)

            TERMINAL_STAGES = {'won', 'lost'}
            if service.stage in TERMINAL_STAGES:
                return error_response(
                    'CONFLICT',
                    f'Cannot reassign a service in terminal stage "{service.stage}".',
                    409,
                )

            pipeline_svc.reassign(
                service,
                new_agent_id=body['new_agent_id'],
                reason=body.get('reason'),
            )

            return success_response(_serialize_service(service))

        except AccessError as exc:
            return error_response('FORBIDDEN', str(exc), 403)
        except (ValidationError, UserError) as exc:
            return error_response('VALIDATION_ERROR', str(exc), 422)
        except Exception:
            _logger.exception('Unexpected error in reassign_service id=%d', service_id)
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)
