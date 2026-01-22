"""
CommissionSplitObserver - Auto-calculate commission split when sale completes

Listens to: sale.created (async)
Action: Calculate commission split between prospector and agent

This observer ensures that when a sale is created for a property with both
prospector_id and agent_id, commission transactions are automatically created
for both parties according to the configured split percentage (default 30/70).

Pattern: Observer with async event handling (sale already created)
"""
import logging
from odoo import api, models, fields

_logger = logging.getLogger(__name__)


class CommissionSplitObserver(models.AbstractModel):
    _name = 'quicksol.observer.commission.split'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Observer: Auto-calculate commission split on sale'
    
    name = fields.Char(default='Commission Split Observer', readonly=True)
    
    @api.model
    def can_handle(self, event_name):
        """Handle sale.created events."""
        return event_name == 'sale.created'
    
    @api.model
    def handle(self, event_name, data, **kwargs):
        """
        Calculate and create commission transactions for prospector and agent.
        
        Args:
            event_name: 'sale.created'
            data: Sale record (real.estate.sale)
            force_sync: False (async processing)
        
        Business Logic (FR-054 to FR-060):
            1. Verify sale has property with both prospector_id and agent_id
            2. If prospector_id == agent_id → skip (no split)
            3. Find applicable commission rule for selling agent
            4. Calculate commission split using calculate_split_commission()
            5. Create 2 commission transactions:
                - Prospector: prospector_commission amount
                - Agent: agent_commission amount
            6. Update property state if needed
        
        Commission Split Example:
            Sale price: R$ 500,000
            Agent commission rule: 6% = R$ 30,000
            Split: 30% prospector / 70% agent
            → Prospector transaction: R$ 9,000
            → Agent transaction: R$ 21,000
        
        Error Handling:
            - If no commission rule found → log warning, skip
            - If commission calculation fails → log error, skip
            - Transactions are atomic (both created or neither)
        """
        if event_name != 'sale.created':
            return
        
        # Extract sale from dict payload
        if not data or not isinstance(data, dict):
            _logger.warning('CommissionSplitObserver: Invalid sale data received (expected dict)')
            return
        
        sale = data.get('sale')
        if not sale:
            _logger.warning('CommissionSplitObserver: No sale object in event data')
            return
        
        env = sale.env
        
        # Verify sale has property
        if not sale.property_id:
            _logger.warning(
                'Sale ID %d has no associated property. Commission split skipped.',
                sale.id
            )
            return
        
        property_obj = sale.property_id
        
        # Check if split applies (must have both prospector and agent, and they must differ)
        if not property_obj.prospector_id or not property_obj.agent_id:
            _logger.debug(
                'Sale ID %d: Property has no prospector_id or agent_id. Commission split skipped.',
                sale.id
            )
            return
        
        if property_obj.prospector_id == property_obj.agent_id:
            _logger.debug(
                'Sale ID %d: Prospector and agent are the same. No commission split.',
                sale.id
            )
            return
        
        # Find applicable commission rule for agent
        CommissionRule = env['real.estate.commission.rule']
        commission_rule = CommissionRule.search([
            ('agent_id', '=', property_obj.agent_id.id),
            ('transaction_type', 'in', ['sale', 'both']),
            ('valid_from', '<=', sale.sale_date),
            '|',
            ('valid_until', '=', False),
            ('valid_until', '>=', sale.sale_date),
            ('min_value', '<=', sale.sale_price),
            ('max_value', '>=', sale.sale_price),
        ], limit=1, order='valid_from desc')
        
        if not commission_rule:
            _logger.warning(
                'Sale ID %d: No applicable commission rule found for agent %s. '
                'Commission split cannot be calculated.',
                sale.id,
                property_obj.agent_id.name
            )
            return
        
        # Calculate commission split
        try:
            split_result = commission_rule.calculate_split_commission(
                property_obj,
                sale.sale_price,
                transaction_type='sale'
            )
        except Exception as e:
            _logger.error(
                'Sale ID %d: Error calculating commission split: %s',
                sale.id,
                str(e)
            )
            return
        
        # Create commission transactions
        CommissionTransaction = env['real.estate.commission_transaction']
        
        # Transaction for Prospector
        prospector_transaction = CommissionTransaction.create({
            'agent_id': property_obj.prospector_id.id,
            'property_id': property_obj.id,
            'amount': split_result['prospector_commission'],
            'transaction_type': 'sale',
            'transaction_date': sale.sale_date,
            'company_id': property_obj.company_ids[0].id if property_obj.company_ids else False,
            'notes': f'Prospector commission split ({split_result["split_percentage"] * 100:.0f}%) - Sale ID: {sale.id}',
        })
        
        # Transaction for Agent
        agent_transaction = CommissionTransaction.create({
            'agent_id': property_obj.agent_id.id,
            'property_id': property_obj.id,
            'amount': split_result['agent_commission'],
            'transaction_type': 'sale',
            'transaction_date': sale.sale_date,
            'company_id': property_obj.company_ids[0].id if property_obj.company_ids else False,
            'notes': f'Agent commission split ({(1 - split_result["split_percentage"]) * 100:.0f}%) - Sale ID: {sale.id}',
        })
        
        _logger.info(
            'Commission split created for Sale ID %d: '
            'Prospector %s (R$ %.2f), Agent %s (R$ %.2f)',
            sale.id,
            property_obj.prospector_id.name,
            split_result['prospector_commission'],
            property_obj.agent_id.name,
            split_result['agent_commission']
        )
