"""Yer imi (bookmark) kategorilendirme motoru ve komut satırı arayüzü."""

import argparse
import json
import logging
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup, Doctype

from categories import get_categories, set_categories
from normalize import match_any_keyword

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(SCRIPT_DIR, "categories_config.json")
DEFAULT_INPUT = os.path.join(SCRIPT_DIR, "bookmarks.html")
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "bookmarks_organized.html")

Item = Dict[str, str]
Structure = Dict[str, Any]


# --------------------------------------------------------------------------- #
# Kategorilendirme
# --------------------------------------------------------------------------- #

def categorize_link(title: str, url: str, categories_def: Dict[str, Any]) -> Optional[List[str]]:
    """Bir yer imi için en uygun kategori yolunu döndürür, eşleşme yoksa None.

    Anahtar kelimeler **kelime sınırı** ile eşleştirilir; "gmail" içindeki
    "ai" veya "index.html" içindeki "ml" gibi yanlış pozitifler oluşmaz.
    """
    if not title and not url:
        return None

    text_to_check = (title + " " + url).lower()

    # Bozuk/özel şemalar her zaman "Bozuk & Kontrol Edilecek" kovasına gider.
    # Anahtar kelime taramasından ÖNCE ele alınır; aksi halde "javascript"
    # kelimesi "Web Geliştirme" kategorisine eşleşirdi.
    lowered_url = url.strip().lower()
    if lowered_url.startswith("javascript:") or lowered_url.startswith("about:blank"):
        if "Bozuk & Kontrol Edilecek" in categories_def:
            return ["Bozuk & Kontrol Edilecek"]

    if "youtube.com/watch?v=" in url or "youtube.com/playlist?list=" in url:
        special = _categorize_youtube(text_to_check)
        if special:
            return special

    for cat_name, cat_data in categories_def.items():
        if isinstance(cat_data, list):
            if match_any_keyword(text_to_check, cat_data):
                return [cat_name]
        elif isinstance(cat_data, dict):
            if "sub" in cat_data:
                sub_path = categorize_link(title, url, cat_data["sub"])
                if sub_path:
                    return [cat_name] + sub_path
            if "keywords" in cat_data and match_any_keyword(text_to_check, cat_data["keywords"]):
                return [cat_name]
    return None


def _categorize_youtube(text_to_check: str) -> Optional[List[str]]:
    """YouTube bağlantıları için özel durum kuralları.

    Dönülen yollar `categories.py` içinde **gerçekten tanımlı** kategorilere
    işaret eder (phantom kategori üretilmez).
    """
    if "tiyatro" in text_to_check or "oyun" in text_to_check:
        return ["Film, Dizi & Sanat", "Tiyatro, Opera & Bale"]
    if "opera" in text_to_check or "bale" in text_to_check:
        return ["Film, Dizi & Sanat", "Tiyatro, Opera & Bale"]
    if "konser" in text_to_check or "concert" in text_to_check:
        return ["Film, Dizi & Sanat", "Müzik & Konserler"]
    if "belgesel" in text_to_check or "documentary" in text_to_check:
        return ["Film, Dizi & Sanat", "Belgesel"]
    if "sesli kitap" in text_to_check or "audiobook" in text_to_check:
        return ["Kültür & Yaşam", "Kitaplar & Kütüphaneler", "Sesli Kitaplar"]
    if "cs50" in text_to_check or "python" in text_to_check or "coding" in text_to_check:
        return ["Teknoloji & Yazılım", "Eğitim Platformları & Kaynaklar"]
    if "gezi" in text_to_check or "walk" in text_to_check or "travel" in text_to_check:
        return ["Kültür & Yaşam", "Gezi & Coğrafya", "YouTube Gezi Kanalları"]
    return None


def path_exists(path: Sequence[str], categories_def: Dict[str, Any]) -> bool:
    """Verilen kategori yolunun yapılandırmada gerçekten var olduğunu doğrular."""
    node: Any = categories_def
    last_index = len(path) - 1

    for index, folder in enumerate(path):
        if not isinstance(node, dict) or folder not in node:
            return False
        node = node[folder]
        if index < last_index:
            if not isinstance(node, dict) or "sub" not in node:
                return False
            node = node["sub"]

    return True


