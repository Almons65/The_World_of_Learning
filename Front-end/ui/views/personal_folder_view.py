from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QGridLayout, QFileDialog, QProgressDialog, QMessageBox,
    QGraphicsDropShadowEffect, QProgressBar, QDialog, QAbstractButton, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QSettings, QRunnable, QObject, QThreadPool, QTimer, QPropertyAnimation, QRect, QEasingCurve, QPoint
from PySide6.QtGui import QFont, QColor, QPainter, QPainterPath, QPixmap, QPen, QLinearGradient

# ── Premium Progress Dialog ───────────────────────────────────────────────────
class PremiumProgressDialog(QDialog):
    def __init__(self, title="Downloading", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 180)
        
        self._container = QFrame(self)
        self._container.setGeometry(10, 10, 380, 160)
        self._container.setStyleSheet("""
            QFrame {
                background: #1c1b1b;
                border: 1px solid #353534;
                border-radius: 12px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 180))
        self._container.setGraphicsEffect(shadow)
        
        lay = QVBoxLayout(self._container)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)
        
        # Title & Percent row
        top_row = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: bold; background: transparent;")
        top_row.addWidget(self.lbl_title)
        
        top_row.addStretch()
        
        self.lbl_pct = QLabel("0%")
        self.lbl_pct.setStyleSheet("color: #f26411; font-size: 14px; font-weight: 900; background: transparent;")
        top_row.addWidget(self.lbl_pct)
        lay.addLayout(top_row)
        
        # Progress Bar
        self.bar = QProgressBar()
        self.bar.setFixedHeight(6)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet("""
            QProgressBar {
                background: #131313;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f26411, stop:1 #ff7326);
                border-radius: 3px;
            }
        """)
        lay.addWidget(self.bar)
        
        self.lbl_status = QLabel("Initializing...")
        self.lbl_status.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 11px; background: transparent;")
        lay.addWidget(self.lbl_status)
        
        lay.addStretch()
        
        # Cancel Button
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()
        self.btn_cancel = QPushButton("CANCEL")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255,255,255,0.3);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                color: #ff4444;
                border-color: #ff4444;
            }
        """)
        btn_lay.addWidget(self.btn_cancel)
        lay.addLayout(btn_lay)
        
        self._canceled = False
        self.btn_cancel.clicked.connect(self._do_cancel)
        
    def _do_cancel(self):
        self._canceled = True
        self.reject()
        
    def wasCanceled(self):
        return self._canceled
        
    def setValue(self, val):
        self.bar.setValue(val)
        self.lbl_pct.setText(f"{val}%")
        
    def setLabelText(self, txt):
        self.lbl_status.setText(txt)

# ── Toast Notification ───────────────────────────────────────────────────────
class ToastNotification(QFrame):
    def __init__(self, text, is_error=False, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        bg_col = "rgba(28, 27, 27, 0.95)"
        accent = "#f26411" if not is_error else "#ff4444"
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {bg_col};
                border: 1px solid {accent};
                border-radius: 25px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 200))
        self.setGraphicsEffect(shadow)
        
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 25, 0)
        lay.setSpacing(12)
        
        icon_lbl = QLabel("✓" if not is_error else "✕")
        icon_lbl.setStyleSheet(f"color: {accent}; font-size: 18px; font-weight: 900; background: transparent;")
        lay.addWidget(icon_lbl)
        
        self.lbl = QLabel(text)
        self.lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 600; background: transparent;")
        lay.addWidget(self.lbl)
        
        # Adjust size to text
        self.lbl.adjustSize()
        width = self.lbl.sizeHint().width() + 80
        self.setFixedSize(max(240, min(width, 600)), 50)
        
    @staticmethod
    def show_toast(text, is_error=False, parent=None):
        toast = ToastNotification(text, is_error, parent)
        if parent:
            # Position at top center
            px = (parent.width() - toast.width()) // 2
            py = 30
            toast.move(px, -60) # Start above
            
            # Slide down animation
            toast._anim = QPropertyAnimation(toast, b"pos")
            toast._anim.setDuration(600)
            toast._anim.setStartValue(QPoint(px, -60))
            toast._anim.setEndValue(QPoint(px, py))
            toast._anim.setEasingCurve(QEasingCurve.OutBack)
            toast._anim.start()
        
        toast.show()
        QTimer.singleShot(4000, lambda: toast._fade_out())
        return toast

    def _fade_out(self):
        self._fader = QPropertyAnimation(self, b"windowOpacity")
        self._fader.setDuration(500)
        self._fader.setStartValue(1.0)
        self._fader.setEndValue(0.0)
        
        self._mover = QPropertyAnimation(self, b"pos")
        self._mover.setDuration(500)
        self._mover.setStartValue(self.pos())
        self._mover.setEndValue(QPoint(self.x(), self.y() - 20))
        self._mover.setEasingCurve(QEasingCurve.InBack)
        
        self._mover.finished.connect(self.close)
        self._fader.start()
        self._mover.start()

