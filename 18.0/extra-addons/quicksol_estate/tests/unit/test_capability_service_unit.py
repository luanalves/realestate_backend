# -*- coding: utf-8 -*-
import importlib.util
import unittest
from pathlib import Path


def _load_module(module_name, relative_path):
    root = Path(__file__).resolve().parents[2]
    module_path = root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


capability_service = _load_module(
    "capability_service", "services/capability_service.py"
)
role_resolver = _load_module(
    "role_resolver",
    "services/role_resolver.py",
)


class FakeUser:
    def __init__(self, enabled_groups=None):
        self.enabled_groups = set(enabled_groups or [])

    def has_group(self, xml_id):
        return xml_id in self.enabled_groups


class FakeRecord:
    def __init__(self, user_id):
        self.id = user_id


class TestCapabilityServiceUnit(unittest.TestCase):
    """Unit coverage for capability projection and shared role resolution."""

    def setUp(self):
        self.service = capability_service.CapabilityService()

    def test_role_resolver_matches_me_endpoint_order(self):
        """FR-006: Shared resolver keeps /me precedence order."""
        user = FakeUser(
            {
                "quicksol_estate.group_real_estate_agent",
                "quicksol_estate.group_real_estate_manager",
            }
        )
        self.assertEqual(role_resolver.resolve_role(user), "manager")

    def test_role_resolver_maps_portal_user_to_tenant(self):
        """FR-010: Portal users resolve to tenant role label."""
        user = FakeUser({"quicksol_estate.group_real_estate_portal_user"})
        self.assertEqual(role_resolver.resolve_role(user), "tenant")

    def test_capability_service_deduplicates_rules(self):
        """FR-015: Duplicate action/subject pairs are omitted."""
        original = capability_service.ROLE_RULES["agent"]
        capability_service.ROLE_RULES["agent"] = [
            ("view", "Property"),
            ("view", "Property"),
            ("create", "Property"),
        ]
        try:
            self.assertEqual(
                self.service.get_rules("agent"),
                [
                    {"action": "view", "subject": "Property"},
                    {"action": "create", "subject": "Property"},
                ],
            )
        finally:
            capability_service.ROLE_RULES["agent"] = original

    def test_capability_service_stable_contract_order(self):
        """FR-016: Rules preserve the declared canonical order."""
        rules = self.service.get_rules("owner")
        self.assertEqual(
            rules[:6],
            [
                {"action": "view", "subject": "MenuCRM"},
                {"action": "view", "subject": "MenuAdmin"},
                {"action": "view", "subject": "Dashboard"},
                {"action": "view", "subject": "Property"},
                {"action": "create", "subject": "Property"},
                {"action": "update", "subject": "Property"},
            ],
        )

    def test_only_whitelisted_subjects_are_serialized(self):
        """FR-012: Unknown subjects fail closed."""
        original = capability_service.ROLE_RULES["legal"]
        capability_service.ROLE_RULES["legal"] = [
            ("view", "Company"),
            ("view", "ForbiddenSubject"),
        ]
        try:
            self.assertEqual(
                self.service.get_rules("legal"),
                [{"action": "view", "subject": "Company"}],
            )
        finally:
            capability_service.ROLE_RULES["legal"] = original

    def test_only_whitelisted_actions_are_serialized(self):
        """FR-012: Unknown actions fail closed."""
        original = capability_service.ROLE_RULES["financial"]
        capability_service.ROLE_RULES["financial"] = [
            ("view", "Report"),
            ("manage", "Report"),
        ]
        try:
            self.assertEqual(
                self.service.get_rules("financial"),
                [{"action": "view", "subject": "Report"}],
            )
        finally:
            capability_service.ROLE_RULES["financial"] = original

    def test_no_role_returns_empty_rules(self):
        """FR-007: Missing role yields empty capability list."""
        self.assertEqual(self.service.get_rules(None), [])
        self.assertEqual(self.service.get_rules("unknown"), [])

    def test_build_payload_contains_exact_contract(self):
        """FR-004/FR-005: Payload contains only user and rules contract keys."""
        payload = self.service.build_payload(FakeRecord(9), "tenant", 22)
        self.assertEqual(set(payload.keys()), {"user", "rules"})
        self.assertEqual(payload["user"], {"id": 9, "role": "tenant", "company_id": 22})
        self.assertEqual(
            payload["rules"],
            [
                {"action": "view", "subject": "Property"},
                {"action": "view", "subject": "Proposal"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
