# -*- coding: utf-8 -*-

import json
import logging
import math
from datetime import datetime

from odoo import http, _
from odoo.http import request, Response
from odoo.exceptions import AccessError, UserError, ValidationError

from .utils.auth import require_jwt
from .utils.response import error_response, success_response
from odoo.addons.thedevkitchen_apigateway.middleware import require_session, require_company
from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request

_logger = logging.getLogger(__name__)

ALLOWED_ATTACHMENT_MIMETYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB


def _load_schema(name):
    import os
    schema_path = os.path.join(
        os.path.dirname(__file__),
        '..', 'schemas', f'{name}.json'
    )
    with open(os.path.realpath(schema_path)) as f:
        return json.load(f)


def _validate_body(body, schema_name):
    """Validate request body dict against a JSON Schema file. Returns errors list."""
    try:
        import jsonschema
        schema = _load_schema(schema_name)
        validator = jsonschema.Draft7Validator(schema)
        errors = sorted(validator.iter_errors(body), key=lambda e: e.path)
        return [
            {'field': '.'.join(str(p) for p in e.absolute_path) or e.schema_path[-1],
             'message': e.message}
            for e in errors
        ]
    except ImportError:
        _logger.warning('jsonschema not installed — skipping schema validation')
        return []


def _serialize_proposal(proposal, include_chain=False, include_attachments=False):
    """Serialize a real.estate.proposal record to dict per openapi.yaml schema."""
    data = {
        'id': proposal.id,
        'proposal_code': proposal.proposal_code,
        'state': proposal.state,
        'proposal_type': proposal.proposal_type,
        'proposal_value': proposal.proposal_value,
        'currency': proposal.currency_id.name,
        'property': {
            'id': proposal.property_id.id,
            'name': proposal.property_id.name,
            'code': proposal.property_id.reference_code or None,
        },
        'client': {
            'id': proposal.partner_id.id,
            'name': proposal.partner_id.name,
            'document': proposal.partner_id.vat or '',
            'email': proposal.partner_id.email or None,
            'phone': proposal.partner_id.phone or None,
        },
        'agent': {
            'id': proposal.agent_id.id,
            'name': proposal.agent_id.name,
        },
        'lead_id': proposal.lead_id.id if proposal.lead_id else None,
        'description': proposal.description or None,
        'valid_until': proposal.valid_until.isoformat() if proposal.valid_until else None,
        'sent_date': proposal.sent_date.isoformat() if proposal.sent_date else None,
        'accepted_date': proposal.accepted_date.isoformat() if proposal.accepted_date else None,
        'rejected_date': proposal.rejected_date.isoformat() if proposal.rejected_date else None,
        'rejection_reason': proposal.rejection_reason or None,
        'cancellation_reason': proposal.cancellation_reason or None,
        'parent_proposal_id': proposal.parent_proposal_id.id if proposal.parent_proposal_id else None,
        'superseded_by_id': proposal.superseded_by_id.id if proposal.superseded_by_id else None,
        'queue_position': proposal.queue_position if proposal.queue_position >= 0 else None,
        'is_active_proposal': proposal.is_active_proposal,
        'documents_count': proposal.documents_count,
        'has_competing_proposals': proposal.has_competing_proposals,
        'created_at': proposal.create_date.isoformat() if proposal.create_date else None,
        'updated_at': proposal.write_date.isoformat() if proposal.write_date else None,
        'attachments': [],
        'proposal_chain': [],
        'links': _build_hateoas_links(proposal),
    }

    if include_attachments:
        attachments = request.env['ir.attachment'].search([
            ('res_model', '=', 'real.estate.proposal'),
            ('res_id', '=', proposal.id),
        ])
        data['attachments'] = [
            {
                'id': a.id,
                'name': a.name,
                'mimetype': a.mimetype,
                'size': a.file_size,
                'download_url': f'/web/content/{a.id}?download=true',
            }
            for a in attachments
        ]

    if include_chain:
        chain = proposal.get_proposal_chain()
        data['proposal_chain'] = [
            {
                'id': p.id,
                'proposal_code': p.proposal_code,
                'state': p.state,
                'proposal_value': p.proposal_value,
                'created_at': p.create_date.isoformat() if p.create_date else None,
            }
            for p in chain
        ]

    return data


