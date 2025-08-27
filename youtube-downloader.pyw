# --- نیازمندی‌ها ---
# pip install customtkinter yt-dlp humanize requests Pillow pycryptodome brotli websockets plyer

from __future__ import annotations
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox, font as tkFont
import tkinter
import threading
import yt_dlp
import requests
from PIL import Image, ImageDraw
from io import BytesIO
import os
import json
from pathlib import Path
import humanize
import time
import re
import shutil
import sys
import pprint
import subprocess
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Tuple

try:
    from plyer import notification
except (ImportError, ModuleNotFoundError):
    notification = None

try:
    from pystray import MenuItem as item, Icon
except (ImportError, ModuleNotFoundError):
    Icon = None

# --- ثابت‌ها و دیکشنری زبان‌ها ---

APP_NAME = "SINA Download Manager"
APP_VERSION = "4.9.0" # Version updated for UI/UX improvements
SETTINGS_FILE = "downloader_settings_v12.json"
QUEUE_STATE_FILE = "queue_state_v3.json"

# Unicode symbols for icons
ICON_SETTINGS = "⚙️"
ICON_DOWNLOAD = "📥"
ICON_CANCEL = "🚫"
ICON_RETRY = "🔄"
ICON_CLEAR = "🗑️"
ICON_FOLDER = "📂"
ICON_ANALYZE = "🔎"
ICON_OPEN_FOLDER = "↗️"
ICON_PAUSE = "⏸️"
ICON_PLAY = "▶️"
ICON_PASTE = "📋"

# دیکشنری کامل زبان‌های زیرنویس بر اساس لیست ارائه شده
SUBTITLE_LANGUAGES = {
'ab': 'Abkhazian', 'aa': 'Afar', 'af': 'Afrikaans', 'ak': 'Akan', 'sq': 'Albanian',
'am': 'Amharic', 'ar': 'Arabic', 'hy': 'Armenian', 'as': 'Assamese', 'ay': 'Aymara',
'az': 'Azerbaijani', 'bn': 'Bangla', 'ba': 'Bashkir', 'eu': 'Basque', 'be': 'Belarusian',
'bho': 'Bhojpuri', 'bs': 'Bosnian', 'br': 'Breton', 'bg': 'Bulgarian', 'my': 'Burmese',
'ca': 'Catalan', 'ceb': 'Cebuano', 'zh-Hans': 'Chinese (Simplified)', 'zh-Hant': 'Chinese (Traditional)',
'co': 'Corsican', 'hr': 'Croatian', 'cs': 'Czech', 'da': 'Danish', 'dv': 'Divehi',
'nl': 'Dutch', 'dz': 'Dzongkha', 'en': 'English', 'eo': 'Esperanto', 'et': 'Estonian',
'ee': 'Ewe', 'fo': 'Faroese', 'fj': 'Fijian', 'fil': 'Filipino', 'fi': 'Finnish',
'fr': 'French', 'gaa': 'Ga', 'gl': 'Galician', 'lg': 'Ganda', 'ka': 'Georgian',
'de': 'German', 'el': 'Greek', 'gn': 'Guarani', 'gu': 'Gujarati', 'ht': 'Haitian Creole',
'ha': 'Hausa', 'haw': 'Hawaiian', 'iw': 'Hebrew', 'hi': 'Hindi', 'hmn': 'Hmong',
'hu': 'Hungarian', 'is': 'Icelandic', 'ig': 'Igbo', 'id': 'Indonesian', 'iu': 'Inuktitut',
'ga': 'Irish', 'it': 'Italian', 'ja': 'Japanese', 'jv': 'Javanese', 'kl': 'Kalaallisut',
'kn': 'Kannada', 'kk': 'Kazakh', 'kha': 'Khasi', 'km': 'Khmer', 'rw': 'Kinyarwanda',
'ko': 'Korean', 'kri': 'Krio', 'ku': 'Kurdish', 'ky': 'Kyrgyz', 'lo': 'Lao', 'la': 'Latin',
'lv': 'Latvian', 'ln': 'Lingala', 'lt': 'Lithuanian', 'lua': 'Luba-Lulua', 'luo': 'Luo',
'lb': 'Luxembourgish', 'mk': 'Macedonian', 'mg': 'Malagasy', 'ms': 'Malay', 'ml': 'Malayalam',
'mt': 'Maltese', 'gv': 'Manx', 'mi': 'Māori', 'mr': 'Marathi', 'mn': 'Mongolian',
'mfe': 'Morisyen', 'ne': 'Nepali', 'new': 'Newari', 'nso': 'Northern Sotho', 'no': 'Norwegian',
'ny': 'Nyanja', 'oc': 'Occitan', 'or': 'Odia', 'om': 'Oromo', 'os': 'Ossetic',
'pam': 'Pampanga', 'ps': 'Pashto', 'fa': 'Persian', 'fa-orig': 'Persian (Original)', 'pl': 'Polish',
'pt': 'Portuguese', 'pt-PT': 'Portuguese (Portugal)', 'pa': 'Punjabi', 'qu': 'Quechua', 'ro': 'Romanian',
'rn': 'Rundi', 'ru': 'Russian', 'sm': 'Samoan', 'sg': 'Sango', 'sa': 'Sanskrit',
'gd': 'Scottish Gaelic', 'sr': 'Serbian', 'crs': 'Seselwa Creole French', 'sn': 'Shona', 'sd': 'Sindhi',
'si': 'Sinhala', 'sk': 'Slovak', 'sl': 'Slovenian', 'so': 'Somali', 'st': 'Southern Sotho',
'es': 'Spanish', 'su': 'Sundanese', 'sw': 'Swahili', 'ss': 'Swati', 'sv': 'Swedish',
'tg': 'Tajik', 'ta': 'Tamil', 'tt': 'Tatar', 'te': 'Telugu', 'th': 'Thai', 'bo': 'Tibetan',
'ti': 'Tigrinya', 'to': 'Tongan', 'ts': 'Tsonga', 'tn': 'Tswana', 'tum': 'Tumbuka',
'tr': 'Turkish', 'tk': 'Turkmen', 'uk': 'Ukrainian', 'ur': 'Urdu', 'ug': 'Uyghur',
'uz': 'Uzbek', 've': 'Venda', 'vi': 'Vietnamese', 'war': 'Waray', 'cy': 'Welsh',
'fy': 'Western Frisian', 'wo': 'Wolof', 'xh': 'Xhosa', 'yi': 'Yiddish', 'yo': 'Yoruba', 'zu': 'Zulu'
}

# --- Enums and Data Classes ---

class DownloadStatus(Enum):
    QUEUED = "در صف"
    STARTING = "در حال شروع..."
    DOWNLOADING = "در حال دانلود"
    PROCESSING = "در حال پردازش..."
    PAUSED = "مکث شده"
    COMPLETED = "تکمیل شد"
    ERROR = "خطا"
    CANCELLED = "لغو شده"
    INVALID = "ناموفق"

class ColorPalette(Enum):
    STATUS_DOWNLOADING = "#1976D2"
    STATUS_COMPLETED = "#2E7D32"
    STATUS_ERROR = "#D32F2F"
    STATUS_PAUSED = "#F57C00"
    STATUS_CANCELLED = "#616161"
    STATUS_PROCESSING = "#6A1B9A"
    STATUS_QUEUED = "gray50"
    HOVER_BG_LIGHT = "#f0f0f0"
    HOVER_BG_DARK = "#3a3d3e"
    BUTTON_CANCEL_FG = "#D32F2F"
    BUTTON_CANCEL_HOVER = "#E57373"
    BUTTON_ACTION_FG = "#4CAF50"
    BUTTON_ACTION_HOVER = "#81C784"

