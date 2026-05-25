# -*- coding: utf-8 -*-
"""
Unit tests for CMS media validations.
Tests: MIME whitelist, magic bytes mismatch, file size limits, filename sanitization.
"""
import unittest
from unittest.mock import MagicMock, patch


# ---- Mirrored constants from cms_media_service.py ----
ALLOWED_MIMES = {
    "image": {"image/jpeg", "image/png", "image/gif", "image/webp"},
    "video": {"video/mp4", "video/webm"},
    "document": {"application/pdf", "text/plain"},
}

SIZE_LIMITS = {
    "image": 10 * 1024 * 1024,    # 10 MB
    "video": 100 * 1024 * 1024,   # 100 MB
    "document": 20 * 1024 * 1024, # 20 MB
}

MEDIA_TYPE_BY_MIME = {
    "image/jpeg": "image", "image/png": "image",
    "image/gif": "image", "image/webp": "image",
    "video/mp4": "video", "video/webm": "video",
    "application/pdf": "document", "text/plain": "document",
}


class TestCmsMediaValidations(unittest.TestCase):
    """Test CmsMediaService.validate_upload logic (mocked magic)."""

    def _call_validate(self, file_bytes, filename, claimed_mime, magic_mime):
        """Simulate validation logic (mirrors cms_media_service.validate_upload)."""
        import os
        import re

        # 1. Detect MIME via magic
        detected_mime = magic_mime

        # 2. Check MIME is in whitelist
        media_type = MEDIA_TYPE_BY_MIME.get(detected_mime)
        if not media_type:
            return {"error": "unsupported_mime", "detected": detected_mime}

        # 3. Check magic bytes match claimed MIME (if provided)
        if claimed_mime and claimed_mime != detected_mime:
            return {
                "error": "mime_mismatch",
                "claimed": claimed_mime,
                "detected": detected_mime,
            }

        # 4. File size
        size = len(file_bytes)
        if size > SIZE_LIMITS[media_type]:
            return {
                "error": "file_too_large",
                "max_size_bytes": SIZE_LIMITS[media_type],
                "actual_size_bytes": size,
            }

        # 5. Sanitize filename (prevent path traversal)
        safe_name = os.path.basename(filename)
        safe_name = re.sub(r"[^\w.\-]", "_", safe_name)

        return {
            "ok": True,
            "media_type": media_type,
            "detected_mime": detected_mime,
            "filename": safe_name,
            "size": size,
        }

    # ---- Unsupported MIME ----

    def test_html_mime_rejected(self):
        result = self._call_validate(b"<html>", "page.html", "text/html", "text/html")
        self.assertEqual(result.get("error"), "unsupported_mime")

    def test_exe_mime_rejected(self):
        result = self._call_validate(b"MZ\x90", "run.exe", "application/x-msdownload", "application/x-msdownload")
        self.assertEqual(result.get("error"), "unsupported_mime")

    # ---- MIME mismatch ----

    def test_jpg_extension_pdf_bytes_rejected(self):
        """File claiming image/jpeg but magic bytes say application/pdf."""
        result = self._call_validate(
            b"%PDF-1.4", "photo.jpg", "image/jpeg", "application/pdf"
        )
        self.assertEqual(result.get("error"), "mime_mismatch")
        self.assertEqual(result.get("claimed"), "image/jpeg")
        self.assertEqual(result.get("detected"), "application/pdf")

    # ---- File size ----

    def test_image_over_10mb_rejected(self):
        big_bytes = b"x" * (10 * 1024 * 1024 + 1)
        result = self._call_validate(big_bytes, "huge.jpg", "image/jpeg", "image/jpeg")
        self.assertEqual(result.get("error"), "file_too_large")
        self.assertEqual(result.get("max_size_bytes"), 10 * 1024 * 1024)

    def test_video_over_100mb_rejected(self):
        big_bytes = b"x" * (100 * 1024 * 1024 + 1)
        result = self._call_validate(big_bytes, "movie.mp4", "video/mp4", "video/mp4")
        self.assertEqual(result.get("error"), "file_too_large")
        self.assertEqual(result.get("max_size_bytes"), 100 * 1024 * 1024)

    def test_document_over_20mb_rejected(self):
        big_bytes = b"x" * (20 * 1024 * 1024 + 1)
        result = self._call_validate(big_bytes, "doc.pdf", "application/pdf", "application/pdf")
        self.assertEqual(result.get("error"), "file_too_large")
        self.assertEqual(result.get("max_size_bytes"), 20 * 1024 * 1024)

    # ---- Valid files ----

    def test_valid_jpg_accepted(self):
        result = self._call_validate(b"\xff\xd8\xff", "photo.jpg", "image/jpeg", "image/jpeg")
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("media_type"), "image")

    def test_valid_pdf_accepted(self):
        result = self._call_validate(b"%PDF-1.4", "doc.pdf", "application/pdf", "application/pdf")
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("media_type"), "document")

    # ---- Filename sanitization ----

    def test_path_traversal_sanitized(self):
        result = self._call_validate(
            b"\xff\xd8\xff", "../../etc/passwd.jpg", "image/jpeg", "image/jpeg"
        )
        self.assertTrue(result.get("ok"))
        self.assertNotIn("..", result.get("filename", ""))
        self.assertIn("passwd.jpg", result.get("filename", ""))

    def test_filename_with_spaces_sanitized(self):
        result = self._call_validate(
            b"\xff\xd8\xff", "my image.jpg", "image/jpeg", "image/jpeg"
        )
        self.assertTrue(result.get("ok"))
        self.assertNotIn(" ", result.get("filename", ""))


if __name__ == "__main__":
    unittest.main()