def _build_hateoas_links(proposal):
    """Build HATEOAS links conditional on state and role (ADR-007)."""
    links = []
    base = '/api/v1/proposals'
    user = request.env.user
    is_manager_or_owner = (
        user.has_group('quicksol_estate.group_real_estate_manager')
        or user.has_group('quicksol_estate.group_real_estate_owner')
    )

    if proposal.state == 'draft':
        links.append({'rel': 'send', 'href': f'{base}/{proposal.id}/send', 'method': 'POST'})
        links.append({'rel': 'cancel', 'href': f'{base}/{proposal.id}', 'method': 'DELETE'})
    elif proposal.state == 'sent':
        links.append({'rel': 'counter', 'href': f'{base}/{proposal.id}/counter', 'method': 'POST'})
        if is_manager_or_owner:
            links.append({'rel': 'accept', 'href': f'{base}/{proposal.id}/accept', 'method': 'POST'})
            links.append({'rel': 'reject', 'href': f'{base}/{proposal.id}/reject', 'method': 'POST'})
        if is_manager_or_owner:
            links.append({'rel': 'cancel', 'href': f'{base}/{proposal.id}', 'method': 'DELETE'})
    elif proposal.state == 'negotiation':
        links.append({'rel': 'counter', 'href': f'{base}/{proposal.id}/counter', 'method': 'POST'})
        if is_manager_or_owner:
            links.append({'rel': 'accept', 'href': f'{base}/{proposal.id}/accept', 'method': 'POST'})
            links.append({'rel': 'reject', 'href': f'{base}/{proposal.id}/reject', 'method': 'POST'})
    elif proposal.state == 'accepted':
        links.append({
            'rel': 'create-contract',
            'href': f'/api/v1/contracts?from_proposal={proposal.id}',
            'method': 'POST',
        })
    elif proposal.state == 'expired':
        links.append({'rel': 'renew', 'href': f'{base}/{proposal.id}/renew', 'method': 'POST'})

    links.append({'rel': 'self', 'href': f'{base}/{proposal.id}', 'method': 'GET'})
    links.append({'rel': 'queue', 'href': f'{base}/{proposal.id}/queue', 'method': 'GET'})
    return links


