import asyncio
import os
import threading
import time
from tkinter import Tk, Label, Entry, Button, Frame, messagebox, CENTER, StringVar
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError, PhoneCodeExpiredError
import re

api_id = 20529421
api_hash = '4e9fbc084cf55a92d34b2c2ad61849ad'

def get_session_path():
    app_name = "TelegramDownloaderApp"
    if os.name == 'nt':  # Windows
        base_dir = os.getenv('APPDATA')
    else:
        base_dir = os.path.join(os.path.expanduser("~"), f".{app_name}")
    folder = os.path.join(base_dir, app_name)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "tg_downloader_session")

session_name = get_session_path()


class TelegramDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Restricted Content Downloader")
        self.root.geometry("700x480")
        self.root.configure(bg="#fafdff")

        main_frame = Frame(root, bg="#fafdff")
        main_frame.place(relx=0.5, rely=0.42, anchor=CENTER)

        Label(main_frame, text="Telegram Restricted Content Downloader",
              font=("Segoe UI", 18, "bold"), bg="#fafdff", fg="#161616").grid(row=0, column=0, columnspan=3, pady=(16, 28))

        Label(main_frame, text="Phone Number (+ country code):", font=("Segoe UI", 12), bg="#fafdff").grid(row=1, column=0, sticky='e', pady=8)
        self.phone_input = Entry(main_frame, font=("Segoe UI", 12), width=27, bg="white", relief="groove")
        self.phone_input.grid(row=1, column=1, pady=8, padx=6)
        self.send_code_button = Button(main_frame, text="Send Code", font=("Segoe UI", 11, "bold"), command=self.send_code,
                                       width=14, bg="#e0e7ef", fg="#123", activebackground="#0066cc", activeforeground="#fff", relief="ridge", bd=2)
        self.send_code_button.grid(row=1, column=2, padx=(12, 2), pady=8)

        Label(main_frame, text="Verification Code:", font=("Segoe UI", 12), bg="#fafdff").grid(row=2, column=0, sticky='e', pady=8)
        self.code_input = Entry(main_frame, font=("Segoe UI", 12), width=27, bg="white", relief="groove")
        self.code_input.grid(row=2, column=1, pady=8, padx=6)
        self.code_input.config(state='disabled')
        self.submit_code_button = Button(main_frame, text="Verify Code", font=("Segoe UI", 11, "bold"), command=self.submit_code,
                                         width=14, bg="#e0e7ef", fg="#123", activebackground="#0066cc", activeforeground="#fff", relief="ridge", bd=2)
        self.submit_code_button.grid(row=2, column=2, padx=(12, 2), pady=8)
        self.submit_code_button.config(state='disabled')

        Label(main_frame, text="Telegram Post Link:", font=("Segoe UI", 12), bg="#fafdff").grid(row=3, column=0, sticky='e', pady=(24, 8))
        self.link_input = Entry(main_frame, font=("Segoe UI", 12), width=38, bg="white", relief="groove")
        self.link_input.grid(row=3, column=1, columnspan=2, pady=(24, 8), padx=4)

        self.download_button = Button(main_frame, text="Download Media", font=("Segoe UI", 13, "bold"),
                                      command=self.start_download, width=21, bg="#23d160", fg="white",
                                      activebackground="#17b137", activeforeground="#fff", relief="raised", bd=3)
        self.download_button.grid(row=4, column=0, columnspan=3, pady=(18, 6))
        self.download_button.config(state='disabled')

        self.status_var = StringVar(value="Welcome! Login to start.")
        self.progress_label = Label(root, textvariable=self.status_var, font=("Segoe UI", 13, "bold"),
                                   fg="#212a34", bg="#fafdff", pady=16, anchor='center')
        self.progress_label.place(relx=0.5, rely=0.85, anchor=CENTER)

        self.phone_number = None
        self.phone_code_hash = None

        threading.Thread(target=self.check_logged_in, daemon=True).start()

    def check_logged_in(self):
        def check():
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()
            client = TelegramClient(session_name, api_id, api_hash)
            async def acheck():
                await client.connect()
                if await client.is_user_authorized():
                    self.status_var.set("Session found: Already logged in!")
                    self.download_button.config(state='normal')
                    self.phone_input.config(state='disabled')
                    self.send_code_button.config(state='disabled')
                    self.code_input.config(state='disabled')
                    self.submit_code_button.config(state='disabled')
                await client.disconnect()
            loop.run_until_complete(acheck())
        threading.Thread(target=check, daemon=True).start()

    def send_code(self):
        phone = self.phone_input.get().strip()
        if not phone:
            messagebox.showerror("Error", "Please enter your phone number")
            return
        self.phone_number = phone
        self.status_var.set(f"Sending code to {phone}...")
        self.send_code_button.config(state='disabled')
        self.code_input.config(state='normal')
        self.submit_code_button.config(state='normal')
        threading.Thread(target=self.send_code_async, daemon=True).start()

    def send_code_async(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        client = TelegramClient(session_name, api_id, api_hash)
        async def run():
            try:
                await client.connect()
                sent = await client.send_code_request(self.phone_number)
                self.phone_code_hash = sent.phone_code_hash
                self.status_var.set("Code sent! Enter code and click 'Verify Code'.")
                await client.disconnect()
            except PhoneNumberInvalidError:
                self.status_var.set("Invalid phone number.")
                self.send_code_button.config(state='normal')
                self.code_input.config(state='disabled')
                self.submit_code_button.config(state='disabled')
            except Exception as e:
                self.status_var.set(f"Error: {str(e)}")
                self.send_code_button.config(state='normal')
                self.code_input.config(state='disabled')
                self.submit_code_button.config(state='disabled')
        loop.run_until_complete(run())

    def submit_code(self):
        code = self.code_input.get().strip()
        if not code:
            messagebox.showerror("Error", "Please enter the verification code")
            return
        self.submit_code_button.config(state='disabled')
        self.status_var.set("Verifying code, please wait...")
        threading.Thread(target=self.verify_code_async, args=(code,), daemon=True).start()

    def verify_code_async(self, code):
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        client = TelegramClient(session_name, api_id, api_hash)
        async def run():
            try:
                await client.connect()
                await client.sign_in(phone=self.phone_number, code=code, phone_code_hash=self.phone_code_hash)
                self.status_var.set("Logged in successfully!")
                self.download_button.config(state='normal')
                self.phone_input.config(state='disabled')
                self.send_code_button.config(state='disabled')
                self.code_input.config(state='disabled')
                self.submit_code_button.config(state='disabled')
                await client.disconnect()
            except SessionPasswordNeededError:
                self.status_var.set("2FA enabled! Use terminal or disable 2FA.")
                messagebox.showwarning("2FA Enabled", "Two-factor authentication enabled. Login via terminal or disable 2FA.")
            except PhoneCodeInvalidError:
                self.status_var.set("Invalid code entered. Try again.")
                messagebox.showerror("Error", "Invalid verification code. Try again.")
                self.submit_code_button.config(state='normal')
            except PhoneCodeExpiredError:
                self.status_var.set("Code expired. Please send again.")
                messagebox.showerror("Error", "Code expired. Please click 'Send Code' again.")
                self.send_code_button.config(state='normal')
                self.code_input.config(state='disabled')
                self.submit_code_button.config(state='disabled')
            except Exception as e:
                self.status_var.set(f"Error: {str(e)}")
                self.send_code_button.config(state='normal')
                self.code_input.config(state='disabled')
                self.submit_code_button.config(state='disabled')
        loop.run_until_complete(run())

    def parse_link(self, link):
        pattern = r"(?:https?://)?(?:t\.me|telegram\.me)/([\w_]+)/(\d+)"
        match = re.match(pattern, link)
        if match:
            return match.group(1), int(match.group(2))
        else:
            return None, None

    def start_download(self):
        link = self.link_input.get().strip()
        if not link:
            messagebox.showerror("Error", "Please enter the Telegram post link")
            return

        channel, post_id = self.parse_link(link)
        if not channel or not post_id:
            messagebox.showerror("Error", "Invalid Telegram post link format")
            return

        self.download_button.config(state='disabled')
        self.status_var.set(f"Parsing channel: @{channel}, post ID: {post_id}\nStarting download...")
        threading.Thread(target=self.download_media_async, args=(channel, post_id), daemon=True).start()

    def progress_callback(self, current, total):
        now = time.time()
        if not hasattr(self, "_last_time"):
            self._last_time = now
            self._last_bytes = current
            speed = 0
        else:
            elapsed = now - self._last_time
            if elapsed > 0:
                speed = (current - self._last_bytes) / elapsed
            else:
                speed = 0
            self._last_time = now
            self._last_bytes = current

        percent = int((current / total) * 100) if total else 0
        speed_mb = speed / (1024 * 1024)
        remaining = (total - current) / speed if speed > 0 else 0

        minutes = int(remaining) // 60
        seconds = int(remaining) % 60

        progress_text = (f"Downloading: {percent}% - "
                         f"Speed: {speed_mb:.2f} MB/s, "
                         f"ETA: {minutes}m {seconds}s")
        self.status_var.set(progress_text)

    def download_media_async(self, channel, post_id):
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        client = TelegramClient(session_name, api_id, api_hash)
        async def run():
            try:
                await client.connect()
                download_folder = os.path.join(os.path.expanduser("~"), "Downloads", "Telegram Restricted Content")
                if not os.path.exists(download_folder):
                    os.makedirs(download_folder)

                message = await client.get_messages(channel, ids=post_id)
                if not message:
                    self.status_var.set("Post not found.")
                    self.download_button.config(state='normal')
                    await client.disconnect()
                    return

                if message.media:
                    self.status_var.set("Media found, downloading...")
                    path = await message.download_media(
                        file=download_folder,
                        progress_callback=self.progress_callback
                    )
                    self.status_var.set(f"Downloaded successfully to: {path}")
                else:
                    self.status_var.set("This post does not contain media.")
                await client.disconnect()
            except Exception as e:
                self.status_var.set(f"Error: {str(e)}")
            finally:
                self.download_button.config(state='normal')

        loop.run_until_complete(run())

if __name__ == "__main__":
    root = Tk()
    app = TelegramDownloaderGUI(root)
    root.mainloop()
