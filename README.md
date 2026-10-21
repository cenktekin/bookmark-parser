# Bookmark Organizer 🔖

[Türkçe Oku](README.md#türkçe) | [Read in English](README.md#english)

---

## Türkçe

Yer imlerinizi düzenlemek hiç bu kadar kolay olmamıştı! Bu Python uygulaması, HTML formatındaki yer imlerinizi (örneğin tarayıcınızdan dışa aktardığınız) okur, içeriğine ve URL'sine göre akıllıca kategorize eder ve size düzenli, hiyerarşik bir HTML yer imi dosyası olarak geri verir. Artık aradığınız linki bulmak için dakikalar harcamanıza gerek kalmayacak!

🎯 **Yeni**: Artık hem **GUI arayüzü** hem de **komut satırı** versiyonu mevcut!

## Özellikler ✨

  * **🖥️ GUI Arayüzü:** Kullanıcı dostu grafik arayüzü ile dosya seçme, ilerleme takibi ve sonuç görüntüleme
  * **⚡ Akıllı Kategorizasyon:** Yer imi başlıklarını ve URL'lerini analiz ederek önceden tanımlanmış kategorilere (Teknoloji & Yazılım, Film & Dizi, Kültür & Yaşam vb.) otomatik olarak atar
  * **🎯 Kelime Sınırı Eşleştirme:** Anahtar kelimeler tam token olarak eşleşir; "gmail" içindeki "ai" veya "index.html" içindeki "ml" yanlış eşleşme oluşturmaz
  * **📊 Hiyerarşik Yapı:** Ana kategoriler altında alt kategoriler oluşturarak daha detaylı bir düzenleme sağlar
  * **🔧 Özelleştirilebilir Kurallar:** Kategori kuralları `categories.py` içinde tanımlıdır; JSON olarak dışa aktarılıp `--config` ile kullanılabilir
  * **🔎 Eşleşmeyen Link Raporu:** Hiçbir kategoriye girmeyen linkler `--report-unmatched` ile raporlanır — kural havuzunu beslemenin en pratik yolu
  * **💾 Otomatik Yedekleme:** İşlem öncesi otomatik yedek dosyası oluşturur
  * **📈 Detaylı İstatistikler:** Kategori başına link sayıları ve işlem raporu
  * **🌐 HTML Çıkışı:** Standart HTML formatında dışa aktarım
  * **📝 Markdown Export:** Düzenlenen yer imlerini Markdown formatında dışa aktarın
  * **🔗 Dead Link Checker:** Linklerin hala aktif olup olmadığını kontrol edin (TLS doğrulaması varsayılan olarak açıktır)
  * **🤖 AI Kategorizasyon (POC):** Gemini API ile yapay zeka destekli kategorizasyon
  * **✅ Test & CI:** Sıfır ek bağımlılıkla `unittest` testleri ve GitHub Actions kapısı

## Nasıl Çalışır? ⚙️

Betiğin kalbi, `categories.py` dosyasındaki `CATEGORIES` sözlüğüdür. Bu sözlük, her bir kategori ve alt kategori için anahtar kelimeleri veya doğrudan URL'leri içerir. Betik, yer imlerinizin başlıklarını ve URL'lerini bu anahtar kelimelerle karşılaştırarak en uygun kategoriye yerleştirir.

Anahtar kelimeler **kelime sınırı** ile eşleştirilir: `ai` kelimesi yalnızca "AI", "Yapay Zeka" gibi tam bir kelime olarak geçtiğinde eşleşir; "gmail.com" içindeki "ai" eşleşmez. Aynı şekilde `ml`, "index.html" içindeki "ml" ile eşleşmez. Özellikle YouTube linkleri için tiyatro, konser, belgesel gibi özel durumları da ele alıyor.

-----

## Kurulum 🚀

1.  **Python'ı Yükleyin:** Bilgisayarınızda Python 3 yüklü olduğundan emin olun. Yoksa, [python.org](https://www.python.org/downloads/) adresinden indirebilirsiniz.
2.  **Gerekli Kütüphaneleri Yükleyin:** Çekirdek betik `BeautifulSoup4` ve `requests` kullanır:
    ```bash
    pip install -r requirements.txt
    ```
    AI kategorizasyonu için ayrıca:
    ```bash
    pip install -r requirements-ai.txt
    ```
3.  **Betiği İndirin:** Bu depoyu klonlayın veya `bookmark_organizer.py` dosyasını indirin.

-----

## Kullanım 🧑‍💻

### 🖥️ GUI Versiyonu (Önerilen)

1. **GUI'yi Başlatın:**
   ```bash
   python bookmark_organizer_gui.py
   ```

2. **Dosyaları Seçin:**
   - "Giriş Dosyası" butonuna tıklayarak bookmark HTML dosyanızı seçin
   - "Çıkış Dosyası" butonuna tıklayarak organize edilmiş dosyanın kaydedileceği yeri belirleyin

3. **Seçenekleri Ayarlayın:**
   - ✅ Orijinal dosyayı yedekle (önerilen)
   - ✅ Sonucu tarayıcıda aç

4. **"Organize Et" Butonuna Tıklayın** ve işlemin tamamlanmasını bekleyin!

### ⌨️ Komut Satırı Versiyonu

1.  **Yer İmlerinizi Dışa Aktarın:** Tarayıcınızdan yer imlerinizi HTML dosyası olarak dışa aktarın
2.  **Dosyayı Yerleştirin:** HTML dosyasını `bookmarks.html` olarak adlandırıp script klasörüne koyun
3.  **Betiği Çalıştırın:**
    ```bash
    python bookmark_organizer.py
    ```
4.  **Sonucu Kontrol Edin:** `bookmarks_organized.html` dosyası oluşacak

### 📝 Markdown Export

Düzenlenen yer imlerini Markdown formatında dışa aktarmak için:

```bash
python bookmark_organizer.py --markdown
python converter.py bookmarks.html
```

### 🔗 Dead Link Checker

Linklerin canlılık kontrolünü yapmak için:

```bash
python bookmark_organizer.py --check-links
python link_checker.py bookmarks.html --output report.txt --timeout 10 --workers 5
```

TLS sertifika doğrulaması **varsayılan olarak açıktır**. Yalnızca hatalı sertifika
üreten kurum içi sunucularda `--insecure` bayrağıyla kapatılabilir:

```bash
python link_checker.py bookmarks.html --insecure
```

### 🔎 Eşleşmeyen Link Raporu

Hiçbir kategori kuralına uymayan linkleri (raporlananlar "Diğer" kovasına girer)
tab ayrılmış bir rapora dökebilirsiniz. Raporu okuyup kural havuzunu
genişletmek en pratik iyileştirme yoludur:

```bash
python bookmark_organizer.py --report-unmatched unmatched_report.txt
```

### 🧩 Özel Kural Dosyası

Program **hiçbir koşulda** kural dosyanızın üzerine yazmaz. Dahili kuralları
JSON olarak dışa aktarıp düzenleyebilir, sonra `--config` ile kullanabilirsiniz:

```bash
# Dahili kuralları JSON'a aktar
python bookmark_organizer.py --export-config my_categories.json

# Düzenlenmiş dosyayla çalıştır
python bookmark_organizer.py --config my_categories.json
python converter.py bookmarks.html out.md --config my_categories.json
```

### 🤖 AI Kategorizasyon (POC)

Gemini API ile yapay zeka destekli kategorizasyon için:

```bash
export GEMINI_API_KEY=<your-gemini-api-key>
python ai_categorizer.py bookmarks.html --output categorized.json
```

**Not:** AI kategorizasyon için `google-generativeai` kütüphanesi gereklidir:
```bash
pip install -r requirements-ai.txt
```

### ✅ Testler

Proje harici test bağımlılığı kullanmaz; standart `unittest` yeterlidir:

```bash
python -m unittest discover -s tests -v
```

-----

## Özelleştirme 🎨

Kategori kurallarının **tek kaynağı** `categories.py` dosyasındaki `CATEGORIES`
sözlüğüdür.

  * **Yeni Kategori Ekleme:**
    ```python
    "Yeni Kategori Adı": {
        "keywords": ["anahtar kelime1", "anahtar kelime2"],
        "sub": {
            "Alt Kategori Adı": ["alt anahtar kelime"]
        }
    }
    ```
  * **Mevcut Kategorileri Düzenleme:** Mevcut kategori ve alt kategorilerin `keywords` listelerini veya doğrudan link listelerini değiştirebilirsiniz.
  * **Kodu değiştirmeden kural kullanmak:** Yukarıdaki `--export-config` / `--config` akışını kullanın. Program config dosyanızı asla üzerine yazmaz.

Unutmayın, değişiklikleriniz ne kadar spesifik olursa, kategorizasyon o kadar isabetli olacaktır. Biraz deneme yanılma ile mükemmel düzeni yakalayabilirsiniz\!

-----

## Katkıda Bulunma 🤝

Geliştirmeye açık bir proje\! Her türlü katkı, hata bildirimi veya özellik önerisi memnuniyetle karşılanır. Bir pull request göndermekten çekinmeyin\!

-----

## Lisans 📄

Bu proje MIT Lisansı altında lisanslanmıştır. Daha fazla bilgi için `LICENSE` dosyasına bakın.


## English
Organizing your bookmarks has never been easier\! This Python script reads your HTML-formatted bookmarks (like those exported from your browser), intelligently categorizes them based on their content and URL, and then provides you with a neatly organized, hierarchical HTML bookmark file. Say goodbye to endless searching and hello to perfectly sorted bookmarks\! ✨

## Features ✨

  * **Smart Categorization:** Analyzes bookmark titles and URLs to automatically assign them to predefined categories (e.g., Tech & Software, Movies & Series, Culture & Life).
  * **Word-Boundary Matching:** Keywords match whole tokens only — the "ai" inside "gmail.com" or the "ml" inside "index.html" no longer misfires.
  * **Hierarchical Structure:** Creates subcategories under main categories for more detailed organization. For instance, under "Tech & Software," you might find "AI & Machine Learning" or "Web Development."
  * **Customizable Rules:** Rules live in the `CATEGORIES` dictionary inside `categories.py`; export them to JSON and load them back with `--config`.
  * **Easy to Use:** Organize your bookmarks in seconds with a single Python script.
  * **HTML Output:** Exports your organized bookmarks in standard HTML format, making them easy to import into any browser.
  * **Markdown Export:** Export organized bookmarks in Markdown format for documentation or Git repos.
  * **Dead Link Checker:** Verify if your bookmarked URLs are still alive (TLS verification is on by default).
  * **Unmatched Link Report:** `--report-unmatched` lists every link no rule matched — the practical way to grow your rule set.
  * **AI Categorization (POC):** Use Google Gemini for intelligent, AI-powered categorization.
  * **Tests & CI:** Zero extra dependencies — `unittest` suite plus a GitHub Actions gate.

## How It Works ⚙️

The heart of the script is the `CATEGORIES` dictionary in `categories.py`. It holds the keywords or direct URLs for each category and subcategory, and the script compares your bookmark titles and URLs against them.

Keywords are matched on **word boundaries**: `ai` matches "AI" or "Yapay Zeka" as a whole token, but never the "ai" inside "gmail.com"; likewise `ml` does not match inside "index.html". Special cases for YouTube links (theater, concerts, documentaries) are handled as well.

-----

## Installation 🚀

1.  **Install Python:** Make sure you have Python 3 installed on your computer. If not, you can download it from [python.org](https://www.python.org/downloads/).
2.  **Install Required Libraries:** The core script needs `BeautifulSoup4` and `requests`:
    ```bash
    pip install -r requirements.txt
    ```
    For AI categorization as well:
    ```bash
    pip install -r requirements-ai.txt
    ```
3.  **Download the Script:** Clone this repository or download the `bookmark_organizer.py` file.

-----

## Usage 🧑‍💻

1.  **Export Your Bookmarks:** Export your bookmarks as an HTML file from your browser (Chrome, Firefox, Edge, etc.). You can usually find an "Export Bookmarks" option in your "Bookmark Manager" or "Bookmarks" menu.
2.  **Rename the File:** Rename the exported HTML file to `bookmarks.html` and place it in the same folder as the `bookmark_organizer.py` script.
3.  **Run the Script:** Open your terminal or command prompt, navigate to the folder where the script is located, and run the following command:
    ```bash
    python bookmark_organizer.py
    ```
4.  **Check the Output:** Once the process is complete, a new file named `bookmarks_organized.html` will be created in the same folder. This file contains your newly organized bookmarks.

### Markdown Export

To export organized bookmarks in Markdown format:

```bash
python bookmark_organizer.py --markdown
python converter.py bookmarks.html
```

### Dead Link Checker

To check if bookmarked URLs are still alive:

```bash
python bookmark_organizer.py --check-links
python link_checker.py bookmarks.html --output report.txt --timeout 10 --workers 5
```

TLS certificate verification is **on by default**. Only turn it off for internal
hosts with broken certificates:

```bash
python link_checker.py bookmarks.html --insecure
```

### Unmatched Link Report

Dump every link that no rule matched (they end up in the "Other" bucket) into a
tab-separated report — the most practical way to grow your rule set:

```bash
python bookmark_organizer.py --report-unmatched unmatched_report.txt
```

### Custom Rule File

The program **never** overwrites your rule file. Export the built-in rules to
JSON, edit them, then load them back with `--config`:

```bash
python bookmark_organizer.py --export-config my_categories.json
python bookmark_organizer.py --config my_categories.json
```

### AI Categorization (POC)

To use Gemini AI for intelligent categorization:

```bash
export GEMINI_API_KEY=<your-gemini-api-key>
python ai_categorizer.py bookmarks.html --output categorized.json
```

**Note:** AI categorization requires the `google-generativeai` package:
```bash
pip install -r requirements-ai.txt
```

### Tests

The project uses the standard library `unittest` — no extra test dependency:

```bash
python -m unittest discover -s tests -v
```

-----

## Customization 🎨

The single source of truth for category rules is the `CATEGORIES` dictionary in `categories.py`.

  * **Adding a New Category:**
    ```python
    "New Category Name": {
        "keywords": ["keyword1", "keyword2"],
        "sub": {
            "Subcategory Name": ["sub_keyword"]
        }
    }
    ```
  * **Modifying Existing Categories:** You can change the `keywords` lists or direct link lists for existing categories and subcategories.
  * **Using rules without touching the code:** use the `--export-config` / `--config` flow described above. The program never writes over your file.

Remember, the more specific your modifications, the more accurate the categorization will be. A little trial and error will help you achieve the perfect organization\!

-----

## Contributing 🤝

This is an open-source project\! All contributions, bug reports, or feature suggestions are welcome. Feel free to submit a pull request\!

-----

## License 📄

This project is licensed under the MIT License. See the `LICENSE` file for more details.

-----
