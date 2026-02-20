
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

        raise NotImplementedError("Subclasses must implement can_handle()")
    
    @api.model
    def handle(self, event_name, data):

        raise NotImplementedError("Subclasses must implement handle()")
    
    @api.model
    def _validate_data(self, data, required_keys):

        missing = [k for k in required_keys if k not in data]
        if missing:
            raise ValueError(f"Missing required keys in event data: {missing}")
