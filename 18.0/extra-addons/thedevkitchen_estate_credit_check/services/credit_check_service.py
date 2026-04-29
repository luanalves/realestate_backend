# -*- coding: utf-8 -*-
import logging
from odoo import fields, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CreditCheckService:

    def __init__(self, env):
        self.env = env

    # ================================================================== #
    #  SHARED HELPERS                                                      #
    # ================================================================== #

    def _get_proposal_or_404(self, proposal_id):

        proposal = self.env['real.estate.proposal'].browse(int(proposal_id))
        if not proposal.exists():
            raise UserError(_('Proposal not found.'))
        return proposal

    def _get_check_or_404(self, proposal_id, check_id):
        proposal = self._get_proposal_or_404(proposal_id)
        check = self.env['thedevkitchen.estate.credit.check'].browse(int(check_id))
        if not check.exists() or check.proposal_id.id != proposal.id:
            raise UserError(_('Credit check not found.'))
        return check

    def _assert_proposal_not_terminal(self, proposal):
        terminal_states = ('rejected', 'accepted', 'expired', 'cancelled')
        if proposal.state in terminal_states:
            raise UserError(_(
                'Cannot initiate a new credit check on a terminal proposal (state: %s).',
                proposal.state,
            ))

    def _assert_agent_owns_proposal(self, proposal):

        user = self.env.user
        if user.has_group('quicksol_estate.group_real_estate_owner'):
            return
        if user.has_group('quicksol_estate.group_real_estate_manager'):
            return
        # Agent scope check
        if user.has_group('quicksol_estate.group_real_estate_agent'):
            agent = self.env['real.estate.agent'].search([
                ('user_id', '=', user.id),
                ('company_id', '=', proposal.company_id.id),
            ], limit=1)
            if not agent or proposal.agent_id.id != agent.id:
                raise UserError(_('Access denied: proposal belongs to another agent.'))
            return
        raise UserError(_('You do not have permission to manage credit checks.'))

    # ================================================================== #
    #  US1 — Initiate Credit Check                                        #
    # ================================================================== #

    def initiate_credit_check(self, proposal_id, insurer_name):
        proposal = self._get_proposal_or_404(proposal_id)
        self._assert_agent_owns_proposal(proposal)
        self._assert_proposal_not_terminal(proposal)

        # FR-006: only lease proposals
        if proposal.proposal_type != 'lease':
            raise UserError(_(
                'Credit check analysis is only available for lease proposals.'
            ))

        # FR-001/FR-002: only sent or negotiation
        if proposal.state not in ('sent', 'negotiation'):
            raise UserError(_(
                'Credit check can only be initiated on proposals in '
                '"sent" or "negotiation" state (current: %s).',
                proposal.state,
            ))

        # FR-010: no existing pending check (partial unique index also enforces this at DB level)
        existing = self.env['thedevkitchen.estate.credit.check'].search([
            ('proposal_id', '=', proposal.id),
            ('result', '=', 'pending'),
            ('active', '=', True),
        ], limit=1)
        if existing:
            raise UserError(_(
                'A credit check is already pending for this proposal.'
            ))

        now = fields.Datetime.now()
        check = self.env['thedevkitchen.estate.credit.check'].create({
            'proposal_id': proposal.id,
            'company_id': proposal.company_id.id,
            'partner_id': proposal.partner_id.id,
            'insurer_name': insurer_name,
            'result': 'pending',
            'requested_by': self.env.user.id,
            'requested_at': now,
        })

        proposal.write({'state': 'credit_check_pending'})
        proposal.message_post(
            body=_(
                'Credit check initiated with insurer "%s" by %s.',
                insurer_name, self.env.user.name,
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        _logger.info(
            'spec-014: credit check %d initiated for proposal %s (insurer: %s)',
            check.id, proposal.proposal_code, insurer_name,
        )
        return check

    # ================================================================== #
    #  US2 — Register Result                                              #
    # ================================================================== #

    def register_result(self, proposal_id, check_id, result, rejection_reason=None, check_date=None):
        check = self._get_check_or_404(proposal_id, check_id)
        proposal = check.proposal_id
        self._assert_agent_owns_proposal(proposal)

        # FR-009: immutability — result already resolved
        if check.result != 'pending':
            raise UserError(_(
                'Credit check result is not in pending state and cannot be modified (immutable).'
            ))

        # Validate check_date not future (FR-024)
        if check_date:
            from datetime import date as _date
            try:
                from datetime import datetime
                if isinstance(check_date, str):
                    parsed = datetime.strptime(check_date, '%Y-%m-%d').date()
                else:
                    parsed = check_date
                if parsed > _date.today():
                    raise UserError(_('Analysis date cannot be a future date.'))
            except ValueError:
                raise UserError(_('Invalid check_date format. Use YYYY-MM-DD.'))
        else:
            parsed = None

        now = fields.Datetime.now()
        write_vals = {
            'result': result,
            'result_registered_by': self.env.user.id,
            'result_registered_at': now,
        }
        if parsed:
            write_vals['check_date'] = parsed
        if rejection_reason:
            write_vals['rejection_reason'] = rejection_reason

        check.write(write_vals)

        if result == 'approved':
            self._handle_approved(proposal)
        elif result == 'rejected':
            self._handle_rejected(proposal, rejection_reason)
        elif result == 'cancelled':
            self._handle_cancelled_via_api(proposal)

        proposal.message_post(
            body=_(
                'Credit check %s: result="%s" registered by %s.',
                check.id, result, self.env.user.name,
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        # Emit EventBus event (ADR-021 Outbox)
        self._emit_credit_check_event(check, result)

        _logger.info(
            'spec-014: credit check %d result=%s registered for proposal %s',
            check.id, result, proposal.proposal_code,
        )
        return check

    def _handle_approved(self, proposal):
        proposal.write({
            'state': 'accepted',
            'accepted_date': fields.Datetime.now(),
        })
        # Update lead to won
        if proposal.lead_id:
            proposal.lead_id.write({'state': 'won'})
        # Cancel all non-terminal competitors on this property
        from odoo.addons.quicksol_estate.models.proposal import TERMINAL_STATES
        competitors = self.env['real.estate.proposal'].search([
            ('property_id', '=', proposal.property_id.id),
            ('id', '!=', proposal.id),
            ('state', 'not in', list(TERMINAL_STATES)),
            ('active', '=', True),
        ])
        for comp in competitors:
            comp.write({
                'state': 'cancelled',
                'active': False,
                'cancellation_reason': _(
                    'Superseded by accepted proposal %s'
                ) % proposal.proposal_code,
                'superseded_by_id': proposal.id,
            })

    def _handle_rejected(self, proposal, rejection_reason):
        proposal.write({
            'state': 'rejected',
            'rejected_date': fields.Datetime.now(),
            'rejection_reason': rejection_reason or '',
            'active': False,
        })
        proposal._promote_next_queued()

    def _handle_cancelled_via_api(self, proposal):
        proposal.write({'state': 'sent'})

    def _emit_credit_check_event(self, check, result):
        try:
            from odoo.addons.quicksol_estate.celery_tasks import (
                send_proposal_notification,
            )
            send_proposal_notification.apply_async(
                kwargs={
                    'proposal_id': check.proposal_id.id,
                    'event_type': 'credit_check.result_registered',
                    'payload': {
                        'check_id': check.id,
                        'result': result,
                        'insurer_name': check.insurer_name,
                    },
                    'db': self.env.cr.dbname,
                },
                queue='notification_events',
            )
        except Exception:
            _logger.exception(
                'spec-014: failed to enqueue credit_check.result_registered '
                'for check %d — state transition succeeded; notification not sent.',
                check.id,
            )

    # ================================================================== #
    #  US4 — Client Credit History                                        #
    # ================================================================== #

    def get_client_credit_history(self, partner_id, limit=100, offset=0, company_id=None):

        company = self.env.company
        user = self.env.user

        # Verify the partner exists in the company (anti-enumeration, ADR-008)
        partner = self.env['res.partner'].browse(int(partner_id))
        if not partner.exists():
            raise UserError(_('Client not found.'))

        # Agent scope: only clients from their own proposals (any state)
        if not (
            user.has_group('quicksol_estate.group_real_estate_owner')
            or user.has_group('quicksol_estate.group_real_estate_manager')
            or user.has_group('quicksol_estate.group_real_estate_receptionist')
        ):
            if user.has_group('quicksol_estate.group_real_estate_agent'):
                agent = self.env['real.estate.agent'].search([
                    ('user_id', '=', user.id),
                    ('company_id', '=', company.id),
                ], limit=1)
                if not agent:
                    raise UserError(_('Client not found.'))
                # Check if this client has any proposal associated with this agent
                scope_proposals = self.env['real.estate.proposal'].with_context(
                    active_test=False
                ).search([
                    ('partner_id', '=', partner.id),
                    ('agent_id', '=', agent.id),
                    ('company_id', '=', company.id),
                ], limit=1)
                if not scope_proposals:
                    raise UserError(_('Client not found.'))
            else:
                raise UserError(_('Client not found.'))

        domain = [
            ('partner_id', '=', partner.id),
            ('company_id', '=', company.id),
            ('active', '=', True),
        ]
        total = self.env['thedevkitchen.estate.credit.check'].search_count(domain)
        checks = self.env['thedevkitchen.estate.credit.check'].search(
            domain,
            order='requested_at desc',
            limit=min(limit, 100),
            offset=offset,
        )

        approved = len(checks.filtered(lambda c: c.result == 'approved'))
        rejected = len(checks.filtered(lambda c: c.result == 'rejected'))
        pending = len(checks.filtered(lambda c: c.result == 'pending'))
        cancelled = len(checks.filtered(lambda c: c.result == 'cancelled'))

        return {
            'partner_id': partner.id,
            'summary': {
                'total': total,
                'approved': approved,
                'rejected': rejected,
                'pending': pending,
                'cancelled': cancelled,
            },
            'items': [c._to_dict() for c in checks],
            'limit': limit,
            'offset': offset,
            '_links': {
                'self': {'href': f'/api/v1/clients/{partner_id}/credit-history'},
            },
        }

    def get_checks_for_proposal(self, proposal_id, result_filter=None, limit=100, offset=0):
        proposal = self._get_proposal_or_404(proposal_id)
        self._assert_agent_owns_proposal(proposal)

        domain = [('proposal_id', '=', proposal.id)]
        if result_filter:
            domain.append(('result', '=', result_filter))

        return self.env['thedevkitchen.estate.credit.check'].search(
            domain,
            order='requested_at desc',
            limit=min(limit, 100),
            offset=offset,
        )
