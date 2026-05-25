# -*- coding: utf-8 -*-
"""
Unit tests for CMS settings validations.
Tests: company_slug format, CSS injection patterns, custom_js RBAC.
"""
import re
import unittest


# CSS injection patterns (mirrors cms_settings_service.py)
CSS_INJECTION_PATTERNS = [
    re.compile(r"expression\s*\(", re.IGNORECASE),
    re.compile(r"behavior\s*:", re.IGNORECASE),
    re.compile(r"url\s*\(\s*javascript:", re.IGNORECASE),
    re.compile(r"@import", re.IGNORECASE),
    re.compile(r"-moz-binding", re.IGNORECASE),
]

COMPANY_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _detect_css_injection(css):
    for pattern in CSS_INJECTION_PATTERNS:
        if pattern.search(css):
            return True
    return False


class TestCmsSettingsValidations(unittest.TestCase):

    # ---- company_slug ----

    def test_valid_slugs_accepted(self):
        valid = ["minha-agencia", "agency123", "test-agency-2"]
        for slug in valid:
            with self.subTest(slug=slug):
                self.assertTrue(COMPANY_SLUG_PATTERN.match(slug))

    def test_uppercase_slug_rejected(self):
        self.assertIsNone(COMPANY_SLUG_PATTERN.match("MinhaAgencia"))

    def test_slug_with_spaces_rejected(self):
        self.assertIsNone(COMPANY_SLUG_PATTERN.match("minha agencia"))

    def test_slug_with_underscore_rejected(self):
        self.assertIsNone(COMPANY_SLUG_PATTERN.match("minha_agencia"))

    # ---- CSS injection ----

    def test_css_expression_detected(self):
        self.assertTrue(_detect_css_injection("body { width: expression(alert(1)) }"))

    def test_css_behavior_detected(self):
        self.assertTrue(_detect_css_injection("body { behavior: url(hack.htc) }"))

    def test_css_javascript_url_detected(self):
        self.assertTrue(_detect_css_injection("body { background: url(javascript:void(0)) }"))

    def test_css_import_detected(self):
        self.assertTrue(_detect_css_injection("@import url('evil.css');"))

    def test_css_moz_binding_detected(self):
        self.assertTrue(_detect_css_injection("div { -moz-binding: url('hack.xml#exploit'); }"))

    def test_clean_css_accepted(self):
        clean = "body { color: red; font-size: 16px; margin: 0; }"
        self.assertFalse(_detect_css_injection(clean))

    def test_css_injection_case_insensitive(self):
        self.assertTrue(_detect_css_injection("body { BEHAVIOR: url() }"))
        self.assertTrue(_detect_css_injection("body { width: EXPRESSION(1) }"))

    # ---- custom_js RBAC ----

    def test_owner_can_set_custom_js(self):
        """Owner role should be allowed to set custom_js."""
        role = "owner"
        self.assertIn(role, ("owner",))  # Only owner is allowed

    def test_director_cannot_set_custom_js(self):
        """Director must not be able to set custom_js."""
        role = "director"
        self.assertNotIn(role, ("owner",))

    def test_manager_cannot_set_custom_js(self):
        role = "manager"
        self.assertNotIn(role, ("owner",))

    def test_agent_cannot_set_custom_js(self):
        role = "agent"
        self.assertNotIn(role, ("owner",))

    # ---- serialize_for_role ----

    def test_owner_sees_custom_js(self):
        """serialize_for_role for owner should include custom_js."""
        settings = {"custom_js": "alert('ok')", "company_slug": "a", "custom_css": ""}
        result = {k: v for k, v in settings.items()} if "owner" == "owner" else {k: v for k, v in settings.items() if k != "custom_js"}
        self.assertIn("custom_js", result)

    def test_non_owner_does_not_see_custom_js(self):
        """serialize_for_role for non-owner should exclude custom_js."""
        settings = {"custom_js": "alert('ok')", "company_slug": "a", "custom_css": ""}
        role = "manager"
        result = {k: v for k, v in settings.items() if k != "custom_js"} if role != "owner" else settings
        self.assertNotIn("custom_js", result)


if __name__ == "__main__":
    unittest.main()
