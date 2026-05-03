# -*- coding: utf-8 -*-
"""
Model: real.estate.service — Feature 015 (Service Pipeline / Atendimentos)

Core entity tracking each agent-client engagement through a 7-stage kanban pipeline.
Inherits mail.thread + mail.activity.mixin for full audit and activity management.

data-model.md: E1
research.md: R1 (EXCLUDE), R2 (last_activity_date), R3 (formalization gate),
             R7 (lead_id independence)
spec.md: FR-001 through FR-026
"""
import logging
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# Ordered stage list (used for forward/backward transition checks)
STAGES = ['no_service', 'in_service', 'visit', 'proposal', 'formalization', 'won', 'lost']
TERMINAL_STAGES = {'won', 'lost'}

STAGE_SELECTION = [
    ('no_service',     'Sem Atendimento'),
    ('in_service',     'Em Atendimento'),
    ('visit',          'Visita'),
    ('proposal',       'Proposta'),
    ('formalization',  'Formalização'),
    ('won',            'Ganho'),
    ('lost',           'Perdido'),
]


class RealEstateService(models.Model):
    _name = 'real.estate.service'
    _description = 'Service (Atendimento)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'last_activity_date desc, id desc'
    _rec_name = 'name'

    # ------------------------------------------------------------------ #
    #  Core identity                                                       #
    # ------------------------------------------------------------------ #
    name = fields.Char(
        'Reference',
        size=50,
        readonly=True,
        copy=False,
        default='/',
        index=True,
        help='Auto-generated from sequence: ATD/YYYY/NNNNN',
    )
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # ------------------------------------------------------------------ #
    #  Relations                                                           #
    # ------------------------------------------------------------------ #
    client_partner_id = fields.Many2one(
        'res.partner',
        'Client',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
    )
    lead_id = fields.Many2one(
        'real.estate.lead',
        'Origin Lead',
        ondelete='set null',
        index=True,
        help='Optional traceability reference to origin lead. '
             'Lifecycle is fully independent (FR-001a / R7).',
    )
    agent_id = fields.Many2one(
        'res.users',
        'Responsible Agent',
        required=True,
        ondelete='restrict',
        default=lambda self: self.env.user,
        index=True,
        tracking=True,
    )
    source_id = fields.Many2one(
        'real.estate.service.source',
        'Source',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    tag_ids = fields.Many2many(
        'real.estate.service.tag',
        string='Tags',
        tracking=True,
    )
    property_ids = fields.Many2many(
        'real.estate.property',
        string='Properties of Interest',
    )
    proposal_ids = fields.One2many(
        'real.estate.proposal',
        'service_id',
        string='Proposals',
    )

    # ------------------------------------------------------------------ #
    #  Pipeline                                                            #
    # ------------------------------------------------------------------ #
    operation_type = fields.Selection(
        selection=[('sale', 'Venda'), ('rent', 'Locação')],
        string='Operation Type',
        required=True,
        index=True,
        tracking=True,
    )
    stage = fields.Selection(
        selection=STAGE_SELECTION,
        string='Stage',
        required=True,
        default='no_service',
        index=True,
        tracking=True,
    )
    lost_reason = fields.Char('Lost Reason', size=255)
    won_date = fields.Datetime('Won Date', readonly=True)

    # ------------------------------------------------------------------ #
    #  Notes                                                               #
    # ------------------------------------------------------------------ #
    notes = fields.Text('Notes')

    # ------------------------------------------------------------------ #
    #  Computed fields (stored)                                            #
    # ------------------------------------------------------------------ #
    last_activity_date = fields.Datetime(
        'Last Activity Date',
        compute='_compute_last_activity_date',
        store=True,
        compute_sudo=True,
        help='Max of manual write_date and latest user-authored mail.message. '
             'Automatic system writes are excluded (R2).',
    )
    is_pending = fields.Boolean(
        'Pending',
        compute='_compute_is_pending',
        store=True,
        compute_sudo=True,
        help='True if last_activity_date is older than company pendency_threshold_days.',
    )
    is_orphan_agent = fields.Boolean(
        'Orphan Agent',
        compute='_compute_is_orphan_agent',
        store=True,
        compute_sudo=True,
        help='True when the responsible agent account is deactivated (FR-024a).',
    )

    # ------------------------------------------------------------------ #
    #  Computed — implementations                                          #
    # ------------------------------------------------------------------ #
    @api.depends('write_date', 'message_ids.create_date', 'message_ids.author_id')
    def _compute_last_activity_date(self):
        """R2: max(write_date, latest user-authored mail.message.create_date).
        System messages (author_id=False) are excluded.
        """
        for rec in self:
            user_msgs = rec.message_ids.filtered(lambda m: m.author_id)
            if user_msgs:
                latest_msg = max(user_msgs.mapped('create_date'))
            else:
                latest_msg = False
            if rec.write_date and latest_msg:
                rec.last_activity_date = max(rec.write_date, latest_msg)
            else:
                rec.last_activity_date = latest_msg or rec.write_date

    @api.depends('last_activity_date', 'company_id')
    def _compute_is_pending(self):
        """True when last_activity_date is older than threshold (FR-015)."""
        Settings = self.env['thedevkitchen.service.settings']
        for rec in self:
            if rec.stage in TERMINAL_STAGES:
                rec.is_pending = False
                continue
            settings = Settings.search([('company_id', '=', rec.company_id.id)], limit=1)
            threshold = settings.pendency_threshold_days if settings else 3
            if not rec.last_activity_date:
                rec.is_pending = True
            else:
                cutoff = fields.Datetime.now() - timedelta(days=threshold)
                rec.is_pending = rec.last_activity_date < cutoff

    @api.depends('agent_id', 'agent_id.active')
    def _compute_is_orphan_agent(self):
        """FR-024a: service is orphaned when responsible agent is deactivated."""
        for rec in self:
            rec.is_orphan_agent = bool(rec.agent_id) and not rec.agent_id.active

    # ------------------------------------------------------------------ #
    #  Cron recompute                                                      #
    # ------------------------------------------------------------------ #
    def _cron_recompute_pendency(self):
        """Daily cron to recompute is_pending for all active services (FR-015)."""
        active_services = self.search([('active', '=', True), ('stage', 'not in', list(TERMINAL_STAGES))])
        _logger.info('Feature 015 cron: recomputing pendency for %d services', len(active_services))
        active_services._compute_is_pending()

    # ------------------------------------------------------------------ #
    #  ORM overrides                                                       #
    # ------------------------------------------------------------------ #
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('real.estate.service') or '/'
        return super().create(vals_list)

    def write(self, vals):
        if 'stage' in vals:
            for rec in self:
                old_stage = rec.stage
                new_stage = vals['stage']
                if old_stage != new_stage:
                    _logger.debug(
                        'Service %s: stage transition %s → %s',
                        rec.name, old_stage, new_stage,
                    )
        result = super().write(vals)
        # Set won_date when moving to won
        if vals.get('stage') == 'won':
            self.filtered(lambda r: not r.won_date).write(
                {'won_date': fields.Datetime.now()}
            )
        return result

    # ------------------------------------------------------------------ #
    #  Python constraints (stage gates) — T013                            #
    # ------------------------------------------------------------------ #
    @api.constrains('stage', 'property_ids')
    def _check_proposal_stage_requires_property(self):
        """FR-004: proposal stage requires at least one linked property."""
        for rec in self:
            if rec.stage == 'proposal' and not rec.property_ids:
                raise ValidationError(_(
                    'Stage "Proposta" requires at least one property linked to the service. '
                    'Please add a property first.'
                ))

    @api.constrains('stage', 'proposal_ids')
    def _check_formalization_requires_approved_proposal(self):
        """FR-005/R3: formalization requires an accepted proposal."""
        for rec in self:
            if rec.stage == 'formalization':
                accepted = rec.proposal_ids.filtered(lambda p: p.state == 'accepted')
                if not accepted:
                    raise ValidationError(_(
                        'Stage "Formalização" requires at least one accepted proposal '
                        'linked to this service.'
                    ))

    @api.constrains('stage', 'lost_reason')
    def _check_lost_requires_reason(self):
        """FR-006: lost stage requires a non-empty lost_reason."""
        for rec in self:
            if rec.stage == 'lost' and not (rec.lost_reason or '').strip():
                raise ValidationError(_(
                    'Marking a service as "Perdido" requires a lost reason. '
                    'Please fill in the "Lost Reason" field.'
                ))

    @api.constrains('stage', 'tag_ids')
    def _check_closed_tag_locks_stage(self):
        """FR-007: system tag 'Encerrado' locks all stage transitions."""
        for rec in self:
            # Find if tag_ids contains any system (closed) tag
            closed_tags = rec.tag_ids.filtered(lambda t: t.is_system)
            if not closed_tags:
                continue
            # Check if stage is actually changing
            origin_stage = rec._origin.stage if rec._origin else None
            if origin_stage and origin_stage != rec.stage:
                raise ValidationError(_(
                    'Service "%(name)s" has the system tag "%(tag)s" applied. '
                    'Stage transitions are locked while a system tag is active. '
                    'Remove the tag first.',
                    name=rec.name,
                    tag=closed_tags[0].name,
                ))

    @api.constrains('stage', 'agent_id')
    def _check_orphan_agent_blocks_stage_change(self):
        """FR-024a: orphaned services (deactivated agent) cannot change stage."""
        for rec in self:
            if not rec.is_orphan_agent:
                continue
            origin_stage = rec._origin.stage if rec._origin else None
            if origin_stage and origin_stage != rec.stage:
                raise ValidationError(_(
                    'Service "%(name)s" has no active responsible agent. '
                    'Stage transitions are blocked until a Manager reassigns the service.',
                    name=rec.name,
                ))

    @api.constrains('stage')
    def _check_terminal_stages_require_explicit_reopen(self):
        """FR-003a: won/lost → non-terminal requires explicit context flag."""
        for rec in self:
            origin_stage = rec._origin.stage if rec._origin else None
            if origin_stage not in TERMINAL_STAGES:
                continue
            if rec.stage in TERMINAL_STAGES:
                continue
            # Transitioning OUT of a terminal stage — require explicit reopen flag
            if not self.env.context.get('service.allow_reopen'):
                raise ValidationError(_(
                    'Service "%(name)s" is in terminal stage "%(stage)s". '
                    'Use the explicit Reopen action to move it back.',
                    name=rec.name,
                    stage=dict(STAGE_SELECTION).get(origin_stage, origin_stage),
                ))
