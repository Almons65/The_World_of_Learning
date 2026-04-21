from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QPushButton, QLabel, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Signal, QRunnable, QThreadPool, QObject, QRectF, QVariantAnimation, QEasingCurve
from PySide6.QtGui import (QPainter, QColor, QPixmap, QImage, QFont,
                            QLinearGradient, QPen, QPainterPath)
import requests

from ..components.video_card import VideoCard


# ── Image loader ─────────────────────────────────────────────────────────────
class _Sigs(QObject):
    done = Signal(QImage)

class _ImgLoader(QRunnable):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.signals = _Sigs()
    def run(self):
        try:
            r = requests.get(self.url, timeout=10)
            if r.status_code == 200:
                img = QImage(); img.loadFromData(r.content)
                self.signals.done.emit(img)
        except: pass


# ── Hero background ───────────────────────────────────────────────────────────
class _HeroBg(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None

    def set_image(self, img: QImage):
        if not img.isNull():
            self._pixmap = QPixmap.fromImage(img).scaled(
                2560, 1440, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        r = self.rect()
        if self._pixmap:
            x = (r.width()  - self._pixmap.width())  // 2
            y = (r.height() - self._pixmap.height()) // 2
            p.setOpacity(0.28)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            p.drawPixmap(x, y, self._pixmap)
            p.setOpacity(1.0)
        grad = QLinearGradient(0, 0, 0, r.height())
        grad.setColorAt(0.0, QColor(10, 10, 10, 170))
        grad.setColorAt(1.0, QColor(10, 10, 10, 235))
        p.fillRect(r, grad)


# ── Thumbnail label ───────────────────────────────────────────────────────────
class _ThumbLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 80)
        self.setStyleSheet("background: #1a1a1a; border-radius: 4px;")
        self.setScaledContents(True)

    def set_image(self, img: QImage):
        if not img.isNull():
            self.setPixmap(QPixmap.fromImage(img).scaled(
                140, 80, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))


# ── Star button ───────────────────────────────────────────────────────────────
class StarBtn(QLabel):
    clicked = Signal()
    def __init__(self):
        super().__init__("☆")
        self.setFixedSize(32, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.setAlignment(Qt.AlignCenter)
        self._on = False
        self._apply()
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(150)
        self._anim.valueChanged.connect(lambda v: None)  # just trigger repaints

    def _apply(self):
        c = "#f26411" if self._on else "#555555"
        self.setStyleSheet(f"color: {c}; font-size: 18px; background: transparent;")

    def toggle(self):
        self._on = not self._on
        self.setText("★" if self._on else "☆")
        self._apply()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.toggle()
            self.clicked.emit()
        super().mousePressEvent(e)

    def enterEvent(self, e):
        self.setStyleSheet(f"color: #f26411; font-size: 18px; background: transparent;")
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._apply()
        super().leaveEvent(e)


# ── Video row item (matches web design) ──────────────────────────────────────
class VideoRowItem(QWidget):
    clicked = Signal(dict)

    def __init__(self, index: int, video_data: dict, parent=None):
        super().__init__(parent)
        self.video_data = video_data
        self.setFixedHeight(104)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        
        self._hover_t = 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._upd_hover)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 12)
        lay.setSpacing(16)

        # Index number
        num_lbl = QLabel(f"{index:02d}")
        num_lbl.setFixedWidth(32)
        num_lbl.setAlignment(Qt.AlignCenter)
        num_lbl.setStyleSheet("color: #555555; font-size: 14px; font-weight: bold; background: transparent;")
        lay.addWidget(num_lbl)

        # Thumbnail
        self._thumb = _ThumbLabel()
        img_url = video_data.get("thumb", "")
        if img_url:
            ldr = _ImgLoader(img_url)
            ldr.signals.done.connect(self._thumb.set_image)
            QThreadPool.globalInstance().start(ldr)
        lay.addWidget(self._thumb)

        # Title + duration block
        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(6)

        title = video_data.get("title", "Unknown")
        title_lbl = QLabel(title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("color: #e5e2e1; font-size: 13px; font-weight: bold; background: transparent;")
        info.addWidget(title_lbl)

        # Duration badge (orange pill)
        dur_row = QHBoxLayout(); dur_row.setContentsMargins(0,0,0,0); dur_row.setSpacing(8)
        duration = video_data.get("desc", "")
        if duration:
            dur_lbl = QLabel(duration)
            dur_lbl.setStyleSheet(
                "background: rgba(242,100,17,0.25); color: #f26411; font-size: 10px; "
                "font-weight: bold; border-radius: 8px; padding: 2px 8px; border: 1px solid rgba(242,100,17,0.4);")
            dur_row.addWidget(dur_lbl, 0, Qt.AlignLeft)

        creator = video_data.get("creator", "")
        if creator:
            cr_lbl = QLabel(creator[:28])
            cr_lbl.setStyleSheet("color: #737373; font-size: 11px; background: transparent;")
            dur_row.addWidget(cr_lbl, 0, Qt.AlignLeft)
        dur_row.addStretch()
        info.addLayout(dur_row)
        info.addStretch()
        lay.addLayout(info, 1)

        # Star
        self._star = StarBtn()
        lay.addWidget(self._star, 0, Qt.AlignVCenter)

        # Separator line (drawn in paint)
    def _upd_hover(self, v):
        self._hover_t = v
        self.update()
        
    def enterEvent(self, e):
        self.anim.stop(); self.anim.setStartValue(self._hover_t)
        self.anim.setEndValue(1.0); self.anim.start()
        super().enterEvent(e)
        
    def leaveEvent(self, e):
        self.anim.stop(); self.anim.setStartValue(self._hover_t)
        self.anim.setEndValue(0.0); self.anim.start()
        super().leaveEvent(e)
        
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.video_data)
        super().mousePressEvent(e)
        
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._hover_t > 0.01:
            p.setPen(Qt.NoPen)
            alpha = int(18 * self._hover_t)
            p.setBrush(QColor(255, 255, 255, alpha))
            p.drawRoundedRect(4, 0, self.width() - 8, self.height() - 1, 8, 8)
            
        # Bottom separator
        p.setPen(QPen(QColor("#2a2a2a"), 1))
        p.drawLine(0, self.height()-1, self.width(), self.height()-1)


