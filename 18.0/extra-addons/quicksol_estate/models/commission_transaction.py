# -*- coding: utf-8 -*-
"""
Real Estate Commission Transaction Model

Records commission transactions with immutable snapshots of commission rules.
Implements non-retroactive commission calculation - rules apply only from
their valid_from date forward.

Author: Quicksol Technologies
Date: 2026-01-12
User Story: US4 - Configurar Comissões de Agentes (P4)
ADRs: ADR-004 (Nomenclatura), ADR-008 (Multi-tenancy)
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import json
from datetime import datetime


class RealEstateCommissionTransaction(models.Model):
    _name = 'real.estate.commission.transaction'
    _description = 'Commission Transaction Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'calculated_at desc, id desc'
    _rec_name = 'display_name'
    
    # ==================== CORE FIELDS ====================
    
    agent_id = fields.Many2one(
        'real.estate.agent',
        'Agent',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
        help='Agent who earned this commission'
    )
    
    rule_id = fields.Many2one(
        'real.estate.commission.rule',
        'Commission Rule',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
        help='Commission rule used for calculation (for reference only)'
    )
    
    company_id = fields.Many2one(
        'thedevkitchen.estate.company',
        'Real Estate Company',
        required=True,
        related='agent_id.company_id',
        store=True,
        index=True,
        help='Company (auto-set from agent)'
    )
    
    # ==================== TRANSACTION DETAILS ====================
    
    transaction_type = fields.Selection(
        [
            ('sale', 'Sale'),
            ('rental', 'Rental'),
        ],
        'Transaction Type',
        required=True,
        tracking=True,
        help='Type of transaction that generated this commission'
    )
    
    transaction_reference = fields.Char(
        'Transaction Reference',
        index=True,
        help='External reference to the sale/lease record (e.g., "SALE-2024-001")'
    )
    
    transaction_date = fields.Date(
        'Transaction Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True,
        help='Date when the transaction occurred'
    )
    
    transaction_amount = fields.Monetary(
        'Transaction Amount',
        currency_field='currency_id',
        required=True,
        tracking=True,
        help='Total amount of the sale/rental transaction'
    )
    
    # ==================== COMMISSION CALCULATION ====================
    
    commission_amount = fields.Monetary(
        'Commission Amount',
        currency_field='currency_id',
        required=True,
        tracking=True,
        help='Calculated commission amount earned by the agent'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        'Currency',
        default=lambda self: self.env.ref('base.BRL').id,
        required=True,
        help='Currency for monetary fields (default: BRL - Brazilian Real)'
    )
    
    # ==================== IMMUTABLE RULE SNAPSHOT ====================
    
    rule_snapshot = fields.Text(
        'Rule Snapshot (JSON)',
        required=True,
        help='Immutable snapshot of commission rule at transaction time (JSON format)'
    )
    
    rule_percentage = fields.Float(
        'Applied Percentage',
        compute='_compute_rule_details',
        store=True,
        help='Percentage applied from rule snapshot'
    )
    
    rule_fixed_amount = fields.Monetary(
        'Applied Fixed Amount',
        currency_field='currency_id',
        compute='_compute_rule_details',
        store=True,
        help='Fixed amount applied from rule snapshot'
    )
    
    rule_structure_type = fields.Selection(
        [
            ('percentage', 'Percentage'),
            ('fixed', 'Fixed Amount'),
        ],
        'Commission Structure',
        compute='_compute_rule_details',
        store=True,
        help='Commission structure from rule snapshot'
    )
    
    # ==================== PAYMENT TRACKING ====================
    
    payment_status = fields.Selection(
        [
            ('pending', 'Pending Payment'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        'Payment Status',
        default='pending',
        required=True,
        tracking=True,
        help='Current payment status of this commission'
    )
    
    payment_date = fields.Date(
        'Payment Date',
        tracking=True,
        help='Date when commission was paid to agent'
    )
    
    payment_notes = fields.Text(
        'Payment Notes',
        help='Additional notes about commission payment'
    )
    
    # ==================== AUDIT FIELDS ====================
    
    calculated_at = fields.Datetime(
        'Calculated At',
        required=True,
        default=fields.Datetime.now,
        readonly=True,
        help='Timestamp when commission was calculated'
    )
    
    calculated_by = fields.Many2one(
        'res.users',
        'Calculated By',
        default=lambda self: self.env.user,
        readonly=True,
        help='User who triggered commission calculation'
    )
    
    create_date = fields.Datetime('Created On', readonly=True)
    create_uid = fields.Many2one('res.users', 'Created By', readonly=True)
    write_date = fields.Datetime('Last Updated', readonly=True)
    write_uid = fields.Many2one('res.users', 'Updated By', readonly=True)
    
    display_name = fields.Char(
        'Display Name',
        compute='_compute_display_name',
        store=False
    )
    
    # ==================== COMPUTED METHODS ====================
    
    @api.depends('rule_snapshot')
    def _compute_rule_details(self):
        """Extract rule details from JSON snapshot for display"""
        for transaction in self:
            if transaction.rule_snapshot:
                try:
                    snapshot = json.loads(transaction.rule_snapshot)
                    transaction.rule_percentage = snapshot.get('percentage', 0.0)
                    transaction.rule_fixed_amount = snapshot.get('fixed_amount', 0.0)
                    transaction.rule_structure_type = snapshot.get('structure_type', 'percentage')
                except (json.JSONDecodeError, ValueError):
                    transaction.rule_percentage = 0.0
                    transaction.rule_fixed_amount = 0.0
                    transaction.rule_structure_type = 'percentage'
            else:
                transaction.rule_percentage = 0.0
                transaction.rule_fixed_amount = 0.0
                transaction.rule_structure_type = 'percentage'
    
    @api.depends('agent_id', 'commission_amount', 'transaction_date')
    def _compute_display_name(self):
        """Generate display name for commission transaction"""
        for transaction in self:
            if transaction.agent_id and transaction.commission_amount:
                transaction.display_name = _('R$ %(amount).2f - %(agent)s (%(date)s)') % {
                    'amount': transaction.commission_amount,
                    'agent': transaction.agent_id.name,
                    'date': transaction.transaction_date or fields.Date.today()
                }
            else:
                transaction.display_name = _('Commission Transaction #%s') % transaction.id
    
    # ==================== CONSTRAINT METHODS ====================
    
    @api.constrains('transaction_amount', 'commission_amount')
    def _check_positive_amounts(self):
        """Validate amounts are positive"""
        for transaction in self:
            if transaction.transaction_amount <= 0:
                raise ValidationError(
                    _('Transaction amount must be positive. Got: %.2f') 
                    % transaction.transaction_amount
                )
            if transaction.commission_amount < 0:
                raise ValidationError(
                    _('Commission amount cannot be negative. Got: %.2f') 
                    % transaction.commission_amount
                )
    
    @api.constrains('commission_amount', 'transaction_amount')
    def _check_commission_reasonable(self):
        """Warn if commission exceeds 50% of transaction (likely error)"""
        for transaction in self:
            if transaction.transaction_amount > 0:
                commission_percentage = (transaction.commission_amount / transaction.transaction_amount) * 100
                if commission_percentage > 50:
                    raise ValidationError(
                        _('Commission (%.2f%%) exceeds 50%% of transaction amount. '
                          'This is likely an error. Please verify calculation.') 
                        % commission_percentage
                    )
    
    @api.constrains('rule_snapshot')
    def _check_rule_snapshot_valid(self):
        """Validate rule_snapshot is valid JSON"""
        for transaction in self:
            if transaction.rule_snapshot:
                try:
                    json.loads(transaction.rule_snapshot)
                except (json.JSONDecodeError, ValueError) as e:
                    raise ValidationError(
                        _('Rule snapshot contains invalid JSON: %s') % str(e)
                    )
    
    @api.constrains('payment_date', 'payment_status')
    def _check_payment_consistency(self):
        """Validate payment_date only set when status is 'paid'"""
        for transaction in self:
            if transaction.payment_date and transaction.payment_status != 'paid':
                raise ValidationError(
                    _('Payment date can only be set when payment status is "Paid"')
                )
            if transaction.payment_status == 'paid' and not transaction.payment_date:
                raise ValidationError(
                    _('Payment date is required when payment status is "Paid"')
                )
    
    # ==================== CRUD OVERRIDES ====================
    
    @api.model
    def create(self, vals):
        """Override create to enforce immutability and create rule snapshot"""
        # If rule_snapshot not provided, create it from rule_id
        if 'rule_id' in vals and 'rule_snapshot' not in vals:
            rule = self.env['real.estate.commission.rule'].browse(vals['rule_id'])
            if rule:
                vals['rule_snapshot'] = json.dumps({
                    'percentage': rule.percentage,
                    'fixed_amount': rule.fixed_amount,
                    'structure_type': rule.structure_type,
                    'transaction_type': rule.transaction_type,
                    'min_value': rule.min_value,
                    'max_value': rule.max_value,
                    'valid_from': str(rule.valid_from) if rule.valid_from else None,
                    'valid_until': str(rule.valid_until) if rule.valid_until else None,
                })
        
        transaction = super().create(vals)
        # Commission transaction creation is automatically tracked by mail.thread
        # via tracking=True on relevant fields (agent_id, commission_amount, etc.)
        
        return transaction
    
    def write(self, vals):
        """Override write to prevent modification of critical fields after creation"""
        # Immutable fields - cannot be changed after creation
        immutable_fields = [
            'agent_id', 'rule_id', 'transaction_type', 'transaction_date',
            'transaction_amount', 'commission_amount', 'rule_snapshot', 'calculated_at'
        ]
        
        for field in immutable_fields:
            if field in vals:
                raise UserError(
                    _('Cannot modify %(field)s after commission transaction is created. '
                      'This field is immutable for audit purposes.') % {'field': field}
                )
        
        result = super().write(vals)
        
        # Log payment status changes
        if 'payment_status' in vals:
            for transaction in self:
                transaction.message_post(
                    body=_('Payment status changed to: %s') 
                    % dict(transaction._fields['payment_status'].selection)[transaction.payment_status]
                )
        
        return result
    
    def unlink(self):
        """Prevent deletion of commission transactions"""
        raise UserError(
            _('Commission transactions cannot be deleted for audit purposes. '
              'Set payment_status to "Cancelled" instead.')
        )
    
    # ==================== ACTION METHODS ====================
    
    def action_mark_paid(self):
        """Mark commission as paid"""
        self.ensure_one()
        if self.payment_status == 'paid':
            raise UserError(_('Commission is already marked as paid'))
        
        self.write({
            'payment_status': 'paid',
            'payment_date': fields.Date.context_today(self),
        })
        
        self.message_post(
            body=_('Commission marked as paid: R$ %(amount).2f on %(date)s') % {
                'amount': self.commission_amount,
                'date': self.payment_date
            }
        )
    
    def action_cancel(self):
        """Cancel commission transaction"""
        self.ensure_one()
        if self.payment_status == 'paid':
            raise UserError(
                _('Cannot cancel a commission that has been paid. '
                  'Please process a reversal instead.')
            )
        
        self.write({'payment_status': 'cancelled'})
        
        self.message_post(
            body=_('Commission transaction cancelled')
        )
    
    # ==================== SQL CONSTRAINTS ====================
    
    _sql_constraints = [
        (
            'check_positive_transaction_amount',
            'CHECK(transaction_amount > 0)',
            'Transaction amount must be positive'
        ),
        (
            'check_non_negative_commission',
            'CHECK(commission_amount >= 0)',
            'Commission amount cannot be negative'
        ),
    ]
