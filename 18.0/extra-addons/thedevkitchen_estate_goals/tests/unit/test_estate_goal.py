# -*- coding: utf-8 -*-
"""
Unit Tests: Estate Goal (Feature 019)

Covers:
- T017: Model constraint tests (unique, non-negative, month range, year, VGV)
- T029: Period resolution and goal_status computation
- T047: SQL query method unit tests

ADRs: ADR-003 (Testing Standards)
"""
from datetime import date, datetime
from unittest.mock import patch, MagicMock
from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError


class TestEstateGoalConstraints(TransactionCase):
    """T017 — Model constraint tests."""

    def setUp(self):
        super().setUp()
        self.GoalModel = self.env['thedevkitchen.estate.goal']
        self.user = self.env.ref('base.user_admin')
        self.company = self.env.ref('base.main_company')
        self._base_vals = {
            'user_id': self.user.id,
            'year': 2026,
            'month': 5,
            'metric_type': 'captacao',
            'operation_type': 'sale',
            'target_count': 10,
            'company_id': self.company.id,
        }

    def _create(self, **overrides):
        vals = dict(self._base_vals, **overrides)
        return self.GoalModel.sudo().create(vals)

    def test_goal_unique_constraint(self):
        """IntegrityError on duplicate (user, year, month, metric, operation)."""
        self._create()
        with self.assertRaises(Exception):
            self._create()

    def test_goal_target_count_non_negative(self):
        """ValidationError on target_count < 0 (DB CHECK constraint)."""
        with self.assertRaises(Exception):
            self._create(target_count=-1)

    def test_goal_target_count_zero_is_valid(self):
        """target_count=0 creates successfully (FR1.6 boundary — zero is valid)."""
        goal = self._create(target_count=0)
        self.assertEqual(goal.target_count, 0)

    def test_goal_month_range_valid(self):
        """ValidationError on month=0 and month=13."""
        with self.assertRaises(Exception):
            self._create(month=0)
        with self.assertRaises(Exception):
            self._create(month=13, operation_type='rent')

    def test_goal_year_min_2000(self):
        """ValidationError on year=1999."""
        with self.assertRaises(Exception):
            self._create(year=1999)

    def test_vgv_forbidden_for_visitas_novos_clientes(self):
        """ValidationError when target_vgv set on visitas or novos_clientes."""
        with self.assertRaises(ValidationError):
            self._create(metric_type='visitas', target_vgv=10000.0)
        with self.assertRaises(ValidationError):
            self._create(metric_type='novos_clientes', target_vgv=5000.0, operation_type='rent')

    def test_goal_soft_delete(self):
        """active=False after write; record still in DB."""
        goal = self._create()
        goal.sudo().write({'active': False})
        self.assertFalse(goal.active)
        # Record still present when searching with active=False
        found = self.GoalModel.sudo().with_context(active_test=False).search(
            [('id', '=', goal.id)]
        )
        self.assertTrue(found)


