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

    # Feature 008: Lifecycle & soft-delete fields
    active = fields.Boolean(string='Active', default=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('terminated', 'Terminated'),
        ('expired', 'Expired'),
    ], string='Status', default='draft', required=True)
    termination_date = fields.Date(string='Termination Date')
    termination_reason = fields.Text(string='Termination Reason')
    termination_penalty = fields.Float(string='Termination Penalty')
    renewal_history_ids = fields.One2many(
        'real.estate.lease.renewal.history', 'lease_id',
        string='Renewal History',
    )

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

    @api.constrains('rent_amount')
    def _validate_rent_amount(self):
        """Validate rent amount is positive (FR-011)."""
        for record in self:
            if record.rent_amount is not None and record.rent_amount <= 0:
                raise ValidationError("Rent amount must be greater than zero.")

    @api.constrains('property_id', 'start_date', 'end_date', 'status')
    def _check_concurrent_lease(self):
        """One active lease per property at a time (FR-013)."""
        for record in self:
            if record.status in ('draft', 'active'):
                overlapping = self.search([
                    ('id', '!=', record.id),
                    ('property_id', '=', record.property_id.id),
                    ('status', 'in', ['draft', 'active']),
                    ('start_date', '<=', record.end_date),
                    ('end_date', '>=', record.start_date),
                ])
                if overlapping:
                    raise ValidationError(
                        "Property already has an active or draft lease in this period."
                    )
