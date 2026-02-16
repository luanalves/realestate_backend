from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Sale(models.Model):
    _name = 'real.estate.sale'
    _description = 'Sale'

    property_id = fields.Many2one('real.estate.property', string='Property', required=True)
    buyer_name = fields.Char(string='Buyer Name', required=True)
    buyer_partner_id = fields.Many2one('res.partner', string='Buyer Contact', help='Partner record for buyer (enables Portal access)')
    buyer_phone = fields.Char('Buyer Phone', size=20, help='Buyer contact phone')
    buyer_email = fields.Char('Buyer Email', size=120, help='Buyer contact email')
    company_ids = fields.Many2many('thedevkitchen.estate.company', 'thedevkitchen_company_sale_rel', 'sale_id', 'company_id', string='Real Estate Companies')
    company_id = fields.Many2one('thedevkitchen.estate.company', string='Primary Company', help='Primary company for sale')
    agent_id = fields.Many2one('real.estate.agent', string='Agent', help='Agent who closed the sale')
    lead_id = fields.Many2one('real.estate.lead', string='Source Lead', help='Lead that was converted to this sale')
    sale_date = fields.Date(string='Sale Date', required=True)
    sale_price = fields.Float(string='Sale Price', required=True)

    # Feature 008: Lifecycle & soft-delete fields
    active = fields.Boolean(string='Active', default=True)
    status = fields.Selection([
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='completed', required=True)
    cancellation_date = fields.Date(string='Cancellation Date')
    cancellation_reason = fields.Text(string='Cancellation Reason')

    @api.constrains('sale_price')
    def _validate_sale_price(self):
        """Validate sale price is positive (FR-022)."""
        for record in self:
            if record.sale_price is not None and record.sale_price <= 0:
                raise ValidationError("Sale price must be greater than zero.")

    @api.model_create_multi
    def create(self, vals_list):
        sales = super().create(vals_list)

        # Emit sale.created event for each sale (triggers commission split)
        event_bus = self.env['quicksol.event.bus']
        for sale in sales:
            event_bus.emit('sale.created', {'sale_id': sale.id, 'sale': sale})
            # Mark property as sold (FR-029)
            if sale.property_id and hasattr(sale.property_id, 'state'):
                sale.property_id.write({'state': 'sold'})

        return sales

    def action_cancel(self, reason):
        """Cancel a sale and revert property status (FR-029).

        CHK009/CHK031: Only reverts property to 'new' if it is still 'sold'.
        If property state was changed after the sale (e.g., new lease created),
        the revert is skipped to avoid data integrity issues.
        """
        self.ensure_one()
        if self.status == 'cancelled':
            raise ValidationError("Sale is already cancelled.")
        self.write({
            'status': 'cancelled',
            'cancellation_date': fields.Date.today(),
            'cancellation_reason': reason,
        })
        # Only revert property status if it's still 'sold'
        if self.property_id and hasattr(self.property_id, 'state'):
            if self.property_id.state == 'sold':
                self.property_id.write({'state': 'new'})
