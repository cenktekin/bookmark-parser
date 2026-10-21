"""
ai_categorizer.py - Gemini AI-powered bookmark categorization module.

Uses Google Gemini API for intelligent bookmark categorization with:
- Single and batch categorization
- Domain-based caching
- Fallback to keyword-based categorization
- Cost estimation
- CLI and importable modes

Requirements:
    pip install google-generativeai

Usage:
    # As module
    from ai_categorizer import categorize_with_ai, categorize_batch, is_ai_available

    # CLI
    python ai_categorizer.py bookmarks.html --output categorized.json
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Union, Any
from urllib.parse import urlparse
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent.resolve()
CACHE_FILE = SCRIPT_DIR / ".ai_cache.json"
CONFIG_FILE = SCRIPT_DIR / ".ai_config.json"

DEFAULT_MODEL = "gemini-2.0-flash"
FALLBACK_CATEGORY = ["Diğer"]

INPUT_TOKEN_COST = 0.10 / 1_000_000
OUTPUT_TOKEN_COST = 0.40 / 1_000_000

_genai = None
_model = None
_cache: Dict[str, Dict[str, Any]] = {}
_token_tracker = None


@dataclass
class CategorizeResult:
    """Structured result from AI categorization."""
    category_path: List[str]
    confidence: float
    reasoning: str
    is_new_category: bool = False
    from_cache: bool = False
    tokens_used: int = 0
    estimated_cost_usd: float = 0.0


@dataclass
class TokenUsage:
    """Token usage tracking."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @property
    def estimated_cost_usd(self) -> float:
        return (
            self.prompt_tokens * INPUT_TOKEN_COST
            + self.completion_tokens * OUTPUT_TOKEN_COST
        )


def _get_token_tracker() -> TokenUsage:
    global _token_tracker
    if _token_tracker is None:
        _token_tracker = TokenUsage()
    return _token_tracker


def _lazy_import():
    global _genai
    if _genai is None:
        try:
            import google.generativeai as genai
            _genai = genai
        except ImportError:
            raise ImportError(
                "google-generativeai is required. "
                "Install it: pip install google-generativeai"
            )
    return _genai


def _load_cache() -> Dict[str, Dict[str, Any]]:
    global _cache
    if _cache:
        return _cache
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _cache = json.load(f)
            logger.info("Cache loaded: %d domains", len(_cache))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Cache load failed, starting fresh: %s", e)
            _cache = {}
    return _cache


def _save_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning("Cache save failed: %s", e)


def _get_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.lower()
    except Exception:
        return ""


def _cache_key(url: str) -> str:
    return _get_domain(url)


def _get_cached(url: str) -> Optional[Dict[str, Any]]:
    _load_cache()
    key = _cache_key(url)
    return _cache.get(key)


def _set_cache(url: str, result: Dict[str, Any]):
    _load_cache()
    key = _cache_key(url)
    if key:
        _cache[key] = {
            "category_path": result["category_path"],
            "confidence": result["confidence"],
        }
        _save_cache()


def _resolve_api_key(api_key: Optional[str] = None) -> Optional[str]:
    if api_key:
        return api_key

    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return cfg.get("api_key")
        except (json.JSONDecodeError, OSError):
            pass

    return None


def _init_model(api_key: Optional[str] = None, model_name: str = DEFAULT_MODEL):
    global _model
    if _model is not None:
        return _model

    genai = _lazy_import()
    key = _resolve_api_key(api_key)
    if not key:
        raise ValueError(
            "No Gemini API key found. Set GEMINI_API_KEY env var, "
            f"create {CONFIG_FILE} with {{\"api_key\": \"...\"}}, "
            "or pass --api-key argument."
        )

    genai.configure(api_key=key)
    _model = genai.GenerativeModel(model_name)
    logger.info("Gemini model initialized: %s", model_name)
    return _model


def _build_categorize_prompt(
    title: str,
    url: str,
    existing_categories: Optional[List[str]] = None,
) -> str:
    cat_section = ""
    if existing_categories:
        cat_json = json.dumps(existing_categories, ensure_ascii=False, indent=2)
        cat_section = f"""
You MUST choose from these existing categories (unless the bookmark clearly doesn't fit any):
{cat_json}

If the bookmark doesn't fit any existing category, suggest a NEW category.
"""
    else:
        cat_section = "Suggest the most appropriate category for this bookmark.\n"

    return f"""You are a bookmark categorization assistant. Categorize bookmarks into hierarchical paths.

{cat_section}

Bookmark to categorize:
- Title: {title}
- URL: {url}

Rules:
1. Category path should be hierarchical: ["Main Category", "Sub Category", ...]
2. Use the EXACT category names from the list above when possible
3. Confidence should be 0.0-1.0 based on how certain you are
4. Keep reasoning concise (1 sentence)
5. Set is_new_category=true only if you created a category NOT in the list

Respond with ONLY valid JSON (no markdown, no code blocks):
{{"category_path": ["Main", "Sub"], "confidence": 0.95, "reasoning": "brief explanation", "is_new_category": false}}"""


