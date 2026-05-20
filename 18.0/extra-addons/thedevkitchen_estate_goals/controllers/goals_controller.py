# -*- coding: utf-8 -*-
import json
import logging
import re
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError
from odoo.addons.thedevkitchen_apigateway.middleware import (
    require_jwt,
    require_session,
    require_company,
)
from odoo.addons.quicksol_estate.services.role_resolver import resolve_role
from ..services.goals_report_service import GoalsReportService

_logger = logging.getLogger(__name__)

# Profiles that may NOT access goal endpoints
_BLOCKED_PROFILES = {'receptionist', 'prospector'}

# Profiles that may manage (create/update/delete) goals
_MANAGER_PROFILES = {'owner', 'director', 'manager'}

_CREATE_REQUIRED_FIELDS = [
    'user_id',
    'year',
    'month',
    'metric_type',
    'operation_type',
    'target_count',
]

# Profile XML ID validation pattern (SEC-9)
_PROFILE_PATTERN = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+$')


def _goal_to_dict(goal):
    """Serialize a goal record to a JSON-safe dict."""
    return {
        'id': goal.id,
        'user_id': goal.user_id.id,
        'user_name': goal.user_id.name,
        'year': goal.year,
        'month': goal.month,
        'metric_type': goal.metric_type,
        'operation_type': goal.operation_type,
        'target_count': goal.target_count,
        'target_vgv': goal.target_vgv or None,
        'active': goal.active,
    }


def _error(status, error, detail):
    """Build a FR6.9-compliant error response."""
    return Response(
        json.dumps({'error': error, 'detail': detail}),
        status=status,
        content_type='application/json',
    )


def _ok(status, body):
    """Build a success response."""
    return Response(
        json.dumps(body, default=str),
        status=status,
        content_type='application/json',
    )


def _goal_links(goal_id):
    return {
        'self': f'/api/v1/goals/{goal_id}',
        'update': f'/api/v1/goals/{goal_id}',
        'delete': f'/api/v1/goals/{goal_id}',
        'collection': '/api/v1/goals',
    }


def _parse_json_body():
    try:
        return json.loads(request.httprequest.data.decode('utf-8')), None
    except (ValueError, UnicodeDecodeError):
        return None, _error(400, 'bad_request', 'Invalid JSON in request body.')


def _ensure_manager_profile(caller_profile, action):
    if caller_profile in _MANAGER_PROFILES:
        return None
    return _error(
        403,
        'forbidden',
        f'Only Owner, Director, or Manager may {action} goals.',
    )


def _build_create_vals(data, company_id):
    missing = [field for field in _CREATE_REQUIRED_FIELDS if data.get(field) is None]
    if missing:
        return None, _error(
            400,
            'bad_request',
            f'Missing required fields: {", ".join(missing)}',
        )

    vals = {
        'user_id': int(data['user_id']),
        'year': int(data['year']),
        'month': int(data['month']),
        'metric_type': data['metric_type'],
        'operation_type': data['operation_type'],
        'target_count': int(data['target_count']),
        'company_id': company_id,
    }
    if data.get('target_vgv') is not None:
        vals['target_vgv'] = float(data['target_vgv'])
    return vals, None


def _validate_create_vals(vals):
    month = vals['month']
    if not 1 <= month <= 12:
        return _error(400, 'bad_request', f'Month must be between 1 and 12, got {month}.')

    year = vals['year']
    if year < 2000:
        return _error(400, 'bad_request', f'Year must be >= 2000, got {year}.')

    if vals['target_count'] < 0:
        return _error(400, 'bad_request', 'target_count cannot be negative.')

    target_user = request.env['res.users'].sudo().browse(vals['user_id'])
    if target_user.exists():
        return None
    return _error(404, 'not_found', f'User {vals["user_id"]} not found.')


def _create_goal_record(vals):
    try:
        return request.env['thedevkitchen.estate.goal'].sudo().create(vals), None
    except IntegrityError:
        request.env.cr.rollback()
        return None, _error(
            409,
            'conflict',
            'A goal for this user/period/metric/operation already exists.',
        )
    except ValidationError as exc:
        return None, _error(422, 'unprocessable_entity', str(exc))


