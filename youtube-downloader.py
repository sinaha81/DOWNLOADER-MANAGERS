import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import yt_dlp
import requests
import json
import time
import humanize
import re
import os
import shutil
from pathlib import Path
from PIL import Image, ImageTk
from io import BytesIO
from datetime import timedelta
import subprocess
import sys

try:
    import libtorrent as lt
except ImportError:
    lt = None

DARK_THEME = {
    "primary": "#121212",
    "secondary": "#1E1E1E",
    "accent": "#007ACC",
    "text": "#E0E0E0",
    "success": "#4CAF50",
    "warning": "#FFC107",
    "error": "#F44336",
    "font": ("Segoe UI", 11)
}

DEFAULT_SETTINGS = {
    "download_path": str(Path.home() / "Downloads"),
    "max_workers": 3,
    "max_retries": 3,
    "dark_mode": True,
    "segment_size": 8,
    "auto_start": True,
    "enable_speed_limit": False,
    "speed_limit": 1024,  # سرعت محدود به KB/s

    "torrent_listen_port": (6881, 6891)
}

def auto_detect_type(url):
    url_lower = url.lower()
    if url.startswith("magnet:") or url_lower.endswith(".torrent"):
        return "torrent"
    if os.path.exists(url):
        ext = os.path.splitext(url_lower)[1]
        if ext == ".torrent":
            return "torrent"
        else:
            return "local"  # اگر فایل محلی باشد
    if "youtube.com/playlist" in url_lower or "list=" in url_lower:
        return "youtube_playlist"
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    if "twitter.com" in url_lower:
        return "twitter"
    if "instagram.com" in url_lower:
        return "instagram"
    if "tiktok.com" in url_lower:
        return "tiktok"
    if "aparat.com" in url_lower:
        return "aparat"
    if "vimeo.com" in url_lower:
        return "vimeo"
    if "XNXX.com" in url_lower:
        return "XNXX"
    if "PORNHUB.com" in url_lower:
        return "PORNHUB"
    if "XHAMESTER.com" in url_lower:
        return "XHAMESTER"      
    return "generic"

