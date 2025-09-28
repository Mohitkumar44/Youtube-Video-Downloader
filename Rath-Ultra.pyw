import yt_dlp
import tkinter as tk
import threading
import os
import sys
import glob
import webbrowser

DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")


class YouTubeDownloader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YT Video Downloader - Mohit Bhai 😎")
        self.geometry("450x230")
        self.resizable(False, False)
        self.configure(bg="#181a22")
        self.selected_format = tk.StringVar(value="Best")
        self.status_var = tk.StringVar(value="Paste YouTube URL and click Download")
        self.create_widgets()
        self.bind("<Return>", lambda e: self.start_download())
        self.status_details = {
            "percent": 0,
            "total_mib": "",
            "dl_mib": "",
            "speed": "",
            "eta": ""
        }
    
    def create_widgets(self):
        # Heading
        title = tk.Label(self, text="Pro Coder", font=("Segoe UI", 17, "bold"),
                         bg="#181a22", fg="#38d8ff")
        title.pack(pady=(14, 6))
        
        url_frame = tk.Frame(self, bg="#181a22")
        url_frame.pack(pady=2)
        tk.Label(url_frame, text="Link:", bg="#181a22", fg="#fafafa", font=("Segoe UI", 10, "bold")).pack(side="left", padx=3)
        self.url_entry = tk.Entry(url_frame, width=36, font=("Segoe UI", 11), borderwidth=0, relief="flat", highlightthickness=2, highlightcolor="#38d8ff")
        self.url_entry.pack(side="left", padx=6)
        self.url_entry.config(highlightbackground="#23233a")
        
        options_frame = tk.Frame(self, bg="#181a22")
        options_frame.pack(pady=3)
        tk.Label(options_frame, text="Quality:", bg="#181a22", fg="white", font=("Segoe UI", 10)).pack(side="left", padx=1)
        from tkinter import ttk
        self.fmt_menu = ttk.Combobox(options_frame, textvariable=self.selected_format,
                                     values=["Best", "1080p", "720p", "Audio Only"],
                                     state="readonly", width=12, font=("Segoe UI", 10))
        self.fmt_menu.pack(side="left", padx=5)
        self.fmt_menu.current(0)
        
        btn_frame = tk.Frame(self, bg="#181a22")
        btn_frame.pack(pady=12)
        self.download_btn = tk.Button(btn_frame, text="Download", command=self.start_download,
                                      font=("Segoe UI", 11, "bold"),
                                      bg="#38d8ff", fg="white", width=13,
                                      bd=0, relief="ridge", activebackground="#17779e", cursor="hand2",
                                      highlightbackground="#15161f", highlightthickness=2)
        self.download_btn.pack(side="left", padx=7)
        self.open_btn = tk.Button(btn_frame, text="Open Folder", command=self.open_folder,
                                  font=("Segoe UI", 10, "bold"), bg="#23233a", fg="#aad8ff",
                                  width=11, bd=0, relief="ridge", activebackground="#23233a", cursor="hand2")
        self.open_btn.pack(side="left", padx=7)

        self.update_btn = tk.Button(btn_frame, text="Update yt-dlp", command=self.update_yt_dlp,
                                    font=("Segoe UI", 10, "bold"), bg="#ff9900", fg="#000000",
                                    width=12, bd=0, relief="ridge", activebackground="#cc7a00", cursor="hand2")
        self.update_btn.pack(side="left", padx=7)
        
        # STATUS BAR
        status_bg = tk.Frame(self, bg="#121219", height=22)
        status_bg.pack(fill="x", ipady=5, pady=(3, 0))
        self.status_lbl = tk.Label(status_bg, textvariable=self.status_var, bg="#121219",
                                  fg="#3cb371", font=("Segoe UI", 10, "bold"),
                                  anchor="center")
        self.status_lbl.pack(fill="x")
    
    def open_folder(self):
        path = DOWNLOAD_FOLDER
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            os.system(f"open '{path}'")
        else:
            os.system(f"xdg-open '{path}'")

    def start_download(self):
        url = self.url_entry.get().strip()
        self.status_lbl.config(fg="#E7C252")
        if not url or ("youtube.com" not in url and "youtu.be" not in url):
            self.set_status("Please enter a valid YouTube link!", color="#F25F73")
            return
        self.download_btn.configure(state="disabled")
        self.set_status("Initializing download...", color="#E7C252")
        threading.Thread(target=self.download_video, args=(url,), daemon=True).start()

    def set_status(self, text, color="#3cb371"):
        self.status_var.set(text)
        self.status_lbl.config(fg=color)
        self.update_idletasks()

    def show_progress(self):
        d = self.status_details
        # Example: 14.7 MB / 28.1 MB   •   2.88 MB/s   •   ETA: 0:13
        prog = f"{d['dl_mib']} MB / {d['total_mib']} MB   •   {d['speed']} MB/s   •   ETA: {d['eta']}"
        self.set_status(prog, color="#42e0fc")

    def ydl_format(self):
        choice = self.selected_format.get().lower()
        if choice == "audio only":
            return "bestaudio"
        if choice == "1080p":
            return "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
        if choice == "720p":
            return "bestvideo[height<=720]+bestaudio/best[height<=720]"
        return "bestvideo+bestaudio/best"

    def clean_temp_files(self, basename):
        patterns = [
            os.path.join(DOWNLOAD_FOLDER, f"{basename}.*.f*"),
            os.path.join(DOWNLOAD_FOLDER, f"{basename}*.webm"),
            os.path.join(DOWNLOAD_FOLDER, f"{basename}*.m4a"),
        ]
        for pattern in patterns:
            for fpath in glob.glob(pattern):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0.0%').replace('%', '').strip()
            try:
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
                downloaded = d.get('downloaded_bytes', 0)
                total_mib = "{0:.1f}".format(total_bytes / 1024 / 1024)
                dl_mib = "{0:.1f}".format(downloaded / 1024 / 1024)
                speed = "{0:.2f}".format((d.get('speed') or 0) / 1024 / 1024) if d.get('speed') else "0.00"
                eta = d.get('eta')
                if eta is not None:
                    min, sec = divmod(int(eta), 60)
                    eta_txt = f"{min}:{sec:02d}"
                else:
                    eta_txt = "--"
                self.status_details = {
                    "percent": percent,
                    "total_mib": total_mib,
                    "dl_mib": dl_mib,
                    "speed": speed,
                    "eta": eta_txt
                }
                self.show_progress()
            except Exception:
                pass
        elif d['status'] == 'finished':
            self.set_status("Processing...", color="#E7C252")
            self.update_idletasks()

    def download_video(self, url):
        try:
            fmt = self.ydl_format()
            with yt_dlp.YoutubeDL({
                'format': fmt,
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
                'noplaylist': True,
                'merge_output_format': 'mp4',
                'quiet': True,
                'progress_hooks': [self.progress_hook],
                'concurrent_fragment_downloads': 1
            }) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'video').replace('/', '_').replace('\\', '_')
                self.set_status(f"Downloading: {title}", color="#E7C252")
                ydl.download([url])
            self.clean_temp_files(title)
            self.set_status("✅ Download complete", color="#32e196")
        except yt_dlp.utils.DownloadError:
            self.set_status("❌ Download failed. Possibly due to YouTube changes.", color="#F25F73")
            self.suggest_update_yt_dlp()
        except Exception as e:
            self.set_status("❌ Error: " + str(e), color="#F25F73")
        finally:
            self.download_btn.configure(state="normal")

    def suggest_update_yt_dlp(self):
        # Prompt user to update yt-dlp with a clickable message
        self.set_status("Try updating yt-dlp to the latest version!", color="#F25F73")

    def update_yt_dlp(self):
        # Open the yt-dlp GitHub releases page for manual latest download or update
        webbrowser.open("https://github.com/yt-dlp/yt-dlp/releases/latest")
        self.set_status("Opened yt-dlp GitHub releases page for update.", color="#E7C252")


if __name__ == "__main__":
    app = YouTubeDownloader()
    app.mainloop()
