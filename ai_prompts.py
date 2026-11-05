"""Yer imi kategorizasyonu icin LLM istemleri."""

import json
from typing import Dict, List, Optional


def build_categorize_prompt(
    title: str,
    url: str,
    existing_categories: Optional[List[str]] = None,
) -> str:
    """Tek bir yer imi icin kategorizasyon istemi uretir."""
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


def build_batch_prompt(
    bookmarks: List[Dict[str, str]],
    existing_categories: Optional[List[str]] = None,
) -> str:
    """Birden fazla yer imi icin toplu kategorizasyon istemi uretir."""
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

Respond with ONLY valid JSON object (no markdown, no code blocks):
{{"results": [{{"category_path": ["Main", "Sub"], "confidence": 0.95, "reasoning": "explanation", "is_new_category": false}}, ...]}}"""


def build_suggest_prompt(
    bookmarks: List[Dict[str, str]],
    existing_categories: List[str],
) -> str:
    """Kategori yapisini iyilestirme onerileri icin istem uretir."""
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
