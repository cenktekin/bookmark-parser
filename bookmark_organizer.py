
import re
from bs4 import BeautifulSoup, Doctype
import os
import json
import logging
from datetime import datetime

# Define categorization rules based on keywords in title or URL
# This structure is more detailed and hierarchical.
CATEGORIES = {
    "Teknoloji & Yazılım": {
        "keywords": ["tech", "developer", "code", "software", "programming", "yazılım", "kodlama", "bilgisayar", "developer", "stack overflow"],
        "sub": {
            "Yapay Zeka & Makine Öğrenmesi": {
                "keywords": ["ai", "artificial intelligence", "ml", "machine learning", "deep learning", "tensorflow", "pytorch", "huggingface", "openai", "gemini", "claude", "deepseek", "llm", "agent-zero", "prompt", "yapay zeka", "agentic"],
                "sub": {
                    "AI Araçları & Platformlar": ["uizard.io", "lovo.ai", "postcheetah", "tryleap.ai", "compose.ai", "schrodi.co", "rows.com", "10web-site.ai", "fliki.ai", "creativeblogtopic", "midjourney", "firefly.adobe", "bluewillow.ai", "chatpdf", "livepolls.app", "replicate.com", "ai21.com", "rtrvr.ai", "codegpt.co", "codeium", "poe.com", "anthropic"],
                    "AI Eğitim & Dokümantasyon": ["huggingface.co/docs", "huggingface.co/learn", "deeplearning.ai", "prompting", "google.dev/gemini-api"]
                }
            },
            "Python": ["python", "django", "flask", "pandas", "numpy", "py", "yazbel.com"],
            "Web Geliştirme": {
                "keywords": ["web", "frontend", "backend", "css", "html", "javascript", "react", "vue", "angular", "node.js", "next.js", "tailwind", "bootstrap"],
                "sub": {
                    "Frontend": ["frontend", "css", "html", "react", "vue", "angular", "tailwind", "bootstrap", "htmldog", "css-tricks"],
                    "Backend": ["backend", "node.js", "nestjs", "spring boot", "api", "server", "firebase", "supabase"],
                    "Web Dev Araçları": ["layoutit", "bootswatch", "bootsnipp", "jsfiddle", "gradienty.codes", "userway.org"]
                }
            },
            "Güvenlik & Hacking": {
                "keywords": ["hack", "security", "cybersecurity", "pentest", "comptia", "siber güvenlik", "exploit-db", "overthewire"],
                "sub": {
                    "CompTIA Sertifikaları": ["comptia"],
                    "Hacking Eğitimleri": ["hack", "pentest", "kali linux", "nmap"],
                }
            },
            "Veri Bilimi & Analiz": ["data", "analytics", "sql", "database", "kaggle", "datacamp", "veri"],
            "Eğitim Platformları & Kaynaklar": ["udemy", "coursera", "freecodecamp", "edx", "patika.dev", "btkakademi", "cs50", "w3schools", "tutorial", "learn", "course", "eğitim", "khanacademy", "theodinproject"],
            "Araçlar & IDEs": ["github", "git", "replit", "codepen", "codesandbox", "vscode", "visual studio", "jetbrains", "docker", "linux", "rapidapi", "postman", "ide", "sublime", "brackets", "idx.google"],
        }
    },
    "Film, Dizi & Sanat": {
        "keywords": ["film", "dizi", "movie", "series", "tv", "eğlence", "entertainment", "seyret", "sanat", "art"],
        "sub": {
            "Film & Dizi Platformları": ["netflix", "blutv", "dizilla", "hdfilmcehennemi", "filmizle", "imdb", "justwatch", "dizibox", "diziroll", "roketdizi", "sinema.cx", "sinema.vip", "tvplus", "kultfilmler"],
            "Tiyatro, Opera & Bale": ["tiyatro", "opera", "bale", "sahne", "musical"],
            "Müzik & Konserler": ["müzik", "konser", "concert", "spotify", "youtube.com/watch", "soundcloud"],
            "Müzeler & Galeriler": ["museum", "muze", "gallery", "sanat", "artsandculture.google", "louvre", "metmuseum", "britishmuseum"],
        }
    },
    "Kültür & Yaşam": {
        "keywords": ["kültür", "kişisel gelişim", "felsefe", "tasavvuf", "kitap", "okuma", "blog", "dergi", "yaşam"],
        "sub": {
            "Haber, Blog & Makale": ["feedly", "news", "gazete", "dunya.com", "hbrturkiye", "medium", "dev.to", "hackernoon", "uplifers", "resmigazete", "indieblog", "neocities", "lemmyverse", "thenewstack"],
            "Bilim & Akademi": ["evrimagaci", "scholar.google", "academia.edu", "bilim", "science", "acikders.ankara.edu.tr", "nationalacademies"],
            "Felsefe & Tasavvuf": ["felsefe", "tasavvuf", "anadoluaydinlanma", "isam", "tevhiddersleri", "stoacı", "sufi", "mevlana", "yunus emre", "risaleoku", "islamveihsan"],
            "Kitaplar & Kütüphaneler": {
                "keywords": ["book", "kütüphane", "library", "gutenberg", "archive.org", "libgen", "pdfdrive", "goodreads", "kitap", "yazmaeserler", "openculture", "wikibooks"],
                "sub": {
                    "Sesli Kitaplar": ["sesli kitap", "audiobook", "librivox"],
                    "Akademik Arşivler": ["devletarsivleri", "makhtota", "yazmaeserler.diyanet", "isam.org.tr", "mkutup.gov.tr"]
                }
            },
            "Gezi & Coğrafya": ["gezi", "seyahat", "travel", "tourist", "wanderlust", "citywalk", "geographicaljourneys", "city tour", "thripy.com"],
            "Yemek Tarifleri": ["yemek", "tarif", "recipe", "lezzet", "nefisyemektarifleri"],
        }
    },
    "Sosyal Medya & Forumlar": ["facebook", "twitter", "x.com", "pinterest", "reddit", "linkedin", "discord", "forum"],
    "İndirme & Torrent": ["torrent", "download", "warez", "pirate", "libgen.is", "rarbg", "1337x"],
    "Diğer": [],
    "Bozuk & Kontrol Edilecek": ["javascript:", "about:blank"]
}


