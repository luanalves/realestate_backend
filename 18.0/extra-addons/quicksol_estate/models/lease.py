from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class Lease(models.Model):
    _name = 'real.estate.lease'
    _description = 'Lease Agreement'
    _rec_name = 'name'
    _order = 'start_date desc'

    name = fields.Char(string='Lease Reference', compute='_compute_name', store=True)
    property_id = fields.Many2one('real.estate.property', string='Property', required=True)
    profile_id = fields.Many2one('thedevkitchen.estate.profile', string='Profile', required=True, ondelete='restrict')
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

    @api.depends('property_id', 'profile_id', 'start_date')
    def _compute_name(self):
        for record in self:
            if record.property_id and record.profile_id and record.start_date:
                record.name = f"{record.property_id.name} - {record.profile_id.name} ({record.start_date})"
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

    # ===== Lease Status Transitions (CHK024) =====

    VALID_TRANSITIONS = {
        'draft': ['active'],
        'active': ['terminated'],  # expired handled by cron only
        'terminated': [],
        'expired': [],
    }

    def write(self, vals):
        """Override write to enforce valid status transitions (CHK024).

        Context flags that bypass validation:
          - cron_expire: used by _cron_expire_leases (active→expired)
          - lease_terminate: used by terminate endpoint (active→terminated)
        """
        if 'status' in vals and not self.env.context.get('cron_expire'):
            new_status = vals['status']
            for record in self:
                old_status = record.status
                if old_status != new_status:
                    # terminate endpoint uses context flag
                    if self.env.context.get('lease_terminate') and new_status == 'terminated':
                        continue
                    allowed = self.VALID_TRANSITIONS.get(old_status, [])
                    if new_status not in allowed:
                        raise ValidationError(
                            f"Invalid status transition: {old_status} → {new_status}. "
                            f"Allowed: {', '.join(allowed) if allowed else 'none (terminal state)'}."
                        )
        return super().write(vals)

    # ===== Cron: Auto-expire leases (CHK002) =====

    @api.model
    def _cron_expire_leases(self):
        """Transition active leases past end_date to 'expired' status.

        Called by ir.cron scheduled action (data/lease_cron.xml).
        Bypasses write() transition validation via context flag.
        """
        today = fields.Date.today()
        expired_leases = self.search([
            ('status', '=', 'active'),
            ('end_date', '<', today),
        ])
        if expired_leases:
            # Use context flag to bypass transition validation (cron-only path)
            expired_leases.with_context(cron_expire=True).sudo().write({
                'status': 'expired',
            })
            _logger.info(
                "Cron: expired %d lease(s): %s",
                len(expired_leases),
                expired_leases.ids,
            )
