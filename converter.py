import os
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from bookmark_organizer import categorize_items
from categories import get_categories

logger = logging.getLogger(__name__)

Structure = Dict[str, Any]


def _count_total_links(structure: Structure) -> int:
    total = 0
    for key, value in structure.items():
        if key == "__items__":
            total += len(value)
        elif isinstance(value, dict):
            total += _count_total_links(value)
    return total


def _build_markdown_lines(
    level_dict: Structure,
    depth: int = 0,
    lines: Optional[List[str]] = None,
) -> List[str]:
    if lines is None:
        lines = []

    sorted_keys = sorted(
        [k for k in level_dict if k != "__items__"],
        key=str.lower,
    )

    for key in sorted_keys:
        heading_prefix = "#" * min(depth + 2, 6)
        lines.append("")
        lines.append(f"{heading_prefix} {key}")
        lines.append("")

        sub = level_dict[key]
        if "__items__" in sub:
            _append_items(sub["__items__"], lines)
        child_dict = {k: v for k, v in sub.items() if k != "__items__"}
        if child_dict:
            _build_markdown_lines(sub, depth + 1, lines)

    if "__items__" in level_dict and not sorted_keys:
        _append_items(level_dict["__items__"], lines)

    return lines


def _append_items(items: List[Dict[str, str]], lines: List[str]) -> None:
    for item in sorted(items, key=lambda x: x.get("title", "").lower()):
        title = item.get("title", "").strip() or "(başlıksız)"
        url = item.get("url", "")
        if url:
            lines.append(f"- [{title}]({url})")
        else:
            lines.append(f"- {title}")
    lines.append("")


def generate_markdown_report(structure: Structure) -> str:
    """Yapıdan Markdown rapor üretir."""
    total = _count_total_links(structure)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: List[str] = [
        "# Organized Bookmarks",
        "",
        f"*Oluşturulma tarihi: {now} - Toplam {total} link*",
        "",
    ]

    top_keys = sorted(
        [k for k in structure if k != "__items__"],
        key=str.lower,
    )

    for key in top_keys:
        lines.append("---")
        lines.append("")
        lines.append(f"## {key}")
        lines.append("")

        sub = structure[key]
        if "__items__" in sub:
            _append_items(sub["__items__"], lines)
        child_dict = {k: v for k, v in sub.items() if k != "__items__"}
        if child_dict:
            _build_markdown_lines(sub, 1, lines)

    if "__items__" in structure:
        lines.append("---")
        lines.append("")
        _append_items(structure["__items__"], lines)

    return "\n".join(lines) + "\n"


def convert_to_markdown(
    input_file: str,
    output_file: Optional[str] = None,
) -> str:
    """HTML bookmark dosyasını okur, kategorilere ayırır ve Markdown üretir.

    Returns:
        Oluşturulan çıktı dosyasının yolu.

    Raises:
        FileNotFoundError: input_file bulunamazsa.
        ValueError: input_file boşsa veya geçersizse.
    """
    if not input_file or not isinstance(input_file, str):
        raise ValueError("input_file geçerli bir dosya yolu olmalıdır.")

    input_file = os.path.abspath(input_file)
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Girdi dosyası bulunamadı: {input_file}")

    if output_file is None:
        stem = os.path.splitext(input_file)[0]
        output_file = f"{stem}_organized.md"
    output_file = os.path.abspath(output_file)

    logger.info("Bookmark dosyası okunuyor: %s", input_file)
    try:
        with open(input_file, "r", encoding="utf-8") as fh:
            content = fh.read()
    except UnicodeDecodeError:
        logger.warning("UTF-8 ile okunamadı, latin-1 deneniyor...")
        with open(input_file, "r", encoding="latin-1") as fh:
            content = fh.read()

    soup = BeautifulSoup(content, "html.parser")
    all_links = soup.find_all("a")
    logger.info("Toplam %d link bulundu.", len(all_links))

    items = []
    for link in all_links:
        title = link.text.strip()
        url = link.get("href", "")
        if not title and not url:
            continue
        items.append({
            "type": "link",
            "title": title,
            "url": url,
            "add_date": link.get("add_date", ""),
            "icon": link.get("icon", ""),
        })

    structure, unmatched = categorize_items(items, get_categories())
    logger.info("Kategorilere ayrıldı: %d link işlendi (%d eşleşmedi).",
                len(items), len(unmatched))

    markdown = generate_markdown_report(structure)

    try:
        with open(output_file, "w", encoding="utf-8") as fh:
            fh.write(markdown)
        logger.info("Markdown dosyası kaydedildi: %s", output_file)
    except OSError as exc:
        logger.error("Dosya yazma hatası: %s", exc)
        raise

    return output_file


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("bookmark_organizer.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> None:
    import argparse

    _setup_logging()

    parser = argparse.ArgumentParser(description="HTML yer imlerini Markdown'a çevirir")
    parser.add_argument("input_file", help="Girdi HTML dosyası")
    parser.add_argument("output_file", nargs="?", default=None, help="Çıktı Markdown dosyası")
    parser.add_argument("--config", default=None,
                        help="Kullanılacak kategori yapılandırma JSON dosyası")
    args = parser.parse_args()

    if args.config:
        from bookmark_organizer import load_categories_config
        if not load_categories_config(os.path.abspath(args.config)):
            logger.warning("Yapılandırma yüklenemedi, dahili kurallar kullanılıyor.")

    try:
        result_path = convert_to_markdown(args.input_file, args.output_file)
        print(f"Başarıyla oluşturuldu: {result_path}")
    except FileNotFoundError as exc:
        logger.error(str(exc))
        sys.exit(1)
    except ValueError as exc:
        logger.error("Geçersiz argüman: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Beklenmeyen hata: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
