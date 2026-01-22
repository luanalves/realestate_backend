"""
EventBus - Central event dispatcher for Observer Pattern.

ADR-020: Observer Pattern for Odoo Event-Driven Architecture
ADR-021: Async Messaging with RabbitMQ + Celery

Provides hybrid sync/async event emission for decoupled business logic.
"""
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class EventBus(models.AbstractModel):
    _name = 'quicksol.event.bus'
    _description = 'Event Bus - Central event dispatcher'
    
    ASYNC_EVENTS = {
        'user.created': 'audit_events',
        'property.created': 'audit_events',
        'commission.split.calculated': 'commission_events',
        'property.assignment.changed': 'notification_events',
    }
    
    @api.model
    def emit(self, event_name, data, force_sync=False):
        """
        Emit an event to all registered observers.
        
        Routing logic:
        - Events starting with 'before_' are ALWAYS synchronous (validations)
        - Events in ASYNC_EVENTS dict are async by default (unless force_sync=True)
        - All other events are synchronous
        
        Args:
            event_name (str): Event identifier (e.g., 'property.before_create', 'user.created')
            data (dict): Event payload with context
            force_sync (bool): Force synchronous processing even for async events
        
        Returns:
            str|None: task_id if async, None if sync
        
        Examples:
            # Sync validation (always blocks)
            self.env['quicksol.event.bus'].emit('user.before_create', {'vals': vals})
            
            # Async audit log (non-blocking)
            task_id = self.env['quicksol.event.bus'].emit('user.created', {'user_id': user.id})
            
            # Force sync for testing
            self.env['quicksol.event.bus'].emit('property.created', data, force_sync=True)
        """
        if event_name.startswith('before_'):
            return self._emit_sync(event_name, data)
        
        if event_name in self.ASYNC_EVENTS and not force_sync:
            return self._emit_async(event_name, data)
        
        return self._emit_sync(event_name, data)
    
    @api.model
    def _emit_sync(self, event_name, data):
        """
        Emit event synchronously to all registered observers.
        
        Args:
            event_name (str): Event identifier
            data (dict): Event payload
        
        Returns:
            None
        """
        _logger.debug(f"EventBus: Emitting sync event '{event_name}' with data: {data}")
        
        # Find all concrete models that inherit from AbstractObserver
        observer_models = []
        for model_name in self.env.registry.models.keys():
            try:
                model = self.env[model_name]
                # Check if model inherits from AbstractObserver
                if hasattr(model, '_inherit') and 'quicksol.abstract.observer' in (model._inherit if isinstance(model._inherit, list) else [model._inherit]):
                    observer_models.append(model_name)
                elif model._name == 'quicksol.abstract.observer':
                    # Skip the abstract model itself
                    continue
                elif hasattr(model, 'can_handle') and hasattr(model, 'handle'):
                    # Model has observer interface methods
                    # Check if it's a concrete observer (has database table)
                    if not model._abstract and model._table:
                        observer_models.append(model_name)
            except Exception:
                # Skip models that cannot be accessed
                continue
        
        # Emit event to each registered observer
        for observer_model_name in observer_models:
            try:
                observer = self.env[observer_model_name]
                if observer.can_handle(event_name):
                    observer.handle(event_name, data)
                    _logger.debug(f"Observer {observer_model_name} handled event '{event_name}'")
            except Exception as exc:
                _logger.error(f"Observer {observer_model_name} failed to handle '{event_name}': {exc}", exc_info=True)
                if event_name.startswith('before_'):
                    raise
        
        return None
    
    @api.model
    def _emit_async(self, event_name, data):
        """
        Emit event asynchronously via RabbitMQ + Celery.
        
        Args:
            event_name (str): Event identifier
            data (dict): Event payload
        
        Returns:
            str: Celery task_id for status polling
        """
        try:
            queue_name = self.ASYNC_EVENTS[event_name]
            _logger.info(f"EventBus: Emitting async event '{event_name}' to queue '{queue_name}'")
            
            # PLACEHOLDER: Integrate with Celery client
            # from odoo.addons.thedevkitchen_celery.celery_client import process_event_task
            # task = process_event_task.apply_async(
            #     args=[event_name, data],
            #     queue=queue_name,
            #     priority=self._get_priority(event_name),
            #     retry=True,
            #     retry_policy={'max_retries': 3}
            # )
            # return task.id
            
            _logger.warning(f"Async messaging not fully integrated yet, falling back to sync for '{event_name}'")
            return self._emit_sync(event_name, data)
        
        except Exception as exc:
            _logger.error(f"Failed to emit async event '{event_name}', falling back to sync: {exc}", exc_info=True)
            return self._emit_sync(event_name, data)
    
    @api.model
    def _get_priority(self, event_name):
        """
        Get priority level for async event (used by Celery).
        
        Args:
            event_name (str): Event identifier
        
        Returns:
            int: Priority (0=lowest, 9=highest)
        """
        priority_map = {
            'commission.split.calculated': 9,
            'property.assignment.changed': 5,
            'user.created': 5,
            'property.created': 5,
        }
        return priority_map.get(event_name, 5)
