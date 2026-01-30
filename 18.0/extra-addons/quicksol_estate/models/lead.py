# -*- coding: utf-8 -*-
"""
Real Estate Lead Model

Manages real estate leads through the sales pipeline with agent isolation,
multi-tenant support, and activity tracking.

Author: Quicksol Technologies  
Date: 2026-01-29
Branch: 006-lead-management
ADRs: ADR-001 (Module Structure), ADR-004 (Naming), ADR-015 (Soft-Delete)
FRs: FR-001 to FR-047 (see specs/006-lead-management/spec.md)
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class RealEstateLead(models.Model):
    _name = 'real.estate.lead'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Real Estate Lead'
    _order = 'create_date desc'
    
    # ==================== CORE IDENTITY ====================
    
    name = fields.Char(
        'Lead Title',
        required=True,
        tracking=True,
        help='Lead name/title (e.g., "João Silva - Apartamento Centro")',
        size=100
    )
    
    active = fields.Boolean(
        'Active',
        default=True,
        help='Soft delete flag. Archived leads have active=False'
    )
    
    state = fields.Selection(
        [
            ('new', 'New'),
            ('contacted', 'Contacted'),
            ('qualified', 'Qualified'),
            ('won', 'Won'),
            ('lost', 'Lost')
        ],
        string='State',
        required=True,
        default='new',
        tracking=True,
        help='Pipeline stage of the lead'
    )
    
    # ==================== CONTACT INFORMATION ====================
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        tracking=True,
        ondelete='restrict',
        help='Linked contact record (optional, can create later)'
    )
    
    phone = fields.Char(
        'Phone',
        size=20,
        tracking=True,
        help='Primary phone number'
    )
    
    email = fields.Char(
        'Email',
        size=120,
        tracking=True,
        help='Email address'
    )
    
    # ==================== OWNERSHIP & MULTI-TENANCY ====================
    
    agent_id = fields.Many2one(
        'real.estate.agent',
        string='Agent',
        required=True,
        tracking=True,
        index=True,
        ondelete='restrict',
        default=lambda self: self._default_agent_id(),
        help='Assigned sales agent (owner of lead)'
    )
    
    company_ids = fields.Many2many(
        'thedevkitchen.estate.company',
        'real_estate_lead_company_rel',
        'lead_id',
        'company_id',
        string='Companies',
        required=True,
        tracking=True,
        default=lambda self: self._default_company_ids(),
        help='Companies this lead belongs to (multi-tenancy)'
    )
    
    # ==================== PROPERTY PREFERENCES ====================
    
    budget_min = fields.Float(
        'Minimum Budget',
        digits='Product Price',
        tracking=True,
        help='Minimum budget (Brazilian Reais)'
    )
    
    budget_max = fields.Float(
        'Maximum Budget',
        digits='Product Price',
        tracking=True,
        help='Maximum budget (Brazilian Reais)'
    )
    
    property_type_interest = fields.Many2one(
        'real.estate.property.type',
        string='Property Type Interest',
        tracking=True,
        ondelete='restrict',
        help='Desired property type (apartamento, casa, etc.)'
    )
    
    location_preference = fields.Char(
        'Location Preference',
        size=200,
        tracking=True,
        help='Preferred locations (free text)'
    )
    
    bedrooms_needed = fields.Integer(
        'Bedrooms Needed',
        tracking=True,
        help='Desired number of bedrooms'
    )
    
    min_area = fields.Float(
        'Minimum Area (m²)',
        digits=(10, 2),
        tracking=True,
        help='Minimum area in m²'
    )
    
    max_area = fields.Float(
        'Maximum Area (m²)',
        digits=(10, 2),
        tracking=True,
        help='Maximum area in m²'
    )
    
    property_interest = fields.Many2one(
        'real.estate.property',
        string='Property of Interest',
        tracking=True,
        ondelete='restrict',
        help='Specific property of interest (optional)'
    )
    
    # ==================== LIFECYCLE TRACKING ====================
    
    first_contact_date = fields.Date(
        'First Contact Date',
        tracking=True,
        help='Date of first contact with client'
    )
    
    expected_closing_date = fields.Date(
        'Expected Closing Date',
        tracking=True,
        help='Expected deal closing date (for forecasting)'
    )
    
    lost_date = fields.Date(
        'Lost Date',
        tracking=True,
        help='Date lead was marked as lost'
    )
    
    lost_reason = fields.Text(
        'Lost Reason',
        tracking=True,
        help='Reason why lead was lost'
    )
    
    # ==================== CONVERSION ====================
    
    converted_property_id = fields.Many2one(
        'real.estate.property',
        string='Converted Property',
        tracking=True,
        ondelete='restrict',
        help='Property linked when converted to sale'
    )
    
    converted_sale_id = fields.Many2one(
        'real.estate.sale',
        string='Converted Sale',
        tracking=True,
        ondelete='restrict',
        help='Sale record created from conversion'
    )
    
    # ==================== COMPUTED FIELDS ====================
    
    display_name = fields.Char(
        'Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    days_in_state = fields.Integer(
        'Days in Current State',
        compute='_compute_days_in_state',
        help='Days since last state change'
    )
    
    # ==================== DEFAULT VALUES ====================
    
    @api.model
    def _default_agent_id(self):
        """Auto-assign current user's agent record (FR-002)"""
        agent = self.env['real.estate.agent'].search([
            ('user_id', '=', self.env.uid)
        ], limit=1)
        return agent.id if agent else False
    
    @api.model
    def _default_company_ids(self):
        """Auto-assign user's companies (FR-031)"""
        return self.env.user.estate_company_ids.ids
    
    # ==================== COMPUTED METHODS ====================
    
    @api.depends('name', 'partner_id')
    def _compute_display_name(self):
        """Display name with partner info"""
        for record in self:
            if record.partner_id:
                record.display_name = f"{record.name} ({record.partner_id.name})"
            else:
                record.display_name = record.name
    
    @api.depends('create_date', 'write_date')
    def _compute_days_in_state(self):
        """Days in current state (for pipeline metrics)"""
        for record in self:
            if record.write_date:
                delta = fields.Datetime.now() - record.write_date
                record.days_in_state = delta.days
            else:
                delta = fields.Datetime.now() - record.create_date
                record.days_in_state = delta.days
    
    # ==================== VALIDATION CONSTRAINTS ====================
    
    @api.constrains('agent_id', 'phone', 'email')
    def _check_duplicate_per_agent(self):
        """Per-Agent Duplicate Prevention (FR-005a)"""
        for record in self:
            if not record.agent_id:
                continue
            
            # Check phone duplicate
            if record.phone:
                domain = [
                    ('agent_id', '=', record.agent_id.id),
                    ('phone', '=ilike', record.phone.strip()),
                    ('state', 'not in', ['lost', 'won']),
                    ('id', '!=', record.id),
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(
                        f"You already have an active lead with phone {record.phone}. "
                        f"Please edit the existing lead or add a new activity."
                    )
            
            # Check email duplicate
            if record.email:
                domain = [
                    ('agent_id', '=', record.agent_id.id),
                    ('email', '=ilike', record.email.strip().lower()),
                    ('state', 'not in', ['lost', 'won']),
                    ('id', '!=', record.id),
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(
                        f"You already have an active lead with email {record.email}. "
                        f"Please edit the existing lead or add a new activity."
                    )
    
    @api.constrains('budget_min', 'budget_max')
    def _check_budget_range(self):
        """Budget Validation (FR-006)"""
        for record in self:
            if record.budget_min and record.budget_max:
                if record.budget_min > record.budget_max:
                    raise ValidationError("Minimum budget cannot exceed maximum budget.")
    
    @api.constrains('agent_id', 'company_ids')
    def _check_agent_company(self):
        """Company Validation (FR-023)"""
        for record in self:
            if record.agent_id and record.company_ids:
                agent_companies = record.agent_id.company_ids
                lead_companies = record.company_ids
                if not (lead_companies & agent_companies):
                    raise ValidationError(
                        "Agent must belong to at least one of the lead's companies."
                    )
    
    @api.constrains('state', 'lost_reason')
    def _check_lost_reason(self):
        """Lost Reason Required (FR-017)"""
        for record in self:
            if record.state == 'lost' and not record.lost_reason:
                raise ValidationError("Lost reason is required when marking lead as lost.")
    
    # ==================== CUSTOM METHODS ====================
    
    def unlink(self):
        """Prevent hard delete - archive instead (FR-018b)"""
        self.write({'active': False})
        return True
    
    def write(self, vals):
        """Override write to log state changes (FR-015)"""
        if 'state' in vals:
            for record in self:
                old_state = record.state
                new_state = vals['state']
                
                # Auto-set lost_date
                if new_state == 'lost' and 'lost_date' not in vals:
                    vals['lost_date'] = fields.Date.today()
                
                # Log state change in chatter
                res = super(RealEstateLead, record).write(vals)
                if old_state != new_state:
                    record.message_post(
                        body=f"State changed from {old_state} to {new_state}",
                        subtype_xmlid='mail.mt_note',
                    )
                return res
        
        return super().write(vals)
    
    def action_reopen(self):
        """Reopen lost lead (FR-018a)"""
        for record in self:
            if record.state != 'lost':
                raise UserError(_("Only lost leads can be reopened."))
            
            record.write({'state': 'contacted'})
            record.message_post(
                body=_("Lead reopened and set to Contacted state."),
                subtype_xmlid='mail.mt_note',
            )
        
        return True
    
    def action_convert_to_sale(self, property_id):
        """Convert lead to sale (FR-010, FR-011, FR-012, FR-013, FR-014)"""
        self.ensure_one()
        
        # Validate property exists and agent has access (FR-014a)
        property_obj = self.env['real.estate.property'].browse(property_id)
        if not property_obj.exists():
            raise ValidationError(_("Selected property does not exist."))
        
        # Check agent has access to property (via company)
        if not (property_obj.company_id in self.company_ids):
            raise ValidationError(_("Agent does not have access to the selected property."))
        
        # Atomic transaction: create sale and update lead
        try:
            # Create sale record (FR-010, FR-013)
            sale_vals = {
                'property_id': property_id,
                'lead_id': self.id,
                'agent_id': self.agent_id.id,
                'company_id': self.company_ids[0].id if self.company_ids else False,
            }
            
            # Copy contact info if partner exists
            if self.partner_id:
                sale_vals['buyer_name'] = self.partner_id.name
                sale_vals['buyer_phone'] = self.phone or self.partner_id.phone
                sale_vals['buyer_email'] = self.email or self.partner_id.email
            elif self.phone or self.email:
                sale_vals['buyer_name'] = self.name
                sale_vals['buyer_phone'] = self.phone
                sale_vals['buyer_email'] = self.email
            
            sale = self.env['real.estate.sale'].create(sale_vals)
            
            # Update lead with conversion info (FR-011, FR-012)
            self.write({
                'state': 'won',
                'converted_property_id': property_id,
                'converted_sale_id': sale.id,
            })
            
            # Log conversion in chatter (FR-015)
            self.message_post(
                body=_(f"Lead converted to sale. Property: {property_obj.name}, Sale ID: {sale.id}"),
                subtype_xmlid='mail.mt_note',
            )
            
            return sale.id
            
        except Exception as e:
            # Transaction rollback happens automatically (FR-014)
            raise ValidationError(_(f"Lead conversion failed: {str(e)}"))