def _active_goal_domain(goal_id, company_id):
    return [('id', '=', goal_id), ('active', '=', True), ('company_id', '=', company_id)]


def _get_active_goal(goal_id, company_id, detail):
    goal = request.env['thedevkitchen.estate.goal'].sudo().search(
        _active_goal_domain(goal_id, company_id),
        limit=1,
    )
    if goal:
        return goal, None
    return None, _error(404, 'not_found', detail)


def _build_update_vals(data):
    vals = {}
    if data.get('target_count') is not None:
        vals['target_count'] = int(data['target_count'])
    if 'target_vgv' in data:
        vals['target_vgv'] = float(data['target_vgv']) if data['target_vgv'] is not None else False
    if vals:
        return vals, None
    return None, _error(
        400,
        'bad_request',
        'At least one of target_count or target_vgv must be provided.',
    )


def _goal_response_body(goal):
    body = _goal_to_dict(goal)
    body['links'] = _goal_links(goal.id)
    return body


def _resolve_goal_filter_user_id(caller, caller_profile, user_id_param, denied_detail):
    if caller_profile != 'agent':
        return (int(user_id_param) if user_id_param else None), None

    if user_id_param is None:
        return caller.id, None

    try:
        requested_uid = int(user_id_param)
    except ValueError:
        return None, _error(400, 'bad_request', 'user_id must be an integer.')

    if requested_uid == caller.id:
        return requested_uid, None
    return None, _error(403, 'forbidden', denied_detail)


def _build_list_domain(company_id, filter_user_id, params):
    domain = [('active', '=', True), ('company_id', '=', company_id)]
    if filter_user_id:
        domain.append(('user_id', '=', filter_user_id))

    for param, field in [
        ('year', 'year'),
        ('month', 'month'),
        ('metric_type', 'metric_type'),
        ('operation_type', 'operation_type'),
    ]:
        value = params.get(param)
        if value:
            domain.append((field, '=', int(value) if param in ('year', 'month') else value))
    return domain


def _parse_pagination(params):
    try:
        limit = int(params.get('limit', 50))
        offset = int(params.get('offset', 0))
    except (ValueError, TypeError):
        return None, None, _error(400, 'bad_request', 'limit and offset must be integers.')

    if 1 <= limit <= 200:
        return limit, offset, None
    return None, None, _error(400, 'bad_request', 'limit must be between 1 and 200.')


def _resolve_profile_group(profile_param):
    if not profile_param:
        return None, None

    if len(profile_param) > 128 or not _PROFILE_PATTERN.match(profile_param):
        return None, _error(
            400,
            'bad_request',
            'Invalid profile format. Expected: module.xml_id',
        )

    try:
        return request.env.ref(profile_param), None
    except ValueError:
        return None, _error(400, 'bad_request', f'Profile "{profile_param}" not found.')


def _get_company_user_ids(company_id):
    users = request.env['res.users'].sudo().search([
        ('company_id', '=', company_id),
        ('active', '=', True),
        ('share', '=', False),
    ])
    return users.ids


def _resolve_report_user_ids(caller, caller_profile, user_id_param):
    if caller_profile == 'agent':
        user_id, response = _resolve_goal_filter_user_id(
            caller,
            caller_profile,
            user_id_param,
            'Agents may only view their own report.',
        )
        if response:
            return None, response
        return [user_id], None

    if user_id_param:
        try:
            return [int(user_id_param)], None
        except ValueError:
            return None, _error(400, 'bad_request', 'user_id must be an integer.')

    return _get_company_user_ids(caller.company_id.id), None


def _filter_user_ids_by_profile(user_ids, profile_group):
    if not profile_group:
        return user_ids
    users = request.env['res.users'].sudo().browse(user_ids)
    return [user.id for user in users if profile_group.id in user.groups_id.ids]


