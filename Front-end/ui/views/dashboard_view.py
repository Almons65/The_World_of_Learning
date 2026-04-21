from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QLineEdit, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor

from api_client import client
from ..components.domain_card import DomainCard
from ..components.flow_layout import FlowLayout


# ── Spinner ──────────────────────────────────────────────────────────────────
from PySide6.QtGui import QPainter, QPen
class SpinnerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
    def start(self): self._timer.start(16)
    def stop(self):  self._timer.stop()
    def _tick(self):
        self._angle = (self._angle + 6) % 360
        self.update()
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor("#f26411"), 3)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.translate(self.width() / 2, self.height() / 2)
        p.rotate(self._angle)
        p.drawArc(-9, -9, 18, 18, 30 * 16, 300 * 16)


# ── AI Sparkle Icon ──────────────────────────────────────────────────────────
from PySide6.QtGui import QPainterPath
class SparkleIconWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#777777"))

        def draw_star(cx, cy, size):
            path = QPainterPath()
            path.moveTo(cx, cy - size)
            path.quadTo(cx, cy, cx + size, cy)
            path.quadTo(cx, cy, cx, cy + size)
            path.quadTo(cx, cy, cx - size, cy)
            path.quadTo(cx, cy, cx, cy - size)
            p.drawPath(path)

        draw_star(8, 10, 6)
        draw_star(15, 5, 3)
        draw_star(14, 15, 2.5)


# ── Lift wrapper (translateY) ────────────────────────────────────────────────
class LiftWrapper(QWidget):
    def __init__(self, child, lift_px=3, parent=None):
        super().__init__(parent)
        self.child = child
        self.lift_px = lift_px
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, lift_px, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.child)
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._upd)
        self.child.installEventFilter(self)
        self.y = 0.0
    def eventFilter(self, obj, event):
        if obj == self.child:
            if event.type() == event.Type.Enter and self.child.isEnabled():
                self.anim.stop(); self.anim.setStartValue(self.y)
                self.anim.setEndValue(float(self.lift_px)); self.anim.start()
            elif event.type() == event.Type.Leave:
                self.anim.stop(); self.anim.setStartValue(self.y)
                self.anim.setEndValue(0.0); self.anim.start()
        return super().eventFilter(obj, event)
    def _upd(self, v):
        self.y = v
        mt = self.lift_px - int(round(v))
        self.layout().setContentsMargins(0, mt, 0, int(round(v)))


# ── Explore Deeper button ────────────────────────────────────────────────────
class ExploreDeeperBtn(QPushButton):
    def __init__(self):
        super().__init__("         EXPLORE DEEPER")
        self.setFixedSize(190, 44)
        self.setCursor(Qt.PointingHandCursor)
        self._t = 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._upd)
        self._apply()
    def _apply(self):
        v = int(24 + 10 * self._t)
        b = int(45 + 30 * self._t)
        self.setStyleSheet(
            f"QPushButton {{ background: rgb({v},{v},{v}); color: #e5e2e1; "
            f"font-weight: bold; font-size: 11px; letter-spacing: 1px; "
            f"border: 1px solid rgb({b},{b},{b}); border-radius: 8px; }}")
    def _upd(self, v): self._t = v; self._apply()
    def enterEvent(self, e):
        self.anim.stop(); self.anim.setStartValue(self._t)
        self.anim.setEndValue(1.0); self.anim.start(); super().enterEvent(e)
    def leaveEvent(self, e):
        self.anim.stop(); self.anim.setStartValue(self._t)
        self.anim.setEndValue(0.0); self.anim.start(); super().leaveEvent(e)
    def paintEvent(self, e):
        super().paintEvent(e)
        from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath
        from PySide6.QtCore import QPointF
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        cx, cy = 34, self.height() / 2
        r = 7.5
        
        # Outer circle
        pen = QPen(QColor("#e5e2e1"), 1.5)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)
        
        # Compass needle
        p.translate(cx, cy)
        p.rotate(45)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#e5e2e1"))
        
        path = QPainterPath()
        path.moveTo(0, -r + 2)
        path.lineTo(1.5, 0)
        path.lineTo(0, r - 2)
        path.lineTo(-1.5, 0)
        path.closeSubpath()
        p.drawPath(path)
        
        # Inner dot hole
        p.setBrush(QColor(int(24 + 10 * self._t), int(24 + 10 * self._t), int(24 + 10 * self._t)))
        p.drawEllipse(QPointF(0, 0), 1.5, 1.5)


