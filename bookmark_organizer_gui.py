import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import os
from bookmark_organizer import categorize_link, add_to_structure, create_html_from_structure, CATEGORIES
from bs4 import BeautifulSoup, Doctype

class BookmarkOrganizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bookmark Organizer")
        self.root.geometry("800x600")
        
        # Variables
        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Hazır")
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # File selection
        ttk.Label(main_frame, text="Giriş Dosyası:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.input_file, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="Seç", command=self.select_input_file).grid(row=0, column=2)
        
        ttk.Label(main_frame, text="Çıkış Dosyası:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_file, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="Seç", command=self.select_output_file).grid(row=1, column=2)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Seçenekler", padding="10")
        options_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Orijinal dosyayı yedekle", variable=self.backup_var).grid(row=0, column=0, sticky=tk.W)
        
        self.open_result_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Sonucu tarayıcıda aç", variable=self.open_result_var).grid(row=1, column=0, sticky=tk.W)
        
        # Process button
        self.process_btn = ttk.Button(main_frame, text="Organize Et", command=self.start_processing)
        self.process_btn.grid(row=3, column=0, columnspan=3, pady=20)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Status label
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=5, column=0, columnspan=3, pady=5)
        
        # Results text area
        self.results_text = tk.Text(main_frame, height=15, width=80)
        self.results_text.grid(row=6, column=0, columnspan=3, pady=10)
        
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.results_text.yview)
        scrollbar.grid(row=6, column=3, sticky=(tk.N, tk.S))
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)
    
    def select_input_file(self):
        filename = filedialog.askopenfilename(
            title="Bookmark dosyasını seçin",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )
        if filename:
            self.input_file.set(filename)
            # Auto-suggest output filename
            if not self.output_file.get():
                base, ext = os.path.splitext(filename)
                self.output_file.set(f"{base}_organized{ext}")
    
    def select_output_file(self):
        filename = filedialog.asksaveasfilename(
            title="Organize edilmiş dosyayı kaydet",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
            defaultextension=".html"
        )
        if filename:
            self.output_file.set(filename)
    
    def start_processing(self):
        if not self.input_file.get():
            messagebox.showerror("Hata", "Lütfen giriş dosyasını seçin!")
            return
        
        if not self.output_file.get():
            messagebox.showerror("Hata", "Lütfen çıkış dosyasını belirtin!")
            return
        
        # Disable button and start processing in thread
        self.process_btn.config(state='disabled')
        self.progress_var.set(0)
        self.results_text.delete(1.0, tk.END)
        
        thread = threading.Thread(target=self.process_bookmarks)
        thread.daemon = True
        thread.start()
    
    def process_bookmarks(self):
        try:
            self.update_status("Dosya okunuyor...")
            self.update_progress(10)
            
            # Backup if requested
            if self.backup_var.get():
                backup_file = self.input_file.get() + ".backup"
                import shutil
                shutil.copy2(self.input_file.get(), backup_file)
                self.log_result(f"Yedek oluşturuldu: {backup_file}")
            
            # Read input file
            with open(self.input_file.get(), 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.update_status("HTML parse ediliyor...")
            self.update_progress(20)
            
            soup = BeautifulSoup(content, 'html.parser')
            organized_structure = {}
            
            all_links = soup.find_all('a')
            total_links = len(all_links)
            self.log_result(f"Toplam {total_links} link bulundu")
            
            self.update_status("Linkler kategorilere ayrılıyor...")
            
            # Process links with progress updates
            for i, link in enumerate(all_links):
                title = link.text.strip()
                url = link.get('href', '')
                if not title and not url:
                    continue
                
                add_date = link.get('add_date', '')
                icon = link.get('icon', '')
                item = {'type': 'link', 'title': title, 'url': url, 'add_date': add_date, 'icon': icon}
                
                path = categorize_link(title, url, CATEGORIES)
                if path:
                    add_to_structure(organized_structure, path, item)
                else:
                    add_to_structure(organized_structure, ["Diğer"], item)
                
                # Update progress
                progress = 20 + (i / total_links) * 60
                self.update_progress(progress)
            
            self.update_status("HTML oluşturuluyor...")
            self.update_progress(85)
            
            # Create new HTML
            new_soup = BeautifulSoup("", 'html.parser')
            doctype = Doctype('NETSCAPE-Bookmark-file-1')
            new_soup.append(doctype)
            
            meta = new_soup.new_tag('META', attrs={'HTTP-EQUIV': 'Content-Type', 'CONTENT': 'text/html; charset=UTF-8'})
            new_soup.append(meta)
            
            title_tag = new_soup.new_tag('TITLE')
            title_tag.string = 'Organized Bookmarks'
            new_soup.append(title_tag)
            
            h1_tag = new_soup.new_tag('H1')
            h1_tag.string = 'Organized Bookmarks'
            new_soup.append(h1_tag)
            
            final_dl = create_html_from_structure(organized_structure, new_soup)
            new_soup.append(final_dl)
            
            self.update_status("Dosya kaydediliyor...")
            self.update_progress(95)
            
            # Save file
            with open(self.output_file.get(), 'w', encoding='utf-8') as f:
                f.write(new_soup.prettify())
            
            self.update_progress(100)
            self.update_status("Tamamlandı!")
            
            # Show statistics
            stats = self.calculate_stats(organized_structure)
            self.show_statistics(stats)
            
            # Open result if requested
            if self.open_result_var.get():
                import webbrowser
                webbrowser.open(f"file://{os.path.abspath(self.output_file.get())}")
            
            messagebox.showinfo("Başarılı", f"Bookmarklar başarıyla organize edildi!\n{self.output_file.get()}")
            
        except Exception as e:
            self.log_result(f"HATA: {str(e)}")
            messagebox.showerror("Hata", f"İşlem sırasında hata oluştu:\n{str(e)}")
        finally:
            self.process_btn.config(state='normal')
    
    def calculate_stats(self, structure):
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
    
    def show_statistics(self, stats):
        self.log_result("\n=== İSTATİSTİKLER ===")
        for category, count in sorted(stats.items()):
            self.log_result(f"{category}: {count} link")
    
    def update_status(self, message):
        self.root.after(0, lambda: self.status_var.set(message))
    
    def update_progress(self, value):
        self.root.after(0, lambda: self.progress_var.set(value))
    
    def log_result(self, message):
        self.root.after(0, lambda: self.results_text.insert(tk.END, message + "\n"))
        self.root.after(0, lambda: self.results_text.see(tk.END))

def main():
    root = tk.Tk()
    app = BookmarkOrganizerGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()