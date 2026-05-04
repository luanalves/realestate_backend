# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ServiceReassignWizard(models.TransientModel):
    _name = 'service.reassign.wizard'
    _description = 'Service Reassign Wizard'

    service_id = fields.Many2one(
        'real.estate.service',
        string='Service',
        required=True,
        readonly=True,
    )
    current_agent_id = fields.Many2one(
        'real.estate.agent',
        string='Current Agent',
        related='service_id.agent_id',
        readonly=True,
    )
    new_agent_id = fields.Many2one(
        'real.estate.agent',
        string='New Agent',
        required=True,
        domain="[('company_id', '=', company_id)]",
    )
    reason = fields.Char(
        string='Reason',
        required=True,
        placeholder='Ex: Agente indisponível, reatribuição por carga de trabalho...',
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        readonly=True,
    )

    @api.constrains('new_agent_id')
    def _check_new_agent_different(self):
        for rec in self:
            if rec.new_agent_id == rec.current_agent_id:
                raise ValidationError(_(
                    'New agent must be different from the current agent.'
                ))

    def action_confirm_reassign(self):
        self.ensure_one()
        from odoo.addons.quicksol_estate.services.service_pipeline_service import (
            reassign as pipeline_reassign
        )
        pipeline_reassign(
            service=self.service_id,
            new_agent_id=self.new_agent_id.id,
            reason=self.reason,
        )
        return {'type': 'ir.actions.act_window_close'}
