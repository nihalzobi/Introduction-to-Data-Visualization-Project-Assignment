import pyperclip
from pynput import keyboard
import pyautogui
import tkinter as tk
from tkinter import messagebox
import time
import threading
import requests
import queue
import sys

# --- AYARLAR ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_ADI = "gemma3:1b"
KISAYOL_METIN = keyboard.Key.f8

# Global değişkenler
root = None
gui_queue = queue.Queue()
kisayol_basildi = False
menu_acik = False

CEVIRI_DILLERI = {
    "🇬🇧 İngilizceye Çevir": "Bu metni İngilizceye çevir. Sadece çeviriyi ver.",
    "🇹🇷 Türkçeye Çevir": "Bu metni Türkçeye çevir. Sadece çeviriyi ver.",
    "🇩🇪 Almancaya Çevir": "Bu metni Almancaya çevir. Sadece çeviriyi ver.",
    "🇫🇷 Fransızcaya Çevir": "Bu metni Fransızcaya çevir. Sadece çeviriyi ver.",
    "🇪🇸 İspanyolcaya Çevir": "Bu metni İspanyolcaya çevir. Sadece çeviriyi ver.",
    "🇷🇺 Rusçaya Çevir": "Bu metni Rusçaya çevir. Sadece çeviriyi ver.",
    "🇯🇵 Japoncaya Çevir": "Bu metni Japoncaya çevir. Sadece çeviriyi ver.",
    "🇸🇦 Arapçaya Çevir": "Bu metni Arapçaya çevir. Sadece çeviriyi ver."
}

def ollama_cevap_al(prompt, model_adi):
    """Ollama API'den cevap al."""
    try:
        payload = {
            "model": model_adi,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
            },
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=180)

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()

        err_msg = f"Ollama API Hatası: {response.status_code}\nCevap: {response.text}"
        print(f"❌ {err_msg}")
        gui_queue.put((messagebox.showerror, ("API Hatası", err_msg)))
        return None

    except requests.exceptions.ConnectionError:
        err_msg = "Ollama'ya bağlanılamadı. Programın çalıştığından emin olun!\n(http://localhost:11434)"
        print(f"❌ {err_msg}")
        gui_queue.put((messagebox.showerror, ("Bağlantı Hatası", err_msg)))
        return None
    except Exception as e:
        err_msg = f"Beklenmeyen Hata: {e}"
        print(f"❌ {err_msg}")
        gui_queue.put((messagebox.showerror, ("Hata", err_msg)))
        return None

def strip_code_fence(text):
    if not text:
        return text
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:] if lines else []
        while lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned

def secili_metni_kopyala():
    sentinel = f"__AI_ASISTAN__{time.time_ns()}__"
    try:
        pyperclip.copy(sentinel)
    except Exception:
        pass

    pyautogui.hotkey("ctrl", "c")
    
    # Kopyalanan metni hızlıca yakalamak için kısa aralıklarla (20ms) kontrol et
    for _ in range(15):
        time.sleep(0.02)
        metin = pyperclip.paste()
        if metin and metin.strip() and metin != sentinel:
            return metin
            
    # Eğer ilk seferde yakalanamazsa veya kopyalama gerçekleşmezse tekrar dene
    pyautogui.hotkey("ctrl", "c")
    for _ in range(15):
        time.sleep(0.02)
        metin = pyperclip.paste()
        if metin and metin.strip() and metin != sentinel:
            return metin
            
    return ""

def sonuc_penceresi_goster(baslik, icerik, x=None, y=None):
    try:
        pencere = tk.Toplevel(root)
        pencere.title(baslik)
        
        geom_x = int(x + 10) if x is not None else 100
        geom_y = int(y + 10) if y is not None else 100
        
        geom_x_str = f"+{geom_x}" if geom_x >= 0 else f"{geom_x}"
        geom_y_str = f"+{geom_y}" if geom_y >= 0 else f"{geom_y}"
        
        if x is not None and y is not None:
            pencere.geometry(f"520x320{geom_x_str}{geom_y_str}")
        else:
            pencere.geometry("520x320")
            
        pencere.minsize(400, 250)
        pencere.attributes("-topmost", True)

        frame = tk.Frame(pencere, bg="#1f1f1f")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        text_alani = tk.Text(
            frame,
            wrap="word",
            bg="#2b2b2b",
            fg="white",
            insertbackground="white",
            font=("Segoe UI", 10),
            padx=10,
            pady=10,
        )
        kaydirma = tk.Scrollbar(frame, command=text_alani.yview)
        text_alani.configure(yscrollcommand=kaydirma.set)

        text_alani.pack(side="left", fill="both", expand=True)
        kaydirma.pack(side="right", fill="y")

        text_alani.insert("1.0", icerik)
        text_alani.config(state="disabled")

        alt_frame = tk.Frame(pencere, bg="#1f1f1f")
        alt_frame.pack(fill="x", padx=10, pady=(0, 10))

        def panoya_kopyala():
            pyperclip.copy(icerik)
            print("✅ Çeviri panoya kopyalandı.")

        tk.Button(
            alt_frame,
            text="Panoya Kopyala",
            command=panoya_kopyala,
            bg="#3d3d3d",
            fg="white",
            activebackground="#4d4d4d",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=6,
        ).pack(side="left")

        tk.Button(
            alt_frame,
            text="Kapat",
            command=pencere.destroy,
            bg="#3d3d3d",
            fg="white",
            activebackground="#4d4d4d",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=6,
        ).pack(side="right")

        pencere.focus_force()
        pencere.lift()
    except Exception as e:
        print(f"❌ Arayüz gösterimi sırasında hata: {e}")

