# -*- coding: utf-8 -*-

from odoo import models, fields


class LeaseRenewalHistory(models.Model):
    _name = 'real.estate.lease.renewal.history'
    _description = 'Lease Renewal History'
    _order = 'renewal_date desc'

    lease_id = fields.Many2one(
        'real.estate.lease',
        string='Lease',
        required=True,
        ondelete='cascade',
        index=True,
    )
    previous_end_date = fields.Date(
        string='Previous End Date',
        required=True,
    )
    previous_rent_amount = fields.Float(
        string='Previous Rent Amount',
        required=True,
    )
    new_end_date = fields.Date(
        string='New End Date',
        required=True,
    )
    new_rent_amount = fields.Float(
        string='New Rent Amount',
        required=True,
    )
    renewed_by_id = fields.Many2one(
        'res.users',
        string='Renewed By',
        required=True,
    )
    reason = fields.Text(
        string='Renewal Reason',
    )
    renewal_date = fields.Datetime(
        string='Renewal Date',
        default=fields.Datetime.now,
        required=True,
    )
