from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QPushButton, QLabel, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRunnable, QThreadPool, QObject, QRectF
from PySide6.QtGui import (QPainter, QColor, QPixmap, QImage, QFont,
                            QLinearGradient, QPen)
import requests

from ..components.domain_card import DomainCard
from ..components.flow_layout import FlowLayout


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


class _HeroBg(QWidget):
    """Full-bleed dark image background widget."""
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
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = self.rect()
        if self._pixmap:
            x = (r.width()  - self._pixmap.width())  // 2
            y = (r.height() - self._pixmap.height()) // 2
            p.setOpacity(0.30)
            p.drawPixmap(x, y, self._pixmap)
            p.setOpacity(1.0)
        # Dark overlay
        grad = QLinearGradient(0, 0, 0, r.height())
        grad.setColorAt(0.0, QColor(10, 10, 10, 180))
        grad.setColorAt(1.0, QColor(10, 10, 10, 230))
        p.fillRect(r, grad)


class DomainView(QWidget):
    return_clicked    = Signal()
    subfolder_selected = Signal(dict)

    def __init__(self):
        super().__init__()
        self._domain = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Hero panel ──────────────────────────────────────────────────
        self._hero = _HeroBg()
        self._hero.setFixedHeight(420)

        hero_layout = QVBoxLayout(self._hero)
        hero_layout.setContentsMargins(50, 20, 50, 40)

        # Return button
        self._ret_btn = QPushButton("← RETURN")
        self._ret_btn.setFixedSize(110, 32)
        self._ret_btn.setCursor(Qt.PointingHandCursor)
        self._ret_btn.setStyleSheet(
            "QPushButton { background: rgba(30,30,30,0.85); color: #e5e2e1; "
            "border: 1px solid #3a3a3a; border-radius: 16px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { border-color: #f26411; color: #f26411; }")
        self._ret_btn.clicked.connect(self.return_clicked)
        top_row = QHBoxLayout()
        top_row.addWidget(self._ret_btn)
        top_row.addStretch()
        hero_layout.addLayout(top_row)
        hero_layout.addStretch()

        # Label
        self._archive_lbl = QLabel("AI DISCOVERY ARCHIVE")
        self._archive_lbl.setStyleSheet(
            "color: #f26411; font-size: 11px; font-weight: bold; letter-spacing: 4px;")
        hero_layout.addWidget(self._archive_lbl)
        hero_layout.addSpacing(8)

        # Title (two lines: white + orange)
        self._title_w = QLabel()
        self._title_w.setStyleSheet("color: #ffffff; font-size: 52px; font-weight: 800; line-height: 1;")
        self._title_o = QLabel()
        self._title_o.setStyleSheet("color: #f26411; font-size: 52px; font-weight: 800; margin-top: -8px;")
        hero_layout.addWidget(self._title_w)
        hero_layout.addWidget(self._title_o)
        hero_layout.addSpacing(16)

        # Description
        self._desc_lbl = QLabel()
        self._desc_lbl.setStyleSheet("color: #aaaaaa; font-size: 13px;")
        hero_layout.addWidget(self._desc_lbl)
        hero_layout.addSpacing(16)

        # Sub-folder count
        meta_row = QHBoxLayout()
        meta_lbl = QLabel("SUB-FOLDERS")
        meta_lbl.setStyleSheet("color: #737373; font-size: 10px; letter-spacing: 2px;")
        self._count_lbl = QLabel("0")
        self._count_lbl.setStyleSheet("color: #f26411; font-size: 22px; font-weight: bold; margin-left: 8px;")
        meta_row.addWidget(meta_lbl)
        meta_row.addWidget(self._count_lbl)
        meta_row.addStretch()
        hero_layout.addLayout(meta_row)

        root.addWidget(self._hero)

        # ── Sub-folder grid ─────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: #0e0e0e; border: none; }")

        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background: #0e0e0e;")
        self._grid = FlowLayout(self._grid_widget, margin=50, hSpacing=24, vSpacing=24)

        scroll.setWidget(self._grid_widget)
        root.addWidget(scroll, 1)

    # ── Public API ──────────────────────────────────────────────────────
    def load_domain(self, domain_data: dict):
        self._domain = domain_data

        # Load hero background
        img_url = domain_data.get("img", "")
        if img_url:
            ldr = _ImgLoader(img_url)
            ldr.signals.done.connect(self._hero.set_image)
            QThreadPool.globalInstance().start(ldr)

        # Split title: first word white, rest orange
        name = domain_data.get("name", domain_data.get("title", "Domain"))
        words = name.split()
        self._title_w.setText(words[0] if words else "")
        self._title_o.setText(" ".join(words[1:]) + ("." if len(words) > 1 else ""))
        self._desc_lbl.setText(f"Immersive exploration into the {name} sector.")

        subs = domain_data.get("items", [])
        self._count_lbl.setText(str(len(subs)))

        # Clear old grid
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Populate sub-folder cards
        for i, sub in enumerate(subs):
            card = DomainCard(sub, card_width=460, card_height=340,
                              show_badge=True, badge_text="ARCHIVE DATA")
            card.clicked.connect(self.subfolder_selected)
            self._grid.addWidget(card)
