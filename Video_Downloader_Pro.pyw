import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import asyncio
import os
import re
import shutil
from pathlib import Path

import yt_dlp
from telethon import TelegramClient


# ============================================================
# UNIVERSAL DOWNLOADER PRO
# YouTube / yt-dlp + Telegram
# ============================================================

APP_NAME = "Universal Downloader Pro"

# Telegram API credentials from the original project.
API_ID = 20529421
API_HASH = "4e9fbc084cf55a92d34b2c2ad61849ad"


# --------------------------- Helpers --------------------------

def get_session_path():
    base_dir = os.getenv("APPDATA") if os.name == "nt" else os.path.expanduser("~")
    folder = os.path.join(base_dir, "UniversalDownloaderApp")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "tg_session")


SESSION_NAME = get_session_path()


def strip_ansi(text):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", str(text))


def find_executable(name):
    """Return an executable path if it exists on PATH."""
    return shutil.which(name)


def human_error(exc):
    text = strip_ansi(str(exc)).strip()
    if not text:
        return "Unknown error"

    # Keep the useful part of yt-dlp errors.
    replacements = {
        "ERROR: ": "",
        "HTTP Error 403: Forbidden": (
            "HTTP 403 Forbidden. YouTube rejected the media request. "
            "Make sure yt-dlp, yt-dlp-ejs and Deno are installed/updated."
        ),
    }

    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)

    return text[:500]


# ------------------------- Download Row -----------------------

