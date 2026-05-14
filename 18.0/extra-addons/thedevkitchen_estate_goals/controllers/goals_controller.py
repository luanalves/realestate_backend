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
from ..services.goals_report_service import GoalsReportService

_logger = logging.getLogger(__name__)

# Profiles that may NOT access goal endpoints
_BLOCKED_PROFILES = {'receptionist', 'prospector'}

# Profiles that may manage (create/update/delete) goals
_MANAGER_PROFILES = {'owner', 'director', 'manager'}

# Group XML ID → profile label mapping (descending hierarchy)
_GROUP_TO_PROFILE = [
    ('quicksol_estate.group_real_estate_owner',       'owner'),
    ('quicksol_estate.group_real_estate_director',    'director'),
    ('quicksol_estate.group_real_estate_manager',     'manager'),
    ('quicksol_estate.group_real_estate_agent',       'agent'),
    ('quicksol_estate.group_real_estate_prospector',  'prospector'),
    ('quicksol_estate.group_real_estate_receptionist','receptionist'),
    ('quicksol_estate.group_real_estate_financial',   'financial'),
    ('quicksol_estate.group_real_estate_legal',       'legal'),
]

# Profile XML ID validation pattern (SEC-9)
_PROFILE_PATTERN = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+$')


def _get_caller_profile(user):
    """Resolve the caller's RBAC profile label from their group membership."""
    for xml_id, label in _GROUP_TO_PROFILE:
        try:
            group = request.env.ref(xml_id)
            if group.id in user.groups_id.ids:
                return label
        except ValueError:
            continue
    return 'unknown'


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
            caller_profile = _get_caller_profile(caller)

            if caller_profile not in _MANAGER_PROFILES:
                return _error(403, 'forbidden', 'Only Owner, Director, or Manager may create goals.')

            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return _error(400, 'bad_request', 'Invalid JSON in request body.')

            required = ['user_id', 'year', 'month', 'metric_type', 'operation_type', 'target_count']
            missing = [f for f in required if f not in data or data[f] is None]
            if missing:
                return _error(400, 'bad_request', f'Missing required fields: {", ".join(missing)}')

            vals = {
                'user_id': int(data['user_id']),
                'year': int(data['year']),
                'month': int(data['month']),
                'metric_type': data['metric_type'],
                'operation_type': data['operation_type'],
                'target_count': int(data['target_count']),
                'company_id': caller.company_id.id,
            }
            if 'target_vgv' in data and data['target_vgv'] is not None:
                vals['target_vgv'] = float(data['target_vgv'])

            # Validate month range at Python level (SQL CHECK raises IntegrityError)
            month = vals['month']
            if month < 1 or month > 12:
                return _error(422, 'unprocessable_entity', f'Month must be between 1 and 12, got {month}.')
            year = vals['year']
            if year < 2000:
                return _error(422, 'unprocessable_entity', f'Year must be >= 2000, got {year}.')

            try:
                goal = request.env['thedevkitchen.estate.goal'].sudo().create(vals)
            except IntegrityError:
                request.env.cr.rollback()
                return _error(409, 'conflict', 'A goal for this user/period/metric/operation already exists.')
            except ValidationError as e:
                return _error(422, 'unprocessable_entity', str(e))

            body = _goal_to_dict(goal)
            body['links'] = {
                'self': f'/api/v1/goals/{goal.id}',
                'collection': '/api/v1/goals',
            }
            return _ok(201, body)

        except Exception as e:
            _logger.exception('goals create_goal error: %s', e)
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
            caller_profile = _get_caller_profile(caller)

            if caller_profile not in _MANAGER_PROFILES:
                return _error(403, 'forbidden', 'Only Owner, Director, or Manager may update goals.')

            goal = request.env['thedevkitchen.estate.goal'].sudo().search(
                [('id', '=', goal_id), ('active', '=', True), ('company_id', '=', caller.company_id.id)],
                limit=1,
            )
            if not goal:
                return _error(404, 'not_found', 'Goal not found.')

            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return _error(400, 'bad_request', 'Invalid JSON in request body.')

            vals = {}
            if 'target_count' in data and data['target_count'] is not None:
                vals['target_count'] = int(data['target_count'])
            if 'target_vgv' in data:
                vals['target_vgv'] = float(data['target_vgv']) if data['target_vgv'] is not None else False

            if not vals:
                return _error(400, 'bad_request', 'At least one of target_count or target_vgv must be provided.')

            try:
                goal.sudo().write(vals)
            except ValidationError as e:
                return _error(422, 'unprocessable_entity', str(e))

            body = _goal_to_dict(goal)
            body['links'] = {
                'self': f'/api/v1/goals/{goal.id}',
                'collection': '/api/v1/goals',
            }
            return _ok(200, body)

        except Exception as e:
            _logger.exception('goals update_goal error: %s', e)
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
            caller_profile = _get_caller_profile(caller)

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
            caller_profile = _get_caller_profile(caller)

            # SEC-2: Receptionist and Prospector → 403 immediately
            if caller_profile in _BLOCKED_PROFILES:
                return _error(403, 'forbidden', 'Access denied for this profile.')

            params = request.httprequest.args

            # SEC-3: Agent RBAC
            user_id_param = params.get('user_id')
            if caller_profile == 'agent':
                if user_id_param is not None:
                    try:
                        requested_uid = int(user_id_param)
                    except ValueError:
                        return _error(400, 'bad_request', 'user_id must be an integer.')
                    if requested_uid != caller.id:
                        return _error(403, 'forbidden', 'Agents may only view their own goals.')
                    filter_user_id = requested_uid
                else:
                    filter_user_id = caller.id
            else:
                filter_user_id = int(user_id_param) if user_id_param else None

            domain = [('active', '=', True), ('company_id', '=', caller.company_id.id)]
            if filter_user_id:
                domain.append(('user_id', '=', filter_user_id))

            for param, field in [('year', 'year'), ('month', 'month'),
                                  ('metric_type', 'metric_type'), ('operation_type', 'operation_type')]:
                val = params.get(param)
                if val:
                    domain.append((field, '=', int(val) if param in ('year', 'month') else val))

            goals = request.env['thedevkitchen.estate.goal'].sudo().search(domain)
            results = [_goal_to_dict(g) for g in goals]

            return _ok(200, {
                'count': len(results),
                'results': results,
                'links': {'self': '/api/v1/goals'},
            })

        except Exception as e:
            _logger.exception('goals list_goals error: %s', e)
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
            caller_profile = _get_caller_profile(caller)
            params = request.httprequest.args

            # SEC-2: Blocked profiles
            if caller_profile in _BLOCKED_PROFILES:
                return _error(403, 'forbidden', 'Access denied for this profile.')

            # ── Period parameters ───────────────────────────────────────────
            year_param = params.get('year')
            month_param = params.get('month')
            date_from_param = params.get('date_from')
            date_to_param = params.get('date_to')
            operation_type = params.get('operation_type', 'all')
            goal_status_filter = params.get('goal_status')

            # ── Profile param validation (SEC-9) ───────────────────────────
            profile_param = params.get('profile')
            profile_group = None
            if profile_param:
                if len(profile_param) > 128 or not _PROFILE_PATTERN.match(profile_param):
                    return _error(400, 'bad_request', 'Invalid profile format. Expected: module.xml_id')
                try:
                    profile_group = request.env.ref(profile_param)
                except ValueError:
                    return _error(400, 'bad_request', f'Profile "{profile_param}" not found.')

            # ── user_id param + RBAC ────────────────────────────────────────
            user_id_param = params.get('user_id')
            if caller_profile == 'agent':
                if user_id_param is not None:
                    try:
                        requested_uid = int(user_id_param)
                    except ValueError:
                        return _error(400, 'bad_request', 'user_id must be an integer.')
                    if requested_uid != caller.id:
                        return _error(403, 'forbidden', 'Agents may only view their own report.')
                    user_ids = [requested_uid]
                else:
                    user_ids = [caller.id]
            else:
                if user_id_param:
                    try:
                        user_ids = [int(user_id_param)]
                    except ValueError:
                        return _error(400, 'bad_request', 'user_id must be an integer.')
                else:
                    # All active users in company
                    all_users = request.env['res.users'].sudo().search([
                        ('company_id', '=', caller.company_id.id),
                        ('active', '=', True),
                        ('share', '=', False),
                    ])
                    user_ids = all_users.ids

            # Apply profile group filter if provided
            if profile_group:
                filtered = [
                    uid for uid in user_ids
                    if profile_group.id in request.env['res.users'].sudo().browse(uid).groups_id.ids
                ]
                user_ids = filtered

            # ── User count hard cap (D006) ──────────────────────────────────
            if len(user_ids) > 200:
                return _error(422, 'unprocessable_entity',
                              f'Report exceeds maximum of 200 users. Found {len(user_ids)}. Apply stricter filters.')

            # ── Compute report via service ──────────────────────────────────
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
            except ValidationError as e:
                return _error(400, 'bad_request', str(e))

            # ── goal_status filter (T034) ───────────────────────────────────
            users_rows = report.get('users', [])
            if goal_status_filter == 'complete':
                users_rows = [r for r in users_rows if r.get('goal_status') == 'complete']
            elif goal_status_filter == 'incomplete':
                users_rows = [r for r in users_rows if r.get('goal_status') in ('in_progress', 'no_goals')]

            # Recompute totals on filtered set
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

        except Exception as e:
            _logger.exception('goals goals_report error: %s', e)
            return _error(500, 'internal_error', 'An unexpected error occurred.')
