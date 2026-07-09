# -*- coding: utf-8 -*-
"""
Unit Test: Lead Company/Agent Isolation Helpers (Feature 024)

Tests _is_agent_role() and _check_lead_company_access(), the two new
helpers on LeadApiController that make company/agent scoping explicit
in list_leads/export_leads_csv/lead_statistics and the activity
endpoints (log_activity/list_activities/schedule_activity).

Follows ADR-003: Unitario (SEM banco, mock only).
"""

import unittest
from unittest.mock import MagicMock
from pathlib import Path
import sys

# Setup odoo.addons namespace for imports (no running Odoo server needed)
import odoo.addons
_addons_root = str(Path(__file__).parent.parent.parent.parent)  # /mnt/extra-addons
if _addons_root not in odoo.addons.__path__:
    odoo.addons.__path__.insert(0, _addons_root)

from odoo.addons.quicksol_estate.controllers.lead_api import LeadApiController


class TestIsAgentRole(unittest.TestCase):
    """Validates _is_agent_role() classification (FR2.1)"""

    def setUp(self):
        self.controller = LeadApiController()

    def _user_with_groups(self, groups):
        user = MagicMock()
        user.has_group.side_effect = lambda group: group in groups
        return user

    def test_pure_agent_returns_true(self):
        user = self._user_with_groups({"quicksol_estate.group_real_estate_agent"})
        self.assertTrue(self.controller._is_agent_role(user))

    def test_agent_and_manager_returns_false(self):
        user = self._user_with_groups(
            {
                "quicksol_estate.group_real_estate_agent",
                "quicksol_estate.group_real_estate_manager",
            }
        )
        self.assertFalse(self.controller._is_agent_role(user))

    def test_agent_and_owner_returns_false(self):
        user = self._user_with_groups(
            {
                "quicksol_estate.group_real_estate_agent",
                "quicksol_estate.group_real_estate_owner",
            }
        )
        self.assertFalse(self.controller._is_agent_role(user))

    def test_admin_with_agent_group_returns_false(self):
        user = self._user_with_groups(
            {"quicksol_estate.group_real_estate_agent", "base.group_system"}
        )
        self.assertFalse(self.controller._is_agent_role(user))

    def test_no_agent_group_returns_false(self):
        user = self._user_with_groups(set())
        self.assertFalse(self.controller._is_agent_role(user))


class TestCheckLeadCompanyAccess(unittest.TestCase):
    """Validates _check_lead_company_access() (FR3.2/FR3.4)"""

    def setUp(self):
        self.controller = LeadApiController()

    def _lead_with_company(self, company_id):
        lead = MagicMock()
        lead.company_id.id = company_id
        return lead

    def test_lead_in_caller_company_allowed(self):
        lead = self._lead_with_company(1)
        self.assertTrue(
            self.controller._check_lead_company_access(lead, user_company_ids=[1, 2])
        )

    def test_lead_outside_caller_companies_denied(self):
        lead = self._lead_with_company(99)
        self.assertFalse(
            self.controller._check_lead_company_access(lead, user_company_ids=[1, 2])
        )

    def test_empty_company_ids_bypasses_check_admin(self):
        lead = self._lead_with_company(99)
        self.assertTrue(
            self.controller._check_lead_company_access(lead, user_company_ids=[])
        )


if __name__ == "__main__":
    unittest.main()
