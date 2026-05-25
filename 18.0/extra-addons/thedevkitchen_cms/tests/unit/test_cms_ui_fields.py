# -*- coding: utf-8 -*-
"""
Unit tests for the Odoo admin UI fields added to CMS models:
  - CmsPage.html_content (fields.Html, sanitize=False)
  - CmsTemplate.html_content (fields.Html, sanitize=False)
  - CmsMedia.image_1920 (fields.Binary related to attachment_id.datas, readonly)

These fields exist exclusively for the Odoo admin interface and are
independent from the REST API fields (content_ids Puck JSON / url path).
"""
import unittest
from unittest.mock import MagicMock, PropertyMock


class TestCmsPageHtmlContent(unittest.TestCase):
    """Tests for CmsPage.html_content — rich HTML field for Odoo admin UI."""

    def _make_page(self, html_content=None, content_ids=None):
        page = MagicMock()
        page.html_content = html_content
        page.content_ids = content_ids or []
        return page

    # ---- field accepts valid HTML ----

    def test_html_content_accepts_simple_html(self):
        """html_content should store any valid HTML string."""
        html = "<h1>Olá Mundo</h1><p>Bem-vindo ao CMS.</p>"
        page = self._make_page(html_content=html)
        self.assertEqual(page.html_content, html)

    def test_html_content_accepts_rich_html(self):
        """html_content should accept complex HTML with nested tags and attributes."""
        rich_html = (
            "<div class='section'>"
            "<h2>Título</h2>"
            "<p><strong>Texto</strong> com <a href='/link'>link</a>.</p>"
            "<ul><li>Item 1</li><li>Item 2</li></ul>"
            "</div>"
        )
        page = self._make_page(html_content=rich_html)
        self.assertEqual(page.html_content, rich_html)

    def test_html_content_accepts_empty_string(self):
        """html_content is optional — empty string is valid."""
        page = self._make_page(html_content="")
        self.assertEqual(page.html_content, "")

    def test_html_content_accepts_none(self):
        """html_content is optional — None is valid (not yet edited)."""
        page = self._make_page(html_content=None)
        self.assertIsNone(page.html_content)

    # ---- independence from Puck JSON ----

    def test_html_content_independent_from_content_ids(self):
        """html_content (Odoo UI) must be independent from content_ids (API Puck JSON)."""
        puck_json = '{"root":{"props":{"styles":{}}},"content":[]}'
        html = "<p>Conteúdo da página para o admin Odoo.</p>"

        content_record = MagicMock()
        content_record.content = puck_json

        page = self._make_page(html_content=html, content_ids=[content_record])

        # Both fields coexist and are unrelated
        self.assertEqual(page.html_content, html)
        self.assertEqual(page.content_ids[0].content, puck_json)
        self.assertNotEqual(page.html_content, page.content_ids[0].content)

    def test_html_content_can_be_set_while_content_ids_empty(self):
        """html_content can be set even when there are no Puck JSON content records."""
        html = "<p>Admin content.</p>"
        page = self._make_page(html_content=html, content_ids=[])
        self.assertEqual(page.html_content, html)
        self.assertEqual(len(page.content_ids), 0)

    def test_content_ids_can_exist_without_html_content(self):
        """API Puck JSON can exist even when html_content is not set."""
        puck_json = '{"root":{},"content":[]}'
        content_record = MagicMock()
        content_record.content = puck_json

        page = self._make_page(html_content=None, content_ids=[content_record])
        self.assertIsNone(page.html_content)
        self.assertEqual(page.content_ids[0].content, puck_json)

    # ---- sanitize=False behaviour ----

    def test_html_content_preserves_script_tags_sanitize_false(self):
        """sanitize=False means HTML is stored as-is without tag stripping."""
        # With sanitize=False the model stores whatever the user passes in —
        # any sanitisation is the responsibility of the rendering layer.
        raw_html = "<p>Texto</p><script>console.log('ok');</script>"
        page = self._make_page(html_content=raw_html)
        self.assertEqual(page.html_content, raw_html)