def _build_batch_prompt(
    bookmarks: List[Dict[str, str]],
    existing_categories: Optional[List[str]] = None,
) -> str:
    cat_section = ""
    if existing_categories:
        cat_json = json.dumps(existing_categories, ensure_ascii=False, indent=2)
        cat_section = f"Existing categories:\n{cat_json}\n"

    bookmarks_text = ""
    for i, bm in enumerate(bookmarks, 1):
        bookmarks_text += f"{i}. Title: {bm.get('title', '')}\n   URL: {bm.get('url', '')}\n\n"

    return f"""You are a bookmark categorization assistant. Categorize each bookmark into a hierarchical path.

{cat_section}

Bookmarks to categorize:
{bookmarks_text}

Rules:
1. Category path: ["Main", "Sub", ...]
2. Use EXACT category names from the list when possible
3. Confidence: 0.0-1.0
4. Keep reasoning concise (1 sentence per bookmark)
5. is_new_category=true only if category is NOT in the existing list

Respond with ONLY valid JSON array (no markdown, no code blocks):
[{{"category_path": ["Main", "Sub"], "confidence": 0.95, "reasoning": "explanation", "is_new_category": false}}, ...]"""


def _build_suggest_prompt(
    bookmarks: List[Dict[str, str]],
    existing_categories: List[str],
) -> str:
    sample_size = min(50, len(bookmarks))
    sample = bookmarks[:sample_size]

    bookmarks_text = ""
    for bm in sample:
        bookmarks_text += f"- {bm.get('title', '')} | {bm.get('url', '')}\n"

    return f"""You are a bookmark organization expert. Analyze these bookmarks and suggest improvements to the category structure.

Current categories:
{json.dumps(existing_categories, ensure_ascii=False, indent=2)}

Sample bookmarks ({sample_size} of {len(bookmarks)} total):
{bookmarks_text}

Suggest:
1. New categories that would better organize these bookmarks
2. Categories that should be merged or split
3. Better naming for existing categories

Respond with ONLY valid JSON (no markdown, no code blocks):
{{
  "suggested_new_categories": [
    {{"name": "Category Name", "parent": "Parent Category or null", "reason": "why"}}
  ],
  "suggested_renames": [
    {{"from": "Old Name", "to": "New Name", "reason": "why"}}
  ],
  "suggested_merges": [
    {{"categories": ["Cat1", "Cat2"], "into": "Merged Name", "reason": "why"}}
  ],
  "analysis_summary": "Overall analysis of bookmark structure"
}}"""