def _filter_report_rows(users_rows, goal_status_filter):
    if goal_status_filter == 'complete':
        return [row for row in users_rows if row.get('goal_status') == 'complete']
    if goal_status_filter == 'incomplete':
        return [
            row for row in users_rows
            if row.get('goal_status') in ('in_progress', 'no_goals')
        ]
    return users_rows


class GoalsController(http.Controller):

    # ─────────────────────────────────────────────────────────────────────────
    # POST /api/v1/goals  —  Create Goal (T013)
    # ─────────────────────────────────────────────────────────────────────────
    @http.route(
        '/api/v1/goals',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
        cors='*',
    )
    @require_jwt
    @require_session
    @require_company
    def create_goal(self, **kwargs):
        try:
            caller = request.env.user
            caller_profile = resolve_role(caller) or 'unknown'

            response = _ensure_manager_profile(caller_profile, 'create')
            if response:
                return response

            data, response = _parse_json_body()
            if response:
                return response

            vals, response = _build_create_vals(data, caller.company_id.id)
            if response:
                return response

            response = _validate_create_vals(vals)
            if response:
                return response

            goal, response = _create_goal_record(vals)
            if response:
                return response

            return _ok(201, _goal_response_body(goal))

        except Exception as exc:
            _logger.exception('goals create_goal error: %s', exc)
            return _error(500, 'internal_error', 'An unexpected error occurred.')

    # ─────────────────────────────────────────────────────────────────────────
    # PUT /api/v1/goals/<goal_id>  —  Update Goal (T014)
    # ─────────────────────────────────────────────────────────────────────────
    @http.route(
        '/api/v1/goals/<int:goal_id>',
        type='http',
        auth='none',
        methods=['PUT'],
        csrf=False,
        cors='*',
    )
    @require_jwt
    @require_session
    @require_company
    def update_goal(self, goal_id, **kwargs):
        try:
            caller = request.env.user
            caller_profile = resolve_role(caller) or 'unknown'

            response = _ensure_manager_profile(caller_profile, 'update')
            if response:
                return response

            goal, response = _get_active_goal(goal_id, caller.company_id.id, 'Goal not found.')
            if response:
                return response

            data, response = _parse_json_body()
            if response:
                return response

            vals, response = _build_update_vals(data)
            if response:
                return response

            try:
                goal.sudo().write(vals)
            except ValidationError as exc:
                return _error(422, 'unprocessable_entity', str(exc))

            return _ok(200, _goal_response_body(goal))

        except Exception as exc:
            _logger.exception('goals update_goal error: %s', exc)
            return _error(500, 'internal_error', 'An unexpected error occurred.')

    # ─────────────────────────────────────────────────────────────────────────
    # DELETE /api/v1/goals/<goal_id>  —  Soft-delete Goal (T015)
    # ─────────────────────────────────────────────────────────────────────────
    @http.route(
        '/api/v1/goals/<int:goal_id>',
        type='http',
        auth='none',
        methods=['DELETE'],
        csrf=False,
        cors='*',
    )
    @require_jwt
    @require_session
    @require_company
    def delete_goal(self, goal_id, **kwargs):
        try:
            caller = request.env.user
            caller_profile = resolve_role(caller) or 'unknown'

            if caller_profile not in _MANAGER_PROFILES:
                return _error(403, 'forbidden', 'Only Owner, Director, or Manager may delete goals.')

            goal = request.env['thedevkitchen.estate.goal'].sudo().search(
                [('id', '=', goal_id), ('active', '=', True), ('company_id', '=', caller.company_id.id)],
                limit=1,
            )
            if not goal:
                return _error(404, 'not_found', 'Goal not found or already inactive.')

            goal.sudo().write({'active': False})

            return _ok(200, {
                'id': goal.id,
                'active': False,
                'message': 'Goal archived successfully',
                'links': {
                    'collection': '/api/v1/goals',
                },
            })

        except Exception as e:
            _logger.exception('goals delete_goal error: %s', e)
            return _error(500, 'internal_error', 'An unexpected error occurred.')

    # ─────────────────────────────────────────────────────────────────────────
    # GET /api/v1/goals  —  List Goals (T016)
    # ─────────────────────────────────────────────────────────────────────────
    @http.route(
        '/api/v1/goals',
        type='http',
        auth='none',
        methods=['GET'],
        csrf=False,
        cors='*',
    )
    @require_jwt
    @require_session
    @require_company
    def list_goals(self, **kwargs):
        try:
            caller = request.env.user
            caller_profile = resolve_role(caller)

            # SEC-2: Receptionist and Prospector → 403 immediately
            if caller_profile in _BLOCKED_PROFILES:
                return _error(403, 'forbidden', 'Access denied for this profile.')

            params = request.httprequest.args
            user_id_param = params.get('user_id')
            filter_user_id, response = _resolve_goal_filter_user_id(
                caller,
                caller_profile,
                user_id_param,
                'Agents may only view their own goals.',
            )
            if response:
                return response

            domain = _build_list_domain(caller.company_id.id, filter_user_id, params)
            limit, offset, response = _parse_pagination(params)
            if response:
                return response

            total = request.env['thedevkitchen.estate.goal'].sudo().search_count(domain)
            goals = request.env['thedevkitchen.estate.goal'].sudo().search(
                domain, limit=limit, offset=offset
            )
            results = [_goal_to_dict(g) for g in goals]

            return _ok(200, {
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                },
                'results': results,
                'links': {'self': '/api/v1/goals'},
            })

        except Exception as exc:
            _logger.exception('goals list_goals error: %s', exc)
            return _error(500, 'internal_error', 'An unexpected error occurred.')

    # ─────────────────────────────────────────────────────────────────────────
    # GET /api/v1/goals/report  —  Goals Report (T028, T034, T045)
    # ─────────────────────────────────────────────────────────────────────────
    @http.route(
        '/api/v1/goals/report',
        type='http',
        auth='none',
        methods=['GET'],
        csrf=False,
        cors='*',
    )
    @require_jwt
    @require_session
    @require_company
    def goals_report(self, **kwargs):
        try:
            caller = request.env.user
            caller_profile = resolve_role(caller)
            params = request.httprequest.args

            if caller_profile in _BLOCKED_PROFILES:
                return _error(403, 'forbidden', 'Access denied for this profile.')

            year_param = params.get('year')
            month_param = params.get('month')
            date_from_param = params.get('date_from')
            date_to_param = params.get('date_to')
            operation_type = params.get('operation_type', 'all')
            goal_status_filter = params.get('goal_status')
            profile_param = params.get('profile')
            user_id_param = params.get('user_id')

            profile_group, response = _resolve_profile_group(profile_param)
            if response:
                return response

            user_ids, response = _resolve_report_user_ids(caller, caller_profile, user_id_param)
            if response:
                return response

            user_ids = _filter_user_ids_by_profile(user_ids, profile_group)
            if len(user_ids) > 200:
                return _error(
                    422,
                    'unprocessable_entity',
                    f'Report exceeds maximum of 200 users. Found {len(user_ids)}. Apply stricter filters.',
                )

            try:
                report = GoalsReportService.compute_report(
                    env=request.env,
                    company_id=caller.company_id.id,
                    user_ids=user_ids,
                    year=int(year_param) if year_param else None,
                    month=int(month_param) if month_param else None,
                    date_from=date_from_param,
                    date_to=date_to_param,
                    operation_type=operation_type,
                )
            except ValidationError as exc:
                return _error(400, 'bad_request', str(exc))

            users_rows = _filter_report_rows(report.get('users', []), goal_status_filter)
            totals = GoalsReportService.compute_totals(users_rows)

            response_body = {
                'users': users_rows,
                'totals': totals,
                'period': report.get('period', {}),
                'filters': {
                    'operation_type': operation_type,
                    'user_id': int(user_id_param) if user_id_param else None,
                    'profile': profile_param,
                    'goal_status': goal_status_filter,
                },
            }
            return _ok(200, response_body)

        except Exception as exc:
            _logger.exception('goals goals_report error: %s', exc)
            return _error(500, 'internal_error', 'An unexpected error occurred.')
