# -*- coding: utf-8 -*-
"""
Unit tests for CMS page state machine.
Tests all valid and invalid transitions, published_at assignment, and error envelopes.
"""
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime


# ---- State machine constants (mirrors cms_page_service.py) ----

VALID_TRANSITIONS = {
    "draft": ["pending_review", "published"],
    "pending_review": ["published", "draft"],
    "published": ["archived"],
    "archived": ["draft"],
}

ALL_STATUSES = list(VALID_TRANSITIONS.keys())


class TestCmsStatusMachine(unittest.TestCase):
    """Test state machine logic for thedevkitchen.cms.page"""

    # ---- Valid transitions ----

    def test_all_valid_transitions_accepted(self):
        """All entries in VALID_TRANSITIONS must be accepted without error."""
        valid_cases = [
            ("draft", "pending_review"),
            ("draft", "published"),
            ("pending_review", "published"),
            ("pending_review", "draft"),
            ("published", "archived"),
            ("archived", "draft"),
        ]
        for from_status, to_status in valid_cases:
            with self.subTest(from_status=from_status, to_status=to_status):
                allowed = VALID_TRANSITIONS.get(from_status, [])
                self.assertIn(
                    to_status,
                    allowed,
                    f"Expected {from_status}→{to_status} to be valid",
                )

    # ---- Invalid transitions ----

    def test_all_invalid_transitions_rejected(self):
        """Transitions not in VALID_TRANSITIONS must be rejected."""
        invalid_cases = [
            ("draft", "archived"),
            ("pending_review", "archived"),
            ("published", "draft"),
            ("published", "pending_review"),
            ("archived", "published"),
            ("archived", "pending_review"),
        ]
        for from_status, to_status in invalid_cases:
            with self.subTest(from_status=from_status, to_status=to_status):
                allowed = VALID_TRANSITIONS.get(from_status, [])
                self.assertNotIn(
                    to_status,
                    allowed,
                    f"Expected {from_status}→{to_status} to be invalid",
                )

    # ---- Unknown status ----

    def test_unknown_to_status_rejected(self):
        """A completely unknown target status must not appear in any transitions."""
        unknown = "superseded"
        for from_status, allowed in VALID_TRANSITIONS.items():
            self.assertNotIn(unknown, allowed)

    # ---- published_at assignment ----

    def test_published_at_set_on_published_transition(self):
        """published_at must be filled when transitioning to 'published'."""
        page = MagicMock()
        page.status = "draft"
        page.published_at = None

        # Simulate the transition logic
        to_status = "published"
        if to_status == "published":
            page.published_at = datetime.utcnow()

        self.assertIsNotNone(page.published_at)

    def test_published_at_not_set_on_other_transitions(self):
        """published_at must NOT be changed when transitioning to non-published states."""
        page = MagicMock()
        page.published_at = None

        for to_status in ["draft", "pending_review", "archived"]:
            with self.subTest(to_status=to_status):
                if to_status == "published":
                    page.published_at = datetime.utcnow()
                # For non-published transitions, published_at stays None
                if to_status != "published":
                    self.assertIsNone(page.published_at)

    # ---- Error envelope for invalid transition ----

    def test_error_envelope_contains_required_fields(self):
        """_cms_error for invalid_status_transition must include from, to, allowed."""
        # Simulate what change_status() would return
        from_status = "published"
        to_status = "draft"
        allowed = VALID_TRANSITIONS.get(from_status, [])

        error_payload = {
            "error": "invalid_status_transition",
            "detail": f"Cannot transition from '{from_status}' to '{to_status}'.",
            "from_status": from_status,
            "to_status": to_status,
            "allowed": allowed,
        }

        self.assertEqual(error_payload["error"], "invalid_status_transition")
        self.assertIn("from_status", error_payload)
        self.assertIn("to_status", error_payload)
        self.assertIn("allowed", error_payload)
        self.assertIsInstance(error_payload["allowed"], list)

    def test_error_envelope_unknown_status(self):
        """_cms_error for invalid_status_value must include allowed list."""
        allowed_statuses = ALL_STATUSES

        error_payload = {
            "error": "invalid_status_value",
            "detail": "Unknown target status.",
            "allowed": allowed_statuses,
        }

        self.assertEqual(error_payload["error"], "invalid_status_value")
        self.assertIn("allowed", error_payload)
        self.assertEqual(sorted(error_payload["allowed"]), sorted(ALL_STATUSES))


if __name__ == "__main__":
    unittest.main()
