import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import yt_dlp
import asyncio
import os
import re
from pathlib import Path
from telethon import TelegramClient

# --- CONFIG ---
API_ID = 20529421
API_HASH = '4e9fbc084cf55a92d34b2c2ad61849ad'

def get_session_path():
    base_dir = os.getenv('APPDATA') if os.name == 'nt' else os.path.expanduser("~")
    folder = os.path.join(base_dir, "UniversalDownloaderApp")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "tg_session")

SESSION_NAME = get_session_path()

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', str(text))

class DownloadRow:
    def __init__(self, parent, url, save_path, mode="VIDEO", format_str="best"):
        self.frame = tk.Frame(parent, bg="#1E2227", bd=1, relief="flat")
        self.frame.pack(fill="x", pady=8, padx=10)
        
        self.url, self.save_path, self.mode, self.format_str = url, Path(save_path), mode, format_str
        self.is_cancelled = False

        self.title_label = tk.Label(self.frame, text=f"[{mode}] {self.save_path.name}", 
                                    font=("Segoe UI", 10, "bold"), bg="#1E2227", fg="#18e86d", anchor="w")
        self.title_label.pack(fill="x", padx=12, pady=(8, 2))

        self.progress = ttk.Progressbar(self.frame, style="Horizontal.TProgressbar", length=500, mode="determinate")
        self.progress.pack(fill="x", padx=12, pady=5)

        self.status_label = tk.Label(self.frame, text="Preparing...", font=("Consolas", 10), bg="#1E2227", fg="#CCCCCC")
        self.status_label.pack(side="left", padx=12, pady=(0, 8))

        self.cancel_btn = tk.Button(self.frame, text="Cancel", bg="#ff4444", fg="white", relief="flat", 
                                   command=self.cancel, font=("Segoe UI", 8, "bold"), cursor="hand2", padx=10)
        self.cancel_btn.pack(side="right", padx=12, pady=(0, 8))

        threading.Thread(target=self.start_engine, daemon=True).start()

    def cancel(self):
        self.is_cancelled = True
        self.status_label.config(text="Cancelled", fg="#ff4444")
        self.cancel_btn.config(text="Remove", command=self.frame.destroy, bg="#444")

    def update_ui(self, percent, speed="0 MiB/s", eta="00:00", status=None):
        def _upd():
            self.progress['value'] = percent
            if status: display_text = status
            else:
                s, e = strip_ansi(speed).strip(), strip_ansi(eta).strip()
                display_text = f"{percent:.1f}%  •  {s}  •  ETA: {e}"
            self.status_label.config(text=display_text)
        self.frame.after(0, _upd)

    def start_engine(self):
        if self.mode == "TELEGRAM": asyncio.run(self.run_telegram())
        else: self.run_ytdlp()

    def run_ytdlp(self):
        def hook(d):
            if self.is_cancelled: raise Exception("User Cancelled")
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
                p = (d.get('downloaded_bytes', 0) / total) * 100
                self.update_ui(p, d.get('_speed_str', '0 MiB/s'), d.get('_eta_str', '00:00'))
            elif d['status'] == 'finished':
                self.update_ui(100, status="Finalizing Video (FFmpeg)...")

        ydl_opts = {'outtmpl': str(self.save_path), 'format': self.format_str, 'progress_hooks': [hook],
                    'merge_output_format': 'mp4', 'quiet': True, 'noprogress': True, 'color': 'no_color'}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([self.url])
            self.finish("✅ Complete")
        except Exception as e:
            if not self.is_cancelled: self.finish(f"❌ Error: {str(e)[:40]}", color="#ff4444")

    async def run_telegram(self):
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        try:
            await client.connect()
            m = re.match(r"(?:https?://)?(?:t\.me|telegram\.me)/([\w_]+)/(\d+)", self.url)
            msg = await client.get_messages(m.group(1), ids=int(m.group(2)))
            if msg and msg.media:
                await msg.download_media(file=str(self.save_path), 
                                        progress_callback=lambda c, t: self.update_ui((c/t)*100, status=f"Downloading: {(c/t)*100:.1f}%"))
                self.finish("✅ Complete")
        except: self.finish("❌ Failed", color="#ff4444")
        finally: await client.disconnect()

    def finish(self, text, color="#00ff95"):
        self.frame.after(0, lambda: [self.status_label.config(text=text, fg=color), self.progress.configure(value=100),
                                     self.cancel_btn.config(text="Close", bg="#333", command=self.frame.destroy)])

class UniversalDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Universal Downloader Pro")
        self.root.geometry("850x650")
        self.root.configure(bg="#181B20")

        # Header
        header = tk.Frame(root, bg="#181B20")
        header.pack(fill="x", padx=20, pady=15)
        tk.Label(header, text="UNIVERSAL DOWNLOADER", font=("Segoe UI", 18, "bold"), bg="#181B20", fg="#18e86d").pack(side="left")

        # Input UI
        input_frame = tk.Frame(root, bg="#1E2227", padx=15, pady=15)
        input_frame.pack(fill="x", padx=20)
        
        self.url_entry = tk.Entry(input_frame, font=("Segoe UI", 12), bg="#fff", fg="#000", relief="flat")
        self.url_entry.pack(fill="x", pady=(5, 10))
        self.url_entry.bind("<Return>", lambda e: self.fetch_info()) 

        q_row = tk.Frame(input_frame, bg="#1E2227")
        q_row.pack(fill="x")
        
        self.quality_var = tk.StringVar(value="Best Quality")
        self.quality_combo = ttk.Combobox(q_row, textvariable=self.quality_var, state="readonly", width=35)
        self.quality_combo.pack(side="left", padx=10)
        
        self.fetch_btn = tk.Button(q_row, text="Analyze Link", bg="#00d7ff", font=("Segoe UI", 9, "bold"), 
                                  command=self.fetch_info, relief="flat", padx=15, cursor="hand2")
        self.fetch_btn.pack(side="left")

        self.add_btn = tk.Button(input_frame, text="ADD TO DOWNLOAD QUEUE", bg="#18e86d", font=("Segoe UI", 11, "bold"), 
                                relief="flat", command=self.handle_add, state="disabled", pady=8, cursor="hand2")
        self.add_btn.pack(fill="x", pady=(15, 0))

        # --- REFINED SMOOTH SCROLL CANVAS ---
        self.canvas = tk.Canvas(root, bg="#181B20", highlightthickness=0)
        self.scroll_frame = tk.Frame(self.canvas, bg="#181B20")
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", width=810)
        self.canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)

        # Pixel-based Scroll State
        self.target_pixel = 0
        self.current_pixel = 0
        
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.scroll_frame.bind("<Configure>", self._on_frame_configure)

        self._smooth_scroll_loop()
        self.formats_map = {}

    def _on_frame_configure(self, event):
        # Update the scrollable area when items are added
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        # Determine total scrollable height
        bbox = self.canvas.bbox("all")
        if not bbox: return
        
        content_height = bbox[3] - bbox[1]
        canvas_height = self.canvas.winfo_height()
        max_scroll = max(0, content_height - canvas_height)

        # Calculate movement (Windows delta is usually 120, we use 60px per notch)
        move = int(-1 * (event.delta / 120) * 60)
        
        # Update target and CLAMP immediately to bounds
        self.target_pixel = max(0, min(max_scroll, self.target_pixel + move))

    def _smooth_scroll_loop(self):
        # Precise Lerp for pixel movement
        diff = self.target_pixel - self.current_pixel
        if abs(diff) > 0.5:
            self.current_pixel += diff * 0.15 # 15% closure per frame (very smooth)
            # Convert pixel position back to fraction for Tkinter
            bbox = self.canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                if content_height > 0:
                    self.canvas.yview_moveto(self.current_pixel / content_height)
        else:
            self.current_pixel = self.target_pixel
            
        self.root.after(10, self._smooth_scroll_loop)

    def fetch_info(self):
        url = self.url_entry.get().strip()
        if not url: return
        self.fetch_btn.config(text="Analyzing...", state="disabled", bg="#555")
        self.add_btn.config(state="disabled")
        threading.Thread(target=self._get_formats, args=(url,), daemon=True).start()

    def _get_formats(self, url):
        try:
            if "t.me" in url:
                res = ["Telegram Media"]; self.formats_map = {"Telegram Media": "best"}
            else:
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    formats = info.get('formats', [])
                    s_res = {2160: "4K (Ultra HD)", 1440: "2K (QHD)", 1080: "1080p (Full HD)", 720: "720p (HD)", 480: "480p", 360: "360p"}
                    fh = sorted(list(set(f.get('height') for f in formats if f.get('height'))), reverse=True)
                    res = ["Best Quality"]; self.formats_map = {"Best Quality": "bestvideo+bestaudio/best"}
                    for h in fh:
                        if h in s_res:
                            label = s_res[h]
                            self.formats_map[label] = f"bestvideo[height<={h}]+bestaudio/best"
                            res.append(label)
                    res.append("Audio Only (MP3)"); self.formats_map["Audio Only (MP3)"] = "bestaudio/best"
            
            self.root.after(0, lambda: [
                self.quality_combo.configure(values=res), 
                self.quality_var.set(res[0]),
                self.add_btn.config(state="normal"),
                self.fetch_btn.config(text="Analyze Link", state="normal", bg="#00d7ff")
            ])
        except Exception as e:
            self.root.after(0, lambda: [
                messagebox.showerror("Error", f"Failed to analyze: {str(e)[:50]}"),
                self.fetch_btn.config(text="Analyze Link", state="normal", bg="#00d7ff")
            ])

    def handle_add(self):
        url, q_label = self.url_entry.get().strip(), self.quality_var.get()
        fmt = self.formats_map.get(q_label, "best")
        ext = ".mp3" if "Audio" in q_label else ".mp4"
        save_path = filedialog.asksaveasfilename(defaultextension=ext)
        if save_path:
            DownloadRow(self.scroll_frame, url, save_path, "TELEGRAM" if "t.me" in url else "VIDEO", fmt)
            self.url_entry.delete(0, tk.END)
            self.add_btn.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style(); style.theme_use("clam")
    style.configure("Horizontal.TProgressbar", troughcolor="#23272e", background="#18e86d", bordercolor="#181B20", thickness=15)
    app = UniversalDownloader(root)
    root.mainloop()