import requests
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QSizePolicy, QGridLayout, QDialog
)
from PySide6.QtCore import Qt, Signal, QVariantAnimation, QEasingCurve, QRectF
from PySide6.QtGui import QFont, QColor, QPainter, QPixmap, QImage, QLinearGradient, QPen

from api_client import client
from image_cache import load_image


# ── Large video card (Recent Sessions) ───────────────────────────────────────
class LargeHistoryCard(QWidget):
    clicked = Signal(dict)

    def __init__(self, v: dict, parent=None):
        super().__init__(parent)
        self._v = v
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._scale = 1.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # Thumbnail
        self._thumb_frame = QFrame()
        self._thumb_frame.setFixedHeight(480)
        self._thumb_frame.setStyleSheet(
            "QFrame{background:#131313;border-radius:6px;border:1px solid #232323;}")
        self._thumb_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._thumb = QLabel(self._thumb_frame)
        self._thumb.setScaledContents(True)
        self._thumb.setGeometry(0, 0, 500, 480)

        # TEMPORAL LOG badge
        badge = QLabel("TEMPORAL LOG", self._thumb_frame)
        badge.setStyleSheet(
            "QLabel{background:#f26411;color:#1a0800;font-size:8px;font-weight:bold;"
            "letter-spacing:2px;padding:3px 8px;border:none;}")
        badge.move(12, 445)
        badge.adjustSize()

        lay.addWidget(self._thumb_frame)

        # Meta row
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        tag_lbl = QLabel(v.get("tag", "WATCHED"))
        tag_lbl.setStyleSheet(
            "color:#f26411;font-size:8px;font-weight:bold;letter-spacing:2px;background:transparent;")
        info_col.addWidget(tag_lbl)

        title_lbl = QLabel(v.get("title", "Untitled"))
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            "color:#e5e2e1;font-size:18px;font-weight:bold;background:transparent;")
        info_col.addWidget(title_lbl)

        sub_lbl = QLabel(f"Last viewed at just now  •  Duration: {v.get('desc', '')}")
        sub_lbl.setStyleSheet(
            "color:rgba(229,226,225,0.35);font-size:11px;background:transparent;")
        info_col.addWidget(sub_lbl)

        meta_row.addLayout(info_col, 1)
        lay.addLayout(meta_row)

        # Load thumbnail
        url = v.get("thumb") or v.get("img", "")
        if url:
            load_image(url, self._on_img)

    def resizeEvent(self, e):
        self._thumb.setGeometry(0, 0, self._thumb_frame.width(), self._thumb_frame.height())
        super().resizeEvent(e)

    def _on_img(self, pm: QPixmap):
        self._thumb.setPixmap(pm)

    def _on_anim(self, v):
        self._scale = v
        self.update()

    def enterEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(1.03)
        self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._scale > 1.0:
            p.translate(self.width()/2, self.height()/2)
            p.scale(self._scale, self._scale)
            p.translate(-self.width()/2, -self.height()/2)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self._v)
        super().mousePressEvent(e)


# ── Small video card (Prior Archives) ────────────────────────────────────────
class SmallHistoryCard(QWidget):
    clicked = Signal(dict)

    def __init__(self, v: dict, parent=None):
        super().__init__(parent)
        self._v = v
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._scale = 1.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self._thumb_frame = QFrame()
        self._thumb_frame.setFixedHeight(340)
        self._thumb_frame.setStyleSheet(
            "QFrame{background:#131313;border-radius:6px;border:1px solid #232323;}")
        self._thumb_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._thumb = QLabel(self._thumb_frame)
        self._thumb.setScaledContents(True)
        self._thumb.setGeometry(0, 0, 300, 340)

        lay.addWidget(self._thumb_frame)

        title_lbl = QLabel(v.get("title", "Untitled"))
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            "color:#e5e2e1;font-size:14px;font-weight:bold;background:transparent;")
        lay.addWidget(title_lbl)

        tag_lbl = QLabel(f"{v.get('tag', 'WATCHED')}  •  {v.get('desc', '')} Viewed")
        tag_lbl.setStyleSheet(
            "color:rgba(229,226,225,0.32);font-size:9px;letter-spacing:1px;background:transparent;")
        lay.addWidget(tag_lbl)

        url = v.get("thumb") or v.get("img", "")
        if url:
            load_image(url, self._on_img)

    def resizeEvent(self, e):
        self._thumb.setGeometry(0, 0, self._thumb_frame.width(), self._thumb_frame.height())
        super().resizeEvent(e)

    def _on_img(self, pm: QPixmap):
        self._thumb.setPixmap(pm)

    def _on_anim(self, v):
        self._scale = v
        self.update()

    def enterEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(1.05)
        self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._scale > 1.0:
            p.translate(self.width()/2, self.height()/2)
            p.scale(self._scale, self._scale)
            p.translate(-self.width()/2, -self.height()/2)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self._v)
        super().mousePressEvent(e)