# ── Section divider with label ───────────────────────────────────────────────
class SectionDivider(QWidget):
    def __init__(self, label, sublabel="", parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 28, 0, 14)
        lay.setSpacing(4)

        title = QLabel(label)
        title.setStyleSheet("color: #e5e2e1; font-size: 11px; font-weight: bold; letter-spacing: 3px;")
        lay.addWidget(title)

        if sublabel:
            sub = QLabel(sublabel)
            sub.setStyleSheet("color: #737373; font-size: 12px;")
            lay.addWidget(sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("border: none; border-top: 1px solid #2a2a2a;")
        sep.setFixedHeight(1)
        lay.addSpacing(8)
        lay.addWidget(sep)


# ── Inline spinner row for "loading more" ───────────────────────────────────
class InlineLoadingRow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 16)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(14)
        self._spinner = SpinnerWidget()
        lbl = QLabel("Fetching more domains...")
        lbl.setStyleSheet("color: #555; font-size: 13px; letter-spacing: 1px;")
        lay.addWidget(self._spinner)
        lay.addWidget(lbl)
        self._spinner.start()

    def stop(self):
        self._spinner.stop()


# ── Dashboard View ───────────────────────────────────────────────────────────
class DashboardView(QWidget):
    video_selected   = Signal(dict)
    domain_selected  = Signal(dict)

    def __init__(self):
        super().__init__()
        self._explore_page = 0
        self._current_domain_names = []
        self._inline_loader = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Search bar ───────────────────────────────────────────────────
        sb_bg = QWidget()
        sb_bg.setStyleSheet("background: transparent;")
        sb_lay = QHBoxLayout(sb_bg)
        sb_lay.setContentsMargins(40, 24, 40, 16)
        sb_lay.setAlignment(Qt.AlignCenter)

        self._search_frame = QFrame()
        self._search_frame.setObjectName("searchFrame")
        self._search_frame.setFixedSize(650, 52)
        self._search_frame.setStyleSheet(
            "QFrame#searchFrame { background: #151515; border: 1px solid #2a2a2a; border-radius: 12px; }")
        sf_lay = QHBoxLayout(self._search_frame)
        sf_lay.setContentsMargins(16, 0, 6, 0)
        sf_lay.setSpacing(12)

        spark = SparkleIconWidget()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search any topic to discover domains...")
        self._search_input.setStyleSheet(
            "QLineEdit { background: transparent; border: none; color: #e5e2e1; font-size: 13px; }")
        self._search_input.setFont(QFont("Segoe UI", 11))
        self._search_input.returnPressed.connect(self._on_search)

        self._search_btn = QPushButton("↑")
        self._search_btn.setFixedSize(38, 38)
        self._search_btn.setCursor(Qt.PointingHandCursor)
        self._search_btn.setStyleSheet(
            "QPushButton { background: #f26411; color: white; font-size: 16px; font-weight: bold; "
            "border: none; border-radius: 8px; }"
            "QPushButton:hover { background: #ff7326; }")
        self._search_btn.clicked.connect(self._on_search)

        sf_lay.addWidget(spark); sf_lay.addWidget(self._search_input, 1); sf_lay.addWidget(self._search_btn)
        sb_lay.addWidget(self._search_frame)
        root.addWidget(sb_bg)

        # ── Scrollable content ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._cl = QVBoxLayout(self._content)
        self._cl.setContentsMargins(40, 0, 40, 40)
        self._cl.setSpacing(0)

        # Section header (initial)
        hf = QWidget(); hf.setStyleSheet("background: transparent;")
        hfl = QVBoxLayout(hf); hfl.setContentsMargins(0, 0, 0, 14); hfl.setSpacing(4)
        self._sec_title = QLabel("GLOBAL DISCOVERY FEED")
        self._sec_title.setStyleSheet("color: #e5e2e1; font-size: 11px; font-weight: bold; letter-spacing: 3px;")
        self._sec_sub = QLabel("Explore trending educational content across the network")
        self._sec_sub.setStyleSheet("color: #737373; font-size: 12px;")
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("border: none; border-top: 1px solid #2a2a2a;"); sep.setFixedHeight(1)
        hfl.addWidget(self._sec_title); hfl.addWidget(self._sec_sub)
        hfl.addSpacing(12); hfl.addWidget(sep)
        self._cl.addWidget(hf)

        # Initial loading frame
        self._load_frame = QFrame()
        self._load_frame.setStyleSheet(
            "QFrame { background: #161616; border: 1px solid #222; border-radius: 8px; }")
        self._load_frame.setFixedHeight(180)
        lfl = QHBoxLayout(self._load_frame); lfl.setAlignment(Qt.AlignCenter); lfl.setSpacing(14)
        self._spinner = SpinnerWidget()
        self._load_lbl = QLabel("Synthesizing Global Data...")
        self._load_lbl.setStyleSheet("color: #737373; font-size: 14px; letter-spacing: 1px;")
        lfl.addWidget(self._spinner); lfl.addWidget(self._load_lbl)
        self._cl.addWidget(self._load_frame)

        # Main domain cards flow widget
        self._cards_widget = QWidget()
        self._cards_widget.setStyleSheet("background: transparent;")
        self._cards_flow = FlowLayout(self._cards_widget, margin=0, hSpacing=18, vSpacing=18)
        self._cards_flow.setContentsMargins(0, 20, 0, 10)
        self._cards_widget.hide()
        self._cl.addWidget(self._cards_widget)

        self._cl.addStretch(1)

        # Explore Deeper
        btn_row = QHBoxLayout(); btn_row.setContentsMargins(0, 24, 0, 0); btn_row.setAlignment(Qt.AlignHCenter)
        self._explore_btn = ExploreDeeperBtn()
        self._explore_wrapper = LiftWrapper(self._explore_btn, lift_px=3)
        self._explore_wrapper.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._explore_btn.clicked.connect(self._on_explore_deeper)
        btn_row.addWidget(self._explore_wrapper)
        self._cl.addLayout(btn_row)

        scroll.setWidget(self._content)
        root.addWidget(scroll, 1)

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _add_cards(self, categories, shuffle=True):
        import random
        domains = list(categories)
        if shuffle:
            random.shuffle(domains)
        for domain in domains:
            card = DomainCard(domain, card_width=460, card_height=340, show_badge=False)
            card.clicked.connect(self.domain_selected)
            self._cards_flow.addWidget(card)
            self._current_domain_names.append(domain.get("name", ""))
        self._cards_widget.show()
        self._cards_widget.updateGeometry()

    def _remove_inline_loader(self):
        if self._inline_loader:
            self._inline_loader.stop()
            # Remove from layout
            idx = self._cl.indexOf(self._inline_loader)
            if idx >= 0:
                self._cl.takeAt(idx)
            self._inline_loader.setParent(None)
            self._inline_loader = None

    def _show_inline_loader(self):
        self._remove_inline_loader()
        self._inline_loader = InlineLoadingRow()
        # Insert before the stretch+button (last 2 items)
        count = self._cl.count()
        self._cl.insertWidget(count - 2, self._inline_loader)

    # ── Initial load ─────────────────────────────────────────────────────────
    def load_data(self):
        self._load_frame.show()
        self._cards_widget.hide()
        self._spinner.start()
        self._load_lbl.setText("Synthesizing Global Data...")
        self._sec_title.setText("GLOBAL DISCOVERY FEED")
        self._sec_sub.setText("Explore trending educational content across the network")
        self._current_domain_names = []
        self._explore_page = 0
        # Clear old cards
        while self._cards_flow.count():
            item = self._cards_flow.takeAt(0)
            if item.widget(): item.widget().setParent(None)
        # Remove any extra section dividers
        self._clear_extra_sections()
        client.get_discover(self._on_initial_loaded, self._on_error)

    def _clear_extra_sections(self):
        """Remove dynamically added SectionDivider and InlineLoadingRow widgets."""
        self._remove_inline_loader()
        to_remove = []
        for i in range(self._cl.count()):
            w = self._cl.itemAt(i)
            if w and w.widget() and isinstance(w.widget(), (SectionDivider, InlineLoadingRow)):
                to_remove.append(w.widget())
        for w in to_remove:
            self._cl.removeWidget(w)
            w.setParent(None)

    def _on_initial_loaded(self, data):
        self._spinner.stop()
        self._load_frame.hide()
        categories = data.get("categories", [])
        if not categories:
            self._load_lbl.setText("No data. Try refreshing."); self._load_frame.show(); return

        self._sec_title.setText("AI DISCOVERY")
        self._sec_sub.setText(f"Curated domains based on your interests")
        self._add_cards(categories)

    # ── Search ───────────────────────────────────────────────────────────────
    def _on_search(self):
        query = self._search_input.text().strip()
        if not query:
            return
        self._show_inline_loader()
        self._explore_btn.setEnabled(False)
        client.search_domains(query, self._on_search_loaded,
                              lambda msg: self._on_append_error(msg))

    def _on_search_loaded(self, data):
        self._remove_inline_loader()
        self._explore_btn.setEnabled(True)
        categories = data.get("categories", [])
        query = data.get("query", self._search_input.text().strip())
        if not categories:
            return

        # Insert a visual divider before the new batch
        divider = SectionDivider(
            f"SEARCH: {query.upper()}",
            f"{len(categories)} domain{'s' if len(categories) != 1 else ''} found for '{query}'"
        )
        count = self._cl.count()
        self._cl.insertWidget(count - 2, divider)
        self._add_cards(categories, shuffle=False)

    # ── Explore Deeper ───────────────────────────────────────────────────────
    def _on_explore_deeper(self):
        self._show_inline_loader()
        self._explore_btn.setEnabled(False)
        self._explore_page += 1
        client.explore_append(
            list(self._current_domain_names),
            self._explore_page,
            self._on_explore_loaded,
            lambda msg: self._on_append_error(msg)
        )

    def _on_explore_loaded(self, data):
        self._remove_inline_loader()
        self._explore_btn.setEnabled(True)
        categories = data.get("categories", [])
        if not categories:
            return
        self._add_cards(categories)

    def _on_append_error(self, msg):
        self._remove_inline_loader()
        self._explore_btn.setEnabled(True)
        print(f"Append error: {msg}")

    def _on_error(self, msg):
        self._spinner.stop()
        self._load_lbl.setText(f"Error: {msg}"); self._load_frame.show()
