"""Kategori yapilandirmasi okuma/yazma ve varsayilan dosya yollari."""

import json
import logging
import os
from typing import Any, Dict, Optional

from categories import get_categories, set_categories

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(SCRIPT_DIR, "categories_config.json")
DEFAULT_INPUT = os.path.join(SCRIPT_DIR, "bookmarks.html")
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "bookmarks_organized.html")


def load_categories_config(filename: str) -> bool:
    """Verilen JSON dosyasindan kategori yapilandirmasini yukler.

    Dosya bulunamazsa veya bozuksa dahili varsayilanlar kullanilmaya devam eder.
    """
    if not filename or not os.path.isfile(filename):
        return False

    try:
        with open(filename, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Yapilandirma okunamadi (%s): %s", filename, exc)
        return False

    if not isinstance(loaded, dict) or not loaded:
        logger.error("Yapilandirma gecersiz (bos veya nesne degil): %s", filename)
        return False

    set_categories(loaded)
    logger.info("Yapilandirma yuklendi: %s", filename)
    return True


def save_categories_config(filename: str, categories_def: Optional[Dict[str, Any]] = None) -> bool:
    """Kategori yapilandirmasini JSON dosyasina yazar.

    Yalnizca `--export-config` bayragi ile cagrilir; hicbir kosulda otomatik
    olarak tetiklenmez (kullanicinin duzenlemeleri ezilmez).
    """
    data = categories_def if categories_def is not None else get_categories()
    try:
        with open(filename, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.error("Yapilandirma yazilamadi (%s): %s", filename, exc)
        return False
    logger.info("Yapilandirma kaydedildi: %s", filename)
    return True
