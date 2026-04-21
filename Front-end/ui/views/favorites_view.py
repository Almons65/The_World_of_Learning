from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QSizePolicy, QGridLayout, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPainter, QPixmap

from api_client import client
from ui.views.personal_hub_view import HubFavCard


def _empty_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(
        "color:rgba(229,226,225,0.20);font-size:14px;font-style:italic;"
        "border:1px dashed rgba(255,255,255,0.06);border-radius:6px;background:transparent;padding:40px;")
    return lbl

class FavoritesView(QWidget):
    video_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#0e0e0e;")
        self._username = ""
        self._favorites = []
        self._sort_asc = True
        self._search_query = ""
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 48, 48, 0)
        root.setSpacing(24)

        # ── Header ──────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(8)
        
        main_title = QLabel("FAVORITES")
        main_title.setStyleSheet("color:#ffffff;font-size:52px;font-weight:900;letter-spacing:-2px;background:transparent;")
        title_col.addWidget(main_title)

        sub_title = QLabel('"Collection of starred videos"')
        sub_title.setStyleSheet("color:rgba(255,255,255,0.4);font-size:14px;font-style:italic;background:transparent;")
        title_col.addWidget(sub_title)
        
        header_row.addLayout(title_col)
        header_row.addStretch()

        # Controls (Sort + Search)
        ctrl_lay = QHBoxLayout()
        ctrl_lay.setSpacing(12)
        
        self._sort_btn = QPushButton("↓ ALPHABETICAL: A-Z")
        self._sort_btn.setFixedHeight(36)
        self._sort_btn.setCursor(Qt.PointingHandCursor)
        self._sort_btn.setStyleSheet("""
            QPushButton{background:rgba(255,255,255,0.05);color:#ffffff;
                border:1px solid rgba(255,255,255,0.1);border-radius:6px;
                font-size:10px;font-weight:bold;letter-spacing:2px;padding:0 16px;}
            QPushButton:hover{background:rgba(255,255,255,0.1);}
        """)
        self._sort_btn.clicked.connect(self._toggle_sort)
        ctrl_lay.addWidget(self._sort_btn)

        self._search_input = QLineEdit()
        self._search_input.setFixedHeight(36)
        self._search_input.setPlaceholderText("Search archive...")
        self._search_input.setStyleSheet("""
            QLineEdit{background:rgba(255,255,255,0.05);color:#ffffff;
                border:1px solid rgba(255,255,255,0.1);border-radius:6px;
                font-size:12px;padding:0 12px;width:200px;}
            QLineEdit:focus{border-color:#f26411;}
        """)
        self._search_input.textChanged.connect(self._on_search)
        ctrl_lay.addWidget(self._search_input)

        header_row.addLayout(ctrl_lay)
        root.addLayout(header_row)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background:rgba(255,255,255,0.05);margin:20px 0;")
        root.addWidget(line)

        # ── Scroll Area for Grid ──────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        content_w = QWidget()
        content_w.setStyleSheet("background:transparent;")
        self._grid_lay = QGridLayout(content_w)
        self._grid_lay.setContentsMargins(0, 0, 0, 40)
        self._grid_lay.setSpacing(24)
        self._grid_lay.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll.setWidget(content_w)
        root.addWidget(scroll, 1)

    def load_data(self, username: str):
        self._username = username
        client.get_profile(self._on_profile, lambda e: print(f"Fav error: {e}"))

    def _on_profile(self, data: dict):
        self._favorites = data.get("favorites", [])
        self._render_grid()

    def _toggle_sort(self):
        self._sort_asc = not self._sort_asc
        label = "↓ ALPHABETICAL: A-Z" if self._sort_asc else "↑ ALPHABETICAL: Z-A"
        self._sort_btn.setText(label)
        self._render_grid()

    def _on_search(self, text: str):
        self._search_query = text.lower()
        self._render_grid()

    def _clear_grid(self):
        while self._grid_lay.count():
            item = self._grid_lay.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

    def _render_grid(self):
        self._clear_grid()
        
        filtered = self._favorites
        if self._search_query:
            filtered = [f for f in filtered if self._search_query in f.get("title", "").lower() 
                        or self._search_query in f.get("tag", "").lower()]
                        
        filtered = sorted(filtered, key=lambda x: x.get("title", "").lower(), reverse=not self._sort_asc)

        if not filtered:
            self._grid_lay.addWidget(_empty_label("No favorites found matching your query."), 0, 0)
            return

        cols = 4
        for i, v in enumerate(filtered):
            card = HubFavCard(v)
            card.clicked.connect(self.video_selected)
            card.removed.connect(self._on_favorite_removed)
            self._grid_lay.addWidget(card, i // cols, i % cols)

    def _on_favorite_removed(self, video_data: dict):
        slug = video_data.get("slug")
        if slug:
            client.remove_favorite(slug, lambda _: self.load_data(self._username), lambda e: print(f"Remove fav error: {e}"))
