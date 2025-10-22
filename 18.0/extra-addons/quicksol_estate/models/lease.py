from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Lease(models.Model):
    _name = 'real.estate.lease'
    _description = 'Lease Agreement'
    _rec_name = 'name'
    _order = 'start_date desc'

    name = fields.Char(string='Lease Reference', compute='_compute_name', store=True)
    property_id = fields.Many2one('real.estate.property', string='Property', required=True)
    tenant_id = fields.Many2one('real.estate.tenant', string='Tenant', required=True)
    company_ids = fields.Many2many('thedevkitchen.estate.company', 'thedevkitchen_company_lease_rel', 'lease_id', 'company_id', string='Real Estate Companies')
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    rent_amount = fields.Float(string='Rent', required=True)

    @api.depends('property_id', 'tenant_id', 'start_date')
    def _compute_name(self):
        for record in self:
            if record.property_id and record.tenant_id and record.start_date:
                record.name = f"{record.property_id.name} - {record.tenant_id.name} ({record.start_date})"
            else:
                record.name = "New Lease"

    @api.constrains('start_date', 'end_date')
    def _validate_lease_dates(self):
        """Validate that end date is after start date"""
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date <= record.start_date:
                    raise ValidationError("End date must be after start date.")
