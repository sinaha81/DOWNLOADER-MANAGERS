import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox, font as tkFont
import threading
import yt_dlp
import requests
from PIL import Image, ImageTk # Pillow for icons if used
from io import BytesIO
import os
import json
from pathlib import Path
import humanize
import time
import re
import shutil # For disk space
import sys # For sys.platform

# --- ثابت‌ها و تنظیمات ---
APP_NAME = "SINA Download Manager"
APP_VERSION = "2.1.5" # Version updated
SETTINGS_FILE = "downloader_settings_v3.json"

DEFAULT_SETTINGS = {
    "download_path": str(Path.home() / "Downloads" / "SinaDownloader"),
    "theme": "System",
    "max_concurrent_downloads": 3,
    "max_retries": 3,
    "default_download_type": "Video",
    "language": "fa",
    "cookies_file": "", # Path to cookies file
    "default_subtitle_langs": "en,fa", # Default subtitle languages to look for
    "embed_subtitles": True,
}

# اطمینان از وجود پوشه دانلود پیش‌فرض
Path(DEFAULT_SETTINGS["download_path"]).mkdir(parents=True, exist_ok=True)

# Unicode symbols for icons (simple approach)
ICON_SETTINGS = "⚙️"
ICON_DOWNLOAD = "🔽"
ICON_PAUSE = "⏸️"
ICON_RESUME = "▶️"
ICON_CANCEL = "❌"
ICON_RETRY = "🔄"
ICON_CLEAR = "🗑️"
ICON_FOLDER = "📁"
ICON_ANALYZE = "🔍"


def clean_ansi_codes(text):
    """Removes ANSI escape codes from a string."""
    if not isinstance(text, str):
        return text
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

class DownloadTask:
    """نشان‌دهنده یک وظیفه دانلود."""
    def __init__(self, task_id, url, ydl_opts, download_type, title="در حال دریافت عنوان...", original_url=None):
        self.task_id = task_id
        self.url = url
        self.original_url = original_url if original_url else url
        self.ydl_opts = ydl_opts
        self.download_type = download_type
        self.title = title
        self.status = "در صف"
        self.progress_str = "0%"
        self.progress_float = 0.0
        self.speed_str = "N/A"
        self.eta_str = "N/A"
        self.total_bytes_str = "N/A"
        self.downloaded_bytes = 0
        self.filepath = None
        self.error_message = None
        self.thread = None
        self.paused = False
        self.globally_paused = False
        self.retries = 0
        self.start_time = None
        self.info_dict = None

        self.frame = None
        self.title_label = None
        self.progress_bar = None
        self.status_label = None
        self.action_button_frame = None
        self.pause_resume_button = None
        self.cancel_button = None
        self.retry_clear_button = None