class ProposalController(http.Controller):

    # ================================================================== #
    #  POST /api/v1/proposals — create proposal (T026)                   #
    # ================================================================== #

    @http.route('/api/v1/proposals', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def create_proposal(self, **kwargs):
        try:
            body = json.loads(request.httprequest.data or '{}')
            errors = _validate_body(body, 'proposal_create')
            if errors:
                return error_response('VALIDATION_ERROR', 'Validation failed', 400,
                                      details=errors)

            # Normalize document
            from odoo.addons.quicksol_estate.utils.validators import normalize_document
            if body.get('client_document'):
                body['client_document'] = normalize_document(body['client_document'])

            # Resolve / create partner
            partner = _resolve_or_create_partner(body)

            vals = {
                'property_id': body['property_id'],
                'partner_id': partner.id,
                'agent_id': body['agent_id'],
                'proposal_type': body['proposal_type'],
                'proposal_value': body['proposal_value'],
                'company_id': request.env.company.id,
                'description': body.get('description'),
                'lead_id': body.get('lead_id'),
            }
            if body.get('valid_until'):
                vals['valid_until'] = body['valid_until']

            proposal = request.env['real.estate.proposal'].create([vals])
            return success_response(
                _serialize_proposal(proposal, include_chain=False, include_attachments=False),
                status_code=201,
            )
        except AccessError as e:
            return error_response('FORBIDDEN', str(e), 403)
        except (ValidationError, UserError) as e:
            return error_response('VALIDATION_ERROR', str(e), 400)
        except Exception:
            _logger.exception('POST /api/v1/proposals failed')
            return error_response('INTERNAL_ERROR', 'Internal server error.', 500)

    # ================================================================== #
    #  GET /api/v1/proposals — list (T056)                               #
    # ================================================================== #

    @http.route('/api/v1/proposals', type='http', auth='none',
                methods=['GET'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def list_proposals(self, **kwargs):
        try:
            user = request.env.user
            domain = [('company_id', '=', request.env.company.id)]

            # Role-based filtering (FR-035): agents see only own proposals
            if (user.has_group('quicksol_estate.group_real_estate_agent')
                    and not user.has_group('quicksol_estate.group_real_estate_manager')
                    and not user.has_group('quicksol_estate.group_real_estate_owner')):
                agent = request.env['real.estate.agent'].search(
                    [('user_id', '=', user.id)], limit=1)
                if agent:
                    domain.append(('agent_id', '=', agent.id))

            # Filters from query params
            if kwargs.get('state'):
                domain.append(('state', '=', kwargs['state']))
            if kwargs.get('agent_id'):
                domain.append(('agent_id', '=', int(kwargs['agent_id'])))
            if kwargs.get('property_id'):
                domain.append(('property_id', '=', int(kwargs['property_id'])))
            if kwargs.get('partner_id'):
                domain.append(('partner_id', '=', int(kwargs['partner_id'])))
            if kwargs.get('date_from'):
                domain.append(('create_date', '>=', kwargs['date_from']))
            if kwargs.get('date_to'):
                domain.append(('create_date', '<=', kwargs['date_to']))
            if kwargs.get('search'):
                term = kwargs['search']
                domain.append('|')
                domain.append('|')
                domain.append(('proposal_code', 'ilike', term))
                domain.append(('partner_id.name', 'ilike', term))
                domain.append(('property_id.name', 'ilike', term))

            page = max(int(kwargs.get('page', 1)), 1)
            page_size = min(int(kwargs.get('page_size', 50)), 100)
            offset = (page - 1) * page_size

            total = request.env['real.estate.proposal'].search_count(domain)
            proposals = request.env['real.estate.proposal'].search(
                domain, limit=page_size, offset=offset, order='create_date desc'
            )
            pages = math.ceil(total / page_size) if page_size else 1
            base_url = '/api/v1/proposals'

            return success_response({
                'data': [_serialize_proposal(p) for p in proposals],
                '_meta': {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'pages': pages,
                },
                '_links': {
                    'first': f'{base_url}?page=1&page_size={page_size}',
                    'prev': f'{base_url}?page={page - 1}&page_size={page_size}' if page > 1 else None,
                    'next': f'{base_url}?page={page + 1}&page_size={page_size}' if page < pages else None,
                    'last': f'{base_url}?page={pages}&page_size={page_size}',
                },
            })
        except Exception:
            _logger.exception('GET /api/v1/proposals failed')
            return error_response('INTERNAL_ERROR', _('Internal server error.'), 500)

    # ================================================================== #
    #  GET /api/v1/proposals/stats — aggregated metrics (T057)           #
    # ================================================================== #

    @http.route('/api/v1/proposals/stats', type='http', auth='none',
                methods=['GET'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def get_proposal_stats(self, **kwargs):
        try:
            domain = [('company_id', '=', request.env.company.id)]
            groups = request.env['real.estate.proposal'].read_group(
                domain, ['state'], ['state']
            )
            by_state = {g['state']: g['state_count'] for g in groups}
            all_states = ('draft', 'queued', 'sent', 'negotiation',
                          'accepted', 'rejected', 'expired', 'cancelled')
            result = {s: by_state.get(s, 0) for s in all_states}
            total = sum(result.values())
            return success_response({'total': total, 'by_state': result})
        except Exception:
            _logger.exception('GET /api/v1/proposals/stats failed')
            return error_response('INTERNAL_ERROR', _('Internal server error.'), 500)

    # ================================================================== #
    #  GET /api/v1/proposals/<id> — detail (T028)                        #
    # ================================================================== #

    @http.route('/api/v1/proposals/<int:proposal_id>', type='http', auth='none',
                methods=['GET'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def get_proposal(self, proposal_id, **kwargs):
        try:
            proposal = _fetch_proposal(proposal_id)
            if not proposal:
                return error_response('NOT_FOUND', _('Proposal not found.'), 404)
            return success_response(
                _serialize_proposal(proposal, include_chain=True, include_attachments=True)
            )
        except AccessError:
            return error_response('NOT_FOUND', _('Proposal not found.'), 404)
        except Exception:
            _logger.exception('GET /api/v1/proposals/%d failed', proposal_id)
            return error_response('INTERNAL_ERROR', _('Internal server error.'), 500)

    # ================================================================== #
    #  PUT /api/v1/proposals/<id> — update (T058)                        #
    # ================================================================== #

    @http.route('/api/v1/proposals/<int:proposal_id>', type='http', auth='none',
                methods=['PUT'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def update_proposal(self, proposal_id, **kwargs):
        try:
            proposal = _fetch_proposal(proposal_id)
            if not proposal:
                return error_response('NOT_FOUND', _('Proposal not found.'), 404)
            if proposal.state in ('accepted', 'rejected', 'expired', 'cancelled'):
                return error_response('CONFLICT',
                    _('Cannot update a proposal in terminal state.'), 409)

            body = json.loads(request.httprequest.data or '{}')
            errors = _validate_body(body, 'proposal_update')
            if errors:
                return error_response('VALIDATION_ERROR', 'Validation failed', 400,
                                      details=errors)

            vals = {}
            if 'proposal_value' in body:
                vals['proposal_value'] = body['proposal_value']
            if 'description' in body:
                vals['description'] = body['description']
            if 'valid_until' in body:
                vals['valid_until'] = body['valid_until']
            if 'agent_id' in body:
                user = request.env.user
                if not (user.has_group('quicksol_estate.group_real_estate_manager')
                        or user.has_group('quicksol_estate.group_real_estate_owner')):
                    return error_response('FORBIDDEN',
                        _('Only managers/owners can reassign agents.'), 403)
                vals['agent_id'] = body['agent_id']

            if vals:
                proposal.write(vals)
            return success_response(_serialize_proposal(proposal))
        except (ValidationError, UserError) as e:
            return error_response('VALIDATION_ERROR', str(e), 400)
        except AccessError:
            return error_response('NOT_FOUND', _('Proposal not found.'), 404)
        except Exception:
            _logger.exception('PUT /api/v1/proposals/%d failed', proposal_id)
            return error_response('INTERNAL_ERROR', _('Internal server error.'), 500)

    # ================================================================== #
    #  DELETE /api/v1/proposals/<id> — soft cancel (T049)                #
    # ================================================================== #

    @http.route('/api/v1/proposals/<int:proposal_id>', type='http', auth='none',
                methods=['DELETE'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def cancel_proposal(self, proposal_id, **kwargs):
        try:
            proposal = _fetch_proposal(proposal_id)
            if not proposal:
                return error_response('NOT_FOUND', _('Proposal not found.'), 404)

            # Only manager/owner can cancel (FR-044)
            user = request.env.user
            if not (user.has_group('quicksol_estate.group_real_estate_manager')
                    or user.has_group('quicksol_estate.group_real_estate_owner')):
                return error_response('FORBIDDEN', _('Only managers/owners can cancel proposals.'), 403)

            body = json.loads(request.httprequest.data or '{}')
            reason = (body.get('cancellation_reason') or '').strip()
            if not reason:
                return error_response('VALIDATION_ERROR',
                    _('cancellation_reason is required.'), 400)

            proposal.action_cancel(reason)
            return success_response(_serialize_proposal(proposal))
        except (ValidationError, UserError) as e:
            return error_response('CONFLICT', str(e), 409)
        except AccessError:
            return error_response('NOT_FOUND', _('Proposal not found.'), 404)
        except Exception:
            _logger.exception('DELETE /api/v1/proposals/%d failed', proposal_id)
            return error_response('INTERNAL_ERROR', _('Internal server error.'), 500)

    # ================================================================== #
    #  POST /api/v1/proposals/<id>/send  (T027)                          #
    # ================================================================== #

    @http.route('/api/v1/proposals/<int:proposal_id>/send', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def send_proposal(self, proposal_id, **kwargs):
        try:
            proposal = _fetch_proposal(proposal_id)
            if not proposal:
                return error_response('NOT_FOUND', _('Proposal not found.'), 404)
            proposal.action_send()
            return success_response(_serialize_proposal(proposal))
        except UserError as e:
            return error_response('UNPROCESSABLE', str(e), 422)
        except AccessError:
            return error_response('NOT_FOUND', _('Proposal not found.'), 404)
        except Exception:
            _logger.exception('POST /api/v1/proposals/%d/send failed', proposal_id)
            return error_response('INTERNAL_ERROR', _('Internal server error.'), 500)

    # ================================================================== #
    #  POST /api/v1/proposals/<id>/accept  (T047)                        #
    # ================================================================== #

    @http.route('/api/v1/proposals/<int:proposal_id>/accept', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def accept_proposal(self, proposal_id, **kwargs):
        try:
            proposal = _fetch_proposal(proposal_id)
            if not proposal:
                return error_response('NOT_FOUND', _('Proposal not found.'), 404)
            proposal.action_accept()
            return success_response(_serialize_proposal(proposal))
        except (UserError, AccessError) as e:
            status = 403 if isinstance(e, AccessError) else 422
            return error_response('FORBIDDEN' if isinstance(e, AccessError) else 'UNPROCESSABLE',
                                  str(e), status)
        except Exception:
            _logger.exception('POST /api/v1/proposals/%d/accept failed', proposal_id)
            return error_response('INTERNAL_ERROR', _('Internal server error.'), 500)

    # ================================================================== #
    #  POST /api/v1/proposals/<id>/reject  (T048)                        #
    # ================================================================== #

    @http.route('/api/v1/proposals/<int:proposal_id>/reject', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def reject_proposal(self, proposal_id, **kwargs):
        try:
            proposal = _fetch_proposal(proposal_id)
            if not proposal:
                return error_response('NOT_FOUND', _('Proposal not found.'), 404)

            body = json.loads(request.httprequest.data or '{}')
            errors = _validate_body(body, 'proposal_reject')
            if errors:
                return error_response('VALIDATION_ERROR', 'Validation failed', 400,
                                      details=errors)

            proposal.action_reject(body.get('rejection_reason', ''))
            return success_response(_serialize_proposal(proposal))
        except (ValidationError, UserError) as e:
            return error_response('UNPROCESSABLE', str(e), 422)
        except AccessError:
            return error_response('NOT_FOUND', _('Proposal not found.'), 404)
        except Exception:
            _logger.exception('POST /api/v1/proposals/%d/reject failed', proposal_id)
            return error_response('INTERNAL_ERROR', _('Internal server error.'), 500)

    # ================================================================== #
    #  POST /api/v1/proposals/<id>/counter  (T042)                       #
    # ================================================================== #

    @http.route('/api/v1/proposals/<int:proposal_id>/counter', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def counter_proposal(self, proposal_id, **kwargs):
        try:
            proposal = _fetch_proposal(proposal_id)
            if not proposal:
                return error_response('NOT_FOUND', _('Proposal not found.'), 404)

            body = json.loads(request.httprequest.data or '{}')
            errors = _validate_body(body, 'proposal_counter')
            if errors:
                return error_response('VALIDATION_ERROR', 'Validation failed', 400,
                                      details=errors)

            counter_vals = {
                'proposal_value': body['proposal_value'],
                'description': body.get('description'),
            }
            if body.get('valid_until'):
                counter_vals['valid_until'] = body['valid_until']

            child = proposal.action_counter(counter_vals)
            return success_response(
                _serialize_proposal(child, include_chain=True),
                status_code=201,
            )
        except (ValidationError, UserError) as e:
            return error_response('UNPROCESSABLE', str(e), 422)
        except AccessError:
            return error_response('NOT_FOUND', _('Proposal not found.'), 404)
        except Exception:
            _logger.exception('POST /api/v1/proposals/%d/counter failed', proposal_id)
            return error_response('INTERNAL_ERROR', _('Internal server error.'), 500)

    # ================================================================== #
    #  GET /api/v1/proposals/<id>/queue  (T036)                          #
    # ================================================================== #

    @http.route('/api/v1/proposals/<int:proposal_id>/queue', type='http', auth='none',
                methods=['GET'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def get_proposal_queue(self, proposal_id, **kwargs):
        try:
            proposal = _fetch_proposal(proposal_id)
            if not proposal:
                return error_response('NOT_FOUND', _('Proposal not found.'), 404)

            property_id = proposal.property_id.id
            Proposal = request.env['real.estate.proposal']

            active_proposal = Proposal.search([
                ('property_id', '=', property_id),
                ('state', 'in', ('draft', 'sent', 'negotiation', 'accepted')),
                ('active', '=', True),
                ('parent_proposal_id', '=', False),
            ], limit=1)

            queue = Proposal.search([
                ('property_id', '=', property_id),
                ('state', '=', 'queued'),
                ('active', '=', True),
                ('parent_proposal_id', '=', False),
            ], order='create_date asc')

            return success_response({
                'property_id': property_id,
                'active_proposal': _serialize_proposal(active_proposal) if active_proposal else None,
                'queue': [_serialize_proposal(p) for p in queue],
            })
        except AccessError:
            return error_response('NOT_FOUND', _('Proposal not found.'), 404)
        except Exception:
            _logger.exception('GET /api/v1/proposals/%d/queue failed', proposal_id)
            return error_response('INTERNAL_ERROR', _('Internal server error.'), 500)

    # ================================================================== #
    #  POST /api/v1/proposals/<id>/attachments  (T061)                   #
    # ================================================================== #

    @http.route('/api/v1/proposals/<int:proposal_id>/attachments', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @trace_http_request
    @require_jwt
    @require_session
    @require_company
    def upload_attachment(self, proposal_id, **kwargs):
        try:
            proposal = _fetch_proposal(proposal_id)
            if not proposal:
                return error_response('NOT_FOUND', _('Proposal not found.'), 404)

            upload = request.httprequest.files.get('file')
            if not upload:
                return error_response('VALIDATION_ERROR', _('No file provided.'), 400)

            content = upload.read()
            if len(content) > MAX_ATTACHMENT_BYTES:
                return error_response('PAYLOAD_TOO_LARGE',
                    _('File exceeds the 10 MB limit.'), 413)

            mimetype = upload.mimetype or ''
            if mimetype not in ALLOWED_ATTACHMENT_MIMETYPES:
                return error_response('VALIDATION_ERROR',
                    _('File type "%s" is not allowed.') % mimetype, 400)

            import base64
            attachment = request.env['ir.attachment'].create({
                'name': upload.filename,
                'datas': base64.b64encode(content),
                'res_model': 'real.estate.proposal',
                'res_id': proposal.id,
                'mimetype': mimetype,
                'company_id': request.env.company.id,
                'description': request.httprequest.form.get('description'),
            })
            return success_response({
                'id': attachment.id,
                'name': attachment.name,
                'mimetype': attachment.mimetype,
                'size': attachment.file_size,
                'download_url': f'/web/content/{attachment.id}?download=true',
            }, status_code=201)
        except AccessError:
            return error_response('NOT_FOUND', _('Proposal not found.'), 404)
        except Exception:
            _logger.exception('POST /api/v1/proposals/%d/attachments failed', proposal_id)
            return error_response('INTERNAL_ERROR', _('Internal server error.'), 500)


# ====================================================================== #
#  Helpers                                                                #
# ====================================================================== #

def _fetch_proposal(proposal_id):
    """Fetch a proposal by ID scoped to the current company (FR-048)."""
    proposal = request.env['real.estate.proposal'].browse(proposal_id)
    if not proposal.exists():
        return None
    if proposal.company_id != request.env.company:
        return None  # return None (not found) — no info leakage (FR-048)
    return proposal


def _resolve_or_create_partner(body):
    """Find or create res.partner from client_name + client_document.

    Uses sudo() because the API user may not have Contact Creation rights;
    the operation is already protected by JWT + session + company middleware.
    """
    from odoo.addons.quicksol_estate.utils.validators import normalize_document
    doc = normalize_document(body.get('client_document', ''))
    Partner = request.env['res.partner'].sudo()
    partner = Partner.search([('vat', '=', doc), ('company_id', '=', False)], limit=1)
    if not partner:
        partner = Partner.create({
            'name': body['client_name'],
            'vat': doc,
            'email': body.get('client_email'),
            'phone': body.get('client_phone'),
        })
    return partner