class DownloadRow:
    def __init__(self, parent, url, save_path, mode="VIDEO", format_str="best",
                 audio_only=False):
        self.frame = tk.Frame(parent, bg="#1E2227", bd=1, relief="flat")
        self.frame.pack(fill="x", pady=8, padx=10)

        self.url = url
        self.save_path = Path(save_path)
        self.mode = mode
        self.format_str = format_str
        self.audio_only = audio_only
        self.is_cancelled = False

        self.title_label = tk.Label(
            self.frame,
            text=f"[{mode}] {self.save_path.name}",
            font=("Segoe UI", 10, "bold"),
            bg="#1E2227",
            fg="#18e86d",
            anchor="w",
        )
        self.title_label.pack(fill="x", padx=12, pady=(8, 2))

        self.progress = ttk.Progressbar(
            self.frame,
            style="Horizontal.TProgressbar",
            length=500,
            mode="determinate",
        )
        self.progress.pack(fill="x", padx=12, pady=5)

        self.status_label = tk.Label(
            self.frame,
            text="Preparing...",
            font=("Consolas", 10),
            bg="#1E2227",
            fg="#CCCCCC",
            anchor="w",
        )
        self.status_label.pack(side="left", padx=12, pady=(0, 8))

        self.cancel_btn = tk.Button(
            self.frame,
            text="Cancel",
            bg="#ff4444",
            fg="white",
            relief="flat",
            command=self.cancel,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            padx=10,
        )
        self.cancel_btn.pack(side="right", padx=12, pady=(0, 8))

        threading.Thread(target=self.start_engine, daemon=True).start()

    def cancel(self):
        self.is_cancelled = True
        self.status_label.config(text="Cancelled", fg="#ff4444")
        self.cancel_btn.config(
            text="Remove",
            command=self.frame.destroy,
            bg="#444444",
        )

    def update_ui(self, percent, speed="0 MiB/s", eta="00:00", status=None):
        def _upd():
            try:
                self.progress["value"] = max(0, min(100, percent))
                if status:
                    display_text = status
                else:
                    s = strip_ansi(speed).strip()
                    e = strip_ansi(eta).strip()
                    display_text = f"{percent:.1f}%  •  {s}  •  ETA: {e}"
                self.status_label.config(text=display_text)
            except tk.TclError:
                pass

        self.frame.after(0, _upd)

    def start_engine(self):
        if self.mode == "TELEGRAM":
            try:
                asyncio.run(self.run_telegram())
            except Exception as exc:
                self.finish(f"❌ {human_error(exc)}", color="#ff4444")
        else:
            self.run_ytdlp()

    # ----------------------- yt-dlp ----------------------------

    def run_ytdlp(self):
        def hook(d):
            if self.is_cancelled:
                raise Exception("User cancelled")

            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
                downloaded = d.get("downloaded_bytes", 0)
                p = (downloaded / total) * 100

                self.update_ui(
                    p,
                    d.get("_speed_str", "0 MiB/s"),
                    d.get("_eta_str", "00:00"),
                )

            elif d["status"] == "finished":
                if self.audio_only:
                    self.update_ui(100, status="Converting audio to MP3...")
                else:
                    self.update_ui(100, status="Finalizing video...")

        ydl_opts = {
            "outtmpl": str(self.save_path),
            "format": self.format_str,
            "progress_hooks": [hook],

            # Modern YouTube extraction.
            # Deno is the recommended JS runtime for yt-dlp.
            "js_runtimes": {"deno": {}},

            # Allow yt-dlp to obtain its EJS challenge solver if the
            # installed yt-dlp package needs it.
            "remote_components": ["ejs:npm"],

            "merge_output_format": "mp4",
            "quiet": True,
            "noprogress": True,
            "color": "no_color",

            # Better network compatibility.
            "retries": 5,
            "fragment_retries": 5,
            "file_access_retries": 3,
            "socket_timeout": 30,
            "concurrent_fragment_downloads": 4,

            # Avoid inheriting a problematic system config.
            "noplaylist": True,
        }

        if self.audio_only:
            # The output template remains temporary; FFmpegExtractAudio
            # performs the real MP3 conversion.
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

            if self.is_cancelled:
                return

            self.finish("✅ Complete")

        except Exception as exc:
            if not self.is_cancelled:
                self.finish(
                    f"❌ Error: {human_error(exc)}",
                    color="#ff4444",
                )

    # ---------------------- Telegram ---------------------------

    async def run_telegram(self):
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

        try:
            self.update_ui(0, status="Connecting to Telegram...")

            await client.connect()

            if not await client.is_user_authorized():
                self.finish(
                    "❌ Telegram login required. Run once and complete login.",
                    color="#ff4444",
                )
                return

            match = re.match(
                r"(?:https?://)?(?:t\.me|telegram\.me)/([\w_]+)/(\d+)",
                self.url,
            )

            if not match:
                raise ValueError("Invalid Telegram message URL")

            username = match.group(1)
            message_id = int(match.group(2))

            msg = await client.get_messages(username, ids=message_id)

            if not msg or not msg.media:
                raise ValueError("No downloadable media found in this message")

            def progress(current, total):
                if total:
                    percent = (current / total) * 100
                    self.update_ui(
                        percent,
                        status=f"Downloading: {percent:.1f}%",
                    )

            await msg.download_media(
                file=str(self.save_path),
                progress_callback=progress,
            )

            if not self.is_cancelled:
                self.finish("✅ Complete")

        except Exception as exc:
            if not self.is_cancelled:
                self.finish(
                    f"❌ Telegram error: {human_error(exc)}",
                    color="#ff4444",
                )

        finally:
            await client.disconnect()

    def finish(self, text, color="#00ff95"):
        def _finish():
            try:
                self.status_label.config(text=text, fg=color)
                self.progress.configure(value=100)
                self.cancel_btn.config(
                    text="Close",
                    bg="#333333",
                    command=self.frame.destroy,
                )
            except tk.TclError:
                pass

        self.frame.after(0, _finish)


# ---------------------- Main Application ----------------------

class UniversalDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x700")
        self.root.minsize(760, 560)
        self.root.configure(bg="#181B20")

        self.formats_map = {}
        self.current_info = None

        self.build_ui()
        self.check_dependencies()

    # ------------------------- UI ------------------------------

    def build_ui(self):
        header = tk.Frame(self.root, bg="#181B20")
        header.pack(fill="x", padx=20, pady=15)

        tk.Label(
            header,
            text="UNIVERSAL DOWNLOADER",
            font=("Segoe UI", 18, "bold"),
            bg="#181B20",
            fg="#18e86d",
        ).pack(side="left")

        tk.Label(
            header,
            text="PRO",
            font=("Segoe UI", 10, "bold"),
            bg="#181B20",
            fg="#00d7ff",
        ).pack(side="left", padx=8, pady=(7, 0))

        input_frame = tk.Frame(
            self.root,
            bg="#1E2227",
            padx=15,
            pady=15,
        )
        input_frame.pack(fill="x", padx=20)

        self.url_entry = tk.Entry(
            input_frame,
            font=("Segoe UI", 12),
            bg="#FFFFFF",
            fg="#000000",
            relief="flat",
            insertbackground="#000000",
        )
        self.url_entry.pack(fill="x", pady=(5, 10))
        self.url_entry.bind("<Return>", lambda _event: self.fetch_info())

        q_row = tk.Frame(input_frame, bg="#1E2227")
        q_row.pack(fill="x")

        self.quality_var = tk.StringVar(value="Best Quality")

        self.quality_combo = ttk.Combobox(
            q_row,
            textvariable=self.quality_var,
            state="readonly",
            width=35,
        )
        self.quality_combo.pack(side="left", padx=10)

        self.fetch_btn = tk.Button(
            q_row,
            text="Analyze Link",
            bg="#00d7ff",
            fg="#000000",
            font=("Segoe UI", 9, "bold"),
            command=self.fetch_info,
            relief="flat",
            padx=15,
            cursor="hand2",
        )
        self.fetch_btn.pack(side="left")

        self.add_btn = tk.Button(
            input_frame,
            text="ADD TO DOWNLOAD QUEUE",
            bg="#18e86d",
            fg="#111111",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            command=self.handle_add,
            state="disabled",
            pady=8,
            cursor="hand2",
        )
        self.add_btn.pack(fill="x", pady=(15, 0))

        self.info_label = tk.Label(
            input_frame,
            text="Paste a YouTube / supported URL or Telegram media link.",
            font=("Segoe UI", 9),
            bg="#1E2227",
            fg="#999999",
            anchor="w",
        )
        self.info_label.pack(fill="x", pady=(9, 0))

        # Scrollable download queue
        queue_holder = tk.Frame(self.root, bg="#181B20")
        queue_holder.pack(fill="both", expand=True, padx=20, pady=10)

        self.canvas = tk.Canvas(
            queue_holder,
            bg="#181B20",
            highlightthickness=0,
        )
        self.scrollbar = ttk.Scrollbar(
            queue_holder,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scroll_frame = tk.Frame(
            self.canvas,
            bg="#181B20",
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scroll_frame,
            anchor="nw",
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.scroll_frame.bind(
            "<Configure>",
            self._on_frame_configure,
        )
        self.canvas.bind(
            "<Configure>",
            self._on_canvas_configure,
        )

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    # --------------------- Dependencies ------------------------

    def check_dependencies(self):
        missing = []

        if find_executable("ffmpeg") is None:
            missing.append("FFmpeg")

        if find_executable("deno") is None:
            missing.append("Deno")

        if missing:
            self.info_label.config(
                text=(
                    "Missing: " + ", ".join(missing) +
                    "  •  Install them, then restart the app."
                ),
                fg="#ffcc66",
            )
        else:
            self.info_label.config(
                text="Ready • yt-dlp + Deno + FFmpeg detected",
                fg="#18e86d",
            )

    # --------------------- Scrolling ---------------------------

    def _on_frame_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(
            self.canvas_window,
            width=event.width,
        )

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(
            int(-1 * (event.delta / 120)),
            "units",
        )

    # -------------------- Analyze URL --------------------------

    def fetch_info(self):
        url = self.url_entry.get().strip()

        if not url:
            messagebox.showwarning(
                "URL Required",
                "Paste a video or Telegram link first.",
            )
            return

        self.fetch_btn.config(
            text="Analyzing...",
            state="disabled",
            bg="#555555",
        )
        self.add_btn.config(state="disabled")

        threading.Thread(
            target=self._get_formats,
            args=(url,),
            daemon=True,
        ).start()

    def _get_formats(self, url):
        try:
            if re.search(r"(?:t\.me|telegram\.me)/", url, re.I):
                res = ["Telegram Media"]
                formats_map = {"Telegram Media": "best"}
                info_text = "Telegram media detected."

            else:
                # Use the same EJS setup during analysis as during download.
                opts = {
                    "quiet": True,
                    "noplaylist": True,
                    "js_runtimes": {"deno": {}},
                    "remote_components": ["ejs:npm"],
                }

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(
                        url,
                        download=False,
                    )

                formats = info.get("formats", [])

                resolutions = {
                    2160: "4K (Ultra HD)",
                    1440: "2K (QHD)",
                    1080: "1080p (Full HD)",
                    720: "720p (HD)",
                    480: "480p",
                    360: "360p",
                    240: "240p",
                    144: "144p",
                }

                heights = sorted(
                    {
                        int(f.get("height"))
                        for f in formats
                        if f.get("height")
                    },
                    reverse=True,
                )

                res = ["Best Quality"]
                formats_map = {
                    "Best Quality": "bestvideo+bestaudio/best"
                }

                for height in heights:
                    if height in resolutions:
                        label = resolutions[height]
                        formats_map[label] = (
                            f"bestvideo[height<={height}]+"
                            f"bestaudio/best"
                        )
                        res.append(label)

                res.append("Audio Only (MP3)")
                formats_map["Audio Only (MP3)"] = "bestaudio/best"

                title = info.get("title") or "Media"
                info_text = f"Detected: {title}"

            self.formats_map = formats_map

            def update():
                self.quality_combo.configure(values=res)
                self.quality_var.set(res[0])
                self.add_btn.config(state="normal")
                self.fetch_btn.config(
                    text="Analyze Link",
                    state="normal",
                    bg="#00d7ff",
                )
                self.info_label.config(
                    text=info_text,
                    fg="#18e86d",
                )

            self.root.after(0, update)

        except Exception as exc:
            error_text = human_error(exc)

            def show_error():
                messagebox.showerror(
                    "Analysis Failed",
                    error_text,
                )
                self.fetch_btn.config(
                    text="Analyze Link",
                    state="normal",
                    bg="#00d7ff",
                )
                self.info_label.config(
                    text="Analysis failed. Check yt-dlp / Deno / network.",
                    fg="#ff6666",
                )

            self.root.after(0, show_error)

    # -------------------- Add to queue -------------------------

    def handle_add(self):
        url = self.url_entry.get().strip()
        q_label = self.quality_var.get()

        if not url:
            return

        is_telegram = bool(
            re.search(r"(?:t\.me|telegram\.me)/", url, re.I)
        )
        audio_only = q_label == "Audio Only (MP3)"

        fmt = self.formats_map.get(q_label, "best")

        if is_telegram:
            ext = ".mp4"
        elif audio_only:
            ext = ".mp3"
        else:
            ext = ".mp4"

        save_path = filedialog.asksaveasfilename(
            title="Choose output file",
            defaultextension=ext,
            filetypes=(
                [("MP3 Audio", "*.mp3"), ("All Files", "*.*")]
                if audio_only
                else [("MP4 Video", "*.mp4"), ("All Files", "*.*")]
            ),
        )

        if not save_path:
            return

        # For yt-dlp audio conversion, give the temporary download a
        # neutral extension so FFmpegExtractAudio can create the MP3.
        actual_save_path = save_path

        if audio_only:
            actual_save_path = str(Path(save_path).with_suffix(".%(ext)s"))

        DownloadRow(
            self.scroll_frame,
            url,
            actual_save_path,
            "TELEGRAM" if is_telegram else "VIDEO",
            fmt,
            audio_only=audio_only,
        )

        self.url_entry.delete(0, tk.END)
        self.add_btn.config(state="disabled")
        self.info_label.config(
            text="Download added to queue.",
            fg="#18e86d",
        )


# ---------------------------- Main -----------------------------

if __name__ == "__main__":
    root = tk.Tk()

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor="#23272E",
        background="#18E86D",
        bordercolor="#181B20",
        thickness=15,
    )

    app = UniversalDownloader(root)
    root.mainloop()
