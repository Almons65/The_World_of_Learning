from PySide6.QtWidgets import (
    QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGraphicsOpacityEffect, QGraphicsProxyWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .views.login_view import LoginView
from .views.dashboard_view import DashboardView
from .views.video_view import VideoView
from .views.onboarding_view import OnboardingView
from .views.domain_view import DomainView
from .views.subfolder_view import SubfolderView
from .views.personal_hub_view import PersonalHubView
from .views.history_view import HistoryView
from .views.favorites_view import FavoritesView
from api_client import client


NAV_ITEMS = [
    ("Home",      '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>'),
    ("Personal",  '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>'),
    ("History",   '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>'),
    ("Favorites", '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>'),
    ("Folders",   '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>'),
]

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QRect, QEvent, QObject, QPoint, QParallelAnimationGroup
from PySide6.QtGui import QCursor

class SvgIcon(QWidget):
    def __init__(self, path_data, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.path_data = path_data
        self.color = "#737373"

    def set_color(self, color):
        self.color = color
        self.update()

    def paintEvent(self, e):
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtCore import QByteArray
        from PySide6.QtGui import QPainter
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" 
                    fill="none" stroke="{self.color}" stroke-width="2" 
                    stroke-linecap="round" stroke-linejoin="round">{self.path_data}</svg>'''
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        renderer.render(p)


class SidebarButton(QPushButton):
    def __init__(self, label, svg_path):
        super().__init__()
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self._label = label

        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 0, 16, 0)
        lay.setSpacing(16)

        self._icon = SvgIcon(svg_path)

        self._txt = QLabel(label)
        self._txt.setFixedWidth(120)
        self._txt.hide()

        lay.addWidget(self._icon)
        lay.addWidget(self._txt)
        lay.addStretch()

        self.setFixedHeight(48)
        self.toggled.connect(self._refresh)
        self._refresh(False)

    def set_expanded(self, expanded):
        self._txt.setVisible(expanded)
        self.setToolTip("" if expanded else self._label)

    def _refresh(self, checked):
        if checked:
            self.setStyleSheet(
                "QPushButton { background: rgba(242,100,17,0.12); border: none; border-radius: 12px; }")
            self._icon.set_color("#f26411")
            self._txt.setStyleSheet("color: #f26411; font-size: 14px; font-weight: bold; background: transparent;")
        else:
            self.setStyleSheet(
                "QPushButton { background: transparent; border: none; border-radius: 12px; }"
                "QPushButton:hover { background: #1e1e1e; }")
            self._icon.set_color("#737373")
            self._txt.setStyleSheet("color: #a0a0a0; font-size: 14px; font-weight: bold; background: transparent;")

class CollapsibleSidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setStyleSheet("QFrame#sidebar { background: #181818; border-right: 1px solid #2a2a2a; }")
        
        self.setFixedWidth(64)
        self.is_pinned = False
        
        self._anim = QPropertyAnimation(self, b"minimumWidth")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self.setFixedWidth)

    def set_open(self, open_state):
        self._anim.stop()
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(220 if open_state else 64)
        self._anim.start()
        
        for btn in self.findChildren(SidebarButton):
            btn.set_expanded(open_state)
            
        if hasattr(self, '_b_name'):
            self._b_name.setVisible(open_state)

    def enterEvent(self, e):
        if not self.is_pinned:
            self.set_open(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not self.is_pinned:
            self.set_open(False)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if not self.is_pinned:
                self.is_pinned = True
                self.set_open(True)
        super().mousePressEvent(e)

    def unpin(self):
        self.is_pinned = False
        if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            self.set_open(False)

class SlidingStackedWidget(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration = 400
        self._easing = QEasingCurve.OutCubic
        self._is_animating = False
        
    def setCurrentWidget(self, next_widget):
        if self.currentIndex() == -1 or self._is_animating:
            super().setCurrentWidget(next_widget)
            return

        current_widget = self.currentWidget()
        if current_widget == next_widget:
            return

        self._is_animating = True
        
        # 1. Grab snapshot of current state
        w, h = self.width(), self.height()
        pix = current_widget.grab()
        
        # 2. Create overlay for the old widget
        overlay = QLabel(self)
        overlay.setPixmap(pix)
        overlay.setGeometry(0, 0, w, h)
        overlay.show()
        overlay.raise_()

        # 3. Switch the actual stack to the new widget immediately
        super().setCurrentWidget(next_widget)
        next_widget.show()
        
        # 4. Animate the overlay fading and sliding out
        eff = QGraphicsOpacityEffect(overlay)
        overlay.setGraphicsEffect(eff)
        
        group = QParallelAnimationGroup(self)
        
        # Fade out overlay
        fade = QPropertyAnimation(eff, b"opacity", group)
        fade.setDuration(self._duration)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(self._easing)
        
        # Slide overlay slightly (parallax)
        idx_now = self.indexOf(current_widget)
        idx_next = self.indexOf(next_widget)
        is_forward = idx_next > idx_now
        
        slide = QPropertyAnimation(overlay, b"pos", group)
        slide.setDuration(self._duration)
        slide.setStartValue(QPoint(0, 0))
        slide.setEndValue(QPoint(-int(w*0.2), 0) if is_forward else QPoint(int(w*0.2), 0))
        slide.setEasingCurve(self._easing)

        def finish():
            overlay.deleteLater()
            self._is_animating = False
            group.deleteLater()

        group.finished.connect(finish)
        group.start()





class GlobalClickFilter(QObject):
    def __init__(self, sidebar):
        super().__init__()
        self.sidebar = sidebar

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if self.sidebar.is_pinned:
                sidebar_rect = self.sidebar.rect()
                global_pos = QCursor.pos()
                sidebar_global_rect = QRect(self.sidebar.mapToGlobal(sidebar_rect.topLeft()), self.sidebar.mapToGlobal(sidebar_rect.bottomRight()))
                if not sidebar_global_rect.contains(global_pos):
                    self.sidebar.unpin()
        return False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("The World of Learning")
        self.resize(1280, 720)

        root = QWidget()
        self.setCentralWidget(root)
        ml = QHBoxLayout(root)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        self._setup_sidebar()

        self.stack = SlidingStackedWidget()

        # Views
        self.login_view = LoginView()
        self.login_view.login_successful.connect(self.show_dashboard)
        self.login_view.needs_onboarding.connect(self.show_onboarding)

        self.onboarding_view = OnboardingView()
        self.onboarding_view.interests_saved.connect(self.show_dashboard)

        self.dashboard_view = DashboardView()
        self.dashboard_view.domain_selected.connect(self.show_domain)

        self.domain_view = DomainView()
        self.domain_view.return_clicked.connect(self.show_dashboard_no_reload)
        self.domain_view.subfolder_selected.connect(self.show_subfolder)

        self.subfolder_view = SubfolderView()
        self.subfolder_view.return_clicked.connect(self._back_to_domain)
        self.subfolder_view.video_selected.connect(self.show_video)

        self.video_view = VideoView()
        self.video_view.back_clicked.connect(self._back_to_subfolder)

        self.personal_hub_view = PersonalHubView()
        self.personal_hub_view.video_selected.connect(self.show_video_from_hub)
        self.personal_hub_view.folder_selected.connect(self.show_personal_folder)
        self.personal_hub_view.view_all_history.connect(self.show_history)
        self.personal_hub_view.view_all_favorites.connect(self.show_favorites)
        self.personal_hub_view.manage_folders.connect(self.show_folders)

        self.history_view = HistoryView()
        self.history_view.video_selected.connect(self.show_video_from_history)

        self.favorites_view = FavoritesView()
        self.favorites_view.video_selected.connect(self.show_video_from_favorites)

        from .views.folders_view import FoldersView
        from .views.personal_folder_view import PersonalFolderView
        self.folders_view = FoldersView()
        self.folders_view.folder_selected.connect(self.show_personal_folder)
        
        self.personal_folder_view = PersonalFolderView()
        self.personal_folder_view.video_selected.connect(self.show_video_from_folder)
        self.personal_folder_view.back_clicked.connect(self.show_folders)

        for v in [self.login_view, self.onboarding_view, self.dashboard_view,
                  self.domain_view, self.subfolder_view, self.video_view,
                  self.personal_hub_view, self.history_view, self.favorites_view,
                  self.folders_view, self.personal_folder_view]:
            self.stack.addWidget(v)

        ml.addWidget(self.sidebar)
        ml.addWidget(self.stack, 1)

        self.sidebar.hide()
        # Set initial without animation
        QStackedWidget.setCurrentWidget(self.stack, self.login_view)

        self._current_domain    = None
        self._current_subfolder = None

        from PySide6.QtWidgets import QApplication
        self._global_click_filter = GlobalClickFilter(self.sidebar)
        QApplication.instance().installEventFilter(self._global_click_filter)

    def _setup_sidebar(self):
        self.sidebar = CollapsibleSidebar(self.centralWidget())
        self.sidebar._b_name = QLabel("The World of Learning")

        sl = QVBoxLayout(self.sidebar)
        sl.setContentsMargins(8, 20, 8, 20)
        sl.setSpacing(8)

        # Brand
        brand = QHBoxLayout(); brand.setContentsMargins(12, 0, 0, 0); brand.setSpacing(16)
        
        from PySide6.QtGui import QPixmap
        import os
        
        b_icon = QLabel()
        icon_path = os.path.join(os.path.dirname(__file__), "..", "imgs", "icon.png")
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            b_icon.setPixmap(pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        b_icon.setFixedSize(24, 24)
        
        self.sidebar._b_name.setStyleSheet("color: #e5e2e1; font-size: 13px; font-weight: bold;")
        self.sidebar._b_name.setWordWrap(False)
        self.sidebar._b_name.hide()
        
        brand.addWidget(b_icon)
        brand.addWidget(self.sidebar._b_name, 1)
        sl.addLayout(brand)
        sl.addSpacing(32)

        self._nav_btns: list[SidebarButton] = []
        for label, icon in NAV_ITEMS:
            btn = SidebarButton(label, icon)
            if label == "Home":
                btn.clicked.connect(self.show_dashboard)
            elif label == "Personal":
                btn.clicked.connect(self.show_personal)
            elif label == "History":
                btn.clicked.connect(self.show_history)
            elif label == "Favorites":
                btn.clicked.connect(self.show_favorites)
            elif label == "Folders":
                btn.clicked.connect(self.show_folders)
            self._nav_btns.append(btn)
            sl.addWidget(btn)

        sl.addStretch()

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("border: none; border-top: 1px solid #2a2a2a; margin: 4px 8px;")
        sep.setFixedHeight(1)
        sl.addWidget(sep)

        self.logout_btn = SidebarButton("Logout", '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>')
        self.logout_btn._icon.set_color("#c0392b")
        self.logout_btn._txt.setStyleSheet("color: #c0392b; font-size: 14px; font-weight: bold; background: transparent;")
        self.logout_btn.clicked.connect(self.show_login)
        sl.addWidget(self.logout_btn)

    def _set_active(self, label):
        for btn in self._nav_btns:
            btn.setChecked(btn._label == label)

    # ── Navigation ────────────────────────────────────────────────────────
    def show_onboarding(self):
        self.sidebar.hide()
        self.stack.setCurrentWidget(self.onboarding_view)

    def show_dashboard(self):
        self.sidebar.show()
        self._set_active("Home")
        self.stack.setCurrentWidget(self.dashboard_view)
        self.dashboard_view.load_data()

    def show_personal(self):
        self.sidebar.show()
        self._set_active("Personal")
        self.stack.setCurrentWidget(self.personal_hub_view)
        self.personal_hub_view.load_data(client.current_username or "")

    def show_history(self):
        self.sidebar.show()
        self._set_active("History")
        self.stack.setCurrentWidget(self.history_view)
        self.history_view.load_data()

    def show_favorites(self):
        self.sidebar.show()
        self._set_active("Favorites")
        self.stack.setCurrentWidget(self.favorites_view)
        self.favorites_view.load_data(client.current_username or "")

    def show_folders(self):
        self.sidebar.show()
        self._set_active("Folders")
        self.stack.setCurrentWidget(self.folders_view)
        self.folders_view.load_data(client.current_username or "")

    def show_personal_folder(self, folder_data: dict):
        self.sidebar.show()
        self._set_active("Folders")
        self.stack.setCurrentWidget(self.personal_folder_view)
        self.personal_folder_view.load_data(client.current_username or "", folder_data["id"])

    def show_dashboard_no_reload(self):
        """Go back to dashboard without re-fetching data."""
        self.sidebar.show()
        self._set_active("Home")
        self.stack.setCurrentWidget(self.dashboard_view)

    def show_domain(self, domain_data: dict):
        self._current_domain = domain_data
        self.domain_view.load_domain(domain_data)
        self.stack.setCurrentWidget(self.domain_view)

    def show_subfolder(self, sub_data: dict):
        self._current_subfolder = sub_data
        self.subfolder_view.load_subfolder(sub_data)
        self.stack.setCurrentWidget(self.subfolder_view)

    def _back_to_subfolder(self):
        if self._current_subfolder:
            self.stack.setCurrentWidget(self.subfolder_view)
        elif self._current_domain:
            self.stack.setCurrentWidget(self.domain_view)
        else:
            self.show_dashboard_no_reload()

    def _back_to_domain(self):
        if self._current_domain:
            self.stack.setCurrentWidget(self.domain_view)
        else:
            self.show_dashboard_no_reload()

    def show_video(self, video_data: dict):
        self.video_view.set_back_target("BACK TO SUB-FOLDER", None)
        self.video_view.load_video(video_data)
        # Pass siblings from current subfolder as related videos
        if self._current_subfolder:
            siblings = [v for v in self._current_subfolder.get("items", [])
                        if v.get("type") != "folder"]
            self.video_view.add_related(siblings)
        self.stack.setCurrentWidget(self.video_view)

    def show_video_from_history(self, video_data: dict):
        self.video_view.set_back_target("BACK TO HISTORY", self.show_history)
        self.video_view.load_video(video_data)
        self.stack.setCurrentWidget(self.video_view)

    def show_video_from_hub(self, video_data: dict):
        self.video_view.set_back_target("BACK TO PERSONAL HUB", self.show_personal)
        self.video_view.load_video(video_data)
        self.stack.setCurrentWidget(self.video_view)

    def show_video_from_favorites(self, video_data: dict):
        self.video_view.set_back_target("BACK TO FAVORITES", self.show_favorites)
        self.video_view.load_video(video_data)
        self.stack.setCurrentWidget(self.video_view)

    def show_video_from_folder(self, video_data: dict):
        self.video_view.set_back_target("BACK TO FOLDER", lambda: self.stack.setCurrentWidget(self.personal_folder_view))
        self.video_view.load_video(video_data)
        self.stack.setCurrentWidget(self.video_view)

    def show_login(self):
        self.sidebar.hide()
        self.stack.setCurrentWidget(self.login_view)