def add_to_structure(structure: Structure, path: Sequence[str], item: Item) -> None:
    """Bir yer imi öğesini iç içe kategori yapısına ekler."""
    current_level = structure
    for folder in path:
        if folder not in current_level:
            current_level[folder] = {"__items__": []}
        current_level = current_level[folder]
    current_level["__items__"].append(item)


def categorize_items(
    items: Sequence[Item],
    categories_def: Optional[Dict[str, Any]] = None,
) -> Tuple[Structure, List[Item]]:
    """Yer imi öğelerini kategorilere ayırır.

    Returns:
        (yapı, eşleşmeyen_öğeler) — eşleşmeyenler "Diğer" kovasına konur ve
        raporlanmak üzere ayrıca döndürülür.
    """
    if categories_def is None:
        categories_def = get_categories()

    structure: Structure = {}
    unmatched: List[Item] = []

    for item in items:
        path = categorize_link(item.get("title", ""), item.get("url", ""), categories_def)
        if path and path_exists(path, categories_def):
            add_to_structure(structure, path, item)
        else:
            if path:
                logger.warning("Tanımsız kategori yolu '%s' -> 'Diğer'", " > ".join(path))
            add_to_structure(structure, ["Diğer"], item)
            unmatched.append(item)

    return structure, unmatched


def generate_statistics(structure: Structure) -> Dict[str, int]:
    """Kategori başına link sayıları üretir."""
    stats: Dict[str, int] = {}

    def count_items(level_dict: Dict[str, Any], path: str = "") -> int:
        total = 0
        for key, value in level_dict.items():
            if key == "__items__":
                count = len(value)
                if path:
                    stats[path] = count
                total += count
            else:
                current_path = f"{path} > {key}" if path else key
                total += count_items(value, current_path)
        return total

    total_count = count_items(structure)
    stats["TOPLAM"] = total_count
    return stats


# --------------------------------------------------------------------------- #
# Yapılandırma (config) yönetimi
# --------------------------------------------------------------------------- #