class TestGoalsReportPeriod(TransactionCase):
    """T029 — Period resolution and goal_status computation."""

    def setUp(self):
        super().setUp()
        from odoo.addons.thedevkitchen_estate_goals.services.goals_report_service import GoalsReportService
        self.Service = GoalsReportService

    def test_resolve_period_single_month(self):
        """year + month → correct date range boundaries."""
        df, dt, info = self.Service._resolve_period(2026, 5, None, None)
        self.assertEqual(df, datetime(2026, 5, 1))
        self.assertEqual(dt, datetime(2026, 6, 1))
        self.assertEqual(info['mode'], 'single_month')
        self.assertEqual(info['year'], 2026)
        self.assertEqual(info['month'], 5)

    def test_resolve_period_accumulated(self):
        """date_from / date_to → correct datetimes; year ignored."""
        df, dt, info = self.Service._resolve_period(None, None, '2026-01-01', '2026-03-31')
        self.assertEqual(df, datetime(2026, 1, 1))
        self.assertEqual(dt, datetime(2026, 4, 1))
        self.assertEqual(info['mode'], 'accumulated')

    def test_resolve_period_missing_year_raises(self):
        """ValidationError when year absent in single-month mode."""
        with self.assertRaises(ValidationError):
            self.Service._resolve_period(None, 5, None, None)

    def test_resolve_period_max_range_exceeded(self):
        """ValidationError when date range > 366 days (SEC-6)."""
        with self.assertRaises(ValidationError):
            self.Service._resolve_period(None, None, '2026-01-01', '2027-02-01')

    def test_goal_status_complete_all_set_goals_met(self):
        """All set goals met → goal_status = 'complete'."""
        user = self.env.ref('base.user_admin')
        company = self.env.ref('base.main_company')
        GoalModel = self.env['thedevkitchen.estate.goal']

        goal = GoalModel.sudo().create({
            'user_id': user.id,
            'year': 2025,
            'month': 1,
            'metric_type': 'captacao',
            'operation_type': 'sale',
            'target_count': 2,
            'company_id': company.id,
        })

        # Achievement exceeds target
        user_goals = {'captacoes': goal}
        user_achievements = {
            'captacoes': {'count': 3, 'vgv': 0},
            'novos_clientes': {'count': 0},
            'visitas': {'count': 0},
            'propostas': {'count': 0, 'vgv': 0},
            'fechamento': {'count': 0, 'vgv': 0},
        }
        row = self.Service._compute_user_row(self.env, user.id, user_goals, user_achievements)
        self.assertEqual(row['goal_status'], 'complete')

    def test_goal_status_no_goals_zero_goals_set(self):
        """Zero goals set → goal_status = 'no_goals' (not 'complete')."""
        user = self.env.ref('base.user_admin')
        row = self.Service._compute_user_row(self.env, user.id, {}, {
            metric: {'count': 0} for metric in ['captacoes', 'novos_clientes', 'visitas', 'propostas', 'fechamento']
        })
        self.assertEqual(row['goal_status'], 'no_goals')

    def test_goal_status_null_metrics_neutral(self):
        """Unset metrics (None goal) don't affect complete status for set metrics."""
        user = self.env.ref('base.user_admin')
        company = self.env.ref('base.main_company')
        GoalModel = self.env['thedevkitchen.estate.goal']

        goal = GoalModel.sudo().create({
            'user_id': user.id,
            'year': 2025,
            'month': 2,
            'metric_type': 'visitas',
            'operation_type': 'all',
            'target_count': 1,
            'company_id': company.id,
        })

        user_goals = {'visitas': goal}
        user_achievements = {
            'captacoes': {'count': 0, 'vgv': 0},
            'novos_clientes': {'count': 0},
            'visitas': {'count': 2},
            'propostas': {'count': 0, 'vgv': 0},
            'fechamento': {'count': 0, 'vgv': 0},
        }
        row = self.Service._compute_user_row(self.env, user.id, user_goals, user_achievements)
        self.assertEqual(row['goal_status'], 'complete')

    def test_totals_metric_aggregation_sums_across_users(self):
        """Two users each with captacoes.conquista=2 → totals.captacoes.conquista=4."""
        from odoo.addons.thedevkitchen_estate_goals.services.goals_report_service import METRICS, _empty_metric

        def make_row(conquista, meta_count):
            metrics = {m: _empty_metric() for m in METRICS}
            metrics['captacoes']['conquista'] = conquista
            metrics['captacoes']['meta_count'] = meta_count
            return {'metrics': metrics}

        rows = [make_row(2, 5), make_row(2, 3)]
        totals = self.Service.compute_totals(rows)
        self.assertEqual(totals['captacoes']['conquista'], 4)
        self.assertEqual(totals['captacoes']['meta_count'], 8)

    def test_totals_null_meta_count_stays_null_when_all_null(self):
        """meta_count in totals is null if ALL users have null for that metric."""
        from odoo.addons.thedevkitchen_estate_goals.services.goals_report_service import METRICS, _empty_metric

        def make_row():
            metrics = {m: _empty_metric() for m in METRICS}
            # meta_count stays None (no goal)
            return {'metrics': metrics}

        rows = [make_row(), make_row()]
        totals = self.Service.compute_totals(rows)
        self.assertIsNone(totals['captacoes']['meta_count'])


class TestGoalsOperationTypeFilter(TransactionCase):
    """T029 — operation_type=all exclusion from filtered report."""

    def test_operation_type_all_excluded_from_filtered_report(self):
        """Goals with operation_type='all' absent from 'sale'-filtered query."""
        user = self.env.ref('base.user_admin')
        company = self.env.ref('base.main_company')
        GoalModel = self.env['thedevkitchen.estate.goal']

        # Create an 'all' goal and a 'sale' goal
        goal_all = GoalModel.sudo().create({
            'user_id': user.id,
            'year': 2025,
            'month': 3,
            'metric_type': 'captacao',
            'operation_type': 'all',
            'target_count': 5,
            'company_id': company.id,
        })
        goal_sale = GoalModel.sudo().create({
            'user_id': user.id,
            'year': 2025,
            'month': 3,
            'metric_type': 'captacao',
            'operation_type': 'sale',
            'target_count': 3,
            'company_id': company.id,
        })

        from odoo.addons.thedevkitchen_estate_goals.services.goals_report_service import GoalsReportService
        df, dt, _ = GoalsReportService._resolve_period(2025, 3, None, None)
        goals = GoalsReportService._load_goals(
            self.env, company.id, [user.id], df, dt, 'sale'
        )
        # Only 'sale' goal should appear
        user_goals = goals.get(user.id, {})
        if 'captacoes' in user_goals:
            g = user_goals['captacoes']
            if isinstance(g, list):
                for gg in g:
                    self.assertNotEqual(gg.operation_type, 'all')
            else:
                self.assertEqual(g.operation_type, 'sale')


