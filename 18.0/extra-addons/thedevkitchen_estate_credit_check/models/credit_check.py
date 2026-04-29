# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CreditCheck(models.Model):
    _name = 'thedevkitchen.estate.credit.check'
    _description = 'Rental Credit Check (Análise de Ficha)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'requested_at desc'
    _rec_name = 'id'

    # ------------------------------------------------------------------ #
    #  Relations                                                           #
    # ------------------------------------------------------------------ #
    proposal_id = fields.Many2one(
        'real.estate.proposal',
        'Proposal',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        index=True,
        help='Denormalized from proposal. Enables company-scoped record rules without join.',
    )
    partner_id = fields.Many2one(
        'res.partner',
        'Tenant',
        required=True,
        index=True,
        help='Denormalized from proposal.partner_id.',
    )

    # ------------------------------------------------------------------ #
    #  Analysis details                                                    #
    # ------------------------------------------------------------------ #
    insurer_name = fields.Char(
        'Insurer',
        size=255,
        required=True,
        help='Name of the insurer performing the analysis (free text, FR-008, FR-022).',
    )
    result = fields.Selection(
        [
            ('pending',   'Pending'),
            ('approved',  'Approved'),
            ('rejected',  'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        'Result',
        required=True,
        default='pending',
        index=True,
        tracking=True,
    )
    check_date = fields.Date(
        'Analysis Date',
        help='Date the analysis was performed by the insurer (optional, must not be future).',
    )
    rejection_reason = fields.Text(
        'Rejection Reason',
        help='Required when result = rejected.',
        copy=False,
    )

    # ------------------------------------------------------------------ #
    #  Audit fields                                                        #
    # ------------------------------------------------------------------ #
    requested_by = fields.Many2one(
        'res.users',
        'Requested By',
        required=True,
        ondelete='restrict',
        default=lambda self: self.env.user,
    )
    requested_at = fields.Datetime(
        'Requested At',
        required=True,
        default=fields.Datetime.now,
    )
    result_registered_by = fields.Many2one(
        'res.users',
        'Result Registered By',
        ondelete='set null',
    )
    result_registered_at = fields.Datetime('Result Registered At')

    # ------------------------------------------------------------------ #
    #  Soft delete (ADR-015)                                               #
    # ------------------------------------------------------------------ #
    active = fields.Boolean(default=True)

    # ================================================================== #
    #  DB-LEVEL CONSTRAINT — partial unique index (ADR-027)               #
    # ================================================================== #

    def _auto_init(self):
        res = super()._auto_init()
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                thedevkitchen_estate_credit_check_one_pending_per_proposal
            ON thedevkitchen_estate_credit_check (proposal_id)
            WHERE result = 'pending' AND active = true
        """)
        return res

    # ================================================================== #
    #  PYTHON CONSTRAINTS                                                  #
    # ================================================================== #

    @api.constrains('result', 'rejection_reason')
    def _check_rejection_reason(self):
        for rec in self:
            if rec.result == 'rejected' and not (rec.rejection_reason or '').strip():
                raise ValidationError(
                    _('Rejection reason is required when result is Rejected.')
                )

    @api.constrains('check_date')
    def _check_date_not_future(self):
        from datetime import date
        today = date.today()
        for rec in self:
            if rec.check_date and rec.check_date > today:
                raise ValidationError(
                    _('Analysis date cannot be a future date.')
                )

    # ================================================================== #
    #  HELPERS                                                             #
    # ================================================================== #

    def _to_dict(self):
        """Return a serializable dict for API responses (ADR-007 HATEOAS)."""
        self.ensure_one()
        return {
            'id': self.id,
            'proposal_id': self.proposal_id.id,
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'insurer_name': self.insurer_name,
            'result': self.result,
            'check_date': str(self.check_date) if self.check_date else None,
            'rejection_reason': self.rejection_reason or None,
            'requested_by': self.requested_by.id,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'result_registered_by': self.result_registered_by.id if self.result_registered_by else None,
            'result_registered_at': self.result_registered_at.isoformat() if self.result_registered_at else None,
            '_links': {
                'self': {'href': f'/api/v1/proposals/{self.proposal_id.id}/credit-checks/{self.id}'},
                'proposal': {'href': f'/api/v1/proposals/{self.proposal_id.id}'},
            },
        }
