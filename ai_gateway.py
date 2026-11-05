"""Merkezi LLM gateway istemcisi ve token muhasebesi.

Model ve API anahtari Karargah tarafindan yonetilir; bu modul yalnizca
OpenAI uyumlu ``/v1/chat/completions`` ucunu cagirir. Boylece projede
saglayici SDK'si (google-generativeai vb.) bulunmaz.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://127.0.0.1:7799")
PROJECT = "bookmark-parser"
GATEWAY_TIMEOUT = 120.0
# Toplu yanitlar (10 yer imi ~ 600 token) akil yurutme tokenlariyla birlikte
# 2000 sinirina takilip bos icerik donebiliyor; 4096 guvenli taban.
MAX_TOKENS = 4096

DEFAULT_MODEL = "central"

INPUT_TOKEN_COST = 0.10 / 1_000_000
OUTPUT_TOKEN_COST = 0.40 / 1_000_000

_model: Optional["GatewayModel"] = None
_token_tracker: Optional["TokenUsage"] = None


@dataclass
class TokenUsage:
    """Token kullanim sayaci."""

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


def extract_token_usage(response: Any) -> int:
    """Yanittaki kullanim bilgisini sayaca isler ve toplam token'i dondurur."""
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
    except (AttributeError, TypeError):
        pass
    return 0


def get_token_usage() -> Dict[str, Any]:
    """Guncel token kullanim istatistiklerini dondurur."""
    tracker = _get_token_tracker()
    return {
        "prompt_tokens": tracker.prompt_tokens,
        "completion_tokens": tracker.completion_tokens,
        "total_tokens": tracker.total_tokens,
        "estimated_cost_usd": round(tracker.estimated_cost_usd, 6),
    }


def reset_token_usage() -> None:
    """Token sayacini sifirlar."""
    global _token_tracker
    _token_tracker = TokenUsage()


class GatewayResponse:
    """OpenAI uyumlu yaniti, eski Gemini yanit arayuzune uyarlar."""

    def __init__(
        self,
        text: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        self.text = text
        self.usage_metadata = SimpleNamespace(
            total_token_count=prompt_tokens + completion_tokens,
            prompt_token_count=prompt_tokens,
            candidates_token_count=completion_tokens,
        )


class GatewayModel:
    """Merkezi gateway'e giden, ``generate_content`` arayuzunu taklit eden istemci."""

    def generate_content(self, prompt: str, json_mode: bool = False) -> GatewayResponse:
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": MAX_TOKENS,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        request = urllib.request.Request(
            f"{GATEWAY_URL}/v1/chat/completions?project={PROJECT}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=GATEWAY_TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"LLM gateway hatasi (HTTP {exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"LLM gateway'e ulasilamadi ({GATEWAY_URL}). "
                "node D:\\projects\\shared\\llm\\llm.mjs serve"
            ) from exc

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("LLM yanitinda choices[0].message.content yok") from exc

        usage = data.get("usage") or {}
        return GatewayResponse(
            str(text or ""),
            int(usage.get("prompt_tokens") or 0),
            int(usage.get("completion_tokens") or 0),
        )


def init_model(api_key: Optional[str] = None, model_name: Optional[str] = None) -> GatewayModel:
    """Singleton gateway istemcisi dondurur.

    ``api_key`` ve ``model_name`` geriye donuk uyumluluk icin kabul edilir;
    model ve anahtar merkezi yapilandirmadan gelir.
    """
    global _model
    if _model is None:
        _model = GatewayModel()
        logger.info("Central LLM gateway configured: %s (proje: %s)", GATEWAY_URL, PROJECT)
    return _model


def is_available(api_key: Optional[str] = None) -> bool:
    """Merkezi LLM gateway erisilebilir mi?

    ``api_key`` geriye donuk uyumluluk icin kabul edilir; kullanilmaz.
    """
    try:
        with urllib.request.urlopen(f"{GATEWAY_URL}/health", timeout=3) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False