class TestGoalsSQLQueries(TransactionCase):
    """T047 — Unit tests for SQL query methods (mock-based)."""

    def setUp(self):
        super().setUp()
        from odoo.addons.thedevkitchen_estate_goals.services.goals_report_service import GoalsReportService
        self.Service = GoalsReportService
        self.df = datetime(2026, 5, 1)
        self.dt = datetime(2026, 6, 1)

    def _mock_env_cr(self, fetchall_return):
        """Create a mock env with a mocked cr.execute/fetchall."""
        mock_cr = MagicMock()
        mock_cr.fetchall.return_value = fetchall_return
        mock_cr.fetchone.return_value = (True,) if fetchall_return else None
        mock_env = MagicMock()
        mock_env.cr = mock_cr
        return mock_env, mock_cr

    def test_query_captacao_sale_returns_count_and_vgv(self):
        """_query_captacao with operation_type='sale' returns count + vgv per user."""
        mock_env, mock_cr = self._mock_env_cr([(5, 3, 150000.0)])
        result = self.Service._query_captacao(mock_env, 1, [5], self.df, self.dt, 'sale')
        self.assertEqual(result[3]['count'], 3)
        self.assertEqual(result[3]['vgv'], 150000.0)
        # Verify FOR SALE filter in SQL
        sql_call = mock_cr.execute.call_args[0][0]
        self.assertIn('for_sale', sql_call)

    def test_query_captacao_rent_filters_for_rent(self):
        """_query_captacao with operation_type='rent' queries for_rent flag."""
        mock_env, mock_cr = self._mock_env_cr([])
        self.Service._query_captacao(mock_env, 1, [5], self.df, self.dt, 'rent')
        sql_call = mock_cr.execute.call_args[0][0]
        self.assertIn('for_rent', sql_call)

    def test_query_novos_clientes_filters_by_operation_type(self):
        """operation_type='sale' adds operation_type filter to novos_clientes query."""
        mock_env, mock_cr = self._mock_env_cr([])
        self.Service._query_novos_clientes(mock_env, 1, [5], self.df, self.dt, 'sale')
        sql_call = mock_cr.execute.call_args[0][0]
        self.assertIn('operation_type', sql_call)

    def test_query_novos_clientes_all_has_no_type_filter(self):
        """operation_type='all' omits operation_type filter."""
        mock_env, mock_cr = self._mock_env_cr([])
        self.Service._query_novos_clientes(mock_env, 1, [5], self.df, self.dt, 'all')
        params = mock_cr.execute.call_args[0][1]
        self.assertNotIn('operation_type', params)

    def test_query_visitas_uses_count_distinct(self):
        """_query_visitas uses COUNT(DISTINCT) to count unique services."""
        mock_env, mock_cr = self._mock_env_cr([])
        self.Service._query_visitas(mock_env, 1, [5], self.df, self.dt, 'all')
        sql_call = mock_cr.execute.call_args[0][0]
        self.assertIn('COUNT(DISTINCT', sql_call)
        self.assertIn("'visit'", sql_call)

    def test_query_propostas_maps_rent_to_lease(self):
        """operation_type='rent' translates to proposal_type='lease' (OP_TYPE_TO_PROPOSAL_TYPE)."""
        mock_env, mock_cr = self._mock_env_cr([])
        self.Service._query_propostas(mock_env, 1, [5], self.df, self.dt, 'rent')
        params = mock_cr.execute.call_args[0][1]
        self.assertEqual(params.get('proposal_type'), 'lease')

    def test_query_fechamento_excludes_other_company(self):
        """company_id parameter is always passed in fechamento query."""
        mock_env, mock_cr = self._mock_env_cr([])
        # fetchone for service_id check returns None (column absent → fallback)
        mock_cr.fetchone.return_value = None
        self.Service._query_fechamento(mock_env, 99, [5], self.df, self.dt, 'all')
        # Two execute calls: first is schema check, second is main query
        calls = mock_cr.execute.call_args_list
        self.assertGreaterEqual(len(calls), 2)
        main_params = calls[-1][0][1]
        self.assertEqual(main_params['company_id'], 99)
