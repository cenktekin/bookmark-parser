"""AI kategorizasyon ciktisini HTML yapisina donusturen boru hatti."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ai_categorizer import CategorizeResult, categorize_batch
from bookmark_organizer import add_to_structure, path_exists

logger = logging.getLogger(__name__)


def _resolve_path(path: List[str], categories_def: Dict[str, Any]) -> Optional[List[str]]:
    """Verilen yolun en uzun gecerli onekini dondurur (hicbiri gecerli degilse None)."""
    if len(path) == 1 and " > " in path[0]:
        path = [part.strip() for part in path[0].split(" > ")]

    for end in range(len(path), 0, -1):
        candidate = list(path[:end])
        if path_exists(candidate, categories_def):
            return candidate
    return None


def categorize_items_with_ai(
    items: List[Dict[str, str]],
    categories_def: Optional[Dict[str, Any]] = None,
    batch_size: int = 10,
    use_cache: bool = True,
) -> Tuple[Dict[str, Any], int]:
    """Yer imi ogelerini AI ile kategorize edip ic ice yapiya yerlestirir.

    Returns:
        (yapi, eslesmeyen_sayisi) — tanimsiz yollar 'Diger' kovasina duser.
    """
    from categories import get_categories, list_category_paths

    if categories_def is None:
        categories_def = get_categories()

    results: List[CategorizeResult] = categorize_batch(
        [{"title": item.get("title", ""), "url": item.get("url", "")} for item in items],
        existing_categories=list_category_paths(categories_def),
        batch_size=batch_size,
        use_cache=use_cache,
    )

    structure: Dict[str, Any] = {}
    unmatched = 0

    for item, result in zip(items, results):
        resolved = _resolve_path(result.category_path, categories_def)
        if resolved:
            if resolved != result.category_path:
                logger.info("AI yolu kisaltildi: %s -> %s",
                            " > ".join(result.category_path), " > ".join(resolved))
            add_to_structure(structure, resolved, item)
        else:
            logger.warning("Tanimsiz AI kategori yolu '%s' -> 'Diğer'",
                           " > ".join(result.category_path))
            add_to_structure(structure, ["Diğer"], item)
            unmatched += 1

    return structure, unmatched
