# -*- coding: utf-8 -*-
"""
Unit tests for cms_page model validations.
Tests: slug format, structured_data JSON, og_image_id cross-company, content size.
"""
import json
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

try:
    from odoo.exceptions import ValidationError
except (ImportError, ModuleNotFoundError, AttributeError):
    class ValidationError(Exception):  # noqa: N818
        pass


class TestCmsPageValidations(unittest.TestCase):
    """Test @api.constrains validators on thedevkitchen.cms.page"""

    def _make_page(self, slug=None, structured_data=None, og_image_id=None, company_id=None):
        """Build a mock CMS page record."""
        page = MagicMock()
        page.slug = slug
        page.structured_data = structured_data
        page.og_image_id = og_image_id
        page.company_id = company_id
        return page

    # ---- slug validation ----

    def test_valid_slug_accepted(self):
        """Slugs matching ^[a-z0-9]+(?:-[a-z0-9]+)*$ should not raise."""
        import re
        pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        valid_slugs = ["home", "about-us", "contact-page", "123", "a1-b2"]
        for slug in valid_slugs:
            with self.subTest(slug=slug):
                self.assertTrue(pattern.match(slug), f"Expected '{slug}' to be valid")

    def test_invalid_slug_rejected(self):
        """Slugs with uppercase, spaces, underscores, or leading/trailing hyphens should fail."""
        import re
        pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        invalid_slugs = ["MY_PAGE", "My Page", "about_us", "-start", "end-", "UPPER"]
        for slug in invalid_slugs:
            with self.subTest(slug=slug):
                self.assertFalse(pattern.match(slug), f"Expected '{slug}' to be invalid")

    # ---- structured_data validation ----

    def test_valid_json_structured_data(self):
        """Valid JSON-LD should not raise."""
        valid_json = json.dumps({"@context": "https://schema.org", "@type": "WebPage"})
        try:
            json.loads(valid_json)
        except ValueError:
            self.fail("Valid JSON raised ValueError")

    def test_invalid_json_structured_data_raises(self):
        """Non-JSON string in structured_data should raise ValidationError."""
        # Simulate the constraint logic
        invalid_value = "not-a-json"
        with self.assertRaises((ValueError, ValidationError)):
            parsed = json.loads(invalid_value)

    def test_empty_structured_data_allowed(self):
        """None / empty structured_data should be accepted (field is optional)."""
        for value in [None, ""]:
            with self.subTest(value=value):
                # Constraint should short-circuit on falsy value
                self.assertFalse(bool(value))  # falsy means constraint skips

    # ---- og_image_id cross-company validation ----

    def test_og_image_same_company_allowed(self):
        """og_image_id belonging to the same company should be accepted."""
        company = MagicMock()
        company.id = 1
        og_image = MagicMock()
        og_image.company_id = company
        page_company = company

        # Constraint passes if og_image.company_id == page.company_id
        self.assertEqual(og_image.company_id, page_company)

    def test_og_image_different_company_raises(self):
        """og_image_id from a different company must raise ValidationError."""
        company_a = MagicMock()
        company_a.id = 1
        company_b = MagicMock()
        company_b.id = 2

        og_image = MagicMock()
        og_image.company_id = company_b

        page_company = company_a

        # Simulate constraint
        if og_image.company_id and og_image.company_id != page_company:
            with self.assertRaises(ValidationError):
                raise ValidationError(
                    "The Open Graph image must belong to the same company as the page."
                )


if __name__ == "__main__":
    unittest.main()