def _parse_json_response(text: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
    text = text.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("JSON parse failed: %s\nRaw text: %s", e, text[:500])
        return None


def _extract_token_usage(response) -> int:
    try:
        usage = response.usage_metadata
        if usage:
            total = getattr(usage, "total_token_count", 0) or 0
            prompt = getattr(usage, "prompt_token_count", 0) or 0
            completion = getattr(usage, "candidates_token_count", 0) or 0
            tracker = _get_token_tracker()
            tracker.prompt_tokens += prompt
            tracker.completion_tokens += completion
            tracker.total_tokens += total
            return total
    except Exception:
        pass
    return 0


def _validate_result(result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {
            "category_path": FALLBACK_CATEGORY,
            "confidence": 0.0,
            "reasoning": "Invalid response format",
            "is_new_category": False,
        }

    category_path = result.get("category_path", FALLBACK_CATEGORY)
    if not isinstance(category_path, list) or not category_path:
        category_path = FALLBACK_CATEGORY

    confidence = result.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    confidence = max(0.0, min(1.0, float(confidence)))

    reasoning = result.get("reasoning", "")
    if not isinstance(reasoning, str):
        reasoning = str(reasoning)

    is_new = result.get("is_new_category", False)
    if not isinstance(is_new, bool):
        is_new = False

    return {
        "category_path": category_path,
        "confidence": confidence,
        "reasoning": reasoning,
        "is_new_category": is_new,
    }


def is_ai_available(api_key: Optional[str] = None) -> bool:
    """
    Check if AI categorization is available.

    Returns True if google-generativeai is installed AND API key is configured.
    """
    try:
        _lazy_import()
    except ImportError:
        return False

    return _resolve_api_key(api_key) is not None


def get_token_usage() -> Dict[str, Any]:
    """Get current token usage statistics."""
    tracker = _get_token_tracker()
    return {
        "prompt_tokens": tracker.prompt_tokens,
        "completion_tokens": tracker.completion_tokens,
        "total_tokens": tracker.total_tokens,
        "estimated_cost_usd": round(tracker.estimated_cost_usd, 6),
    }


def reset_token_usage():
    """Reset token usage counter."""
    global _token_tracker
    _token_tracker = TokenUsage()


def categorize_with_ai(
    title: str,
    url: str,
    existing_categories: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
    use_cache: bool = True,
    fallback_to_keyword: bool = True,
) -> CategorizeResult:
    """
    Categorize a single bookmark using Gemini AI.

    Args:
        title: Bookmark title
        url: Bookmark URL
        existing_categories: List of existing category paths to prefer
        api_key: Gemini API key (overrides env var / config)
        model_name: Gemini model to use
        use_cache: Whether to use domain-based cache
        fallback_to_keyword: Whether to fall back to keyword categorization on error

    Returns:
        CategorizeResult with category_path, confidence, reasoning, etc.
    """
    if use_cache:
        cached = _get_cached(url)
        if cached:
            logger.debug("Cache hit for domain: %s", _get_domain(url))
            return CategorizeResult(
                category_path=cached["category_path"],
                confidence=cached["confidence"],
                reasoning="From domain cache",
                from_cache=True,
            )

    try:
        model = _init_model(api_key, model_name)
        prompt = _build_categorize_prompt(title, url, existing_categories)
        response = model.generate_content(prompt)

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

    except Exception as e:
        logger.error("AI categorization failed for '%s': %s", title, e)

        if fallback_to_keyword:
            return _keyword_fallback(title, url)

        return CategorizeResult(
            category_path=FALLBACK_CATEGORY,
            confidence=0.0,
            reasoning=f"AI error: {e}",
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
    """
    Categorize multiple bookmarks efficiently in batches.

    Args:
        bookmarks: List of dicts with 'title' and 'url' keys
        existing_categories: List of existing category paths
        batch_size: Number of bookmarks per API call
        api_key: Gemini API key
        model_name: Gemini model to use
        use_cache: Whether to use domain-based cache
        fallback_to_keyword: Whether to fall back on error

    Returns:
        List of CategorizeResult, one per bookmark
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
                    reasoning="From domain cache",
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
    except Exception as e:
        logger.error("Model init failed: %s", e)
        if fallback_to_keyword:
            for i, idx in enumerate(uncached_indices):
                bm = uncached_bookmarks[i]
                results[idx] = _keyword_fallback(bm.get("title", ""), bm.get("url", ""))
            return [r for r in results if r is not None]
        for idx in uncached_indices:
            results[idx] = CategorizeResult(
                category_path=FALLBACK_CATEGORY,
                confidence=0.0,
                reasoning=f"Model init failed: {e}",
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
            response = model.generate_content(prompt)
            tokens = _extract_token_usage(response)

            parsed = _parse_json_response(response.text)

            if isinstance(parsed, list):
                for i, idx in enumerate(batch_indices):
                    if i < len(parsed):
                        validated = _validate_result(parsed[i])
                        result = CategorizeResult(
                            category_path=validated["category_path"],
                            confidence=validated["confidence"],
                            reasoning=validated["reasoning"],
                            is_new_category=validated["is_new_category"],
                            tokens_used=0,
                        )
                    else:
                        result = CategorizeResult(
                            category_path=FALLBACK_CATEGORY,
                            confidence=0.0,
                            reasoning="Missing from batch response",
                        )

                    if use_cache and result.confidence >= 0.5:
                        _set_cache(
                            batch[i].get("url", ""),
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
                    r = results[idx]
                    if r is not None:
                        r.tokens_used = tokens // len(batch)
                        r.estimated_cost_usd = per_bookmark_cost

            else:
                logger.warning("Batch response was not a list, falling back to individual calls")
                for i, idx in enumerate(batch_indices):
                    bm = batch[i]
                    results[idx] = categorize_with_ai(
                        bm.get("title", ""),
                        bm.get("url", ""),
                        existing_categories,
                        api_key,
                        model_name,
                        use_cache=False,
                        fallback_to_keyword=fallback_to_keyword,
                    )

        except Exception as e:
            logger.error("Batch %d-%d failed: %s", batch_start + 1, batch_end, e)
            if fallback_to_keyword:
                for i, idx in enumerate(batch_indices):
                    bm = batch[i]
                    results[idx] = _keyword_fallback(bm.get("title", ""), bm.get("url", ""))
            else:
                for idx in batch_indices:
                    results[idx] = CategorizeResult(
                        category_path=FALLBACK_CATEGORY,
                        confidence=0.0,
                        reasoning=f"Batch error: {e}",
                    )

    return [r for r in results if r is not None]


def suggest_new_categories(
    bookmarks: List[Dict[str, str]],
    existing_categories: List[str],
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """
    Suggest improvements to category structure based on bookmark analysis.

    Args:
        bookmarks: List of dicts with 'title' and 'url' keys
        existing_categories: Current category structure (list of names)
        api_key: Gemini API key
        model_name: Gemini model to use

    Returns:
        dict with suggested_new_categories, suggested_renames,
        suggested_merges, analysis_summary
    """
    try:
        model = _init_model(api_key, model_name)
        prompt = _build_suggest_prompt(bookmarks, existing_categories)
        response = model.generate_content(prompt)

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

    except Exception as e:
        logger.error("Category suggestion failed: %s", e)
        return {
            "suggested_new_categories": [],
            "suggested_renames": [],
            "suggested_merges": [],
            "analysis_summary": f"Error: {e}",
        }


def _keyword_fallback(title: str, url: str) -> CategorizeResult:
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
    except Exception as e:
        logger.warning("Keyword fallback error: %s", e)

    return CategorizeResult(
        category_path=FALLBACK_CATEGORY,
        confidence=0.0,
        reasoning="No keyword match found",
    )


def _parse_bookmarks_html(html_path: str) -> List[Dict[str, str]]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("beautifulsoup4 is required: pip install beautifulsoup4")

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    bookmarks = []

    for link in soup.find_all("a"):
        title = link.text.strip()
        url = link.get("href", "")
        if title or url:
            bookmarks.append({"title": title, "url": url})

    return bookmarks


def _extract_top_categories(categories_def: Dict[str, Any]) -> List[str]:
    return list(categories_def.keys())


def _build_output_structure(
    bookmarks: List[Dict[str, str]],
    results: List[CategorizeResult]
) -> Dict[str, List[Dict[str, Any]]]:
    structure: Dict[str, List[Dict[str, Any]]] = {}

    for bm, result in zip(bookmarks, results):
        path = result.category_path if result else FALLBACK_CATEGORY
        key = " > ".join(path)
        if key not in structure:
            structure[key] = []
        structure[key].append({
            "title": bm.get("title", ""),
            "url": bm.get("url", ""),
            "confidence": result.confidence if result else 0.0,
            "reasoning": result.reasoning if result else "",
        })

    return structure


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI-powered bookmark categorization using Gemini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ai_categorizer.py bookmarks.html
  python ai_categorizer.py bookmarks.html --api-key YOUR_KEY --output result.json
  python ai_categorizer.py bookmarks.html --batch-size 20 --no-cache
        """,
    )
    parser.add_argument("input", help="Bookmarks HTML file to categorize")
    parser.add_argument("--api-key", help="Gemini API key (overrides GEMINI_API_KEY env)")
    parser.add_argument("--output", "-o", help="Output JSON file (default: stdout)")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for API calls (default: 10)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--no-cache", action="store_true", help="Disable domain caching")
    parser.add_argument("--no-fallback", action="store_true", help="Don't fall back to keyword categorization")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--check", action="store_true", help="Check if AI is available and exit")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    if args.check:
        available = is_ai_available(args.api_key)
        print(f"AI available: {available}")
        if available:
            print(f"Model: {args.model}")
            print(f"Cache file: {CACHE_FILE}")
        sys.exit(0 if available else 1)

    if not os.path.exists(args.input):
        logger.error("Input file not found: %s", args.input)
        sys.exit(1)

    logger.info("Parsing bookmarks from: %s", args.input)
    bookmarks = _parse_bookmarks_html(args.input)
    logger.info("Found %d bookmarks", len(bookmarks))

    if not bookmarks:
        logger.warning("No bookmarks found in file")
        sys.exit(0)

    existing_categories = None
    try:
        from categories import get_categories
        existing_categories = _extract_top_categories(get_categories())
    except ImportError:
        logger.warning("categories module not found, AI will suggest categories freely")

    logger.info("Starting AI categorization (batch size: %d)...", args.batch_size)
    results = categorize_batch(
        bookmarks=bookmarks,
        existing_categories=existing_categories,
        batch_size=args.batch_size,
        api_key=args.api_key,
        model_name=args.model,
        use_cache=not args.no_cache,
        fallback_to_keyword=not args.no_fallback,
    )

    output = _build_output_structure(bookmarks, results)

    token_info = get_token_usage()
    metadata = {
        "total_bookmarks": len(bookmarks),
        "total_categories": len(output),
        "token_usage": token_info,
        "model": args.model,
        "cached_domains": len(_cache),
    }

    result_payload = {
        "metadata": metadata,
        "categories": output,
    }

    json_output = json.dumps(result_payload, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_output)
        logger.info("Results written to: %s", args.output)
    else:
        print(json_output)

    logger.info("=== SUMMARY ===")
    logger.info("Bookmarks processed: %d", len(bookmarks))
    logger.info("Categories used: %d", len(output))
    logger.info("Token usage: %s", token_info)


if __name__ == "__main__":
    main()