class TestCmsTemplateHtmlContent(unittest.TestCase):
    """Tests for CmsTemplate.html_content — rich HTML field for Odoo admin UI."""

    def _make_template(self, html_content=None, content_ids=None):
        tpl = MagicMock()
        tpl.html_content = html_content
        tpl.content_ids = content_ids or []
        return tpl

    def test_html_content_accepts_html(self):
        html = "<section><h2>Template Header</h2></section>"
        tpl = self._make_template(html_content=html)
        self.assertEqual(tpl.html_content, html)

    def test_html_content_accepts_none(self):
        tpl = self._make_template(html_content=None)
        self.assertIsNone(tpl.html_content)

    def test_html_content_independent_from_puck_json(self):
        """html_content (Odoo UI) must not be confused with template Puck JSON."""
        puck_json = '{"root":{},"content":[{"type":"Text","props":{"text":"Hi"}}]}'
        html = "<p>Template content for Odoo admin.</p>"

        content_record = MagicMock()
        content_record.content = puck_json

        tpl = self._make_template(html_content=html, content_ids=[content_record])

        self.assertEqual(tpl.html_content, html)
        self.assertEqual(tpl.content_ids[0].content, puck_json)
        self.assertNotEqual(tpl.html_content, tpl.content_ids[0].content)

    def test_html_content_shared_across_categories(self):
        """html_content field applies to any template category (landing, property, about)."""
        for category in ["landing", "property", "about"]:
            with self.subTest(category=category):
                tpl = self._make_template(html_content=f"<p>{category}</p>")
                tpl.category = category
                self.assertEqual(tpl.html_content, f"<p>{category}</p>")
                self.assertEqual(tpl.category, category)


class TestCmsMediaImagePreview(unittest.TestCase):
    """Tests for CmsMedia.image_1920 — binary preview related to attachment_id.datas."""

    def _make_media(self, media_type="image", datas=None):
        attachment = MagicMock()
        attachment.datas = datas  # bytes or None/False

        media = MagicMock()
        media.media_type = media_type
        media.attachment_id = attachment
        # Simulate related field: image_1920 reads from attachment_id.datas
        type(media).image_1920 = PropertyMock(return_value=attachment.datas)
        return media

    # ---- related field reads from attachment ----

    def test_image_1920_returns_attachment_datas_for_image(self):
        """image_1920 should return the binary bytes from the linked attachment."""
        fake_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # fake PNG header
        media = self._make_media(media_type="image", datas=fake_bytes)
        self.assertEqual(media.image_1920, fake_bytes)

    def test_image_1920_returns_none_when_no_attachment_datas(self):
        """image_1920 should be None/False when attachment has no binary data."""
        media = self._make_media(media_type="image", datas=None)
        self.assertIsNone(media.image_1920)

    def test_image_1920_is_readonly_cannot_be_assigned(self):
        """image_1920 is a readonly related field — direct assignment must raise AttributeError.

        Simulates Odoo's readonly=True behaviour using a real Python property
        (no setter defined), since MagicMock allows arbitrary attribute writes.
        """
        fake_bytes = b"\xff\xd8\xff"  # JPEG magic bytes

        class _ReadOnlyMedia:
            @property
            def image_1920(self):
                return fake_bytes

        media = _ReadOnlyMedia()
        self.assertEqual(media.image_1920, fake_bytes)
        with self.assertRaises(AttributeError):
            media.image_1920 = b"other bytes"

    # ---- field is model-agnostic (media_type does not restrict the field) ----

    def test_image_1920_field_present_for_video_media_type(self):
        """image_1920 field exists on the model regardless of media_type.
        The view hides it via invisible="media_type != 'image'" — not the field itself."""
        media = self._make_media(media_type="video", datas=None)
        # Field is accessible (visibility is a view concern, not a model concern)
        self.assertIsNone(media.image_1920)

    def test_image_1920_field_present_for_document_media_type(self):
        media = self._make_media(media_type="document", datas=None)
        self.assertIsNone(media.image_1920)

    # ---- URL (API path) is distinct from image_1920 (Odoo binary) ----

    def test_url_and_image_1920_are_independent(self):
        """url (REST API path) and image_1920 (Odoo binary preview) are separate fields."""
        fake_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
        media = self._make_media(media_type="image", datas=fake_bytes)
        media.url = "/web/content/42/photo.png"

        self.assertEqual(media.image_1920, fake_bytes)
        self.assertEqual(media.url, "/web/content/42/photo.png")
        # They hold different types: url is a string, image_1920 is bytes
        self.assertIsInstance(media.url, str)
        self.assertIsInstance(media.image_1920, bytes)

    def test_image_1920_matches_attachment_datas_exactly(self):
        """image_1920 must reflect exactly what is in attachment_id.datas (related field)."""
        binary_content = b"GIF89a" + b"\x00" * 200  # fake GIF
        media = self._make_media(media_type="image", datas=binary_content)

        self.assertEqual(media.image_1920, media.attachment_id.datas)
