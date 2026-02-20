# -*- coding: utf-8 -*-

from odoo import models, api


class TestConcreteObserver(models.AbstractModel):
    _name = 'test.concrete.observer'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Test Observer for Unit Tests'
    
    @api.model
    def can_handle(self, event_name):
        """Return True for test events."""
        return event_name in ['test.event', 'test.another.event']
    
    @api.model
    def handle(self, event_name, data):
        """Handle test events and return status."""
        return {'status': 'handled', 'event': event_name, 'data': data}
