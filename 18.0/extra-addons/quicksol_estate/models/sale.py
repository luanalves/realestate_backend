from odoo import models, fields

class Sale(models.Model):
    _name = 'real.estate.sale'
    _description = 'Sale'

    property_id = fields.Many2one('real.estate.property', string='Property', required=True)
    buyer_name = fields.Char(string='Buyer Name', required=True)
    company_ids = fields.Many2many('thedevkitchen.estate.company', 'thedevkitchen_company_sale_rel', 'sale_id', 'company_id', string='Real Estate Companies')
    sale_date = fields.Date(string='Sale Date', required=True)
    sale_price = fields.Float(string='Sale Price', required=True)
