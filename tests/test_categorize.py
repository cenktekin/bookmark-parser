"""Kategori kurallarının kelime sınırı ile eşleştirilmesini doğrular.

Denetimde kanıtlanan hata: `keyword in text` substring eşleşmesi yüzünden
"gmail.com" -> "Yapay Zeka & Makine Ogrenmesi", "*.html" -> "..." gibi
yanlış kategoriler üretiliyordu.
"""

import unittest

from bookmark_organizer import categorize_link, path_exists
from categories import get_categories


class CategorizeLinkTests(unittest.TestCase):

    def setUp(self):
        self.categories = get_categories()

    def categorize(self, title, url):
        return categorize_link(title, url, self.categories)

    # --- T2 regresyon: substring eslesmesi -------------------------------- #

    def test_gmail_is_not_matched_as_ai(self):
        path = self.categorize("Gmail - Mail", "https://mail.google.com/mail/u/0/")
        self.assertNotIn("Yapay Zeka & Makine Öğrenmesi", path or [])

    def test_html_suffix_is_not_matched_as_ml(self):
        path = self.categorize("Rapor", "https://example.com/index.html")
        self.assertNotIn("Yapay Zeka & Makine Öğrenmesi", path or [])

    def test_trainline_is_not_matched_as_ai(self):
        path = self.categorize("Trainline", "https://www.trainline.eu/")
        self.assertNotIn("Yapay Zeka & Makine Öğrenmesi", path or [])

    def test_ai_keyword_matches_standalone_token(self):
        path = self.categorize("AI Tools", "https://example.com/ai")
        self.assertIn("Yapay Zeka & Makine Öğrenmesi", path or [])

    def test_short_keyword_requires_full_token(self):
        for keyword, text in (("ml", "html"), ("ai", "mail"), ("py", "python")):
            with self.subTest(keyword=keyword):
                self.assertNotIn(
                    "Yapay Zeka & Makine Öğrenmesi",
                    self.categorize(text, "https://example.com/x") or [],
                )

    # --- temel eslesmeler ------------------------------------------------ #

    def test_python_keyword(self):
        path = self.categorize("Python Dersleri", "https://yazbel.com/")
        self.assertEqual(path, ["Teknoloji & Yazılım", "Python"])

    def test_domain_keyword(self):
        path = self.categorize("Netflix", "https://www.netflix.com/browse")
        self.assertEqual(path, ["Film, Dizi & Sanat", "Film & Dizi Platformları"])

    def test_turkish_keyword_normalization(self):
        path = self.categorize("Yazılım Notları", "https://example.com/blog")
        self.assertIn("Teknoloji & Yazılım", path or [])

    def test_javascript_scheme_goes_to_broken_bucket(self):
        path = self.categorize("boş", "javascript:void(0)")
        self.assertEqual(path, ["Bozuk & Kontrol Edilecek"])

    def test_unmatched_returns_none(self):
        self.assertIsNone(self.categorize("qqqq zzzz", "https://example.com/qqq"))

    # --- T3: phantom kategori -------------------------------------------- #

    def test_youtube_tiyatro_path_exists(self):
        path = self.categorize("Tiyatro: Hamlet", "https://www.youtube.com/watch?v=abc")
        self.assertTrue(path_exists(path, self.categories))
        self.assertNotIn("Etkinlik & Sanat", path)

    def test_youtube_belgesel_path_exists(self):
        path = self.categorize("Belgesel: Doğa", "https://www.youtube.com/watch?v=abc")
        self.assertTrue(path_exists(path, self.categories))

    def test_youtube_gezi_path_exists(self):
        path = self.categorize("Gezi: İstanbul", "https://www.youtube.com/watch?v=abc")
        self.assertTrue(path_exists(path, self.categories))

    def test_path_exists_rejects_unknown_path(self):
        self.assertFalse(path_exists(["Olmayan Kategori"], self.categories))
        self.assertFalse(
            path_exists(["Film, Dizi & Sanat", "Olmayan Alt"], self.categories)
        )


if __name__ == "__main__":
    unittest.main()
