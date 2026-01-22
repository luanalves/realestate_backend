"""
AbstractObserver - Base class for event observers.

ADR-020: Observer Pattern for Odoo Event-Driven Architecture

All concrete observers must inherit from this base class and implement
the can_handle() and handle() methods.
"""
import logging
from odoo import api, models, fields

_logger = logging.getLogger(__name__)


class AbstractObserver(models.AbstractModel):
    _name = 'quicksol.abstract.observer'
    _description = 'Abstract Observer - Base class for event handlers'
    
    name = fields.Char(string='Observer Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    
    @api.model
    def can_handle(self, event_name):
        """
        Determine if this observer should handle the given event.
        
        Args:
            event_name (str): Event identifier (e.g., 'property.before_create')
        
        Returns:
            bool: True if this observer handles the event
        
        Must be overridden by concrete observers.
        """
        raise NotImplementedError("Subclasses must implement can_handle()")
    
    @api.model
    def handle(self, event_name, data):
        """
        Process the event with provided data.
        
        Args:
            event_name (str): Event identifier
            data (dict): Event payload with context
        
        Returns:
            dict|None: Processing result or None
        
        Must be overridden by concrete observers.
        """
        raise NotImplementedError("Subclasses must implement handle()")
    
    @api.model
    def _validate_data(self, data, required_keys):
        """
        Validate event payload contains required keys.
        
        Args:
            data (dict): Event payload
            required_keys (list): List of required keys
        
        Raises:
            ValueError: If required keys are missing
        """
        missing = [k for k in required_keys if k not in data]
        if missing:
            raise ValueError(f"Missing required keys in event data: {missing}")
