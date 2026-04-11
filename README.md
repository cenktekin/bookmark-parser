# Bookmark Organizer 🔖

[Türkçe Oku](README.md#türkçe) | [Read in English](README.md#english)

---

## Türkçe

Yer imlerinizi düzenlemek hiç bu kadar kolay olmamıştı! Bu Python uygulaması, HTML formatındaki yer imlerinizi (örneğin tarayıcınızdan dışa aktardığınız) okur, içeriğine ve URL'sine göre akıllıca kategorize eder ve size düzenli, hiyerarşik bir HTML yer imi dosyası olarak geri verir. Artık aradığınız linki bulmak için dakikalar harcamanıza gerek kalmayacak!

🎯 **Yeni**: Artık hem **GUI arayüzü** hem de **komut satırı** versiyonu mevcut!

## Özellikler ✨

  * **🖥️ GUI Arayüzü:** Kullanıcı dostu grafik arayüzü ile dosya seçme, ilerleme takibi ve sonuç görüntüleme
  * **⚡ Akıllı Kategorizasyon:** Yer imi başlıklarını ve URL'lerini analiz ederek önceden tanımlanmış kategorilere (Teknoloji & Yazılım, Film & Dizi, Kültür & Yaşam vb.) otomatik olarak atar
  * **📊 Hiyerarşik Yapı:** Ana kategoriler altında alt kategoriler oluşturarak daha detaylı bir düzenleme sağlar
  * **🔧 Özelleştirilebilir Kurallar:** Kategori yapılandırmasını JSON dosyası ile kolayca düzenleyebilirsiniz
  * **💾 Otomatik Yedekleme:** İşlem öncesi otomatik yedek dosyası oluşturur
  * **📈 Detaylı İstatistikler:** Kategori başına link sayıları ve işlem raporu
  * **🌐 HTML Çıkışı:** Standart HTML formatında dışa aktarım

## Nasıl Çalışır? ⚙️

Betiğin kalbi, `CATEGORIES` adlı devasa bir sözlükte yatıyor. Bu sözlük, her bir kategori ve alt kategori için anahtar kelimeler veya doğrudan URL'ler içeriyor. Betik, yer imlerinizin başlıklarını ve URL'lerini bu anahtar kelimelerle karşılaştırarak en uygun kategoriye yerleştiriyor. Özellikle YouTube linkleri için tiyatro, konser, belgesel gibi özel durumları bile ele alıyor, tam bir akıllı asistan\! 😉

-----

## Kurulum 🚀

1.  **Python'ı Yükleyin:** Bilgisayarınızda Python 3 yüklü olduğundan emin olun. Yoksa, [python.org](https://www.python.org/downloads/) adresinden indirebilirsiniz.
2.  **Gerekli Kütüphaneleri Yükleyin:** Betik, `BeautifulSoup4` kütüphanesini kullanır. Aşağıdaki komutla yükleyebilirsiniz:
    ```bash
    pip install beautifulsoup4
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

-----

## Özelleştirme 🎨

`bookmark_organizer.py` dosyasını açarak **`CATEGORIES`** sözlüğünü kendi ihtiyaçlarınıza göre düzenleyebilirsiniz.

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
  * **Hierarchical Structure:** Creates subcategories under main categories for more detailed organization. For instance, under "Tech & Software," you might find "AI & Machine Learning" or "Web Development."
  * **Customizable Rules:** Easily add your own categories and keywords or modify existing ones by editing the `CATEGORIES` dictionary.
  * **Easy to Use:** Organize your bookmarks in seconds with a single Python script.
  * **HTML Output:** Exports your organized bookmarks in standard HTML format, making them easy to import into any browser.

## How It Works ⚙️

The heart of the script lies in a large dictionary called `CATEGORIES`. This dictionary contains keywords or direct URLs for each category and subcategory. The script compares your bookmark titles and URLs against these keywords to place them into the most suitable category. It even handles special cases for YouTube links, categorizing them as theater, concerts, or documentaries, acting like your personal smart assistant\! 😉

-----

## Installation 🚀

1.  **Install Python:** Make sure you have Python 3 installed on your computer. If not, you can download it from [python.org](https://www.python.org/downloads/).
2.  **Install Required Libraries:** The script uses the `BeautifulSoup4` library. You can install it using the following command:
    ```bash
    pip install beautifulsoup4
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

-----

## Customization 🎨

You can open the `bookmark_organizer.py` file and modify the `CATEGORIES` dictionary to suit your specific needs.

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

Remember, the more specific your modifications, the more accurate the categorization will be. A little trial and error will help you achieve the perfect organization\!

-----

## Contributing 🤝

This is an open-source project\! All contributions, bug reports, or feature suggestions are welcome. Feel free to submit a pull request\!

-----

## License 📄

This project is licensed under the MIT License. See the `LICENSE` file for more details.

-----
