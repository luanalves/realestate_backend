# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProposalCreditCheckExtension(models.Model):
    """
    Extends real.estate.proposal to add credit_check_pending state,
    the reverse relation to CreditChecks, and the credit_history_summary
    computed field. Also overrides action_cancel() and action_counter()
    to enforce the credit-check invariants (FR-007b, FR-005a).
    Extends the spec-013 daily cron for credit_check_pending expiry (FR-007a).
    """
    _inherit = 'real.estate.proposal'

    # ------------------------------------------------------------------ #
    #  New state value — injected into the existing Selection field        #
    # ------------------------------------------------------------------ #
    state = fields.Selection(
        selection_add=[
            ('credit_check_pending', 'Credit Check Pending'),
        ],
        ondelete={'credit_check_pending': 'cascade'},
    )

    # ------------------------------------------------------------------ #
    #  Reverse relation to CreditChecks                                   #
    # ------------------------------------------------------------------ #
    credit_check_ids = fields.One2many(
        'thedevkitchen.estate.credit.check',
        'proposal_id',
        'Credit Checks',
    )

    # ------------------------------------------------------------------ #
    #  Computed: client credit history summary                            #
    # ------------------------------------------------------------------ #
    credit_history_summary = fields.Char(
        'Credit History',
        compute='_compute_credit_history_summary',
        store=False,
        help='Approved/rejected counts for this client across all proposals in the company.',
    )

    @api.depends('partner_id', 'company_id', 'credit_check_ids')
    def _compute_credit_history_summary(self):
        for rec in self:
            if not rec.partner_id or not rec.company_id:
                rec.credit_history_summary = ''
                continue
            checks = self.env['thedevkitchen.estate.credit.check'].search([
                ('partner_id', '=', rec.partner_id.id),
                ('company_id', '=', rec.company_id.id),
                ('active', '=', True),
            ])
            approved = len(checks.filtered(lambda c: c.result == 'approved'))
            rejected = len(checks.filtered(lambda c: c.result == 'rejected'))
            rec.credit_history_summary = f"{approved} aprovada(s) / {rejected} rejeitada(s)"

    # ================================================================== #
    #  OVERRIDES                                                           #
    # ================================================================== #

    def action_cancel(self, cancellation_reason=''):
        """
        Override: before cancelling, if proposal is in credit_check_pending,
        mark the active pending CreditCheck as cancelled (FR-007b).
        """
        for rec in self:
            if rec.state == 'credit_check_pending':
                pending_check = self.env['thedevkitchen.estate.credit.check'].search([
                    ('proposal_id', '=', rec.id),
                    ('result', '=', 'pending'),
                    ('active', '=', True),
                ], limit=1)
                if pending_check:
                    pending_check.write({
                        'result': 'cancelled',
                        'result_registered_by': self.env.user.id,
                        'result_registered_at': fields.Datetime.now(),
                    })
                    rec.message_post(
                        body=_('Credit check cancelled automatically due to proposal cancellation.'),
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                    )
        return super().action_cancel(cancellation_reason)

    def action_counter(self, vals):
        """
        Override: block counter-proposal creation when proposal is in
        credit_check_pending state (FR-005a).
        """
        self.ensure_one()
        if self.state == 'credit_check_pending':
            raise UserError(_(
                'Counter-proposal not allowed while a credit check is pending. '
                'Please wait for the analysis result before negotiating.'
            ))
        return super().action_counter(vals)

    # ================================================================== #
    #  CRON EXTENSION — expire credit_check_pending proposals (FR-007a)  #
    # ================================================================== #

    @api.model
    def _cron_expire_proposals(self):
        """
        Extend spec-013 cron: also expire proposals in credit_check_pending
        state when their valid_until date has passed (FR-007a).

        For each expired credit_check_pending proposal:
        1. Mark the active pending CreditCheck as cancelled.
        2. Move proposal to expired.
        3. Promote next queued proposal.
        4. Post timeline message.
        """
        # Run the base spec-013 expiry first (sent + negotiation states)
        super()._cron_expire_proposals()

        today = fields.Date.today()
        pending_expired = self.search([
            ('state', '=', 'credit_check_pending'),
            ('active', '=', True),
            ('valid_until', '<', today),
        ])
        _logger.info(
            'spec-014 expiration cron: %d credit_check_pending proposals to expire',
            len(pending_expired),
        )
        CHUNK = 200
        for i in range(0, len(pending_expired), CHUNK):
            chunk = pending_expired[i:i + CHUNK]
            for rec in chunk:
                pending_check = self.env['thedevkitchen.estate.credit.check'].search([
                    ('proposal_id', '=', rec.id),
                    ('result', '=', 'pending'),
                    ('active', '=', True),
                ], limit=1)
                if pending_check:
                    pending_check.write({
                        'result': 'cancelled',
                        'result_registered_by': self.env.user.id,
                        'result_registered_at': fields.Datetime.now(),
                    })
                rec.write({'state': 'expired', 'active': False})
                rec._promote_next_queued()
                rec.message_post(
                    body=_(
                        'Proposal expired: validity date passed while credit check was pending. '
                        'Active credit check cancelled automatically.'
                    ),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            if not self.env.registry.in_test_mode():
                try:
                    self.env.cr.commit()
                except AssertionError:
                    pass  # silently skip commit when cursor is test-wrapped
