"""Kaynak Kutuphanesi disa aktarim testleri."""

import csv
import json
import os
import re
import tempfile
import unittest

from library_export import CSV_FIELDS, build_library_rows, export_library


SAMPLE_HTML = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<DL><p>
    <DT><A HREF="https://www.reuters.com/" ADD_DATE="0">Reuters</A>
    <DT><A HREF="https://yazbel.com/python-temelleri" ADD_DATE="1700000000">Python Dersleri</A>
    <DT><A HREF="https://qqqq-zzz.example.org/bilinmeyen">Bilinmeyen Site</A>
</DL><p>
"""


def _write_sample(tmp):
    path = os.path.join(tmp, "bookmarks.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(SAMPLE_HTML)
    return path


class BuildRowsTests(unittest.TestCase):

    def test_rows_follow_blog_generator_schema(self):
        from bookmark_organizer import extract_items

        rows = build_library_rows(extract_items(SAMPLE_HTML))
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(set(row.keys()), set(CSV_FIELDS))

    def test_category_and_subcategory_are_split(self):
        from bookmark_organizer import extract_items

        rows = build_library_rows(extract_items(SAMPLE_HTML))
        by_url = {row["url"]: row for row in rows}
        reuters = by_url["https://www.reuters.com/"]
        self.assertEqual(reuters["kategori"], "Kültür & Yaşam")
        self.assertEqual(reuters["alt_kategori"], "Haber, Blog & Makale")

    def test_unmatched_goes_to_other_bucket(self):
        from bookmark_organizer import extract_items

        rows = build_library_rows(extract_items(SAMPLE_HTML))
        by_url = {row["url"]: row for row in rows}
        other = by_url["https://qqqq-zzz.example.org/bilinmeyen"]
        self.assertEqual(other["kategori"], "Diğer")
        self.assertEqual(other["alt_kategori"], "")

    def test_dates_are_yyyy_mm_dd_or_empty(self):
        from bookmark_organizer import extract_items

        rows = build_library_rows(extract_items(SAMPLE_HTML))
        for row in rows:
            value = row["eklenme_tarihi"]
            self.assertTrue(value == "" or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value), value)


class ExportTests(unittest.TestCase):

    def test_json_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_path = _write_sample(tmp)
            out_path = os.path.join(tmp, "kutuphane.json")
            count = export_library(html_path, out_path)
            self.assertEqual(count, 3)
            with open(out_path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(len(data), 3)
            self.assertEqual(data[0]["kategori"], "Kültür & Yaşam")

    def test_csv_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_path = _write_sample(tmp)
            out_path = os.path.join(tmp, "kutuphane.csv")
            count = export_library(html_path, out_path)
            self.assertEqual(count, 3)
            with open(out_path, encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 3)
            self.assertEqual(list(rows[0].keys()), CSV_FIELDS)

    def test_unsupported_extension_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            html_path = _write_sample(tmp)
            with self.assertRaises(ValueError):
                export_library(html_path, os.path.join(tmp, "kutuphane.xml"))


if __name__ == "__main__":
    unittest.main()
