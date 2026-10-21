"""Boru hattı, yapılandırma yönetimi ve Markdown çıktısı testleri."""

import json
import os
import tempfile
import unittest

import bookmark_organizer
from bookmark_organizer import (
    categorize_items,
    load_categories_config,
    save_categories_config,
    write_unmatched_report,
)
from categories import get_categories, set_categories
from converter import convert_to_markdown


SAMPLE_HTML = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<DL><p>
    <DT><A HREF="https://mail.google.com/mail/u/0/" ADD_DATE="1">Gmail</A>
    <DT><A HREF="https://yazbel.com/python-temelleri">Python Dersleri</A>
    <DT><A HREF="https://qqqq-zzz.example.org/bilinmeyen">Bilinmeyen Site</A>
</DL><p>
"""


class ConfigTests(unittest.TestCase):

    def setUp(self):
        self.original = get_categories()

    def tearDown(self):
        set_categories(self.original)

    def test_export_and_reload_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cfg.json")
            self.assertTrue(save_categories_config(path))
            self.assertTrue(load_categories_config(path))
            self.assertEqual(get_categories(), self.original)

    def test_load_rejects_invalid_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "broken.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("{ not json")
            self.assertFalse(load_categories_config(path))
            self.assertEqual(get_categories(), self.original)

    def test_load_missing_file_keeps_defaults(self):
        self.assertFalse(load_categories_config(os.path.join("yok", "cfg.json")))
        self.assertEqual(get_categories(), self.original)

    def test_custom_config_is_applied(self):
        custom = {"Benim Kategorim": ["ozel"]}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cfg.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(custom, fh, ensure_ascii=False)
            self.assertTrue(load_categories_config(path))
            structure, unmatched = categorize_items(
                [{"type": "link", "title": "Ozel", "url": "https://x.test/ozel"}]
            )
            self.assertIn("Benim Kategorim", structure)
            self.assertEqual(len(unmatched), 0)


class CategorizeItemsTests(unittest.TestCase):

    def test_unmatched_links_are_collected(self):
        items = bookmark_organizer.extract_items(SAMPLE_HTML)
        structure, unmatched = categorize_items(items)
        self.assertEqual(len(items), 3)
        # Gmail artık "ai" ile eslesmiyor; Bilinmeyen Site de eslesmiyor.
        self.assertEqual(len(unmatched), 2)
        self.assertIn("Diğer", structure)
        unmatched_urls = {item["url"] for item in unmatched}
        self.assertIn("https://qqqq-zzz.example.org/bilinmeyen", unmatched_urls)
        self.assertIn("https://mail.google.com/mail/u/0/", unmatched_urls)

    def test_matched_links_do_not_land_in_other(self):
        items = bookmark_organizer.extract_items(SAMPLE_HTML)
        structure, _ = categorize_items(items)
        self.assertIn("Teknoloji & Yazılım", structure)
        ai_items = structure.get("Yapay Zeka & Makine Öğrenmesi", {}).get("__items__", [])
        ai_urls = {item["url"] for item in ai_items}
        self.assertNotIn("https://mail.google.com/mail/u/0/", ai_urls)


class ReportTests(unittest.TestCase):

    def test_unmatched_report_is_written(self):
        items = bookmark_organizer.extract_items(SAMPLE_HTML)
        _, unmatched = categorize_items(items)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.txt")
            write_unmatched_report(unmatched, path)
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("Bilinmeyen Site", content)
            self.assertIn("Toplam: 2", content)


class MarkdownTests(unittest.TestCase):

    def test_markdown_contains_category_headings(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_path = os.path.join(tmp, "bookmarks.html")
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(SAMPLE_HTML)
            md_path = convert_to_markdown(html_path)
            with open(md_path, encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("# Organized Bookmarks", content)
            self.assertIn("Teknoloji & Yazılım", content)
            self.assertIn("yazbel.com", content)


class RunDoesNotOverwriteConfigTests(unittest.TestCase):
    """T5 regresyonu: program calistiginda config dosyasi ezilmemeli."""

    def test_config_file_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "categories_config.json")
            custom = {"Ozel Kategori": ["ozel"]}
            with open(cfg_path, "w", encoding="utf-8") as fh:
                json.dump(custom, fh, ensure_ascii=False)

            html_path = os.path.join(tmp, "bookmarks.html")
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(SAMPLE_HTML)
            out_path = os.path.join(tmp, "out.html")

            original_categories = get_categories()
            try:
                load_categories_config(cfg_path)
                bookmark_organizer.main(input_file=html_path, output_file=out_path)
            finally:
                set_categories(original_categories)

            with open(cfg_path, encoding="utf-8") as fh:
                self.assertEqual(json.load(fh), custom)
            self.assertTrue(os.path.isfile(out_path))


if __name__ == "__main__":
    unittest.main()