@dataclass
class DownloadTask:
    """Represents a download task's data. Decoupled from the UI."""
    task_id: str
    url: str
    ydl_opts: Dict[str, Any]
    download_type: str
    title: str = "در حال دریافت عنوان..."
    original_url: Optional[str] = None
    info_dict: Dict[str, Any] = field(default_factory=dict)
    status: DownloadStatus = DownloadStatus.QUEUED
    progress_str: str = "0%"
    progress_float: float = 0.0
    speed_str: str = "N/A"
    eta_str: str = "N/A"
    total_bytes_str: str = "N/A"
    filepath: Optional[str] = None
    error_message: Optional[str] = None
    is_terminating: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Converts the task to a JSON-serializable dictionary."""
        opts_copy = self.ydl_opts.copy()
        opts_copy.pop('logger', None)
        opts_copy.pop('progress_hooks', None)
        opts_copy.pop('cookiesfrombrowser', None)

        return {
            "task_id": self.task_id, "url": self.url, "original_url": self.original_url or self.url,
            "ydl_opts": opts_copy, "download_type": self.download_type, "title": self.title,
            "info_dict": self.info_dict, "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DownloadTask:
        task = cls(
            task_id=data.get("task_id", f"task_{time.time_ns()}"), url=data["url"], ydl_opts=data["ydl_opts"],
            download_type=data["download_type"], title=data["title"], original_url=data.get("original_url"),
            info_dict=data.get("info_dict", {}),
        )
        saved_status = data.get("status")
        if saved_status == DownloadStatus.PAUSED.value:
            task.status = DownloadStatus.PAUSED
        elif saved_status not in [DownloadStatus.COMPLETED.value, DownloadStatus.CANCELLED.value]:
            task.status = DownloadStatus.QUEUED
        else:
            task.status = DownloadStatus.QUEUED
        return task

# --- Helper Functions ---

def clean_ansi_codes(text: Any) -> str:
    if not isinstance(text, str): return str(text)
    return re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]').sub('', text)

def open_file_location(filepath: Optional[str]):
    if not filepath or not os.path.exists(filepath):
        messagebox.showwarning("خطا", "فایل یا مسیر آن یافت نشد.")
        return
    directory = os.path.dirname(filepath)
    try:
        if sys.platform == "win32":
            subprocess.run(['explorer', '/select,', os.path.normpath(filepath)], check=True)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", filepath], check=True)
        else:
            subprocess.run(["xdg-open", directory], check=True)
    except Exception as e:
        messagebox.showerror("خطا", f"امکان باز کردن پوشه وجود ندارد: {e}")

# --- Manager Classes ---

class SettingsManager:
    """Handles loading, saving, and accessing application settings."""
    DEFAULT_SETTINGS: Dict[str, Any] = {
        "download_path": str(Path.home() / "Downloads" / "SinaDownloader"), "theme": "System",
        "max_concurrent_downloads": 3, "max_retries": 3, "default_download_type": "Video",
        "default_subtitle_langs": "en,fa", "embed_subtitles": True,
        "font_family": "Vazirmatn", "concurrent_fragments": 4, "audio_format": "mp3", "debug_mode": False,
        "proxy_enabled": False, "proxy_type": "http", "proxy_address": "", "proxy_port": "",
        "cookie_source": "browser", "cookies_file_path": "", "cookie_browser": "chrome",
        "ffmpeg_path": "ffmpeg"
    }

    def __init__(self, settings_file: str, logger: Callable):
        self.settings_file = settings_file
        self.log = logger
        self.settings = self._load()
        Path(self.get("download_path")).mkdir(parents=True, exist_ok=True)

    def get(self, key: str, default: Any = None) -> Any: return self.settings.get(key, default)
    def set(self, key: str, value: Any): self.settings[key] = value
    def _load(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                settings_changed = False
                for key, default_value in self.DEFAULT_SETTINGS.items():
                    if key not in loaded_settings:
                        loaded_settings[key] = default_value
                        settings_changed = True
                if settings_changed:
                    self.log("فایل تنظیمات با کلیدهای جدید به‌روزرسانی شد.")
                return loaded_settings
        except (json.JSONDecodeError, IOError) as e:
            self.log(f"خطا در خواندن فایل تنظیمات: {e}. بازگشت به پیش‌فرض.", level="error")
        return self.DEFAULT_SETTINGS.copy()

    def save(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            self.log("تنظیمات با موفقیت ذخیره شد.")
        except IOError as e: self.log(f"خطا در ذخیره تنظیمات: {e}", level="error")

class DownloadManager:
    """Manages the download queue, active threads, and task states."""
    def __init__(self, app_callback: 'AdvancedYoutubeDownloaderApp'):
        self.app = app_callback
        self.settings = self.app.settings_manager
        self.log = self.app.log_message
        self.tasks: Dict[str, DownloadTask] = {}
        self.download_queue: List[str] = []
        self.active_threads: Dict[str, threading.Thread] = {}
        self.state_lock = threading.Lock()
        self.is_shutting_down = False

    def start_processing(self): self._process_queue()
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        with self.state_lock: return self.tasks.get(task_id)

    def add_task(self, task: DownloadTask, from_restore: bool = False):
        self.log(f"افزودن تسک به صف: {task.title}")
        with self.state_lock:
            self.tasks[task.task_id] = task
            if task.status != DownloadStatus.PAUSED:
                if task.task_id not in self.download_queue: self.download_queue.append(task.task_id)
        self.app.after(0, self.app.add_task_to_ui, task)
        if not from_restore: self.save_queue_state()
        self.app.after(10, self.app._update_global_progress)

    def pause_task(self, task_id: str):
        with self.state_lock:
            task = self.tasks.get(task_id)
            if not task or task.status != DownloadStatus.DOWNLOADING: return
            self.log(f"درخواست مکث برای تسک: {task.title}")
            task.is_terminating = True
            task.status = DownloadStatus.PAUSED
        self.app.after(0, self.app.update_task_ui, task_id)
        self.save_queue_state()
    
    def resume_task(self, task_id: str):
        with self.state_lock:
            task = self.tasks.get(task_id)
            if not task or task.status != DownloadStatus.PAUSED: return
            self.log(f"درخواست ادامه برای تسک: {task.title}")
            task.status = DownloadStatus.QUEUED
            task.is_terminating = False
            if task_id not in self.download_queue: self.download_queue.insert(0, task_id)
        self.app.after(0, self.app.update_task_ui, task_id)
        self.save_queue_state()

    def retry_task(self, task_id: str):
        with self.state_lock:
            task = self.tasks.get(task_id)
            if not task or task.status not in [DownloadStatus.ERROR, DownloadStatus.CANCELLED, DownloadStatus.INVALID]: return
            self.log(f"تلاش مجدد برای تسک: {task.title}. برنامه تلاش می‌کند دانلود را در صورت وجود فایل ناقص، ادامه دهد.")
            task.status = DownloadStatus.QUEUED
            task.is_terminating = False
            task.progress_float = 0.0
            task.error_message = None
            if task_id not in self.download_queue: self.download_queue.insert(0, task_id)
        self.app.after(0, self.app.update_task_ui, task_id)
        self.save_queue_state()

    def cancel_task(self, task_id: str):
        with self.state_lock:
            task = self.tasks.get(task_id)
            if not task: return
            task.is_terminating = True
            task.status = DownloadStatus.CANCELLED
            if task_id in self.download_queue: self.download_queue.remove(task_id)
        self.app.after(0, self.app.update_task_ui, task_id)
        self.save_queue_state()

    def remove_task_from_ui(self, task_id: str):
        with self.state_lock:
            self.tasks.pop(task_id, None)
            if task_id in self.download_queue: self.download_queue.remove(task_id)
            self.active_threads.pop(task_id, None)
        self.app.after(0, self.app.remove_task_widget, task_id)
        self.save_queue_state()

    def _process_queue(self):
        if self.is_shutting_down: return
        with self.state_lock:
            can_start_new = len(self.active_threads) < self.settings.get("max_concurrent_downloads")
            if can_start_new and self.download_queue:
                task_id = self.download_queue.pop(0)
                task = self.tasks.get(task_id)
                if task and not task.is_terminating:
                    task.status = DownloadStatus.STARTING
                    self.app.after(0, self.app.update_task_ui, task_id)
                    thread = threading.Thread(target=self._execute_download, args=(task,), daemon=True)
                    self.active_threads[task_id] = thread
                    thread.start()
        self.app.after(1000, self._process_queue)

    def _execute_download(self, task: DownloadTask):
        def progress_hook(d: Dict[str, Any]):
            if task.is_terminating: raise yt_dlp.utils.DownloadError("دانلود توسط کاربر لغو/مکث شد.")
            if d['status'] == 'downloading':
                task.status = DownloadStatus.DOWNLOADING
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                if total_bytes and d.get('downloaded_bytes') is not None:
                    task.progress_float = d['downloaded_bytes'] / total_bytes
                    task.progress_str = f"{task.progress_float:.1%}"
                    task.total_bytes_str = humanize.naturalsize(total_bytes, binary=True)
                task.speed_str, task.eta_str = d.get('_speed_str', 'N/A'), d.get('_eta_str', 'N/A')
            elif d['status'] == 'finished':
                task.status, task.progress_float, task.filepath = DownloadStatus.PROCESSING, 1.0, d.get('filename')
            self.app.after(0, self.app.update_task_ui, task.task_id)

        try:
            task.ydl_opts['progress_hooks'] = [progress_hook]
            outtmpl = task.ydl_opts.get('outtmpl', '')
            if outtmpl:
                try:
                    dummy_info = {'id': 'id', 'title': 'title', 'ext': 'ext', 'playlist_index': '01', 'chapter': 'chapter', **task.info_dict}
                    Path(os.path.dirname(outtmpl % dummy_info)).mkdir(parents=True, exist_ok=True)
                except Exception as e: self.log(f"خطا در ایجاد پوشه مقصد: {e}", level="warning")
            
            with yt_dlp.YoutubeDL(task.ydl_opts) as ydl: ydl.download([task.url])

            if task.status not in [DownloadStatus.COMPLETED, DownloadStatus.ERROR, DownloadStatus.CANCELLED, DownloadStatus.PAUSED]:
                if not task.filepath:
                     with yt_dlp.YoutubeDL(task.ydl_opts) as ydl_info:
                         info = ydl_info.extract_info(task.url, download=False)
                         task.filepath = ydl_info.prepare_filename(info)
                task.status = DownloadStatus.COMPLETED
        except Exception as e:
            if not task.is_terminating:
                task.status = DownloadStatus.ERROR
                task.error_message = clean_ansi_codes(str(e))
        finally:
            self._finalize_task(task.task_id)

    def _finalize_task(self, task_id: str):
        with self.state_lock:
            self.active_threads.pop(task_id, None)
            task = self.tasks.get(task_id)
            if task and task.status not in [DownloadStatus.COMPLETED, DownloadStatus.ERROR, DownloadStatus.CANCELLED, DownloadStatus.PAUSED]:
                task.status = DownloadStatus.INVALID
        
        if task: 
            self.app.after(0, self.app.update_task_ui, task_id)
            if notification and not self.app.state() == "iconic":
                try:
                    if task.status == DownloadStatus.COMPLETED:
                        notification.notify(title=f"{APP_NAME}", message=f"دانلود تکمیل شد: {task.title[:50]}...", app_name=APP_NAME, timeout=10)
                    elif task.status == DownloadStatus.ERROR:
                        notification.notify(title=f"{APP_NAME} - خطا", message=f"دانلود ناموفق بود: {task.title[:50]}...", app_name=APP_NAME, timeout=10)
                except Exception as e:
                    self.log(f"خطا در نمایش اعلان دسکتاپ: {e}", level="warning")

        self.app.after(0, self.app.update_status_bar)
        self.save_queue_state()

    def shutdown(self):
        self.is_shutting_down = True
        self.save_queue_state()
        with self.state_lock:
            for task in self.tasks.values():
                if task.status in [DownloadStatus.DOWNLOADING, DownloadStatus.STARTING]: task.is_terminating = True

    def save_queue_state(self):
        if self.is_shutting_down: return
        try:
            with self.state_lock:
                tasks_to_save = [self.tasks[tid].to_dict() for tid in self.tasks if self.tasks[tid].status not in [DownloadStatus.COMPLETED]]
            if not tasks_to_save:
                if os.path.exists(QUEUE_STATE_FILE): os.remove(QUEUE_STATE_FILE)
                return
            with open(QUEUE_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(tasks_to_save, f, indent=4, ensure_ascii=False)
        except Exception as e: self.log(f"خطا در ذخیره وضعیت صف دانلود: {e}", level="error", exc_info=True)

    def load_queue_state(self):
        try:
            if not os.path.exists(QUEUE_STATE_FILE): return
            with open(QUEUE_STATE_FILE, 'r', encoding='utf-8') as f: tasks_data = json.load(f)
            if not tasks_data: os.remove(QUEUE_STATE_FILE); return
            for task_data in tasks_data: self.add_task(DownloadTask.from_dict(task_data), from_restore=True)
            self.log(f"{len(tasks_data)} وظیفه از جلسه قبل بازیابی شد.")
            os.remove(QUEUE_STATE_FILE)
        except Exception as e:
            self.log(f"خطا در بازیابی صف دانلود: {e}", level="error")
            if os.path.exists(QUEUE_STATE_FILE): os.remove(QUEUE_STATE_FILE)

# --- UI Classes ---

class SettingsWindow(ctk.CTkToplevel):
    """A dedicated window for managing all application settings."""
    def __init__(self, parent: 'AdvancedYoutubeDownloaderApp', settings_manager: SettingsManager, app_font: ctk.CTkFont, available_fonts: List[str], apply_callback: Callable):
        super().__init__(parent)
        self.parent_app = parent
        self.settings_manager = settings_manager
        self.default_font = app_font
        self.available_fonts = available_fonts
        self.apply_callback = apply_callback

        self.title("تنظیمات")
        self.geometry("700x900")
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(1, weight=1)
        self.row_idx = 0

        self._create_widgets()
    
    def _add_row(self, label_text: str, widget: ctk.CTkBaseClass, sticky="ew", pady=8):
        ctk.CTkLabel(self, text=label_text, font=self.default_font, justify="left").grid(row=self.row_idx, column=0, padx=10, pady=pady, sticky="nw")
        widget.grid(row=self.row_idx, column=1, padx=10, pady=pady, sticky=sticky)
        self.row_idx += 1

    def _create_widgets(self):
        # Download Path
        path_frame = ctk.CTkFrame(self, fg_color="transparent")
        path_frame.grid_columnconfigure(0, weight=1)
        self.path_entry = ctk.CTkEntry(path_frame, font=self.default_font)
        self.path_entry.insert(0, self.settings_manager.get("download_path"))
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(path_frame, text=ICON_FOLDER, command=self._browse_download_path, font=self.default_font, width=40).pack(side="left")
        self._add_row("مسیر دانلود:", path_frame)

        # FFmpeg Path
        ffmpeg_frame = ctk.CTkFrame(self, fg_color="transparent")
        ffmpeg_frame.grid_columnconfigure(0, weight=1)
        self.ffmpeg_entry = ctk.CTkEntry(ffmpeg_frame, font=self.default_font)
        self.ffmpeg_entry.insert(0, self.settings_manager.get("ffmpeg_path"))
        self.ffmpeg_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(ffmpeg_frame, text="انتخاب فایل", command=self._browse_ffmpeg_path, font=self.default_font, width=100).pack(side="left")
        self._add_row("مسیر FFmpeg (اختیاری):", ffmpeg_frame)

        self.theme_var = ctk.StringVar(value=self.settings_manager.get("theme"))
        theme_menu = ctk.CTkOptionMenu(self, variable=self.theme_var, values=["System", "Dark", "Light"], font=self.default_font)
        self._add_row("پوسته برنامه:", theme_menu)

        self.font_var = ctk.StringVar(value=self.settings_manager.get("font_family"))
        font_menu = ctk.CTkComboBox(self, variable=self.font_var, values=self.available_fonts, font=self.default_font, state='readonly')
        self._add_row("فونت برنامه:", font_menu)

        self.max_dl_var = ctk.StringVar(value=str(self.settings_manager.get("max_concurrent_downloads")))
        self._add_row("حداکثر دانلود همزمان:", ctk.CTkEntry(self, textvariable=self.max_dl_var, font=self.default_font))

        self.fragments_var = ctk.StringVar(value=str(self.settings_manager.get("concurrent_fragments")))
        self._add_row("رشته‌های دانلود (سرعت):", ctk.CTkEntry(self, textvariable=self.fragments_var, font=self.default_font))
        
        self.audio_format_var = ctk.StringVar(value=self.settings_manager.get("audio_format"))
        audio_menu = ctk.CTkOptionMenu(self, variable=self.audio_format_var, values=["mp3", "m4a", "flac", "opus", "wav", "best"], font=self.default_font)
        self._add_row("فرمت صوت خروجی:", audio_menu)

        self._create_cookie_settings()
        self._create_proxy_settings()
        self._create_subtitle_selector()

        self.close_to_tray_var = ctk.BooleanVar(value=self.settings_manager.get("close_to_tray"))
        close_check = ctk.CTkCheckBox(self, text="انتقال به سینی سیستم (Tray) هنگام بستن پنجره", variable=self.close_to_tray_var, font=self.default_font)
        self._add_row("رفتار بستن برنامه:", close_check, sticky="w")
        
        self.debug_var = ctk.BooleanVar(value=self.settings_manager.get("debug_mode"))
        debug_check = ctk.CTkCheckBox(self, text="فعال‌سازی لاگ‌های دقیق برای اشکال‌زدایی", variable=self.debug_var, font=self.default_font)
        self._add_row("حالت اشکال‌زدایی:", debug_check, sticky="w")
        
        self.update_button = ctk.CTkButton(self, text="به‌روزرسانی کتابخانه‌ها", command=self._run_library_update, font=self.default_font)
        self._add_row("نگهداری:", self.update_button, sticky="w")

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=self.row_idx, column=0, columnspan=2, pady=20, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(button_frame, text="ذخیره و اعمال", command=self._apply_settings, font=self.default_font, height=35).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(button_frame, text="انصراف", command=self.destroy, font=self.default_font, fg_color="gray", height=35).grid(row=0, column=1, padx=5, sticky="ew")

    def _create_cookie_settings(self):
        cookie_frame = ctk.CTkFrame(self)
        self._add_row("احراز هویت (کوکی):\n(برای حل خطای Sign-in)", cookie_frame, sticky="nsew")

        self.cookie_source_var = ctk.StringVar()
        self.cookie_map = {"none": "بدون کوکی", "file": "از فایل", "browser": "از مرورگر"}
        
        segmented_button = ctk.CTkSegmentedButton(cookie_frame, values=list(self.cookie_map.values()), variable=self.cookie_source_var, command=self._toggle_cookie_widgets, font=self.default_font)
        segmented_button.pack(padx=10, pady=10, fill="x")
        self.cookie_source_var.set(self.cookie_map[self.settings_manager.get("cookie_source")])
        
        self.cookie_file_frame = ctk.CTkFrame(cookie_frame, fg_color="transparent")
        self.cookie_file_frame.pack(fill="x", expand=True, padx=5, pady=5)
        self.cookie_file_frame.grid_columnconfigure(0, weight=1)
        
        self.cookies_path_entry = ctk.CTkEntry(self.cookie_file_frame, font=self.default_font, placeholder_text="مسیر فایل cookies.txt")
        self.cookies_path_entry.insert(0, self.settings_manager.get("cookies_file_path", ""))
        self.cookies_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(self.cookie_file_frame, text=ICON_FOLDER, command=self._browse_cookies_file, font=self.default_font, width=40).pack(side="left")

        self.cookie_browser_frame = ctk.CTkFrame(cookie_frame, fg_color="transparent")
        self.cookie_browser_frame.pack(fill="x", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(self.cookie_browser_frame, text="انتخاب مرورگر:", font=self.default_font).pack(side="left", padx=5)
        self.cookie_browser_var = ctk.StringVar(value=self.settings_manager.get("cookie_browser"))
        browsers = ['chrome', 'firefox', 'edge', 'opera', 'brave', 'vivaldi', 'chromium', 'safari']
        self.cookie_browser_menu = ctk.CTkOptionMenu(self.cookie_browser_frame, variable=self.cookie_browser_var, values=browsers, font=self.default_font)
        self.cookie_browser_menu.pack(side="left", fill="x", expand=True, padx=5)
        
        self._toggle_cookie_widgets(self.cookie_source_var.get())

    def _toggle_cookie_widgets(self, selected_value: str):
        if selected_value == "از فایل":
            self.cookie_file_frame.pack(fill="x", expand=True, padx=5, pady=5)
            self.cookie_browser_frame.pack_forget()
        elif selected_value == "از مرورگر":
            self.cookie_file_frame.pack_forget()
            self.cookie_browser_frame.pack(fill="x", expand=True, padx=5, pady=5)
        else:
            self.cookie_file_frame.pack_forget()
            self.cookie_browser_frame.pack_forget()

    def _create_proxy_settings(self):
        proxy_frame = ctk.CTkFrame(self)
        self._add_row("تنظیمات پروکسی:", proxy_frame, sticky="ew")
        
        self.proxy_enabled_var = ctk.BooleanVar(value=self.settings_manager.get("proxy_enabled"))
        self.proxy_enabled_check = ctk.CTkCheckBox(proxy_frame, text="فعال کردن پروکسی", variable=self.proxy_enabled_var, font=self.default_font, command=self._toggle_proxy_widgets)
        self.proxy_enabled_check.pack(padx=10, pady=(10,5), anchor="w")

        self.proxy_details_frame = ctk.CTkFrame(proxy_frame, fg_color="transparent")
        self.proxy_details_frame.pack(fill="x", expand=True, padx=5)
        self.proxy_details_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.proxy_details_frame, text="نوع:", font=self.default_font).grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.proxy_type_var = ctk.StringVar(value=self.settings_manager.get("proxy_type"))
        self.proxy_type_menu = ctk.CTkOptionMenu(self.proxy_details_frame, variable=self.proxy_type_var, values=["http", "https", "socks4", "socks5"], font=self.default_font)
        self.proxy_type_menu.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ctk.CTkLabel(self.proxy_details_frame, text="آدرس:", font=self.default_font).grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.proxy_address_entry = ctk.CTkEntry(self.proxy_details_frame, font=self.default_font, placeholder_text="e.g., 127.0.0.1")
        self.proxy_address_entry.insert(0, self.settings_manager.get("proxy_address"))
        self.proxy_address_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ctk.CTkLabel(self.proxy_details_frame, text="پورت:", font=self.default_font).grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.proxy_port_entry = ctk.CTkEntry(self.proxy_details_frame, font=self.default_font, placeholder_text="e.g., 8080")
        self.proxy_port_entry.insert(0, self.settings_manager.get("proxy_port"))
        self.proxy_port_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        self._toggle_proxy_widgets()

    def _toggle_proxy_widgets(self):
        state = "normal" if self.proxy_enabled_var.get() else "disabled"
        for widget in [self.proxy_type_menu, self.proxy_address_entry, self.proxy_port_entry]:
            widget.configure(state=state)

    def _create_subtitle_selector(self):
        subs_frame = ctk.CTkFrame(self)
        self._add_row("زبان‌های پیش‌فرض زیرنویس:", subs_frame, sticky="nsew")
        
        self.grid_rowconfigure(self.row_idx - 1, weight=1)
        
        self.embed_subs_var = ctk.BooleanVar(value=self.settings_manager.get("embed_subtitles", True))
        ctk.CTkCheckBox(subs_frame, text="ادغام خودکار زیرنویس در ویدیو", variable=self.embed_subs_var, font=self.default_font).pack(padx=10, pady=(10,5), anchor="w")

        scroll_frame = ctk.CTkScrollableFrame(subs_frame, label_text="زبان‌ها را انتخاب کنید")
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.subs_lang_vars = {}
        current_langs = set(self.settings_manager.get("default_subtitle_langs", "").split(','))
        
        sorted_langs = sorted(SUBTITLE_LANGUAGES.items(), key=lambda item: item[1])

        for code, name in sorted_langs:
            var = ctk.BooleanVar(value=code in current_langs)
            cb = ctk.CTkCheckBox(scroll_frame, text=f"{name} ({code})", variable=var, font=self.default_font)
            cb.pack(anchor="w", padx=5)
            self.subs_lang_vars[code] = var

    def _browse_download_path(self):
        path = filedialog.askdirectory(initialdir=self.path_entry.get(), parent=self)
        if path: self.path_entry.delete(0, ctk.END); self.path_entry.insert(0, path)
    
    def _browse_ffmpeg_path(self):
        filepath = filedialog.askopenfilename(
            title="فایل اجرایی ffmpeg را انتخاب کنید",
            filetypes=(("Executable files", "ffmpeg.exe"), ("All files", "*.*")) if sys.platform == "win32" else (("All files", "*"),)
        )
        if filepath:
            self.ffmpeg_entry.delete(0, ctk.END)
            self.ffmpeg_entry.insert(0, filepath)

    def _browse_cookies_file(self):
        path = filedialog.askopenfilename(title="انتخاب فایل کوکی", filetypes=(("Text files", "*.txt"), ("All files", "*.*")), parent=self)
        if path: self.cookies_path_entry.delete(0, ctk.END); self.cookies_path_entry.insert(0, path)

    def _run_library_update(self):
        self.update_button.configure(state="disabled", text="در حال به‌روزرسانی...")
        threading.Thread(target=self._update_thread_target, daemon=True).start()

    def _update_thread_target(self):
        log = self.parent_app.log_message
        log("شروع فرآیند به‌روزرسانی کتابخانه‌ها...")
        command = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp", "customtkinter", "plyer", "pycryptodome", "brotli", "websockets", "pystray"]
        
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', creationflags=creation_flags)
            
            for output in process.stdout:
                if output: log(f"PIP: {output.strip()}", level="debug")
            
            return_code = process.wait()
            if return_code == 0:
                log("کتابخانه‌ها با موفقیت به‌روزرسانی شدند.", level="info")
                self.parent_app.after(0, lambda: messagebox.showinfo("موفقیت", "کتابخانه‌ها با موفقیت به‌روزرسانی شدند.\nبرای اعمال تغییرات، لطفاً برنامه را مجدداً راه‌اندازی کنید.", parent=self))
            else:
                log(f"خطا در به‌روزرسانی کتابخانه‌ها. کد خطا: {return_code}", level="error")
                self.parent_app.after(0, lambda: messagebox.showerror("خطا", f"فرآیند به‌روزرسانی با خطا مواجه شد.\nکد خطا: {return_code}\nجزئیات را در تب گزارش رویدادها ببینید.", parent=self))

        except Exception as e:
            log(f"یک استثنا در حین به‌روزرسانی رخ داد: {e}", level="error", exc_info=True)
            self.parent_app.after(0, lambda: messagebox.showerror("خطای بحرانی", f"امکان اجرای فرآیند به‌روزرسانی وجود نداشت.\nخطا: {e}", parent=self))
        finally:
            self.parent_app.after(0, lambda: self.update_button.configure(state="normal", text="به‌روزرسانی کتابخانه‌ها"))

    def _apply_settings(self):
        try:
            self.settings_manager.set("download_path", self.path_entry.get())
            self.settings_manager.set("ffmpeg_path", self.ffmpeg_entry.get())
            self.settings_manager.set("max_concurrent_downloads", int(self.max_dl_var.get()))
            self.settings_manager.set("concurrent_fragments", int(self.fragments_var.get()))
            
            cookie_source_display = self.cookie_source_var.get()
            cookie_source_key = [k for k, v in self.cookie_map.items() if v == cookie_source_display][0]
            self.settings_manager.set("cookie_source", cookie_source_key)
            self.settings_manager.set("cookies_file_path", self.cookies_path_entry.get())
            self.settings_manager.set("cookie_browser", self.cookie_browser_var.get())

            self.settings_manager.set("proxy_enabled", self.proxy_enabled_var.get())
            if self.proxy_enabled_var.get():
                if not self.proxy_address_entry.get() or not self.proxy_port_entry.get(): raise ValueError("آدرس و پورت پروکسی نمی‌تواند خالی باشد.")
                int(self.proxy_port_entry.get())
            self.settings_manager.set("proxy_type", self.proxy_type_var.get())
            self.settings_manager.set("proxy_address", self.proxy_address_entry.get())
            self.settings_manager.set("proxy_port", self.proxy_port_entry.get())
            
            selected_subs = [code for code, var in self.subs_lang_vars.items() if var.get()]
            self.settings_manager.set("default_subtitle_langs", ",".join(selected_subs))
            
            self.settings_manager.set("theme", self.theme_var.get())
            self.settings_manager.set("font_family", self.font_var.get())
            self.settings_manager.set("audio_format", self.audio_format_var.get())
            self.settings_manager.set("embed_subtitles", self.embed_subs_var.get())
            self.settings_manager.set("debug_mode", self.debug_var.get())
            self.settings_manager.set("close_to_tray", self.close_to_tray_var.get())

            self.settings_manager.save()
            self.apply_callback()
            self.destroy()

        except ValueError as e: messagebox.showerror("خطای ورودی", str(e), parent=self)
        except Exception as e: messagebox.showerror("خطا", f"امکان ذخیره تنظیمات وجود ندارد: {e}", parent=self)

class PlaylistSelectionWindow(ctk.CTkToplevel):
    # ... (This class remains unchanged) ...
    def __init__(self, parent: ctk.CTk, playlist_info: Dict[str, Any], default_font: ctk.CTkFont):
        super().__init__(parent)
        self.playlist_info = playlist_info
        self.default_font = default_font
        self.selected_entries: List[Dict[str, Any]] = []
        self.item_widgets: List[Dict[str, Any]] = []

        self.title(f"انتخاب از پلی‌لیست: {self.playlist_info.get('title', 'ناشناس')[:50]}")
        self.geometry("850x650")
        self.transient(parent); self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self._create_widgets()
        self.after(100, self._populate_items)

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(top_frame, text="انتخاب همه", command=self._select_all, font=self.default_font).pack(side="left", padx=5)
        ctk.CTkButton(top_frame, text="لغو انتخاب همه", command=self._deselect_all, font=self.default_font).pack(side="left", padx=5)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="آیتم‌های پلی‌لیست")
        self.scrollable_frame.grid(row=1, column=0, padx=10, pady=0, sticky="nsew")

        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        bottom_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(bottom_frame, text="کیفیت دانلود:", font=self.default_font).grid(row=0, column=0, padx=(5,2), pady=5)
        self.quality_var = ctk.StringVar(value="Best Video")
        quality_options = ["Best Video", "4320p (8K)", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "Audio Only"]
        ctk.CTkOptionMenu(bottom_frame, variable=self.quality_var, values=quality_options, font=self.default_font).grid(row=0, column=1, padx=(0,10), pady=5, sticky="ew")
        ctk.CTkButton(bottom_frame, text=f"{ICON_DOWNLOAD} افزودن به صف", command=self._on_confirm, height=35, font=self.default_font).grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(bottom_frame, text="انصراف", command=self._on_cancel, fg_color="gray", font=self.default_font).grid(row=1, column=2, padx=5, pady=5)

    def _populate_items(self):
        for entry in self.playlist_info.get('entries', []):
            if not entry: continue
            item_var = ctk.BooleanVar(value=True)
            item_frame = ctk.CTkFrame(self.scrollable_frame, border_width=1); item_frame.pack(fill="x", padx=5, pady=3)
            item_frame.grid_columnconfigure(2, weight=1)
            ctk.CTkCheckBox(item_frame, text="", variable=item_var, width=20).grid(row=0, column=0, rowspan=2, padx=5)
            thumbnail_label = ctk.CTkLabel(item_frame, text="...", width=128, height=72, fg_color=("gray80", "gray20"))
            thumbnail_label.grid(row=0, column=1, rowspan=2, padx=5, pady=5)
            ctk.CTkLabel(item_frame, text=entry.get('title', 'عنوان نامشخص'), anchor="w", font=self.default_font, wraplength=550).grid(row=0, column=2, sticky="ew", padx=5)
            duration_str = time.strftime('%H:%M:%S', time.gmtime(entry.get('duration', 0))) if entry.get('duration') else 'N/A'
            ctk.CTkLabel(item_frame, text=f"مدت زمان: {duration_str}", anchor="w", font=ctk.CTkFont(size=10)).grid(row=1, column=2, sticky="ew", padx=5)
            self.item_widgets.append({'var': item_var, 'entry': entry})
            threading.Thread(target=self._load_item_thumbnail, args=(entry.get('thumbnail'), thumbnail_label), daemon=True).start()

    def _load_item_thumbnail(self, url: Optional[str], label: ctk.CTkLabel):
        try:
            if not url: raise ValueError("No URL")
            response = requests.get(url, stream=True, timeout=20)
            response.raise_for_status()
            with Image.open(BytesIO(response.content)) as pil_image:
                pil_image.thumbnail((128, 72))
                ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(128, 72))
            if label.winfo_exists(): self.after(0, lambda: label.configure(image=ctk_image, text=""))
        except Exception:
            if label.winfo_exists(): self.after(0, lambda: label.configure(image=None, text="بدون تصویر"))

    def _select_all(self): [item['var'].set(True) for item in self.item_widgets]
    def _deselect_all(self): [item['var'].set(False) for item in self.item_widgets]
    def _on_confirm(self):
        self.selected_entries = [item['entry'] for item in self.item_widgets if item['var'].get()]
        if not self.selected_entries: messagebox.showwarning("انتخاب خالی", "حداقل یک آیتم را انتخاب کنید.", parent=self); return
        self.grab_release(); self.destroy()
    def _on_cancel(self): self.selected_entries = []; self.grab_release(); self.destroy()
    def get_selection(self) -> Tuple[List[Dict[str, Any]], str]:
        self.wait_window()
        return self.selected_entries, self.quality_var.get()

class AdvancedYoutubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} نسخه {APP_VERSION}")
        self.geometry("1250x900"); self.minsize(850, 650)

        self.log_message_buffer = []
        self.settings_manager = SettingsManager(SETTINGS_FILE, self.log_message)
        self.download_manager = DownloadManager(self)
        
        ctk.set_appearance_mode(self.settings_manager.get("theme", "System"))
        ctk.set_default_color_theme("blue")
        
        self.available_fonts = self._get_system_fonts()
        self.font_family = self.settings_manager.get("font_family", "Vazirmatn")
        if self.font_family not in self.available_fonts:
            self.font_family = next((f for f in ["Vazirmatn", "Tahoma", "Segoe UI"] if f in self.available_fonts), self.available_fonts[0] if self.available_fonts else "sans-serif")
        
        self._create_font_objects()
        
        self.task_ui_elements: Dict[str, Dict[str, Any]] = {}
        self.current_media_info: Optional[Dict[str, Any]] = None
        self.thumbnail_image: Optional[ctk.CTkImage] = None
        self.selected_subs_vars: Dict[str, ctk.BooleanVar] = {}
        self.chapter_vars: List[Tuple[ctk.BooleanVar, Dict]] = []
        
        self._create_widgets()
        self._layout_widgets()
        self._process_log_buffer()
        self.update_status_bar()
        self.update_disk_space_periodically()
        self._update_global_progress()
        
        self.download_manager.start_processing()
        self.after(1000, self._check_restore_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        self.log_message(f"{APP_NAME} v{APP_VERSION} با موفقیت راه‌اندازی شد.")

    def _get_system_fonts(self) -> List[str]:
        try: return sorted(list(set(tkFont.families())))
        except Exception: return ["Vazirmatn", "Tahoma", "Arial", "Calibri", "Segoe UI", "sans-serif"]

    def _create_font_objects(self):
        sizes = {'default': 12, 'title': 14, 'treeview': 11, 'task_title': 13, 'task_status': 11, 'icon_button': 20}
        self.fonts = {
            'default': ctk.CTkFont(family=self.font_family, size=sizes['default']),
            'title': ctk.CTkFont(family=self.font_family, size=sizes['title'], weight="bold"),
            'treeview_tuple': (self.font_family, sizes['treeview']),
            'treeview_heading_tuple': (self.font_family, sizes['treeview'], "bold"),
            'task_title': ctk.CTkFont(family=self.font_family, size=sizes['task_title'], weight="bold"),
            'task_status': ctk.CTkFont(family=self.font_family, size=sizes['task_status']),
            'icon_only_button': ctk.CTkFont(family=self.font_family, size=sizes['icon_button'])
        }

    def _create_widgets(self):
        self.top_frame = ctk.CTkFrame(self)
        self.analysis_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_tab_view = ctk.CTkTabview(self)
        self.status_bar_frame = ctk.CTkFrame(self)
        self.url_label = ctk.CTkLabel(self.top_frame, text="لینک (URL):", font=self.fonts['default'])
        self.url_entry = ctk.CTkEntry(self.top_frame, placeholder_text="لینک ویدیو، پلی‌لیست یا سایت را وارد کنید", font=self.fonts['default'])
        self.paste_button = ctk.CTkButton(self.top_frame, text=ICON_PASTE, command=self._paste_from_clipboard, font=self.fonts['icon_only_button'], width=40)
        self.analyze_button = ctk.CTkButton(self.top_frame, text=f"{ICON_ANALYZE} تحلیل لینک", command=self._analyze_url, font=self.fonts['default'])
        
        self.quality_frame = ctk.CTkFrame(self.analysis_frame)
        self.quality_label = ctk.CTkLabel(self.quality_frame, text="انتخاب کیفیت:", font=self.fonts['title'])
        self.tree_style = ttk.Style()
        self.tree_style.theme_use("default")
        self._configure_treeview_style()
        self.quality_tree = ttk.Treeview(self.quality_frame, columns=("res", "fps", "vcodec", "acodec", "size", "ext"), show="headings", height=6, style="Treeview")
        tree_headings = {"res": "رزولوشن", "fps": "فریم‌ریت", "vcodec": "کدک ویدیو", "acodec": "کدک صدا", "size": "حجم", "ext": "فرمت"}
        for col, text in tree_headings.items(): self.quality_tree.heading(col, text=text)

        self.chapters_frame_outer = ctk.CTkFrame(self.quality_frame, fg_color="transparent")
        self.chapters_frame = ctk.CTkScrollableFrame(self.chapters_frame_outer, label_text="فصل‌های ویدیو", label_font=self.fonts['title'])
        
        self.info_panel_frame = ctk.CTkFrame(self.analysis_frame)
        self.thumbnail_label = ctk.CTkLabel(self.info_panel_frame, text="", width=256, height=144)
        self.video_title_label = ctk.CTkLabel(self.info_panel_frame, text="عنوان: در دسترس نیست", justify="left", anchor="nw", font=self.fonts['default'])
        self.download_type_label = ctk.CTkLabel(self.info_panel_frame, text="نوع دانلود:", font=self.fonts['default'])
        self.download_type_var = ctk.StringVar(value=self.settings_manager.get("default_download_type", "Video"))
        self.download_type_segmented_button = ctk.CTkSegmentedButton(self.info_panel_frame, values=["ویدیو", "صوت"], variable=self.download_type_var, command=self._on_download_type_change, font=self.fonts['default'])
        self.download_type_segmented_button.set(self.settings_manager.get("default_download_type", "Video").replace("Video", "ویدیو").replace("Audio", "صوت"))
        
        self.merge_audio_var = ctk.BooleanVar(value=True)
        self.merge_audio_checkbox = ctk.CTkCheckBox(self.info_panel_frame, text="ترکیب با بهترین صدا", variable=self.merge_audio_var, font=self.fonts['default'], state="disabled")
        
        self.subtitle_frame = ctk.CTkFrame(self.info_panel_frame)
        self.subtitle_label = ctk.CTkLabel(self.subtitle_frame, text="انتخاب زیرنویس:", font=self.fonts['title'])
        self.subtitle_options_frame = ctk.CTkScrollableFrame(self.subtitle_frame, fg_color="transparent")
        self.embed_subs_var = ctk.BooleanVar(value=self.settings_manager.get("embed_subtitles", True))
        self.embed_subs_checkbox = ctk.CTkCheckBox(self.subtitle_frame, text="ادغام زیرنویس در فایل ویدیو", variable=self.embed_subs_var, font=self.fonts['default'])
        self.download_button = ctk.CTkButton(self.info_panel_frame, text=f"{ICON_DOWNLOAD} افزودن به صف", command=self._start_download, state="disabled", height=40, font=self.fonts['default'])
        
        self.bottom_tab_view.add("صف دانلود"); self.bottom_tab_view.add("گزارش رویدادها")
        self.downloads_scroll_frame = ctk.CTkScrollableFrame(self.bottom_tab_view.tab("صف دانلود"), fg_color="transparent")
        self.empty_queue_label = ctk.CTkLabel(self.downloads_scroll_frame, text="صف دانلود خالی است.", font=ctk.CTkFont(family=self.font_family, size=14, slant="italic"), text_color="gray")
        self.log_textbox = ctk.CTkTextbox(self.bottom_tab_view.tab("گزارش رویدادها"), state="disabled", wrap="word", font=self.fonts['default'])
        
        self.settings_button = ctk.CTkButton(self.status_bar_frame, text=ICON_SETTINGS, command=self._open_settings_window, width=45, height=30, font=self.fonts['icon_only_button'])
        self.global_progress_bar = ctk.CTkProgressBar(self.status_bar_frame, height=12, corner_radius=6)
        self.global_progress_bar.set(0)
        self.status_bar_label = ctk.CTkLabel(self.status_bar_frame, text="وضعیت: آماده", anchor="e", font=self.fonts['default'])
        self.speed_status_label = ctk.CTkLabel(self.status_bar_frame, text="سرعت کل: 0 B/s", anchor="w", font=self.fonts['default'])
        self.disk_space_label = ctk.CTkLabel(self.status_bar_frame, text="فضای دیسک: N/A", anchor="w", font=self.fonts['default'])

    def _layout_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=4) 
        self.grid_rowconfigure(2, weight=5)
        
        self.top_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.top_frame.grid_columnconfigure(1, weight=1)
        self.url_label.grid(row=0, column=0, padx=5, pady=5)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.paste_button.grid(row=0, column=2, padx=(0, 5), pady=5)
        self.analyze_button.grid(row=0, column=3, padx=5, pady=5)
        
        self.analysis_frame.grid(row=1, column=0, padx=10, pady=(5, 0), sticky="nsew") 
        self.analysis_frame.grid_columnconfigure(0, weight=2); self.analysis_frame.grid_columnconfigure(1, weight=1); self.analysis_frame.grid_rowconfigure(0, weight=1)
        
        self.quality_frame.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="nsew")
        self.quality_frame.grid_rowconfigure(1, weight=3); self.quality_frame.grid_rowconfigure(2, weight=1); self.quality_frame.grid_columnconfigure(0, weight=1)
        self.quality_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.quality_tree.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.quality_tree.column("res", width=120, stretch=True); self.quality_tree.column("size", width=100, anchor="center")
        
        self.info_panel_frame.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="nsew")
        self.info_panel_frame.grid_columnconfigure(0, weight=1); self.info_panel_frame.grid_rowconfigure(5, weight=1)
        self.info_panel_frame.bind("<Configure>", lambda e: self.video_title_label.configure(wraplength=max(1, self.info_panel_frame.winfo_width() - 20)))
        self.thumbnail_label.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.video_title_label.grid(row=1, column=0, padx=5, pady=5, sticky="new")
        self.download_type_label.grid(row=2, column=0, padx=5, pady=(10, 0), sticky="w")
        self.download_type_segmented_button.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        self.merge_audio_checkbox.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.subtitle_frame.grid(row=5, column=0, padx=5, pady=5, sticky="nsew")
        self.download_button.grid(row=6, column=0, padx=5, pady=10, sticky="sew")
        
        self.subtitle_frame.grid_columnconfigure(0, weight=1); self.subtitle_frame.grid_rowconfigure(1, weight=1)
        self.subtitle_label.pack(side="top", anchor="w", padx=5, pady=(5,0))
        self.subtitle_options_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        self.embed_subs_checkbox.pack(side="bottom", anchor="w", padx=5, pady=5)
        
        self.bottom_tab_view.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="nsew")
        self.bottom_tab_view.tab("صف دانلود").grid_columnconfigure(0, weight=1); self.bottom_tab_view.tab("صف دانلود").grid_rowconfigure(0, weight=1)
        self.downloads_scroll_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.empty_queue_label.pack(pady=50, padx=20, expand=True, fill="both")
        self.bottom_tab_view.tab("گزارش رویدادها").grid_columnconfigure(0, weight=1); self.bottom_tab_view.tab("گزارش رویدادها").grid_rowconfigure(0, weight=1)
        self.log_textbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.status_bar_frame.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.status_bar_frame.grid_columnconfigure(2, weight=1)
        self.settings_button.grid(row=0, column=0, rowspan=2, padx=5, pady=5, sticky="w")
        self.global_progress_bar.grid(row=0, column=1, columnspan=2, padx=10, pady=(5,0), sticky="ew")
        self.disk_space_label.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.speed_status_label.grid(row=1, column=2, padx=10, pady=5, sticky="w")
        self.status_bar_label.grid(row=1, column=3, padx=5, pady=5, sticky="e")

    def _configure_treeview_style(self):
        bg = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        fg = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        sel = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        self.tree_style.configure("Treeview", font=self.fonts['treeview_tuple'], rowheight=int(self.fonts['default'].cget("size") * 2.5), background=bg, foreground=fg, fieldbackground=bg)
        self.tree_style.map("Treeview", background=[('selected', sel)])
        self.tree_style.configure("Treeview.Heading", font=self.fonts['treeview_heading_tuple'], background=bg, foreground=fg, relief="flat")
        self.tree_style.map("Treeview.Heading", relief=[('active','groove'),('pressed','sunken')])

    def _apply_appearance_mode(self, color: Tuple[str, str] | str) -> str:
        is_dark = ctk.get_appearance_mode().lower() == "dark"
        return color[1] if isinstance(color, (list, tuple)) and len(color) == 2 and is_dark else color[0] if isinstance(color, (list, tuple)) else color

    def log_message(self, message: str, level: str = "info", debug_data: Any = None, exc_info: bool = False):
        log_entry = f"[{time.strftime('%H:%M:%S')}] [{level.upper()}] {message}\n"
        if self.settings_manager.get("debug_mode", False) and debug_data: log_entry += f"--- DEBUG DATA ---\n{pprint.pformat(debug_data, indent=2)}\n--- END ---\n"
        if exc_info: import traceback; log_entry += traceback.format_exc() + "\n"
        print(log_entry.strip())
        if hasattr(self, 'log_textbox') and self.log_textbox.winfo_exists():
            self.after(0, self._write_to_log_textbox, log_entry)
        else:
            self.log_message_buffer.append(log_entry)

    def _process_log_buffer(self):
        if hasattr(self, 'log_textbox'):
            for entry in self.log_message_buffer: self._write_to_log_textbox(entry)
            self.log_message_buffer.clear()

    def _write_to_log_textbox(self, entry: str):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert(ctk.END, entry)
        self.log_textbox.see(ctk.END)
        self.log_textbox.configure(state="disabled")

    def _check_restore_queue(self):
        if os.path.exists(QUEUE_STATE_FILE) and os.path.getsize(QUEUE_STATE_FILE) > 0:
            if messagebox.askyesno("بازیابی صف", "یک صف دانلود از جلسه قبل یافت شد. آیا مایل به بازیابی آن هستید؟"):
                self.download_manager.load_queue_state()
            else: os.remove(QUEUE_STATE_FILE)

    def _paste_from_clipboard(self):
        try:
            clipboard_content = self.clipboard_get()
            self.url_entry.delete(0, ctk.END)
            self.url_entry.insert(0, clipboard_content)
            self.log_message("لینک از کلیپ‌بورد جای‌گذاری شد.")
        except tkinter.TclError:
            self.log_message("کلیپ‌بورد خالی است یا محتوای متنی ندارد.", level="warning")

    def _analyze_url(self):
        url = self.url_entry.get().strip()
        if not url: return
        self._reset_analysis_ui()
        self.analyze_button.configure(text="در حال تحلیل...", state="disabled")
        threading.Thread(target=self._fetch_media_info_thread, args=(url,), daemon=True).start()

    def _fetch_media_info_thread(self, url: str):
        try:
            ydl_opts = {'extract_flat': 'discard_in_playlist', 'listsubtitles': True, 'logger': self.YTDLLogger(self)}
            self._apply_network_settings(ydl_opts)

            if self.settings_manager.get("debug_mode"): ydl_opts.update({'quiet': False, 'verbose': True})
            else: ydl_opts.update({'quiet': True})
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: info = ydl.extract_info(url, download=False)
            except yt_dlp.utils.DownloadError as e:
                if "Failed to decrypt with DPAPI" in str(e) and 'cookiesfrombrowser' in ydl_opts:
                    self.log_message("خطا در خواندن کوکی‌های مرورگر. تلاش مجدد بدون کوکی...", level="warning")
                    self.after(0, lambda: messagebox.showwarning("خطای کوکی", "خواندن کوکی‌های مرورگر ناموفق بود.\nبرنامه بدون کوکی به کار خود ادامه می‌دهد.\nبرای حل مشکل، از روش 'کوکی از فایل' در تنظیمات استفاده کنید.", parent=self))
                    ydl_opts.pop('cookiesfrombrowser')
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl: info = ydl.extract_info(url, download=False)
                else:
                    raise
            
            if not info: raise yt_dlp.utils.DownloadError("اطلاعاتی از لینک دریافت نشد.")
            
            self.log_message("اطلاعات لینک با موفقیت دریافت شد.", debug_data=info if self.settings_manager.get("debug_mode") else None)
            
            if info.get('_type') == 'playlist':
                self.after(0, lambda: self._handle_playlist_info(info))
            else:
                self.after(0, lambda: self._update_ui_with_media_info(info))
                
        except Exception as e:
            error_msg = clean_ansi_codes(str(e))
            self.after(0, lambda: messagebox.showerror("خطای تحلیل", f"عدم موفقیت در دریافت اطلاعات:\n{error_msg}"))
            self.after(0, self._reset_analysis_ui)
            self.log_message(f"خطا در تحلیل لینک {url}: {error_msg}", level="error", exc_info=self.settings_manager.get("debug_mode"))

    def _apply_network_settings(self, opts: Dict[str, Any]):
        if self.settings_manager.get("proxy_enabled"):
            proxy_type = self.settings_manager.get("proxy_type")
            proxy_addr = self.settings_manager.get("proxy_address")
            proxy_port = self.settings_manager.get("proxy_port")
            if proxy_addr and proxy_port:
                proxy_url = f"{proxy_type}://{proxy_addr}:{proxy_port}"
                opts['proxy'] = proxy_url
                self.log_message(f"استفاده از پروکسی: {proxy_url}")

        cookie_source = self.settings_manager.get("cookie_source")
        if cookie_source == 'file':
            cookies_path = self.settings_manager.get("cookies_file_path")
            if cookies_path and os.path.exists(cookies_path):
                opts['cookiefile'] = cookies_path
                self.log_message(f"استفاده از فایل کوکی: {cookies_path}")
            else:
                self.log_message("منبع کوکی 'فایل' است اما مسیر نامعتبر یا خالی است.", level="warning")
        elif cookie_source == 'browser':
            browser = self.settings_manager.get("cookie_browser")
            opts['cookiesfrombrowser'] = (browser, )
            self.log_message(f"تلاش برای استفاده از کوکی‌های مرورگر: {browser}")

    def _reset_analysis_ui(self):
        # ... (This method remains unchanged) ...
        self.analyze_button.configure(text=f"{ICON_ANALYZE} تحلیل لینک", state="normal")
        self.video_title_label.configure(text="عنوان: در دسترس نیست")
        self.thumbnail_label.configure(image=None, text=""); self.thumbnail_image = None
        for item in self.quality_tree.get_children(): self.quality_tree.delete(item)
        for widget in self.subtitle_options_frame.winfo_children(): widget.destroy()
        self.selected_subs_vars.clear()
        self._populate_chapters(None)
        self.download_button.configure(state="disabled")
        self.current_media_info = None
        self.merge_audio_checkbox.configure(state="disabled")

    def _update_ui_with_media_info(self, info: Dict[str, Any]):
        # ... (This method remains unchanged) ...
        self.current_media_info = info
        self.video_title_label.configure(text=f"عنوان: {info.get('title', 'N/A')}")
        self.log_message(f"ویدیوی تحلیل شد: {info.get('title', 'N/A')}")
        if info.get('thumbnail'): threading.Thread(target=self._load_thumbnail, args=(info['thumbnail'],), daemon=True).start()
        self._populate_quality_treeview(info)
        self._populate_subtitle_options(info)
        self._populate_chapters(info)
        self.download_button.configure(state="normal"); self.analyze_button.configure(text=f"{ICON_ANALYZE} تحلیل لینک", state="normal")
        self._on_download_type_change()

    def _handle_playlist_info(self, playlist_info: Dict[str, Any]):
        # ... (This method remains unchanged) ...
        num_entries = len(playlist_info.get('entries', []))
        self.log_message(f"پلی‌لیست '{playlist_info.get('title', 'ناشناس')}' با {num_entries} آیتم تحلیل شد.")
        self._reset_analysis_ui()
        self.video_title_label.configure(text=f"پلی‌لیست: {playlist_info.get('title', 'ناشناس')} ({num_entries} آیتم)")
        self.analyze_button.configure(text=f"{ICON_ANALYZE} تحلیل لینک", state="normal")
        dialog = PlaylistSelectionWindow(self, playlist_info, self.fonts['default'])
        selected_entries, quality_profile = dialog.get_selection()
        if selected_entries:
            self.log_message(f"شروع افزودن {len(selected_entries)} آیتم از پلی‌لیست با پروفایل کیفیت '{quality_profile}'.")
            self._download_playlist_items(selected_entries, quality_profile, playlist_info)
        else:
            self.log_message("هیچ آیتمی از پلی‌لیست انتخاب نشد.")

    def _populate_quality_treeview(self, info: Dict[str, Any]):
        # ... (This method remains unchanged) ...
        for item in self.quality_tree.get_children(): self.quality_tree.delete(item)
        if not info or 'formats' not in info: return
        download_type = self.download_type_var.get()
        processed_formats = []
        for f in info.get('formats', []):
            is_video = f.get('vcodec') != 'none'
            is_audio = f.get('acodec') != 'none'
            if (download_type == "ویدیو" and not is_video): continue
            if (download_type == "صوت" and not is_audio): continue
            size = humanize.naturalsize(f.get('filesize') or f.get('filesize_approx'), binary=True) if f.get('filesize') or f.get('filesize_approx') else "N/A"
            res = f"{f.get('width')}x{f.get('height')}" if is_video else "فقط صدا"
            vcodec = f.get('vcodec', '-').split('.')[0]
            acodec = f.get('acodec', '-').split('.')[0]
            values = (res, f.get('fps', '-'), vcodec, acodec, size, f.get('ext'))
            processed_formats.append((values, f))
        sort_key = (lambda x: (x[1].get('height', 0), x[1].get('vbr', 0) or x[1].get('tbr', 0) or 0)) if download_type == "ویدیو" else (lambda x: (x[1].get('abr', 0) or x[1].get('tbr', 0) or 0))
        processed_formats.sort(key=sort_key, reverse=True)
        for values, f in processed_formats: 
            self.quality_tree.insert("", "end", values=values, tags=(f['format_id'],))
        if self.quality_tree.get_children(): 
            self.quality_tree.selection_set(self.quality_tree.get_children()[0])

    def _populate_subtitle_options(self, info: Dict[str, Any]):
        # ... (This method remains unchanged) ...
        for widget in self.subtitle_options_frame.winfo_children(): widget.destroy()
        self.selected_subs_vars.clear()
        subs = info.get('subtitles', {}) or info.get('automatic_captions', {})
        if not subs:
            ctk.CTkLabel(self.subtitle_options_frame, text="زیرنویس یافت نشد.", font=self.fonts['default']).pack(anchor="w")
            return
        default_langs = {lang.strip().lower() for lang in self.settings_manager.get("default_subtitle_langs", "").split(',')}
        for lang, sub_info_list in sorted(subs.items()):
            if not sub_info_list: continue
            var = ctk.BooleanVar(value=lang.lower() in default_langs)
            full_name = SUBTITLE_LANGUAGES.get(lang, lang)
            is_auto = '(خودکار)' if 'auto' in sub_info_list[0].get('url', '') or sub_info_list[0].get('ext') in ('srv1', 'srv2', 'srv3') else ''
            cb = ctk.CTkCheckBox(self.subtitle_options_frame, text=f"{full_name} ({lang}) {is_auto}", variable=var, font=self.fonts['default'])
            cb.pack(anchor="w", padx=5, pady=2)
            self.selected_subs_vars[lang] = var

    def _populate_chapters(self, info: Optional[Dict[str, Any]]):
        # ... (This method remains unchanged) ...
        for widget in self.chapters_frame.winfo_children(): widget.destroy()
        self.chapter_vars.clear()
        chapters = info.get('chapters') if info else None
        if not chapters:
            self.chapters_frame_outer.grid_forget()
            return
        for i, chapter in enumerate(chapters):
            var = ctk.BooleanVar(value=False)
            start = time.strftime('%H:%M:%S', time.gmtime(chapter.get('start_time', 0)))
            end = time.strftime('%H:%M:%S', time.gmtime(chapter.get('end_time', 0)))
            title = chapter.get('title', f'فصل {i+1}')
            cb_text = f"{i+1}. {title} ({start} - {end})"
            cb = ctk.CTkCheckBox(self.chapters_frame, text=cb_text, variable=var, font=self.fonts['default'])
            cb.pack(anchor="w", padx=5, pady=2)
            self.chapter_vars.append((var, chapter))
        self.chapters_frame_outer.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")

    def _on_download_type_change(self, *args):
        # ... (This method remains unchanged) ...
        if self.current_media_info and 'entries' not in self.current_media_info:
            download_type = self.download_type_var.get()
            merge_state = "normal" if download_type == "ویدیو" else "disabled"
            self.merge_audio_checkbox.configure(state=merge_state)
            self._populate_quality_treeview(self.current_media_info)

    def _load_thumbnail(self, url: str):
        # ... (This method remains unchanged) ...
        try:
            response = requests.get(url, stream=True, timeout=20)
            response.raise_for_status()
            with Image.open(BytesIO(response.content)) as pil_image:
                pil_image.thumbnail((256, 144))
                self.thumbnail_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(256, 144))
            if self.thumbnail_label.winfo_exists():
                self.after(0, lambda: self.thumbnail_label.configure(image=self.thumbnail_image, text=""))
        except Exception as e:
            if self.thumbnail_label.winfo_exists():
                self.after(0, lambda: self.thumbnail_label.configure(image=None, text="خطای تصویر"))
            self.log_message(f"خطا در بارگذاری تصویر {url}: {e}", level="warning")

    def _start_download(self):
        # ... (This method remains unchanged) ...
        if not self.current_media_info or 'entries' in self.current_media_info: return
        selected_item = self.quality_tree.focus()
        if not selected_item:
            messagebox.showerror("خطا", "لطفاً یک کیفیت از جدول انتخاب کنید.", parent=self)
            return
        format_id = self.quality_tree.item(selected_item, "tags")[0]
        download_type = "Video" if self.download_type_var.get() == "ویدیو" else "Audio"
        subs = [lang for lang, var in self.selected_subs_vars.items() if var.get()]
        merge_audio = self.merge_audio_var.get() if download_type == "Video" else False
        selected_chapters = [chapter_info for var, chapter_info in self.chapter_vars if var.get()]
        if selected_chapters:
            self.log_message(f"شروع افزودن {len(selected_chapters)} فصل به صف دانلود.")
            for chapter in selected_chapters:
                task = self._create_task(self.current_media_info, format_id, download_type, subs, merge_audio=merge_audio, chapter=chapter)
                self.download_manager.add_task(task)
        else:
            task = self._create_task(self.current_media_info, format_id, download_type, subs, merge_audio=merge_audio)
            self.download_manager.add_task(task)

    def _download_playlist_items(self, entries: List[Dict[str, Any]], quality_profile: str, playlist_info: Dict[str, Any]):
        # ... (This method remains unchanged) ...
        format_map = {
            "Best Video": "bestvideo*+bestaudio/best", "4320p (8K)": "bestvideo[height<=4320]+bestaudio/best[height<=4320]",
            "2160p (4K)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]", "1440p (2K)": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]", "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]", "Audio Only": "bestaudio/best"
        }
        format_selector = format_map.get(quality_profile, "bestvideo*+bestaudio/best")
        download_type = "Audio" if quality_profile == "Audio Only" else "Video"
        merge_audio = True if download_type == "Video" else False
        default_subs = [lang.strip() for lang in self.settings_manager.get("default_subtitle_langs", "").split(',') if lang.strip()]
        for entry in entries:
            task = self._create_task(entry, format_selector, download_type, default_subs, merge_audio=merge_audio, is_playlist_item=True, playlist_title=playlist_info.get('title'))
            self.download_manager.add_task(task)

    def _create_task(self, info: Dict[str, Any], format_id: str, download_type: str, subs: List[str], merge_audio: bool, 
                     is_playlist_item: bool = False, playlist_title: Optional[str] = None, chapter: Optional[Dict] = None) -> DownloadTask:
        # ... (This method remains unchanged) ...
        url = info.get('webpage_url') or info.get('url')
        title = info.get('title', f"آیتم {info.get('id', 'ناشناس')}")
        if chapter:
            title = f"{title} - [فصل] {chapter.get('title', 'ناشناس')}"
        task_id = f"task_{time.time_ns()}"
        ydl_opts = self._get_ydl_opts(format_id, download_type, subs, merge_audio, is_playlist_item, playlist_title, chapter)
        return DownloadTask(task_id, url, ydl_opts, download_type, title, self.url_entry.get(), info)

    def _get_ydl_opts(self, format_selector: str, download_type: str, subs_langs: List[str], merge_audio: bool, 
                      is_playlist_item: bool, playlist_title: Optional[str], chapter: Optional[Dict]) -> Dict[str, Any]:
        # ... (This method remains unchanged) ...
        def sanitize(name): return re.sub(r'[<>:"/\\|?*]', '_', name or "").strip()
        base_path = self.settings_manager.get("download_path")
        if chapter:
            title_template = '%(title)s - %(chapter)s [%(id)s].%(ext)s'
        else:
            title_template = '%(title)s [%(id)s].%(ext)s'
        path_template = os.path.join(base_path, sanitize(playlist_title), f"%(playlist_index)s - {title_template}") if is_playlist_item and playlist_title else os.path.join(base_path, title_template)
        opts = {
            'outtmpl': path_template, 'retries': self.settings_manager.get("max_retries"), 'continuedl': True, 
            'overwrites': False, 'nopart': True, 'ignoreerrors': is_playlist_item, 'logger': self.YTDLLogger(self), 
            'noprogress': True, 'writethumbnail': True, 'postprocessors': [{'key': 'FFmpegMetadata', 'add_metadata': True}],
        }
        ffmpeg_path = self.settings_manager.get("ffmpeg_path", "ffmpeg")
        if ffmpeg_path and ffmpeg_path != "ffmpeg":
            opts['ffmpeg_location'] = ffmpeg_path
        if chapter:
            opts['download_sections'] = f"*{re.escape(chapter['title'])}"
        self._apply_network_settings(opts)
        if self.settings_manager.get("concurrent_fragments", 1) > 1: opts['concurrent_fragments'] = self.settings_manager.get("concurrent_fragments")
        if download_type == "Audio":
            opts['format'] = format_selector if "audio" in format_selector else "bestaudio/best"
            opts['postprocessors'].extend([{'key': 'FFmpegExtractAudio', 'preferredcodec': self.settings_manager.get("audio_format", "mp3"), 'preferredquality': '192'}, {'key': 'EmbedThumbnail', 'already_have_thumbnail': False},])
        else:
            if merge_audio:
                opts['format'] = f"{format_selector}+bestaudio/best[ext=m4a] / {format_selector}+bestaudio/best"
            else:
                opts['format'] = format_selector.split('+')[0]
            if subs_langs:
                opts.update({'writesubtitles': True, 'subtitleslangs': subs_langs, 'subtitlesformat': 'srt/vtt'})
                if self.settings_manager.get("embed_subtitles"): opts['embedsubtitles'] = True
            opts.setdefault('merge_output_format', 'mkv' if opts.get('embedsubtitles') else 'mp4')
        return opts

    def add_task_to_ui(self, task: DownloadTask):
        # ... (This method remains unchanged) ...
        if self.empty_queue_label.winfo_ismapped(): self.empty_queue_label.pack_forget()
        frame = ctk.CTkFrame(self.downloads_scroll_frame, border_width=2, corner_radius=10)
        frame.pack(fill="x", pady=5, padx=5); frame.grid_columnconfigure(1, weight=1)
        base_fg_color = frame.cget("fg_color")
        frame.bind("<Enter>", lambda e, f=frame: f.configure(fg_color=self._apply_appearance_mode((ColorPalette.HOVER_BG_LIGHT.value, ColorPalette.HOVER_BG_DARK.value))))
        frame.bind("<Leave>", lambda e, f=frame: f.configure(fg_color=base_fg_color))
        thumbnail_label = ctk.CTkLabel(frame, text="", width=128, height=72, fg_color=("gray80", "gray20"), corner_radius=8)
        thumbnail_label.grid(row=0, column=0, rowspan=3, padx=8, pady=8, sticky="ns")
        if task.info_dict.get('thumbnail'): self._load_task_thumbnail(task, thumbnail_label)
        title_label = ctk.CTkLabel(frame, text=task.title, anchor="w", font=self.fonts['task_title'])
        title_label.grid(row=0, column=1, sticky="new", padx=5, pady=(8,0))
        def update_wraplength(event, label=title_label, parent_frame=frame):
            other_elements_width = 128 + (40 * 3) + 50 
            new_width = max(1, parent_frame.winfo_width() - other_elements_width)
            label.configure(wraplength=new_width)
        frame.bind('<Configure>', update_wraplength)
        progress_bar = ctk.CTkProgressBar(frame, height=12, corner_radius=6); progress_bar.grid(row=1, column=1, sticky="ew", padx=5, pady=4); progress_bar.set(0)
        bottom_frame = ctk.CTkFrame(frame, fg_color="transparent"); bottom_frame.grid(row=2, column=1, sticky="ew", padx=5, pady=(0,8)); bottom_frame.grid_columnconfigure(0, weight=1)
        status_label = ctk.CTkLabel(bottom_frame, text=f"وضعیت: {task.status.value}", anchor="w", font=self.fonts['task_status'])
        status_label.grid(row=0, column=0, sticky="ew")
        action_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent"); action_frame.grid(row=0, column=1, sticky="e")
        btn_width, btn_font = 40, self.fonts['icon_only_button']
        open_folder_button = ctk.CTkButton(action_frame, text=ICON_OPEN_FOLDER, width=btn_width, font=btn_font, command=lambda t=task: open_file_location(t.filepath))
        action_button = ctk.CTkButton(action_frame, text="", width=btn_width, font=btn_font)
        cancel_button = ctk.CTkButton(action_frame, text=ICON_CANCEL, width=btn_width, font=btn_font, fg_color=ColorPalette.BUTTON_CANCEL_FG.value, hover_color=ColorPalette.BUTTON_CANCEL_HOVER.value, command=lambda tid=task.task_id: self.download_manager.cancel_task(tid))
        open_folder_button.pack(side="right", padx=2); action_button.pack(side="right", padx=2); cancel_button.pack(side="right", padx=2)
        self.task_ui_elements[task.task_id] = {"frame": frame, "progress_bar": progress_bar, "status_label": status_label, "action_button": action_button, "cancel_button": cancel_button, "open_folder_button": open_folder_button}
        self.update_task_ui(task.task_id)

    def update_task_ui(self, task_id: str):
        # ... (This method remains unchanged) ...
        task = self.download_manager.get_task(task_id); ui = self.task_ui_elements.get(task_id)
        if not task or not ui or not ui['frame'].winfo_exists(): return
        color_map = {DownloadStatus.COMPLETED: ColorPalette.STATUS_COMPLETED.value, DownloadStatus.DOWNLOADING: ColorPalette.STATUS_DOWNLOADING.value, DownloadStatus.ERROR: ColorPalette.STATUS_ERROR.value, DownloadStatus.PAUSED: ColorPalette.STATUS_PAUSED.value, DownloadStatus.CANCELLED: ColorPalette.STATUS_CANCELLED.value, DownloadStatus.PROCESSING: ColorPalette.STATUS_PROCESSING.value}
        color = color_map.get(task.status, ColorPalette.STATUS_QUEUED.value)
        ui['frame'].configure(border_color=color); ui['progress_bar'].configure(progress_color=color)
        if task.status == DownloadStatus.PROCESSING: ui['progress_bar'].start()
        else: ui['progress_bar'].stop(); ui['progress_bar'].set(task.progress_float)
        status_text = f"وضعیت: {task.status.value}"
        if task.status == DownloadStatus.DOWNLOADING: status_text += f" - {task.progress_str} از {task.total_bytes_str} ({task.speed_str}, ETA: {task.eta_str})"
        elif task.status == DownloadStatus.ERROR and task.error_message: status_text += f" - {task.error_message[:100]}"
        ui['status_label'].configure(text=clean_ansi_codes(status_text))
        is_finished = task.status in [DownloadStatus.COMPLETED, DownloadStatus.ERROR, DownloadStatus.CANCELLED, DownloadStatus.INVALID]
        ui['cancel_button'].configure(state="disabled" if is_finished else "normal")
        ui['open_folder_button'].configure(state="normal" if task.status == DownloadStatus.COMPLETED else "disabled")
        action_btn = ui['action_button']
        if task.status == DownloadStatus.DOWNLOADING: action_btn.configure(text=ICON_PAUSE, state="normal", command=lambda: self.download_manager.pause_task(task_id), fg_color=ColorPalette.STATUS_PAUSED.value)
        elif task.status == DownloadStatus.PAUSED: action_btn.configure(text=ICON_PLAY, state="normal", command=lambda: self.download_manager.resume_task(task_id), fg_color=ColorPalette.BUTTON_ACTION_FG.value)
        elif task.status in [DownloadStatus.ERROR, DownloadStatus.CANCELLED, DownloadStatus.INVALID]: action_btn.configure(text=ICON_RETRY, state="normal", command=lambda: self.download_manager.retry_task(task_id), fg_color=ColorPalette.BUTTON_ACTION_FG.value)
        elif task.status == DownloadStatus.COMPLETED: action_btn.configure(text=ICON_CLEAR, state="normal", command=lambda: self.download_manager.remove_task_from_ui(task_id), fg_color="gray")
        else: action_btn.configure(text="", state="disabled", fg_color="transparent")
        self.after(50, self._update_global_progress)
            
    def remove_task_widget(self, task_id: str):
        # ... (This method remains unchanged) ...
        ui = self.task_ui_elements.pop(task_id, None)
        if ui and ui['frame'].winfo_exists(): ui['frame'].destroy()
        with self.download_manager.state_lock:
            if not self.download_manager.tasks and not self.empty_queue_label.winfo_ismapped():
                self.empty_queue_label.pack(pady=50, padx=20, expand=True, fill="both")
        self.update_status_bar()
        self.after(50, self._update_global_progress)

    def _load_task_thumbnail(self, task: DownloadTask, label: ctk.CTkLabel):
        # ... (This method remains unchanged) ...
        def _loader():
            try:
                url = task.info_dict.get('thumbnail');
                if not url: return
                response = requests.get(url, stream=True, timeout=20)
                response.raise_for_status()
                with Image.open(BytesIO(response.content)) as pil_image:
                    pil_image.thumbnail((128, 72))
                    ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(128, 72))
                if label.winfo_exists(): self.after(0, lambda: label.configure(image=ctk_image, text=""))
            except Exception as e: self.log_message(f"خطا در لود تصویر تسک {task.title}: {e}", "warning")
        threading.Thread(target=_loader, daemon=True).start()

    def update_status_bar(self):
        # ... (This method remains unchanged) ...
        with self.download_manager.state_lock:
            active = len(self.download_manager.active_threads); queued = len(self.download_manager.download_queue)
            speed = sum(self._parse_speed(self.download_manager.tasks[tid].speed_str) for tid in self.download_manager.active_threads if tid in self.download_manager.tasks)
        max_dls = self.settings_manager.get('max_concurrent_downloads')
        self.status_bar_label.configure(text=f"فعال: {active} | در صف: {queued} | حداکثر: {max_dls}")
        self.speed_status_label.configure(text=f"سرعت کل: {humanize.naturalsize(speed, binary=True, gnu=True)}/s")

    def _update_global_progress(self):
        # ... (This method remains unchanged) ...
        with self.download_manager.state_lock:
            relevant_tasks = [task for task in self.download_manager.tasks.values() if task.status not in [DownloadStatus.COMPLETED, DownloadStatus.ERROR, DownloadStatus.CANCELLED, DownloadStatus.INVALID]]
            if not relevant_tasks: self.global_progress_bar.set(0); return
            total_progress = sum(task.progress_float for task in relevant_tasks)
            self.global_progress_bar.set(total_progress / len(relevant_tasks))

    def _parse_speed(self, speed_str: str) -> float:
        # ... (This method remains unchanged) ...
        match = re.search(r"([\d\.]+)\s*([KMGT]i?B)/s", speed_str, re.I)
        if not match: return 0.0
        val, unit = float(match.group(1)), match.group(2).upper()
        multipliers = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
        return val * multipliers.get(unit[0], 1)

    def update_disk_space_periodically(self):
        # ... (This method remains unchanged) ...
        try:
            download_path = self.settings_manager.get("download_path")
            if os.path.exists(download_path):
                usage = shutil.disk_usage(download_path)
                self.disk_space_label.configure(text=f"فضای دیسک: {humanize.naturalsize(usage.free, binary=True)}")
            else:
                self.disk_space_label.configure(text="فضای دیسک: مسیر نامعتبر")
        except Exception: self.disk_space_label.configure(text="فضای دیسک: خطا")
        self.after(30000, self.update_disk_space_periodically)

    class YTDLLogger:
        def __init__(self, app: 'AdvancedYoutubeDownloaderApp'): self.app = app
        def debug(self, msg: str):
            if self.app.settings_manager.get("debug_mode") and "[debug]" in msg: self.app.log_message(f"YT-DLP: {msg}", "debug")
        def info(self, msg: str): pass
        def warning(self, msg: str): self.app.log_message(f"YT-DLP هشدار: {msg}", "warning")
        def error(self, msg: str): self.app.log_message(f"YT-DLP خطا: {msg}", "error")

    def _open_settings_window(self):
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.focus(); return
        self.settings_window = SettingsWindow(parent=self, settings_manager=self.settings_manager, app_font=self.fonts['default'], available_fonts=self.available_fonts, apply_callback=self._apply_ui_settings)

    def _apply_ui_settings(self):
        new_theme = self.settings_manager.get("theme")
        ctk.set_appearance_mode(new_theme)
        
        new_font_family = self.settings_manager.get("font_family")
        if new_font_family != self.font_family:
            self.font_family = new_font_family
            self._create_font_objects()
            messagebox.showinfo("تغییر فونت", "فونت برنامه تغییر کرد. برای اعمال کامل تغییرات، بهتر است برنامه را مجدداً راه‌اندازی کنید.", parent=self)
        
        self.embed_subs_var.set(self.settings_manager.get("embed_subtitles"))
        self._configure_treeview_style()
        self.update_status_bar()
        self.update_disk_space_periodically()

    def _on_window_close(self):
        self.quit_app()

    def quit_app(self):
        self.log_message("درخواست خروج از برنامه.")
        self._on_closing()
        
    def _on_closing(self):
        self.log_message("برنامه در حال بسته شدن...")
        self.download_manager.shutdown()
        self.after(200, self.destroy)

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    app = AdvancedYoutubeDownloaderApp()
    app.mainloop()