# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.addons.thedevkitchen_apigateway.middleware import (
    require_jwt,
    require_session,
    require_company,
)
from ..services.credit_check_service import CreditCheckService

_logger = logging.getLogger(__name__)

VALID_RESULTS = ('approved', 'rejected', 'cancelled')


class CreditCheckController(http.Controller):

    # ================================================================== #
    #  HELPERS                                                             #
    # ================================================================== #

    def _json_response(self, data, status=200):
        return Response(
            json.dumps({'status': 'success', 'data': data}),
            status=status,
            headers={'Content-Type': 'application/json'},
        )

    def _error_response(self, status, error_code, message, details=None):
        body = {'status': 'error', 'error': {'code': error_code, 'message': message}}
        if details:
            body['error']['details'] = details
        return Response(
            json.dumps(body),
            status=status,
            headers={'Content-Type': 'application/json'},
        )

    def _parse_json_body(self):
        try:
            return json.loads(request.httprequest.data.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return None

    # ================================================================== #
    #  US1 — POST /api/v1/proposals/{proposal_id}/credit-checks           #
    # ================================================================== #

    @http.route(
        '/api/v1/proposals/<int:proposal_id>/credit-checks',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
        cors='*',
    )
    @require_jwt
    @require_session
    @require_company
    def initiate_credit_check(self, proposal_id, **kwargs):
        data = self._parse_json_body()
        if data is None:
            return self._error_response(400, 'validation_error', 'Invalid JSON in request body.')

        insurer_name = (data.get('insurer_name') or '').strip()
        if not insurer_name:
            return self._error_response(
                400, 'validation_error', 'Missing required field: insurer_name.',
                {'missing_fields': ['insurer_name']},
            )
        if len(insurer_name) > 255:
            return self._error_response(
                400, 'validation_error', 'insurer_name must not exceed 255 characters.',
            )

        try:
            svc = CreditCheckService(request.env)
            check = svc.initiate_credit_check(proposal_id, insurer_name)
            return self._json_response(check._to_dict(), status=201)
        except UserError as e:
            msg = str(e.args[0]) if e.args else 'Bad request.'
            # Anti-enumeration: treat "not found" messages as 404
            if 'not found' in msg.lower():
                return self._error_response(404, 'not_found', msg)
            # Duplicate pending → 409
            if 'already pending' in msg.lower():
                return self._error_response(409, 'conflict', msg)
            # Agent scope violation → 403
            if 'access denied' in msg.lower() or 'permission' in msg.lower():
                return self._error_response(403, 'forbidden', msg)
            return self._error_response(422, 'unprocessable', msg)
        except ValidationError as e:
            return self._error_response(400, 'validation_error', str(e.args[0]))
        except AccessError as e:
            return self._error_response(403, 'forbidden', str(e.args[0]))
        except Exception:
            _logger.exception('spec-014: unexpected error in initiate_credit_check')
            return self._error_response(500, 'server_error', 'Internal server error.')

    # ================================================================== #
    #  US1 — GET /api/v1/proposals/{proposal_id}/credit-checks            #
    # ================================================================== #

    @http.route(
        '/api/v1/proposals/<int:proposal_id>/credit-checks',
        type='http',
        auth='none',
        methods=['GET'],
        csrf=False,
        cors='*',
    )
    @require_jwt
    @require_session
    @require_company
    def list_credit_checks(self, proposal_id, **kwargs):
        result_filter = request.params.get('result')
        try:
            limit = int(request.params.get('limit', 100))
            offset = int(request.params.get('offset', 0))
        except (ValueError, TypeError):
            return self._error_response(400, 'validation_error', 'limit and offset must be integers.')

        limit = min(limit, 100)

        if result_filter and result_filter not in ('pending', 'approved', 'rejected', 'cancelled'):
            return self._error_response(400, 'validation_error', f'Invalid result filter: {result_filter}')

        try:
            svc = CreditCheckService(request.env)
            checks = svc.get_checks_for_proposal(proposal_id, result_filter, limit, offset)
            return self._json_response({
                'items': [c._to_dict() for c in checks],
                'limit': limit,
                'offset': offset,
                '_links': {
                    'self': {'href': f'/api/v1/proposals/{proposal_id}/credit-checks'},
                },
            })
        except UserError as e:
            msg = str(e.args[0]) if e.args else 'Not found.'
            if 'not found' in msg.lower():
                return self._error_response(404, 'not_found', msg)
            return self._error_response(422, 'unprocessable', msg)
        except AccessError as e:
            return self._error_response(403, 'forbidden', str(e.args[0]))
        except Exception:
            _logger.exception('spec-014: unexpected error in list_credit_checks')
            return self._error_response(500, 'server_error', 'Internal server error.')

    # ================================================================== #
    #  US2 — PATCH /api/v1/proposals/{proposal_id}/credit-checks/{check_id}
    # ================================================================== #

    @http.route(
        '/api/v1/proposals/<int:proposal_id>/credit-checks/<int:check_id>',
        type='http',
        auth='none',
        methods=['PATCH'],
        csrf=False,
        cors='*',
    )
    @require_jwt
    @require_session
    @require_company
    def register_credit_check_result(self, proposal_id, check_id, **kwargs):
        data = self._parse_json_body()
        if data is None:
            return self._error_response(400, 'validation_error', 'Invalid JSON in request body.')

        result = (data.get('result') or '').strip()
        if not result:
            return self._error_response(400, 'validation_error', 'Missing required field: result.')
        if result not in VALID_RESULTS:
            return self._error_response(
                400, 'validation_error',
                f'Invalid result "{result}". Must be one of: {", ".join(VALID_RESULTS)}.'
            )

        rejection_reason = (data.get('rejection_reason') or '').strip() or None
        check_date = (data.get('check_date') or '').strip() or None

        if result == 'rejected' and not rejection_reason:
            return self._error_response(
                400, 'validation_error',
                'rejection_reason is required when result is "rejected".',
                {'missing_fields': ['rejection_reason']},
            )

        try:
            svc = CreditCheckService(request.env)
            check = svc.register_result(proposal_id, check_id, result, rejection_reason, check_date)
            return self._json_response(check._to_dict())
        except UserError as e:
            msg = str(e.args[0]) if e.args else 'Bad request.'
            if 'not found' in msg.lower():
                return self._error_response(404, 'not_found', msg)
            if 'not in pending' in msg.lower() or 'already resolved' in msg.lower() or 'immutable' in msg.lower():
                return self._error_response(409, 'conflict', msg)
            if 'access denied' in msg.lower() or 'permission' in msg.lower():
                return self._error_response(403, 'forbidden', msg)
            return self._error_response(422, 'unprocessable', msg)
        except ValidationError as e:
            return self._error_response(400, 'validation_error', str(e.args[0]))
        except AccessError as e:
            return self._error_response(403, 'forbidden', str(e.args[0]))
        except Exception:
            _logger.exception('spec-014: unexpected error in register_credit_check_result')
            return self._error_response(500, 'server_error', 'Internal server error.')

    # ================================================================== #
    #  US4 — GET /api/v1/clients/{partner_id}/credit-history             #
    # ================================================================== #

    @http.route(
        '/api/v1/clients/<int:partner_id>/credit-history',
        type='http',
        auth='none',
        methods=['GET'],
        csrf=False,
        cors='*',
    )
    @require_jwt
    @require_session
    @require_company
    def get_client_credit_history(self, partner_id, **kwargs):
        try:
            limit = int(request.params.get('limit', 100))
            offset = int(request.params.get('offset', 0))
        except (ValueError, TypeError):
            return self._error_response(400, 'validation_error', 'limit and offset must be integers.')

        limit = min(limit, 100)

        try:
            svc = CreditCheckService(request.env)
            result = svc.get_client_credit_history(partner_id, limit, offset)
            return self._json_response(result)
        except UserError as e:
            msg = str(e.args[0]) if e.args else 'Not found.'
            # Anti-enumeration: all scope/not-found errors → 404 (ADR-008)
            return self._error_response(404, 'not_found', 'Client not found.')
        except AccessError as e:
            return self._error_response(403, 'forbidden', str(e.args[0]))
        except Exception:
            _logger.exception('spec-014: unexpected error in get_client_credit_history')
            return self._error_response(500, 'server_error', 'Internal server error.')
