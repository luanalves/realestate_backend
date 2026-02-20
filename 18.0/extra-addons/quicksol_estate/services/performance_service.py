# -*- coding: utf-8 -*-

import logging
import json
from datetime import date, datetime, timedelta
from odoo import models, fields
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PerformanceService:

    def __init__(self, env):

        self.env = env
        self.cache_ttl = 300  # 5 minutes cache TTL
    
    def get_agent_performance(self, agent_id, date_from=None, date_to=None):
        # Validate agent exists
        agent = self.env['real.estate.agent'].sudo().browse(agent_id)
        if not agent.exists():
            raise UserError(f'Agent {agent_id} not found')
        
        # Company isolation check
        user = self.env.user
        if hasattr(user, 'estate_company_ids'):
            if agent.company_id.id not in user.estate_company_ids.ids:
                raise UserError('Access denied: Agent belongs to a different company')
        
        # Check cache first
        cache_key = f"performance:agent:{agent_id}:{date_from}:{date_to}"
        cached_data = self._get_cached_performance(cache_key)
        if cached_data:
            _logger.info(f'Performance cache HIT for agent {agent_id}')
            return cached_data
        
        # Calculate performance metrics
        metrics = self._calculate_performance_metrics(agent, date_from, date_to)
        
        # Build response
        performance_data = {
            'agent_id': agent.id,
            'agent_name': agent.name,
            'company_id': agent.company_id.id,
            'company_name': agent.company_id.name,
            'period': {
                'date_from': str(date_from) if date_from else None,
                'date_to': str(date_to) if date_to else None,
            },
            'metrics': metrics['aggregated'],
            'transactions': metrics['transactions'],
        }
        
        # Cache the result
        self._cache_performance(cache_key, performance_data)
        
        _logger.info(f'Calculated performance for agent {agent.name}: {metrics["aggregated"]["total_sales_count"]} sales, R$ {metrics["aggregated"]["total_commissions"]:,.2f} total')
        
        return performance_data
    
    def get_top_agents_ranking(self, company_id, metric='total_commissions', limit=10, date_from=None, date_to=None):

        # Validate metric
        valid_metrics = ['total_commissions', 'total_sales', 'average_commission']
        if metric not in valid_metrics:
            raise ValidationError(f'Invalid metric: {metric}. Must be one of: {", ".join(valid_metrics)}')
        
        # Validate company exists
        company = self.env['thedevkitchen.estate.company'].sudo().browse(company_id)
        if not company.exists():
            raise UserError(f'Company {company_id} not found')
        
        # Company isolation check
        user = self.env.user
        if hasattr(user, 'estate_company_ids'):
            if company_id not in user.estate_company_ids.ids:
                raise UserError('Access denied: Cannot view rankings for different company')
        
        # Get all active agents for this company
        agents = self.env['real.estate.agent'].sudo().search([
            ('company_id', '=', company_id),
            ('active', '=', True),
        ])
        
        # Calculate performance for each agent
        agent_performances = []
        for agent in agents:
            metrics = self._calculate_performance_metrics(agent, date_from, date_to)
            
            agent_performances.append({
                'agent_id': agent.id,
                'agent_name': agent.name,
                'total_sales_count': metrics['aggregated']['total_sales_count'],
                'total_commissions': metrics['aggregated']['total_commissions'],
                'average_commission': metrics['aggregated']['average_commission'],
                'active_properties_count': metrics['aggregated']['active_properties_count'],
            })
        
        # Sort by selected metric (descending)
        if metric == 'total_commissions':
            agent_performances.sort(key=lambda x: x['total_commissions'], reverse=True)
        elif metric == 'total_sales':
            agent_performances.sort(key=lambda x: x['total_sales_count'], reverse=True)
        elif metric == 'average_commission':
            agent_performances.sort(key=lambda x: x['average_commission'], reverse=True)
        
        # Apply limit and add ranking
        top_agents = agent_performances[:limit]
        for idx, agent_data in enumerate(top_agents, start=1):
            agent_data['rank'] = idx
        
        _logger.info(f'Generated ranking for company {company.name}: top {len(top_agents)} agents by {metric}')
        
        return {
            'company_id': company.id,
            'company_name': company.name,
            'metric': metric,
            'period': {
                'date_from': str(date_from) if date_from else None,
                'date_to': str(date_to) if date_to else None,
            },
            'ranking': top_agents,
        }
    
    def _calculate_performance_metrics(self, agent, date_from=None, date_to=None):

        # Build search domain for transactions
        domain = [('agent_id', '=', agent.id)]
        
        # Apply date filtering
        if date_from:
            domain.append(('transaction_date', '>=', date_from))
        if date_to:
            domain.append(('transaction_date', '<=', date_to))
        
        # Search transactions
        transactions = self.env['real.estate.commission.transaction'].sudo().search(domain, order='transaction_date desc')
        
        # Calculate aggregated metrics
        total_sales_count = len(transactions.filtered(lambda t: t.transaction_type == 'sale'))
        total_commissions = sum(transactions.mapped('commission_amount'))
        average_commission = total_commissions / total_sales_count if total_sales_count > 0 else 0.0
        
        # Calculate by payment status
        pending_commissions = sum(transactions.filtered(lambda t: t.payment_status == 'pending').mapped('commission_amount'))
        paid_commissions = sum(transactions.filtered(lambda t: t.payment_status == 'paid').mapped('commission_amount'))
        cancelled_commissions = sum(transactions.filtered(lambda t: t.payment_status == 'cancelled').mapped('commission_amount'))
        
        # Active properties count (not filtered by date)
        active_properties_count = len(agent.assignment_ids.filtered('active'))
        
        # Serialize transactions for response
        transactions_data = []
        for transaction in transactions:
            transactions_data.append({
                'id': transaction.id,
                'date': str(transaction.transaction_date),
                'amount': transaction.transaction_amount,
                'commission': transaction.commission_amount,
                'status': transaction.payment_status,
                'reference': transaction.transaction_reference or '',
                'type': transaction.transaction_type,
            })
        
        return {
            'aggregated': {
                'total_sales_count': total_sales_count,
                'total_commissions': total_commissions,
                'average_commission': average_commission,
                'active_properties_count': active_properties_count,
                'pending_commissions': pending_commissions,
                'paid_commissions': paid_commissions,
                'cancelled_commissions': cancelled_commissions,
            },
            'transactions': transactions_data,
        }
    
    def _get_cached_performance(self, cache_key):

        try:
            # Try to get from Redis (configured in odoo.conf with db_index=1)
            # Note: Redis integration requires odoo-redis module or custom implementation
            # For now, return None (cache disabled until Redis integration is complete)
            return None
        except Exception as e:
            _logger.warning(f'Redis cache read error for key {cache_key}: {e}')
            return None
    
    def _cache_performance(self, cache_key, performance_data):

        try:
            # Store in Redis with TTL=300s (5 minutes)
            # Implementation pending Redis integration
            _logger.debug(f'Performance data cached (stub): {cache_key}')
        except Exception as e:
            _logger.warning(f'Redis cache write error for key {cache_key}: {e}')
    
    def invalidate_cache(self, agent_id):

        try:
            # Delete all cache keys matching pattern "performance:agent:{agent_id}:*"
            # Implementation pending Redis integration
            _logger.info(f'Performance cache invalidated for agent {agent_id} (stub)')
        except Exception as e:
            _logger.warning(f'Redis cache invalidation error for agent {agent_id}: {e}')
