
__appname__ = "Mullern Downloader"
__version__ = "1.0.0"
__author__ = "Samson Akach"
__email__="sammyryan100@gmail.com"
__license__ = "MIT"



import sys
import threading
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import QFrame
from PyQt6.QtGui import QIcon, QPainter, QPixmap, QColor
from PyQt6.QtCore import QTranslator, QLocale, QLibraryInfo, Qt, QTimer
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QProgressBar, QRadioButton, QComboBox,
    QMessageBox, QListWidgetItem, QStackedLayout
)
from yt_dlp import YoutubeDL

CONFIG_FILE = "config.json"
HISTORY_FILE = "history.json"

class DownloadPanel(QWidget):
    def __init__(self, title="Pending..."):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        
          # Create a title bar with an icon
        icon_label = QLabel()
        icon_label.setPixmap(QPixmap("resources/icons/icon.png").scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio))


        self.title_label = QLabel(title)
        self.size_label = QLabel("Size: ...")
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)

        layout.addWidget(self.title_label)
        layout.addWidget(self.size_label)
        layout.addWidget(self.progress)

        self.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 500;
            }
            QProgressBar {
                height: 18px;
                border-radius: 8px;
                background-color: #ddd;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 8px;
            }
        """)

    def update_progress(self, percent, size, speed, eta):
        self.size_label.setText(f"Size: {size}")
        self.progress.setFormat(f"{percent}% | ETA: {eta}s | {speed}")
        self.progress.setValue(percent)


class YTDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.app = app 

        self.translator = QTranslator()
        self.queue = []
        self.active_threads = []
        self.active_panels = []

        self.max_parallel_downloads = 2  # changeable later
        self.download_paused = False
        self.theme = "dark"
        self.history = []
        self.panel_map = {}  # url => DownloadPanel


        self.init_ui()
        lang, theme = self.load_config()
        self.lang_selector.setCurrentText(lang)
        self.theme = theme
        self.load_language(lang)
        self.load_history()
        self.apply_theme()
        self.update_status()

    def init_ui(self):
        self.setWindowTitle("Mullern-Downloader")
        self.setGeometry(100, 100, 900, 600)

        main_layout = QHBoxLayout(self)


        


        

        # Sidebar with shadow
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setObjectName("sidebar")  # for QSS
        self.sidebar_layout = QVBoxLayout(self.sidebar_widget)

        # Add icon buttons
        # In init_ui or wherever you define the buttons
        self.home_btn = QPushButton("  Home")
        self.home_btn.setIcon(QIcon("resources/icons/home.png"))
        self.home_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.sidebar_layout.addWidget(self.home_btn)

        self.history_btn = QPushButton("  History")
        self.history_btn.setIcon(QIcon("resources/icons/history.png"))
        self.history_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.sidebar_layout.addWidget(self.history_btn)

        self.theme_btn = QPushButton("  Toggle Theme")
        self.theme_btn.setIcon(QIcon("resources/icons/theme.png"))
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.sidebar_layout.addWidget(self.theme_btn)

        self.pause_btn = QPushButton("  Pause Queue")
        self.pause_btn.setIcon(QIcon("resources/icons/pause.png"))
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.sidebar_layout.addWidget(self.pause_btn)


        self.sidebar_layout.addStretch(1)
        main_layout.addWidget(self.sidebar_widget)

        # Modern QSS styles
        self.sidebar_widget.setStyleSheet("""
            #sidebar {
                background-color: #4CAF50;
                border-top-right-radius: 15px;
                border-bottom-right-radius: 15px;
                padding: 10px;
            }
            QPushButton {
                background-color: white;
                color: black;
                padding: 10px;
                margin-bottom: 10px;
                border-radius: 8px;
                text-align: left;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e8f5e9;
            }
        """)

        app.setStyleSheet("""
            QLabel {
                font-family: "Segoe UI", "Roboto", sans-serif;
                font-size: 14px;
                font-weight: 500;
                color: #333333;
                background-color: transparent;
                padding: 4px 8px;
                border-radius: 5px;
                letter-spacing: 0.5px;
            }
        """)





        self.stack = QStackedLayout()
        self.home_widget = QWidget()
        home_layout = QVBoxLayout(self.home_widget)

        self.downloads_container = QWidget()
        self.downloads_layout = QVBoxLayout(self.downloads_container)
        self.downloads_layout.setSpacing(10)
        self.downloads_layout.setContentsMargins(0, 10, 0, 0)

        home_layout.addWidget(self.downloads_container)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("🔗Paste YouTube URL here...")
        home_layout.addWidget(self.url_input)

        self.add_button = QPushButton("Add to Queue")
        self.add_button.clicked.connect(self.add_to_queue)
        home_layout.addWidget(self.add_button)


        self.queue_list = QListWidget()
        home_layout.addWidget(self.queue_list)

        format_layout = QHBoxLayout()
        self.video_radio = QRadioButton("🎥 Video + Audio")
        self.audio_radio = QRadioButton("🎵 Audio Only")
        self.video_radio.setChecked(True)
        format_layout.addWidget(self.video_radio)
        format_layout.addWidget(self.audio_radio)
        home_layout.addLayout(format_layout)

        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("🌍 Language:"))
        self.lang_selector = QComboBox()
        self.lang_selector.addItems(["English", "French", "Spanish", "Swahili"])
        self.lang_selector.currentTextChanged.connect(self.change_language)
        lang_layout.addWidget(self.lang_selector)
        home_layout.addLayout(lang_layout)

        self.download_button = QPushButton("⬇️ Start Download")
        self.download_button.setText(self.tr("⬇️ Start Download"))
        self.download_button.clicked.connect(self.start_download_queue)
        home_layout.addWidget(self.download_button)


        self.current_title_label = QLabel("Title: ")
        self.current_size_label = QLabel("Size: ")
        home_layout.addWidget(self.current_title_label)
        home_layout.addWidget(self.current_size_label)


        self.progress = QProgressBar()

        self.progress.setStyleSheet("""
                QProgressBar {
                    background-color: #ddd;
                    border-radius: 10px;
                    height: 20px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;
                    border-radius: 10px;
                }
            """)


        home_layout.addWidget(self.progress)

        self.status_label = QLabel()
        home_layout.addWidget(self.status_label)

        self.stack.addWidget(self.home_widget)

        self.history_widget = QWidget()
        history_layout = QVBoxLayout(self.history_widget)

        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)

        clear_btn = QPushButton("🗑️ Clear History")
        clear_btn.clicked.connect(self.clear_history)
        history_layout.addWidget(clear_btn)

        self.stack.addWidget(self.history_widget)
        main_layout.addLayout(self.stack)

        parallel_layout = QHBoxLayout()
        parallel_layout.addWidget(QLabel("⚙️ Parallel Downloads:"))
        self.parallel_selector = QComboBox()
        self.parallel_selector.addItems([str(i) for i in range(1, 6)])
        self.parallel_selector.setCurrentIndex(self.max_parallel_downloads - 1)
        self.parallel_selector.currentIndexChanged.connect(self.update_parallel_setting)
        parallel_layout.addWidget(self.parallel_selector)
        home_layout.addLayout(parallel_layout)



        info_frame = QFrame()
        info_layout = QVBoxLayout(info_frame)
        info_layout.addWidget(self.current_title_label)
        info_layout.addWidget(self.current_size_label)
        info_frame.setFrameShape(QFrame.Shape.Box)
        info_frame.setStyleSheet("background-color: green; padding: 5px;")
        home_layout.addWidget(info_frame)
    
    def update_parallel_setting(self, index):
        self.max_parallel_downloads = index + 1


    def retranslate_ui(self):
        self.setWindowTitle(self.tr("Mullern-Downloader"))

        # Sidebar buttons
        self.home_btn.setText(self.tr("  Home"))
        self.history_btn.setText(self.tr("  History"))
        self.theme_btn.setText(self.tr("  Toggle Theme"))
        self.pause_btn.setText(self.tr("  Pause Queue"))

        # Main page elements
        self.url_input.setPlaceholderText(self.tr("🔗Paste YouTube URL here..."))
        self.add_button.setText(self.tr("Load Link"))
        self.download_button.setText(self.tr("⬇️ Start Download"))
        self.video_radio.setText(self.tr("🎥 Video + Audio"))
        self.audio_radio.setText(self.tr("🎵 Audio Only"))
        self.current_title_label.setText(self.tr("Title:"))
        self.current_size_label.setText(self.tr("Size:"))
        self.status_label.setText(self.tr(""))

        # Language dropdown items (if visible to user)
        self.lang_selector.setItemText(0, self.tr("English"))
        self.lang_selector.setItemText(1, self.tr("French"))
        self.lang_selector.setItemText(2, self.tr("Spanish"))
        self.lang_selector.setItemText(3, self.tr("Swahili"))





    def update_status(self):
        total = len(self.queue)
        running = sum(1 for t in self.active_threads if t.is_alive())
        self.status_label.setText(f"{total} in queue | {running} downloading")

    def make_hook(self, panel):
        def hook(d):
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', '0.0%').strip().replace('%', '')
                eta = d.get('eta', 0)
                speed = d.get('_speed_str', '0.0KiB/s')
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                size = f"{total_bytes / (1024 * 1024):.2f} MB" if total_bytes else "Unknown"

                try:
                    panel.update_progress(int(float(percent)), size, speed, eta)
                except Exception as e:
                    print(f"[hook error] {e}")
            elif d['status'] == 'finished':
                panel.progress.setFormat("Download complete!")
                panel.progress.setValue(100)
        return hook



    def add_to_queue(self):
        url = self.url_input.text().strip()
        if url:
            self.queue.append(url)
            self.queue_list.addItem(url)
            self.url_input.clear()
            self.update_status()

    def toggle_pause(self):
        self.download_paused = not self.download_paused
        self.pause_btn.setText("Resume Queue" if self.download_paused else "Pause Queue")

    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        self.apply_theme()
        self.save_config()

    def apply_theme(self):
        if self.theme == "dark":
            self.setStyleSheet("""
                QWidget { background-color: #2e2e2e; color: white; }
                QPushButton { background-color: #444; color: white; padding: 6px; }
                QLineEdit, QListWidget, QComboBox { background-color: #555; color: white; }
            """)
        else:
            self.setStyleSheet("""
                QWidget { background-color: #f0f0f0; color: black; }
                QPushButton { background-color: #ddd; color: black; padding: 6px; }
                QLineEdit, QListWidget, QComboBox { background-color: white; color: black; }
            """)

        # Sidebar theme
        self.sidebar_widget.setStyleSheet("""
            #sidebar {
                background-color: #4CAF50;
                border-top-right-radius: 15px;
                border-bottom-right-radius: 15px;
                padding: 10px;
            }
            QPushButton {
                background-color: white;
                color: black;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)

    def start_download_queue(self):
        print("Start Download pressed!")  # Debug line
        for _ in range(min(self.max_parallel_downloads, len(self.queue))):
            self.try_start_next()


    def try_start_next(self):
        if self.download_paused or not self.queue:
            return

        # 🧠 FIRST: extract the URL from the queue
        url = self.queue.pop(0)
        self.queue_list.takeItem(0)
        self.update_status()

        # 🧩 THEN: create the panel
        panel = DownloadPanel()
        self.downloads_layout.addWidget(panel)
        self.active_panels.append(panel)

        # 🪝 Create the hook
        hook = self.make_hook(panel)

        if self.audio_radio.isChecked():
            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': '%(title)s.%(ext)s',
                'progress_hooks': [hook],
                'noplaylist': True,
                'quiet': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        else:
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': '%(title)s.%(ext)s',
                'progress_hooks': [hook],
                'noplaylist': True,
                'merge_output_format': 'mp4',
                'quiet': True,
            }

        # 🧵 Start download thread
        thread = threading.Thread(target=self.download_thread, args=(url, ydl_opts))
        thread.start()
        self.active_threads.append(thread)


      

        

    def download_thread(self, url, ydl_opts, panel):
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                self.save_to_history(info.get('title', 'Unknown'), 'audio' if self.audio_radio.isChecked() else 'video')
        except Exception as e:
            self.show_error(str(e))
        finally:
            QTimer.singleShot(0, self.try_start_next)


    def hook(self, d):
        if d['status'] == 'downloading':
            title = d.get('info_dict', {}).get('title', 'Unknown')
            total_bytes = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            size_mb = f"{total_bytes / (1024 * 1024):.2f} MB" if total_bytes else "Unknown size"
            
            percent_str = d.get('_percent_str', '0.0%').strip()
            eta = d.get('eta', 0)
            speed = d.get('_speed_str', '0.0KiB/s')

            try:
                percent = int(float(percent_str.replace('%', '').strip()))
            except:
                percent = 0

        def update_ui():
            self.current_title_label.setText(f"Title: {title}")
            self.current_size_label.setText(f"Size: {size_mb}")
            self.progress.setValue(percent)
            self.progress.setFormat(f"{percent_str} | ETA: {eta}s | {speed}")
            self.progress.setStyleSheet("""
                QProgressBar {
                    background-color: #ddd;
                    border-radius: 10px;
                    height: 20px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;
                    border-radius: 10px;
                }
            """)

        # Ensure UI update runs on the main thread
        QTimer.singleShot(0, update_ui)
    




    def save_to_history(self, title, format_):
        entry = {
            'title': title,
            'format': format_,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.history.append(entry)
        self.update_history_list()
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.history, f, indent=2)

    def load_history(self):
        try:
            if os.path.exists(HISTORY_FILE) and os.path.getsize(HISTORY_FILE) > 0:
                with open(HISTORY_FILE, "r") as f:
                    self.history = json.load(f)
            else:
                self.history = []
        except json.JSONDecodeError:
            self.history = []

    def update_history_list(self):
        self.history_list.clear()
        for item in self.history:
            self.history_list.addItem(f"{item['time']} - {item['title']} ({item['format']})")

    def clear_history(self):
        self.history = []
        self.history_list.clear()
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def load_language(self, lang_name):
        lang_codes = {
            "English": "en",
            "French": "fr",
            "Spanish": "es",
            "Swahili": "sw"
        }
        code = lang_codes.get(lang_name, "en")
        qm_path = f"translations/yt_downloader_{code}.qm"

        # Remove any previous translator before installing new one
        self.app.removeTranslator(self.translator)
        if self.translator.load(qm_path):
            self.app.installTranslator(self.translator)
            self.retranslate_ui()


    def change_language(self, lang_name):
        self.load_language(lang_name)
        self.save_config()
        self.retranslate_ui()


    def save_config(self):
        config = {
            "language": self.lang_selector.currentText(),
            "theme": self.theme
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                try:
                    config = json.load(f)
                    return config.get("language", "English"), config.get("theme", "light")
                except json.JSONDecodeError:
                    return "English", "light"
        return "English", "light"



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YTDownloader()
    window.show()
    sys.exit(app.exec())
