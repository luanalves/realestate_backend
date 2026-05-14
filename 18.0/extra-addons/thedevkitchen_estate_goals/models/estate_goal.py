# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

METRIC_TYPES = [
    ('captacao', 'Captação'),
    ('novos_clientes', 'Novos Clientes'),
    ('visitas', 'Visitas'),
    ('propostas', 'Propostas'),
    ('fechamento', 'Fechamento'),
]

OPERATION_TYPES = [
    ('all', 'Todos'),
    ('sale', 'Venda'),
    ('rent', 'Locação'),
]

VGV_METRICS = {'captacao', 'propostas', 'fechamento'}


class EstateGoal(models.Model):
    _name = 'thedevkitchen.estate.goal'
    _description = 'Estate Performance Goal'
    _order = 'year desc, month desc, user_id'

    # ── Lifecycle ────────────────────────────────────────────────────────────
    active = fields.Boolean(default=True)

    # ── Multitenancy ─────────────────────────────────────────────────────────
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # ── Ownership ────────────────────────────────────────────────────────────
    user_id = fields.Many2one(
        'res.users',
        string='Agent',
        required=True,
        ondelete='cascade',
    )

    # ── Period ───────────────────────────────────────────────────────────────
    year = fields.Integer(string='Year', required=True)
    month = fields.Integer(string='Month', required=True)

    # ── Metric ───────────────────────────────────────────────────────────────
    metric_type = fields.Selection(
        selection=METRIC_TYPES,
        string='Metric',
        required=True,
    )
    operation_type = fields.Selection(
        selection=OPERATION_TYPES,
        string='Operation Type',
        required=True,
        default='all',
    )

    # ── Target ───────────────────────────────────────────────────────────────
    target_count = fields.Integer(
        string='Target (count)',
        required=True,
        default=0,
    )
    target_vgv = fields.Monetary(
        string='Target VGV',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True,
        store=True,
    )

    # ── Constraints ──────────────────────────────────────────────────────────
    _sql_constraints = [
        (
            'unique_user_company_period_metric_optype',
            'UNIQUE (user_id, company_id, year, month, metric_type, operation_type)',
            'A goal for this user/company/period/metric/operation already exists.',
        ),
        (
            'check_year_min',
            'CHECK (year >= 2000)',
            'Year must be >= 2000.',
        ),
        (
            'check_month_range',
            'CHECK (month >= 1 AND month <= 12)',
            'Month must be between 1 and 12.',
        ),
        (
            'check_target_count_non_negative',
            'CHECK (target_count >= 0)',
            'Target count cannot be negative.',
        ),
        (
            'check_target_vgv_non_negative',
            'CHECK (target_vgv IS NULL OR target_vgv >= 0)',
            'Target VGV cannot be negative.',
        ),
    ]

    @api.constrains('metric_type', 'target_vgv')
    def _check_vgv_applicability(self):
        for rec in self:
            if rec.target_vgv and rec.metric_type not in VGV_METRICS:
                raise ValidationError(
                    'target_vgv only applies to captacao, propostas, and fechamento metrics.'
                )

    # ── Composite index via _auto_init ────────────────────────────────────────
    def _auto_init(self):
        super()._auto_init()
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_estate_goal_report
              ON thedevkitchen_estate_goal (company_id, year, month, operation_type)
              WHERE active = true;
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_estate_goal_user
              ON thedevkitchen_estate_goal (user_id, company_id)
              WHERE active = true;
        """)
