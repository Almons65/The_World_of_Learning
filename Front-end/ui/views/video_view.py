from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser,
    QLineEdit, QPushButton, QScrollArea, QFrame, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QUrl, Signal, QRunnable, QThreadPool, QObject, QRectF
from PySide6.QtGui import QColor, QPixmap, QImage, QFont, QPainter, QPen, QLinearGradient
import requests

from api_client import client
from ui.components.video_player import VideoPlayerWidget
from image_cache import load_image


# ── Image loader (kept for RelatedCard; backed by shared cache) ──────────────
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


# ── Related Content Card ─────────────────────────────────────────────────────
class RelatedCard(QWidget):
    clicked = Signal(dict)

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(88)
        self._hovered = False

        self.setStyleSheet(
            "QWidget { background: rgba(30,30,30,0.3); border: 1px solid rgba(60,60,60,0.5); "
            "border-radius: 16px; }")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 8, 12, 8)
        lay.setSpacing(12)

        # Thumbnail with duration badge
        thumb_container = QWidget()
        thumb_container.setFixedSize(110, 70)
        thumb_container.setStyleSheet("background: transparent; border: none;")

        self._thumb = QLabel(thumb_container)
        self._thumb.setFixedSize(110, 70)
        self._thumb.setStyleSheet("background: #1a1a1a; border-radius: 10px; border: none;")
        self._thumb.setScaledContents(True)

        self._dur_badge = QLabel(thumb_container)
        self._dur_badge.setFixedSize(36, 18)
        self._dur_badge.move(70, 50)
        self._dur_badge.setAlignment(Qt.AlignCenter)
        self._dur_badge.setStyleSheet(
            "background: rgba(0,0,0,0.8); color: white; font-size: 9px; "
            "font-weight: bold; border-radius: 4px; border: none;")

        url = data.get("thumb", "")
        if url:
            load_image(url, self._set_img)

        dur = data.get("desc", "")
        self._dur_badge.setText(dur[:6] if dur else "")

        lay.addWidget(thumb_container)

        # Text
        info = QVBoxLayout(); info.setSpacing(4); info.setContentsMargins(0,4,0,4)
        title = data.get("title", "")
        tl = QLabel(title[:50] + ("..." if len(title) > 50 else ""))
        tl.setWordWrap(True)
        tl.setStyleSheet(
            "color: #e5e2e1; font-size: 12px; font-weight: bold; "
            "background: transparent; border: none;")
        self._title_lbl = tl

        creator = data.get("creator", "")
        cl = QLabel(creator[:25])
        cl.setStyleSheet("color: #737373; font-size: 10px; background: transparent; border: none;")
        info.addWidget(tl); info.addWidget(cl); info.addStretch()
        lay.addLayout(info, 1)

    def _set_img(self, pm: QPixmap):
        self._thumb.setPixmap(pm.scaled(
            110, 70, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))

    def enterEvent(self, e):
        self._hovered = True
        self.setStyleSheet(
            "QWidget { background: rgba(50,50,50,0.4); "
            "border: 1px solid rgba(242,100,17,0.3); border-radius: 16px; }")
        self._title_lbl.setStyleSheet(
            "color: #f26411; font-size: 12px; font-weight: bold; "
            "background: transparent; border: none;")
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.setStyleSheet(
            "QWidget { background: rgba(30,30,30,0.3); border: 1px solid rgba(60,60,60,0.5); "
            "border-radius: 16px; }")
        self._title_lbl.setStyleSheet(
            "color: #e5e2e1; font-size: 12px; font-weight: bold; "
            "background: transparent; border: none;")
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.clicked.emit(self.data)
        super().mousePressEvent(e)


