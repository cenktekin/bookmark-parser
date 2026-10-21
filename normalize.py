"""Türkçe karakter normalizasyonu ve anahtar kelime eşleştirme yardımcıları.

Bu modül `bookmark_organizer.categorize_link` tarafından kullanılır: anahtar
kelimeler "gmail" içindeki "ai", "index.html" içindeki "ml" gibi yanlış
pozitiflere yol açmaması için **kelime sınırı** ile eşleştirilir.
"""

import re
import unicodedata
from functools import lru_cache
from typing import List, Optional, Sequence


TURKISH_MAP = {
    'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
    'Ç': 'C', 'Ğ': 'G', 'İ': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U'
}


def normalize_text(text: str) -> str:
    """Metni küçük harfe indirir, Türkçe harfleri ASCII karşılıklarına çevirir
    ve aksan işaretlerini temizler."""
    if not text:
        return ""

    text = text.lower()

    for tr_char, en_char in TURKISH_MAP.items():
        text = text.replace(tr_char.lower(), en_char.lower())

    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def normalize_keywords(keywords: List[str]) -> List[str]:
    """Anahtar kelime listesini normalize edilmiş ve çıplak halleriyle döndürür."""
    normalized = []
    for keyword in keywords:
        if isinstance(keyword, str):
            normalized.append(keyword.lower())
            norm = normalize_text(keyword)
            if norm != keyword.lower() and norm not in normalized:
                normalized.append(norm)
    return normalized


@lru_cache(maxsize=8192)
def _normalize_cached(text: str) -> str:
    return normalize_text(text)


_PATTERN_CACHE = {}


def _keyword_pattern(keyword: str) -> re.Pattern:
    """Anahtar kelime için derlenmiş 'kelime sınırı' regex'ini önbellekleyerek döndürür.

    Başlangıçta/sonunda kelime karakteri varsa ilgili tarafa lookaround
    eklenir; böylece "javascript:" gibi nokta ile biten anahtarlar yine de
    çalışır ("javascript:void(0)" -> eşleşme).
    """
    cached = _PATTERN_CACHE.get(keyword)
    if cached is not None:
        return cached

    escaped = re.escape(keyword)
    prefix = r'(?<!\w)' if keyword[:1].isalnum() or keyword[:1] == '_' else ''
    suffix = r'(?!\w)' if keyword[-1:].isalnum() or keyword[-1:] == '_' else ''
    pattern = re.compile(prefix + escaped + suffix)
    _PATTERN_CACHE[keyword] = pattern
    return pattern


def match_keyword(text: str, keyword: str) -> bool:
    """Anahtar kelimeyi metin içinde **kelime sınırı** ile arar.

    Örnekler:
        match_keyword("Gmail - Mail", "ai")        -> False
        match_keyword("index.html dosyasi", "ml") -> False
        match_keyword("Python Dersleri", "python")-> True
        match_keyword("node.js nedir", "node.js") -> True
    """
    if not text or not keyword:
        return False

    normalized_text = normalize_text(text)
    normalized_keyword = _normalize_cached(keyword)
    if not normalized_text or not normalized_keyword:
        return False

    return _keyword_pattern(normalized_keyword).search(normalized_text) is not None


def match_any_keyword(text: str, keywords: Sequence[str]) -> Optional[str]:
    """Anahtar kelime listesinde eşleşen ilk kelimeyi döndürür, eşleşme yoksa None.

    Metin yalnızca bir kez normalize edilir; anahtar kelimeler önbellekten okunur.
    """
    if not text or not keywords:
        return None

    normalized_text = normalize_text(text)
    if not normalized_text:
        return None

    for keyword in keywords:
        if not isinstance(keyword, str):
            continue
        normalized_keyword = _normalize_cached(keyword)
        if not normalized_keyword:
            continue
        if _keyword_pattern(normalized_keyword).search(normalized_text):
            return keyword

    return None


def normalize_url(url: str) -> str:
    """URL'yi standart biçime getirir (şema, küçük harf domain, sondaki eğik çizgi)."""
    if not url:
        return ""

    url = url.strip()

    if not url.startswith(('http://', 'https://', 'ftp://', 'javascript:', 'about:', 'file:')):
        url = 'https://' + url

    parts = url.split('/', 3)
    if len(parts) >= 3:
        parts[2] = parts[2].lower()
        url = '/'.join(parts)

    if url.endswith('/') and url.count('/') > 3:
        url = url[:-1]

    return url


def extract_domain(url: str) -> str:
    """URL'den alan adını çıkarır."""
    if not url:
        return ""

    url = normalize_url(url)

    if '://' in url:
        url = url.split('://', 1)[1]

    url = url.split('/', 1)[0]
    url = url.split(':', 1)[0]

    if url.startswith('www.'):
        url = url[4:]

    return url.lower()


if __name__ == '__main__':
    print("=== normalize_text ===")
    print(normalize_text("Merhaba Dünya"))
    print(normalize_text("Python Programlama"))

    print("\n=== match_keyword (kelime siniri) ===")
    print("Gmail + ai      ->", match_keyword("Gmail - Mail", "ai"))
    print("index.html + ml->", match_keyword("index.html dosyasi", "ml"))
    print("Python + python ->", match_keyword("Python Dersleri", "python"))
    print("node.js + node.js ->", match_keyword("node.js nedir", "node.js"))
    print("javascript:void + javascript: ->",
          match_keyword("javascript:void(0)", "javascript:"))
