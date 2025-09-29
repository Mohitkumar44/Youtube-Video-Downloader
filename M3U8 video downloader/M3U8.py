import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import yt_dlp
from pathlib import Path

def seconds_to_time(seconds):
    try:
        seconds = int(seconds)
        if seconds > 3600:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            return f"{h} hour{'s' if h > 1 else ''} {m} min"
        elif seconds > 60:
            m = seconds // 60
            s = seconds % 60
            return f"{m} min {s} sec"
        else:
            return f"{seconds} seconds"
    except Exception:
        return "calculating..."

def clean_speed(speed_str):
    if not speed_str or speed_str == "N/A":
        return "calculating speed..."
    clean = str(speed_str).replace("ï¿½", "").replace("B/s", " per second")
    return clean

def start_new_download():
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Error", "Please enter a video link")
        return
    save_path = filedialog.asksaveasfilename(
        defaultextension=".mp4",
        filetypes=[("MP4 Video", "*.mp4"), ("All files", "*.*")],
        title="Save video as..."
    )
    if not save_path:
        return
    DownloadRow(downloads_frame, url, save_path)
    url_entry.delete(0, tk.END)

class DownloadRow:
    def __init__(self, parent, url, save_path):
        self.frame = tk.Frame(parent, bg="#181B20", bd=1, relief="solid")
        self.frame.pack(fill="x", pady=(3, 7), padx=5)

        self.url = url
        self.save_path = Path(save_path)
        self.output_base = self.save_path.stem
        self.folder = self.save_path.parent

        display_url = (self.url[:60] + '...') if len(self.url) > 60 else self.url
        tk.Label(self.frame, text=f"Downloading: {display_url}", font=("Segoe UI", 10, "bold"),
                 bg="#181B20", fg="#18e86d").pack(anchor="w", pady=(6, 2), padx=8)
        
        self.progress = ttk.Progressbar(self.frame, style="Horizontal.TProgressbar", orient="horizontal",
                                        length=460, mode="determinate", maximum=100)
        self.progress.pack(pady=4, padx=8)
        
        self.status_label = tk.Label(self.frame, text="Starting download...", font=("Segoe UI", 10, "bold"),
                                     bg="#181B20", fg="#ffc107")
        self.status_label.pack(anchor="w", padx=8)

        self.details_label = tk.Label(self.frame, text="", font=("Segoe UI", 9), bg="#181B20", fg="#CCCCCC")
        self.details_label.pack(anchor="w", padx=8, pady=(0, 6))

        self.cancel_btn = tk.Button(self.frame, text="Cancel", font=("Segoe UI", 9),
                                   bg="#ff4444", fg="#fff", relief="flat",
                                   command=self.cancel_download, width=10, cursor="hand2")
        self.cancel_btn.pack(side="right", pady=6, padx=10)

        self.is_cancelled = False
        threading.Thread(target=self.run_download, daemon=True).start()

    def cancel_download(self):
        self.is_cancelled = True
        self.status_label.config(text="Download cancelled by user.", fg="#ff4444")
        self.cancel_btn.config(state='disabled')

    def run_download(self):
        def hook(d):
            if self.is_cancelled:
                raise Exception("Download cancelled by user.")
            status = d.get('status', '')
            if status == 'downloading':
                downloaded = d.get('downloaded_bytes') or 0
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                if total > 0:
                    percent = downloaded / total * 100
                    self.progress['value'] = percent

                    downloaded_mb = downloaded / (1024 * 1024)
                    total_mb = total / (1024 * 1024)

                    eta = d.get('eta', 0)
                    time_left = seconds_to_time(eta)
                    speed = clean_speed(d.get('_speed_str'))

                    self.status_label.config(
                        text=f"Downloading: {percent:.0f}% • Speed: {speed} • ETA: {time_left}",
                        fg="#00d7ff"
                    )
                    self.details_label.config(
                        text=f"Downloaded {downloaded_mb:.2f} MB of {total_mb:.2f} MB"
                    )
                else:
                    self.status_label.config(text="Retrieving video info...", fg="#00d7ff")
                    self.details_label.config(text="")
            elif status == 'finished':
                self.status_label.config(text="Finalizing and merging video...", fg="#cccc00")
                self.details_label.config(text="")
            elif status == 'error':
                self.status_label.config(text="Error during download.", fg="#ff4444")
            else:
                self.status_label.config(text=f"Status: {status}", fg="#cccccc")

        ydl_opts = {
            'outtmpl': str(self.save_path),       # Full user path with filename
            'format': 'best',
            'progress_hooks': [hook],
            'quiet': True,
            'noprogress': True,
            'nocheckcertificate': True,
            'continuedl': False,                   # Disable resuming partial downloads
            'merge_output_format': None,           # Disable ffmpeg merging
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.status_label.config(
                text=f"✅ Download complete: {self.save_path.name}",
                fg="#00ff95"
            )
            self.details_label.config(text=f"Saved to: {self.save_path.parent}")
            self.cancel_btn.config(text="Close", command=self.close_row, bg="#24d158")
        except Exception as e:
            if self.is_cancelled:
                pass
            else:
                self.status_label.config(text=f"❌ Download failed: {str(e)}", fg="#ff4444")
                self.details_label.config(text="")
                self.cancel_btn.config(text="Close", command=self.close_row, bg="#666")

    def close_row(self):
        self.frame.destroy()

# Scrollable downloads frame
root = tk.Tk()
root.title("M3U8 Video Downloader")
root.geometry("720x540")
root.configure(bg="#181B20")
root.resizable(False, False)

style = ttk.Style(root)
style.theme_use("clam")
style.configure("Horizontal.TProgressbar",
                troughcolor="#23272e",
                background="#24d158",
                bordercolor="#23272e",
                lightcolor="#24d158",
                darkcolor="#24d158",
                thickness=13)

main_frame = tk.Frame(root, bg="#181B20")
main_frame.pack(fill="x", padx=18, pady=12)

tk.Label(main_frame, text="Pro Coder", font=("Segoe UI", 17, "bold"),
         bg="#181B20", fg="#18e86d").pack(pady=(8, 6))

tk.Label(main_frame, text="M3U8 Link:", font=("Segoe UI", 13, "bold"),
         bg="#181B20", fg="#00d7ff", anchor="w").pack(anchor="w")

url_entry = tk.Entry(main_frame, width=70, font=("Segoe UI", 12), bg="#fff", fg="#222",
                     insertbackground="#444", relief="flat")
url_entry.pack(ipady=5, pady=(2,12), anchor="w")

download_btn = tk.Button(main_frame, text="Download", font=("Segoe UI", 13, "bold"),
                         bg="#24d158", fg="#fff", activebackground="#1caf4e", activeforeground="#cee",
                         relief="flat", cursor="hand2", command=start_new_download, width=18, height=2, bd=0)
download_btn.pack(anchor="w")

# Scrollable frame setup for downloads
downloads_canvas = tk.Canvas(root, bg="#181B20", highlightthickness=0)
scrollbar = ttk.Scrollbar(root, orient="vertical", command=downloads_canvas.yview)
downloads_frame = tk.Frame(downloads_canvas, bg="#181B20")

downloads_frame.bind(
    "<Configure>",
    lambda e: downloads_canvas.configure(
        scrollregion=downloads_canvas.bbox("all")
    )
)

downloads_canvas.create_window((0, 0), window=downloads_frame, anchor="nw")
downloads_canvas.configure(yscrollcommand=scrollbar.set)

downloads_canvas.pack(side="left", fill="both", expand=True, padx=18, pady=12)
scrollbar.pack(side="right", fill="y")

root.mainloop()