def categorize_link(title, url, categories_def):
    """Recursively find the best category for a given link."""
    if not title and not url:
        return None

    text_to_check = (title + " " + url).lower()

    # Handle special cases first
    if "youtube.com/watch?v=" in url or "youtube.com/playlist?list=" in url:
        if "tiyatro" in text_to_check or "oyun" in text_to_check:
            return ["Film, Dizi & Sanat", "Etkinlik & Sanat", "Tiyatro"]
        if "opera" in text_to_check or "bale" in text_to_check:
            return ["Film, Dizi & Sanat", "Etkinlik & Sanat", "Opera & Bale"]
        if "konser" in text_to_check or "concert" in text_to_check:
            return ["Film, Dizi & Sanat", "Müzik & Konserler"]
        if "belgesel" in text_to_check or "documentary" in text_to_check:
            return ["Film, Dizi & Sanat", "Belgesel"]
        if "sesli kitap" in text_to_check or "audiobook" in text_to_check:
            return ["Kültür & Yaşam", "Kitaplar & Kütüphaneler", "Sesli Kitaplar"]
        if "cs50" in text_to_check or "python" in text_to_check or "coding" in text_to_check or "developer" in text_to_check:
            return ["Teknoloji & Yazılım", "Eğitim Platformları & Kaynaklar"]
        if "gezi" in text_to_check or "walk" in text_to_check or "travel" in text_to_check:
            return ["Kültür & Yaşam", "Gezi & Coğrafya", "YouTube Gezi Kanalları"]

    for cat_name, cat_data in categories_def.items():
        if isinstance(cat_data, list):
            if any(keyword in text_to_check for keyword in cat_data):
                return [cat_name]
        elif isinstance(cat_data, dict):
            if "sub" in cat_data:
                sub_path = categorize_link(title, url, cat_data["sub"])
                if sub_path:
                    return [cat_name] + sub_path
            if "keywords" in cat_data and any(keyword in text_to_check for keyword in cat_data["keywords"]):
                return [cat_name]
    return None


def add_to_structure(structure, path, item):
    """Add a bookmark item to the nested dictionary structure."""
    current_level = structure
    for folder in path:
        if folder not in current_level:
            current_level[folder] = {"__items__": []}
        current_level = current_level[folder]
    current_level["__items__"].append(item)


