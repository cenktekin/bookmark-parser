"""ai_categorizer komut satiri arayuzu."""

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List

from ai_cache import CACHE_FILE, cache_size
from ai_categorizer import (
    CategorizeResult,
    DEFAULT_MODEL,
    FALLBACK_CATEGORY,
    GATEWAY_URL,
    PROJECT,
    categorize_batch,
    get_token_usage,
    is_ai_available,
)

logger = logging.getLogger(__name__)


def parse_bookmarks_html(html_path: str) -> List[Dict[str, str]]:
    """HTML dosyasindan baslik/adres ciftlerini cikarir."""
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise ImportError("beautifulsoup4 is required: pip install beautifulsoup4") from exc

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


def build_output_structure(
    bookmarks: List[Dict[str, str]],
    results: List[CategorizeResult],
) -> Dict[str, List[Dict[str, Any]]]:
    """Sonuclari kategori yolu -> yer imi listesi seklinde gruplar."""
    structure: Dict[str, List[Dict[str, Any]]] = {}

    for bm, result in zip(bookmarks, results):
        path = result.category_path if result else FALLBACK_CATEGORY
        key = " > ".join(path)
        structure.setdefault(key, []).append({
            "title": bm.get("title", ""),
            "url": bm.get("url", ""),
            "confidence": result.confidence if result else 0.0,
            "reasoning": result.reasoning if result else "",
        })

    return structure


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI-powered bookmark categorization via the central LLM gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ai_categorizer.py bookmarks.html
  python ai_categorizer.py bookmarks.html --output result.json
  python ai_categorizer.py bookmarks.html --batch-size 20 --no-cache

Gateway: http://127.0.0.1:7799 (LLM_GATEWAY_URL ile degistirilebilir).
Model ve anahtar Karargah'tan secilir: http://127.0.0.1:9100
        """,
    )
    parser.add_argument("input", nargs="?", help="Bookmarks HTML file to categorize")
    parser.add_argument("--api-key", help="(Kullanilmiyor) anahtar merkezde")
    parser.add_argument("--output", "-o", help="Output JSON file (default: stdout)")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="Batch size for API calls (default: 10)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help="(Kullanilmiyor) modeli merkez secer")
    parser.add_argument("--no-cache", action="store_true", help="Disable URL caching")
    parser.add_argument("--no-fallback", action="store_true",
                        help="Don't fall back to keyword categorization")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--check", action="store_true",
                        help="Check gateway availability and exit")
    return parser


def main(argv: List[str] = None) -> int:
    """CLI giris noktasi."""
    args = _build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    if args.check:
        available = is_ai_available(args.api_key)
        print(f"AI available: {available}")
        print(f"Gateway: {GATEWAY_URL} (proje: {PROJECT})")
        if available:
            print(f"Cache file: {CACHE_FILE}")
        return 0 if available else 1

    if not args.input:
        logger.error("Input file is required")
        return 2

    if not os.path.exists(args.input):
        logger.error("Input file not found: %s", args.input)
        return 1

    logger.info("Parsing bookmarks from: %s", args.input)
    bookmarks = parse_bookmarks_html(args.input)
    logger.info("Found %d bookmarks", len(bookmarks))

    if not bookmarks:
        logger.warning("No bookmarks found in file")
        return 0

    existing_categories = None
    try:
        from categories import get_categories, list_category_paths
        existing_categories = list_category_paths(get_categories())
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

    output = build_output_structure(bookmarks, results)

    token_info = get_token_usage()
    metadata = {
        "total_bookmarks": len(bookmarks),
        "total_categories": len(output),
        "token_usage": token_info,
        "model": args.model,
        "cached_urls": cache_size(),
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