def islemi_yap(komut_adi, secili_metin, prompt_emri, x=None, y=None):
    try:
        print("\n" + "="*40)
        print(f"🤖 İŞLEM BAŞLADI")
        print(f"🌍 Seçilen Dil: {komut_adi}")
        print(f"🧠 Model Adı: {MODEL_ADI}")
        print(f"📄 Seçili Metin: '{secili_metin}'")
        print("="*40)
        print("⏳ Ollama ile işleniyor, lütfen bekleyin...")

        full_prompt = f"{prompt_emri}:\n\n'{secili_metin}'"

        sonuc = ollama_cevap_al(full_prompt, MODEL_ADI)
        if not sonuc:
            print("❌ Sonuç alınamadı (Ollama boş veya hata döndürdü).")
            return

        sonuc = strip_code_fence(sonuc)
        if sonuc.startswith("'") and sonuc.endswith("'"):
            sonuc = sonuc[1:-1]

        gui_queue.put((sonuc_penceresi_goster, (komut_adi, sonuc, x, y)))
        print("✅ Çeviri başarıyla alındı ve pencerede gösterilmesi için kuyruğa eklendi.\n")

    except Exception as e:
        print(f"❌ İşlem sırasında bir hata oluştu: {e}")
        gui_queue.put((messagebox.showerror, ("Hata", f"İşlem sırasında hata oluştu: {e}")))

def process_queue():
    """Kuyruktaki GUI işlemlerini ana thread'de çalıştırır."""
    try:
        while True:
            try:
                task = gui_queue.get_nowait()
            except queue.Empty:
                break
            func, args = task
            func(*args)
    except Exception as e:
        print(f"❌ Kuyruk işlenirken hata oluştu: {e}")
    finally:
        if root:
            root.after(100, process_queue)

def reset_menu_acik():
    global menu_acik
    menu_acik = False

def menu_goster():
    """Metni kopyalar ve menüyü gösterir (ana thread)."""
    global menu_acik
    if menu_acik:
        return
    menu_acik = True

    try:
        print("🔍 Metin kopyalanıyor...")
        secili_metin = secili_metni_kopyala()
        if not secili_metin.strip():
            print("⚠️ Seçili metin bulunamadı!")
            messagebox.showwarning(
                "Seçim Bulunamadı",
                "Lütfen önce metin seçin, sonra F8 ile menüyü açın."
            )
            return

        print("🪟 Menü açılıyor...")
        dummy = tk.Toplevel(root)
        dummy.overrideredirect(True)
        x, y = pyautogui.position()
        dummy.geometry(f"1x1+{int(x)}+{int(y)}")
        dummy.attributes("-alpha", 0.0)
        dummy.attributes("-topmost", True)
        dummy.update_idletasks()
        dummy.focus_force()

        menu = tk.Menu(
            dummy,
            tearoff=0,
            bg="#2b2b2b",
            fg="white",
            activebackground="#4a4a4a",
            activeforeground="white",
            font=("Segoe UI", 10),
        )

        def komut_olustur(k_adi, s_metin, p_emri):
            def komut_calistir():
                try:
                    print(f"\n▶️ Menüden seçildi: {k_adi}")
                    mx, my = pyautogui.position()
                    threading.Thread(
                        target=islemi_yap, args=(k_adi, s_metin, p_emri, mx, my), daemon=True
                    ).start()
                except Exception as e:
                    print(f"❌ Komut başlatılamadı: {e}")
            return komut_calistir

        for dil_baslik, dil_prompt in CEVIRI_DILLERI.items():
            menu.add_command(label=dil_baslik, command=komut_olustur(dil_baslik, secili_metin, dil_prompt))

        menu.add_separator()
        menu.add_command(label="❌ İptal", command=lambda: print("İptal edildi."))

        try:
            menu.tk_popup(int(x), int(y))
        finally:
            menu.grab_release()
            # ÖNEMLİ DÜZELTME: Menü kapatıldıktan hemen sonra dummy'i yok etmek
            # Tkinter'da tıklanan komutun iptal olmasına sebep olabiliyor.
            root.after(200, dummy.destroy)

    except Exception as e:
        print(f"❌ Menü gösterilirken hata oluştu: {e}")
    finally:
        # Menü durumu flag'ini temizlemek için gecikme ekliyoruz
        root.after(300, reset_menu_acik)

def on_press(key):
    global kisayol_basildi, menu_acik
    try:
        if key == KISAYOL_METIN and not kisayol_basildi:
            kisayol_basildi = True
            if not menu_acik:
                gui_queue.put((menu_goster, ()))
    except AttributeError:
        pass

def on_release(key):
    global kisayol_basildi
    try:
        if key == KISAYOL_METIN:
            kisayol_basildi = False
    except AttributeError:
        pass

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 AI Asistan - Sadece Metin Çeviri")
    print("=" * 60)
    print(f"📦 Seçili Model: {MODEL_ADI}")
    print()
    print("🔧 Kullanım:")
    print("   F8 - Metin seç ve çeviri menüsünü aç")
    print()
    print("⚠️ Programı kapatmak için bu pencereyi kapatın veya Ctrl+C yapın.")
    print("=" * 60)

    try:
        test_response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if test_response.status_code == 200:
            print("✅ Ollama bağlantısı başarılı!")
        else:
            print("⚠️ Ollama'ya bağlanılamadı, servisi kontrol edin!")
    except Exception as e:
        print(f"⚠️ Ollama çalışmıyor olabilir! Hata: {e}")

    print("\n🎧 Klavye dinleniyor...\n")

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    root = tk.Tk()
    root.withdraw()
    root.after(100, process_queue)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Kapatılıyor...")
        sys.exit(0)
