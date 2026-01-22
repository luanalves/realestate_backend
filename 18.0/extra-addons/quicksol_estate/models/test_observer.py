# -*- coding: utf-8 -*-
"""
Test Observer for unit tests.

This concrete observer implementation is used by test_abstract_observer.py
to test the AbstractObserver base class without dynamic model registration issues.
"""
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
