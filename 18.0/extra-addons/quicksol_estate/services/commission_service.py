# -*- coding: utf-8 -*-

from odoo import _
from odoo.exceptions import ValidationError, UserError, AccessError
from odoo.sql_db import Cursor
from datetime import datetime, date
import logging
import json

_logger = logging.getLogger(__name__)


class CommissionService:

    def __init__(self, env):
        self.env = env
    
    def calculate_commission(self, rule, transaction_amount):
        if not rule:
            raise ValidationError(_('Commission rule is required'))
        
        if transaction_amount <= 0:
            raise ValidationError(
                _('Transaction amount must be positive. Got: %.2f') % transaction_amount
            )
        
        # Verify transaction amount is within rule's value range
        if transaction_amount < rule.min_value:
            raise ValidationError(
                _('Transaction amount (%.2f) is below minimum value (%.2f) for this rule') 
                % (transaction_amount, rule.min_value)
            )
        
        if transaction_amount > rule.max_value:
            raise ValidationError(
                _('Transaction amount (%.2f) exceeds maximum value (%.2f) for this rule') 
                % (transaction_amount, rule.max_value)
            )
        
        # Calculate based on structure type
        if rule.structure_type == 'percentage':
            commission = (transaction_amount * rule.percentage) / 100.0
            _logger.info(
                'Calculated percentage commission: %.2f%% of %.2f = %.2f',
                rule.percentage, transaction_amount, commission
            )
        elif rule.structure_type == 'fixed':
            commission = rule.fixed_amount
            _logger.info(
                'Applied fixed commission: %.2f (transaction: %.2f)',
                commission, transaction_amount
            )
        else:
            raise ValidationError(
                _('Invalid commission structure type: %s') % rule.structure_type
            )
        
        return commission
    
    def get_active_rule_for_agent(self, agent_id, transaction_type, transaction_date=None):
        if transaction_date is None:
            transaction_date = date.today()
        
        if isinstance(transaction_date, datetime):
            transaction_date = transaction_date.date()
        
        # Build domain for active rules
        domain = [
            ('agent_id', '=', agent_id),
            ('active', '=', True),
            '|',
            ('transaction_type', '=', transaction_type),
            ('transaction_type', '=', 'both'),
            ('valid_from', '<=', transaction_date),  # Non-retroactive: must be valid from this date
        ]
        
        # Add valid_until check (if set, must not be expired)
        domain.append(
            '|',
        )
        domain.append(('valid_until', '=', False))  # No expiration
        domain.append(('valid_until', '>=', transaction_date))  # Or not yet expired
        
        # Search for matching rules, order by most recent first
        rules = self.env['real.estate.commission.rule'].search(
            domain,
            order='valid_from desc, id desc',
            limit=1
        )
        
        if rules:
            _logger.info(
                'Found active commission rule (ID: %s) for agent %s, type %s, date %s',
                rules.id, agent_id, transaction_type, transaction_date
            )
            return rules[0]
        else:
            _logger.warning(
                'No active commission rule found for agent %s, type %s, date %s',
                agent_id, transaction_type, transaction_date
            )
            return False
    
    def create_commission_transaction(self, agent_id, company_id, transaction_type, transaction_amount, 
                                     transaction_date=None, transaction_reference=None):
        if transaction_date is None:
            transaction_date = date.today()
        
        if isinstance(transaction_date, datetime):
            transaction_date = transaction_date.date()
        
        # Get active rule
        rule = self.get_active_rule_for_agent(agent_id, transaction_type, transaction_date)
        
        if not rule:
            agent = self.env['real.estate.agent'].browse(agent_id)
            raise UserError(
                _('No active commission rule found for agent %(agent)s and transaction type %(type)s '
                  'on date %(date)s. Please configure a commission rule first.') % {
                    'agent': agent.name if agent else f'ID {agent_id}',
                    'type': transaction_type,
                    'date': transaction_date
                }
            )
        
        # Calculate commission
        commission_amount = self.calculate_commission(rule, transaction_amount)
        
        # Create rule snapshot (immutable)
        rule_snapshot = json.dumps({
            'percentage': rule.percentage,
            'fixed_amount': rule.fixed_amount,
            'structure_type': rule.structure_type,
            'transaction_type': rule.transaction_type,
            'min_value': rule.min_value,
            'max_value': rule.max_value,
            'valid_from': str(rule.valid_from) if rule.valid_from else None,
            'valid_until': str(rule.valid_until) if rule.valid_until else None,
            'rule_id': rule.id,
            'rule_name': rule.name_get()[0][1] if rule.name_get() else '',
        })
        
        # Create transaction record
        transaction = self.env['real.estate.commission.transaction'].create({
            'agent_id': agent_id,
            'company_id': company_id,
            'rule_id': rule.id,
            'transaction_type': transaction_type,
            'transaction_amount': transaction_amount,
            'commission_amount': commission_amount,
            'transaction_date': transaction_date,
            'transaction_reference': transaction_reference,
            'rule_snapshot': rule_snapshot,
            'payment_status': 'pending',
            'calculated_at': datetime.now(),
            'calculated_by': self.env.user.id,
        })
        
        _logger.info(
            'Created commission transaction (ID: %s) for agent %s: R$ %.2f commission '
            '(%.2f%% of R$ %.2f)',
            transaction.id, agent_id, commission_amount,
            rule.percentage if rule.structure_type == 'percentage' else 0,
            transaction_amount
        )
        
        return transaction
    
    def bulk_create_transactions(self, transactions_data):
        created_transactions = []
        errors = []
        
        # Use savepoint for transactional integrity - all or nothing
        savepoint = self.env.cr.savepoint()
        try:
            for i, data in enumerate(transactions_data):
                try:
                    transaction = self.create_commission_transaction(
                        agent_id=data['agent_id'],
                        transaction_type=data['transaction_type'],
                        transaction_amount=data['transaction_amount'],
                        transaction_date=data.get('transaction_date'),
                        transaction_reference=data.get('transaction_reference'),
                    )
                    created_transactions.append(transaction)
                except (ValidationError, UserError) as e:
                    error_msg = f'Transaction {i+1}: {str(e)}'
                    errors.append(error_msg)
                    _logger.error('Bulk transaction creation failed: %s', error_msg)
            
            if errors:
                # Rollback all changes if any error occurred
                savepoint.__exit__(True, None, None)
                raise UserError(
                    _('Failed to create %(count)s transaction(s):\n%(errors)s') % {
                        'count': len(errors),
                        'errors': '\n'.join(errors)
                    }
                )
            
            # Commit the savepoint if all transactions succeeded
            savepoint.__exit__(False, None, None)
        except Exception:
            # Ensure savepoint is cleaned up on unexpected errors
            try:
                savepoint.__exit__(True, None, None)
            except Exception:
                pass
            raise
        
        _logger.info(
            'Bulk created %s commission transactions successfully',
            len(created_transactions)
        )
        
        return created_transactions
    
    def get_agent_commission_summary(self, agent_id, date_from=None, date_to=None):

        # Load agent and verify company isolation
        agent = self.env['real.estate.agent'].browse(agent_id)
        
        if not agent.exists():
            raise ValidationError(_('Agent with ID %s does not exist') % agent_id)
        
        # Check if agent's company is accessible to current user
        user_accessible_companies = self.env.user.company_ids
        if user_accessible_companies and agent.company_id not in user_accessible_companies:
            raise AccessError(
                _('You do not have access to the company of agent %s') % agent.name
            )
        
        domain = [('agent_id', '=', agent_id)]
        
        if date_from:
            domain.append(('transaction_date', '>=', date_from))
        if date_to:
            domain.append(('transaction_date', '<=', date_to))
        
        transactions = self.env['real.estate.commission.transaction'].search(domain)
        
        total_commission = sum(t.commission_amount for t in transactions)
        paid_commission = sum(
            t.commission_amount for t in transactions if t.payment_status == 'paid'
        )
        pending_commission = sum(
            t.commission_amount for t in transactions if t.payment_status == 'pending'
        )
        
        return {
            'total_transactions': len(transactions),
            'total_commission': total_commission,
            'paid_commission': paid_commission,
            'pending_commission': pending_commission,
            'cancelled_commission': total_commission - paid_commission - pending_commission,
            'transactions': transactions,
        }