def load_categories_config(filename: str) -> bool:
    """Verilen JSON dosyasından kategori yapılandırmasını yükler.

    Dosya bulunamazsa veya bozuksa dahili varsayılanlar kullanılmaya devam eder.
    """
    if not filename or not os.path.isfile(filename):
        return False

    try:
        with open(filename, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Yapılandırma okunamadı (%s): %s", filename, exc)
        return False

    if not isinstance(loaded, dict) or not loaded:
        logger.error("Yapılandırma geçersiz (boş veya nesne değil): %s", filename)
        return False

    set_categories(loaded)
    logger.info("Yapılandırma yüklendi: %s", filename)
    return True


def save_categories_config(filename: str, categories_def: Optional[Dict[str, Any]] = None) -> bool:
    """Kategori yapılandırmasını JSON dosyasına yazar.

    Yalnızca `--export-config` bayrağı ile çağrılır; hiçbir koşulda otomatik
    olarak tetiklenmez (kullanıcının düzenlemeleri ezilmez).
    """
    data = categories_def if categories_def is not None else get_categories()
    try:
        with open(filename, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.error("Yapılandırma yazılamadı (%s): %s", filename, exc)
        return False
    logger.info("Yapılandırma kaydedildi: %s", filename)
    return True


# --------------------------------------------------------------------------- #
# HTML üretimi
# --------------------------------------------------------------------------- #

def create_html_from_structure(structure: Structure, soup: BeautifulSoup) -> BeautifulSoup:
    """Düzenlenmiş yer imi yapısından standart HTML üretir."""
    def build_level(parent_dl: Any, level_dict: Dict[str, Any]) -> None:
        sorted_keys = sorted(level_dict.keys(), key=lambda k: (k == "__items__", k.lower()))

        for key in sorted_keys:
            if key == "__items__":
                continue

            dt_folder = soup.new_tag('DT')
            h3 = soup.new_tag('H3')
            h3.string = key
            dt_folder.append(h3)
            parent_dl.append(soup.new_tag('p'))

            sub_dl = soup.new_tag('DL')
            p_sub = soup.new_tag('p')
            sub_dl.append(p_sub)
            parent_dl.append(sub_dl)

            build_level(sub_dl, level_dict[key])

        if "__items__" in level_dict:
            for item in sorted(level_dict["__items__"], key=lambda x: x['title'].lower()):
                if item['type'] == 'link':
                    dt_link = soup.new_tag('DT')
                    a = soup.new_tag('A', href=item['url'])
                    if item.get('add_date'):
                        a['add_date'] = item['add_date']
                    if item.get('icon'):
                        a['icon'] = item['icon']
                    a.string = item['title']
                    dt_link.append(a)
                    parent_dl.append(dt_link)

    top_dl = soup.new_tag('DL')
    p_tag = soup.new_tag('p')
    top_dl.append(p_tag)
    build_level(top_dl, structure)
    return top_dl


def write_unmatched_report(unmatched: Sequence[Item], output_file: str) -> str:
    """Eşleşmeyen yer imlerini rapor dosyasına yazar."""
    lines = [
        "# Eşleşmeyen Yer İmleri",
        f"Oluşturulma: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Toplam: {len(unmatched)}",
        "",
    ]
    for item in unmatched:
        title = (item.get("title") or "").strip() or "(başlıksız)"
        lines.append(f"{item.get('url', '')}\t{title}")

    with open(output_file, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    return output_file


# --------------------------------------------------------------------------- #
# Ana akış
# --------------------------------------------------------------------------- #

def extract_items(content: str) -> List[Item]:
    """HTML içeriğinden yer imi öğelerini çıkarır."""
    soup = BeautifulSoup(content, 'html.parser')
    items: List[Item] = []

    for link in soup.find_all('a'):
        title = link.text.strip()
        url = link.get('href', '')
        if not title and not url:
            continue
        items.append({
            'type': 'link',
            'title': title,
            'url': url,
            'add_date': link.get('add_date', ''),
            'icon': link.get('icon', ''),
        })

    return items


def setup_logging(verbose: bool = False) -> None:
    """Konsol (ve isteğe bağlı dosya) günlüklemesini kurar."""
    handlers: List[logging.Handler] = [logging.StreamHandler()]
    try:
        handlers.append(logging.FileHandler(
            os.path.join(SCRIPT_DIR, 'bookmark_organizer.log'), encoding='utf-8'))
    except OSError:
        pass

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers,
    )


def main(
    input_file: Optional[str] = None,
    output_file: Optional[str] = None,
    report_unmatched: Optional[str] = None,
) -> int:
    """Yer imlerini kategorize eder ve düzenlenmiş HTML'i yazar."""
    input_file = os.path.abspath(input_file or DEFAULT_INPUT)
    output_file = os.path.abspath(output_file or DEFAULT_OUTPUT)

    if not os.path.exists(input_file):
        logger.error("'%s' dosyası bulunamadı.", input_file)
        return 1

    try:
        with open(input_file, 'r', encoding='utf-8') as fh:
            content = fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        logger.error("Dosya okunurken hata: %s", exc)
        return 1

    backup_file = f"{input_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        shutil.copy2(input_file, backup_file)
        logger.info("Yedek dosya oluşturuldu: %s", backup_file)
    except OSError as exc:
        logger.warning("Yedek oluşturulamadı: %s", exc)

    items = extract_items(content)
    logger.info("Toplam %d adet link bulundu ve işleniyor...", len(items))

    organized_structure, unmatched = categorize_items(items)

    new_soup = BeautifulSoup("", 'html.parser')
    new_soup.append(Doctype('NETSCAPE-Bookmark-file-1'))
    new_soup.append(new_soup.new_tag('META', attrs={
        'HTTP-EQUIV': 'Content-Type', 'CONTENT': 'text/html; charset=UTF-8'}))
    title_tag = new_soup.new_tag('TITLE')
    title_tag.string = 'Organized Bookmarks'
    new_soup.append(title_tag)
    h1_tag = new_soup.new_tag('H1')
    h1_tag.string = 'Organized Bookmarks'
    new_soup.append(h1_tag)
    info_p = new_soup.new_tag('p')
    info_p.string = (
        f"Organize edildi: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} "
        f"- Toplam {len(items)} link"
    )
    new_soup.append(info_p)

    new_soup.append(create_html_from_structure(organized_structure, new_soup))

    try:
        with open(output_file, 'w', encoding='utf-8') as fh:
            fh.write(new_soup.prettify())
    except OSError as exc:
        logger.error("Dosya yazılırken hata: %s", exc)
        return 1

    logger.info("Başarıyla kaydedildi: '%s'", output_file)

    stats = generate_statistics(organized_structure)
    logger.info("=== İSTATİSTİKLER ===")
    for category, count in sorted(stats.items()):
        logger.info("%s: %d link", category, count)

    if report_unmatched:
        write_unmatched_report(unmatched, report_unmatched)
        logger.info("Eşleşmeyen %d link raporlandı: %s", len(unmatched), report_unmatched)

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Bookmark Organizer - Yer imlerini otomatik kategorize eder')
    parser.add_argument('--input', '-i', default=None,
                        help='Giriş HTML dosyası (varsayılan: bookmarks.html)')
    parser.add_argument('--output', '-o', default=None,
                        help='Çıkış HTML dosyası (varsayılan: bookmarks_organized.html)')
    parser.add_argument('--markdown', '-m', action='store_true',
                        help='Markdown formatında çıktı üret')
    parser.add_argument('--check-links', '-c', action='store_true',
                        help="Linklerin canlılık kontrolünü yap")
    parser.add_argument('--timeout', '-t', type=int, default=10,
                        help='HTTP timeout süresi (saniye)')
    parser.add_argument('--workers', '-w', type=int, default=5,
                        help='Eşzamanlı thread sayısı')
    parser.add_argument('--insecure', action='store_true',
                        help='TLS doğrulamasını kapatır (link kontrolü; önerilmez)')
    parser.add_argument('--config', default=None,
                        help='Kullanılacak kategori yapılandırma JSON dosyası')
    parser.add_argument('--export-config', default=None, metavar='DOSYA',
                        help='Dahili kategori kurallarını JSON dosyasına yazar')
    parser.add_argument('--report-unmatched', nargs='?', const='unmatched_report.txt',
                        metavar='DOSYA',
                        help='Eşleşmeyen yer imlerini raporlar')
    parser.add_argument('--verbose', '-v', action='store_true', help='Ayrıntılı günlük')
    return parser


def cli() -> int:
    args = _build_parser().parse_args()

    setup_logging(args.verbose)

    if args.export_config:
        target = os.path.abspath(args.export_config)
        return 0 if save_categories_config(target) else 1

    if args.config:
        if not load_categories_config(os.path.abspath(args.config)):
            logger.warning("Yapılandırma yüklenemedi, dahili kurallar kullanılıyor.")

    if args.markdown:
        output_file = args.output or os.path.join(SCRIPT_DIR, 'bookmarks_organized.md')
        import converter
        converter.convert_to_markdown(args.input or DEFAULT_INPUT, output_file)
        return 0

    if args.check_links:
        output_report = args.output or os.path.join(SCRIPT_DIR, 'link_report.txt')
        import link_checker
        report = link_checker.check_links(
            args.input or DEFAULT_INPUT,
            output_report,
            timeout=args.timeout,
            max_workers=args.workers,
            verify=not args.insecure,
        )
        return 1 if report["dead"] else 0

    return main(
        input_file=args.input,
        output_file=args.output,
        report_unmatched=args.report_unmatched,
    )


if __name__ == '__main__':
    raise SystemExit(cli())
