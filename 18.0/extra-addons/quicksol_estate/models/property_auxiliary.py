# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PropertyKey(models.Model):
    _name = 'real.estate.property.key'
    _description = 'Property Key Control'
    _rec_name = 'key_code'

    key_code = fields.Char(string='Key Code', required=True)
    key_type = fields.Selection([
        ('original', 'Original'),
        ('copy', 'Copy'),
        ('master', 'Master'),
        ('gate', 'Gate/Entrance'),
        ('mailbox', 'Mailbox'),
        ('other', 'Other'),
    ], string='Key Type', required=True, default='original')
    quantity = fields.Integer(string='Quantity', default=1)
    location = fields.Char(string='Current Location')
    status = fields.Selection([
        ('available', 'Available'),
        ('checked_out', 'Checked Out'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged'),
    ], string='Status', default='available')
    notes = fields.Text(string='Notes')
    property_id = fields.Many2one('real.estate.property', string='Property', ondelete='cascade', required=True)
    checked_out_by = fields.Many2one('res.users', string='Checked Out By')
    checked_out_date = fields.Datetime(string='Checked Out Date')
    expected_return_date = fields.Date(string='Expected Return Date')
    active = fields.Boolean(default=True)

    @api.constrains('quantity')
    def _check_quantity(self):
        for key in self:
            if key.quantity < 0:
                raise ValidationError('Quantity cannot be negative.')


class PropertyCommission(models.Model):
    _name = 'real.estate.property.commission'
    _description = 'Property Commission'

    name = fields.Char(string='Description', required=True)
    commission_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], string='Commission Type', required=True, default='percentage')
    value = fields.Float(string='Value', required=True)
    applies_to = fields.Selection([
        ('sale', 'Sale'),
        ('rent', 'Rent'),
        ('both', 'Both'),
    ], string='Applies To', required=True, default='sale')
    agent_id = fields.Many2one('real.estate.agent', string='Agent')
    property_id = fields.Many2one('real.estate.property', string='Property', ondelete='cascade', required=True)
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    
    # Computed fields
    commission_amount = fields.Monetary(string='Commission Amount', compute='_compute_commission_amount', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='property_id.currency_id',
        store=True,
    )

    @api.depends('value', 'commission_type', 'property_id.price', 'property_id.rent_price')
    def _compute_commission_amount(self):
        for commission in self:
            if commission.commission_type == 'fixed':
                commission.commission_amount = commission.value
            elif commission.commission_type == 'percentage':
                if commission.applies_to == 'sale':
                    commission.commission_amount = (commission.property_id.price or 0) * commission.value / 100
                elif commission.applies_to == 'rent':
                    commission.commission_amount = (commission.property_id.rent_price or 0) * commission.value / 100
                else:
                    commission.commission_amount = 0
            else:
                commission.commission_amount = 0

    @api.constrains('value')
    def _check_value(self):
        for commission in self:
            if commission.commission_type == 'percentage' and (commission.value < 0 or commission.value > 100):
                raise ValidationError('Percentage must be between 0 and 100.')
            if commission.value < 0:
                raise ValidationError('Commission value cannot be negative.')
