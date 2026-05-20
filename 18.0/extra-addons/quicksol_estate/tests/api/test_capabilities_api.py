# -*- coding: utf-8 -*-
import json
from datetime import timedelta

from odoo import fields
from odoo.tests.common import HttpCase, tagged
from odoo.tools import config

from .utils import (
    build_capabilities_headers,
    build_session_security_token,
    make_session_id,
)


@tagged("post_install", "-at_install", "capabilities_api")
class TestCapabilitiesAPI(HttpCase):
    """HTTP coverage for GET /api/v1/me/capabilities."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secret = (
            config.get("database_secret") or config.get("admin_passwd") or "admin"
        )
        cls.oauth_app = cls.env["thedevkitchen.oauth.application"].create(
            {
                "name": "Capabilities API Test App",
            }
        )
        cls.access_token = "capabilities_api_test_token"
        cls.env["thedevkitchen.oauth.token"].create(
            {
                "application_id": cls.oauth_app.id,
                "access_token": cls.access_token,
                "refresh_token": "capabilities_api_refresh_token",
                "expires_at": fields.Datetime.now() + timedelta(hours=1),
                "revoked": False,
            }
        )

        cls.company_a = cls.env.ref("quicksol_estate.company_capabilities_a")
        cls.company_b = cls.env.ref("quicksol_estate.company_capabilities_b")
        cls.owner_a = cls.env.ref("quicksol_estate.user_capabilities_owner_a")
        cls.manager_a = cls.env.ref("quicksol_estate.user_capabilities_manager_a")
        cls.agent_a = cls.env.ref("quicksol_estate.user_capabilities_agent_a")
        cls.director_a = cls.env.ref("quicksol_estate.user_capabilities_director_a")
        cls.prospector_a = cls.env.ref("quicksol_estate.user_capabilities_prospector_a")
        cls.receptionist_a = cls.env.ref(
            "quicksol_estate.user_capabilities_receptionist_a"
        )
        cls.financial_a = cls.env.ref("quicksol_estate.user_capabilities_financial_a")
        cls.legal_a = cls.env.ref("quicksol_estate.user_capabilities_legal_a")
        cls.property_owner_a = cls.env.ref(
            "quicksol_estate.user_capabilities_property_owner_a"
        )
        cls.tenant_a = cls.env.ref("quicksol_estate.user_capabilities_tenant_a")
        cls.multi_role_a = cls.env.ref("quicksol_estate.user_capabilities_multi_role_a")
        cls.owner_multi_company = cls.env.ref(
            "quicksol_estate.user_capabilities_owner_multi_company"
        )
        cls.no_role_a = cls.env.ref("quicksol_estate.user_capabilities_no_role_a")

    @classmethod
    def _session_for(
        cls, user, user_agent="CapabilitiesTest/1.0", accept_language="en-US"
    ):
        session_id = make_session_id()
        security_token = build_session_security_token(
            user.id,
            cls.secret,
            user_agent=user_agent,
            accept_language=accept_language,
        )
        cls.env["thedevkitchen.api.session"].create(
            {
                "session_id": session_id,
                "user_id": user.id,
                "ip_address": "127.0.0.1",
                "user_agent": user_agent,
                "security_token": security_token,
                "is_active": True,
            }
        )
        return session_id

    def _capabilities_get(self, user, company_id, user_agent="CapabilitiesTest/1.0"):
        session_id = self._session_for(user, user_agent=user_agent)
        headers = build_capabilities_headers(
            self.access_token,
            session_id,
            company_id,
            user_agent=user_agent,
        )
        response = self.url_open("/api/v1/me/capabilities", headers=headers)
        return response, json.loads(response.text)

    def _me_get(self, user):
        session_id = self._session_for(user, user_agent="MeContractTest/1.0")
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Openerp-Session-Id": session_id,
            "User-Agent": "MeContractTest/1.0",
            "Accept-Language": "en-US",
        }
        response = self.url_open("/api/v1/me", headers=headers)
        return response, json.loads(response.text)

    def test_get_capabilities_requires_jwt(self):
        response = self.url_open("/api/v1/me/capabilities")
        self.assertEqual(response.status_code, 401)

    def test_get_capabilities_requires_session(self):
        response = self.url_open(
            "/api/v1/me/capabilities",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        self.assertEqual(response.status_code, 401)

    def test_get_capabilities_requires_company_authorization(self):
        response, body = self._capabilities_get(self.owner_a, self.company_b.id)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(body["error"], "forbidden")

    def test_get_capabilities_returns_exact_contract_shape(self):
        response, body = self._capabilities_get(self.owner_a, self.company_a.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(body.keys()), {"user", "rules"})
        self.assertEqual(set(body["user"].keys()), {"id", "role", "company_id"})
        self.assertEqual(body["user"]["company_id"], self.company_a.id)
        self.assertTrue(
            any(
                rule == {"action": "view", "subject": "MenuAdmin"}
                for rule in body["rules"]
            )
        )

    def test_agent_does_not_receive_owner_only_rules(self):
        response, body = self._capabilities_get(self.agent_a, self.company_a.id)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn({"action": "view", "subject": "MenuAdmin"}, body["rules"])
        self.assertIn({"action": "cancel", "subject": "Service"}, body["rules"])

    def test_manager_receives_reassign_rules(self):
        response, body = self._capabilities_get(self.manager_a, self.company_a.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn({"action": "reassign", "subject": "Lead"}, body["rules"])
        self.assertIn({"action": "reassign", "subject": "Service"}, body["rules"])

    def test_external_roles_receive_limited_rules(self):
        _, owner_body = self._capabilities_get(self.property_owner_a, self.company_a.id)
        _, tenant_body = self._capabilities_get(self.tenant_a, self.company_a.id)
        expected = [
            {"action": "view", "subject": "Property"},
            {"action": "view", "subject": "Proposal"},
        ]
        self.assertEqual(owner_body["rules"], expected)
        self.assertEqual(tenant_body["rules"], expected)

    def test_multi_role_user_matches_me_role_precedence(self):
        cap_response, cap_body = self._capabilities_get(
            self.multi_role_a, self.company_a.id
        )
        me_response, me_body = self._me_get(self.multi_role_a)
        self.assertEqual(cap_response.status_code, 200)
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(cap_body["user"]["role"], "manager")
        self.assertEqual(cap_body["user"]["role"], me_body["user"]["role"])

    def test_no_role_user_returns_empty_rules(self):
        response, body = self._capabilities_get(self.no_role_a, self.company_a.id)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(body["user"]["role"])
        self.assertEqual(body["rules"], [])

    def test_capabilities_respects_requested_active_company(self):
        response_a, body_a = self._capabilities_get(
            self.owner_multi_company, self.company_a.id
        )
        response_b, body_b = self._capabilities_get(
            self.owner_multi_company, self.company_b.id
        )
        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_b.status_code, 200)
        self.assertEqual(body_a["user"]["company_id"], self.company_a.id)
        self.assertEqual(body_b["user"]["company_id"], self.company_b.id)

    def test_all_supported_roles_matrix_smoke(self):
        users = {
            "owner": self.owner_a,
            "director": self.director_a,
            "manager": self.manager_a,
            "agent": self.agent_a,
            "prospector": self.prospector_a,
            "receptionist": self.receptionist_a,
            "financial": self.financial_a,
            "legal": self.legal_a,
            "property_owner": self.property_owner_a,
            "tenant": self.tenant_a,
        }
        for expected_role, user in users.items():
            response, body = self._capabilities_get(user, self.company_a.id)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(body["user"]["role"], expected_role)
            self.assertIsInstance(body["rules"], list)

    def test_response_never_leaks_internal_rbac_artifacts(self):
        response, body = self._capabilities_get(self.owner_a, self.company_a.id)
        self.assertEqual(response.status_code, 200)
        payload = json.dumps(body)
        self.assertNotIn("quicksol_estate.group_real_estate_owner", payload)
        self.assertNotIn("domain", payload.lower())
        self.assertNotIn("xml_id", payload.lower())
        self.assertNotIn("model", payload.lower())

    def test_me_endpoint_contract_unchanged(self):
        response, body = self._me_get(self.manager_a)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(body.keys()), {"user"})
        self.assertIn("companies", body["user"])
        self.assertIn("default_company_id", body["user"])
        self.assertEqual(body["user"]["role"], "manager")
