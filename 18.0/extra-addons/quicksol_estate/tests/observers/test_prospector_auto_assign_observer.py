"""
Test suite for ProspectorAutoAssignObserver.

Tests observer pattern with force_sync=True for prospector_id auto-assignment.
Coverage: event handling, sync execution, edge cases.
"""
from odoo.tests.common import TransactionCase
from odoo.addons.quicksol_estate.models.event_bus import EventBus
from odoo.addons.quicksol_estate.models.observers.prospector_auto_assign_observer import ProspectorAutoAssignObserver


class TestProspectorAutoAssignObserver(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.Company = cls.env['thedevkitchen.estate.company']
        cls.Property = cls.env['real.estate.property']
        cls.Agent = cls.env['real.estate.agent']
        cls.User = cls.env['res.users']
        
        cls.prospector_group = cls.env.ref('quicksol_estate.group_real_estate_prospector')
        cls.manager_group = cls.env.ref('quicksol_estate.group_real_estate_manager')
        
        cls.company_a = cls.Company.create({
            'name': 'Company A',
            'cnpj': '12.345.678/0001-90',
            'creci': 'CRECI-SP 12345',
        })
        
        # Create prospector user and agent
        cls.prospector_user = cls.User.create({
            'name': 'Prospector User',
            'login': 'prospector_obs@test.com',
            'email': 'prospector_obs@test.com',
            'groups_id': [(6, 0, [cls.prospector_group.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        cls.prospector_agent = cls.Agent.create({
            'name': 'Prospector Agent',
            'creci': 'CRECI-SP 99999',
            'user_id': cls.prospector_user.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        # Create manager user (non-prospector)
        cls.manager_user = cls.User.create({
            'name': 'Manager User',
            'login': 'manager_obs@test.com',
            'email': 'manager_obs@test.com',
            'groups_id': [(6, 0, [cls.manager_group.id])],
            'estate_company_ids': [(6, 0, [cls.company_a.id])],
        })
        
        cls.observer = ProspectorAutoAssignObserver()
        cls.event_bus = cls.env['quicksol.event.bus']
    
    def test_observer_handles_property_before_create_event(self):
        """T098.1: Observer listens to property.before_create event."""
        vals = {
            'name': 'Observer Test Property',
            'company_ids': [(6, 0, [self.company_a.id])],
        }
        
        # Emit event as Prospector user
        self.observer.handle('property.before_create', vals, env=self.env.with_user(self.prospector_user))
        
        # prospector_id should be auto-assigned
        self.assertIn('prospector_id', vals)
        self.assertEqual(vals['prospector_id'], self.prospector_agent.id)
    
    def test_observer_uses_force_sync_true(self):
        """T098.2: Observer handles event with force_sync=True (data mutation before create)."""
        # Create property as Prospector user (triggers observer via EventBus)
        property_obj = self.Property.with_user(self.prospector_user).create({
            'name': 'Force Sync Test',
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        # prospector_id should be auto-assigned by observer
        self.assertEqual(property_obj.prospector_id.id, self.prospector_agent.id)
    
    def test_observer_skips_non_prospector_users(self):
        """T098.3: Observer does NOT assign prospector_id for non-Prospector users."""
        vals = {
            'name': 'Manager Property',
            'company_ids': [(6, 0, [self.company_a.id])],
        }
        
        # Emit event as Manager user (not a Prospector)
        self.observer.handle('property.before_create', vals, env=self.env.with_user(self.manager_user))
        
        # prospector_id should NOT be assigned
        self.assertNotIn('prospector_id', vals)
    
    def test_observer_respects_manual_prospector_id(self):
        """T098.4: Observer does NOT overwrite manually set prospector_id."""
        # Create another agent
        another_agent = self.Agent.create({
            'name': 'Another Agent',
            'cpf': '888.999.000-11',
            'creci': 'CRECI-SP 77777',
            'company_ids': [(6, 0, [self.company_a.id])],
        })
        
        vals = {
            'name': 'Manual Prospector ID',
            'prospector_id': another_agent.id,
            'company_ids': [(6, 0, [self.company_a.id])],
        }
        
        # Emit event as Prospector user
        self.observer.handle('property.before_create', vals, env=self.env.with_user(self.prospector_user))
        
        # prospector_id should remain the manually set value
        self.assertEqual(vals['prospector_id'], another_agent.id)
        self.assertNotEqual(vals['prospector_id'], self.prospector_agent.id)
    
    def test_observer_handles_prospector_without_agent_record(self):
        """T098.5: Observer handles Prospector user without linked agent record gracefully."""
        # Create prospector user without agent record
        prospector_no_agent = self.User.create({
            'name': 'Prospector No Agent',
            'login': 'prospector_no_agent@test.com',
            'email': 'prospector_no_agent@test.com',
            'groups_id': [(6, 0, [self.prospector_group.id])],
            'estate_company_ids': [(6, 0, [self.company_a.id])],
        })
        
        vals = {
            'name': 'Property No Agent Link',
            'company_ids': [(6, 0, [self.company_a.id])],
        }
        
        # Emit event as prospector_no_agent
        self.observer.handle('property.before_create', vals, env=self.env.with_user(prospector_no_agent))
        
        # prospector_id should NOT be assigned (no agent record)
        self.assertNotIn('prospector_id', vals)
    
    def test_observer_ignores_other_events(self):
        """T098.6: Observer ignores events other than property.before_create."""
        vals = {
            'name': 'Wrong Event',
            'company_ids': [(6, 0, [self.company_a.id])],
        }
        
        # Emit property.created event (not property.before_create)
        self.observer.handle('property.created', vals, env=self.env.with_user(self.prospector_user))
        
        # prospector_id should NOT be assigned
        self.assertNotIn('prospector_id', vals)
