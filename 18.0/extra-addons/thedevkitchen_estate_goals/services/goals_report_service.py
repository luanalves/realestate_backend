# -*- coding: utf-8 -*-
import logging
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError
from odoo.addons.quicksol_estate.services.role_resolver import resolve_role

_logger = logging.getLogger(__name__)

# All 5 funnel metrics (plural Portuguese keys used in response JSON)
METRICS = ['captacoes', 'novos_clientes', 'visitas', 'propostas', 'fechamento']

# Metric keys that support VGV (volume gross value)
VGV_METRICS = {'captacoes', 'propostas', 'fechamento'}

# Map goal metric_type DB values → response JSON keys
METRIC_TYPE_TO_KEY = {
    'captacao':      'captacoes',
    'novos_clientes': 'novos_clientes',
    'visitas':       'visitas',
    'propostas':     'propostas',
    'fechamento':    'fechamento',
}

# Reverse map: response key → goal metric_type value
KEY_TO_METRIC_TYPE = {v: k for k, v in METRIC_TYPE_TO_KEY.items()}

# Map operation_type param → proposal_type DB value (D004 mapping)
OP_TYPE_TO_PROPOSAL_TYPE = {'sale': 'sale', 'rent': 'lease', 'all': None}


def _empty_metric():
    return {
        'meta_count': None,
        'conquista': 0,
        'meta_vgv': None,
        'conquista_vgv': 0.0,
        'completion_pct': None,
    }


