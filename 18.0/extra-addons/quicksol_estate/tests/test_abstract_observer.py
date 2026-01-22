"""
Test suite for AbstractObserver (quicksol.abstract.observer).

Tests base observer class and validation helpers.
Coverage: ADR-020, FR-042 (Observer Pattern)

NOTE: Uses real observer model (test.concrete.observer) defined in models/test_observer.py
to avoid dynamic class registration issues.
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestAbstractObserver(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Use the real test observer model defined in models/test_observer.py
        cls.observer = cls.env['test.concrete.observer']
    
    def test_can_handle_returns_true_for_supported_events(self):
        """T023.1: can_handle() must return True for events observer supports."""
        observer = self.observer
        
        self.assertTrue(observer.can_handle('test.event'))
        self.assertTrue(observer.can_handle('test.another.event'))
    
    def test_can_handle_returns_false_for_unsupported_events(self):
        """T023.2: can_handle() must return False for events observer doesn't support."""
        observer = self.observer
        
        self.assertFalse(observer.can_handle('unsupported.event'))
        self.assertFalse(observer.can_handle('property.created'))
    
    def test_handle_processes_event_data(self):
        """T023.3: handle() must process event data and return result."""
        observer = self.observer
        
        result = observer.handle('test.event', {'property_id': 5, 'agent_id': 10})
        
        self.assertEqual(result['status'], 'handled')
        self.assertEqual(result['event'], 'test.event')
        self.assertEqual(result['data'], {'property_id': 5, 'agent_id': 10})
    
    def test_validate_data_passes_with_all_required_keys(self):
        """T023.4: _validate_data() must pass when all required keys present."""
        observer = self.observer
        
        data = {'property_id': 10, 'agent_id': 5, 'company_id': 1}
        
        observer._validate_data(data, ['property_id', 'agent_id'])
    
    def test_validate_data_raises_on_missing_keys(self):
        """T023.5: _validate_data() must raise ValueError if required keys missing."""
        observer = self.observer
        
        data = {'property_id': 10}
        
        with self.assertRaises(ValueError) as ctx:
            observer._validate_data(data, ['property_id', 'agent_id', 'company_id'])
        
        self.assertIn('agent_id', str(ctx.exception))
        self.assertIn('company_id', str(ctx.exception))
    
    def test_abstract_observer_not_implemented_methods(self):
        """T023.6: Direct instantiation of AbstractObserver must raise NotImplementedError."""
        base_observer = self.env['quicksol.abstract.observer']
        
        with self.assertRaises(NotImplementedError):
            base_observer.can_handle('test.event')
        
        with self.assertRaises(NotImplementedError):
            base_observer.handle('test.event', {})
