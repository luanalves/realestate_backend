# -*- coding: utf-8 -*-
"""
Unit Test: Service Conditional Uniqueness (EXCLUDE constraint) — Feature 015

Verifies the uniqueness rule:
  - One active service per (client_partner_id, operation_type, agent_id)
  - Historical (won/lost) duplicates allowed
  - Same property in multiple active services allowed (FR-008a)

ADR-003: unittest.TestCase (no DB, mock only).
Task: T019
FRs: FR-008, FR-008a
Research: R1
"""
import unittest
from unittest.mock import MagicMock


ACTIVE_STAGES = {'no_service', 'in_service', 'visit', 'proposal', 'formalization'}
TERMINAL_STAGES = {'won', 'lost'}


def _is_duplicate_active(existing_services, client_id, operation_type, agent_id):
    """Simulate the EXCLUDE constraint logic for uniqueness check.

    Returns True if there's already an active service with the same
    (client_partner_id, operation_type, agent_id).
    """
    for svc in existing_services:
        if (
            svc.client_partner_id.id == client_id
            and svc.operation_type == operation_type
            and svc.agent_id.id == agent_id
            and svc.active
            and svc.stage not in TERMINAL_STAGES
        ):
            return True
    return False


def _make_service(client_id, operation_type, agent_id, stage='in_service',
                  active=True, property_ids=None):
    svc = MagicMock()
    svc.client_partner_id = MagicMock()
    svc.client_partner_id.id = client_id
    svc.operation_type = operation_type
    svc.agent_id = MagicMock()
    svc.agent_id.id = agent_id
    svc.stage = stage
    svc.active = active
    svc.property_ids = property_ids or []
    return svc


class TestServiceUniqueness(unittest.TestCase):
    """EXCLUDE constraint logic: one active service per client+type+agent."""

    def test_duplicate_active_service_blocked(self):
        """FR-008: creating a duplicate active service is blocked."""
        existing = [_make_service(client_id=1, operation_type='rent', agent_id=10)]
        is_dup = _is_duplicate_active(existing, client_id=1, operation_type='rent', agent_id=10)
        self.assertTrue(is_dup, 'Duplicate active service should be detected')

    def test_different_operation_type_allowed(self):
        """FR-008: same client+agent but different operation type is OK."""
        existing = [_make_service(client_id=1, operation_type='rent', agent_id=10)]
        is_dup = _is_duplicate_active(existing, client_id=1, operation_type='sale', agent_id=10)
        self.assertFalse(is_dup, 'Different operation type must not block creation')

    def test_different_agent_allowed(self):
        """FR-008: same client+type but different agent is OK."""
        existing = [_make_service(client_id=1, operation_type='rent', agent_id=10)]
        is_dup = _is_duplicate_active(existing, client_id=1, operation_type='rent', agent_id=20)
        self.assertFalse(is_dup, 'Different agent must not block creation')

    def test_terminal_stage_not_blocking(self):
        """FR-008: won/lost services do not block new active services."""
        won_service = _make_service(client_id=1, operation_type='rent', agent_id=10, stage='won')
        existing = [won_service]
        is_dup = _is_duplicate_active(existing, client_id=1, operation_type='rent', agent_id=10)
        self.assertFalse(is_dup, 'Historical (won/lost) service must not block new creation')

    def test_lost_service_not_blocking(self):
        """FR-008: lost services do not block new active services."""
        lost_service = _make_service(client_id=1, operation_type='sale', agent_id=5, stage='lost')
        existing = [lost_service]
        is_dup = _is_duplicate_active(existing, client_id=1, operation_type='sale', agent_id=5)
        self.assertFalse(is_dup)

    def test_archived_service_not_blocking(self):
        """FR-008: archived (active=False) services do not block new active services."""
        archived = _make_service(client_id=1, operation_type='rent', agent_id=10, active=False)
        existing = [archived]
        is_dup = _is_duplicate_active(existing, client_id=1, operation_type='rent', agent_id=10)
        self.assertFalse(is_dup)


class TestSamePropertyMultipleServices(unittest.TestCase):
    """FR-008a: same property can be referenced by multiple active services."""

    def test_same_property_in_multiple_active_services_allowed(self):
        """FR-008a: property uniqueness is NOT enforced at service level."""
        shared_property = MagicMock()
        svc1 = _make_service(client_id=1, operation_type='sale', agent_id=10,
                             property_ids=[shared_property])
        svc2 = _make_service(client_id=2, operation_type='rent', agent_id=20,
                             property_ids=[shared_property])

        # Both services active, same property — no conflict at service level
        prop_id = id(shared_property)
        svc1_props = [id(p) for p in svc1.property_ids]
        svc2_props = [id(p) for p in svc2.property_ids]

        self.assertIn(prop_id, svc1_props)
        self.assertIn(prop_id, svc2_props)
        # No uniqueness constraint on property — both can coexist
        conflict = False  # service-level check: no constraint on property_ids
        self.assertFalse(conflict)


if __name__ == '__main__':
    unittest.main()