# ── Timeline section label ────────────────────────────────────────────────────
def _section_sep(text: str) -> QWidget:
    w = QWidget()
    w.setStyleSheet("background:transparent;")
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(16)

    line_l = QFrame()
    line_l.setFrameShape(QFrame.HLine)
    line_l.setStyleSheet("border:none;border-top:1px solid #232323;")
    lay.addWidget(line_l, 1)

    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color:rgba(229,226,225,0.30);font-size:8px;font-weight:bold;"
        "letter-spacing:4px;padding:4px 16px;border:1px solid #232323;"
        "background:transparent;")
    lay.addWidget(lbl, 0)

    line_r = QFrame()
    line_r.setFrameShape(QFrame.HLine)
    line_r.setStyleSheet("border:none;border-top:1px solid #232323;")
    lay.addWidget(line_r, 1)
    return w


# ── Confirm Clear dialog ──────────────────────────────────────────────────────
class ClearConfirmDialog(QDialog):
    confirmed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clear History")
        self.setFixedSize(380, 210)
        self.setStyleSheet("""
            QDialog{background:#1c1b1b;border:1px solid #3a1010;}
            QLabel{color:#e5e2e1;background:transparent;}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)

        title = QLabel("Clear Watch History")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#ffffff;background:transparent;")
        lay.addWidget(title)

        body = QLabel(
            "This will permanently erase your entire watch history.\n"
            "This action cannot be undone.")
        body.setWordWrap(True)
        body.setStyleSheet("color:rgba(255,255,255,0.50);font-size:12px;background:transparent;")
        lay.addWidget(body)

        btns = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#a0a0a0;border:none;border-radius:6px;"
            "font-weight:bold;padding:10px 24px;}QPushButton:hover{background:#333;}")
        cancel.clicked.connect(self.reject)

        confirm = QPushButton("Clear All")
        confirm.setStyleSheet(
            "QPushButton{background:#7f1d1d;color:#ffffff;border:none;border-radius:6px;"
            "font-weight:bold;padding:10px 24px;letter-spacing:2px;}"
            "QPushButton:hover{background:#991b1b;}")
        confirm.clicked.connect(self._on_confirm)

        btns.addWidget(cancel)
        btns.addWidget(confirm)
        lay.addLayout(btns)

    def _on_confirm(self):
        self.confirmed.emit()
        self.accept()


# ── History View ──────────────────────────────────────────────────────────────
class HistoryView(QWidget):
    video_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#0e0e0e;")
        self._history: list = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Scrollable body ───────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        self._body = QWidget()
        self._body.setStyleSheet("background:transparent;")
        self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(56, 40, 56, 60)
        self._body_lay.setSpacing(0)

        # Page header
        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(0, 0, 0, 0)

        hdr_col = QVBoxLayout()
        hdr_col.setSpacing(8)

        hist_tag = QLabel("HISTORY")
        hist_tag.setStyleSheet(
            "color:#f26411;font-size:9px;font-weight:bold;letter-spacing:5px;background:transparent;")
        hdr_col.addWidget(hist_tag)

        title_lbl = QLabel()
        title_lbl.setTextFormat(Qt.RichText)
        title_lbl.setText(
            '<span style="color:#ffffff;font-size:48px;font-weight:900;">Chronological</span>'
            ' <span style="color:rgba(229,226,225,0.35);font-size:48px;font-weight:300;">Logs</span>')
        hdr_col.addWidget(title_lbl)

        hdr_row.addLayout(hdr_col, 1)

        self._clear_btn = QPushButton("⌫   CLEAR HISTORY")
        self._clear_btn.setFixedHeight(38)
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setStyleSheet("""
            QPushButton{background:rgba(127,29,29,0.25);color:#f87171;
                border:1px solid rgba(127,29,29,0.5);border-radius:6px;
                font-size:9px;font-weight:bold;letter-spacing:2px;padding:0 16px;}
            QPushButton:hover{background:rgba(127,29,29,0.5);}
        """)
        self._clear_btn.clicked.connect(self._on_clear)
        hdr_row.addWidget(self._clear_btn, 0, Qt.AlignBottom)

        self._body_lay.addLayout(hdr_row)
        self._body_lay.addSpacing(36)

        # Content placeholder (populated in load_data)
        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background:transparent;")
        self._content_lay = QVBoxLayout(self._content_widget)
        self._content_lay.setContentsMargins(0, 0, 0, 0)
        self._content_lay.setSpacing(24)
        self._body_lay.addWidget(self._content_widget)
        self._body_lay.addStretch()

        scroll.setWidget(self._body)
        root.addWidget(scroll, 1)

    # ── Public ────────────────────────────────────────────────────────────────
    def load_data(self):
        self._show_loading()
        client.get_profile(self._on_profile, lambda e: self._render([]))

    def _on_profile(self, data: dict):
        self._history = data.get("history", [])
        self._render(self._history)

    # ── Rendering ─────────────────────────────────────────────────────────────
    def _clear_content(self):
        while self._content_lay.count():
            item = self._content_lay.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

    def _show_loading(self):
        self._clear_content()
        lbl = QLabel("Synchronizing Temporal Records...")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            "color:rgba(229,226,225,0.25);font-size:12px;letter-spacing:2px;"
            "font-style:italic;background:transparent;")
        lbl.setFixedHeight(120)
        self._content_lay.addWidget(lbl)

    def _render(self, videos: list):
        self._clear_content()

        if not videos:
            self._render_empty()
            return

        # ── RECENT SESSIONS (first 2 — large cards in 2-col grid) ─────────
        self._content_lay.addWidget(_section_sep("RECENT SESSIONS"))
        self._content_lay.addSpacing(20)

        recent = videos[:2]
        recent_grid = QHBoxLayout()
        recent_grid.setSpacing(28)
        for v in recent:
            card = LargeHistoryCard(v)
            card.clicked.connect(self.video_selected)
            recent_grid.addWidget(card, 1)
        # Fill empty slot if only 1 video
        if len(recent) == 1:
            recent_grid.addWidget(QWidget(), 1)

        recent_w = QWidget()
        recent_w.setStyleSheet("background:transparent;")
        recent_w.setLayout(recent_grid)
        self._content_lay.addWidget(recent_w)

        # ── PRIOR ARCHIVES (next videos — small cards in 3-col grid) ──────
        older = videos[2:]
        if older:
            self._content_lay.addSpacing(40)
            self._content_lay.addWidget(_section_sep("PRIOR ARCHIVES"))
            self._content_lay.addSpacing(20)

            cols = 3
            grid_w = QWidget()
            grid_w.setStyleSheet("background:transparent;")
            grid = QGridLayout(grid_w)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(20)

            for i, v in enumerate(older[:9]):
                card = SmallHistoryCard(v)
                card.clicked.connect(self.video_selected)
                grid.addWidget(card, i // cols, i % cols)

            self._content_lay.addWidget(grid_w)

    def _render_empty(self):
        container = QWidget()
        container.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(container)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(16)

        icon = QLabel("⏳")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size:64px;background:transparent;")
        lay.addWidget(icon)

        h = QLabel("Chronological Void")
        h.setAlignment(Qt.AlignCenter)
        h.setStyleSheet(
            "color:#ffffff;font-size:28px;font-weight:bold;background:transparent;")
        lay.addWidget(h)

        sub = QLabel(
            "Your journey through the archives has not yet been logged.\n"
            "Start exploring to populate your temporal records.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet(
            "color:rgba(229,226,225,0.30);font-size:13px;font-style:italic;background:transparent;")
        lay.addWidget(sub)
        container.setFixedHeight(280)
        self._content_lay.addWidget(container)

    # ── Clear history ─────────────────────────────────────────────────────────
    def _on_clear(self):
        dlg = ClearConfirmDialog(self)
        dlg.confirmed.connect(self._do_clear)
        dlg.exec()

    def _do_clear(self):
        client.clear_history(self._on_cleared, lambda e: print(f"Clear history error: {e}"))

    def _on_cleared(self, _):
        self._history = []
        self._render([])
