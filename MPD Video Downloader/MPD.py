import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import threading

class HotstarDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hotstar Video Downloader")
        self.root.geometry("500x250")

        self.label = tk.Label(root, text="Enter Hotstar MPD Link:")
        self.label.pack(pady=10)

        self.url_entry = tk.Entry(root, width=60)
        self.url_entry.pack(pady=5)

        self.progress_label = tk.Label(root, text="Progress: 0%")
        self.progress_label.pack(pady=10)

        self.download_button = tk.Button(root, text="Download Video", command=self.start_download_thread)
        self.download_button.pack(pady=20)

    def start_download_thread(self):
        threading.Thread(target=self.download_video).start()

    def download_video(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a valid MPD URL")
            return

        downloads_folder = os.path.join(os.path.expanduser('~'), 'Downloads', 'Hotstar Downloads')
        if not os.path.exists(downloads_folder):
            os.makedirs(downloads_folder)

        output_file = os.path.join(downloads_folder, "downloaded_hotstar_video.mp4")

        command = [
            'yt-dlp',
            url,
            '-o', output_file,
            '--newline'
        ]

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

            for line in process.stdout:
                if '%' in line:
                    start_idx = max(0, line.find('%')-5)
                    progress = line[start_idx:line.find('%')+1].strip()
                    self.update_progress(progress)

            process.wait()
            if process.returncode == 0:
                self.update_progress("Completed")
                messagebox.showinfo("Success", f"Video downloaded successfully to: {output_file}")
            else:
                messagebox.showerror("Error", "Failed to download video. Check your link and try again.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def update_progress(self, progress):
        self.progress_label.config(text=f"Progress: {progress}")

if __name__ == '__main__':
    root = tk.Tk()
    app = HotstarDownloaderApp(root)
    root.mainloop()