# ── Pill action button ───────────────────────────────────────────────────────
class PillBtn(QPushButton):
    def __init__(self, svg_path, label, accent=False, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self._accent = accent
        self._svg_path = svg_path
        self._label = label
        self._hovered = False
        self._apply(False)

    def set_accent(self, is_accent):
        self._accent = is_accent
        self._apply(self._hovered)

    def set_label(self, label):
        self._label = label
        self.update()

    def _apply(self, hovered):
        self._hovered = hovered
        if self._accent:
            bg = "rgba(242,100,17,0.85)" if not hovered else "#f26411"
            self.setStyleSheet(
                f"QPushButton {{ background: {bg}; border: none; border-radius: 8px; }}")
        else:
            bg = "#151515" if not hovered else "#1e1e1e"
            self.setStyleSheet(
                f"QPushButton {{ background: {bg}; border: 1px solid #2a2a2a; border-radius: 8px; }}")
        self.update()

    def enterEvent(self, e): self._apply(True); super().enterEvent(e)
    def leaveEvent(self, e): self._apply(False); super().leaveEvent(e)
    
    def paintEvent(self, e):
        super().paintEvent(e)
        from PySide6.QtGui import QPainter, QColor, QFontMetrics, QFont
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtCore import QByteArray, QRectF
        
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        if self._accent:
            color = "#ffffff"
        else:
            color = "#f26411" if self._label == "ASK AI" else ("#ffffff" if self._hovered else "#a0a0a0")

        font = QFont()
        font.setPixelSize(11)
        font.setBold(True)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        p.setFont(font)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self._label)
        icon_size = 14
        spacing = 8
        total_w = icon_size + spacing + text_w
        
        start_x = (self.width() - total_w) / 2
        
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{icon_size}" height="{icon_size}" viewBox="0 0 24 24" 
                    fill="none" stroke="{color}" stroke-width="2" 
                    stroke-linecap="round" stroke-linejoin="round">'''
        path_filled = self._svg_path.replace("currentColor", color)
        svg += f"{path_filled}</svg>"
        
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        icon_rect = QRectF(start_x, (self.height() - icon_size) / 2, icon_size, icon_size)
        renderer.render(p, icon_rect)
        
        p.setPen(QColor(color))
        p.drawText(int(start_x + icon_size + spacing), int((self.height() + fm.ascent() - fm.descent()) / 2), self._label)

class SuggestionPill(QLabel):
    clicked = Signal()
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "QLabel { background: rgba(255,255,255,0.05); color: #cccccc; "
            "border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 10px 16px; font-size: 12px; text-align: right; }"
            "QLabel:hover { background: rgba(255,255,255,0.1); }")
    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self.clicked.emit()


# ── Chat bubble ──────────────────────────────────────────────────────────────
class ChatBubble(QWidget):
    link_clicked = Signal(str)
    
    def __init__(self, text, is_ai=True, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        
        if is_ai:
            from PySide6.QtSvgWidgets import QSvgWidget
            from PySide6.QtCore import QByteArray
            svg = '''<svg width="16" height="16" viewBox="0 0 24 24" fill="#f26411" stroke="none">
                <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
            </svg>'''
            icon_w = QSvgWidget()
            icon_w.load(QByteArray(svg.encode("utf-8")))
            icon_w.setFixedSize(16, 16)
            
            icon_container = QVBoxLayout()
            icon_container.addWidget(icon_w)
            icon_container.addStretch()
            lay.addLayout(icon_container)
            
            self.lbl = QLabel()
            self.lbl.setWordWrap(True)
            self.lbl.setOpenExternalLinks(False)
            self.lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
            self.lbl.linkActivated.connect(self.link_clicked.emit)
            self.lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            self.lbl.setStyleSheet("color: #cccccc; font-size: 13px; line-height: 1.5;")
            self.lbl.setMaximumWidth(290)
            
            import re
            def replace_time(match):
                time_str = match.group(1)
                parts = time_str.split(':')
                if len(parts) == 2:
                    seconds = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    seconds = 0
                return f'<a href="seek:{seconds}" style="color: #f26411; text-decoration: none; background-color: rgba(242,100,17,0.2);">&nbsp;{time_str}&nbsp;</a>'

            styled_text = re.sub(r'(\d{1,2}:\d{2}(?::\d{2})?)', replace_time, text)
            self.lbl.setTextFormat(Qt.MarkdownText)
            self.lbl.setText(styled_text)
            
            lay.addWidget(self.lbl)
            lay.addStretch()
        else:
            self.lbl = QLabel()
            self.lbl.setTextFormat(Qt.MarkdownText)
            self.lbl.setText(text)
            self.lbl.setWordWrap(True)
            self.lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            self.lbl.setMaximumWidth(270)
            self.lbl.setStyleSheet(
                "background: rgba(60,60,60,0.5); color: #e5e2e1; font-size: 13px; "
                "border-radius: 14px; border-top-right-radius: 4px; padding: 10px 14px;")
            
            lay.addStretch()
            lay.addWidget(self.lbl)


# ── Video View ───────────────────────────────────────────────────────────────
class VideoView(QWidget):
    back_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.video_data = None
        self._is_fav = False
        self._back_callback = None
        self._stream_gen = 0   # incremented each load_video(); guards stale callbacks
        self._setup_ui()

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ═══ LEFT: Player + Info ═════════════════════════════════════════
        left_scroll = QScrollArea()
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setWidgetResizable(True)
        left_scroll.setStyleSheet("QScrollArea { background: #0a0a0b; border: none; }")

        left_w = QWidget(); left_w.setStyleSheet("background: #0a0a0b;")
        lv = QVBoxLayout(left_w)
        lv.setContentsMargins(32, 24, 32, 40)
        lv.setSpacing(0)

        # Back button
        self._back_btn = QPushButton("← BACK TO SUB-FOLDER")
        self._back_btn.setFixedSize(170, 34)
        self._back_btn.setCursor(Qt.PointingHandCursor)
        self._back_btn.setStyleSheet(
            "QPushButton { background: rgba(30,30,30,0.9); color: #e5e2e1; "
            "border: 1px solid #3a3a3a; border-radius: 17px; font-size: 11px; "
            "font-weight: bold; letter-spacing: 1px; }"
            "QPushButton:hover { border-color: #f26411; color: #f26411; }")
        self._back_btn.clicked.connect(self._on_back)
        lv.addWidget(self._back_btn, 0, Qt.AlignLeft)
        lv.addSpacing(16)

        # Video player container (rounded, dark)
        player_frame = QFrame()
        player_frame.setStyleSheet(
            "QFrame { background: #111; border: 1px solid rgba(60,60,60,0.3); border-radius: 20px; }")
        pfl = QVBoxLayout(player_frame)
        pfl.setContentsMargins(0, 0, 0, 0)
        pfl.setSpacing(0)

        # Native video player (replaces QWebEngineView)
        self._player = VideoPlayerWidget()
        self._player.playback_error.connect(self._on_player_error)
        pfl.addWidget(self._player)

        # Error label (hidden by default)
        self._error_lbl = QLabel()
        self._error_lbl.setWordWrap(True)
        self._error_lbl.setAlignment(Qt.AlignCenter)
        self._error_lbl.setStyleSheet(
            "color: #ff6b6b; font-size: 12px; background: rgba(255,80,80,0.08); "
            "border: 1px solid rgba(255,80,80,0.2); border-radius: 10px; padding: 12px;")
        self._error_lbl.hide()
        pfl.addWidget(self._error_lbl)

        lv.addWidget(player_frame)
        lv.addSpacing(24)

        # Title + metadata + action buttons row inside a Card
        info_card = QFrame()
        info_card.setStyleSheet("QFrame { background: #181818; border-radius: 20px; }")
        
        info_row = QHBoxLayout(info_card)
        info_row.setSpacing(40)
        info_row.setContentsMargins(40, 40, 40, 40)

        # Title block (left)
        title_col = QVBoxLayout(); title_col.setSpacing(16)
        title_col.setAlignment(Qt.AlignTop)
        self._title_lbl = QLabel()
        self._title_lbl.setWordWrap(True)
        self._title_lbl.setStyleSheet(
            "color: #ffffff; font-size: 38px; font-weight: 900; background: transparent; line-height: 1.2;")
        title_col.addWidget(self._title_lbl)

        self._desc_lbl = QLabel()
        self._desc_lbl.setWordWrap(True)
        self._desc_lbl.setStyleSheet(
            "color: #888888; font-size: 15px; line-height: 1.6; background: transparent;")
        title_col.addWidget(self._desc_lbl)
        title_col.addStretch()
        info_row.addLayout(title_col, 1)

        # Metadata Card (right)
        meta_col = QVBoxLayout(); meta_col.setSpacing(20)
        meta_col.setAlignment(Qt.AlignTop)

        stats_row = QHBoxLayout()
        views_col = QVBoxLayout(); views_col.setSpacing(4)
        v_lbl = QLabel("VIEWS"); v_lbl.setStyleSheet("color: #666; font-size: 9px; font-weight: bold; letter-spacing: 1px; background: transparent;")
        self._views_val = QLabel("Unknown")
        self._views_val.setStyleSheet("color: #fff; font-size: 13px; font-weight: bold; background: transparent;")
        views_col.addWidget(v_lbl); views_col.addWidget(self._views_val)

        date_col = QVBoxLayout(); date_col.setSpacing(4)
        d_lbl = QLabel("UPLOAD DATE"); d_lbl.setStyleSheet("color: #666; font-size: 9px; font-weight: bold; letter-spacing: 1px; background: transparent;")
        self._date_val = QLabel("Unknown")
        self._date_val.setStyleSheet("color: #fff; font-size: 13px; font-weight: bold; background: transparent;")
        date_col.addWidget(d_lbl); date_col.addWidget(self._date_val)

        stats_row.addLayout(views_col)
        stats_row.addSpacing(40)
        stats_row.addLayout(date_col)
        stats_row.addStretch()
        meta_col.addLayout(stats_row)

        creator_col = QVBoxLayout(); creator_col.setSpacing(4)
        c_lbl = QLabel("CREATOR"); c_lbl.setStyleSheet("color: #666; font-size: 9px; font-weight: bold; letter-spacing: 1px; background: transparent;")
        self._creator_val = QLabel("● Unknown")
        self._creator_val.setStyleSheet("color: #f26411; font-size: 12px; font-weight: bold; background: transparent;")
        creator_col.addWidget(c_lbl); creator_col.addWidget(self._creator_val)
        meta_col.addLayout(creator_col)
        
        # Horizontal separator
        hline = QFrame()
        hline.setFrameShape(QFrame.HLine)
        hline.setStyleSheet("background: rgba(255,255,255,0.05);")
        meta_col.addWidget(hline)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        
        self._fav_btn    = PillBtn('<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" fill="currentColor" stroke="none"/>', "FAVORITES", accent=False)
        self._folder_btn = PillBtn('<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/><line x1="12" y1="10" x2="12" y2="16"/><line x1="9" y1="13" x2="15" y2="13"/>', "ADD TO FOLDER")
        self._fav_btn.clicked.connect(self._on_fav)
        self._folder_btn.clicked.connect(self._on_add_folder)
        self._fav_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._folder_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        btn_row.addWidget(self._fav_btn)
        btn_row.addWidget(self._folder_btn)
        
        meta_col.addLayout(btn_row)

        self._ask_btn    = PillBtn('<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" fill="currentColor" stroke="none"/>', "ASK AI")
        self._ask_btn.clicked.connect(self._on_ask_ai)
        self._ask_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self._download_btn = PillBtn('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>', "DOWNLOAD")
        self._download_btn.clicked.connect(self._on_download)
        self._download_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(12)
        btn_row2.addWidget(self._ask_btn)
        btn_row2.addWidget(self._download_btn)
        meta_col.addLayout(btn_row2)
        
        # Fixed width for the metadata column
        meta_col_w = QWidget()
        meta_col_w.setStyleSheet("background: transparent;")
        meta_col_w.setLayout(meta_col)
        meta_col_w.setFixedWidth(340)
        info_row.addWidget(meta_col_w)

        lv.addWidget(info_card)
        lv.addStretch()

        left_scroll.setWidget(left_w)

        # ═══ RIGHT: Related Content ══════════════════════════════════════
        right_w = QWidget()
        right_w.setFixedWidth(420)
        right_w.setStyleSheet("background: #0d0d0e; border-left: 1px solid rgba(60,60,60,0.3);")
        rv = QVBoxLayout(right_w)
        rv.setContentsMargins(20, 24, 20, 16)
        rv.setSpacing(0)

        # Related Content header
        rel_hdr_row = QHBoxLayout()
        rel_hdr = QLabel("RELATED VIDEO")
        rel_hdr.setStyleSheet("color: #e5e2e1; font-size: 10px; font-weight: bold; letter-spacing: 2px;")
        rel_hdr_sub = QLabel("GLOBAL ARCHIVE BRANCH")
        rel_hdr_sub.setStyleSheet("color: rgba(255,255,255,0.3); font-size: 9px; font-weight: bold; letter-spacing: 1px;")
        rel_hdr_row.addWidget(rel_hdr)
        rel_hdr_row.addStretch()
        rel_hdr_row.addWidget(rel_hdr_sub)
        
        rv.addLayout(rel_hdr_row)
        rv.addSpacing(16)

        # Related scroll area
        rel_scroll = QScrollArea()
        rel_scroll.setFrameShape(QFrame.NoFrame)
        rel_scroll.setWidgetResizable(True)
        rel_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._rel_widget = QWidget()
        self._rel_widget.setStyleSheet("background: transparent;")
        self._rel_layout = QVBoxLayout(self._rel_widget)
        self._rel_layout.setContentsMargins(0, 0, 0, 0)
        self._rel_layout.setSpacing(12)
        self._rel_layout.addStretch()
        rel_scroll.setWidget(self._rel_widget)
        rv.addWidget(rel_scroll)

        # ═══ FAR RIGHT: Chat Panel (Hidden by default) ════════════════════════
        self._chat_w = QWidget()
        self._chat_w.setFixedWidth(360)
        self._chat_w.setStyleSheet("background: #111111; border-left: 1px solid rgba(60,60,60,0.3);")
        self._chat_w.hide()
        
        cw = QVBoxLayout(self._chat_w)
        cw.setContentsMargins(16, 24, 16, 16)
        cw.setSpacing(0)
        
        chat_hdr_row = QHBoxLayout()
        chat_hdr = QLabel("✦ ASK ABOUT THIS VIDEO")
        chat_hdr.setStyleSheet("color: #e5e2e1; font-size: 10px; font-weight: bold; letter-spacing: 2px;")
        
        self._close_chat_btn = QPushButton("✕")
        self._close_chat_btn.setFixedSize(24, 24)
        self._close_chat_btn.setCursor(Qt.PointingHandCursor)
        self._close_chat_btn.setStyleSheet("QPushButton { color: #888; background: transparent; border: none; font-size: 14px; } QPushButton:hover { color: #fff; }")
        self._close_chat_btn.clicked.connect(self._chat_w.hide)
        
        chat_hdr_row.addWidget(chat_hdr)
        chat_hdr_row.addStretch()
        chat_hdr_row.addWidget(self._close_chat_btn)
        cw.addLayout(chat_hdr_row)
        cw.addSpacing(20)
        
        intro_lbl = QLabel("Curious about what you're watching? I'm here to help.")
        intro_lbl.setWordWrap(True)
        intro_lbl.setStyleSheet("color: #888; font-size: 12px;")
        cw.addWidget(intro_lbl)
        cw.addSpacing(20)

        # Chat scroll
        self._chat_scroll = QScrollArea()
        self._chat_scroll.setFrameShape(QFrame.NoFrame)
        self._chat_scroll.setWidgetResizable(True)
        self._chat_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._chat_widget = QWidget()
        self._chat_widget.setStyleSheet("background: transparent;")
        self._chat_layout = QVBoxLayout(self._chat_widget)
        self._chat_layout.setContentsMargins(0, 0, 0, 0)
        self._chat_layout.setSpacing(8)
        self._chat_layout.addStretch()
        self._chat_scroll.setWidget(self._chat_widget)
        cw.addWidget(self._chat_scroll, 1)
        cw.addSpacing(16)

        # Input row
        inp_frame = QWidget()
        inp_frame.setStyleSheet("background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 12px;")
        inp_row = QHBoxLayout(inp_frame)
        inp_row.setContentsMargins(12, 8, 12, 8)
        inp_row.setSpacing(8)

        self._chat_input = QLineEdit()
        self._chat_input.setPlaceholderText("Ask a question...")
        self._chat_input.setStyleSheet("QLineEdit { background: transparent; border: none; color: #e5e2e1; font-size: 12px; }")
        self._chat_input.returnPressed.connect(self._send_chat)

        self._send_btn = QPushButton("➤")
        self._send_btn.setFixedSize(24, 24)
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #888; border: none; font-size: 14px; }"
            "QPushButton:hover { color: #f26411; }")
        self._send_btn.clicked.connect(self._send_chat)

        inp_row.addWidget(self._chat_input, 1)
        inp_row.addWidget(self._send_btn)
        cw.addWidget(inp_frame)

        root.addWidget(left_scroll, 1)
        root.addWidget(right_w)
        root.addWidget(self._chat_w)

    def hideEvent(self, e):
        if hasattr(self, "_player"):
            self._player.pause()
        super().hideEvent(e)

    # ── Public API ────────────────────────────────────────────────────────
    def set_back_target(self, label: str, callback):
        """Override where the back button goes and its label."""
        self._back_callback = callback
        self._back_btn.setText(f"← {label}")

    def load_video(self, video_data: dict):
        self.video_data = video_data
        # Reset button states
        self._is_fav = False
        self._fav_btn.set_label("FAVORITES")
        self._fav_btn.set_accent(False)
        self._folder_btn.set_label("ADD TO FOLDER")
        self._folder_btn.set_accent(False)
        self._error_lbl.hide()

        # Check if already in favorites
        def on_profile(data):
            if not self.video_data: return
            slug = self.video_data.get("slug")
            favs = data.get("favorites", [])
            if any(f.get("slug") == slug for f in favs):
                self._is_fav = True
                self._fav_btn.set_label("FAVORITED")
                self._fav_btn.set_accent(True)
        client.get_profile(on_profile, lambda e: None)

        # Stop any previous playback
        self._player.stop()
        self._stream_gen += 1
        gen = self._stream_gen

        slug = video_data.get("slug", "")
        if slug:
            client.get_stream_url(
                slug,
                self._player.current_resolution(),
                lambda d, g=gen: self._on_stream_url(d, g),
                self._on_stream_err)

        self._views_val.setText(video_data.get("views", "Unknown"))
        
        # Format date to "day, month,year" and handle Thai localization string
        raw_date = video_data.get("date", "Unknown")
        import re, datetime
        dm = re.search(r'(\d+)\s*(y|year|mo|month|w|week|d|day|h|hour|ปี|เดือน|สัปดาห์|วัน|ชั่วโมง)s?\s*(ago|ที่ผ่านมา)?', raw_date, re.IGNORECASE)
        if dm:
            n2, u2 = int(dm.group(1)), dm.group(2).lower()
            now2 = datetime.datetime.now()
            if u2 in ['ปี', 'y', 'year']: now2 -= datetime.timedelta(days=n2*365)
            elif u2 in ['เดือน', 'mo', 'month']: now2 -= datetime.timedelta(days=n2*30)
            elif u2 in ['สัปดาห์', 'w', 'week']: now2 -= datetime.timedelta(days=n2*7)
            elif u2 in ['วัน', 'd', 'day']: now2 -= datetime.timedelta(days=n2)
            raw_date = now2.strftime("%d, %B, %Y")
        
        self._date_val.setText(raw_date)
        self._creator_val.setText(f"● {video_data.get('creator', 'Unknown')}")

        title = video_data.get("title", "Unknown Title")
        self._title_lbl.setText(title)
        
        # Format description to look like a summary
        desc_text = (f"An exclusive presentation of '{title}'. "
                     f"This video provides unique insights and captivating visuals, "
                     f"contributing significantly to our expansive historical archive.")
        self._desc_lbl.setText(desc_text)

        # Chat
        self._clear_chat()
        client.video_suggest(title, video_data.get("desc", ""),
                             self._on_suggest, self._on_suggest_err)

        self._clear_related()
        # Fetch related videos
        client.get_related_videos(title, video_data.get("slug", ""), self._on_related_loaded, lambda err: print(f"Related err: {err}"))

        # ── Auto-track watch history ──────────────────────────────────────
        client.add_history(video_data, lambda _: None, lambda e: print(f"History track err: {e}"))


    def _on_related_loaded(self, data):
        videos = data.get("videos", [])
        self.add_related(videos)

    def _on_stream_url(self, data, gen: int):
        """Received stream URL — ignore if a newer load_video() has started."""
        if gen != self._stream_gen:
            return
        url = data.get("stream_url", "")
        if url:
            self._player.play_url(url)
        else:
            self._on_stream_err("No stream URL returned")

    def _on_stream_err(self, err):
        """Failed to get stream URL."""
        self._error_lbl.setText(f"⚠ Could not load video stream: {err}")
        self._error_lbl.show()

    def _on_player_error(self, err):
        """Native player reported an error."""
        self._error_lbl.setText(f"⚠ Playback error: {err}")
        self._error_lbl.show()

    def _on_back(self):
        self._player.stop()
        if self._back_callback:
            self._back_callback()
        else:
            self.back_clicked.emit()

    def _clear_related(self):
        while self._rel_layout.count() > 1:
            item = self._rel_layout.takeAt(0)
            if item.widget(): item.widget().setParent(None)

    def _on_download(self):
        slug = self.video_data.get("slug")
        if not slug: return
        
        from PySide6.QtWidgets import QFileDialog
        import re
        title = self.video_data.get("title", "video")
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Video", f"{safe_title}.mp4", "Video Files (*.mp4)")
        if not save_path: return

        self._download_btn.set_label("DOWNLOADING...")
        self._download_btn.setEnabled(False)
        
        def on_done(data):
            self._download_btn.set_label("DOWNLOADED")
            self._download_btn.set_accent(True)
            
        def on_err(err):
            self._download_btn.set_label("DOWNLOAD")
            self._download_btn.setEnabled(True)
            print(f"Download error: {err}")

        client.download_video(slug, on_done, on_err, save_path=save_path)

    def add_related(self, videos: list):
        self._clear_related()
        for v in videos[:8]:
            if v.get("slug") == self.video_data.get("slug"):
                continue
            card = RelatedCard(v)
            card.clicked.connect(self.load_video)
            self._rel_layout.insertWidget(self._rel_layout.count() - 1, card)

    # ── Chat ──────────────────────────────────────────────────────────────
    def _clear_chat(self):
        while self._chat_layout.count() > 1:
            item = self._chat_layout.takeAt(0)
            if item.widget(): item.widget().setParent(None)

    def _add_bubble(self, text, is_ai):
        bubble = ChatBubble(text, is_ai)
        if is_ai:
            bubble.link_clicked.connect(self._on_timestamp_clicked)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, bubble)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._chat_scroll.verticalScrollBar().setValue(
            self._chat_scroll.verticalScrollBar().maximum()))

    def _on_timestamp_clicked(self, url):
        if url.startswith("seek:"):
            try:
                seconds = int(url.split(":")[1])
                self._player.seek_to(seconds * 1000)
            except ValueError:
                pass

    def _on_suggest(self, data):
        qs = data.get("questions", [
            "Summarize this video",
            "Recommend related content",
            "What *actually* caused so many civilizations to fall?",
            "Were common people aware of the chaos happening?",
            "Could something like this happen again today?"
        ])
        
        lbl = QLabel("NOT SURE WHAT TO ASK? CHOOSE SOMETHING:")
        lbl.setStyleSheet("color: #666; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, lbl, 0, Qt.AlignLeft)
        
        for q in qs:
            q_display = q[:65] + "..." if len(q) > 65 else q
            btn = SuggestionPill(q_display)
            btn.clicked.connect(lambda text=q: self._send_text(text))
            
            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(0, 0, 0, 0)
            l.addStretch()
            l.addWidget(btn)
            self._chat_layout.insertWidget(self._chat_layout.count() - 1, w)

    def _on_suggest_err(self, _):
        self._add_bubble("I couldn't load suggestions right now. Feel free to ask anything!", True)

    def _send_text(self, msg):
        self._add_bubble(msg, False)
        self._chat_input.clear()
        self._chat_input.setEnabled(False)
        self._send_btn.setEnabled(False)
        
        for i in range(self._chat_layout.count()):
            item = self._chat_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), SuggestionPill):
                item.widget().setEnabled(False)
                
        # Add loading bubble
        self._loading_bubble = ChatBubble("Analyzing...", True)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, self._loading_bubble)
        
        dur_str = self._player._dur_lbl.text() if hasattr(self._player, "_dur_lbl") else "14:00"
        video_id = self.video_data.get("slug", "unknown")
        title = self.video_data.get("title", "Unknown Video")
        desc = self.video_data.get("desc", "")
        
        client.video_chat(video_id, title, desc, dur_str, msg, self._on_reply, self._on_reply_err)

    def _send_chat(self):
        msg = self._chat_input.text().strip()
        if not msg: return
        self._send_text(msg)

    def _on_reply(self, data):
        if hasattr(self, "_loading_bubble") and self._loading_bubble:
            self._loading_bubble.setParent(None)
            self._loading_bubble = None
            
        self._chat_input.setEnabled(True); self._send_btn.setEnabled(True)
        reply = data.get("reply", "")
        self._add_bubble(reply, True)

    def _on_reply_err(self, err):
        if hasattr(self, "_loading_bubble") and self._loading_bubble:
            self._loading_bubble.setParent(None)
            self._loading_bubble = None
            
        self._chat_input.setEnabled(True); self._send_btn.setEnabled(True)
        self._add_bubble(f"Error: {err}", True)

    # ── Button handlers ───────────────────────────────────────────────────
    def _on_fav(self):
        if not self.video_data: return
        if self._is_fav:
            slug = self.video_data.get("slug", "")
            if slug: client.remove_favorite(slug, lambda _: None, lambda _: None)
            self._is_fav = False
            self._fav_btn.set_label("FAVORITES")
            self._fav_btn.set_accent(False)
        else:
            client.add_favorite(self.video_data, lambda _: None, lambda _: None)
            self._is_fav = True
            self._fav_btn.set_label("FAVORITED")
            self._fav_btn.set_accent(True)

    def _on_add_folder(self):
        if not self.video_data: return
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QScrollArea, QWidget, QLabel
        from ui.folder_store import get_user_folders, save_user_folders
        from ui.views.folders_view import CreateFolderDialog
        import uuid, datetime

        class PickFolderDialog(QDialog):
            def __init__(self, username, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Add to Folder")
                self.setFixedSize(300, 400)
                self.setStyleSheet("QDialog{background:#1c1b1b;} QPushButton{background:#131313;color:#e5e2e1;border:1px solid #353534;border-radius:6px;padding:12px;font-weight:bold;text-align:left;} QPushButton:hover{border-color:#f26411;color:#f26411;}")
                self.selected_folder = None
                self.username = username
                
                lay = QVBoxLayout(self)
                title = QLabel("Select Folder")
                title.setStyleSheet("color:#fff;font-size:16px;font-weight:bold;")
                lay.addWidget(title)
                
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
                
                content = QWidget()
                content.setStyleSheet("background:transparent;")
                self.list_lay = QVBoxLayout(content)
                
                self.folders = get_user_folders(self.username)
                
                create_btn = QPushButton("+ Create New Folder")
                create_btn.setStyleSheet("QPushButton{background:rgba(242,100,17,0.1);color:#f26411;border:1px dashed #f26411;border-radius:6px;padding:12px;font-weight:bold;} QPushButton:hover{background:rgba(242,100,17,0.2);}")
                create_btn.clicked.connect(self._create_new)
                self.list_lay.addWidget(create_btn)
                
                for f in self.folders:
                    btn = QPushButton(f.get("name", "Folder"))
                    btn.clicked.connect(lambda _, fd=f: self._select(fd))
                    self.list_lay.addWidget(btn)
                    
                self.list_lay.addStretch()
                scroll.setWidget(content)
                lay.addWidget(scroll)

            def _select(self, fd):
                self.selected_folder = fd
                self.accept()

            def _create_new(self):
                dlg = CreateFolderDialog(self)
                if dlg.exec():
                    data = dlg.get_data()
                    if data["name"]:
                        new_f = {
                            "id": str(uuid.uuid4())[:8],
                            "name": data["name"],
                            "domain": data["name"].upper(),
                            "folder_slug": data["name"].lower().replace(" ", "-"),
                            "color": data["color"],
                            "updated": datetime.datetime.now().strftime("%B %d, %Y").upper(),
                            "hero_img": data["hero_img"],
                            "items": []
                        }
                        self.folders.append(new_f)
                        save_user_folders(self.username, self.folders)
                        self.selected_folder = new_f
                        self.accept()

        dlg = PickFolderDialog(client.current_username or "", self)
        if dlg.exec():
            # Add video to the selected folder
            f = dlg.selected_folder
            if f:
                folders = get_user_folders(client.current_username or "")
                for x in folders:
                    if x["id"] == f["id"]:
                        # Avoid duplicates
                        if not any(v.get("slug") == self.video_data.get("slug") for v in x.get("items", [])):
                            x.setdefault("items", []).append(self.video_data)
                        break
                save_user_folders(client.current_username or "", folders)
                self._folder_btn.set_label("ADDED!")

    def _on_ask_ai(self):
        self._chat_w.show()
        self._chat_input.setFocus()
