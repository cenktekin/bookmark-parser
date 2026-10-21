"""Türkçe karakter normalizasyonu ve kelime sınırı eşleştirme testleri."""

import unittest

from normalize import (
    extract_domain,
    match_any_keyword,
    match_keyword,
    normalize_text,
    normalize_url,
)


class NormalizeTextTests(unittest.TestCase):

    def test_lowercases(self):
        self.assertEqual(normalize_text("MERHABA"), "merhaba")

    def test_turkish_characters(self):
        self.assertEqual(normalize_text("Çğıöşü"), "cgiosu")
        self.assertEqual(normalize_text("İstanbul"), "istanbul")

    def test_collapses_whitespace(self):
        self.assertEqual(normalize_text("  fazla   bosluk  "), "fazla bosluk")

    def test_empty_input(self):
        self.assertEqual(normalize_text(""), "")


class MatchKeywordTests(unittest.TestCase):

    def test_word_boundary_blocks_substring(self):
        self.assertFalse(match_keyword("Gmail", "ai"))
        self.assertFalse(match_keyword("index.html", "ml"))
        self.assertFalse(match_keyword("cart", "art"))
        self.assertFalse(match_keyword("python", "py"))

    def test_word_boundary_allows_token(self):
        self.assertTrue(match_keyword("Python Dersleri", "python"))
        self.assertTrue(match_keyword("Yazılım", "yazılım"))
        self.assertTrue(match_keyword("node.js nedir", "node.js"))

    def test_scheme_keyword_with_punctuation(self):
        self.assertTrue(match_keyword("javascript:void(0)", "javascript:"))

    def test_empty_inputs(self):
        self.assertFalse(match_keyword("", "ai"))
        self.assertFalse(match_keyword("ai", ""))

    def test_match_any_keyword_returns_first_hit(self):
        matched = match_any_keyword("Python ve Django", ["django", "python"])
        self.assertEqual(matched, "django")

    def test_match_any_keyword_returns_none(self):
        self.assertIsNone(match_any_keyword("Merhaba", ["python", "django"]))


class UrlHelpersTests(unittest.TestCase):

    def test_normalize_url_adds_scheme(self):
        self.assertEqual(normalize_url("example.com"), "https://example.com")

    def test_normalize_url_lowercases_host(self):
        self.assertEqual(normalize_url("https://Example.com/path/"), "https://example.com/path")
        self.assertEqual(normalize_url("https://Example.com/"), "https://example.com/")

    def test_extract_domain(self):
        self.assertEqual(extract_domain("https://www.example.com/path"), "example.com")
        self.assertEqual(extract_domain("http://blog.example.com:8080/page"), "blog.example.com")


if __name__ == "__main__":
    unittest.main()
