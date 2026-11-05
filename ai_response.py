"""LLM yanitlarini ayristirma ve dogrulama yardimcilari."""

import json
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

FALLBACK_CATEGORY = ["Diğer"]


def parse_json_response(text: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """Model yanitindaki JSON'u ayristirir; markdown citlerini temizler."""
    text = text.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse failed: %s\nRaw text: %s", exc, text[:500])
        return None


def validate_result(result: Any) -> Dict[str, Any]:
    """Kategori sonucunu beklenen semaya gore dogrular, gecersizi 'Diger'e indirir."""
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
