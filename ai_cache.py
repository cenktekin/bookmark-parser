"""Alan adi bazli yer imi kategori onbellegi."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent.resolve()
CACHE_FILE = SCRIPT_DIR / ".ai_cache.json"

_cache: Dict[str, Dict[str, Any]] = {}


def load_cache() -> Dict[str, Dict[str, Any]]:
    """Onbellegi diskten yukler (bellekte varsa onu dondurur)."""
    global _cache
    if _cache:
        return _cache
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _cache = json.load(f)
            logger.info("Cache loaded: %d domains", len(_cache))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Cache load failed, starting fresh: %s", exc)
            _cache = {}
    return _cache


def save_cache() -> None:
    """Onbellegi diske yazar; hata durumunda akisi bozmaz."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.warning("Cache save failed: %s", exc)


def get_domain(url: str) -> str:
    """URL'den onbellek anahtari olarak kullanilacak alan adini cikarir."""
    try:
        parsed = urlparse(url)
        domain = (parsed.netloc or parsed.path.split("/")[0]).lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except (AttributeError, ValueError):
        return ""


def cache_key(url: str) -> str:
    return get_domain(url)


def get_cached(url: str) -> Optional[Dict[str, Any]]:
    """Alan adi icin onbellek kaydini dondurur."""
    load_cache()
    return _cache.get(cache_key(url))


def set_cache(url: str, result: Dict[str, Any]) -> None:
    """Alan adi icin kategori sonucunu onbellege yazar."""
    load_cache()
    key = cache_key(url)
    if key:
        _cache[key] = {
            "category_path": result["category_path"],
            "confidence": result["confidence"],
        }
        save_cache()


def cache_size() -> int:
    """Bellekteki alan adi sayisi."""
    return len(_cache)
