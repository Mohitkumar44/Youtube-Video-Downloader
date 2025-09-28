import tkinter as tk
from tkinter import ttk, messagebox
import threading
import yt_dlp
import os
from pathlib import Path

def get_unique_filepath(folder, filename_base, ext):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{filename_base}.{ext}"
    filepath = folder / filename
    count = 1
    while filepath.exists():
        filename = f"{filename_base}{count}.{ext}"
        filepath = folder / filename
        count += 1
    return str(filepath)

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
    except:
        return "calculating..."

def clean_speed(speed_str):
    if not speed_str or speed_str == "N/A":
        return "calculating speed..."
    clean = str(speed_str).replace("ï¿½", "").replace("B/s", " per second")
    return clean

def download_video():
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Error", "Please enter a video link")
        return

    downloads = Path.home() / "Downloads" / "m3u8 video downloader"
    downloads.mkdir(parents=True, exist_ok=True)
    output_template = get_unique_filepath(downloads, "master", "mp4")
    output_base = os.path.splitext(os.path.basename(output_template))[0]

    download_btn.config(state='disabled', bg="#444", fg="#aaa")
    progress['value'] = 0
    progress_label.config(text="Starting your download...", fg="#ffc107")
    details_label.config(text="")

    def run_download():
        try:
            ydl_opts = {
                'outtmpl': str(downloads / (output_base + '.%(ext)s')),
                'merge_output_format': 'mp4',
                'format': 'best',
                'progress_hooks': [progress_hook],
                'quiet': True,
                'noprogress': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            progress_label.config(text=f"✅ Video saved as: {output_base}.mp4", fg="#00ff95")
            details_label.config(text="Check your Downloads folder → m3u8 video downloader")
        except Exception as e:
            progress_label.config(text=f"❌ Download failed: {str(e)}", fg="#ff4444")
        finally:
            download_btn.config(state='normal', bg="#24d158", fg="#fff")

    threading.Thread(target=run_download, daemon=True).start()

def progress_hook(d):
    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes') or 0
        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0

        if total > 0:
            percent = (downloaded / total) * 100
            progress['value'] = percent

            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)

            eta = d.get('eta', 0)
            time_left = seconds_to_time(eta)
            speed = clean_speed(d.get('_speed_str'))

            progress_label.config(
                text=f"📥 Downloading {percent:.0f}% • {speed} • {time_left} left", 
                fg="#00d7ff"
            )
            details_label.config(
                text=f"Downloaded: {downloaded_mb:.1f} MB of {total_mb:.1f} MB"
            )
        else:
            progress_label.config(text="📥 Downloading... getting file info", fg="#00d7ff")
    elif d['status'] == 'finished':
        progress_label.config(text="🔄 Almost done! Processing final video...", fg="#cccc00")

# --- UI SETUP ---
root = tk.Tk()
root.title("M3U8 Video Downloader")
root.geometry("650x270")
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
main_frame.pack(fill="both", expand=True, padx=18, pady=10)

tk.Label(main_frame, text="Pro Coder", font=("Segoe UI", 17, "bold"),
         bg="#181B20", fg="#18e86d").pack(pady=(8, 6))

tk.Label(main_frame, text="M3U8 Link:", font=("Segoe UI", 13, "bold"),
         bg="#181B20", fg="#00d7ff", anchor="w").pack(pady=(0,2))

url_entry = tk.Entry(main_frame, width=66, font=("Segoe UI", 12), bg="#ffffff", fg="#222", 
                    insertbackground="#444", relief="flat")
url_entry.pack(ipady=5, pady=(0,12))

download_btn = tk.Button(
    main_frame, text="Download", font=("Segoe UI", 13, "bold"),
    bg="#24d158", fg="#fff", activebackground="#1caf4e", activeforeground="#cee",
    relief="flat", cursor="hand2", command=download_video, width=16, height=2, bd=0)
download_btn.pack(pady=(0, 10))

progress = ttk.Progressbar(main_frame, style="Horizontal.TProgressbar", orient="horizontal", 
                          length=520, mode="determinate", maximum=100)
progress.pack(pady=(2, 4))

progress_label = tk.Label(main_frame, text="", font=("Segoe UI", 11, "bold"), bg="#181B20", fg="#ffc107")
progress_label.pack(pady=(0,1))
details_label = tk.Label(main_frame, text="", font=("Segoe UI", 10), bg="#181B20", fg="#CCCCCC")
details_label.pack()

root.mainloop()
