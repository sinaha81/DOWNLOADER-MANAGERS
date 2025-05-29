import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox, font as tkFont
import tkinter # For TclError
import threading
import yt_dlp
import requests
from PIL import Image, ImageTk
from io import BytesIO
import os
import json
from pathlib import Path
import humanize
import time
import re
import shutil
import sys
import pprint # For pretty printing debug data

# --- ثابت‌ها و تنظیمات ---
APP_NAME = "SINA Download Manager"
APP_VERSION = "2.2.0" # Version updated
SETTINGS_FILE = "downloader_settings_v4.json" # Incremented settings version

DEFAULT_SETTINGS = {
    "download_path": str(Path.home() / "Downloads" / "SinaDownloader"),
    "theme": "System",
    "max_concurrent_downloads": 3,
    "max_retries": 3,
    "default_download_type": "Video",
    "language": "fa",
    "cookies_file": "",
    "default_subtitle_langs": "en,fa",
    "embed_subtitles": True,
    "font_family": "Vazirmatn", # Default font
    "debug_mode": False, # Debug mode setting
}

# اطمینان از وجود پوشه دانلود پیش‌فرض
Path(DEFAULT_SETTINGS["download_path"]).mkdir(parents=True, exist_ok=True)

# Unicode symbols for icons (updated for a more modern look)
ICON_SETTINGS = "⚙️"  # تنظیمات
ICON_DOWNLOAD = "📥"  # دانلود
ICON_PAUSE = "⏸️"   # مکث
ICON_RESUME = "▶️"  # ادامه
ICON_CANCEL = "🚫"  # لغو
ICON_RETRY = "🔄"   # تلاش مجدد
ICON_CLEAR = "🗑️"   # پاک کردن
ICON_FOLDER = "📂"  # پوشه
ICON_ANALYZE = "🔎"  # تحلیل


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
        self.minsize(950, 700) # Slightly increased minsize for bigger fonts

        self.settings = self.load_settings()
        ctk.set_appearance_mode(self.settings.get("theme", "System"))
        ctk.set_default_color_theme("blue")

        self.font_family = self.settings.get("font_family", DEFAULT_SETTINGS["font_family"])
        self.debug_mode = self.settings.get("debug_mode", DEFAULT_SETTINGS["debug_mode"])
        self.available_fonts = ["Vazirmatn", "Tahoma", "Arial", "Calibri", "Segoe UI", "IranSans"] # Added IranSans as an option

        self._create_font_objects() # Create font objects based on loaded settings

        self.active_downloads = {}
        self.download_queue = []
        self.download_lock = threading.Lock()
        self.current_media_info = None
        self.thumbnail_image = None
        self.is_globally_paused = False
        self.available_subs_map = {}
        self.selected_subs_vars = {}

        self._create_widgets()
        self._layout_widgets()
        self.update_status_bar()
        self.update_disk_space_periodically()
        self._apply_current_font_to_all_widgets() # Apply font to already created widgets

        self.after(1000, self._process_download_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.log_message("برنامه با موفقیت راه‌اندازی شد.")

    def _create_font_objects(self):
        """ایجاد یا به‌روزرسانی اشیاء فونت برنامه بر اساس self.font_family."""
        default_size = 12
        title_size = 14
        treeview_size = 11
        task_title_size = 12
        task_status_size = 11
        icon_button_size = 20 # Increased for better icon visibility

        self.default_font = ctk.CTkFont(family=self.font_family, size=default_size)
        self.title_font = ctk.CTkFont(family=self.font_family, size=title_size, weight="bold")
        self.treeview_font_tuple = (self.font_family, treeview_size)
        self.treeview_heading_font_tuple = (self.font_family, treeview_size, "bold")
        self.task_title_font = ctk.CTkFont(family=self.font_family, size=task_title_size, weight="bold")
        self.task_status_font = ctk.CTkFont(family=self.font_family, size=task_status_size)
        self.icon_only_button_font = ctk.CTkFont(family=self.font_family, size=icon_button_size)


    def _apply_current_font_to_all_widgets(self):
        """اعمال فونت‌های فعلی به تمام ویجت‌های مربوطه در UI."""
        if not hasattr(self, 'url_label'): # Check if widgets are created
            return

        # Update fonts for existing widgets
        self.url_label.configure(font=self.default_font)
        self.url_entry.configure(font=self.default_font)
        self.analyze_button.configure(font=self.default_font)
        self.video_title_label.configure(font=self.default_font)
        self.download_type_label.configure(font=self.default_font)
        self.download_type_segmented_button.configure(font=self.default_font)
        self.quality_label.configure(font=self.title_font)
        self.subtitle_label.configure(font=self.title_font)
        self.embed_subs_checkbox.configure(font=self.default_font)
        self.download_button.configure(font=self.default_font)
        self.pause_all_button.configure(font=self.default_font)
        self.cancel_all_button.configure(font=self.default_font)
        self.log_textbox.configure(font=self.default_font)
        self.settings_button.configure(font=self.icon_only_button_font) # Special font for icon button
        self.status_bar_label.configure(font=self.default_font)
        self.speed_status_label.configure(font=self.default_font)
        self.disk_space_label.configure(font=self.default_font)

        # Update Treeview style
        self.tree_style.configure("Treeview", font=self.treeview_font_tuple, rowheight=int(self.default_font.cget("size") * 2.2)) # Adjust rowheight based on font
        self.tree_style.configure("Treeview.Heading", font=self.treeview_heading_font_tuple)

        # Update fonts for subtitle option checkboxes (if any)
        for widget in self.subtitle_options_frame.winfo_children():
            if isinstance(widget, ctk.CTkCheckBox) or isinstance(widget, ctk.CTkLabel):
                widget.configure(font=self.default_font)

        # Update fonts for dynamic task items
        for task in self.active_downloads.values():
            if task.frame and task.frame.winfo_exists():
                if task.title_label: task.title_label.configure(font=self.task_title_font)
                if task.status_label: task.status_label.configure(font=self.task_status_font)
                if task.pause_resume_button: task.pause_resume_button.configure(font=self.default_font) # Or icon_only_button_font if applicable
                if task.cancel_button: task.cancel_button.configure(font=self.default_font)
                if task.retry_clear_button: task.retry_clear_button.configure(font=self.default_font)
        
        # Update fonts in settings window if it's open
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            for child in self.settings_window.winfo_children():
                if isinstance(child, (ctk.CTkLabel, ctk.CTkButton, ctk.CTkEntry, ctk.CTkOptionMenu, ctk.CTkCheckBox)):
                    try:
                        if child == self.settings_window_save_button or child == self.settings_window_browse_path_button or child == self.settings_window_browse_cookies_button :
                             child.configure(font=self.default_font)
                        elif hasattr(child, '_text') and ICON_SETTINGS in child._text : # Heuristic for icon buttons
                             child.configure(font=self.icon_only_button_font)
                        else:
                             child.configure(font=self.default_font)
                    except Exception:
                        pass # Some widgets might not have font option or specific text

    def _apply_appearance_mode(self, color_tuple):
        if isinstance(color_tuple, (list, tuple)) and len(color_tuple) == 2:
            return color_tuple[1] if ctk.get_appearance_mode().lower() == "dark" else color_tuple[0]
        return color_tuple

    def _create_widgets(self):
        """ایجاد تمام ویجت‌های UI با استفاده از فونت‌های تعریف شده."""
        # --- Top Frame ---
        self.top_frame = ctk.CTkFrame(self)
        self.url_label = ctk.CTkLabel(self.top_frame, text="لینک (URL):", font=self.default_font)
        self.url_entry = ctk.CTkEntry(self.top_frame, placeholder_text="لینک ویدیو، پلی‌لیست یا سایت را وارد کنید", font=self.default_font, width=400)
        self.url_entry.bind("<<Paste>>", self._handle_paste_for_url_entry)
        self.analyze_button = ctk.CTkButton(self.top_frame, text=f"{ICON_ANALYZE} تحلیل لینک", command=self._analyze_url, font=self.default_font)

        # --- Main Content Frame ---
        self.main_content_frame = ctk.CTkFrame(self, fg_color="transparent")
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
        self._configure_treeview_style() # Helper to set style

        self.quality_tree = ttk.Treeview(self.quality_frame, columns=("res", "fps", "vcodec", "acodec", "size", "ext", "note"), show="headings", height=6, style="Treeview")
        self.quality_tree.heading("res", text="رزولوشن")
        self.quality_tree.heading("fps", text="فریم‌ریت")
        # ... (other headings)
        self.quality_tree.heading("vcodec", text="کدک ویدیو")
        self.quality_tree.heading("acodec", text="کدک صدا")
        self.quality_tree.heading("size", text="حجم تقریبی")
        self.quality_tree.heading("ext", text="فرمت")
        self.quality_tree.heading("note", text="توضیحات")
        for col_name in ("res", "fps", "vcodec", "acodec", "size", "ext", "note"):
            heading_text = self.quality_tree.heading(col_name)["text"]
            font_obj = tkFont.Font(family=self.treeview_heading_font_tuple[0], size=self.treeview_heading_font_tuple[1], weight=self.treeview_heading_font_tuple[2])
            col_width = font_obj.measure(heading_text) + 30 # Increased padding
            self.quality_tree.column(col_name, width=col_width, anchor="center", stretch=False if col_name != "note" else True)
        self.quality_tree.column("note", width=250, stretch=True)
        self.quality_tree.column("size", width=120, stretch=False)


        # --- Subtitle Frame ---
        self.subtitle_frame = ctk.CTkFrame(self.main_content_frame)
        self.subtitle_label = ctk.CTkLabel(self.subtitle_frame, text="انتخاب زیرنویس (اختیاری):", font=self.title_font)
        self.subtitle_options_frame = ctk.CTkScrollableFrame(self.subtitle_frame, height=100, fg_color="transparent") # Increased height
        self.embed_subs_var = ctk.BooleanVar(value=self.settings.get("embed_subtitles", True))
        self.embed_subs_checkbox = ctk.CTkCheckBox(self.subtitle_frame, text="ادغام زیرنویس در فایل ویدیو", variable=self.embed_subs_var, font=self.default_font)

        # --- Download Button ---
        self.download_button = ctk.CTkButton(self.main_content_frame, text=f"{ICON_DOWNLOAD} شروع دانلود", command=self._start_download, state="disabled", font=self.default_font, height=35) # Increased height

        # --- Global Controls ---
        self.global_controls_frame = ctk.CTkFrame(self)
        self.pause_all_button = ctk.CTkButton(self.global_controls_frame, text=f"{ICON_PAUSE} مکث همه", command=self._toggle_pause_all, font=self.default_font)
        self.cancel_all_button = ctk.CTkButton(self.global_controls_frame, text=f"{ICON_CANCEL} لغو همه", command=self._cancel_all_tasks, font=self.default_font, fg_color="#D32F2F", hover_color="#E57373") # More distinct red

        # --- TabView for Downloads and Logs ---
        self.bottom_tab_view = ctk.CTkTabview(self)
        self.bottom_tab_view.add("صف دانلود")
        self.bottom_tab_view.add("گزارش رویدادها")
        self.bottom_tab_view._segmented_button.configure(font=self.default_font) # Font for tab names
        for tab_name in ["صف دانلود", "گزارش رویدادها"]: # Font for tab names
            self.bottom_tab_view._segmented_button.configure(font=self.default_font)


        # --- Downloads Area (inside TabView) ---
        self.downloads_scroll_frame = ctk.CTkScrollableFrame(self.bottom_tab_view.tab("صف دانلود"), fg_color="transparent")

        # --- Log Area (inside TabView) ---
        self.log_textbox = ctk.CTkTextbox(self.bottom_tab_view.tab("گزارش رویدادها"), font=self.default_font, state="disabled", wrap="word")

        # --- Bottom Frame (Status Bar) ---
        self.status_bar_frame = ctk.CTkFrame(self)
        self.settings_button = ctk.CTkButton(self.status_bar_frame, text=ICON_SETTINGS, command=self._open_settings_window, font=self.icon_only_button_font, width=45, height=30) # Using icon font
        self.status_bar_label = ctk.CTkLabel(self.status_bar_frame, text="وضعیت: آماده", font=self.default_font, anchor="e")
        self.speed_status_label = ctk.CTkLabel(self.status_bar_frame, text="سرعت کل: 0 B/s", font=self.default_font, anchor="w")
        self.disk_space_label = ctk.CTkLabel(self.status_bar_frame, text="فضای دیسک: N/A", font=self.default_font, anchor="w")

    def _configure_treeview_style(self):
        """Helper function to configure Treeview style based on current theme and font."""
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

        self.tree_style.configure("Treeview", background=fg_color, foreground=text_color, fieldbackground=fg_color, font=self.treeview_font_tuple, rowheight=int(self.default_font.cget("size") * 2.2))
        self.tree_style.map("Treeview", background=[('selected', selected_color)], foreground=[('selected', text_color)])
        self.tree_style.configure("Treeview.Heading", font=self.treeview_heading_font_tuple, background=fg_color, foreground=text_color)


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
        self.main_content_frame.grid_rowconfigure(1, weight=0) # Subtitle frame should not expand excessively

        # Info Sub-Frame (Right Pane - Top)
        self.info_sub_frame.grid(row=0, column=1, padx=(5,0), pady=5, sticky="nsew")
        self.info_sub_frame.grid_columnconfigure(0, weight=1) # Allow title to expand
        self.info_sub_frame.grid_rowconfigure(1, weight=1) # Allow title label to take space
        self.thumbnail_label.pack(pady=5, padx=5, anchor="center")
        self.video_title_label.pack(fill="x", expand=True, pady=5, padx=5)
        self.download_type_label.pack(anchor="w", padx=5, pady=(10,0))
        self.download_type_segmented_button.pack(fill="x", pady=5, padx=5)

        # Quality Frame (Left Pane)
        self.quality_frame.grid(row=0, column=0, rowspan=2, padx=(0,5), pady=5, sticky="nsew")
        self.quality_frame.grid_rowconfigure(1, weight=1) # Treeview expands
        self.quality_frame.grid_columnconfigure(0, weight=1)
        self.quality_label.pack(side="top", anchor="w", padx=5, pady=(0,5))
        self.quality_tree.pack(side="top", fill="both", expand=True, padx=5, pady=5)


        # Subtitle Frame (Right Pane - Bottom)
        self.subtitle_frame.grid(row=1, column=1, padx=(5,0), pady=5, sticky="nsew")
        self.subtitle_frame.grid_columnconfigure(0, weight=1)
        self.subtitle_frame.grid_rowconfigure(1, weight=1) # Scrollable frame expands
        self.subtitle_label.pack(side="top", anchor="w", padx=5, pady=(5,0))
        self.subtitle_options_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        self.embed_subs_checkbox.pack(side="bottom", anchor="w", padx=5, pady=5)

        # Download button below quality and subtitle frames
        self.download_button.grid(row=2, column=0, columnspan=2, padx=10, pady=(5,10), sticky="ew")


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

    def _handle_paste_for_url_entry(self, event=None):
        try:
            clipboard_text = self.clipboard_get()
            self.url_entry.insert(ctk.INSERT, clipboard_text)
        except tkinter.TclError:
            self.log_message("کلیپ‌بورد خالی است یا حاوی اطلاعات غیرمتنی است.", level="warning")
        except Exception as e:
            self.log_message(f"خطا در عملیات پیست برای ورودی لینک: {e}", level="error")
        return "break"

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
            ydl_opts = {
                'extract_flat': 'discard_in_playlist', 
                'noplaylist': False, 
                'listsubtitles': True
            }
            if self.debug_mode:
                ydl_opts.update({'quiet': False, 'verbose': True, 'print_traffic': True, 'dump_intermediate_pages': True, 'logger': self.YTDLLogger(self)})
            else:
                ydl_opts.update({'quiet': True, 'verbose': False, 'logger': self.YTDLLogger(self)})


            if self.settings.get("cookies_file") and os.path.exists(self.settings["cookies_file"]):
                ydl_opts['cookiefile'] = self.settings["cookies_file"]
            
            self.log_message(f"yt-dlp options for fetching info: {ydl_opts}", level="debug")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.current_media_info = ydl.extract_info(url, download=False)
            
            if not self.current_media_info:
                 raise yt_dlp.utils.DownloadError("اطلاعاتی از لینک دریافت نشد.")
            
            self.log_message("اطلاعات لینک با موفقیت دریافت شد.", debug_data=self.current_media_info if self.debug_mode else None)

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
            self.log_message(f"خطا در تحلیل لینک {url}: {error_msg}", level="error")
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("خطای تحلیل", f"یک خطای غیرمنتظره رخ داد: {clean_ansi_codes(str(e))}", parent=self))
            self.after(0, self._reset_analysis_ui)
            self.log_message(f"خطای غیرمنتظره در تحلیل لینک {url}: {clean_ansi_codes(str(e))}", level="error", exc_info=True)


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
            note = clean_ansi_codes(f.get('format_note', ''))
            if f.get('acodec') == 'none' and is_video_type: note = "فقط ویدیو " + note
            elif f.get('vcodec') == 'none' and is_audio_type: note = "فقط صدا " + note
            elif is_video_type and is_audio_type: note = "ویدیو + صدا " + note
            processed_formats.append(((res, fps, vcodec, acodec, size_str, ext, note.strip()), f, format_id))
        
        if download_type_ui == "ویدیو":
            processed_formats.sort(key=lambda x: (x[1].get('height',0), x[1].get('vbr',0) or x[1].get('tbr',0) or 0, x[1].get('fps', 0)), reverse=True)
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
                self.log_message("خطا: نتوانست اولین آیتم را در جدول کیفیت انتخاب کند.", level="warning")


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
        
        # Sort subtitles by language code for consistent order
        sorted_subs = sorted(subs.items(), key=lambda item: item[0])

        for lang_code, sub_info_list in sorted_subs:
            if sub_info_list:
                lang_name = sub_info_list[0].get('name', lang_code)
                is_auto_caption = info.get('automatic_captions') and lang_code in info.get('automatic_captions')
                is_auto_text = '(خودکار)' if is_auto_caption else ''
                
                self.available_subs_map[lang_code] = lang_name
                var = ctk.BooleanVar()
                if lang_code.lower() in default_selected_langs:
                    var.set(True)
                
                cb_text = f"{lang_name} ({lang_code}) {is_auto_text}"
                cb = ctk.CTkCheckBox(self.subtitle_options_frame, text=cb_text, variable=var, font=self.default_font)
                cb.pack(anchor="w", padx=5, pady=2)
                self.selected_subs_vars[lang_code] = var
        if not self.available_subs_map:
             ctk.CTkLabel(self.subtitle_options_frame, text="زیرنویس یافت نشد.", font=self.default_font).pack(anchor="w", padx=5)


    def _on_download_type_change(self, *args):
        if self.current_media_info:
            if 'entries' in self.current_media_info and self.current_media_info.get('_type') == 'playlist':
                pass # For playlists, quality is handled per item or uses default
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
            video_url = entry.get('webpage_url') or entry.get('url')
            if not video_url and entry.get('id'):
                 video_url = f"https://www.youtube.com/watch?v={entry.get('id')}" # More reliable URL
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
            return name if name else "Untitled"

        base_path = self.settings["download_path"]
        # Ensure title template handles potential None values from sanitize_filename
        sane_title_template = '%(title).100B - %(id)s.%(ext)s' # .100B for bytes, safer for filenames

        if is_playlist_item:
            sane_playlist_title = sanitize_filename(playlist_title if playlist_title else "Playlist")
            # Use os.path.join for path construction
            download_path_template = os.path.join(base_path, sane_playlist_title[:50], f"%(playlist_index)02d - {sane_title_template}")
        else:
            download_path_template = os.path.join(base_path, sane_title_template)

        ydl_opts = {
            'outtmpl': download_path_template,
            'progress_hooks': [self._yt_dlp_progress_hook],
            'postprocessor_hooks': [self._yt_dlp_postprocessor_hook],
            'retries': self.settings["max_retries"],
            'continuedl': True, 
            'nopart': True, # Avoid .part files
            'ignoreerrors': True if is_playlist_item else False,
            'encoding': 'utf-8',
            'restrictfilenames': sys.platform == "win32", # Only restrict on Windows
            'logger': self.YTDLLogger(self), # Custom logger
            'noprogress': True, # We handle progress via hooks
        }
        
        if self.debug_mode:
            ydl_opts.update({'quiet': False, 'verbose': True, 'print_traffic': False, 'dump_intermediate_pages': False}) # Adjusted for less noise
        else:
            ydl_opts.update({'quiet': True, 'verbose': False})


        if self.settings.get("cookies_file") and os.path.exists(self.settings["cookies_file"]):
            ydl_opts['cookiefile'] = self.settings["cookies_file"]

        if download_type_internal == "Audio":
            ydl_opts['format'] = "bestaudio/best"
            if format_selector and not ("bestaudio" in format_selector or "/" in format_selector):
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
            if format_selector == "bestvideo*+bestaudio/best" or (is_playlist_item and format_selector == "bestvideo*+bestaudio/best"):
                ydl_opts['format'] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best" # Prefer mp4 containers
            elif '+' in format_selector or 'audio' in format_selector.lower():
                ydl_opts['format'] = format_selector
            else: # Assumed video-only stream ID or "bestvideo"
                ydl_opts['format'] = f"{format_selector}[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"


            effective_subtitle_langs_to_request = []
            if ui_selected_subtitle_langs:
                effective_subtitle_langs_to_request = ui_selected_subtitle_langs
            else:
                default_langs_str = self.settings.get("default_subtitle_langs", "")
                if default_langs_str:
                    effective_subtitle_langs_to_request = [lang.strip() for lang in default_langs_str.split(',') if lang.strip()]

            if effective_subtitle_langs_to_request:
                ydl_opts['writesubtitles'] = True
                ydl_opts['subtitleslangs'] = effective_subtitle_langs_to_request
                ydl_opts['subtitlesformat'] = 'srt/ass/vtt/best' # Common subtitle formats
                if self.embed_subs_var.get(): # Check app's embed checkbox state
                    ydl_opts['embedsubtitles'] = True
            
            # Set merge format based on whether subtitles are embedded or audio needs merging
            if ydl_opts.get('embedsubtitles') or '+' in ydl_opts.get('format', ''):
                ydl_opts.setdefault('merge_output_format', 'mkv') # MKV is good for embedded subs and merging
            else:
                ydl_opts.setdefault('merge_output_format', 'mp4') # Default to mp4 if no merging/embedding

        self.log_message(f"Final ydl_opts for download: {ydl_opts}", level="debug")
        return ydl_opts

    def _add_task_to_queue(self, task):
        with self.download_lock:
            self.download_queue.append(task)
        task_frame = ctk.CTkFrame(self.downloads_scroll_frame, corner_radius=5, border_width=1)
        task_frame.pack(fill="x", pady=5, padx=5)
        task.frame = task_frame
        task.frame._task_id_ref = task.task_id

        top_task_info_frame = ctk.CTkFrame(task_frame, fg_color="transparent")
        top_task_info_frame.pack(side="top", fill="x", padx=5, pady=(5,2))
        top_task_info_frame.grid_columnconfigure(0, weight=1)

        task.title_label = ctk.CTkLabel(top_task_info_frame, text=task.title, anchor="w", font=self.task_title_font)
        task.title_label.grid(row=0, column=0, sticky="ew", pady=(0,2))
        task.progress_bar = ctk.CTkProgressBar(top_task_info_frame, orientation="horizontal", height=12) # Slightly thicker
        task.progress_bar.set(0)
        task.progress_bar.grid(row=1, column=0, sticky="ew")

        bottom_task_info_frame = ctk.CTkFrame(task_frame, fg_color="transparent")
        bottom_task_info_frame.pack(side="top", fill="x", padx=5, pady=(2,5))
        bottom_task_info_frame.grid_columnconfigure(0, weight=1)

        task.status_label = ctk.CTkLabel(bottom_task_info_frame, text=f"وضعیت: {task.status}", anchor="w", font=self.task_status_font)
        task.status_label.grid(row=0, column=0, sticky="ew", padx=(0,5))

        action_button_frame = ctk.CTkFrame(bottom_task_info_frame, fg_color="transparent")
        action_button_frame.grid(row=0, column=1, sticky="e")
        task.action_button_frame = action_button_frame

        button_font = self.default_font # Use default font for buttons with text
        icon_font_for_buttons = self.icon_only_button_font # For icon-only style if needed
        
        task.pause_resume_button = ctk.CTkButton(action_button_frame, text=ICON_PAUSE, width=35, font=icon_font_for_buttons, # Using icon font
                                             command=lambda t=task: self._toggle_pause_task(t.task_id))
        task.pause_resume_button.pack(side="left", padx=(0,3))
        task.cancel_button = ctk.CTkButton(action_button_frame, text=ICON_CANCEL, width=35, font=icon_font_for_buttons, fg_color="#E65100", hover_color="#FF9800", # Orange
                                         command=lambda t=task: self._cancel_task(t.task_id))
        task.cancel_button.pack(side="left", padx=3)
        task.retry_clear_button = ctk.CTkButton(action_button_frame, text=" ", width=35, font=icon_font_for_buttons)
        task.retry_clear_button.pack(side="left", padx=(3,0))

        self._update_task_ui(task)
        self.update_status_bar()

    def _update_task_ui(self, task):
        if not (task and task.frame and task.frame.winfo_exists()): return

        if task.title_label: task.title_label.configure(text=task.title)
        if task.progress_bar: task.progress_bar.set(task.progress_float if task.progress_float is not None else 0)

        status_text = f"وضعیت: {clean_ansi_codes(task.status)}"
        if task.status == "در حال دانلود":
            status_text += f" - {clean_ansi_codes(task.progress_str)} ({clean_ansi_codes(task.speed_str)}, ETA: {clean_ansi_codes(task.eta_str)})"
        elif task.status == "خطا":
            status_text += f" - {clean_ansi_codes(task.error_message or 'خطای نامشخص')}"
        elif task.status == "تکمیل شد":
            status_text += f" - در: {os.path.basename(task.filepath) if task.filepath else 'N/A'}"

        if task.status_label: task.status_label.configure(text=status_text)
        
        icon_font_for_buttons = self.icon_only_button_font

        if task.pause_resume_button:
            task.pause_resume_button.configure(font=icon_font_for_buttons) # Ensure icon font
            if task.status in ["در حال دانلود", "در حال شروع..."]:
                task.pause_resume_button.configure(text=ICON_PAUSE, state="normal")
            elif task.status == "مکث شده" or task.status == "مکث شده (کلی)":
                task.pause_resume_button.configure(text=ICON_RESUME, state="normal")
            else: task.pause_resume_button.configure(text=ICON_PAUSE, state="disabled")

        if task.cancel_button:
            task.cancel_button.configure(font=icon_font_for_buttons) # Ensure icon font
            if task.status not in ["تکمیل شد", "لغو شده", "خطا", "ناموفق"]: task.cancel_button.configure(state="normal")
            else: task.cancel_button.configure(state="disabled")

        if task.retry_clear_button:
            task.retry_clear_button.configure(font=icon_font_for_buttons) # Ensure icon font
            if task.status == "خطا" and task.retries < self.settings["max_retries"]:
                task.retry_clear_button.configure(text=ICON_RETRY, state="normal", fg_color="#4CAF50", hover_color="#81C784", command=lambda t_id=task.task_id: self._retry_task(t_id)) # Green
            elif task.status in ["تکمیل شد", "لغو شده", "ناموفق"] or (task.status == "خطا" and task.retries >= self.settings["max_retries"]):
                task.retry_clear_button.configure(text=ICON_CLEAR, state="normal", fg_color="#757575", hover_color="#BDBDBD", command=lambda t_id=task.task_id: self._remove_task_ui(t_id)) # Gray
            else: task.retry_clear_button.configure(text=" ", state="disabled", command=None)

        self.update_status_bar()


    def _open_settings_window(self):
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.focus()
            return
        self.settings_window = ctk.CTkToplevel(self)
        self.settings_window.title("تنظیمات")
        self.settings_window.geometry("600x550") # Increased size for new options
        self.settings_window.transient(self)
        self.settings_window.grab_set()
        self.settings_window.attributes("-topmost", True)

        current_row = 0
        # Download Path
        ctk.CTkLabel(self.settings_window, text="مسیر دانلود:", font=self.default_font).grid(row=current_row, column=0, padx=10, pady=10, sticky="w")
        self.settings_path_entry = ctk.CTkEntry(self.settings_window, width=350, font=self.default_font)
        self.settings_path_entry.insert(0, self.settings["download_path"])
        self.settings_path_entry.grid(row=current_row, column=1, padx=10, pady=10, sticky="ew")
        self.settings_window_browse_path_button = ctk.CTkButton(self.settings_window, text=f"{ICON_FOLDER} انتخاب...", command=self._browse_download_path, font=self.default_font)
        self.settings_window_browse_path_button.grid(row=current_row, column=2, padx=10, pady=10)
        current_row += 1

        # Theme
        ctk.CTkLabel(self.settings_window, text="پوسته برنامه:", font=self.default_font).grid(row=current_row, column=0, padx=10, pady=10, sticky="w")
        self.settings_theme_var = ctk.StringVar(value=self.settings["theme"])
        theme_options = ctk.CTkOptionMenu(self.settings_window, variable=self.settings_theme_var, values=["System", "Dark", "Light"], font=self.default_font)
        theme_options.grid(row=current_row, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        current_row += 1
        
        # Font Family
        ctk.CTkLabel(self.settings_window, text="فونت برنامه:", font=self.default_font).grid(row=current_row, column=0, padx=10, pady=10, sticky="w")
        self.settings_font_family_var = ctk.StringVar(value=self.font_family)
        font_options_menu = ctk.CTkOptionMenu(self.settings_window, variable=self.settings_font_family_var, values=self.available_fonts, font=self.default_font)
        font_options_menu.grid(row=current_row, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        current_row += 1

        # Max Concurrent Downloads
        ctk.CTkLabel(self.settings_window, text="حداکثر دانلود همزمان:", font=self.default_font).grid(row=current_row, column=0, padx=10, pady=10, sticky="w")
        self.settings_max_downloads_var = ctk.StringVar(value=str(self.settings["max_concurrent_downloads"]))
        max_downloads_entry = ctk.CTkEntry(self.settings_window, textvariable=self.settings_max_downloads_var, width=50, font=self.default_font)
        max_downloads_entry.grid(row=current_row, column=1, padx=10, pady=10, sticky="w")
        current_row += 1
        
        # Default Download Type
        ctk.CTkLabel(self.settings_window, text="نوع دانلود پیش‌فرض:", font=self.default_font).grid(row=current_row, column=0, padx=10, pady=10, sticky="w")
        self.settings_default_type_var = ctk.StringVar(value=self.settings.get("default_download_type", "Video").replace("Video","ویدیو").replace("Audio","صوت"))
        default_type_options = ctk.CTkOptionMenu(self.settings_window, variable=self.settings_default_type_var, values=["ویدیو", "صوت"], font=self.default_font)
        default_type_options.grid(row=current_row, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        current_row += 1

        # Cookies File
        ctk.CTkLabel(self.settings_window, text="فایل کوکی (اختیاری):", font=self.default_font).grid(row=current_row, column=0, padx=10, pady=10, sticky="w")
        self.settings_cookies_entry = ctk.CTkEntry(self.settings_window, width=350, font=self.default_font)
        self.settings_cookies_entry.insert(0, self.settings.get("cookies_file", ""))
        self.settings_cookies_entry.grid(row=current_row, column=1, padx=10, pady=10, sticky="ew")
        self.settings_window_browse_cookies_button = ctk.CTkButton(self.settings_window, text=f"{ICON_FOLDER} انتخاب...", command=self._browse_cookies_file, font=self.default_font)
        self.settings_window_browse_cookies_button.grid(row=current_row, column=2, padx=10, pady=10)
        current_row += 1
        
        # Default Subtitle Languages
        ctk.CTkLabel(self.settings_window, text="زبان‌های پیش‌فرض زیرنویس (جدا با کاما):", font=self.default_font).grid(row=current_row, column=0, padx=10, pady=10, sticky="w")
        self.settings_subs_entry = ctk.CTkEntry(self.settings_window, width=150, font=self.default_font)
        self.settings_subs_entry.insert(0, self.settings.get("default_subtitle_langs", "en,fa"))
        self.settings_subs_entry.grid(row=current_row, column=1, padx=10, pady=10, sticky="w")
        self.settings_embed_subs_var = ctk.BooleanVar(value=self.settings.get("embed_subtitles", True))
        ctk.CTkCheckBox(self.settings_window, text="ادغام زیرنویس (پیش‌فرض کلی)", variable=self.settings_embed_subs_var, font=self.default_font).grid(row=current_row, column=2, padx=10, pady=10, sticky="w")
        current_row += 1

        # Debug Mode
        ctk.CTkLabel(self.settings_window, text="حالت اشکال‌زدایی:", font=self.default_font).grid(row=current_row, column=0, padx=10, pady=10, sticky="w")
        self.settings_debug_mode_var = ctk.BooleanVar(value=self.debug_mode)
        debug_mode_checkbox = ctk.CTkCheckBox(self.settings_window, text="فعال‌سازی لاگ‌های دقیق", variable=self.settings_debug_mode_var, font=self.default_font)
        debug_mode_checkbox.grid(row=current_row, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        current_row += 1

        # Save Button
        self.settings_window_save_button = ctk.CTkButton(self.settings_window, text="ذخیره تنظیمات", command=self._apply_settings, font=self.default_font, height=35)
        self.settings_window_save_button.grid(row=current_row, column=0, columnspan=3, padx=10, pady=20)
        
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
        # Download Path
        new_path = self.settings_path_entry.get()
        if not os.path.isdir(new_path):
            try:
                Path(new_path).mkdir(parents=True, exist_ok=True)
                self.settings["download_path"] = new_path
            except Exception as e:
                messagebox.showerror("خطا", f"مسیر دانلود نامعتبر: {new_path}\n{e}. لطفاً یک مسیر معتبر انتخاب کنید.", parent=self.settings_window)
                return
        else: self.settings["download_path"] = new_path

        # Theme
        new_theme = self.settings_theme_var.get()
        if new_theme != self.settings["theme"]:
            self.settings["theme"] = new_theme
            ctk.set_appearance_mode(new_theme)
            self._configure_treeview_style() # Re-apply style for theme change

        # Font Family
        new_font_family = self.settings_font_family_var.get()
        if new_font_family != self.font_family:
            self.font_family = new_font_family
            self.settings["font_family"] = new_font_family
            self._create_font_objects() # Recreate font objects
            self._apply_current_font_to_all_widgets() # Apply to all UI

        # Max Concurrent Downloads
        try:
            max_dls = int(self.settings_max_downloads_var.get())
            if 1 <= max_dls <= 10: self.settings["max_concurrent_downloads"] = max_dls
            else: raise ValueError("حداکثر دانلود همزمان باید بین 1 تا 10 باشد.")
        except ValueError as e:
            messagebox.showerror("خطا", str(e), parent=self.settings_window)
            return
        
        # Other settings
        self.settings["default_download_type"] = self.settings_default_type_var.get().replace("ویدیو","Video").replace("صوت","Audio")
        self.settings["cookies_file"] = self.settings_cookies_entry.get()
        self.settings["default_subtitle_langs"] = self.settings_subs_entry.get()
        self.settings["embed_subtitles"] = self.settings_embed_subs_var.get()
        
        # Debug Mode
        self.debug_mode = self.settings_debug_mode_var.get()
        self.settings["debug_mode"] = self.debug_mode

        self.save_settings()
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        self.log_message("تنظیمات اعمال شدند.")
        self.update_disk_space()
        self.embed_subs_var.set(self.settings.get("embed_subtitles", True)) # Update main window checkbox


    def _load_thumbnail(self, url):
        try:
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            image_data = BytesIO(response.content)
            pil_image = Image.open(image_data)
            pil_image.thumbnail((160, 90)) # Resize to fit label
            self.thumbnail_image = ImageTk.PhotoImage(pil_image)
            self.after(0, lambda: self.thumbnail_label.configure(image=self.thumbnail_image, text=""))
        except Exception as e:
            self.after(0, lambda: self.thumbnail_label.configure(image=None, text="خطای تصویر"))
            self.log_message(f"خطا در بارگذاری تصویر {url}: {e}", level="warning")

    def _process_download_queue(self):
        with self.download_lock:
            running_tasks_count = 0
            for task_iter in self.active_downloads.values():
                if task_iter.status == "در حال دانلود" and not task_iter.paused and not task_iter.globally_paused:
                    running_tasks_count +=1
            
            while running_tasks_count < self.settings["max_concurrent_downloads"] and self.download_queue:
                if not self.download_queue: break # Extra check
                task = self.download_queue.pop(0)
                if task.status == "لغو شده":
                    self._remove_task_ui(task.task_id, remove_from_active=False)
                    continue
                if self.is_globally_paused:
                    task.status = "مکث شده (کلی)"
                    task.globally_paused = True
                     # Re-add to front of queue if globally paused before start, or manage active_downloads
                    self.active_downloads[task.task_id] = task # Add to active to show in UI
                    self._update_task_ui(task)
                    # Don't start thread, will be picked up when unpaused
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
                # No need to call _finalize_task here, it will be handled by pause logic or queue processing
                self.after(0, self._update_task_ui, task) # Just update UI
                return

            # Ensure output directory exists
            if task.ydl_opts.get('outtmpl'):
                # Create a dummy info dict for path formatting if task.info_dict is not yet populated
                dummy_info_for_path = {
                    'title': task.title, 'id': 'temp_id', 'ext': 'mp4', 
                    'playlist_title': 'Playlist', 'playlist_index': '01',
                    **(task.info_dict or {}) # Merge with actual info_dict if available
                }
                # Sanitize parts of the dummy info that go into filenames
                for key in ['title', 'playlist_title']:
                    if key in dummy_info_for_path and isinstance(dummy_info_for_path[key], str):
                        dummy_info_for_path[key] = re.sub(r'[<>:"/\\|?*]', '_', dummy_info_for_path[key])


                try:
                    # Attempt to format the path template to get the directory
                    potential_filepath = task.ydl_opts['outtmpl'] % dummy_info_for_path
                    output_dir = os.path.dirname(potential_filepath)
                    if output_dir: # Ensure output_dir is not empty
                        Path(output_dir).mkdir(parents=True, exist_ok=True)
                except (TypeError, ValueError, KeyError) as path_e: # Catch errors during string formatting
                    self.log_message(f"خطا در فرمت‌بندی مسیر خروجی برای {task.title}: {path_e}. استفاده از مسیر دانلود پیش‌فرض.", level="warning")
                    # Fallback to a simpler path structure if formatting fails
                    sane_title = re.sub(r'[<>:"/\\|?*]', '_', task.title[:100])
                    task.ydl_opts['outtmpl'] = os.path.join(self.settings["download_path"], f"{sane_title}.%(ext)s")
                    Path(self.settings["download_path"]).mkdir(parents=True, exist_ok=True)


            with yt_dlp.YoutubeDL(task.ydl_opts) as ydl:
                ydl.download([task.url])
            
            # If download completes without error but status wasn't set by hooks (e.g. file already exists)
            if task.status not in ["تکمیل شد", "خطا", "لغو شده"]:
                # Try to determine filepath if not set by hooks
                if not task.filepath and 'outtmpl' in task.ydl_opts:
                    try:
                        # Re-evaluate filepath based on final info_dict if available
                        final_info = task.info_dict if task.info_dict else ydl.extract_info(task.url, download=False) # Potentially re-fetch if needed
                        if final_info:
                             task.filepath = ydl.prepare_filename(final_info, outtmpl=task.ydl_opts['outtmpl'])
                    except Exception as e_fp:
                        self.log_message(f"Could not determine final filepath for {task.title}: {e_fp}", level="warning")

                task.status = "تکمیل شد" # Assume success if no error
                task.progress_float = 1.0
                task.progress_str = "100%"
                self.log_message(f"دانلود '{task.title}' به نظر تکمیل شده (بدون خطای صریح).", level="info")


        except yt_dlp.utils.DownloadError as e:
            task.status = "خطا"; task.error_message = clean_ansi_codes(str(e))
            self.log_message(f"خطای DownloadError برای '{task.title}': {task.error_message}", level="error")
        except Exception as e:
            task.status = "خطا"; task.error_message = clean_ansi_codes(f"خطای غیرمنتظره: {str(e)}")
            self.log_message(f"خطای غیرمنتظره برای '{task.title}': {task.error_message}", level="error", exc_info=True)
        finally:
            # Finalize task status if it's still ambiguous
            if task.status not in ["تکمیل شد", "لغو شده", "خطا", "مکث شده", "مکث شده (کلی)"]:
                task.status = "ناموفق"
            self._finalize_task(task.task_id)

    def _yt_dlp_progress_hook(self, d):
        # self.log_message(f"Progress hook data for {d.get('info_dict',{}).get('title','Unknown')}", debug_data=d) # Log all hook data in debug
        task_id = self._find_task_for_hook(d)
        if not task_id: 
            self.log_message("Progress hook: Task ID not found for hook data.", level="debug", debug_data=d)
            return
        
        task = self.active_downloads.get(task_id)
        if not task: 
            self.log_message(f"Progress hook: Task object not found for ID {task_id}.", level="debug")
            return

        if task.globally_paused or task.paused:
            if task.status == "در حال دانلود":
                new_status = "مکث شده (کلی)" if task.globally_paused else "مکث شده"
                if task.status != new_status:
                    task.status = new_status
                    self.after(0, self._update_task_ui, task)
            return

        if d['status'] == 'downloading':
            task.status = "در حال دانلود"
            task.downloaded_bytes = d.get('downloaded_bytes', 0)
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
            if 'info_dict' in d and not task.info_dict: task.info_dict = d['info_dict'] # Store info_dict if available

        elif d['status'] == 'finished':
            task.status = "در حال پردازش..." # Might go to postprocessor hook
            task.progress_float = 1.0; task.progress_str = "100%"
            if 'filename' in d and d['filename'] != '-' : task.filepath = d.get('filename')
            if 'info_dict' in d and not task.info_dict: task.info_dict = d['info_dict']
            self.log_message(f"دانلود '{d.get('info_dict',{}).get('title','یک فایل')}' تمام شد، در انتظار پس‌پردازش...", level="info", debug_data=d if self.debug_mode else None)


        elif d['status'] == 'error':
            task.status = "خطا"; task.error_message = clean_ansi_codes(d.get('error', "خطای نامشخص yt-dlp در دانلود"))
            self.log_message(f"خطای yt-dlp برای '{task.title}': {task.error_message}", level="error", debug_data=d if self.debug_mode else None)
        
        self.after(0, self._update_task_ui, task)

    def _yt_dlp_postprocessor_hook(self, d):
        # self.log_message(f"Postprocessor hook data for {d.get('info_dict',{}).get('title','Unknown')}", debug_data=d)
        task_id = self._find_task_for_hook(d, from_info_dict=True)
        if not task_id: 
            self.log_message("Postprocessor hook: Task ID not found.", level="debug", debug_data=d)
            return

        task = self.active_downloads.get(task_id)
        if not task: 
            self.log_message(f"Postprocessor hook: Task object not found for ID {task_id}.", level="debug")
            return

        if d['status'] == 'finished':
            task.status = "تکمیل شد"
            task.progress_float = 1.0; task.progress_str = "100%"
            if 'info_dict' in d and 'filepath' in d['info_dict']:
                task.filepath = d['info_dict']['filepath']
            elif 'filepath' in d : # Sometimes filepath is directly in d for postprocessors
                 task.filepath = d['filepath']
            self.log_message(f"دانلود و پردازش موفق: {task.title} در {task.filepath or 'مسیر نامشخص'}", level="info", debug_data=d if self.debug_mode else None)
        elif d['status'] == 'error':
            task.status = "خطا"; task.error_message = clean_ansi_codes(f"خطای پس‌پردازش ({d.get('postprocessor')}): {d.get('error', 'نامشخص')}")
            self.log_message(f"خطای پس‌پردازش برای '{task.title}': {task.error_message}", level="error", debug_data=d if self.debug_mode else None)
        
        self.after(0, self._update_task_ui, task)

    def _find_task_for_hook(self, d, from_info_dict=False):
        # Try to find the task this hook belongs to. This can be tricky.
        info_dict = d.get('info_dict', {})
        hook_video_id = info_dict.get('id')
        # filename from hook might be temporary, use it cautiously
        hook_filename_direct = d.get('filename') if d.get('filename') != '-' else None
        hook_filepath_info_dict = info_dict.get('filepath') or info_dict.get('_filename')

        with self.download_lock:
            # Prioritize tasks that are actively downloading or processing
            candidate_tasks = [t for t in self.active_downloads.values() if t.status in ["در حال دانلود", "در حال پردازش...", "در حال شروع..."]]
            if not candidate_tasks:
                candidate_tasks = list(self.active_downloads.values()) # Fallback to any active task

            if not candidate_tasks: return None
            if len(candidate_tasks) == 1 and candidate_tasks[0].url == (info_dict.get('webpage_url') or info_dict.get('original_url')):
                 return candidate_tasks[0].task_id


            # Match by video ID if available in task's info_dict (might not be set early)
            if hook_video_id:
                for task in candidate_tasks:
                    if task.info_dict and task.info_dict.get('id') == hook_video_id:
                        return task.task_id
            
            # Match by original URL if info_dict has it
            hook_original_url = info_dict.get('webpage_url') or info_dict.get('original_url')
            if hook_original_url:
                for task in candidate_tasks:
                    if task.original_url == hook_original_url:
                        return task.task_id
            
            # Fallback: if only one task is in a state to receive hooks, assume it's that one
            # This is less reliable but can help in some cases.
            if len(candidate_tasks) == 1:
                return candidate_tasks[0].task_id
                
        self.log_message("Could not definitively match hook to a task.", level="debug", debug_data=d)
        return None


    def _finalize_task(self, task_id):
        task = None
        with self.download_lock:
            if task_id in self.active_downloads:
                # Don't pop here if it's just paused, allow it to be resumed from active_downloads
                task = self.active_downloads.get(task_id)
                if task and task.status not in ["مکث شده", "مکث شده (کلی)", "در حال دانلود", "در حال شروع...", "در حال پردازش..."]:
                    self.active_downloads.pop(task_id, None) # Remove if truly finished/failed
            else: # Task might have been removed if it was in queue and cancelled
                return


        if task:
            if task.status not in ["تکمیل شد", "لغو شده", "خطا", "ناموفق", "مکث شده", "مکث شده (کلی)"]:
                task.status = "پایان یافته (نامشخص)"
            self.after(0, self._update_task_ui, task)
            if task.status == "خطا" and task.retries >= self.settings["max_retries"]:
                 self.log_message(f"وظیفه '{task.title}' پس از حداکثر تلاش ناموفق بود.", level="error")
        self.update_status_bar()


    def _toggle_pause_all(self):
        self.is_globally_paused = not self.is_globally_paused
        action_icon = ICON_RESUME if self.is_globally_paused else ICON_PAUSE
        action_text = "ادامه" if self.is_globally_paused else "مکث"
        self.pause_all_button.configure(text=f"{action_icon} {action_text} همه")
        self.log_message(f"همه دانلودها {action_text} شدند.")

        with self.download_lock:
            # Update tasks in active_downloads
            for task in list(self.active_downloads.values()): # Iterate over a copy
                task.globally_paused = self.is_globally_paused
                if self.is_globally_paused:
                    if task.status == "در حال دانلود" or task.status == "در حال شروع...":
                        task.status = "مکث شده (کلی)"
                else: # Globally unpausing
                    if task.status == "مکث شده (کلی)" and not task.paused: # If not individually paused
                        # It should be re-queued or its download thread restarted.
                        # For simplicity, we'll mark it for the queue processor to pick up.
                        task.status = "در صف" # Mark to be picked by queue processor
                        # Move from active back to queue if it wasn't really "active"
                        if task.task_id in self.active_downloads: # Should be true
                            # self.download_queue.insert(0, self.active_downloads.pop(task.task_id)) # Re-queue
                             pass # Let queue processor handle it if it's already in active_downloads
                self.after(0, self._update_task_ui, task)

            # Update tasks in download_queue
            for task_in_q in self.download_queue:
                task_in_q.globally_paused = self.is_globally_paused
                if self.is_globally_paused:
                    if task_in_q.status == "در صف": task_in_q.status = "مکث شده (کلی)"
                else:
                    if task_in_q.status == "مکث شده (کلی)": task_in_q.status = "در صف"
                # UI for queued tasks is not typically updated until they become active,
                # but if they were shown as "globally paused" then made active, this is handled.

        if not self.is_globally_paused:
            self.after(200, self._process_download_queue) # Give a moment for UI updates


    def _cancel_all_tasks(self):
        if not messagebox.askyesno("لغو همه", "آیا مطمئن هستید که می‌خواهید همه دانلودها را لغو کنید؟", parent=self): return
        with self.download_lock:
            for task_id in list(self.active_downloads.keys()):
                task = self.active_downloads.get(task_id)
                if task:
                    task.status = "لغو شده"
                    # task.thread might need to be handled if yt-dlp doesn't exit cleanly on its own
                    self.log_message(f"وظیفه فعال لغو شد (علامت‌گذاری شده): {task.title}")
                    self.after(0, self._update_task_ui, task)
                    # Don't remove from active_downloads here, let finalize_task or UI clear do it.
            
            # Clear the queue and mark tasks as cancelled
            cleared_queue_tasks = []
            for task_in_q in self.download_queue:
                task_in_q.status = "لغو شده"
                self.log_message(f"وظیفه در صف لغو شد: {task_in_q.title}")
                # If these tasks had UI elements (they shouldn't if only in queue), update them.
                # For now, assume they don't until they are added via _add_task_to_queue
                cleared_queue_tasks.append(task_in_q) # Keep track to potentially remove their UI if it exists
            
            self.download_queue.clear() # Empty the queue

            # If queued tasks somehow had UI, remove it
            for task_obj in cleared_queue_tasks:
                if task_obj.frame and task_obj.frame.winfo_exists():
                    self._remove_task_ui(task_obj.task_id, remove_from_active=False)


        self.log_message("همه دانلودها برای لغو علامت‌گذاری شدند."); self.update_status_bar()


    def _toggle_pause_task(self, task_id):
        task = self.active_downloads.get(task_id)
        if not task: return
        
        task.paused = not task.paused
        
        if task.paused:
            task.status = "مکث شده"
            self.log_message(f"وظیفه '{task.title}' مکث شد.")
        else: # Resuming
            if task.globally_paused:
                task.status = "مکث شده (کلی)" # Still globally paused
                self.log_message(f"وظیفه '{task.title}' از مکث شخصی خارج شد اما همچنان مکث کلی فعال است.")
            else:
                task.status = "در حال دانلود" # Or "در صف" to be picked by queue
                self.log_message(f"وظیفه '{task.title}' ادامه یافت.")
                # If it was paused and is now unpaused (and not globally paused),
                # it might need to be re-added to the processing logic if its thread died.
                # For simplicity, the _process_download_queue should pick it up if status is 'در صف' or 'در حال دانلود'
                # and it's in active_downloads.
                # If its thread is still alive, yt-dlp should resume. If not, a new thread is needed.
                # This part can be complex. For now, assume yt-dlp handles resume or it gets re-processed.
                if task.status == "در حال دانلود" and (not task.thread or not task.thread.is_alive()):
                    self.log_message(f"Resuming task {task.title} by restarting its thread.", level="debug")
                    task.status = "در حال شروع..." # Reset status to re-trigger download execution
                    task.thread = threading.Thread(target=self._execute_download_task, args=(task,), daemon=True)
                    task.thread.start()


        self._update_task_ui(task)
        # if not task.paused and not task.globally_paused:
            # self.after(100, self._process_download_queue) # May trigger queue processing


    def _cancel_task(self, task_id):
        task_to_cancel = None
        was_in_active = False
        with self.download_lock:
            if task_id in self.active_downloads:
                task_to_cancel = self.active_downloads[task_id]
                was_in_active = True
            else:
                # Check queue
                for i, queued_task in enumerate(self.download_queue):
                    if queued_task.task_id == task_id:
                        task_to_cancel = self.download_queue.pop(i)
                        break
        
        if task_to_cancel:
            task_to_cancel.status = "لغو شده"
            self.log_message(f"وظیفه '{task_to_cancel.title}' لغو شد.")
            # If it was active, its thread might need to be signaled or yt-dlp instance closed.
            # yt-dlp should ideally handle SIGINT or similar, but direct thread killing is risky.
            # For now, rely on yt-dlp exiting on next IO or error.
            if was_in_active :
                 self._finalize_task(task_id) # This will update UI and potentially remove from active_downloads
            elif task_to_cancel.frame and task_to_cancel.frame.winfo_exists(): # If it was from queue but had UI
                 self._update_task_ui(task_to_cancel) # Update its UI to show "Cancelled"
                 # It will be cleared by retry/clear button or if app closes.
        self.update_status_bar()


    def _retry_task(self, task_id_to_retry):
        original_task_data = None # Store ydl_opts, url, type, title, original_url, info_dict

        # Find the task data, even if it's already removed from active_downloads but UI exists
        task_widget_found = False
        for widget in self.downloads_scroll_frame.winfo_children():
            if hasattr(widget, '_task_id_ref') and widget._task_id_ref == task_id_to_retry:
                # We have the widget, but need the task object's data.
                # This requires task objects to be stored even after completion/failure if retry is possible.
                # For now, let's assume if UI is there, we might find it in a temporary "completed/failed" list
                # or we need to reconstruct from limited info.
                # This part needs a more robust way to access original task parameters.
                
                # Simplification: Try to find it in active_downloads or a hypothetical completed_tasks list.
                # If not found, we can't reliably retry with all original parameters.
                task_obj_for_retry = self.active_downloads.get(task_id_to_retry)
                # In a more robust system, you'd have a list of all tasks (even completed/failed)
                # from which to retrieve this info.
                
                if task_obj_for_retry:
                    original_task_data = {
                        "url": task_obj_for_retry.original_url, # Use original_url for retry
                        "ydl_opts": task_obj_for_retry.ydl_opts.copy(), # Crucial: copy the opts
                        "download_type": task_obj_for_retry.download_type,
                        "title": task_obj_for_retry.title.replace("[تلاش مجدد] ", ""), # Clean title
                        "original_url": task_obj_for_retry.original_url,
                        "info_dict": task_obj_for_retry.info_dict.copy() if task_obj_for_retry.info_dict else None, # Copy info_dict
                        "previous_retries": task_obj_for_retry.retries
                    }
                task_widget_found = True
                break
        
        if not original_task_data:
            self.log_message(f"عدم موفقیت در تلاش مجدد برای وظیفه {task_id_to_retry}. اطلاعات اصلی وظیفه یافت نشد.", level="warning")
            messagebox.showwarning("خطای تلاش مجدد", "اطلاعات وظیفه برای تلاش مجدد یافت نشد. ممکن است نیاز به تحلیل مجدد لینک باشد.", parent=self)
            return

        self.log_message(f"تلاش مجدد برای وظیفه: {original_task_data['title']}")
        
        # Remove the old task UI and from active downloads if it's there
        self._remove_task_ui(task_id_to_retry, remove_from_active=True)

        new_task_id = f"task_{time.time_ns()}_{(original_task_data['info_dict'].get('id','retryrandom') if original_task_data['info_dict'] else 'retryrandom')}"
        
        # Modify ydl_opts for retry if needed (e.g., clear previous error flags, though yt-dlp usually handles this)
        # For example, ensure 'ignoreerrors' is appropriate for a retry.
        # original_task_data['ydl_opts']['ignoreerrors'] = False # Example: be less tolerant on retry

        retried_task = DownloadTask(
            new_task_id,
            original_task_data["url"], # This should be the primary URL to download from
            original_task_data["ydl_opts"],
            original_task_data["download_type"],
            title=f"[تلاش مجدد] {original_task_data['title']}",
            original_url=original_task_data["original_url"] # Preserve the initial URL entered by user
        )
        retried_task.retries = original_task_data["previous_retries"] + 1
        retried_task.info_dict = original_task_data["info_dict"]
        
        self._add_task_to_queue(retried_task)


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
                    # Ensure essential keys exist, falling back to defaults if not
                    for key, default_value in DEFAULT_SETTINGS.items():
                        if key not in loaded_settings:
                            loaded_settings[key] = default_value
                    
                    Path(loaded_settings.get("download_path", DEFAULT_SETTINGS["download_path"])).mkdir(parents=True, exist_ok=True)
                    return loaded_settings # No merge needed if all keys are ensured
            else: # Settings file does not exist, use defaults
                Path(DEFAULT_SETTINGS["download_path"]).mkdir(parents=True, exist_ok=True)
                return DEFAULT_SETTINGS.copy()

        except Exception as e:
            self.log_message(f"خطا در بارگذاری تنظیمات: {e}. استفاده از تنظیمات پیش‌فرض.", level="error", exc_info=True)
            Path(DEFAULT_SETTINGS["download_path"]).mkdir(parents=True, exist_ok=True)
        return DEFAULT_SETTINGS.copy()


    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            self.log_message("تنظیمات ذخیره شدند.")
        except Exception as e:
            messagebox.showerror("خطا", f"عدم موفقیت در ذخیره تنظیمات: {e}", parent=self)
            self.log_message(f"خطا در ذخیره تنظیمات: {e}", level="error", exc_info=True)

    def _browse_download_path(self):
        path = filedialog.askdirectory(initialdir=self.settings["download_path"], parent=self.settings_window if hasattr(self, 'settings_window') and self.settings_window.winfo_exists() else self)
        if path:
            self.settings_path_entry.delete(0, ctk.END)
            self.settings_path_entry.insert(0, path)

    def update_status_bar(self):
        active_processing_count = sum(1 for task in self.active_downloads.values()
                                   if task.status in ["در حال دانلود", "در حال پردازش...", "در حال شروع..."]
                                   and not task.paused and not task.globally_paused)
        queued_count = len(self.download_queue)
        status_text = f"فعال: {active_processing_count} | در صف: {queued_count} | حداکثر: {self.settings['max_concurrent_downloads']}"
        if hasattr(self, 'status_bar_label'): self.status_bar_label.configure(text=status_text)
        
        total_speed_bytes = 0
        for task in self.active_downloads.values():
            if task.status == "در حال دانلود" and not task.paused and not task.globally_paused:
                speed_match = re.match(r"([\d\.]+)\s*([KMGT]?B)/s", task.speed_str, re.IGNORECASE)
                if speed_match:
                    val = float(speed_match.group(1))
                    unit = speed_match.group(2).upper()
                    if unit == "KIB": val *= 1024 # yt-dlp often uses KiB, MiB
                    elif unit == "MIB": val *= 1024**2
                    elif unit == "GIB": val *= 1024**3
                    elif unit == "TIB": val *= 1024**4
                    elif unit == "KB": val *= 1000 # Less common from yt-dlp
                    elif unit == "MB": val *= 1000**2
                    elif unit == "GB": val *= 1000**3
                    elif unit == "TB": val *= 1000**4
                    elif unit == "B": pass # Already in bytes
                    total_speed_bytes += val
        if hasattr(self, 'speed_status_label'): self.speed_status_label.configure(text=f"سرعت کل: {humanize.naturalsize(total_speed_bytes, binary=True, gnu=True)}/s")


    def update_disk_space(self):
        try:
            download_dir = Path(self.settings["download_path"])
            if not download_dir.exists(): # If path was changed and doesn't exist yet
                download_dir.mkdir(parents=True, exist_ok=True)
            
            usage = shutil.disk_usage(str(download_dir))
            if hasattr(self, 'disk_space_label'): self.disk_space_label.configure(text=f"فضای دیسک: {humanize.naturalsize(usage.free, binary=True, gnu=True)}")
        except FileNotFoundError:
            if hasattr(self, 'disk_space_label'): self.disk_space_label.configure(text="فضای دیسک: مسیر نامعتبر")
        except Exception as e:
            if hasattr(self, 'disk_space_label'): self.disk_space_label.configure(text="فضای دیسک: خطا")
            self.log_message(f"خطا در بررسی فضای دیسک: {e}", level="warning")

    def update_disk_space_periodically(self):
        self.update_disk_space()
        self.after(30000, self.update_disk_space_periodically) # Check every 30 seconds

    class YTDLLogger: # Custom logger for yt-dlp
        def __init__(self, app_instance):
            self.app = app_instance

        def debug(self, msg):
            if "[debug]" not in msg.lower() and "youtube:search:" not in msg.lower(): # Filter out some common noisy debug messages
                 self.app.log_message(f"YT-DLP DEBUG: {msg}", level="debug")

        def info(self, msg):
             self.app.log_message(f"YT-DLP INFO: {msg}", level="info")

        def warning(self, msg):
            self.app.log_message(f"YT-DLP هشدار: {msg}", level="warning")

        def error(self, msg):
            self.app.log_message(f"YT-DLP خطا: {msg}", level="error")

    def log_message(self, message, level="info", debug_data=None, exc_info=False):
        """level can be 'info', 'warning', 'error', 'debug'."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Skip logging if it's a debug message and debug_mode is off
        if level == "debug" and not self.debug_mode:
            return

        log_entry = f"[{timestamp}] [{level.upper()}] {message}\n"
        
        if self.debug_mode and debug_data:
            try:
                debug_str = pprint.pformat(debug_data, indent=2, width=100) # Make it more readable
                log_entry += f"--- BEGIN DEBUG DATA ---\n{debug_str}\n--- END DEBUG DATA ---\n"
            except Exception as e:
                log_entry += f"Error formatting debug data: {e}\n"
        
        if exc_info: # Add traceback if requested (for errors)
            import traceback
            log_entry += traceback.format_exc() + "\n"

        print(log_entry.strip()) # Also print to console for live debugging
        
        if hasattr(self, 'log_textbox') and self.log_textbox.winfo_exists():
            # Correct way to manage CTkTextbox state for inserting text
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert(ctk.END, log_entry)
            self.log_textbox.see(ctk.END)
            self.log_textbox.configure(state="disabled") # Set back to disabled


    def _on_closing(self):
        if messagebox.askokcancel("خروج", "آیا می‌خواهید خارج شوید؟ دانلودهای فعال لغو خواهند شد.", parent=self):
            self.log_message("کاربر درخواست خروج از برنامه را داد.")
            active_task_ids = list(self.active_downloads.keys()) # Get IDs before modifying dict
            if active_task_ids:
                 self.log_message(f"درحال تلاش برای لغو {len(active_task_ids)} وظیفه فعال...")
                 for task_id in active_task_ids: self._cancel_task(task_id) # This will mark them as cancelled
            
            # Wait a bit for threads to potentially acknowledge cancellation if yt-dlp supports it well.
            # This is optimistic; yt-dlp threads might not terminate immediately.
            self.after(500, self._really_destroy)


    def _really_destroy(self):
        self.log_message("ذخیره تنظیمات قبل از خروج..."); self.save_settings()
        self.log_message("خروج از برنامه."); self.destroy()

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            from ctypes import windll
            # DPI Awareness: 0 for unaware, 1 for system aware, 2 for per-monitor aware
            # Per-monitor aware is best but might need more handling in Tkinter for font scaling.
            # System aware is a good compromise.
            windll.shcore.SetProcessDpiAwareness(1)
        except (ImportError, AttributeError, OSError): # Fallback for older Windows or if shcore fails
            try:
                windll.user32.SetProcessDPIAware()
            except Exception as e:
                print(f"هشدار: امکان تنظیم DPI awareness وجود ندارد: {e}")
    app = AdvancedYoutubeDownloaderApp()
    app.mainloop()
