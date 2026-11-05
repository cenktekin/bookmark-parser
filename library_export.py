"""Kaynak Kutuphanesi disa aktarimi (JSON/CSV).

Cikti semasi blog-generator ile uyumludur:
    {kategori, alt_kategori, baslik, url, eklenme_tarihi}
"""

import csv
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from bookmark_organizer import categorize_link, extract_items, path_exists
from categories import get_categories

logger = logging.getLogger(__name__)

FALLBACK_CATEGORY = "Diğer"
CSV_FIELDS = ["kategori", "alt_kategori", "baslik", "url", "eklenme_tarihi"]


def _format_date(raw: str) -> str:
    """Bookmark ADD_DATE (epoch saniye/milisaniye) degerini YYYY-MM-DD'ye cevirir."""
    raw = (raw or "").strip()
    if not raw.isdigit():
        return ""
    try:
        value = int(raw)
        if len(raw) > 10:
            value //= 1000
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d")
    except (ValueError, OSError, OverflowError):
        return ""


def build_library_rows(
    items: List[Dict[str, str]],
    categories_def: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """Yer imi ogelerini Kaynak Kutuphanesi satirlarina donusturur."""
    if categories_def is None:
        categories_def = get_categories()

    rows: List[Dict[str, str]] = []

    for item in items:
        title = (item.get("title") or "").strip()
        url = item.get("url", "")
        path = categorize_link(title, url, categories_def)
        if not path or not path_exists(path, categories_def):
            path = [FALLBACK_CATEGORY]

        rows.append({
            "kategori": path[0],
            "alt_kategori": " > ".join(path[1:]),
            "baslik": title,
            "url": url,
            "eklenme_tarihi": _format_date(item.get("add_date", "")),
        })

    return rows


def _write_json(rows: List[Dict[str, str]], output_file: str) -> None:
    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)


def _write_csv(rows: List[Dict[str, str]], output_file: str) -> None:
    with open(output_file, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def export_library(
    input_file: str,
    output_file: str,
    categories_def: Optional[Dict[str, Any]] = None,
) -> int:
    """Yer imlerini kategori + metadata ile JSON veya CSV olarak disa aktarir.

    Format uzantidan secilir: `.csv` -> CSV, digerleri -> JSON.

    Returns:
        Yazilan satir sayisi.

    Raises:
        ValueError: Desteklenmeyen uzanti.
        OSError: Girdi/cikti dosyasi erisilemez.
    """
    extension = os.path.splitext(output_file)[1].lower()
    if extension not in (".json", ".csv"):
        raise ValueError(f"Desteklenmeyen uzanti: {extension or '(yok)'} — .json veya .csv kullanin")

    with open(input_file, "r", encoding="utf-8") as fh:
        content = fh.read()

    rows = build_library_rows(extract_items(content), categories_def)

    if extension == ".csv":
        _write_csv(rows, output_file)
    else:
        _write_json(rows, output_file)

    logger.info("Kaynak Kutuphanesi yazildi: %s (%d kayit)", output_file, len(rows))
    return len(rows)
