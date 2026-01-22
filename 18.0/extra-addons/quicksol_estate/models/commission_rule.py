# -*- coding: utf-8 -*-
"""
Real Estate Commission Rule Model

Manages commission rules for real estate agents with support for percentage
and fixed-amount structures. Rules apply only to future transactions (non-retroactive).

Author: Quicksol Technologies
Date: 2026-01-12
User Story: US4 - Configurar Comissões de Agentes (P4)
ADRs: ADR-004 (Nomenclatura), ADR-008 (Multi-tenancy), ADR-015 (Soft-Delete)
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class RealEstateCommissionRule(models.Model):
    _name = 'real.estate.commission.rule'
    _description = 'Commission Rule for Real Estate Agent'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'valid_from desc, id desc'
    
    # ==================== CORE FIELDS ====================
    
    agent_id = fields.Many2one(
        'real.estate.agent',
        'Agent',
        required=True,
        ondelete='cascade',
        tracking=True,
        index=True,
        help='Agent this commission rule applies to'
    )
    
    company_id = fields.Many2one(
        'thedevkitchen.estate.company',
        'Real Estate Company',
        required=True,
        default=lambda self: self._get_default_company(),
        ondelete='restrict',
        tracking=True,
        index=True,
        help='Company this commission rule belongs to (for multi-tenant isolation)'
    )
    
    # ==================== TRANSACTION DETAILS ====================
    
    transaction_type = fields.Selection(
        [
            ('sale', 'Sale'),
            ('rental', 'Rental'),
            ('both', 'Both (Sale and Rental)'),
        ],
        'Transaction Type',
        required=True,
        default='sale',
        tracking=True,
        help='Type of transaction this rule applies to'
    )
    
    structure_type = fields.Selection(
        [
            ('percentage', 'Percentage'),
            ('fixed', 'Fixed Amount'),
        ],
        'Commission Structure',
        required=True,
        default='percentage',
        tracking=True,
        help='How commission is calculated: percentage of value or fixed amount'
    )
    
    # ==================== COMMISSION CALCULATION ====================
    
    percentage = fields.Float(
        'Commission Percentage',
        digits=(5, 2),
        default=0.0,
        tracking=True,
        help='Commission percentage (0-100). Used when structure_type = percentage'
    )
    
    fixed_amount = fields.Monetary(
        'Fixed Commission Amount',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='Fixed commission amount. Used when structure_type = fixed'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        'Currency',
        default=lambda self: self._get_default_currency(),
        required=True,
        help='Currency for monetary fields (default: BRL - Brazilian Real)'
    )
    
    # ==================== VALUE RANGE CONSTRAINTS ====================
    
    min_value = fields.Monetary(
        'Minimum Transaction Value',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='Minimum transaction value for this rule to apply. 0 = no minimum'
    )
    
    max_value = fields.Monetary(
        'Maximum Transaction Value',
        currency_field='currency_id',
        default=999999999.99,
        tracking=True,
        help='Maximum transaction value for this rule to apply. Large value = no maximum'
    )
    
    # ==================== VALIDITY PERIOD ====================
    
    valid_from = fields.Date(
        'Valid From',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True,
        help='Date from which this rule becomes active (non-retroactive)'
    )
    
    valid_until = fields.Date(
        'Valid Until',
        tracking=True,
        index=True,
        help='Date until which this rule is active. Leave empty for no expiration'
    )
    
    # ==================== COMPUTED FIELDS ====================
    
    is_active = fields.Boolean(
        'Is Currently Active',
        compute='_compute_is_active',
        store=False,
        help='Whether this rule is currently active based on valid_from/valid_until dates'
    )
    
    active = fields.Boolean(
        'Active',
        default=True,
        tracking=True,
        help='Set to false to archive this rule (soft-delete)'
    )
    
    # ==================== RELATIONSHIP FIELDS ====================
    
    transaction_ids = fields.One2many(
        'real.estate.commission.transaction',
        'rule_id',
        'Commission Transactions',
        readonly=True,
        help='Commission transactions calculated using this rule'
    )
    
    transaction_count = fields.Integer(
        'Transaction Count',
        compute='_compute_transaction_count',
        store=False,
        help='Number of transactions using this rule'
    )
    
    # ==================== AUDIT FIELDS ====================
    
    create_date = fields.Datetime('Created On', readonly=True)
    create_uid = fields.Many2one('res.users', 'Created By', readonly=True)
    write_date = fields.Datetime('Last Updated', readonly=True)
    write_uid = fields.Many2one('res.users', 'Updated By', readonly=True)
    
    # ==================== COMPUTED METHODS ====================
    
    @api.depends('valid_from', 'valid_until')
    def _compute_is_active(self):
        """Compute whether rule is currently active based on validity dates"""
        today = fields.Date.context_today(self)
        
        for rule in self:
            if not rule.active:
                rule.is_active = False
                continue
            
            # Check valid_from
            if rule.valid_from and rule.valid_from > today:
                rule.is_active = False
                continue
            
            # Check valid_until
            if rule.valid_until and rule.valid_until < today:
                rule.is_active = False
                continue
            
            rule.is_active = True
    
    @api.depends('transaction_ids')
    def _compute_transaction_count(self):
        """Count commission transactions using this rule"""
        for rule in self:
            rule.transaction_count = len(rule.transaction_ids)
    
    # ==================== CONSTRAINT METHODS ====================
    
    @api.constrains('percentage')
    def _check_percentage_range(self):
        """Validate percentage is between 0 and 100"""
        for rule in self:
            if rule.structure_type == 'percentage':
                if rule.percentage < 0 or rule.percentage > 100:
                    raise ValidationError(
                        _('Commission percentage must be between 0 and 100. '
                          'Got: %.2f%%') % rule.percentage
                    )
    
    @api.constrains('fixed_amount')
    def _check_fixed_amount(self):
        """Validate fixed amount is not negative"""
        for rule in self:
            if rule.structure_type == 'fixed':
                if rule.fixed_amount < 0:
                    raise ValidationError(
                        _('Fixed commission amount cannot be negative. '
                          'Got: %.2f') % rule.fixed_amount
                    )
    
    @api.constrains('min_value', 'max_value')
    def _check_value_range(self):
        """Validate min_value <= max_value"""
        for rule in self:
            if rule.min_value > rule.max_value:
                raise ValidationError(
                    _('Minimum value (%.2f) cannot be greater than maximum value (%.2f)') 
                    % (rule.min_value, rule.max_value)
                )
    
    @api.constrains('valid_from', 'valid_until')
    def _check_validity_period(self):
        """Validate valid_from <= valid_until"""
        for rule in self:
            if rule.valid_from and rule.valid_until:
                if rule.valid_from > rule.valid_until:
                    raise ValidationError(
                        _('Valid From date (%s) cannot be after Valid Until date (%s)') 
                        % (rule.valid_from, rule.valid_until)
                    )
    
    @api.constrains('agent_id', 'company_id')
    def _check_agent_company_match(self):
        """Validate agent belongs to the same company as the rule"""
        for rule in self:
            if rule.agent_id and rule.company_id:
                if rule.agent_id.company_id.id != rule.company_id.id:
                    raise ValidationError(
                        _('Commission rule company (%s) must match agent company (%s)') 
                        % (rule.company_id.name, rule.agent_id.company_id.name)
                    )
    
    # ==================== CRUD OVERRIDES ====================
    
    @api.model
    def create(self, vals):
        """Override create to auto-set company_id from agent if not provided"""
        # Auto-set company from agent if not specified
        if 'agent_id' in vals and 'company_id' not in vals:
            agent = self.env['real.estate.agent'].browse(vals['agent_id'])
            if agent and agent.company_id:
                vals['company_id'] = agent.company_id.id
        
        rule = super().create(vals)
        # Commission rule creation is automatically tracked by mail.thread
        # via tracking=True on relevant fields (agent_id, transaction_type, etc.)
        
        return rule
    
    def write(self, vals):
        """Override write to prevent company_id changes"""
        if 'company_id' in vals and any(rule.company_id.id != vals['company_id'] for rule in self):
            raise ValidationError(
                _('Cannot change company of an existing commission rule. '
                  'Create a new rule instead.')
            )
        
        result = super().write(vals)
        return result
    
    # ==================== HELPER METHODS ====================
    
    def _get_default_company(self):
        """Get default company from user context"""
        user = self.env.user
        if hasattr(user, 'estate_default_company_id') and user.estate_default_company_id:
            return user.estate_default_company_id.id
        if hasattr(user, 'estate_company_ids') and user.estate_company_ids:
            return user.estate_company_ids[0].id
        return None
    
    def _get_default_currency(self):
        """
        Get default currency for commission rules.
        Tries to use BRL (Brazilian Real) as default, falls back to company currency.
        """
        try:
            return self.env.ref('base.BRL').id
        except ValueError:
            # BRL currency not installed, fall back to company currency
            if self.env.company.currency_id:
                return self.env.company.currency_id.id
            return None
    
    def name_get(self):
        """Custom display name for commission rules"""
        result = []
        for rule in self:
            if rule.structure_type == 'percentage':
                name = _('%(percentage).2f%% commission - %(type)s') % {
                    'percentage': rule.percentage,
                    'type': dict(rule._fields['transaction_type'].selection)[rule.transaction_type]
                }
            else:
                name = _('R$ %(amount).2f commission - %(type)s') % {
                    'amount': rule.fixed_amount,
                    'type': dict(rule._fields['transaction_type'].selection)[rule.transaction_type]
                }
            
            if rule.valid_until:
                name += _(' (expires %s)') % rule.valid_until
            
            result.append((rule.id, name))
        
        return result
    
    def calculate_split_commission(self, property_id, transaction_amount, transaction_type='sale'):
        """
        Calculate commission split when property has both agent_id and prospector_id.
        
        Args:
            property_id: Property record (real.estate.property)
            transaction_amount: Sale/rental amount (float)
            transaction_type: 'sale' or 'rental' (default: 'sale')
        
        Returns:
            dict: {
                'prospector_commission': float,
                'agent_commission': float,
                'total_commission': float,
                'split_percentage': float,  # Prospector's share (0.0-1.0)
            }
        
        Business Logic (FR-054 to FR-060):
            - If prospector_id == agent_id OR prospector_id is empty → no split (100% to agent)
            - If prospector_id != agent_id:
                * Get split percentage from system parameter (default 30%)
                * Calculate total commission using agent's commission rule
                * Prospector receives: total_commission * split_percentage
                * Agent receives: total_commission * (1 - split_percentage)
        
        Example:
            Property sale: R$ 500,000
            Agent commission rule: 6% = R$ 30,000 total
            Split percentage: 30%
            → Prospector: R$ 9,000 (30% of R$ 30,000)
            → Agent: R$ 21,000 (70% of R$ 30,000)
        """
        self.ensure_one()
        
        if not property_id or not property_id.agent_id:
            raise ValidationError(_('Property must have an assigned agent to calculate commission.'))
        
        # Check if split applies (prospector_id exists and differs from agent_id)
        if not property_id.prospector_id or property_id.prospector_id == property_id.agent_id:
            # No split: 100% to agent
            total_commission = self._calculate_commission_amount(transaction_amount)
            return {
                'prospector_commission': 0.0,
                'agent_commission': total_commission,
                'total_commission': total_commission,
                'split_percentage': 0.0,
            }
        
        # Get split percentage from system parameter
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        split_percentage = float(
            IrConfigParameter.get_param(
                'quicksol_estate.prospector_commission_percentage',
                default='0.30'
            )
        )
        
        # Validate split percentage (0.0-1.0)
        if not 0.0 <= split_percentage <= 1.0:
            raise ValidationError(
                _('Invalid prospector commission split percentage: %(percentage).2f%%. '
                  'Must be between 0.0 and 1.0.') % {'percentage': split_percentage}
            )
        
        # Calculate total commission using agent's rule
        total_commission = self._calculate_commission_amount(transaction_amount)
        
        # Calculate split
        prospector_commission = total_commission * split_percentage
        agent_commission = total_commission * (1 - split_percentage)
        
        return {
            'prospector_commission': prospector_commission,
            'agent_commission': agent_commission,
            'total_commission': total_commission,
            'split_percentage': split_percentage,
        }
    
    def _calculate_commission_amount(self, transaction_amount):
        """
        Helper method: Calculate commission amount based on rule structure.
        
        Args:
            transaction_amount: Sale/rental value (float)
        
        Returns:
            float: Commission amount
        """
        self.ensure_one()
        
        if self.structure_type == 'percentage':
            return transaction_amount * (self.percentage / 100.0)
        else:
            return self.fixed_amount
    
    # ==================== SQL CONSTRAINTS ====================
    
    _sql_constraints = [
        (
            'check_positive_percentage',
            'CHECK(percentage >= 0)',
            'Commission percentage must be non-negative'
        ),
        (
            'check_positive_fixed_amount',
            'CHECK(fixed_amount >= 0)',
            'Fixed commission amount must be non-negative'
        ),
        (
            'check_value_range_positive',
            'CHECK(min_value >= 0 AND max_value >= 0)',
            'Transaction value range must be non-negative'
        ),
    ]