from ui.folder_store import get_user_folders, save_user_folders
from ui.views.personal_hub_view import HubVideoCard
from image_cache import load_image
from api_client import client, API_BASE_URL
import requests


class _DownloadSignals(QObject):
    done = Signal(str)   # save path
    error = Signal(str)
    progress = Signal(int, int)  # downloaded, total

class _DownloadWorker(QRunnable):
    def __init__(self, stream_url: str, save_path: str):
        super().__init__()
        self.stream_url = stream_url
        self.save_path = save_path
        self.signals = _DownloadSignals()

    def run(self):
        try:
            with requests.get(self.stream_url, stream=True, timeout=60) as r:
                total = int(r.headers.get('content-length', 0))
                downloaded = 0
                with open(self.save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            self.signals.progress.emit(downloaded, total)
            self.signals.done.emit(self.save_path)
        except Exception as e:
            self.signals.error.emit(str(e))


class FolderVideoCard(HubVideoCard):
    removed = Signal(dict)
    download_requested = Signal(dict)

    def __init__(self, vd: dict, parent=None):
        super().__init__(vd, parent)

        # Remove button (top-right)
        self._remove_btn = QPushButton("✕", self)
        self._remove_btn.setFixedSize(24, 24)
        self._remove_btn.move(208, 8)
        self._remove_btn.setCursor(Qt.PointingHandCursor)
        self._remove_btn.setStyleSheet(
            "QPushButton{background:rgba(200,0,0,0.8);color:white;border:none;"
            "border-radius:12px;font-size:12px;font-weight:bold;}"
            "QPushButton:hover{background:red;}"
        )
        self._remove_btn.hide()
        self._remove_btn.clicked.connect(lambda: self.removed.emit(vd))

        # Download button — custom painted icon, no emoji
        from PySide6.QtWidgets import QAbstractButton
        from PySide6.QtGui import QPainter as _P, QPen as _Pen, QPainterPath as _Path

        class DownloadIconBtn(QAbstractButton):
            def __init__(self, parent=None):
                super().__init__(parent)
                self._hov = False
                self.setFixedSize(24, 24)
                self.setCursor(Qt.PointingHandCursor)
                self.setToolTip("Download video")
            def enterEvent(self, e): self._hov = True; self.update()
            def leaveEvent(self, e): self._hov = False; self.update()
            def paintEvent(self, ev):
                p = _P(self)
                p.setRenderHint(_P.Antialiasing)
                p.setBrush(QColor(0, 180, 90) if self._hov else QColor(0, 130, 65))
                p.setPen(Qt.NoPen)
                p.drawEllipse(0, 0, 24, 24)
                pen = _Pen(QColor(255, 255, 255), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                p.setPen(pen)
                p.drawLine(12, 5, 12, 15)   # stem
                path = _Path()
                path.moveTo(7, 12); path.lineTo(12, 17); path.lineTo(17, 12)
                p.drawPath(path)             # arrowhead
                p.drawLine(7, 19, 17, 19)   # base line
                p.end()

        self._dl_btn = DownloadIconBtn(self)
        self._dl_btn.move(178, 8)
        self._dl_btn.hide()
        self._dl_btn.clicked.connect(lambda: self.download_requested.emit(vd))


    def enterEvent(self, e):
        super().enterEvent(e)
        self._remove_btn.raise_()
        self._dl_btn.raise_()
        self._remove_btn.show()
        self._dl_btn.show()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self._remove_btn.hide()
        self._dl_btn.hide()


class PersonalFolderView(QWidget):
    video_selected = Signal(dict)
    back_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#0e0e0e;")
        self._username = ""
        self._folder_id = None
        self._folder_data = None
        self._dl_prog = None
        self._dl_worker = None
        self._dl_save_path = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Hero ──────────────────────────────────────────────────────────
# ── Folder Hero Section ───────────────────────────────────────────────────────
class FolderHero(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(460)
        self._pm = None
        self._color = "#f26411"
        self._setup_ui()

    def _setup_ui(self):
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(48, 48, 48, 48)
        self.lay.setAlignment(Qt.AlignBottom)

    def set_data(self, pm, color):
        self._pm = pm
        self._color = color
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        
        if self._pm and not self._pm.isNull():
            p.drawPixmap(r, self._pm.scaled(r.width(), r.height(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            # Overlay to make text readable
            p.fillRect(r, QColor(14, 14, 14, 160))
        else:
            grad = QLinearGradient(0, 0, 0, r.height())
            grad.setColorAt(0, QColor(self._color))
            grad.setColorAt(1, QColor("#0e0e0e"))
            p.fillRect(r, grad)
        
        # Bottom fade to blend with content
        g = QLinearGradient(0, r.height()*0.7, 0, r.height())
        g.setColorAt(0, QColor(14, 14, 14, 0))
        g.setColorAt(1, QColor(14, 14, 14, 255))
        p.fillRect(r, g)
        p.end()

class PersonalFolderView(QWidget):
    video_selected = Signal(dict)
    back_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#0e0e0e;")
        self._username = ""
        self._folder_id = None
        self._folder_data = None
        self._dl_prog = None
        self._dl_worker = None
        self._dl_save_path = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Hero ──────────────────────────────────────────────────────────
        self._hero = FolderHero()
        self._hero_lay = self._hero.lay

        top_bar = QHBoxLayout()
        self._back_btn = QPushButton("← BACK")
        self._back_btn.setCursor(Qt.PointingHandCursor)
        self._back_btn.setStyleSheet("background:rgba(255,255,255,0.1);color:#fff;border-radius:6px;padding:8px 16px;font-weight:bold;")
        self._back_btn.clicked.connect(lambda: self.back_clicked.emit())
        top_bar.addWidget(self._back_btn)
        top_bar.addStretch()
        
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search in folder...")
        self._search_input.setFixedWidth(250)
        self._search_input.setStyleSheet("QLineEdit{background:rgba(0,0,0,0.5);color:#fff;border:1px solid rgba(255,255,255,0.2);border-radius:6px;padding:8px 12px;font-weight:bold;} QLineEdit:focus{border-color:#f26411;}")
        self._search_input.textChanged.connect(self._render_grid)
        top_bar.addWidget(self._search_input)
        
        top_bar.addStretch()
        
        self._edit_bg_btn = QPushButton("EDIT BACKGROUND")
        self._edit_bg_btn.setCursor(Qt.PointingHandCursor)
        self._edit_bg_btn.setStyleSheet("background:rgba(255,255,255,0.1);color:#fff;border-radius:6px;padding:8px 16px;font-weight:bold;")
        self._edit_bg_btn.clicked.connect(self._on_edit_bg)
        top_bar.addWidget(self._edit_bg_btn)
        
        self._clear_btn = QPushButton("CLEAR ALL")
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setStyleSheet("background:rgba(200,0,0,0.4);color:#fff;border-radius:6px;padding:8px 16px;font-weight:bold;")
        self._clear_btn.clicked.connect(self._on_clear_all)
        top_bar.addWidget(self._clear_btn)

        self._hero_lay.addLayout(top_bar)
        
        self._title = QLabel("FOLDER")
        self._title.setStyleSheet("color:#ffffff;font-size:72px;font-weight:900;letter-spacing:-2px;background:transparent;")
        self._hero_lay.addWidget(self._title)

        self._subtitle = QLabel("COLLECTION OF 0 ARCHIVED VIDEOS")
        self._subtitle.setStyleSheet("color:rgba(255,255,255,0.6);font-size:12px;font-weight:bold;letter-spacing:4px;background:transparent;")
        self._hero_lay.addWidget(self._subtitle)

        root.addWidget(self._hero)

        # ── Scroll Area for Grid ──────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        content_w = QWidget()
        content_w.setStyleSheet("background:transparent;")
        self._grid_lay = QGridLayout(content_w)
        self._grid_lay.setContentsMargins(48, 48, 48, 80)
        self._grid_lay.setSpacing(32)
        self._grid_lay.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll.setWidget(content_w)
        root.addWidget(scroll, 1)


    def load_data(self, username: str, folder_id: str):
        self._username = username
        self._folder_id = folder_id
        folders = get_user_folders(username)
        self._folder_data = next((f for f in folders if f["id"] == folder_id), None)
        if not self._folder_data:
            self._title.setText("NOT FOUND")
            return

        self._title.setText(self._folder_data.get("name", "FOLDER").upper())
        items = self._folder_data.get("items", [])
        self._subtitle.setText(f"COLLECTION OF {len(items)} ARCHIVED VIDEOS")

        hero_img = self._folder_data.get("hero_img")
        if not hero_img:
            # Fall back to the first saved video's thumbnail
            items = self._folder_data.get("items", [])
            if items:
                hero_img = items[0].get("thumb", "")
        
        # Reset hero with current folder color while loading
        color = self._folder_data.get("color", "#f26411")
        self._hero.set_data(None, color)

        if hero_img:
            if hero_img.startswith("http"):
                load_image(hero_img, self._on_hero_loaded)
            else:
                pm = QPixmap(hero_img)
                self._on_hero_loaded(pm)

        self._search_input.setText("")
        self._render_grid()

    def _on_hero_loaded(self, pm: QPixmap):
        color = self._folder_data.get("color", "#f26411") if self._folder_data else "#f26411"
        self._hero.set_data(pm, color)

    def _on_edit_bg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Background", "", "Images (*.png *.jpg *.jpeg)")
        if path and self._folder_data:
            self._folder_data["hero_img"] = path
            folders = get_user_folders(self._username)
            for f in folders:
                if f["id"] == self._folder_id:
                    f["hero_img"] = path
                    break
            save_user_folders(self._username, folders)
            self.load_data(self._username, self._folder_id)

    def _on_clear_all(self):
        if self._folder_data:
            folders = get_user_folders(self._username)
            for f in folders:
                if f["id"] == self._folder_id:
                    f["items"] = []
                    break
            save_user_folders(self._username, folders)
            self.load_data(self._username, self._folder_id)

    def _clear_grid(self):
        while self._grid_lay.count():
            item = self._grid_lay.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

    def _render_grid(self):
        self._clear_grid()
        items = self._folder_data.get("items", [])

        query = self._search_input.text().strip().lower()
        filtered_items = [v for v in items if query in v.get("title", "").lower()]

        cols = 3
        
        if not query:
            explore_btn = QFrame()
            explore_btn.setFixedSize(320, 220)
            explore_btn.setCursor(Qt.PointingHandCursor)
            explore_btn.setStyleSheet("QFrame{background:rgba(255,255,255,0.02);border:2px dashed rgba(255,255,255,0.1);border-radius:12px;} QFrame:hover{border-color:#f26411;background:rgba(242,100,17,0.05);}")
            e_lay = QVBoxLayout(explore_btn)
            e_lay.setAlignment(Qt.AlignCenter)
            lbl = QLabel("EXPLORE MORE\nDiscover related domains")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color:#fff;font-weight:bold;font-size:12px;letter-spacing:2px;")
            e_lay.addWidget(lbl)
            explore_btn.mousePressEvent = lambda e: self.back_clicked.emit()
            self._grid_lay.addWidget(explore_btn, 0, 0)

        for i, v in enumerate(filtered_items):
            idx = i + 1 if not query else i

            card = FolderVideoCard(v)
            card.clicked.connect(self.video_selected)
            card.removed.connect(self._on_remove_video)
            card.download_requested.connect(self._on_download_video)
            self._grid_lay.addWidget(card, idx // cols, idx % cols)

    def _on_download_video(self, video_data: dict):
        slug = video_data.get("slug", "")
        if not slug: return

        import re
        title = video_data.get("title", "video")
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Video", f"{safe_title}.mp4", "Video Files (*.mp4)")
        if not save_path: return

        # Show toast that download has started
        ToastNotification.show_toast(f"Starting download for {video_data.get('title', 'video')}...", parent=self)

        def on_done(data):
            ToastNotification.show_toast("Download Complete! Saved to your machine.", is_error=False, parent=self)

        def on_err(e):
            ToastNotification.show_toast(f"Download failed: {e}", is_error=True, parent=self)

        client.download_video(slug, on_done, on_err, save_path=save_path)

    def _on_remove_video(self, video_data: dict):
        if self._folder_data:
            folders = get_user_folders(self._username)
            for f in folders:
                if f["id"] == self._folder_id:
                    f["items"] = [i for i in f.get("items", []) if i.get("slug") != video_data.get("slug")]
                    break
            save_user_folders(self._username, folders)
            self.load_data(self._username, self._folder_id)
