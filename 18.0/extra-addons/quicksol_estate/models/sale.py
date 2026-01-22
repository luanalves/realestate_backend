from odoo import models, fields, api

class Sale(models.Model):
    _name = 'real.estate.sale'
    _description = 'Sale'

    property_id = fields.Many2one('real.estate.property', string='Property', required=True)
    buyer_name = fields.Char(string='Buyer Name', required=True)
    buyer_partner_id = fields.Many2one('res.partner', string='Buyer Contact', help='Partner record for buyer (enables Portal access)')
    company_ids = fields.Many2many('thedevkitchen.estate.company', 'thedevkitchen_company_sale_rel', 'sale_id', 'company_id', string='Real Estate Companies')
    sale_date = fields.Date(string='Sale Date', required=True)
    sale_price = fields.Float(string='Sale Price', required=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        sales = super().create(vals_list)
        
        # Emit sale.created event for each sale (triggers commission split)
        event_bus = self.env['quicksol.event.bus']
        for sale in sales:
            event_bus.emit('sale.created', {'sale_id': sale.id, 'sale': sale})
        
        return sales