class ProfessionalDownloader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SINA Download Manager")
        self.geometry("1400x691")
        self.settings = self.load_settings()
        self.active_downloads = {}  
        self.download_queue = []     
        self.download_tasks_lock = threading.Lock()
        self.auto_detected_type = None  
        self.current_thumbnail = None
        self.status_labels = {}     
        self.setup_ui()
        self.setup_styles()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_interval = 100  
        self.after(self.update_interval, self.update_ui)

    def setup_ui(self):
        # ساختار اصلی پنجره
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
    
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=10)
        
        
        self.thumbnail_label = ttk.Label(header_frame)
        self.thumbnail_label.pack(side=tk.RIGHT, padx=15)
        
        input_frame = ttk.Frame(header_frame)
        input_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
    
        self.url_entry = ttk.Entry(
            input_frame,
            width=80,
            font=DARK_THEME["font"],
            style="Custom.TEntry"
        )
        self.url_entry.pack(side=tk.LEFT, expand=True, padx=10, pady=5)
        
        ttk.Button(
            input_frame,
            text="تحلیل",
            command=self.analyze_and_start,
            style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        
        self.quality_tree = self.create_treeview(
            main_frame,
            columns=[
                ("resolution", "رزولوشن", 120),
                ("codec", "کدک", 150),
                ("bitrate", "بیتریت", 100),
                ("size", "حجم", 120),
                ("fps", "فریم ریت", 80),
                ("hdr", "HDR", 60)
            ],
            height=7
        )
        self.quality_tree.pack(fill=tk.BOTH, expand=True, pady=10)
        
       
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        control_buttons = [
            ("شروع دانلود", self.start_download, "success"),
            ("مکث همه", self.pause_all, "warning"),
            ("ادامه همه", self.resume_all, "success"),
            ("لغو همه", self.cancel_all, "error"),
            ("📂 مسیر دانلود", self.set_download_path, "secondary"),
            ("⚙ تنظیمات", self.show_settings, "secondary")
        ]
        
        for text, cmd, style in control_buttons:
            ttk.Button(
                control_frame,
                text=text,
                command=cmd,
                style=f"{style.capitalize()}.TButton"
            ).pack(side=tk.RIGHT, padx=5)
        
     
        self.progress_tree = self.create_treeview(
            main_frame,
            columns=[
                ("source", "نوع", 80),
                ("status", "وضعیت", 120),
                ("title", "عنوان", 300),
                ("progress", "پیشرفت", 150),
                ("speed", "سرعت", 120),
                ("size", "حجم", 120),
                ("eta", "زمان باقیمانده", 150),
                ("path", "مسیر", 300)
            ],
            height=6
        )
        self.progress_tree.pack(fill=tk.BOTH, expand=True)
        # افزودن منوی راست کلیک به جدول پیشرفت
        self.progress_tree.bind("<Button-3>", self.show_context_menu)
        self.progress_tree.bind("<Double-1>", self.on_progress_double_click)
        
        # نوار وضعیت
        status_bar = ttk.Frame(main_frame)
        status_bar.pack(fill=tk.X, pady=5)
        
        status_items = [
            ("speed", "سرعت کل: 0 MB/s"),
            ("active", "دانلودهای فعال: 0"),
            ("queue", "صف دانلود: 0"),
            ("disk", "فضای آزاد: 0 GB")
        ]
        for key, text in status_items:
            lbl = ttk.Label(status_bar, text=text, style="Status.TLabel")
            lbl.pack(side=tk.RIGHT, padx=20)
            self.status_labels[key] = lbl

        self.update_disk_space()

        # بخش گزارش (log)
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        ttk.Label(log_frame, text="گزارش:", style="TLabel").pack(anchor="w")
        self.log_text = tk.Text(log_frame, height=8, bg=DARK_THEME["secondary"], fg=DARK_THEME["text"], font=DARK_THEME["font"])
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log("")

    def create_treeview(self, parent, columns, height):
        tree = ttk.Treeview(
            parent,
            columns=[col[0] for col in columns],
            show="headings",
            height=height,
            selectmode="extended",
            style="Custom.Treeview"
        )
        for col_id, col_text, width in columns:
            tree.heading(col_id, text=col_text, anchor=tk.CENTER)
            tree.column(col_id, width=width, anchor=tk.CENTER)
        return tree

    def setup_styles(self):
        style = ttk.Style()
        style.theme_create("ydl_dark", parent="alt", settings={
            ".": {
                "configure": {
                    "background": DARK_THEME["primary"],
                    "foreground": DARK_THEME["text"],
                    "font": DARK_THEME["font"]
                }
            },
            "TFrame": {"configure": {"background": DARK_THEME["primary"]}},
            "TLabel": {"configure": {"foreground": DARK_THEME["text"]}},
            "Custom.TEntry": {
                "configure": {
                    "fieldbackground": DARK_THEME["secondary"],
                    "foreground": DARK_THEME["text"],
                    "padding": 5
                }
            },
            "Custom.Treeview": {
                "configure": {
                    "fieldbackground": DARK_THEME["secondary"],
                    "background": DARK_THEME["secondary"],
                    "rowheight": 30
                },
                "map": {
                    "background": [("selected", DARK_THEME["accent"])],
                    "foreground": [("selected", "white")]
                }
            },
            "Accent.TButton": {
                "configure": {
                    "background": DARK_THEME["accent"],
                    "foreground": "white",
                    "padding": 8,
                    "font": (DARK_THEME["font"][0], DARK_THEME["font"][1], "bold")
                }
            },
            "Status.TLabel": {
                "configure": {
                    "background": DARK_THEME["secondary"],
                    "foreground": DARK_THEME["text"],
                    "padding": 5
                }
            }
        })
        for color in ["Success", "Warning", "Error", "Secondary"]:
            style.configure(
                f"{color}.TButton",
                background=DARK_THEME[color.lower()],
                foreground="white"
            )
        style.theme_use("ydl_dark")
        self.configure(background=DARK_THEME["primary"])

    def load_settings(self):
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except Exception as e:
            return DEFAULT_SETTINGS

    def save_settings(self, new_settings=None):
        if new_settings:
            self.settings.update(new_settings)
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)
        self.log("تنظیمات ذخیره شدند.")

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def analyze_and_start(self):
        """
        پس از وارد کردن لینک، ابتدا نوع آن به‌صورت خودکار تشخیص داده می‌شود.
        سپس در صورت پشتیبانی از استخراج اطلاعات (مثلاً برای سایت‌های ویدیویی و پلی‌لیست یوتیوب)
        اطلاعات رسانه استخراج شده و کیفیت‌ها نمایش داده می‌شود. در صورت پلی‌لیست از کاربر سوال می‌شود.
        """
        url = self.url_entry.get().strip()
        if not url:
            self.show_error("خطا", "لطفا لینک را وارد کنید")
            return

        self.auto_detected_type = auto_detect_type(url)
        self.log(f"لینک وارد شده: {url} | نوع تشخیص داده شده: {self.auto_detected_type}")
        # اگر منبع تورنت یا فایل تورنت باشد، مستقیماً دانلود آغاز می‌شود.
        if self.auto_detected_type in ["torrent", "local"]:
            self.thumbnail_label.config(image="", text="تورنت/فایل تورنت تشخیص داده شد")
            self.quality_tree.delete(*self.quality_tree.get_children())
            self.quality_tree.insert("", "end", values=("ناموجود",)*6)
            self.start_download()
        else:
            threading.Thread(
                target=self.fetch_media_info,
                args=(url,),
                daemon=True
            ).start()

    def fetch_media_info(self, url):
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                # اگر پلی‌لیست باشد، کلید entries وجود دارد
                if info.get('entries'):
                    self.after(0, lambda: self.handle_playlist(info))
                else:
                    self.after(0, lambda: self.update_media_ui(info))
        except Exception as e:
            self.after(0, lambda: self.show_error("خطای تحلیل", str(e)))
            self.log(f"خطای تحلیل: {str(e)}")

    def handle_playlist(self, info):
        total = len(info.get('entries', []))
        answer = messagebox.askyesno("پلی‌لیست شناسایی شد",
                                     f"این لینک یک پلی‌لیست با {total} ویدیو است. آیا همه ویدیوها دانلود شوند؟")
        if answer:
            for entry in info['entries']:
                # در برخی موارد عنوان یا url ممکن است در entry به صورت None باشد
                url = entry.get('url')
                if url:
                    # در نظر گرفتن لینک کامل در صورت نسبی بودن
                    if not url.startswith("http"):
                        base_url = info.get('webpage_url')
                        url = base_url + url if base_url else url
                    # ایجاد یک تسک جدید برای هر ویدیو
                    task = {
                        'id': str(time.time_ns()),
                        'url': url,
                        'quality': "best",  # یا بر اساس انتخاب کاربر
                        'status': 'در صف انتظار',
                        'progress': '0%',
                        'speed': '0 KB/s',
                        'size': "--",
                        'eta': "--",
                        'type': "youtube",
                        'start_time': time.time(),
                        'paused': False,
                        'retries': 0,
                        'title': entry.get('title', 'بدون عنوان'),
                        'path': '--'
                    }
                    with self.download_tasks_lock:
                        self.download_queue.append(task)
                    self.log(f"تسک پلی‌لیست اضافه شد: {task['title']}")
            self.process_queue()
        else:
            # در صورت عدم تایید، تنها اولین ویدیو دانلود می‌شود
            first_entry = info['entries'][0]
            info_single = first_entry
            self.update_media_ui(info_single)

    def update_media_ui(self, info):
        self.show_thumbnail(info.get('thumbnail'))
        self.update_quality_list(info.get('formats', []))
        self.log("اطلاعات رسانه به‌روزرسانی شد.")

    def show_thumbnail(self, url):
        if not url:
            return
        try:
            response = requests.get(url, timeout=10)
            img = Image.open(BytesIO(response.content))
            img.thumbnail((120, 110))
            self.current_thumbnail = ImageTk.PhotoImage(img)
            self.thumbnail_label.config(image=self.current_thumbnail, text="")
        except Exception as e:
            self.log(f"خطای دریافت تصویر: {str(e)}")

    def update_quality_list(self, formats):
        self.quality_tree.delete(*self.quality_tree.get_children())
        # فیلتر کردن فرمت‌هایی که ویدیو دارند
        filtered_formats = [f for f in formats if f.get('vcodec') != 'none']
        # استفاده از مقدار 0 در صورت None بودن height یا tbr
        for fmt in sorted(filtered_formats, key=lambda x: (-(x.get('height') if x.get('height') is not None else 0),
                                                            -(x.get('tbr') if x.get('tbr') is not None else 0))):
            filesize = fmt.get('filesize')
            filesize_str = humanize.naturalsize(filesize) if filesize else "نامشخص"
            self.quality_tree.insert("", "end", values=(
                f"{fmt.get('height', 0)}p",
                fmt.get('vcodec', 'N/A').split('.')[0],
                f"{fmt.get('tbr', 0):.1f}kbps",
                filesize_str,
                fmt.get('fps', 0),
                "✅" if fmt.get('dynamic_range') == 'HDR' else "❌"
            ))
        self.log("لیست کیفیت به‌روزرسانی شد.")

    def start_download(self):
        """
        ایجاد تسک دانلود بر اساس لینک وارد شده و نوع تشخیص داده‌شده.
        در صورت سایت‌های ویدیویی (مانند یوتیوب، توییتر، اینستا و ...) در صورت انتخاب کیفیت از جدول،
        کیفیت انتخاب می‌شود. در غیر این صورت، بهترین کیفیت انتخاب می‌شود.
        """
        url = self.url_entry.get().strip()
        if not url:
            self.show_error("خطا", "لطفا لینک را وارد کنید")
            return

        detected_type = auto_detect_type(url)
        if detected_type not in ["torrent", "local", "youtube_playlist"]:
            selected = self.quality_tree.selection()
            if selected:
                item = self.quality_tree.item(selected[0])
                quality = item['values'][0]
            else:
                quality = "best"
        else:
            quality = "ناموجود"

        task_id = str(time.time_ns())
        task = {
            'id': task_id,
            'url': url,
            'quality': quality,
            'status': 'در صف انتظار',
            'progress': '0%',
            'speed': '0 KB/s',
            'size': "--",
            'eta': "--",
            'type': detected_type if detected_type != "youtube_playlist" else "youtube",
            'start_time': time.time(),
            'paused': False,
            'retries': 0,
            'title': 'در حال آماده‌سازی',
            'path': '--'
        }
        with self.download_tasks_lock:
            self.download_queue.append(task)
        self.log(f"تسک جدید اضافه شد: {task['id']} | نوع: {task['type']}")
        self.process_queue()

    def process_queue(self):
        """
        بررسی و شروع دانلودها طبق تعداد همزمان مجاز.
        هر تسک بر اساس نوع آن (yt-based یا تورنت) پردازش می‌شود.
        """
        with self.download_tasks_lock:
            active_dls = [t for t in self.active_downloads.values() if not t.get('paused', False)]
            while len(active_dls) < self.settings["max_workers"] and self.download_queue:
                task = self.download_queue.pop(0)
                task['status'] = 'در حال آماده‌سازی'
                if task['type'] in ["torrent", "local"]:
                    if lt is None:
                        self.show_error("خطا", "کتابخانه libtorrent نصب نشده است!")
                        self.log("خطای تورنت: libtorrent نصب نشده.")
                        return
                    thread = threading.Thread(
                        target=self.handle_torrent_download,
                        args=(task,),
                        daemon=True
                    )
                else:
                    thread = threading.Thread(
                        target=self.handle_video_download,
                        args=(task,),
                        daemon=True
                    )
                thread.start()
                self.active_downloads[task['id']] = task
                active_dls.append(task)
                self.log(f"دانلود شروع شد: {task['title']}")
        if self.settings.get("auto_start", True):
            self.after(100, self.process_queue)

    def handle_video_download(self, task):
        """
        دانلود ویدیو (یا محتوای سایت‌های پشتیبانی‌شده توسط yt_dlp) با استفاده از yt_dlp.
        در صورت بروز خطا، تلاش مجدد انجام می‌شود.
        """
        try:
            ydl_opts = {
                'format': f'bestvideo[height={task["quality"].replace("p", "")}]+bestaudio/best'
                          if task["quality"] != "best" else "best",
                'outtmpl': os.path.join(self.settings["download_path"], '%(title)s.%(ext)s'),
                'progress_hooks': [lambda d: self.update_download_progress(d, task)],
                'retries': self.settings["max_retries"],
                'nopart': False,
                'continuedl': True,
            }
            # اعمال محدودیت سرعت در صورت فعال بودن تنظیم
            if self.settings.get("enable_speed_limit", False):
                ydl_opts['ratelimit'] = self.settings.get("speed_limit", 1024) * 1024  # تبدیل به بایت بر ثانیه
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(task['url'], download=False)
                task['title'] = info.get('title', 'بدون عنوان')
                task['path'] = ydl.prepare_filename(info)
                task['status'] = 'در حال دانلود'
                self.log(f"شروع دانلود ویدیو: {task['title']}")
                ydl.download([task['url']])
            task['status'] = '✅ تکمیل شد'
            self.show_success("دانلود با موفقیت انجام شد")
            self.log(f"دانلود تکمیل شد: {task['title']}")
        except Exception as e:
            self.handle_download_error(task, e)
            self.log(f"خطای دانلود ویدیو: {str(e)}")
        finally:
            self.finalize_download(task)

    def handle_torrent_download(self, task):
        """
        دانلود تورنت با استفاده از libtorrent.
        لینک وارد شده می‌تواند magnet یا مسیر فایل torrent باشد.
        """
        try:
            ses = lt.session()
            port_min, port_max = self.settings.get("torrent_listen_port", (6881, 6891))
            ses.listen_on(port_min, port_max)
            params = {
                'save_path': self.settings["download_path"],
                'storage_mode': lt.storage_mode_t(2)
            }
            if task['url'].startswith("magnet:"):
                handle = lt.add_magnet_uri(ses, task['url'], params)
            else:
                info = lt.torrent_info(task['url'])
                params['ti'] = info
                handle = ses.add_torrent(params)
            task['status'] = 'در حال دانلود'
            task['title'] = "تورنت: " + os.path.basename(task['url'])
            self.log(f"شروع دانلود تورنت: {handle.name()}")
            while not handle.is_seed():
                s = handle.status()
                task['progress'] = f"{s.progress * 100:.2f}%"
                task['speed'] = f"{humanize.naturalsize(s.download_rate)}/s"
                task['eta'] = str(timedelta(seconds=int(s.eta))) if s.eta > 0 else "--"
                time.sleep(1)
            task['status'] = '✅ تکمیل شد'
            task['path'] = os.path.join(self.settings["download_path"], handle.name())
            self.show_success("دانلود تورنت با موفقیت انجام شد")
            self.log(f"دانلود تورنت تکمیل شد: {handle.name()}")
        except Exception as e:
            self.handle_download_error(task, e)
            self.log(f"خطای دانلود تورنت: {str(e)}")
        finally:
            self.finalize_download(task)

    def update_download_progress(self, d, task):
        if d.get('status') == 'downloading':
            task['progress'] = d.get('_percent_str', '0%')
            task['speed'] = d.get('_speed_str', '0 KB/s')
            task['eta'] = d.get('_eta_str', '--')
        elif d.get('status') == 'finished':
            task['progress'] = '100%'
            task['speed'] = '0 KB/s'
            task['eta'] = '0'

    def handle_download_error(self, task, error):
        task['retries'] = task.get('retries', 0) + 1
        if task['retries'] <= self.settings["max_retries"]:
            task['status'] = f'🔄 تلاش مجدد ({task["retries"]})'
            with self.download_tasks_lock:
                self.download_queue.append(task)
            self.log(f"تلاش مجدد برای تسک {task['id']} | تلاش {task['retries']}")
        else:
            task['status'] = f'❌ خطا: {str(error)[:30]}...'
            self.show_error("خطای دانلود", str(error))
            self.log(f"تسک {task['id']} با خطا مواجه شد: {str(error)}")

    def finalize_download(self, task):
        with self.download_tasks_lock:
            if task['id'] in self.active_downloads:
                del self.active_downloads[task['id']]
        self.process_queue()

    def update_ui(self):
        # به‌روزرسانی جدول پیشرفت
        self.progress_tree.delete(*self.progress_tree.get_children())
        total_speed = 0
        active_count = 0
        with self.download_tasks_lock:
            for task in list(self.active_downloads.values()):
                status_text = task['status']
                if "در حال دانلود" in status_text:
                    status_color = DARK_THEME["success"]
                elif "در صف" in status_text:
                    status_color = DARK_THEME["warning"]
                elif "تکمیل" in status_text:
                    status_color = DARK_THEME["success"]
                elif "خطا" in status_text:
                    status_color = DARK_THEME["error"]
                elif "مکث" in status_text:
                    status_color = DARK_THEME["warning"]
                else:
                    status_color = DARK_THEME["text"]
                self.progress_tree.insert("", "end", iid=task['id'], values=(
                    "YT" if task['type'] not in ["torrent", "local"] else "TOR",
                    task['status'],
                    task.get('title', 'بدون عنوان'),
                    task['progress'],
                    task['speed'],
                    task['size'],
                    task.get('eta', '--'),
                    task.get('path', '--')
                ), tags=(status_color,))
                if "در حال دانلود" in task['status']:
                    active_count += 1
                    total_speed += self.parse_speed(task['speed'])
        self.status_labels['active'].config(text=f"دانلودهای فعال: {active_count}")
        self.status_labels['queue'].config(text=f"صف دانلود: {len(self.download_queue)}")
        self.status_labels['speed'].config(text=f"سرعت کل: {humanize.naturalsize(total_speed)}/s")
        self.update_disk_space()
        self.after(self.update_interval, self.update_ui)

    def parse_speed(self, speed_str):
        units = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}
        match = re.match(r"([\d.]+)\s*([KMG]B)/s", speed_str)
        return float(match.group(1)) * units.get(match.group(2), 0) if match else 0

    def update_disk_space(self):
        try:
            usage = shutil.disk_usage(self.settings["download_path"])
            free_space = usage.free
            self.status_labels['disk'].config(text=f"فضای آزاد: {humanize.naturalsize(free_space)}")
        except Exception as e:
            self.log(f"خطای بررسی فضای دیسک: {str(e)}")

    def show_settings(self):
        """
        پنجره تنظیمات پیشرفته شامل مسیر دانلود، تعداد دانلود همزمان،
        تنظیم تم تاریک/روشن، محدودیت سرعت و پورت‌های تورنت می‌باشد.
        """
        settings_win = tk.Toplevel(self)
        settings_win.title("تنظیمات پیشرفته")
        settings_win.geometry("400x500")
        
        self.settings_widgets = {}
        
        ttk.Label(settings_win, text="مسیر دانلود:", style="TLabel").pack(pady=10)
        path_frame = ttk.Frame(settings_win)
        path_frame.pack()
        self.settings_widgets['download_path'] = ttk.Entry(path_frame, width=40)
        self.settings_widgets['download_path'].insert(0, self.settings["download_path"])
        self.settings_widgets['download_path'].pack(side=tk.LEFT, padx=5)
        ttk.Button(
            path_frame,
            text="انتخاب مسیر",
            command=lambda: self.set_setting_path(settings_win)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(settings_win, text="حداکثر دانلود همزمان:", style="TLabel").pack(pady=10)
        self.settings_widgets['max_workers'] = ttk.Spinbox(settings_win, from_=1, to=10, width=5)
        self.settings_widgets['max_workers'].set(self.settings["max_workers"])
        self.settings_widgets['max_workers'].pack()
        
        
        ttk.Label(settings_win, text="پورت‌های تورنت (شروع-پایان):", style="TLabel").pack(pady=10)
        torrent_frame = ttk.Frame(settings_win)
        torrent_frame.pack()
        self.settings_widgets['torrent_port_min'] = ttk.Entry(torrent_frame, width=6)
        self.settings_widgets['torrent_port_min'].insert(0, str(self.settings.get("torrent_listen_port", (6881, 6891))[0]))
        self.settings_widgets['torrent_port_min'].pack(side=tk.LEFT, padx=5)
        self.settings_widgets['torrent_port_max'] = ttk.Entry(torrent_frame, width=6)
        self.settings_widgets['torrent_port_max'].insert(0, str(self.settings.get("torrent_listen_port", (6881, 6891))[1]))
        self.settings_widgets['torrent_port_max'].pack(side=tk.LEFT, padx=5)
        
        # تنظیمات محدودیت سرعت
        ttk.Label(settings_win, text="فعال کردن محدودیت سرعت:", style="TLabel").pack(pady=10)
        self.settings_widgets['enable_speed_limit'] = tk.BooleanVar(value=self.settings.get("enable_speed_limit", False))
        speed_limit_chk = ttk.Checkbutton(settings_win, text="محدودیت سرعت", variable=self.settings_widgets['enable_speed_limit'])
        speed_limit_chk.pack()
        
        ttk.Label(settings_win, text="سرعت محدود (KB/s):", style="TLabel").pack(pady=10)
        self.settings_widgets['speed_limit'] = ttk.Entry(settings_win, width=10)
        self.settings_widgets['speed_limit'].insert(0, str(self.settings.get("speed_limit", 1024)))
        self.settings_widgets['speed_limit'].pack(pady=5)
        
        ttk.Button(
            settings_win,
            text="ذخیره تنظیمات",
            command=self.save_new_settings,
            style="Success.TButton"
        ).pack(pady=20)

    def set_setting_path(self, parent):
        path = filedialog.askdirectory(parent=parent)
        if path:
            self.settings_widgets['download_path'].delete(0, tk.END)
            self.settings_widgets['download_path'].insert(0, path)

    def save_new_settings(self):
        try:
            torrent_min = int(self.settings_widgets['torrent_port_min'].get())
            torrent_max = int(self.settings_widgets['torrent_port_max'].get())
            speed_limit_val = int(self.settings_widgets['speed_limit'].get())
        except ValueError:
            self.show_error("خطا", "پورت‌های تورنت و سرعت محدود باید عددی باشند")
            return
        new_settings = {
            "download_path": self.settings_widgets['download_path'].get(),
            "max_workers": int(self.settings_widgets['max_workers'].get()),
            "dark_mode": self.settings_widgets['dark_mode'].get(),
            "torrent_listen_port": (torrent_min, torrent_max),
            "enable_speed_limit": self.settings_widgets['enable_speed_limit'].get(),
            "speed_limit": speed_limit_val
        }
        self.save_settings(new_settings)
        messagebox.showinfo("ذخیره شد", "تنظیمات با موفقیت ذخیره شدند")
        if new_settings["dark_mode"]:
            self.configure(background=DARK_THEME["primary"])
        else:
            self.configure(background="white")

    def pause_all(self):
        with self.download_tasks_lock:
            for task in self.active_downloads.values():
                task['paused'] = True
                task['status'] = 'مکث شده'
        self.log("همه دانلودها مکث شدند.")

    def resume_all(self):
        with self.download_tasks_lock:
            for task in self.active_downloads.values():
                task['paused'] = False
                task['status'] = 'در حال دانلود'
        self.log("همه دانلودها از سر گرفته شدند.")
        self.process_queue()

    def cancel_all(self):
        with self.download_tasks_lock:
            self.active_downloads.clear()
            self.download_queue.clear()
        self.log("همه دانلودها لغو شدند.")
        self.update_ui()

    def set_download_path(self):
        path = filedialog.askdirectory()
        if path:
            self.settings["download_path"] = path
            self.save_settings()

    def on_progress_double_click(self, event):
        """
        با دابل کلیک روی ردیف دانلود، در صورت تکمیل شدن، فایل دانلود شده با برنامه پیش‌فرض باز می‌شود.
        """
        selected = self.progress_tree.focus()
        if not selected:
            return
        values = self.progress_tree.item(selected, "values")
        status = values[1]
        file_path = values[7]
        if "تکمیل" in status and os.path.exists(file_path):
            try:
                if sys.platform.startswith('win'):
                    os.startfile(file_path)
                elif sys.platform.startswith('darwin'):
                    subprocess.call(('open', file_path))
                else:
                    subprocess.call(('xdg-open', file_path))
            except Exception as e:
                self.show_error("خطا", f"نمی‌توان فایل را باز کرد: {str(e)}")
        else:
            self.show_error("خطا", "فایل موجود نیست یا دانلود تکمیل نشده است.")

    def show_context_menu(self, event):
        """
        نمایش منوی راست کلیک برای عملیات روی یک تسک دانلود (لغو یا مکث/ادامه)
        """
        item_id = self.progress_tree.identify_row(event.y)
        if item_id:
            self.progress_tree.selection_set(item_id)
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="لغو دانلود", command=lambda: self.cancel_task(item_id))
            menu.add_command(label="مکث/ادامه", command=lambda: self.toggle_pause_task(item_id))
            menu.tk_popup(event.x_root, event.y_root)

    def cancel_task(self, task_id):
        with self.download_tasks_lock:
            if task_id in self.active_downloads:
                task = self.active_downloads[task_id]
                task['status'] = 'لغو شده'
                del self.active_downloads[task_id]
                self.log(f"تسک {task_id} لغو شد.")
            self.download_queue = [t for t in self.download_queue if t['id'] != task_id]
        self.update_ui()

    def toggle_pause_task(self, task_id):
        with self.download_tasks_lock:
            if task_id in self.active_downloads:
                task = self.active_downloads[task_id]
                task['paused'] = not task.get('paused', False)
                if task['paused']:
                    task['status'] = 'مکث شده'
                    self.log(f"تسک {task_id} مکث شد.")
                else:
                    task['status'] = 'در حال دانلود'
                    self.log(f"تسک {task_id} از حالت مکث خارج شد.")
        self.update_ui()

    def show_error(self, title, message):
        messagebox.showerror(title, message)

    def show_success(self, message):
        messagebox.showinfo("موفقیت", message)

    def on_close(self):
        if messagebox.askyesno("خروج", "آیا مطمئن هستید؟"):
            self.save_settings()
            self.destroy()

if __name__ == "__main__":
    app = ProfessionalDownloader()
    app.mainloop()