def create_html_from_structure(structure, soup):
    """Generate HTML bookmark structure from the organized dictionary."""
    def build_level(parent_dl, level_dict):
        # Sort keys: folders first (not "__items__"), then links
        sorted_keys = sorted(level_dict.keys(), key=lambda k: (
            k == "__items__", k.lower()))

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


def generate_statistics(structure):
    """Generate statistics about categorized bookmarks."""
    stats = {}

    def count_items(level_dict, path=""):
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


def save_categories_config(filename="categories_config.json"):
    """Save current categories configuration to JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(CATEGORIES, f, ensure_ascii=False, indent=2)
        print(f"Kategori yapılandırması '{filename}' dosyasına kaydedildi.")
    except Exception as e:
        print(f"Kategori yapılandırması kaydedilemedi: {e}")


def load_categories_config(filename="categories_config.json"):
    """Load categories configuration from JSON file."""
    global CATEGORIES
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                CATEGORIES = json.load(f)
            print(
                f"Kategori yapılandırması '{filename}' dosyasından yüklendi.")
            return True
    except Exception as e:
        print(f"Kategori yapılandırması yüklenemedi: {e}")
    return False


def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bookmark_organizer.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    # Load custom categories if available
    load_categories_config()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, 'bookmarks.html')
    output_file = os.path.join(script_dir, 'bookmarks_organized.html')

    if not os.path.exists(input_file):
        logging.error(f"'{input_file}' dosyası bulunamadı.")
        return

    try:
        logging.info("Bookmark dosyası okunuyor...")
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logging.error(f"Dosya okunurken hata: {e}")
        return

    # Create backup
    backup_file = f"{input_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(input_file, backup_file)
        logging.info(f"Yedek dosya oluşturuldu: {backup_file}")
    except Exception as e:
        logging.warning(f"Yedek oluşturulamadı: {e}")

    soup = BeautifulSoup(content, 'html.parser')
    organized_structure = {}

    all_links = soup.find_all('a')
    logging.info(f"Toplam {len(all_links)} adet link bulundu ve işleniyor...")

    processed_count = 0
    for i, link in enumerate(all_links):
        title = link.text.strip()
        url = link.get('href', '')
        if not title and not url:
            continue

        add_date = link.get('add_date', '')
        icon = link.get('icon', '')
        item = {'type': 'link', 'title': title,
                'url': url, 'add_date': add_date, 'icon': icon}

        path = categorize_link(title, url, CATEGORIES)
        if path:
            add_to_structure(organized_structure, path, item)
        else:
            add_to_structure(organized_structure, ["Diğer"], item)

        processed_count += 1

        # Progress indicator
        if (i + 1) % 100 == 0:
            logging.info(f"İşlenen: {i + 1}/{len(all_links)}")

    logging.info("HTML yapısı oluşturuluyor...")

    # Create a new HTML structure
    new_soup = BeautifulSoup("", 'html.parser')
    doctype = Doctype('NETSCAPE-Bookmark-file-1')
    new_soup.append(doctype)

    meta = new_soup.new_tag('META', attrs={
                            'HTTP-EQUIV': 'Content-Type', 'CONTENT': 'text/html; charset=UTF-8'})
    new_soup.append(meta)

    title_tag = new_soup.new_tag('TITLE')
    title_tag.string = 'Organized Bookmarks'
    new_soup.append(title_tag)

    h1_tag = new_soup.new_tag('H1')
    h1_tag.string = 'Organized Bookmarks'
    new_soup.append(h1_tag)

    # Add generation info
    info_p = new_soup.new_tag('p')
    info_p.string = f"Organize edildi: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} - Toplam {processed_count} link"
    new_soup.append(info_p)

    final_dl = create_html_from_structure(organized_structure, new_soup)
    new_soup.append(final_dl)

    try:
        logging.info("Organize edilmiş dosya kaydediliyor...")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(new_soup.prettify())
        logging.info(f"Başarıyla kaydedildi: '{output_file}'")

        # Generate and display statistics
        stats = generate_statistics(organized_structure)
        logging.info("\n=== İSTATİSTİKLER ===")
        for category, count in sorted(stats.items()):
            logging.info(f"{category}: {count} link")

        # Save current categories config for future use
        save_categories_config()

    except Exception as e:
        logging.error(f"Dosya yazılırken hata: {e}")


if __name__ == '__main__':
    main()