# ── A→Z sort button ───────────────────────────────────────────────────────────
class SortBtn(QPushButton):
    def __init__(self):
        super().__init__("☆  A → Z")
        self.setCheckable(True)
        self.setFixedSize(90, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.toggled.connect(self._upd)
        self._upd(False)

    def _upd(self, on):
        if on:
            self.setText("★  Z → A")
            self.setStyleSheet(
                "QPushButton { background: rgba(242,100,17,0.2); color: #f26411; "
                "border: 1px solid #f26411; border-radius: 4px; font-size: 10px; font-weight: bold; letter-spacing: 1px; }")
        else:
            self.setText("☆  A → Z")
            self.setStyleSheet(
                "QPushButton { background: #1e1e1e; color: #e5e2e1; "
                "border: 1px solid #3a3a3a; border-radius: 4px; font-size: 10px; font-weight: bold; letter-spacing: 1px; }"
                "QPushButton:hover { border-color: #f26411; color: #f26411; }")


# ── Subfolder View ────────────────────────────────────────────────────────────
class SubfolderView(QWidget):
    return_clicked = Signal()
    video_selected = Signal(dict)

    def __init__(self):
        super().__init__()
        self._videos = []
        self._sort_az = True
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Hero ────────────────────────────────────────────────────────
        self._hero = _HeroBg()
        self._hero.setFixedHeight(340)
        hl = QVBoxLayout(self._hero)
        hl.setContentsMargins(50, 20, 50, 36)

        # Top row: RETURN + video count
        top = QHBoxLayout()
        self._ret_btn = QPushButton("← RETURN")
        self._ret_btn.setFixedSize(110, 32)
        self._ret_btn.setCursor(Qt.PointingHandCursor)
        self._ret_btn.setStyleSheet(
            "QPushButton { background: rgba(30,30,30,0.85); color: #e5e2e1; "
            "border: 1px solid #3a3a3a; border-radius: 16px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { border-color: #f26411; color: #f26411; }")
        self._ret_btn.clicked.connect(self.return_clicked)
        top.addWidget(self._ret_btn)
        top.addStretch()
        self._vcnt_lbl = QLabel()
        self._vcnt_lbl.setStyleSheet("color: #f26411; font-size: 15px; font-weight: bold;")
        self._vcnt_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(self._vcnt_lbl)
        hl.addLayout(top)
        hl.addStretch()

        # AI DISCOVERY badge
        self._badge = QLabel("AI DISCOVERY")
        self._badge.setFixedHeight(24)
        self._badge.setStyleSheet(
            "background: #f26411; color: white; font-size: 9px; font-weight: bold; "
            "letter-spacing: 2px; border-radius: 4px; padding: 0 8px;")
        hl.addWidget(self._badge, 0, Qt.AlignLeft)
        hl.addSpacing(10)

        # Split title
        self._title_w = QLabel()
        self._title_w.setStyleSheet("color: #ffffff; font-size: 46px; font-weight: 800;")
        self._title_o = QLabel()
        self._title_o.setStyleSheet("color: #f26411; font-size: 46px; font-weight: 800; margin-top: -6px;")
        self._title_o.setWordWrap(True)
        hl.addWidget(self._title_w)
        hl.addWidget(self._title_o)
        hl.addSpacing(8)

        self._desc_lbl = QLabel()
        self._desc_lbl.setStyleSheet("color: #999999; font-size: 12px;")
        hl.addWidget(self._desc_lbl)
        hl.addSpacing(12)

        # Orange separator line
        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.HLine)
        sep_line.setFixedHeight(2)
        sep_line.setMaximumWidth(260)
        sep_line.setStyleSheet("border: none; background: #f26411;")
        hl.addWidget(sep_line, 0, Qt.AlignLeft)

        root.addWidget(self._hero)

        # ── Video list ──────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: #0e0e0e; border: none; }")

        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background: #0e0e0e;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(50, 30, 50, 40)
        self._list_layout.setSpacing(0)

        # "Videos" heading + A→Z sort
        vid_hdr = QHBoxLayout()
        vhdr_lbl = QLabel("Videos")
        vhdr_lbl.setStyleSheet("color: #e5e2e1; font-size: 18px; font-weight: bold;")
        self._sort_btn = SortBtn()
        self._sort_btn.toggled.connect(self._on_sort_toggled)
        vid_hdr.addWidget(vhdr_lbl)
        vid_hdr.addStretch()
        vid_hdr.addWidget(self._sort_btn)
        self._list_layout.addLayout(vid_hdr)
        self._list_layout.addSpacing(16)

        # Rows container
        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(0)
        self._rows_layout.setContentsMargins(0,0,0,0)
        self._list_layout.addLayout(self._rows_layout)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_widget)
        root.addWidget(scroll, 1)

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _clear_rows(self):
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            if item.widget(): item.widget().setParent(None)

    def _populate_rows(self):
        self._clear_rows()
        vids = sorted(self._videos, key=lambda v: v.get("title","").lower(),
                      reverse=not self._sort_az)
        for i, v in enumerate(vids):
            row = VideoRowItem(i + 1, v)
            row.clicked.connect(self.video_selected)
            self._rows_layout.addWidget(row)

    def _on_sort_toggled(self, checked):
        # checked = True means A→Z button is now showing Z→A (i.e. we flipped to desc)
        self._sort_az = not checked
        self._populate_rows()

    # ── Public API ───────────────────────────────────────────────────────────
    def load_subfolder(self, sub_data: dict):
        # Reset sort state
        self._sort_btn.setChecked(False)
        self._sort_az = True

        # Hero image
        img_url = sub_data.get("img", "")
        if img_url:
            ldr = _ImgLoader(img_url)
            ldr.signals.done.connect(self._hero.set_image)
            QThreadPool.globalInstance().start(ldr)

        # Title split: first word white, rest orange
        name = sub_data.get("name", sub_data.get("title", "Sub-Folder"))
        words = name.split()
        self._title_w.setText(words[0] if words else "")
        self._title_o.setText(" ".join(words[1:]))
        self._desc_lbl.setText(f"Exploring contents of {name}.")

        self._videos = [v for v in sub_data.get("items", []) if v.get("type") != "folder"]
        self._vcnt_lbl.setText(f"{len(self._videos)} Videos")
        self._populate_rows()