class GoalsReportService:

    @staticmethod
    def compute_report(env, company_id, user_ids, year=None, month=None,
                       date_from=None, date_to=None, operation_type='all'):
        """Main entry point — returns the full report dict."""
        # SEC-1: Guard against empty user_ids (prevents IN () SQL crash)
        if not user_ids:
            return {
                'users': [],
                'totals': {m: _empty_metric() for m in METRICS},
                'period': {},
            }

        # Resolve period
        date_from_dt, date_to_dt, period_info = GoalsReportService._resolve_period(
            year, month, date_from, date_to
        )

        # Load goals for all users in period
        goals = GoalsReportService._load_goals(
            env, company_id, user_ids, date_from_dt, date_to_dt, operation_type
        )

        # Compute achievements from domain entities
        achievements = GoalsReportService._compute_achievements(
            env, company_id, user_ids, date_from_dt, date_to_dt, operation_type
        )

        # Build per-user rows
        user_rows = []
        for uid in user_ids:
            row = GoalsReportService._compute_user_row(
                env, uid, goals.get(uid, {}), achievements.get(uid, {})
            )
            user_rows.append(row)

        totals = GoalsReportService.compute_totals(user_rows)

        return {
            'users': user_rows,
            'totals': totals,
            'period': period_info,
        }

    @staticmethod
    def compute_totals(user_rows):
        """Aggregate per-metric totals across all user rows."""
        totals = {}
        for metric in METRICS:
            conquista_sum = 0
            meta_count_sum = None
            conquista_vgv_sum = None
            meta_vgv_sum = None

            for row in user_rows:
                m = row.get('metrics', {}).get(metric, _empty_metric())

                conquista_sum += (m.get('conquista') or 0)

                mc = m.get('meta_count')
                if mc is not None:
                    meta_count_sum = (meta_count_sum or 0) + mc

                if metric in VGV_METRICS:
                    cvgv = m.get('conquista_vgv')
                    if cvgv is not None:
                        conquista_vgv_sum = (conquista_vgv_sum or 0.0) + cvgv

                    mvgv = m.get('meta_vgv')
                    if mvgv is not None:
                        meta_vgv_sum = (meta_vgv_sum or 0.0) + mvgv

            totals[metric] = {
                'conquista': conquista_sum,
                'meta_count': meta_count_sum,
                'conquista_vgv': conquista_vgv_sum,
                'meta_vgv': meta_vgv_sum,
            }
        return totals

    # ─────────────────────────────────────────────────────────────────────────
    # Period resolution (T026)
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _resolve_period(year, month, date_from, date_to):
        """Return (date_from_dt, date_to_dt, period_info_dict)."""
        if date_from and date_to:
            return GoalsReportService._resolve_accumulated_period(date_from, date_to)
        return GoalsReportService._resolve_single_month_period(year, month)

    @staticmethod
    def _resolve_accumulated_period(date_from, date_to):
        try:
            date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
            date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
        except ValueError:
            raise ValidationError('date_from and date_to must be in YYYY-MM-DD format.')

        if date_to_dt < date_from_dt:
            raise ValidationError('date_to must be >= date_from.')
        if (date_to_dt - date_from_dt).days > 366:
            raise ValidationError('Date range exceeds maximum of 366 days (12 months).')

        return date_from_dt, date_to_dt + timedelta(days=1), {
            'mode': 'accumulated',
            'date_from': date_from,
            'date_to': date_to,
        }

    @staticmethod
    def _resolve_single_month_period(year, month):
        year_value, month_value = GoalsReportService._coerce_year_month(year, month)
        next_month = GoalsReportService._get_next_month_start(year_value, month_value)
        return datetime(year_value, month_value, 1), datetime(
            next_month.year,
            next_month.month,
            next_month.day,
        ), {
            'mode': 'single_month',
            'year': year_value,
            'month': month_value,
        }

    @staticmethod
    def _coerce_year_month(year, month):
        if not year:
            raise ValidationError('year is required when date_from/date_to are not provided.')
        if not month:
            raise ValidationError('month is required when date_from/date_to are not provided.')

        try:
            year_value = int(year)
            month_value = int(month)
        except (ValueError, TypeError):
            raise ValidationError('year and month must be integers.')

        if 1 <= month_value <= 12:
            return year_value, month_value
        raise ValidationError('month must be between 1 and 12.')

    @staticmethod
    def _get_next_month_start(year, month):
        if month == 12:
            return date(year + 1, 1, 1)
        return date(year, month + 1, 1)

    # ─────────────────────────────────────────────────────────────────────────
    # Goal loading
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _load_goals(env, company_id, user_ids, date_from_dt, date_to_dt, operation_type):
        """
        Load goal records for the given users and period.
        Returns {user_id: {metric_key: goal_record}} dict.
        """
        # Determine year/month range from date window
        df_date = date_from_dt.date() if hasattr(date_from_dt, 'date') else date_from_dt
        dt_date = (date_to_dt - timedelta(seconds=1)).date() if hasattr(date_to_dt, 'date') else date_to_dt

        domain = [
            ('active', '=', True),
            ('company_id', '=', company_id),
            ('user_id', 'in', user_ids),
        ]

        # operation_type filter: when sale/rent, exclude 'all' goals (D007)
        if operation_type in ('sale', 'rent'):
            domain.append(('operation_type', '=', operation_type))

        # Filter goals that fall within the date range (by year/month)
        start_year, start_month = df_date.year, df_date.month
        end_year, end_month = dt_date.year, dt_date.month

        # Build year-month range
        period_months = []
        y, m = start_year, start_month
        while (y, m) <= (end_year, end_month):
            period_months.append((y, m))
            if m == 12:
                y, m = y + 1, 1
            else:
                m += 1

        if len(period_months) == 1:
            y, mo = period_months[0]
            domain.extend([('year', '=', y), ('month', '=', mo)])
        else:
            # Multi-month: use tuple domain
            # Simplified: filter year in range; refine with month in Python if needed
            start_y = period_months[0][0]
            end_y = period_months[-1][0]
            if start_y == end_y:
                domain.extend([
                    ('year', '=', start_y),
                    ('month', '>=', period_months[0][1]),
                    ('month', '<=', period_months[-1][1]),
                ])
            else:
                domain.append(('year', '>=', start_y))
                domain.append(('year', '<=', end_y))

        goals = env['thedevkitchen.estate.goal'].sudo().search(domain)

        result = {}
        for goal in goals:
            uid = goal.user_id.id
            if uid not in result:
                result[uid] = {}
            metric_key = METRIC_TYPE_TO_KEY.get(goal.metric_type, goal.metric_type)
            # Sum across months for accumulated mode
            existing = result[uid].get(metric_key)
            if existing is None:
                result[uid][metric_key] = goal
            else:
                # Accumulated: keep separate for multi-month — stored as list
                if isinstance(existing, list):
                    existing.append(goal)
                else:
                    result[uid][metric_key] = [existing, goal]

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Achievement computation
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _compute_achievements(env, company_id, user_ids, date_from_dt, date_to_dt, operation_type):
        """Runs all 5 SQL queries and merges results into {user_id: {metric_key: {...}}}."""
        result = {}

        captacao = GoalsReportService._query_captacao(env, company_id, user_ids, date_from_dt, date_to_dt, operation_type)
        novos = GoalsReportService._query_novos_clientes(env, company_id, user_ids, date_from_dt, date_to_dt, operation_type)
        visitas = GoalsReportService._query_visitas(env, company_id, user_ids, date_from_dt, date_to_dt, operation_type)
        propostas = GoalsReportService._query_propostas(env, company_id, user_ids, date_from_dt, date_to_dt, operation_type)
        fechamento = GoalsReportService._query_fechamento(env, company_id, user_ids, date_from_dt, date_to_dt, operation_type)

        for uid in user_ids:
            result[uid] = {
                'captacoes': captacao.get(uid, {'count': 0, 'vgv': 0.0}),
                'novos_clientes': novos.get(uid, {'count': 0}),
                'visitas': visitas.get(uid, {'count': 0}),
                'propostas': propostas.get(uid, {'count': 0, 'vgv': 0.0}),
                'fechamento': fechamento.get(uid, {'count': 0, 'vgv': 0.0}),
            }

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # SQL query methods (T021-T025)
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _query_captacao(env, company_id, user_ids, date_from_dt, date_to_dt, operation_type):
        """Count captações (property registrations) and VGV per user (D003)."""
        cr = env.cr

        if operation_type == 'sale':
            flag_filter = 'rp.for_sale = true'
            price_field = 'rp.price'
        elif operation_type == 'rent':
            flag_filter = 'rp.for_rent = true'
            price_field = 'rp.rent_price'
        else:
            # all: count for_sale OR for_rent; VGV = sum(price where for_sale) + sum(rent_price where for_rent)
            flag_filter = '(rp.for_sale = true OR rp.for_rent = true)'
            price_field = '(CASE WHEN rp.for_sale THEN rp.price ELSE 0 END + CASE WHEN rp.for_rent THEN rp.rent_price ELSE 0 END)'

        cr.execute(f"""
            SELECT rea.user_id, COUNT(rp.id) AS count, SUM({price_field}) AS vgv
            FROM real_estate_property rp
            JOIN real_estate_agent rea ON rea.id = rp.agent_id
            WHERE {flag_filter}
              AND rp.create_date >= %(date_from)s
              AND rp.create_date <  %(date_to)s
              AND rp.company_id = %(company_id)s
              AND rea.user_id IN %(user_ids)s
            GROUP BY rea.user_id
        """, {
            'date_from': date_from_dt,
            'date_to': date_to_dt,
            'company_id': company_id,
            'user_ids': tuple(user_ids),
        })

        return {row[0]: {'count': row[1], 'vgv': float(row[2] or 0)} for row in cr.fetchall()}

    @staticmethod
    def _query_novos_clientes(env, company_id, user_ids, date_from_dt, date_to_dt, operation_type):
        """Count new services (novos clientes) per user (D005 — direct FK to res.users)."""
        cr = env.cr

        params = {
            'date_from': date_from_dt,
            'date_to': date_to_dt,
            'company_id': company_id,
            'user_ids': tuple(user_ids),
        }

        op_filter = ''
        if operation_type in ('sale', 'rent'):
            op_filter = 'AND rs.operation_type = %(operation_type)s'
            params['operation_type'] = operation_type

        cr.execute(f"""
            SELECT rs.agent_id AS user_id, COUNT(rs.id) AS count
            FROM real_estate_service rs
            WHERE rs.create_date >= %(date_from)s
              AND rs.create_date <  %(date_to)s
              AND rs.company_id = %(company_id)s
              AND rs.agent_id IN %(user_ids)s
              {op_filter}
            GROUP BY rs.agent_id
        """, params)

        return {row[0]: {'count': row[1]} for row in cr.fetchall()}

    @staticmethod
    def _query_visitas(env, company_id, user_ids, date_from_dt, date_to_dt, operation_type):
        """Count distinct services with a visit stage transition per user (D002)."""
        cr = env.cr

        cr.execute("""
            SELECT rs.agent_id AS user_id, COUNT(DISTINCT rs.id) AS count
            FROM real_estate_service rs
            JOIN mail_message mm
              ON mm.res_id = rs.id
             AND mm.model = 'real.estate.service'
            JOIN mail_tracking_value mtv
              ON mtv.mail_message_id = mm.id
            JOIN ir_model_fields imf
              ON imf.id = mtv.field_id
             AND imf.name = 'stage'
            WHERE mtv.new_value_char = 'visit'
              AND mtv.create_date >= %(date_from)s
              AND mtv.create_date <  %(date_to)s
              AND rs.company_id = %(company_id)s
              AND rs.agent_id IN %(user_ids)s
            GROUP BY rs.agent_id
        """, {
            'date_from': date_from_dt,
            'date_to': date_to_dt,
            'company_id': company_id,
            'user_ids': tuple(user_ids),
        })

        return {row[0]: {'count': row[1]} for row in cr.fetchall()}

    @staticmethod
    def _query_propostas(env, company_id, user_ids, date_from_dt, date_to_dt, operation_type):
        """Count proposals and VGV per user (D004 — two-hop via real.estate.agent)."""
        cr = env.cr

        proposal_type = OP_TYPE_TO_PROPOSAL_TYPE.get(operation_type)
        params = {
            'date_from': date_from_dt,
            'date_to': date_to_dt,
            'company_id': company_id,
            'user_ids': tuple(user_ids),
        }

        type_filter = ''
        if proposal_type is not None:
            type_filter = 'AND rpr.proposal_type = %(proposal_type)s'
            params['proposal_type'] = proposal_type

        cr.execute(f"""
            SELECT rea.user_id, COUNT(rpr.id) AS count, SUM(rpr.proposal_value) AS vgv
            FROM real_estate_proposal rpr
            JOIN real_estate_agent rea ON rea.id = rpr.agent_id
            WHERE rpr.create_date >= %(date_from)s
              AND rpr.create_date <  %(date_to)s
              AND rpr.company_id = %(company_id)s
              AND rea.user_id IN %(user_ids)s
              {type_filter}
            GROUP BY rea.user_id
        """, params)

        return {row[0]: {'count': row[1], 'vgv': float(row[2] or 0)} for row in cr.fetchall()}

    @staticmethod
    def _query_fechamento(env, company_id, user_ids, date_from_dt, date_to_dt, operation_type):
        """
        Count won services (fechamento) + VGV from accepted proposals (D004 / D005).
        ⚠️ Assumes real_estate_proposal.service_id FK exists (verify with \\d real_estate_proposal).
        """
        cr = env.cr

        # Check if service_id column exists on real_estate_proposal
        cr.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'real_estate_proposal' AND column_name = 'service_id'
        """)
        has_service_id = bool(cr.fetchone())

        if has_service_id:
            join_clause = "LEFT JOIN real_estate_proposal rpr ON rpr.service_id = rs.id AND rpr.state = 'accepted'"
            vgv_field = 'SUM(rpr.proposal_value)'
        else:
            # Fallback: no VGV (service_id FK absent — see research.md D004-addendum)
            _logger.warning(
                'real_estate_proposal.service_id not found — fechamento VGV will be 0. '
                'See research.md D004-addendum.'
            )
            join_clause = ''
            vgv_field = '0'

        cr.execute(f"""
            SELECT rs.agent_id AS user_id,
                   COUNT(DISTINCT rs.id) AS count,
                   {vgv_field} AS vgv
            FROM real_estate_service rs
            JOIN mail_message mm
              ON mm.res_id = rs.id
             AND mm.model = 'real.estate.service'
            JOIN mail_tracking_value mtv
              ON mtv.mail_message_id = mm.id
            JOIN ir_model_fields imf
              ON imf.id = mtv.field_id
             AND imf.name = 'stage'
            {join_clause}
            WHERE mtv.new_value_char = 'won'
              AND mtv.create_date >= %(date_from)s
              AND mtv.create_date <  %(date_to)s
              AND rs.company_id = %(company_id)s
              AND rs.agent_id IN %(user_ids)s
            GROUP BY rs.agent_id
        """, {
            'date_from': date_from_dt,
            'date_to': date_to_dt,
            'company_id': company_id,
            'user_ids': tuple(user_ids),
        })

        return {row[0]: {'count': row[1], 'vgv': float(row[2] or 0)} for row in cr.fetchall()}

    # ─────────────────────────────────────────────────────────────────────────
    # Per-user row computation (T027)
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _compute_user_row(env, user_id, user_goals, user_achievements):
        """
        Build a single user report row merging goals with achievements.
        user_goals: {metric_key: goal_record_or_list}
        user_achievements: {metric_key: {'count': N, 'vgv': V}}
        """
        user = env['res.users'].sudo().browse(user_id)

        # Resolve profile label
        resolved_role = resolve_role(user)
        profile_label = resolved_role.capitalize() if resolved_role else None

        metrics = {}
        has_any_goal = False
        all_met = True

        for metric_key in METRICS:
            achievement = user_achievements.get(metric_key, {})
            conquista = achievement.get('count', 0)
            conquista_vgv = achievement.get('vgv', 0.0) if metric_key in VGV_METRICS else None

            goal_data = user_goals.get(metric_key)

            if goal_data is None:
                # No goal set for this metric
                metric_entry = {
                    'meta_count': None,
                    'conquista': conquista,
                    'meta_vgv': None,
                    'conquista_vgv': conquista_vgv,
                    'completion_pct': None,
                }
            else:
                has_any_goal = True

                # Handle accumulated (list) vs single goal record
                if isinstance(goal_data, list):
                    target_count = sum(g.target_count for g in goal_data)
                    target_vgv = sum(g.target_vgv or 0 for g in goal_data) or None
                else:
                    target_count = goal_data.target_count
                    target_vgv = goal_data.target_vgv or None

                completion_pct = None
                if target_count > 0:
                    completion_pct = round((conquista / target_count) * 100, 2)
                # target_count == 0 → spec §FR3.3: return null (no measurable target)

                # Check if this goal is met for goal_status determination
                if conquista < target_count:
                    all_met = False

                metric_entry = {
                    'meta_count': target_count,
                    'conquista': conquista,
                    'meta_vgv': float(target_vgv) if target_vgv else None,
                    'conquista_vgv': conquista_vgv,
                    'completion_pct': completion_pct,
                }

            metrics[metric_key] = metric_entry

        # D009: goal_status
        if not has_any_goal:
            goal_status = 'no_goals'
        elif all_met:
            goal_status = 'complete'
        else:
            goal_status = 'in_progress'

        return {
            'user_id': user_id,
            'user_name': user.name,
            'profile': profile_label,
            'goal_status': goal_status,
            'metrics': metrics,
        }
