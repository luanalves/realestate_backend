# -*- coding: utf-8 -*-

import logging
from datetime import timedelta, date

import psycopg2

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError, AccessError

_logger = logging.getLogger(__name__)

# States that occupy the active slot on a property
ACTIVE_STATES = ('draft', 'sent', 'negotiation', 'accepted')
# States that enforce the partial unique index (ADR-027)
INDEX_ACTIVE_STATES = ('draft', 'sent', 'accepted')
# Terminal states — no further transitions allowed
TERMINAL_STATES = ('accepted', 'rejected', 'expired', 'cancelled')

VALID_TRANSITIONS = {
    'draft':       {'sent', 'cancelled'},
    'queued':      {'draft', 'cancelled'},
    'sent':        {'negotiation', 'accepted', 'rejected', 'expired', 'cancelled'},
    'negotiation': {'accepted', 'rejected', 'expired', 'cancelled'},
    'accepted':    set(),
    'rejected':    set(),
    'expired':     set(),
    'cancelled':   set(),
}


class RealEstateProposal(models.Model):
    _name = 'real.estate.proposal'
    _description = 'Real Estate Proposal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'proposal_code'

    # ------------------------------------------------------------------ #
    #  SQL constraints                                                     #
    # ------------------------------------------------------------------ #
    _sql_constraints = [
        (
            'proposal_code_company_uniq',
            'unique(proposal_code, company_id)',
            'Proposal code must be unique per company.',
        ),
        (
            'proposal_value_positive',
            'CHECK(proposal_value > 0)',
            'Proposal value must be greater than zero.',
        ),
    ]

    # ------------------------------------------------------------------ #
    #  Core identity                                                       #
    # ------------------------------------------------------------------ #
    proposal_code = fields.Char(
        'Proposal Code',
        size=20,
        required=True,
        readonly=True,
        copy=False,
        default='/',
        tracking=True,
        index=True,
        help='Auto-generated per-company code (e.g. PRP001). Never editable.',
    )
    name = fields.Char(
        'Display Name',
        compute='_compute_name',
        store=True,
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
    property_id = fields.Many2one(
        'real.estate.property',
        'Property',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        'Client',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
    )
    lead_id = fields.Many2one(
        'real.estate.lead',
        'Lead',
        ondelete='set null',
        index=True,
    )
    agent_id = fields.Many2one(
        'real.estate.agent',
        'Agent',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
    )

    # ------------------------------------------------------------------ #
    #  Proposal terms                                                      #
    # ------------------------------------------------------------------ #
    proposal_type = fields.Selection(
        [('sale', 'Sale'), ('lease', 'Lease')],
        'Type',
        required=True,
        tracking=True,
    )
    proposal_value = fields.Monetary(
        'Offer Value',
        currency_field='currency_id',
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        'Currency',
        required=True,
        default=lambda self: self.env.ref('base.BRL', raise_if_not_found=False)
                             or self.env.company.currency_id,
    )
    description = fields.Text('Notes')
    valid_until = fields.Date(
        'Valid Until',
        tracking=True,
        help='Must be > today and ≤ today + 90 days. Defaults to sent_date + 7d.',
    )

    # ------------------------------------------------------------------ #
    #  State machine                                                       #
    # ------------------------------------------------------------------ #
    state = fields.Selection(
        [
            ('draft',       'Draft'),
            ('queued',      'Queued'),
            ('sent',        'Sent'),
            ('negotiation', 'Negotiation'),
            ('accepted',    'Accepted'),
            ('rejected',    'Rejected'),
            ('expired',     'Expired'),
            ('cancelled',   'Cancelled'),
        ],
        'State',
        required=True,
        default='draft',
        tracking=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    #  Timestamps & reasons                                                #
    # ------------------------------------------------------------------ #
    sent_date = fields.Datetime('Sent On', readonly=True, copy=False)
    accepted_date = fields.Datetime('Accepted On', readonly=True, copy=False)
    rejected_date = fields.Datetime('Rejected On', readonly=True, copy=False)
    rejection_reason = fields.Text('Rejection Reason', copy=False)
    cancellation_reason = fields.Text('Cancellation Reason', copy=False)

    # ------------------------------------------------------------------ #
    #  Counter-proposal chain                                              #
    # ------------------------------------------------------------------ #
    parent_proposal_id = fields.Many2one(
        'real.estate.proposal',
        'Parent Proposal',
        ondelete='set null',
        index=True,
        copy=False,
    )
    child_proposal_ids = fields.One2many(
        'real.estate.proposal',
        'parent_proposal_id',
        'Counter-Proposals',
    )
    superseded_by_id = fields.Many2one(
        'real.estate.proposal',
        'Superseded By',
        ondelete='set null',
        copy=False,
        readonly=True,
    )

    # ------------------------------------------------------------------ #
    #  Computed fields                                                     #
    # ------------------------------------------------------------------ #
    queue_position = fields.Integer(
        'Queue Position',
        compute='_compute_queue_position',
        store=True,
        help='0 = active slot; ≥1 = FIFO queue position; -1 = terminal',
    )
    is_active_proposal = fields.Boolean(
        'Is Active Proposal',
        compute='_compute_queue_position',
        store=True,
    )
    documents_count = fields.Integer(
        'Documents',
        compute='_compute_documents_count',
        store=True,
    )
    has_competing_proposals = fields.Boolean(
        'Has Competitors',
        compute='_compute_has_competing',
    )

    # ------------------------------------------------------------------ #
    #  Computed: display name                                              #
    # ------------------------------------------------------------------ #
    @api.depends('proposal_code', 'property_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.proposal_code} - {rec.property_id.name}" \
                if rec.property_id else rec.proposal_code

    # ------------------------------------------------------------------ #
    #  Computed: queue position & is_active_proposal                      #
    # ------------------------------------------------------------------ #
    @api.depends(
        'property_id',
        'property_id.proposal_ids.state',
        'property_id.proposal_ids.active',
        'property_id.proposal_ids.create_date',
        'property_id.proposal_ids.parent_proposal_id',
        'state',
        'active',
        'parent_proposal_id',
        'create_date',
    )
    def _compute_queue_position(self):
        for rec in self:
            if rec.state in TERMINAL_STATES:
                rec.queue_position = -1
                rec.is_active_proposal = False
                continue

            # All non-terminal, active, root proposals on this property
            siblings = self.search([
                ('property_id', '=', rec.property_id.id),
                ('state', 'in', list(ACTIVE_STATES)),
                ('active', '=', True),
                ('parent_proposal_id', '=', False),
                ('id', '!=', rec.id),
            ], order='create_date asc')

            if rec.state in INDEX_ACTIVE_STATES and not rec.parent_proposal_id:
                rec.queue_position = 0
                rec.is_active_proposal = True
            elif rec.state == 'queued':
                # 0-indexed position within the queue (FIFO, tiebreak by id)
                queued_before = self.search([
                    ('property_id', '=', rec.property_id.id),
                    ('state', '=', 'queued'),
                    ('active', '=', True),
                    ('parent_proposal_id', '=', False),
                    '|',
                    ('create_date', '<', rec.create_date),
                    '&', ('create_date', '=', rec.create_date), ('id', '<', rec.id),
                ], order='create_date asc, id asc')
                rec.queue_position = len(queued_before)
                rec.is_active_proposal = False
            else:
                # counter-proposal in negotiation chain
                rec.queue_position = 0
                rec.is_active_proposal = True

    # ------------------------------------------------------------------ #
    #  Computed: documents count                                           #
    # ------------------------------------------------------------------ #
    @api.depends()
    def _compute_documents_count(self):
        for rec in self:
            rec.documents_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', 'real.estate.proposal'),
                ('res_id', '=', rec.id),
            ])

    # ------------------------------------------------------------------ #
    #  Computed: has competing proposals                                   #
    # ------------------------------------------------------------------ #
    def _compute_has_competing(self):
        for rec in self:
            rec.has_competing_proposals = bool(
                self.search_count([
                    ('property_id', '=', rec.property_id.id),
                    ('id', '!=', rec.id),
                    ('state', 'in', list(ACTIVE_STATES)),
                    ('active', '=', True),
                ])
            )

    # ================================================================== #
    #  CONSTRAINTS                                                         #
    # ================================================================== #

    @api.constrains('property_id', 'company_id')
    def _check_property_same_company(self):
        for rec in self:
            if rec.property_id and rec.property_id.company_id != rec.company_id:
                raise ValidationError(_(
                    'Property "%s" belongs to a different organization.',
                    rec.property_id.name
                ))

    @api.constrains('agent_id', 'property_id')
    def _check_agent_assigned_to_property(self):
        for rec in self:
            if not rec.agent_id or not rec.property_id:
                continue
            if rec.agent_id not in rec.property_id.assigned_agent_ids:
                raise ValidationError(_(
                    'Agent "%s" is not assigned to property "%s".',
                    rec.agent_id.name, rec.property_id.name,
                ))

    @api.constrains('rejection_reason', 'state')
    def _check_rejection_reason(self):
        for rec in self:
            if rec.state == 'rejected' and not (rec.rejection_reason or '').strip():
                raise ValidationError(_('A rejection reason is required.'))

    @api.constrains('cancellation_reason', 'state')
    def _check_cancellation_reason(self):
        for rec in self:
            if rec.state == 'cancelled' and not (rec.cancellation_reason or '').strip():
                raise ValidationError(_('A cancellation reason is required.'))

    @api.constrains('valid_until', 'create_date')
    def _check_valid_until_bounds(self):
        for rec in self:
            if not rec.valid_until:
                continue
            today = date.today()
            if rec.valid_until <= today:
                raise ValidationError(_(
                    'Validity date must be strictly after today.'
                ))
            create_dt = rec.create_date.date() if rec.create_date else today
            if rec.valid_until > create_dt + timedelta(days=90):
                raise ValidationError(_(
                    'Validity date must be at most 90 days from the creation date.'
                ))

    @api.constrains('partner_id')
    def _check_document_format(self):
        """Validate CPF/CNPJ format (FR-033, ADR — utils/validators.py)."""
        from odoo.addons.quicksol_estate.utils.validators import validate_document
        for rec in self:
            vat = (rec.partner_id.vat or '').strip()
            if vat and not validate_document(vat):
                raise ValidationError(_(
                    'Client document "%s" is not a valid CPF or CNPJ.', vat
                ))

    @api.constrains('parent_proposal_id', 'property_id', 'partner_id', 'company_id')
    def _check_counter_consistency(self):
        for rec in self:
            parent = rec.parent_proposal_id
            if not parent:
                continue
            if parent.property_id != rec.property_id:
                raise ValidationError(_(
                    'Counter-proposal must reference the same property as its parent.'
                ))
            if parent.company_id != rec.company_id:
                raise ValidationError(_(
                    'Counter-proposal must belong to the same company as its parent.'
                ))

    @api.constrains('state', 'parent_proposal_id', 'property_id', 'active')
    def _check_one_active_in_chain(self):
        """Application-level mirror of the partial unique index (ADR-027)."""
        for rec in self:
            if rec.state not in INDEX_ACTIVE_STATES or not rec.active:
                continue
            if rec.parent_proposal_id:
                # Counter-proposal: only one active child per chain
                siblings = self.search([
                    ('parent_proposal_id', '=', rec.parent_proposal_id.id),
                    ('state', 'in', list(INDEX_ACTIVE_STATES)),
                    ('active', '=', True),
                    ('id', '!=', rec.id),
                ])
                if siblings:
                    raise ValidationError(_(
                        'Another counter-proposal in this chain is already active.'
                    ))
            else:
                # Root proposal: at most one active per property
                others = self.search([
                    ('property_id', '=', rec.property_id.id),
                    ('state', 'in', list(INDEX_ACTIVE_STATES)),
                    ('active', '=', True),
                    ('parent_proposal_id', '=', False),
                    ('id', '!=', rec.id),
                ])
                if others:
                    raise ValidationError(_(
                        'Property "%s" already has an active proposal (%s).',
                        rec.property_id.name, others[0].proposal_code,
                    ))

    # ================================================================== #
    #  CREATE — active-slot decision with pessimistic lock (ADR-027)      #
    # ================================================================== #

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            property_id = vals.get('property_id')
            if not property_id:
                continue

            # Pessimistic lock on the property row (ADR-027 Layer 1)
            try:
                self.env.cr.execute(
                    "SELECT id FROM real_estate_property WHERE id = %s FOR UPDATE NOWAIT",
                    (property_id,),
                )
            except Exception as e:
                if 'could not obtain lock' in str(e).lower() or \
                   'LockNotAvailable' in type(e).__name__:
                    raise UserError(_(
                        'Another proposal is being created for this property. '
                        'Please try again in a moment.'
                    ))
                raise

            # Decide initial state
            active_exists = self.search_count([
                ('property_id', '=', property_id),
                ('state', 'in', list(INDEX_ACTIVE_STATES)),
                ('active', '=', True),
                ('parent_proposal_id', '=', False),
            ])
            if vals.get('parent_proposal_id'):
                # Counter-proposals always start as draft (take active slot)
                vals['state'] = 'draft'
            elif active_exists:
                vals['state'] = 'queued'
            else:
                vals['state'] = 'draft'

            # Generate proposal_code if not yet assigned
            if vals.get('proposal_code', '/') == '/':
                vals['proposal_code'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.proposal'
                ) or '/'

        records = super().create(vals_list)

        for rec in records:
            rec._resolve_or_create_lead()

        return records

    # ================================================================== #
    #  LEAD RESOLUTION (US5 / FR-030)                                     #
    # ================================================================== #

    def _resolve_or_create_lead(self):
        """Link existing active lead or auto-create one with source='proposal'."""
        self.ensure_one()
        if self.lead_id:
            return  # explicit lead already set

        partner = self.partner_id
        if not partner:
            return

        # Search for an active lead with this partner in the company
        existing = self.env['real.estate.lead'].search([
            ('partner_id', '=', partner.id),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ('new', 'contacted', 'qualified', 'won')),
            ('active', '=', True),
        ], limit=1, order='create_date desc')

        if existing:
            self.lead_id = existing.id
        else:
            lead = self.env['real.estate.lead'].create({
                'name': f"{partner.name} — {self.property_id.name}",
                'partner_id': partner.id,
                'company_id': self.company_id.id,
                'state': 'new',
                'source': 'proposal',
                'agent_id': self.agent_id.id,
            })
            self.lead_id = lead.id

    # ================================================================== #
    #  VALIDATION helper                                                   #
    # ================================================================== #

    def _assert_transition(self, target_state):
        """Raise UserError if the transition is not in VALID_TRANSITIONS."""
        self.ensure_one()
        if self.state in TERMINAL_STATES:
            raise UserError(_(
                'Proposal %s is in terminal state "%s" and cannot be modified.',
                self.proposal_code, self.state,
            ))
        allowed = VALID_TRANSITIONS.get(self.state, set())
        if target_state not in allowed:
            raise UserError(_(
                'Cannot transition from "%s" to "%s".',
                self.state, target_state,
            ))

    def _validate_valid_until(self, valid_until_val):
        """Validate client-supplied valid_until (FR-025a)."""
        if not valid_until_val:
            return
        today = date.today()
        if isinstance(valid_until_val, str):
            from datetime import datetime
            valid_until_val = datetime.strptime(valid_until_val, '%Y-%m-%d').date()
        if valid_until_val <= today:
            raise ValidationError(_('Validity date must be strictly after today.'))
        if valid_until_val > today + timedelta(days=90):
            raise ValidationError(_(
                'Validity date must be at most 90 days from today.'
            ))

    # ================================================================== #
    #  FSM ACTIONS                                                         #
    # ================================================================== #

    def action_send(self):
        """Draft → Sent (FR-022). Stamps sent_date, applies default validity."""
        self.ensure_one()
        self._assert_transition('sent')
        now = fields.Datetime.now()
        today = date.today()
        vals = {
            'state': 'sent',
            'sent_date': now,
        }
        if not self.valid_until:
            vals['valid_until'] = today + timedelta(days=7)
        self.write(vals)
        self._emit_event('proposal.sent', {
            'template': 'email_template_proposal_sent',
            'recipient_partner_ids': [self.partner_id.id],
        })
        return True

    def action_accept(self):
        """Sent/Negotiation → Accepted (FR-014, FR-028). Auto-cancels all competitors."""
        self.ensure_one()
        self._assert_transition('accepted')
        # RBAC: only manager/owner
        user = self.env.user
        if not (
            user.has_group('quicksol_estate.group_real_estate_manager')
            or user.has_group('quicksol_estate.group_real_estate_owner')
        ):
            raise AccessError(_('Only managers and owners can accept proposals.'))

        now = fields.Datetime.now()
        self.write({'state': 'accepted', 'accepted_date': now})

        # Update lead state to 'won' when proposal is accepted (FR-031)
        if self.lead_id:
            self.lead_id.write({'state': 'won'})

        # Auto-cancel all non-terminal competitors on this property (FR-014)
        competitors = self.search([
            ('property_id', '=', self.property_id.id),
            ('id', '!=', self.id),
            ('state', 'not in', list(TERMINAL_STATES)),
            ('active', '=', True),
        ])
        for comp in competitors:
            comp.write({
                'state': 'cancelled',
                'active': False,
                'cancellation_reason': _('Superseded by accepted proposal %s') % self.proposal_code,
                'superseded_by_id': self.id,
            })
            comp._emit_event('proposal.superseded', {
                'template': 'email_template_proposal_superseded',
                'recipient_partner_ids': [comp.agent_id.user_id.partner_id.id],
                'winner_code': self.proposal_code,
            })

        self._emit_event('proposal.accepted', {
            'template': 'email_template_proposal_accepted',
            'recipient_partner_ids': [self.partner_id.id, self.agent_id.user_id.partner_id.id],
            'hateoas_links': [{
                'rel': 'create-contract',
                'href': f'/api/v1/contracts?from_proposal={self.id}',
                'method': 'POST',
            }],
        })
        return True

    def action_reject(self, rejection_reason):
        """Sent/Negotiation → Rejected (FR-020). Promotes next queued."""
        self.ensure_one()
        if not (rejection_reason or '').strip():
            raise ValidationError(_('A rejection reason is required.'))
        self._assert_transition('rejected')
        now = fields.Datetime.now()
        self.write({
            'state': 'rejected',
            'rejected_date': now,
            'rejection_reason': rejection_reason,
            'active': False,
        })
        self._promote_next_queued()
        self._emit_event('proposal.rejected', {
            'template': 'email_template_proposal_rejected',
            'recipient_partner_ids': [self.partner_id.id],
            'rejection_reason': rejection_reason,
        })
        return True

    def action_cancel(self, cancellation_reason):
        """Any non-terminal → Cancelled (FR-021)."""
        self.ensure_one()
        if not (cancellation_reason or '').strip():
            raise ValidationError(_('A cancellation reason is required.'))
        self._assert_transition('cancelled')
        self.write({
            'state': 'cancelled',
            'cancellation_reason': cancellation_reason,
            'active': False,
        })
        self._promote_next_queued()
        return True

    def action_counter(self, vals):
        """
        Sent/Negotiation → Negotiation (parent); new child Draft takes active slot.
        (FR-018, US3)
        """
        self.ensure_one()
        if self.state not in ('sent', 'negotiation'):
            raise UserError(_(
                'Counter-proposals can only be created for proposals in '
                'Sent or Negotiation state.'
            ))
        # Counter value must differ from the parent (FR-019)
        if 'proposal_value' in vals and vals['proposal_value'] == self.proposal_value:
            raise UserError(_(
                'Counter-proposal value must differ from the parent proposal value.'
            ))
        # Transition parent to Negotiation first, then flush, then create child
        self.write({'state': 'negotiation'})
        self.env.cr.flush()  # ensure parent state is persisted before child insert

        child_vals = {
            'property_id': self.property_id.id,
            'partner_id': self.partner_id.id,
            'agent_id': self.agent_id.id,
            'company_id': self.company_id.id,
            'proposal_type': self.proposal_type,
            'currency_id': self.currency_id.id,
            'parent_proposal_id': self.id,
            'lead_id': self.lead_id.id if self.lead_id else False,
        }
        child_vals.update(vals)
        child = self.create([child_vals])

        self._emit_event('proposal.countered', {
            'template': 'email_template_proposal_countered',
            'recipient_partner_ids': [self.partner_id.id],
            'child_id': child.id,
        })
        return child

    # ================================================================== #
    #  QUEUE PROMOTION (US2 / FR-011)                                     #
    # ================================================================== #

    def _promote_next_queued(self):
        """
        When the active slot is released (reject / expire / cancel),
        promote the oldest queued root proposal to Draft and notify its agent.
        """
        next_queued = self.search([
            ('property_id', '=', self.property_id.id),
            ('state', '=', 'queued'),
            ('active', '=', True),
            ('parent_proposal_id', '=', False),
        ], order='create_date asc, id asc', limit=1)

        if not next_queued:
            return

        next_queued.write({'state': 'draft'})
        next_queued._emit_event('proposal.promoted', {
            'template': 'email_template_proposal_promoted',
            'recipient_partner_ids': [next_queued.agent_id.user_id.partner_id.id],
        })

    # ================================================================== #
    #  CRON: daily expiration (US8 / FR-026)                              #
    # ================================================================== #

    @api.model
    def _cron_expire_proposals(self):
        """
        Hourly cron: move Sent/Negotiation proposals past their valid_until
        date to Expired, then promote next queued.  Processes in chunks to
        keep the transaction short (SC-010).
        """
        today = fields.Date.today()
        expirable = self.search([
            ('state', 'in', ('sent', 'negotiation')),
            ('active', '=', True),
            ('valid_until', '<', today),
        ])
        _logger.info(
            'Feature 013 expiration cron: %d proposals to expire', len(expirable)
        )
        CHUNK = 200
        for i in range(0, len(expirable), CHUNK):
            chunk = expirable[i:i + CHUNK]
            for rec in chunk:
                rec.write({'state': 'expired', 'active': False})
                rec._promote_next_queued()
                rec._emit_event('proposal.expired', {
                    'template': 'email_template_proposal_expired',
                    'recipient_partner_ids': [rec.agent_id.user_id.partner_id.id],
                })
            if not self.env.registry.in_test_mode():
                try:
                    self.env.cr.commit()
                except AssertionError:
                    pass  # silently skip commit when cursor is test-wrapped

    # ================================================================== #
    #  OUTBOX / EVENT EMISSION (ADR-021)                                  #
    # ================================================================== #

    def _emit_event(self, event_type, payload):
        """
        Enqueue a notification event for async processing via Celery
        (notification_events queue, ADR-021).  Failures are logged to the
        proposal chatter and never block the state transition (FR-041a).
        """
        self.ensure_one()
        try:
            from odoo.addons.quicksol_estate.celery_tasks import (
                send_proposal_notification,
            )
            send_proposal_notification.apply_async(
                kwargs={
                    'proposal_id': self.id,
                    'event_type': event_type,
                    'payload': payload,
                    'db': self.env.cr.dbname,
                },
                queue='notification_events',
            )
        except Exception:
            _logger.exception(
                'Feature 013: failed to enqueue %s for proposal %s — '
                'state transition succeeded; notification not sent.',
                event_type, self.proposal_code,
            )
            try:
                self.message_post(
                    body=_(
                        'Notification "%s" could not be queued. '
                        'Please send manually if needed.', event_type
                    ),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            except Exception:
                _logger.warning(
                    'Feature 013: message_post fallback also failed for %s.',
                    self.proposal_code,
                )

    # ================================================================== #
    #  PROPOSAL CHAIN (US3 / FR-019)                                      #
    # ================================================================== #

    def _get_chain_root(self):
        """Walk up parent links to find the root proposal."""
        self.ensure_one()
        rec = self.with_context(active_test=False)
        visited = set()
        while rec.parent_proposal_id and rec.id not in visited:
            visited.add(rec.id)
            rec = rec.parent_proposal_id.with_context(active_test=False)
        return rec

    def get_proposal_chain(self):
        """Return all proposals in the chain (root + descendants) ordered by create_date."""
        root = self._get_chain_root()
        chain = self.env['real.estate.proposal']
        queue = [root]
        visited = set()
        while queue:
            current = queue.pop(0)
            if current.id in visited:
                continue
            visited.add(current.id)
            chain |= current
            queue.extend(current.with_context(active_test=False).child_proposal_ids)
        return chain.sorted('create_date')

    # ================================================================== #
    #  EMAIL HELPERS (T029 / FR-041a)                                     #
    # ================================================================== #

    EVENT_TEMPLATE_MAP = {
        'proposal.sent': 'quicksol_estate.email_template_proposal_sent',
        'proposal.accepted': 'quicksol_estate.email_template_proposal_accepted',
        'proposal.rejected': 'quicksol_estate.email_template_proposal_rejected',
        'proposal.cancelled': 'quicksol_estate.email_template_proposal_cancelled',
        'proposal.countered': 'quicksol_estate.email_template_proposal_counter',
        'proposal.expired': 'quicksol_estate.email_template_proposal_expiration',
        'proposal.queued': 'quicksol_estate.email_template_proposal_queued',
    }

    @api.model
    def send_notification_email(self, proposal_id, event_name):
        """Called by Celery send_proposal_email_task (T029).
        Renders the mail.template associated with *event_name* and sends it.
        Returns True on success. Raises on error so Celery can retry.
        """
        xmlid = self.EVENT_TEMPLATE_MAP.get(event_name)
        if not xmlid:
            return True  # Unknown event — silently skip
        proposal = self.browse(proposal_id).exists()
        if not proposal:
            return True  # Already deleted — skip
        template = self.env.ref(xmlid, raise_if_not_found=False)
        if template:
            template.send_mail(proposal.id, force_send=True)
        return True

    @api.model
    def log_email_failure(self, proposal_id, event_name, error_message):
        """Log an email delivery failure to the proposal chatter (T029/FR-041a).
        Does NOT raise so the DB transaction is not rolled back.
        """
        proposal = self.browse(proposal_id).exists()
        if proposal:
            proposal.message_post(
                body=_(
                    'Email delivery failed for event <b>%s</b>: %s',
                    event_name,
                    error_message,
                ),
                subject=_('Email Delivery Failure'),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

    @api.model
    def _seed_fix_states(self):
        """Corrige os estados das proposals de seed via SQL direto.
        Chamado por seed_proposals_states.xml após seed_proposals.xml.
        """
        from datetime import datetime, timedelta
        now = datetime.now()
        updates = {
            # QuickSol Real Estate proposals
            'proposal_sent_1':        ('sent',        {'sent_date': now - timedelta(hours=2)}),
            'proposal_negotiation_1': ('negotiation', {'sent_date': now - timedelta(days=3)}),
            'proposal_accepted_1':    ('accepted',    {'sent_date': now - timedelta(days=7),
                                                       'accepted_date': now - timedelta(days=2)}),
            'proposal_rejected_1':    ('rejected',    {'sent_date': now - timedelta(days=10),
                                                       'rejected_date': now - timedelta(days=5)}),
            'proposal_cancelled_1':   ('cancelled',   {}),
            'proposal_expired_1':     ('expired',     {'sent_date': now - timedelta(days=20)}),
            # Imobiliária Seed proposals
            'seed_proposal_sent_1':     ('sent',     {'sent_date': now - timedelta(hours=3)}),
            'seed_proposal_rejected_1': ('rejected', {'sent_date': now - timedelta(days=5),
                                                      'rejected_date': now - timedelta(days=2),
                                                      'rejection_reason': 'Valor abaixo do mínimo aceito.'}),
        }
        for xml_name, (state, extra) in updates.items():
            rec = self.env.ref(f'quicksol_estate.{xml_name}', raise_if_not_found=False)
            if not rec:
                continue
            vals = {'state': state, **extra}
            set_sql = ', '.join(f'"{k}" = %s' for k in vals)
            self.env.cr.execute(
                f'UPDATE real_estate_proposal SET {set_sql} WHERE id = %s',
                [*vals.values(), rec.id],
            )
