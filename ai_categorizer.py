"""ai_categorizer - Merkezi LLM gateway uzerinden yer imi kategorizasyonu.

Sagladigi yetenekler:
- Tekli ve toplu kategorizasyon
- URL bazli onbellek (TTL'li)
- Anahtar kelime tabanli yedek kategori
- Token/maliyet tahmini
- Kutuphane ve CLI kullanimi

Bilesenler: ai_gateway (HTTP + token), ai_prompts, ai_cache, ai_response,
ai_cli (komut satiri), ai_pipeline (yer imi -> yapi).

Gateway calisma kosulu:
    node D:\\projects\\shared\\llm\\llm.mjs serve
    (model ve anahtar Karargah'tan: http://127.0.0.1:9100)
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ai_cache import get_cached as _get_cached
from ai_cache import normalize_url as _normalize_url
from ai_cache import set_cache as _set_cache
from ai_gateway import (
    DEFAULT_MODEL,
    GATEWAY_URL,
    INPUT_TOKEN_COST,
    OUTPUT_TOKEN_COST,
    PROJECT,
    extract_token_usage as _extract_token_usage,
    get_token_usage,
    init_model as _init_model,
    is_available as is_ai_available,
    reset_token_usage,
)
from ai_prompts import (
    build_batch_prompt as _build_batch_prompt,
    build_categorize_prompt as _build_categorize_prompt,
    build_suggest_prompt as _build_suggest_prompt,
)
from ai_response import FALLBACK_CATEGORY
from ai_response import parse_json_response as _parse_json_response
from ai_response import validate_result as _validate_result

__all__ = [
    "CategorizeResult",
    "FALLBACK_CATEGORY",
    "DEFAULT_MODEL",
    "GATEWAY_URL",
    "PROJECT",
    "categorize_with_ai",
    "categorize_batch",
    "suggest_new_categories",
    "is_ai_available",
    "get_token_usage",
    "reset_token_usage",
]

logger = logging.getLogger(__name__)


@dataclass
class CategorizeResult:
    """AI kategorizasyon sonucu."""

    category_path: List[str]
    confidence: float
    reasoning: str
    is_new_category: bool = False
    from_cache: bool = False
    tokens_used: int = 0
    estimated_cost_usd: float = 0.0


def categorize_with_ai(
    title: str,
    url: str,
    existing_categories: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
    use_cache: bool = True,
    fallback_to_keyword: bool = True,
) -> CategorizeResult:
    """Tek bir yer imini AI ile kategorize eder.

    Args:
        title: Yer imi basligi
        url: Yer imi adresi
        existing_categories: Tercih edilecek mevcut kategori adlari
        api_key: (Kullanilmiyor) anahtar merkezi yapilandirmadan gelir
        model_name: (Kullanilmiyor) modeli merkez secer
        use_cache: URL onbellegi kullanilsin mi
        fallback_to_keyword: Hata durumunda anahtar kelime yedegine dusulsun mu

    Returns:
        CategorizeResult
    """
    if use_cache:
        cached = _get_cached(url)
        if cached:
            logger.debug("Cache hit for URL: %s", _normalize_url(url))
            return CategorizeResult(
                category_path=cached["category_path"],
                confidence=cached["confidence"],
                reasoning="From URL cache",
                from_cache=True,
            )

    try:
        model = _init_model(api_key, model_name)
        prompt = _build_categorize_prompt(title, url, existing_categories)
        response = model.generate_content(prompt, json_mode=True)

        tokens = _extract_token_usage(response)
        raw = _parse_json_response(response.text)
        validated = _validate_result(raw if isinstance(raw, dict) else {})

        result = CategorizeResult(
            category_path=validated["category_path"],
            confidence=validated["confidence"],
            reasoning=validated["reasoning"],
            is_new_category=validated["is_new_category"],
            tokens_used=tokens,
            estimated_cost_usd=round(
                tokens * (INPUT_TOKEN_COST + OUTPUT_TOKEN_COST) / 2, 6
            ),
        )

        if use_cache and result.confidence >= 0.5:
            _set_cache(url, {
                "category_path": result.category_path,
                "confidence": result.confidence,
            })

        return result

    except Exception as exc:
        logger.error("AI categorization failed for '%s': %s", title, exc)

        if fallback_to_keyword:
            return _keyword_fallback(title, url)

        return CategorizeResult(
            category_path=FALLBACK_CATEGORY,
            confidence=0.0,
            reasoning=f"AI error: {exc}",
        )


def categorize_batch(
    bookmarks: List[Dict[str, str]],
    existing_categories: Optional[List[str]] = None,
    batch_size: int = 10,
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
    use_cache: bool = True,
    fallback_to_keyword: bool = True,
) -> List[CategorizeResult]:
    """Birden fazla yer imini toplu olarak kategorize eder.

    Args:
        bookmarks: 'title' ve 'url' anahtarli sozluk listesi
        existing_categories: Mevcut kategori adlari
        batch_size: Istek basina yer imi sayisi
        api_key: (Kullanilmiyor) anahtar merkezi yapilandirmadan gelir
        model_name: (Kullanilmiyor) modeli merkez secer
        use_cache: URL onbellegi kullanilsin mi
        fallback_to_keyword: Hata durumunda anahtar kelime yedegine dusulsun mu

    Returns:
        Her yer imi icin bir CategorizeResult
    """
    results: List[Optional[CategorizeResult]] = []
    uncached_indices: List[int] = []
    uncached_bookmarks: List[Dict[str, str]] = []

    for i, bm in enumerate(bookmarks):
        if use_cache:
            cached = _get_cached(bm.get("url", ""))
            if cached:
                results.append(CategorizeResult(
                    category_path=cached["category_path"],
                    confidence=cached["confidence"],
                    reasoning="From URL cache",
                    from_cache=True,
                ))
                continue

        results.append(None)
        uncached_indices.append(i)
        uncached_bookmarks.append(bm)

    if not uncached_bookmarks:
        logger.info("All %d bookmarks served from cache", len(bookmarks))
        return [r for r in results if r is not None]

    logger.info(
        "Cache hit: %d, API needed: %d (batch size: %d)",
        len(bookmarks) - len(uncached_bookmarks),
        len(uncached_bookmarks),
        batch_size,
    )

    try:
        model = _init_model(api_key, model_name)
    except Exception as exc:
        logger.error("Model init failed: %s", exc)
        for position, idx in enumerate(uncached_indices):
            bm = uncached_bookmarks[position]
            if fallback_to_keyword:
                results[idx] = _keyword_fallback(bm.get("title", ""), bm.get("url", ""))
            else:
                results[idx] = CategorizeResult(
                    category_path=FALLBACK_CATEGORY,
                    confidence=0.0,
                    reasoning=f"Model init failed: {exc}",
                )
        return [r for r in results if r is not None]

    for batch_start in range(0, len(uncached_bookmarks), batch_size):
        batch_end = min(batch_start + batch_size, len(uncached_bookmarks))
        batch = uncached_bookmarks[batch_start:batch_end]
        batch_indices = uncached_indices[batch_start:batch_end]

        logger.info(
            "Processing batch %d-%d of %d",
            batch_start + 1,
            batch_end,
            len(uncached_bookmarks),
        )

        try:
            prompt = _build_batch_prompt(batch, existing_categories)
            response = model.generate_content(prompt, json_mode=True)
            tokens = _extract_token_usage(response)

            parsed = _parse_json_response(response.text)
            entries = parsed.get("results") if isinstance(parsed, dict) else parsed

            if isinstance(entries, list):
                _apply_batch_results(
                    entries, batch, batch_indices, results, tokens, use_cache,
                    existing_categories, api_key, model_name, fallback_to_keyword,
                )
            else:
                logger.warning("Batch response was not a list, falling back to individual calls")
                for position, idx in enumerate(batch_indices):
                    bm = batch[position]
                    results[idx] = categorize_with_ai(
                        bm.get("title", ""),
                        bm.get("url", ""),
                        existing_categories,
                        api_key,
                        model_name,
                        use_cache=False,
                        fallback_to_keyword=fallback_to_keyword,
                    )

        except Exception as exc:
            logger.error("Batch %d-%d failed: %s", batch_start + 1, batch_end, exc)
            for position, idx in enumerate(batch_indices):
                bm = batch[position]
                if fallback_to_keyword:
                    results[idx] = _keyword_fallback(bm.get("title", ""), bm.get("url", ""))
                else:
                    results[idx] = CategorizeResult(
                        category_path=FALLBACK_CATEGORY,
                        confidence=0.0,
                        reasoning=f"Batch error: {exc}",
                    )

    return [r for r in results if r is not None]


def _apply_batch_results(
    parsed: List[Any],
    batch: List[Dict[str, str]],
    batch_indices: List[int],
    results: List[Optional[CategorizeResult]],
    tokens: int,
    use_cache: bool,
    existing_categories: Optional[List[str]],
    api_key: Optional[str],
    model_name: str,
    fallback_to_keyword: bool,
) -> None:
    """Toplu yaniti sonuc listesine isler; eksik kayitlar icin tekil cagri yapar."""
    for position, idx in enumerate(batch_indices):
        if position < len(parsed):
            validated = _validate_result(parsed[position])
            result = CategorizeResult(
                category_path=validated["category_path"],
                confidence=validated["confidence"],
                reasoning=validated["reasoning"],
                is_new_category=validated["is_new_category"],
            )
        else:
            bm = batch[position]
            result = categorize_with_ai(
                bm.get("title", ""),
                bm.get("url", ""),
                existing_categories,
                api_key,
                model_name,
                use_cache=False,
                fallback_to_keyword=fallback_to_keyword,
            )

        if use_cache and result.confidence >= 0.5:
            _set_cache(
                batch[position].get("url", ""),
                {
                    "category_path": result.category_path,
                    "confidence": result.confidence,
                },
            )

        results[idx] = result

    per_bookmark_cost = round(
        tokens * (INPUT_TOKEN_COST + OUTPUT_TOKEN_COST) / 2 / len(batch), 6
    )
    for idx in batch_indices:
        result = results[idx]
        if result is not None:
            result.tokens_used = tokens // len(batch)
            result.estimated_cost_usd = per_bookmark_cost


def suggest_new_categories(
    bookmarks: List[Dict[str, str]],
    existing_categories: List[str],
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """Yer imlerine bakarak kategori yapisi iyilestirme onerileri uretir."""
    try:
        model = _init_model(api_key, model_name)
        prompt = _build_suggest_prompt(bookmarks, existing_categories)
        response = model.generate_content(prompt, json_mode=True)

        _extract_token_usage(response)
        parsed = _parse_json_response(response.text)

        if isinstance(parsed, dict):
            return parsed

        return {
            "suggested_new_categories": [],
            "suggested_renames": [],
            "suggested_merges": [],
            "analysis_summary": "Could not parse AI response",
        }

    except Exception as exc:
        logger.error("Category suggestion failed: %s", exc)
        return {
            "suggested_new_categories": [],
            "suggested_renames": [],
            "suggested_merges": [],
            "analysis_summary": f"Error: {exc}",
        }


def _keyword_fallback(title: str, url: str) -> CategorizeResult:
    """Anahtar kelime kurallariyla yedek kategori uretir."""
    try:
        from bookmark_organizer import categorize_link
        from categories import get_categories

        path = categorize_link(title, url, get_categories())
        if path:
            return CategorizeResult(
                category_path=path,
                confidence=0.6,
                reasoning="Keyword-based fallback",
            )
    except ImportError:
        logger.warning("bookmark_organizer not available for fallback")
    except Exception as exc:
        logger.warning("Keyword fallback error: %s", exc)

    return CategorizeResult(
        category_path=FALLBACK_CATEGORY,
        confidence=0.0,
        reasoning="No keyword match found",
    )


if __name__ == "__main__":
    import sys

    from ai_cli import main

    sys.exit(main())
