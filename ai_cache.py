"""URL bazli yer imi kategori onbellegi (TTL'li).

Anahtar, alan adi degil **normalize edilmis URL**'dir: ayni alan adindaki
farkli sayfalar ayri kayit tutar, ayni sayfanin izleme parametreli varyantlari
tek kayda duser. Kayitlar `CACHE_TTL_SECONDS` sonra gecersiz sayilir.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent.resolve()
CACHE_FILE = SCRIPT_DIR / ".ai_cache.json"

CACHE_TTL_SECONDS = 30 * 24 * 60 * 60
TRACKING_PARAMS = {"fbclid", "gclid", "igshid", "mc_cid", "mc_eid", "ref_src", "ref_url"}

_cache: Dict[str, Dict[str, Any]] = {}
_loaded = False


def _is_tracking_param(name: str) -> bool:
    """Izleme amacli sorgu parametresi mi?"""
    lowered = name.lower()
    return lowered.startswith("utm_") or lowered in TRACKING_PARAMS


def _is_expired(entry: Dict[str, Any], now: Optional[float] = None) -> bool:
    """Kaydin TTL'i gectiyse (veya eski semada, zaman damgasi yoksa) True."""
    stamp = entry.get("cached_at")
    if not isinstance(stamp, (int, float)):
        return True
    current = time.time() if now is None else now
    return current - stamp > CACHE_TTL_SECONDS


def load_cache() -> Dict[str, Dict[str, Any]]:
    """Onbellegi diskten yukler; suresi gecmis/eski semali kayitlari ayiklar."""
    global _cache, _loaded
    if _loaded:
        return _cache
    _loaded = True
    if not CACHE_FILE.exists():
        return _cache

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Cache load failed, starting fresh: %s", exc)
        _cache = {}
        return _cache

    if not isinstance(raw, dict):
        _cache = {}
        return _cache

    _cache = {
        key: value
        for key, value in raw.items()
        if isinstance(value, dict) and not _is_expired(value)
    }
    logger.info("Cache loaded: %d URLs", len(_cache))
    return _cache


def save_cache() -> None:
    """Onbellegi diske yazar; hata durumunda akisi bozmaz."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.warning("Cache save failed: %s", exc)


def get_domain(url: str) -> str:
    """URL'den alan adini cikarir (raporlama/olcum icin)."""
    try:
        parsed = urlparse(url)
        domain = (parsed.netloc or parsed.path.split("/")[0]).lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except (AttributeError, ValueError):
        return ""


def normalize_url(url: str) -> str:
    """Onbellek anahtari icin URL'yi sadelestirir.

    Semayi ve alan adini kucultur; `www.` onekini, parcayi (#...) ve izleme
    parametrelerini (`utm_*`, `fbclid` vb.) atar; kalan parametreleri siralar.
    Boylece ayni sayfanin etiketli varyantlari tek anahtara duser, farkli
    sayfalar ayri kalir.
    """
    raw = (url or "").strip()
    if not raw:
        return ""

    try:
        parsed = urlparse(raw)
    except ValueError:
        return get_domain(raw)

    if not parsed.netloc:
        return get_domain(raw)

    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    params = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_param(key)
    ]
    query = urlencode(sorted(params))
    return urlunparse((parsed.scheme.lower() or "https", host, parsed.path or "/", "", query, ""))


def cache_key(url: str) -> str:
    return normalize_url(url)


def get_cached(url: str) -> Optional[Dict[str, Any]]:
    """URL icin onbellek kaydini dondurur; suresi gecmisse None."""
    load_cache()
    key = cache_key(url)
    entry = _cache.get(key)
    if not entry:
        return None
    if _is_expired(entry):
        logger.debug("Cache expired: %s", key)
        _cache.pop(key, None)
        return None
    return entry


def set_cache(url: str, result: Dict[str, Any]) -> None:
    """URL icin kategori sonucunu zaman damgasiyla onbellege yazar."""
    load_cache()
    key = cache_key(url)
    if key:
        _cache[key] = {
            "category_path": result["category_path"],
            "confidence": result["confidence"],
            "cached_at": time.time(),
        }
        save_cache()


def cache_size() -> int:
    """Bellekteki URL sayisi."""
    return len(_cache)