class AdvancedYoutubeDownloaderApp(ctk.CTk):
    """کلاس اصلی برنامه دانلود منیجر پیشرفته."""

    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} نسخه {APP_VERSION}")
        self.geometry("1100x800") 
        self.minsize(900, 650)

        self.settings = self.load_settings()
        ctk.set_appearance_mode(self.settings.get("theme", "System"))
        ctk.set_default_color_theme("blue")

        self.active_downloads = {}
        self.download_queue = []
        self.download_lock = threading.Lock()
        self.current_media_info = None
        self.thumbnail_image = None 
        self.is_globally_paused = False
        self.available_subs_map = {} 
        self.selected_subs_vars = {} 

        self.default_font = ctk.CTkFont(family="Tahoma", size=11)
        self.title_font = ctk.CTkFont(family="Tahoma", size=12, weight="bold")
        self.treeview_font = ("Tahoma", 10) 
        self.treeview_heading_font = ("Tahoma", 10, "bold")
        self.task_title_font = ctk.CTkFont(family="Tahoma", size=11, weight="bold")
        self.task_status_font = ctk.CTkFont(family="Tahoma", size=10)


        self._create_widgets()
        self._layout_widgets()
        self.update_status_bar()
        self.update_disk_space_periodically()

        self.after(1000, self._process_download_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.log_message("برنامه با موفقیت راه‌اندازی شد.")

    def _apply_appearance_mode(self, color_tuple):
        """Applies the correct color from a (light, dark) tuple based on current appearance mode."""
        if isinstance(color_tuple, (list, tuple)) and len(color_tuple) == 2:
            return color_tuple[1] if ctk.get_appearance_mode().lower() == "dark" else color_tuple[0]
        return color_tuple 

    def _create_widgets(self):
        """ایجاد تمام ویجت‌های UI."""
        # --- Top Frame ---
        self.top_frame = ctk.CTkFrame(self)
        self.url_label = ctk.CTkLabel(self.top_frame, text="لینک (URL):", font=self.default_font)
        self.url_entry = ctk.CTkEntry(self.top_frame, placeholder_text="لینک ویدیو، پلی‌لیست یا سایت را وارد کنید", font=self.default_font, width=400)
        self.analyze_button = ctk.CTkButton(self.top_frame, text=f"{ICON_ANALYZE} تحلیل لینک", command=self._analyze_url, font=self.default_font)

        # --- Main Content Frame (Info + Qualities + Subtitles) ---
        self.main_content_frame = ctk.CTkFrame(self, fg_color="transparent")

        # --- Info Sub-Frame (Thumbnail, Title, Download Type) ---
        self.info_sub_frame = ctk.CTkFrame(self.main_content_frame)
        self.thumbnail_label = ctk.CTkLabel(self.info_sub_frame, text="", width=160, height=90) 
        self.video_title_label = ctk.CTkLabel(self.info_sub_frame, text="عنوان: در دسترس نیست", wraplength=350, justify="left", font=self.default_font, anchor="nw")
        self.download_type_label = ctk.CTkLabel(self.info_sub_frame, text="نوع دانلود:", font=self.default_font)
        self.download_type_var = ctk.StringVar(value=self.settings.get("default_download_type", "Video"))
        self.download_type_segmented_button = ctk.CTkSegmentedButton(
            self.info_sub_frame, values=["ویدیو", "صوت"], variable=self.download_type_var,
            command=self._on_download_type_change, font=self.default_font 
        )
        self.download_type_segmented_button.set(self.settings.get("default_download_type", "Video").replace("Video","ویدیو").replace("Audio","صوت"))

        # --- Quality Treeview Frame ---
        self.quality_frame = ctk.CTkFrame(self.main_content_frame)
        self.quality_label = ctk.CTkLabel(self.quality_frame, text="انتخاب کیفیت:", font=self.title_font)
        
        self.tree_style = ttk.Style()
        self.tree_style.theme_use("default") 
        
        try:
            frame_fg_color_tuple = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
            label_text_color_tuple = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
            button_fg_color_tuple = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
            fg_color = self._apply_appearance_mode(frame_fg_color_tuple)
            text_color = self._apply_appearance_mode(label_text_color_tuple)
            selected_color = self._apply_appearance_mode(button_fg_color_tuple)
        except Exception as e: 
            self.log_message(f"خطا در خواندن رنگ‌های پوسته برای Treeview: {e}. استفاده از رنگ‌های پیش‌فرض.")
            fg_color = "#2a2d2e" if ctk.get_appearance_mode().lower() == "dark" else "#ebebeb"
            text_color = "white" if ctk.get_appearance_mode().lower() == "dark" else "black"
            selected_color = "#1f6aa5" 

        self.tree_style.configure("Treeview", background=fg_color, foreground=text_color, fieldbackground=fg_color, font=self.treeview_font, rowheight=25)
        self.tree_style.map("Treeview", background=[('selected', selected_color)], foreground=[('selected', text_color)])
        self.tree_style.configure("Treeview.Heading", font=self.treeview_heading_font, background=fg_color, foreground=text_color)

        self.quality_tree = ttk.Treeview(self.quality_frame, columns=("res", "fps", "vcodec", "acodec", "size", "ext", "note"), show="headings", height=6, style="Treeview")
        # ... (Headings and column configurations remain the same)
        self.quality_tree.heading("res", text="رزولوشن")
        self.quality_tree.heading("fps", text="فریم‌ریت")
        self.quality_tree.heading("vcodec", text="کدک ویدیو")
        self.quality_tree.heading("acodec", text="کدک صدا")
        self.quality_tree.heading("size", text="حجم تقریبی")
        self.quality_tree.heading("ext", text="فرمت")
        self.quality_tree.heading("note", text="توضیحات")
        for col in ("res", "fps", "vcodec", "acodec", "size", "ext", "note"):
            heading_text = self.quality_tree.heading(col)["text"]
            col_width = tkFont.Font(font=self.treeview_heading_font).measure(heading_text) + 25 
            self.quality_tree.column(col, width=col_width, anchor="center", stretch=False) 
        self.quality_tree.column("note", width=200, stretch=True) 
        self.quality_tree.column("size", width=100, stretch=False)

        # --- Subtitle Frame ---
        self.subtitle_frame = ctk.CTkFrame(self.main_content_frame)
        self.subtitle_label = ctk.CTkLabel(self.subtitle_frame, text="انتخاب زیرنویس (اختیاری):", font=self.title_font)
        self.subtitle_options_frame = ctk.CTkScrollableFrame(self.subtitle_frame, height=80, fg_color="transparent")
        self.embed_subs_var = ctk.BooleanVar(value=self.settings.get("embed_subtitles", True))
        self.embed_subs_checkbox = ctk.CTkCheckBox(self.subtitle_frame, text="ادغام زیرنویس در فایل ویدیو", variable=self.embed_subs_var, font=self.default_font)

        # --- Download Button ---
        self.download_button = ctk.CTkButton(self.main_content_frame, text=f"{ICON_DOWNLOAD} شروع دانلود", command=self._start_download, state="disabled", font=self.default_font)

        # --- Global Controls ---
        self.global_controls_frame = ctk.CTkFrame(self)
        self.pause_all_button = ctk.CTkButton(self.global_controls_frame, text=f"{ICON_PAUSE} مکث همه", command=self._toggle_pause_all, font=self.default_font)
        self.cancel_all_button = ctk.CTkButton(self.global_controls_frame, text=f"{ICON_CANCEL} لغو همه", command=self._cancel_all_tasks, font=self.default_font, fg_color="red")

        # --- TabView for Downloads and Logs ---
        self.bottom_tab_view = ctk.CTkTabview(self)
        self.bottom_tab_view.add("صف دانلود")
        self.bottom_tab_view.add("گزارش رویدادها")

        # --- Downloads Area (inside TabView) ---
        self.downloads_scroll_frame = ctk.CTkScrollableFrame(self.bottom_tab_view.tab("صف دانلود"), fg_color="transparent")
        
        # --- Log Area (inside TabView) ---
        self.log_textbox = ctk.CTkTextbox(self.bottom_tab_view.tab("گزارش رویدادها"), font=self.default_font, state="disabled", wrap="word")

        # --- Bottom Frame (Status Bar) ---
        self.status_bar_frame = ctk.CTkFrame(self) # Renamed from bottom_frame for clarity
        self.settings_button = ctk.CTkButton(self.status_bar_frame, text=ICON_SETTINGS, command=self._open_settings_window, font=self.default_font, width=40)
        self.status_bar_label = ctk.CTkLabel(self.status_bar_frame, text="وضعیت: آماده", font=self.default_font, anchor="e")
        self.speed_status_label = ctk.CTkLabel(self.status_bar_frame, text="سرعت کل: 0 B/s", font=self.default_font, anchor="w")
        self.disk_space_label = ctk.CTkLabel(self.status_bar_frame, text="فضای دیسک: N/A", font=self.default_font, anchor="w")

    def _layout_widgets(self):
        # Configure grid weights for responsive resizing
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Top frame: no vertical expansion
        self.grid_rowconfigure(1, weight=3)  # Main content (quality, info): expands most
        self.grid_rowconfigure(2, weight=0)  # Global controls: no vertical expansion
        self.grid_rowconfigure(3, weight=2)  # TabView (Downloads/Logs): expands
        self.grid_rowconfigure(4, weight=0)  # Status bar: no vertical expansion


        # Top Frame
        self.top_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="ew")
        self.top_frame.grid_columnconfigure(1, weight=1)
        self.url_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.analyze_button.grid(row=0, column=2, padx=5, pady=5)

        # Main Content Frame
        self.main_content_frame.grid(row=1, column=0, padx=10, pady=0, sticky="nsew")
        self.main_content_frame.grid_columnconfigure(0, weight=3) 
        self.main_content_frame.grid_columnconfigure(1, weight=1) 
        self.main_content_frame.grid_rowconfigure(0, weight=1) 
        self.main_content_frame.grid_rowconfigure(1, weight=0) 

        # Info Sub-Frame (Right Pane - Top)
        self.info_sub_frame.grid(row=0, column=1, padx=(5,0), pady=5, sticky="nsew") # Reduced padx
        self.info_sub_frame.grid_columnconfigure(0, weight=1)
        self.thumbnail_label.pack(pady=5, padx=5, anchor="center") # Use pack for centering
        self.video_title_label.pack(fill="x", pady=5, padx=5)
        self.download_type_label.pack(anchor="w", padx=5, pady=(10,0))
        self.download_type_segmented_button.pack(fill="x", pady=5, padx=5)

        # Quality Frame (Left Pane)
        self.quality_frame.grid(row=0, column=0, rowspan=2, padx=(0,5), pady=5, sticky="nsew") # Reduced padx
        self.quality_frame.grid_rowconfigure(1, weight=1)
        self.quality_frame.grid_columnconfigure(0, weight=1)
        self.quality_label.pack(side="top", anchor="w", padx=5, pady=(0,5))
        self.quality_tree.pack(side="top", fill="both", expand=True, padx=5, pady=5)


        # Subtitle Frame (Right Pane - Bottom)
        self.subtitle_frame.grid(row=1, column=1, padx=(5,0), pady=5, sticky="nsew") # Reduced padx
        self.subtitle_frame.grid_columnconfigure(0, weight=1)
        self.subtitle_frame.grid_rowconfigure(1, weight=1) 
        self.subtitle_label.pack(side="top", anchor="w", padx=5, pady=(5,0))
        self.subtitle_options_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        self.embed_subs_checkbox.pack(side="bottom", anchor="w", padx=5, pady=5)

        # Download button below quality and subtitle frames
        self.download_button.grid(row=2, column=0, columnspan=2, padx=10, pady=(5,10), sticky="ew") # Adjusted pady


        # Global Controls
        self.global_controls_frame.grid(row=2, column=0, padx=10, pady=(0,5), sticky="ew") # Moved up to row 2
        self.pause_all_button.pack(side="left", padx=5, pady=5)
        self.cancel_all_button.pack(side="left", padx=5, pady=5)

        # TabView for Downloads and Logs
        self.bottom_tab_view.grid(row=3, column=0, padx=10, pady=(5,5), sticky="nsew")
        self.bottom_tab_view.tab("صف دانلود").grid_columnconfigure(0, weight=1)
        self.bottom_tab_view.tab("صف دانلود").grid_rowconfigure(0, weight=1)
        self.bottom_tab_view.tab("گزارش رویدادها").grid_columnconfigure(0, weight=1)
        self.bottom_tab_view.tab("گزارش رویدادها").grid_rowconfigure(0, weight=1)

        self.downloads_scroll_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.log_textbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Status Bar Frame
        self.status_bar_frame.grid(row=4, column=0, padx=10, pady=(5,10), sticky="ew")
        self.status_bar_frame.grid_columnconfigure(2, weight=1) 
        self.settings_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.disk_space_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.speed_status_label.grid(row=0, column=2, padx=10, pady=5, sticky="w")
        self.status_bar_label.grid(row=0, column=3, padx=5, pady=5, sticky="e")

    # --- Core Logic Methods ---

    def _analyze_url(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("ورودی خالی", "لطفاً یک لینک برای تحلیل وارد کنید.", parent=self)
            return
        self.log_message(f"شروع تحلیل لینک: {url}")
        self._reset_analysis_ui() 
        self.analyze_button.configure(text="در حال تحلیل...", state="disabled")
        threading.Thread(target=self._fetch_media_info_thread, args=(url,), daemon=True).start()

    def _fetch_media_info_thread(self, url):
        try:
            ydl_opts = {'quiet': True, 'extract_flat': 'discard_in_playlist', 'noplaylist': False, 'listsubtitles': True, 'verbose': False} # Added verbose: False
            if self.settings.get("cookies_file") and os.path.exists(self.settings["cookies_file"]):
                ydl_opts['cookiefile'] = self.settings["cookies_file"]
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.current_media_info = ydl.extract_info(url, download=False)
            if not self.current_media_info:
                 raise yt_dlp.utils.DownloadError("اطلاعاتی از لینک دریافت نشد.")
            if 'entries' in self.current_media_info and self.current_media_info.get('_type') == 'playlist':
                self.after(0, self._handle_playlist_info)
            else: 
                self.after(0, self._update_ui_with_media_info, self.current_media_info)
        except yt_dlp.utils.DownloadError as e:
            error_msg = clean_ansi_codes(str(e))
            if "Unsupported URL" in error_msg: error_msg = "لینک پشتیبانی نمی‌شود."
            elif "Unable to extract" in error_msg: error_msg = "خطا در استخراج اطلاعات از لینک."
            self.after(0, lambda: messagebox.showerror("خطای تحلیل", f"عدم موفقیت در دریافت اطلاعات لینک: \n{error_msg}", parent=self))
            self.after(0, self._reset_analysis_ui)
            self.log_message(f"خطا در تحلیل لینک {url}: {error_msg}")
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("خطای تحلیل", f"یک خطای غیرمنتظره رخ داد: {clean_ansi_codes(str(e))}", parent=self))
            self.after(0, self._reset_analysis_ui)
            self.log_message(f"خطای غیرمنتظره در تحلیل لینک {url}: {clean_ansi_codes(str(e))}")


    def _reset_analysis_ui(self):
        self.analyze_button.configure(text=f"{ICON_ANALYZE} تحلیل لینک", state="normal")
        self.video_title_label.configure(text="عنوان: در دسترس نیست")
        self.thumbnail_label.configure(image=None, text="") 
        if isinstance(self.thumbnail_image, ImageTk.PhotoImage): 
            self.thumbnail_image = None
        for item in self.quality_tree.get_children():
            self.quality_tree.delete(item)
        for widget in self.subtitle_options_frame.winfo_children():
            widget.destroy()
        self.selected_subs_vars.clear()
        self.available_subs_map.clear()
        self.download_button.configure(state="disabled")
        self.current_media_info = None


    def _update_ui_with_media_info(self, info):
        if not info:
            self._reset_analysis_ui()
            return
        title = info.get('title', 'N/A')
        self.video_title_label.configure(text=f"عنوان: {title}")
        self.log_message(f"ویدیوی تحلیل شد: {title}")
        thumbnail_url = info.get('thumbnail')
        if thumbnail_url:
            threading.Thread(target=self._load_thumbnail, args=(thumbnail_url,), daemon=True).start()
        else:
            self.thumbnail_label.configure(image=None, text="بدون تصویر")
            if isinstance(self.thumbnail_image, ImageTk.PhotoImage): self.thumbnail_image = None
        self._populate_quality_treeview(info)
        self._populate_subtitle_options(info)
        self.download_button.configure(state="normal")
        self.analyze_button.configure(text=f"{ICON_ANALYZE} تحلیل لینک", state="normal")
        self._on_download_type_change() 


    def _handle_playlist_info(self):
        playlist_title = self.current_media_info.get('title', 'پلی‌لیست بدون عنوان')
        num_entries = len(self.current_media_info.get('entries', []))
        self.video_title_label.configure(text=f"پلی‌لیست: {playlist_title} ({num_entries} آیتم)")
        self.log_message(f"پلی‌لیست تحلیل شد: {playlist_title} با {num_entries} آیتم.")
        self.thumbnail_label.configure(text="پلی‌لیست", image=None)
        if isinstance(self.thumbnail_image, ImageTk.PhotoImage): self.thumbnail_image = None
        for item in self.quality_tree.get_children():
            self.quality_tree.delete(item)
        self.quality_tree.insert("", "end", values=("پلی‌لیست", "-", "-", "-", "N/A", "-", "دانلود با بهترین کیفیت پیش‌فرض برای هر آیتم"))
        for widget in self.subtitle_options_frame.winfo_children():
            widget.destroy()
        self.selected_subs_vars.clear()
        ctk.CTkLabel(self.subtitle_options_frame, text="زیرنویس‌ها برای هر آیتم جداگانه بررسی می‌شوند.", font=self.default_font).pack(anchor="center", pady=10)
        self.download_button.configure(state="normal", text=f"{ICON_DOWNLOAD} دانلود همه ({num_entries})")
        self.analyze_button.configure(text=f"{ICON_ANALYZE} تحلیل لینک", state="normal")


    def _populate_quality_treeview(self, info):
        for item in self.quality_tree.get_children():
            self.quality_tree.delete(item)
        if not info or 'formats' not in info:
            self.quality_tree.insert("", "end", values=("N/A",)*7)
            return
        formats = info.get('formats', [])
        download_type_ui = self.download_type_var.get() 
        processed_formats = []
        for f in formats:
            format_id = f.get('format_id')
            if not format_id: continue
            is_video_type = f.get('vcodec') != 'none' and f.get('vcodec') is not None
            is_audio_type = f.get('acodec') != 'none' and f.get('acodec') is not None
            if download_type_ui == "ویدیو":
                if not is_video_type: continue 
            elif download_type_ui == "صوت":
                if not is_audio_type: continue 
                if is_video_type and is_audio_type : pass 
                elif is_video_type and not is_audio_type: continue 
            res = f"{f.get('width')}x{f.get('height')}" if f.get('width') and f.get('height') else (f"{f.get('height')}p" if f.get('height') else "صدا")
            if download_type_ui == "صوت" and not is_video_type : res = "فقط صدا"
            fps = str(f.get('fps','-')) if is_video_type else "-"
            vcodec = f.get('vcodec','none').split('.')[0] if is_video_type else "-" 
            acodec = f.get('acodec','none').split('.')[0] if is_audio_type else "-" 
            filesize = f.get('filesize') or f.get('filesize_approx')
            size_str = humanize.naturalsize(filesize, binary=True, gnu=True) if filesize else "نامشخص"
            ext = f.get('ext', '-')
            note = clean_ansi_codes(f.get('format_note', '')) # Clean ANSI codes from note
            if f.get('acodec') == 'none' and is_video_type: note = "فقط ویدیو " + note
            elif f.get('vcodec') == 'none' and is_audio_type: note = "فقط صدا " + note
            elif is_video_type and is_audio_type: note = "ویدیو + صدا " + note
            processed_formats.append(((res, fps, vcodec, acodec, size_str, ext, note.strip()), f, format_id))
        if download_type_ui == "ویدیو":
            processed_formats.sort(key=lambda x: (x[1].get('height',0), x[1].get('vbr',0) or x[1].get('tbr',0) or 0), reverse=True)
        else: 
            processed_formats.sort(key=lambda x: (x[1].get('abr',0) or x[1].get('tbr',0) or 0), reverse=True)
        for fmt_values, _, format_id_val in processed_formats:
            self.quality_tree.insert("", "end", values=fmt_values, tags=(format_id_val,))
        if not processed_formats:
            self.quality_tree.insert("", "end", values=("فرمت مناسبی یافت نشد",)*7)
        elif processed_formats :
            try: 
                first_item_iid = self.quality_tree.get_children()[0]
                self.quality_tree.selection_set(first_item_iid)
                self.quality_tree.focus(first_item_iid)
            except IndexError:
                self.log_message("خطا: نتوانست اولین آیتم را در جدول کیفیت انتخاب کند.")


    def _populate_subtitle_options(self, info):
        for widget in self.subtitle_options_frame.winfo_children():
            widget.destroy()
        self.selected_subs_vars.clear()
        self.available_subs_map.clear()
        subs = info.get('subtitles') or info.get('automatic_captions') 
        if not subs:
            ctk.CTkLabel(self.subtitle_options_frame, text="زیرنویس یافت نشد.", font=self.default_font).pack(anchor="w", padx=5)
            return
        default_selected_langs = [lang.strip().lower() for lang in self.settings.get("default_subtitle_langs", "en,fa").split(',')]
        for lang_code, sub_info_list in subs.items():
            if sub_info_list: 
                lang_name = sub_info_list[0].get('name', lang_code) 
                is_auto = '(خودکار)' if info.get('automatic_captions') and lang_code in info.get('automatic_captions') else ''
                self.available_subs_map[lang_code] = lang_name
                var = ctk.BooleanVar()
                if lang_code.lower() in default_selected_langs:
                    var.set(True)
                cb = ctk.CTkCheckBox(self.subtitle_options_frame, text=f"{lang_name} ({lang_code}) {is_auto}", variable=var, font=self.default_font)
                cb.pack(anchor="w", padx=5, pady=2)
                self.selected_subs_vars[lang_code] = var
        if not self.available_subs_map: 
             ctk.CTkLabel(self.subtitle_options_frame, text="زیرنویس یافت نشد.", font=self.default_font).pack(anchor="w", padx=5)


    def _on_download_type_change(self, *args): 
        if self.current_media_info:
            if 'entries' in self.current_media_info and self.current_media_info.get('_type') == 'playlist':
                pass
            elif 'entries' not in self.current_media_info: 
                 self._populate_quality_treeview(self.current_media_info)


    def _start_download(self):
        if not self.current_media_info:
            messagebox.showerror("خطا", "لطفاً ابتدا یک لینک را تحلیل کنید.", parent=self)
            return
        download_type_ui = self.download_type_var.get()
        download_type_internal = "Video" if download_type_ui == "ویدیو" else "Audio"
        selected_subs_langs_ui = [lang for lang, var in self.selected_subs_vars.items() if var.get()]
        if 'entries' in self.current_media_info and self.current_media_info.get('_type') == 'playlist':
            self._download_playlist(download_type_internal, selected_subs_langs_ui)
        else: 
            selected_item_iid = self.quality_tree.focus()
            if not selected_item_iid:
                messagebox.showerror("خطا", "لطفاً یک کیفیت از جدول انتخاب کنید.", parent=self)
                return
            try:
                selected_format_id = self.quality_tree.item(selected_item_iid, "tags")[0]
            except IndexError: 
                 messagebox.showerror("خطا", "آیتم انتخاب شده در جدول کیفیت معتبر نیست.", parent=self)
                 return
            if not selected_format_id or selected_format_id == "پلی‌لیست": 
                 messagebox.showerror("خطا", "کیفیت انتخاب شده معتبر نیست (پلی‌لیست).", parent=self)
                 return
            self._download_single_media(selected_format_id, download_type_internal, selected_subs_langs_ui)


    def _download_playlist(self, download_type_internal, ui_selected_subs_langs):
        playlist_info = self.current_media_info
        if not playlist_info or 'entries' not in playlist_info: return
        num_entries = len(playlist_info['entries'])
        confirm = messagebox.askyesno("تأیید دانلود پلی‌لیست",
                                      f"آیا می‌خواهید تمام {num_entries} آیتم از پلی‌لیست '{playlist_info.get('title', 'N/A')}' دانلود شوند؟\n(زیرنویس‌ها بر اساس تنظیمات و انتخاب شما اعمال خواهند شد)", parent=self)
        if not confirm: return
        format_selector = "bestvideo*+bestaudio/best" 
        if download_type_internal == "Audio":
            format_selector = "bestaudio/best"
        for entry in playlist_info['entries']:
            if entry is None: continue 
            video_url = entry.get('webpage_url') or entry.get('url') # Prefer webpage_url if available
            if not video_url and entry.get('id'): 
                 video_url = f"https://www.youtube.com/watch?v={entry.get('id')}" 
            video_title = entry.get('title', f"آیتم پلی‌لیست - {entry.get('id', 'ID نامشخص')}")
            task_id = f"task_{time.time_ns()}_{entry.get('id','random')}" 
            ydl_opts = self._get_ydl_opts(format_selector, download_type_internal, ui_selected_subs_langs,
                                          is_playlist_item=True, playlist_title=playlist_info.get('title'))
            task = DownloadTask(task_id, video_url, ydl_opts, download_type_internal, title=video_title, original_url=self.url_entry.get().strip())
            task.info_dict = entry 
            self._add_task_to_queue(task)
        self.log_message(f"{num_entries} آیتم از پلی‌لیست به صف دانلود اضافه شد.")


    def _download_single_media(self, selected_format_id, download_type_internal, ui_selected_subs_langs):
        media_url = self.current_media_info.get('webpage_url') or self.url_entry.get().strip()
        media_title = self.current_media_info.get('title', 'فایل بدون عنوان')
        task_id = f"task_{time.time_ns()}" 
        ydl_opts = self._get_ydl_opts(selected_format_id, download_type_internal, ui_selected_subs_langs)
        task = DownloadTask(task_id, media_url, ydl_opts, download_type_internal, title=media_title)
        task.info_dict = self.current_media_info 
        self._add_task_to_queue(task)
        self.log_message(f"فایل '{media_title}' برای دانلود به صف اضافه شد.")


    def _get_ydl_opts(self, format_selector, download_type_internal, ui_selected_subtitle_langs=None,
                      is_playlist_item=False, playlist_title=None):
        def sanitize_filename(name):
            name = re.sub(r'[<>:"/\\|?*]', '_', name) 
            name = re.sub(r'\s+', ' ', name).strip()   
            return name
        base_path = self.settings["download_path"]
        title_template = '%(title).100s - %(id)s.%(ext)s' 
        if is_playlist_item:
            sane_playlist_title = sanitize_filename(playlist_title if playlist_title else "Playlist")
            download_path_template = os.path.join(base_path, sane_playlist_title[:50], '%(playlist_index)s - ' + title_template)
        else:
            download_path_template = os.path.join(base_path, title_template)
        ydl_opts = {
            'outtmpl': download_path_template,
            'progress_hooks': [self._yt_dlp_progress_hook],
            'postprocessor_hooks': [self._yt_dlp_postprocessor_hook],
            'noprogress': True, 'quiet': True, 'verbose': False,
            'retries': self.settings["max_retries"],
            'continuedl': True, 'nopart': True, 
            'ignoreerrors': True if is_playlist_item else False, 
            'encoding': 'utf-8',
            'restrictfilenames': sys.platform == "win32", 
        }
        if self.settings.get("cookies_file") and os.path.exists(self.settings["cookies_file"]):
            ydl_opts['cookiefile'] = self.settings["cookies_file"]

        if download_type_internal == "Audio":
            ydl_opts['format'] = "bestaudio/best" # Always best audio for audio type
            if format_selector and not ("bestaudio" in format_selector or "/" in format_selector):
                 # If a specific audio format ID was somehow passed, use it.
                 # This path is less likely if UI for audio only shows audio formats.
                 ydl_opts['format'] = format_selector
            ydl_opts.update({
                'extract_audio': True,
                'audioformat': 'mp3', 
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                    {'key': 'FFmpegMetadata', 'add_metadata': True}, 
                    {'key': 'EmbedThumbnail', 'already_have_thumbnail': False}, 
                ],
                'writethumbnail': True, 
            })
            if 'writesubtitles' in ydl_opts: del ydl_opts['writesubtitles']
            if 'embedsubtitles' in ydl_opts: del ydl_opts['embedsubtitles']

        elif download_type_internal == "Video":
            # Ensure the format selector requests both best video and best audio.
            # If format_selector is a specific video stream ID (e.g., "299"), add best audio.
            # If format_selector is a generic like "bestvideo", add best audio.
            # If format_selector already includes audio (e.g., "299+140" or "bestvideo*+bestaudio"), use as is.
            if format_selector == "bestvideo*+bestaudio/best" or (is_playlist_item and format_selector == "bestvideo*+bestaudio/best"): # Default for playlist
                ydl_opts['format'] = "bestvideo*+bestaudio/best"
            elif '+' in format_selector or 'audio' in format_selector.lower(): # Already combined or audio-inclusive
                ydl_opts['format'] = format_selector
            else: # Assumed to be a video-only stream ID or "bestvideo"
                ydl_opts['format'] = f"{format_selector}+bestaudio/best"


            effective_subtitle_langs_to_request = []
            if ui_selected_subtitle_langs: 
                effective_subtitle_langs_to_request = ui_selected_subtitle_langs
            else: 
                default_langs_str = self.settings.get("default_subtitle_langs", "") 
                if default_langs_str:
                    effective_subtitle_langs_to_request = [lang.strip() for lang in default_langs_str.split(',') if lang.strip()]
            
            if self.embed_subs_var.get(): 
                ydl_opts['writesubtitles'] = True 
                ydl_opts['embedsubtitles'] = True
                ydl_opts['subtitlesformat'] = 'srt/ass/vtt/best'
                if effective_subtitle_langs_to_request:
                    ydl_opts['subtitleslangs'] = effective_subtitle_langs_to_request
            elif effective_subtitle_langs_to_request: 
                ydl_opts['writesubtitles'] = True
                ydl_opts['subtitleslangs'] = effective_subtitle_langs_to_request
                ydl_opts['subtitlesformat'] = 'srt/ass/vtt/best'
            
            if ydl_opts.get('embedsubtitles'): 
                ydl_opts['merge_output_format'] = 'mkv' # MKV is best for embedded subs
            elif '+' in ydl_opts.get('format', ''): 
                ydl_opts.setdefault('merge_output_format', 'mkv') # Prefer mkv if merging
            else: 
                ydl_opts.setdefault('merge_output_format', 'mp4')
        return ydl_opts

    def _add_task_to_queue(self, task):
        with self.download_lock:
            self.download_queue.append(task)
        task_frame = ctk.CTkFrame(self.downloads_scroll_frame, corner_radius=5, border_width=1) # Added border
        task_frame.pack(fill="x", pady=5, padx=5)
        task.frame = task_frame
        task.frame._task_id_ref = task.task_id 
        
        # Top part of task frame: Title and Progress Bar
        top_task_info_frame = ctk.CTkFrame(task_frame, fg_color="transparent")
        top_task_info_frame.pack(side="top", fill="x", padx=5, pady=(5,2))
        top_task_info_frame.grid_columnconfigure(0, weight=1)

        task_title_label = ctk.CTkLabel(top_task_info_frame, text=task.title, anchor="w", font=self.task_title_font)
        task_title_label.grid(row=0, column=0, sticky="ew", pady=(0,2))
        task.title_label = task_title_label

        task_progress_bar = ctk.CTkProgressBar(top_task_info_frame, orientation="horizontal", height=10) # Slightly thicker
        task_progress_bar.set(0)
        task_progress_bar.grid(row=1, column=0, sticky="ew")
        task.progress_bar = task_progress_bar

        # Bottom part of task frame: Status and Buttons
        bottom_task_info_frame = ctk.CTkFrame(task_frame, fg_color="transparent")
        bottom_task_info_frame.pack(side="top", fill="x", padx=5, pady=(2,5))
        bottom_task_info_frame.grid_columnconfigure(0, weight=1) # Status label expands

        task_status_label = ctk.CTkLabel(bottom_task_info_frame, text=f"وضعیت: {task.status}", anchor="w", font=self.task_status_font)
        task_status_label.grid(row=0, column=0, sticky="ew", padx=(0,5))
        task.status_label = task_status_label

        action_button_frame = ctk.CTkFrame(bottom_task_info_frame, fg_color="transparent")
        action_button_frame.grid(row=0, column=1, sticky="e")
        task.action_button_frame = action_button_frame

        button_width = 35 # Smaller buttons
        task.pause_resume_button = ctk.CTkButton(action_button_frame, text=ICON_PAUSE, width=button_width, font=self.default_font,
                                             command=lambda t=task: self._toggle_pause_task(t.task_id))
        task.pause_resume_button.pack(side="left", padx=(0,2)) 
        task.cancel_button = ctk.CTkButton(action_button_frame, text=ICON_CANCEL, width=button_width, font=self.default_font, fg_color="orange",
                                         command=lambda t=task: self._cancel_task(t.task_id))
        task.cancel_button.pack(side="left", padx=2)
        task.retry_clear_button = ctk.CTkButton(action_button_frame, text=" ", width=button_width, font=self.default_font) 
        task.retry_clear_button.pack(side="left", padx=(2,0))
        
        self._update_task_ui(task) 
        self.update_status_bar()

    def _update_task_ui(self, task):
        if not (task and task.frame and task.frame.winfo_exists()): return 
        
        if task.title_label:
            task.title_label.configure(text=task.title) # Wraplength handled by grid/pack

        if task.progress_bar: task.progress_bar.set(task.progress_float if task.progress_float is not None else 0)

        status_text = f"وضعیت: {clean_ansi_codes(task.status)}"
        if task.status == "در حال دانلود": 
            status_text += f" - {clean_ansi_codes(task.progress_str)} ({clean_ansi_codes(task.speed_str)}, ETA: {clean_ansi_codes(task.eta_str)})"
        elif task.status == "خطا": 
            status_text += f" - {clean_ansi_codes(task.error_message or 'خطای نامشخص')}"
        elif task.status == "تکمیل شد": 
            status_text += f" - در: {os.path.basename(task.filepath) if task.filepath else 'N/A'}"
        
        if task.status_label: task.status_label.configure(text=status_text)

        if task.pause_resume_button:
            if task.status in ["در حال دانلود", "در حال شروع..."]:
                task.pause_resume_button.configure(text=ICON_PAUSE, state="normal")
            elif task.status == "مکث شده" or task.status == "مکث شده (کلی)":
                task.pause_resume_button.configure(text=ICON_RESUME, state="normal")
            else: task.pause_resume_button.configure(text=ICON_PAUSE, state="disabled")
        
        if task.cancel_button:
            if task.status not in ["تکمیل شد", "لغو شده", "خطا", "ناموفق"]: task.cancel_button.configure(state="normal")
            else: task.cancel_button.configure(state="disabled")
        
        if task.retry_clear_button:
            if task.status == "خطا" and task.retries < self.settings["max_retries"]:
                task.retry_clear_button.configure(text=ICON_RETRY, state="normal", fg_color="green")
            elif task.status in ["تکمیل شد", "لغو شده", "ناموفق"] or (task.status == "خطا" and task.retries >= self.settings["max_retries"]):
                task.retry_clear_button.configure(text=ICON_CLEAR, state="normal", fg_color="gray")
            else: task.retry_clear_button.configure(text=" ", state="disabled") 
        
        self.update_status_bar()


    def _open_settings_window(self):
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.focus()
            return
        self.settings_window = ctk.CTkToplevel(self)
        self.settings_window.title("تنظیمات")
        self.settings_window.geometry("550x480")
        self.settings_window.transient(self) 
        self.settings_window.grab_set()      
        self.settings_window.attributes("-topmost", True)
        # ... (rest of settings window code remains the same)
        ctk.CTkLabel(self.settings_window, text="مسیر دانلود:", font=self.default_font).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.settings_path_entry = ctk.CTkEntry(self.settings_window, width=350, font=self.default_font)
        self.settings_path_entry.insert(0, self.settings["download_path"])
        self.settings_path_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(self.settings_window, text=f"{ICON_FOLDER} انتخاب...", command=self._browse_download_path, font=self.default_font).grid(row=0, column=2, padx=10, pady=10)
        ctk.CTkLabel(self.settings_window, text="پوسته برنامه:", font=self.default_font).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.settings_theme_var = ctk.StringVar(value=self.settings["theme"])
        theme_options = ctk.CTkOptionMenu(self.settings_window, variable=self.settings_theme_var, values=["System", "Dark", "Light"], font=self.default_font)
        theme_options.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(self.settings_window, text="حداکثر دانلود همزمان:", font=self.default_font).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.settings_max_downloads_var = ctk.StringVar(value=str(self.settings["max_concurrent_downloads"]))
        max_downloads_entry = ctk.CTkEntry(self.settings_window, textvariable=self.settings_max_downloads_var, width=50, font=self.default_font)
        max_downloads_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        ctk.CTkLabel(self.settings_window, text="نوع دانلود پیش‌فرض:", font=self.default_font).grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.settings_default_type_var = ctk.StringVar(value=self.settings.get("default_download_type", "Video").replace("Video","ویدیو").replace("Audio","صوت"))
        default_type_options = ctk.CTkOptionMenu(self.settings_window, variable=self.settings_default_type_var, values=["ویدیو", "صوت"], font=self.default_font)
        default_type_options.grid(row=3, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(self.settings_window, text="فایل کوکی (اختیاری):", font=self.default_font).grid(row=4, column=0, padx=10, pady=10, sticky="w")
        self.settings_cookies_entry = ctk.CTkEntry(self.settings_window, width=350, font=self.default_font)
        self.settings_cookies_entry.insert(0, self.settings.get("cookies_file", ""))
        self.settings_cookies_entry.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(self.settings_window, text=f"{ICON_FOLDER} انتخاب...", command=self._browse_cookies_file, font=self.default_font).grid(row=4, column=2, padx=10, pady=10)
        ctk.CTkLabel(self.settings_window, text="زبان‌های پیش‌فرض زیرنویس (جدا با کاما):", font=self.default_font).grid(row=5, column=0, padx=10, pady=10, sticky="w")
        self.settings_subs_entry = ctk.CTkEntry(self.settings_window, width=150, font=self.default_font)
        self.settings_subs_entry.insert(0, self.settings.get("default_subtitle_langs", "en,fa"))
        self.settings_subs_entry.grid(row=5, column=1, padx=10, pady=10, sticky="w")
        self.settings_embed_subs_var = ctk.BooleanVar(value=self.settings.get("embed_subtitles", True))
        ctk.CTkCheckBox(self.settings_window, text="ادغام زیرنویس (پیش‌فرض کلی)", variable=self.settings_embed_subs_var, font=self.default_font).grid(row=5, column=2, padx=10, pady=10, sticky="w")
        save_button = ctk.CTkButton(self.settings_window, text="ذخیره تنظیمات", command=self._apply_settings, font=self.default_font)
        save_button.grid(row=6, column=0, columnspan=3, padx=10, pady=20)
        self.settings_window.grid_columnconfigure(1, weight=1) 

    def _browse_cookies_file(self):
        path = filedialog.askopenfilename(
            title="انتخاب فایل کوکی (فرمت Netscape)",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
            parent=self.settings_window 
        )
        if path:
            self.settings_cookies_entry.delete(0, ctk.END)
            self.settings_cookies_entry.insert(0, path)

    def _apply_settings(self):
        new_path = self.settings_path_entry.get()
        if not os.path.isdir(new_path):
            try:
                Path(new_path).mkdir(parents=True, exist_ok=True)
                self.settings["download_path"] = new_path
            except Exception as e:
                messagebox.showerror("خطا", f"مسیر دانلود نامعتبر: {new_path}\n{e}. لطفاً یک مسیر معتبر انتخاب کنید.", parent=self.settings_window)
                return
        else: self.settings["download_path"] = new_path
        new_theme = self.settings_theme_var.get()
        if new_theme != self.settings["theme"]:
            self.settings["theme"] = new_theme
            ctk.set_appearance_mode(new_theme)
        try:
            max_dls = int(self.settings_max_downloads_var.get())
            if 1 <= max_dls <= 10: self.settings["max_concurrent_downloads"] = max_dls
            else: raise ValueError("حداکثر دانلود همزمان باید بین 1 تا 10 باشد.")
        except ValueError as e:
            messagebox.showerror("خطا", str(e), parent=self.settings_window)
            return
        self.settings["default_download_type"] = self.settings_default_type_var.get().replace("ویدیو","Video").replace("صوت","Audio")
        self.settings["cookies_file"] = self.settings_cookies_entry.get()
        self.settings["default_subtitle_langs"] = self.settings_subs_entry.get()
        self.settings["embed_subtitles"] = self.settings_embed_subs_var.get() 
        self.save_settings()
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        self.log_message("تنظیمات اعمال شدند.")
        self.update_disk_space()
        self.embed_subs_var.set(self.settings.get("embed_subtitles", True))


    def _load_thumbnail(self, url):
        try:
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status() 
            image_data = BytesIO(response.content)
            pil_image = Image.open(image_data)
            pil_image.thumbnail((160, 90)) 
            self.thumbnail_image = ImageTk.PhotoImage(pil_image) 
            self.after(0, lambda: self.thumbnail_label.configure(image=self.thumbnail_image, text=""))
        except Exception as e:
            self.after(0, lambda: self.thumbnail_label.configure(image=None, text="خطای تصویر")) 
            self.log_message(f"خطا در بارگذاری تصویر {url}: {e}")

    def _process_download_queue(self):
        with self.download_lock:
            running_tasks_count = 0
            for task_iter in self.active_downloads.values():
                if task_iter.status == "در حال دانلود" and not task_iter.paused and not task_iter.globally_paused:
                    running_tasks_count +=1
            while running_tasks_count < self.settings["max_concurrent_downloads"] and self.download_queue:
                task = self.download_queue.pop(0)
                if task.status == "لغو شده": 
                    self._remove_task_ui(task.task_id, remove_from_active=False) 
                    continue
                if self.is_globally_paused: 
                    task.status = "مکث شده (کلی)"
                    task.globally_paused = True
                    self.active_downloads[task.task_id] = task 
                    self._update_task_ui(task)
                    continue 
                self.active_downloads[task.task_id] = task
                task.status = "در حال شروع..."
                task.globally_paused = self.is_globally_paused 
                self._update_task_ui(task)
                task.thread = threading.Thread(target=self._execute_download_task, args=(task,), daemon=True)
                task.thread.start()
                running_tasks_count += 1
                self.log_message(f"شروع دانلود برای: {task.title}")
        self.update_status_bar()
        self.after(1000, self._process_download_queue) 

    def _execute_download_task(self, task):
        try:
            task.start_time = time.time()
            if task.globally_paused or task.paused: 
                task.status = "مکث شده (کلی)" if task.globally_paused else "مکث شده"
                self._finalize_task(task.task_id) 
                return
            if task.ydl_opts.get('outtmpl'):
                dummy_info_for_path = {
                    'playlist_title': 'پلی‌لیست', 'title': task.title, 'id': 'شناسه',
                    'ext': task.ydl_opts.get('audioformat', 'mp4'), 
                     'playlist_index': '00', 'webpage_url': task.url,
                    **(task.info_dict or {}) 
                }
                try:
                    temp_title_for_path = re.sub(r'[<>:"/\\|?*]', '_', task.title[:50]) 
                    dummy_info_for_path['title'] = temp_title_for_path
                    if 'playlist_title' in dummy_info_for_path and dummy_info_for_path['playlist_title']:
                        dummy_info_for_path['playlist_title'] = re.sub(r'[<>:"/\\|?*]', '_', str(dummy_info_for_path['playlist_title'])[:50])
                    full_path_template = task.ydl_opts['outtmpl']
                    sample_output_path = full_path_template % dummy_info_for_path
                    output_dir = os.path.dirname(sample_output_path)
                    Path(output_dir).mkdir(parents=True, exist_ok=True)
                except Exception as path_e:
                    self.log_message(f"خطا در ایجاد پوشه دانلود برای {task.title}: {path_e}. استفاده از مسیر پیش‌فرض.")
                    default_title_template = '%(title).100s - %(id)s.%(ext)s'
                    task.ydl_opts['outtmpl'] = os.path.join(self.settings["download_path"], default_title_template)
            with yt_dlp.YoutubeDL(task.ydl_opts) as ydl:
                ydl.download([task.url]) 
            if task.status not in ["تکمیل شد", "خطا", "لغو شده"]:
                 task.status = "پردازش نهایی..." 
                 self._update_task_ui(task)
        except yt_dlp.utils.DownloadError as e:
            task.status = "خطا"; task.error_message = clean_ansi_codes(str(e))
            self.log_message(f"خطای DownloadError برای '{task.title}': {clean_ansi_codes(str(e))}")
        except Exception as e: 
            task.status = "خطا"; task.error_message = clean_ansi_codes(f"خطای غیرمنتظره: {str(e)}")
            self.log_message(f"خطای غیرمنتظره برای '{task.title}': {clean_ansi_codes(str(e))}")
        finally:
            if task.status not in ["تکمیل شد", "لغو شده", "خطا"]: 
                task.status = "ناموفق" if task.status != "خطا" else "خطا"
            self._finalize_task(task.task_id)

    def _yt_dlp_progress_hook(self, d):
        task_id = self._find_task_for_hook(d)
        if not task_id: return
        task = self.active_downloads.get(task_id)
        if not task: return
        if task.globally_paused or task.paused:
            if task.status == "در حال دانلود": 
                new_status = "مکث شده (کلی)" if task.globally_paused else "مکث شده"
                if task.status != new_status:
                    task.status = new_status
                    self.after(0, self._update_task_ui, task)
            return 
        if d['status'] == 'downloading':
            task.status = "در حال دانلود"; task.downloaded_bytes = d.get('downloaded_bytes', 0)
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes and total_bytes > 0:
                task.progress_float = min(1.0, task.downloaded_bytes / total_bytes)
                task.progress_str = f"{task.progress_float:.1%}"
                task.total_bytes_str = humanize.naturalsize(total_bytes, binary=True, gnu=True)
            else: 
                task.progress_str = f"{humanize.naturalsize(task.downloaded_bytes, binary=True, gnu=True)}"
                task.total_bytes_str = "نامشخص"
            task.speed_str = clean_ansi_codes(d.get('_speed_str', "N/A").replace("Unknown", "N/A"))
            task.eta_str = clean_ansi_codes(d.get('_eta_str', "N/A").replace("Unknown", "N/A"))
            if 'filename' in d and d['filename'] != '-' : task.filepath = d.get('filename') 
        elif d['status'] == 'finished': 
            task.status = "در حال پردازش..."; task.progress_float = 1.0; task.progress_str = "100%"
            if 'filename' in d and d['filename'] != '-' : task.filepath = d.get('filename')
        elif d['status'] == 'error':
            task.status = "خطا"; task.error_message = clean_ansi_codes(d.get('error', "خطای نامشخص yt-dlp"))
            self.log_message(f"خطای yt-dlp برای '{task.title}': {task.error_message}")
        self.after(0, self._update_task_ui, task) 

    def _yt_dlp_postprocessor_hook(self, d):
        task_id = self._find_task_for_hook(d, from_info_dict=True) 
        if not task_id: return
        task = self.active_downloads.get(task_id)
        if not task: return
        if d['status'] == 'finished': 
            task.status = "تکمیل شد"; task.progress_float = 1.0; task.progress_str = "100%"
            if 'info_dict' in d and 'filepath' in d['info_dict']: 
                task.filepath = d['info_dict']['filepath']
            self.log_message(f"دانلود و پردازش موفق: {task.title} در {task.filepath or 'مسیر نامشخص'}")
        elif d['status'] == 'error':
            task.status = "خطا"; task.error_message = clean_ansi_codes(f"خطای پس‌پردازش ({d.get('postprocessor')}): {d.get('error', 'نامشخص')}")
            self.log_message(f"خطای پس‌پردازش برای '{task.title}': {task.error_message}")
        self.after(0, self._update_task_ui, task)

    def _find_task_for_hook(self, d, from_info_dict=False):
        info_dict = d.get('info_dict', {})
        hook_video_id = info_dict.get('id') 
        hook_filename_direct = d.get('filename') 
        hook_filename_info_dict = info_dict.get('_filename') or info_dict.get('filepath')
        with self.download_lock: 
            candidate_tasks = [(tid, tsk) for tid, tsk in self.active_downloads.items() if tsk.status in ["در حال دانلود", "در حال پردازش...", "در حال شروع..."]]
            if not candidate_tasks: candidate_tasks = list(self.active_downloads.items())
            if len(candidate_tasks) == 1: return candidate_tasks[0][0]
            if hook_video_id:
                for task_id, task in candidate_tasks:
                    if task.info_dict and task.info_dict.get('id') == hook_video_id: return task_id
            if hook_filename_direct and hook_filename_direct != '-':
                for task_id, task in candidate_tasks:
                    try:
                        if Path(task.filepath or "").name == Path(hook_filename_direct).name : return task_id # More robust filename check
                        sanitized_task_title = re.sub(r'[<>:"/\\|?*]', '_', task.title[:50])
                        if sanitized_task_title in Path(hook_filename_direct).name: return task_id
                    except Exception: pass 
            if hook_filename_info_dict and hook_filename_info_dict != '-':
                 for task_id, task in candidate_tasks:
                    try:
                        if Path(task.filepath or "").name == Path(hook_filename_info_dict).name : return task_id # More robust filename check
                        sanitized_task_title = re.sub(r'[<>:"/\\|?*]', '_', task.title[:50])
                        if sanitized_task_title in Path(hook_filename_info_dict).name: return task_id
                    except Exception: pass
        return None 

    def _finalize_task(self, task_id):
        task = None
        with self.download_lock: 
            if task_id in self.active_downloads: 
                task = self.active_downloads.pop(task_id, None) 
        if task:
            if task.status not in ["تکمیل شد", "لغو شده", "خطا", "ناموفق"]: 
                task.status = "پایان یافته (نامشخص)" 
            self.after(0, self._update_task_ui, task) 
            if task.status == "خطا" and task.retries >= self.settings["max_retries"]:
                 self.log_message(f"وظیفه '{task.title}' پس از حداکثر تلاش ناموفق بود.")
        self.update_status_bar()

    def _toggle_pause_all(self):
        self.is_globally_paused = not self.is_globally_paused
        action_icon = ICON_RESUME if self.is_globally_paused else ICON_PAUSE
        action_text = "ادامه" if self.is_globally_paused else "مکث"
        self.pause_all_button.configure(text=f"{action_icon} {action_text} همه")
        self.log_message(f"همه دانلودها {action_text} شدند.")
        with self.download_lock:
            for task in self.active_downloads.values():
                task.globally_paused = self.is_globally_paused
                if self.is_globally_paused:
                    if task.status == "در حال دانلود": task.status = "مکث شده (کلی)"
                else: 
                    if task.status == "مکث شده (کلی)" and not task.paused : task.status = "در صف" 
                self.after(0, self._update_task_ui, task)
            for task in self.download_queue:
                task.globally_paused = self.is_globally_paused
                if self.is_globally_paused:
                     if task.status == "در صف": task.status = "مکث شده (کلی)"
                else: 
                     if task.status == "مکث شده (کلی)": task.status = "در صف"
        if not self.is_globally_paused: 
            self.after(100, self._process_download_queue) 

    def _cancel_all_tasks(self):
        if not messagebox.askyesno("لغو همه", "آیا مطمئن هستید که می‌خواهید همه دانلودها را لغو کنید؟", parent=self): return
        with self.download_lock:
            for task_id in list(self.active_downloads.keys()): 
                task = self.active_downloads.get(task_id)
                if task: 
                    task.status = "لغو شده"
                    self.log_message(f"وظیفه فعال لغو شد (علامت‌گذاری شده): {task.title}")
                    self.after(0, self._update_task_ui, task) 
            for task in self.download_queue: 
                task.status = "لغو شده"
                self.log_message(f"وظیفه در صف لغو شد: {task.title}")
        self.log_message("همه دانلودها برای لغو علامت‌گذاری شدند."); self.update_status_bar()

    def _toggle_pause_task(self, task_id):
        task = self.active_downloads.get(task_id)
        if not task: return
        task.paused = not task.paused
        if task.paused: 
            task.status = "مکث شده"
            self.log_message(f"وظیفه '{task.title}' مکث شد.")
        else: 
            task.status = "مکث شده (کلی)" if task.globally_paused else "در حال دانلود" 
            self.log_message(f"وظیفه '{task.title}' ادامه یافت.")
        self._update_task_ui(task)
        if not task.paused and not task.globally_paused: 
            self.after(100, self._process_download_queue) 

    def _cancel_task(self, task_id):
        task_to_cancel = None
        with self.download_lock:
            if task_id in self.active_downloads: 
                task_to_cancel = self.active_downloads[task_id]
            else: 
                for queued_task in self.download_queue: 
                    if queued_task.task_id == task_id: 
                        task_to_cancel = queued_task 
                        break
        if task_to_cancel: 
            task_to_cancel.status = "لغو شده"
            self.log_message(f"وظیفه '{task_to_cancel.title}' لغو شد.")
            if task_to_cancel.frame and task_to_cancel.frame.winfo_exists(): 
                 self.after(0, self._update_task_ui, task_to_cancel)
        self.update_status_bar()

    def _retry_task(self, task_id_to_retry):
        original_task_info = None
        task_to_rebuild_from = None
        if task_id_to_retry in self.active_downloads:
            task_to_rebuild_from = self.active_downloads[task_id_to_retry]
        if task_to_rebuild_from:
            original_task_info = task_to_rebuild_from
            self.log_message(f"تلاش مجدد برای وظیفه: {original_task_info.title}")
            self._remove_task_ui(original_task_info.task_id, remove_from_active=True) 
            new_task_id = f"task_{time.time_ns()}_{(original_task_info.info_dict.get('id','retryrandom') if original_task_info.info_dict else 'retryrandom')}"
            retried_task = DownloadTask(
                new_task_id,
                original_task_info.original_url, 
                original_task_info.ydl_opts.copy(), 
                original_task_info.download_type,
                title=f"[تلاش مجدد] {original_task_info.title.replace('[تلاش مجدد] ','')}" 
            )
            retried_task.retries = original_task_info.retries + 1 
            retried_task.info_dict = original_task_info.info_dict 
            self._add_task_to_queue(retried_task)
        else:
            self.log_message(f"عدم موفقیت در تلاش مجدد برای وظیفه {task_id_to_retry}. اطلاعات اصلی وظیفه یافت نشد یا وظیفه دیگر فعال نیست.")
            messagebox.showwarning("خطای تلاش مجدد", "اطلاعات وظیفه برای تلاش مجدد یافت نشد. لطفاً دوباره لینک را تحلیل کنید.", parent=self)

    def _remove_task_ui(self, task_id, remove_from_active=True):
        if remove_from_active: 
            with self.download_lock: 
                self.active_downloads.pop(task_id, None)
        for widget in list(self.downloads_scroll_frame.winfo_children()): 
            if hasattr(widget, '_task_id_ref') and widget._task_id_ref == task_id:
                widget.destroy()
                self.log_message(f"UI برای وظیفه {task_id} پاک شد.")
                break 
        self.update_status_bar()

    def load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    Path(loaded_settings.get("download_path", DEFAULT_SETTINGS["download_path"])).mkdir(parents=True, exist_ok=True)
                    return {**DEFAULT_SETTINGS, **loaded_settings} 
        except Exception as e: 
            self.log_message(f"خطا در بارگذاری تنظیمات: {e}. استفاده از تنظیمات پیش‌فرض.")
        Path(DEFAULT_SETTINGS["download_path"]).mkdir(parents=True, exist_ok=True) 
        return DEFAULT_SETTINGS.copy()

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            self.log_message("تنظیمات ذخیره شدند.")
        except Exception as e:
            messagebox.showerror("خطا", f"عدم موفقیت در ذخیره تنظیمات: {e}", parent=self)
            self.log_message(f"خطا در ذخیره تنظیمات: {e}")

    def _browse_download_path(self):
        path = filedialog.askdirectory(initialdir=self.settings["download_path"], parent=self.settings_window)
        if path: 
            self.settings_path_entry.delete(0, ctk.END)
            self.settings_path_entry.insert(0, path)

    def update_status_bar(self):
        active_processing_count = sum(1 for task in self.active_downloads.values() 
                                   if task.status in ["در حال دانلود", "در حال پردازش...", "در حال شروع..."] 
                                   and not task.paused and not task.globally_paused)
        queued_count = len(self.download_queue)
        status_text = f"فعال: {active_processing_count} | در صف: {queued_count} | حداکثر: {self.settings['max_concurrent_downloads']}"
        self.status_bar_label.configure(text=status_text)
        total_speed_bytes = 0
        for task in self.active_downloads.values():
            if task.status == "در حال دانلود" and not task.paused and not task.globally_paused:
                speed_match = re.match(r"([\d\.]+)\s*([KMGT]?B)/s", task.speed_str, re.IGNORECASE)
                if speed_match:
                    val = float(speed_match.group(1))
                    unit = speed_match.group(2).upper()
                    if unit == "KB": val *= 1024
                    elif unit == "MB": val *= 1024**2
                    elif unit == "GB": val *= 1024**3
                    elif unit == "TB": val *= 1024**4
                    total_speed_bytes += val
        self.speed_status_label.configure(text=f"سرعت کل: {humanize.naturalsize(total_speed_bytes, binary=True, gnu=True)}/s")

    def update_disk_space(self):
        try:
            download_dir = Path(self.settings["download_path"])
            download_dir.mkdir(parents=True, exist_ok=True) 
            usage = shutil.disk_usage(str(download_dir))
            self.disk_space_label.configure(text=f"فضای دیسک: {humanize.naturalsize(usage.free, binary=True, gnu=True)}")
        except FileNotFoundError: 
            self.disk_space_label.configure(text="فضای دیسک: مسیر نامعتبر")
        except Exception as e: 
            self.disk_space_label.configure(text="فضای دیسک: خطا")
            self.log_message(f"خطا در بررسی فضای دیسک: {e}")

    def update_disk_space_periodically(self):
        self.update_disk_space()
        self.after(30000, self.update_disk_space_periodically) 

    def log_message(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        print(log_entry.strip()) 
        if hasattr(self, 'log_textbox') and self.log_textbox.winfo_exists(): 
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert(ctk.END, log_entry)
            self.log_textbox.see(ctk.END) 
            self.log_textbox.configure(state="disabled")

    def _on_closing(self):
        if messagebox.askokcancel("خروج", "آیا می‌خواهید خارج شوید؟ دانلودهای فعال لغو خواهند شد.", parent=self):
            self.log_message("کاربر درخواست خروج از برنامه را داد.")
            active_task_ids = list(self.active_downloads.keys())
            if active_task_ids:
                 self.log_message(f"درحال تلاش برای لغو {len(active_task_ids)} وظیفه فعال...")
                 for task_id in active_task_ids: self._cancel_task(task_id) 
            self.after(500, self._really_destroy) 

    def _really_destroy(self):
        self.log_message("ذخیره تنظیمات قبل از خروج..."); self.save_settings()
        self.log_message("خروج از برنامه."); self.destroy()

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1) 
        except (ImportError, AttributeError, OSError):
            try:
                windll.user32.SetProcessDPIAware() 
            except Exception as e:
                print(f"هشدار: امکان تنظیم DPI awareness وجود ندارد: {e}") 
    app = AdvancedYoutubeDownloaderApp()
    app.mainloop()
