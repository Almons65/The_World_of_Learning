import requests
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QSizePolicy, QGridLayout, QFileDialog,
    QDialog, QLineEdit, QTextEdit, QApplication
)
from PySide6.QtCore import Qt, Signal, QSettings, QVariantAnimation, QEasingCurve, QSize
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPainterPath, QPixmap, QImage,
    QLinearGradient, QPen, QIcon
)
from api_client import client
from image_cache import load_image



# ── Circular avatar ───────────────────────────────────────────────────────────
class AvatarWidget(QWidget):
    def __init__(self, size=92, parent=None):
        super().__init__(parent)
        self._sz = size
        self.setFixedSize(size, size)
        self._pm = None

    def set_pixmap(self, pm: QPixmap):
        self._pm = pm
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addEllipse(1, 1, self._sz - 2, self._sz - 2)
        p.setClipPath(path)
        if self._pm:
            p.drawPixmap(0, 0, self._sz, self._sz,
                         self._pm.scaled(self._sz, self._sz,
                                         Qt.KeepAspectRatioByExpanding,
                                         Qt.SmoothTransformation))
        else:
            p.fillRect(0, 0, self._sz, self._sz, QColor("#1c1b1b"))
            p.setPen(QColor("#ffffff15"))
            p.setBrush(QColor("#ffffff08"))
            c, r = self._sz // 2, self._sz // 3
            p.drawEllipse(c - r // 2, c - r, r, r)
            p.drawEllipse(c - r, c + 4, r * 2, r)
        p.setClipping(False)
        p.setPen(QPen(QColor("#ffffff18"), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(1, 1, self._sz - 2, self._sz - 2)


# ── Hero banner ───────────────────────────────────────────────────────────────
class HeroBanner(QWidget):
    edit_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(300)
        self._bg = None
        self._avatar = AvatarWidget(size=92)
        self._name  = QLabel("USER")
        self._bio   = QLabel("experience the domains")
        self._setup()

    def _setup(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(48, 0, 48, 36)
        root.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        root.setSpacing(22)
        root.addWidget(self._avatar, 0, Qt.AlignBottom)

        col = QVBoxLayout()
        col.setSpacing(5)
        col.setAlignment(Qt.AlignBottom)

        hub_lbl = QLabel("PERSONAL HUB")
        hub_lbl.setStyleSheet(
            "color:#f26411;font-size:9px;font-weight:bold;letter-spacing:6px;background:transparent;")

        f = QFont("Segoe UI", 38)
        f.setWeight(QFont.Black)
        self._name.setFont(f)
        self._name.setStyleSheet("color:#ffffff;background:transparent;letter-spacing:-2px;")

        self._bio.setStyleSheet(
            "color:rgba(255,255,255,0.38);font-size:12px;background:transparent;")
        self._bio.setWordWrap(True)
        self._bio.setMaximumWidth(480)

        edit_btn = QPushButton("✎   EDIT PROFILE")
        edit_btn.setFixedHeight(32)
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setStyleSheet("""
            QPushButton{background:transparent;color:rgba(255,255,255,0.5);
                border:1px solid rgba(255,255,255,0.18);font-size:9px;
                font-weight:bold;letter-spacing:3px;padding:0 16px;}
            QPushButton:hover{color:#f26411;border-color:#f26411;}
        """)
        edit_btn.clicked.connect(self.edit_clicked)

        btn_row = QHBoxLayout()
        btn_row.addWidget(edit_btn)
        btn_row.addStretch()

        col.addWidget(hub_lbl)
        col.addWidget(self._name)
        col.addWidget(self._bio)
        col.addSpacing(10)
        col.addLayout(btn_row)
        root.addLayout(col, 1)

    def set_name(self, name: str):
        self._name.setText(name.upper())

    def set_bio(self, bio: str):
        self._bio.setText(bio)

    def set_avatar(self, pm: QPixmap):
        self._avatar.set_pixmap(pm)

    def set_bg(self, pm: QPixmap):
        self._bg = pm
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if self._bg:
            p.setOpacity(0.22)
            p.drawPixmap(0, 0, w, h,
                         self._bg.scaled(w, h, Qt.KeepAspectRatioByExpanding,
                                         Qt.SmoothTransformation))
            p.setOpacity(1.0)
        else:
            p.fillRect(0, 0, w, h, QColor("#0e0e0e"))
        # bottom-fade
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, QColor(14, 14, 14, 0))
        g.setColorAt(0.45, QColor(14, 14, 14, 120))
        g.setColorAt(1, QColor(14, 14, 14, 255))
        p.fillRect(0, 0, w, h, g)
        # left-fade
        g2 = QLinearGradient(0, 0, w * 0.55, 0)
        g2.setColorAt(0, QColor(14, 14, 14, 210))
        g2.setColorAt(1, QColor(14, 14, 14, 0))
        p.fillRect(0, 0, w, h, g2)


# ── Section header row ────────────────────────────────────────────────────────
class SectionHeader(QWidget):
    action_clicked = Signal()

    def __init__(self, title: str, subtitle: str, action: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self.setFixedHeight(44)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        bar = QFrame()
        bar.setFixedSize(3, 20)
        bar.setStyleSheet("background:#f26411;border:none;")
        lay.addWidget(bar, 0, Qt.AlignVCenter)

        t = QLabel(title)
        t.setStyleSheet(
            "color:#e5e2e1;font-size:10px;font-weight:bold;letter-spacing:3px;background:transparent;")
        lay.addWidget(t, 0, Qt.AlignVCenter)

        s = QLabel(subtitle)
        s.setStyleSheet(
            "color:rgba(229,226,225,0.32);font-size:10px;font-weight:600;"
            "letter-spacing:3px;background:transparent;")
        lay.addWidget(s, 0, Qt.AlignVCenter)
        lay.addStretch()

        act = QPushButton(action)
        act.setCursor(Qt.PointingHandCursor)
        act.setFixedHeight(26)
        act.setStyleSheet("""
            QPushButton{background:transparent;color:rgba(229,226,225,0.32);
                border:none;font-size:9px;font-weight:bold;letter-spacing:2px;padding:0 6px;}
            QPushButton:hover{color:#f26411;}
        """)
        act.clicked.connect(self.action_clicked)
        lay.addWidget(act, 0, Qt.AlignVCenter)


# ── Horizontal-scroll video card ─────────────────────────────────────────────
class HubVideoCard(QFrame):
    clicked = Signal(dict)

    def __init__(self, v: dict, parent=None):
        super().__init__(parent)
        self._v = v
        self.setFixedSize(240, 200)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame{background:#181818;border-radius:6px;border:1px solid #232323;}
        """)
        self._scale = 1.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 10)
        lay.setSpacing(6)

        self._thumb = QLabel()
        self._thumb.setFixedHeight(130)
        self._thumb.setStyleSheet("background:#131313;border-radius:5px 5px 0 0;")
        self._thumb.setScaledContents(True)
        lay.addWidget(self._thumb)

        tag = QLabel(v.get("tag", "WATCHED"))
        tag.setStyleSheet(
            "color:#f26411;font-size:8px;font-weight:bold;letter-spacing:2px;"
            "background:transparent;padding-left:10px;")
        lay.addWidget(tag)

        title = QLabel(v.get("title", "Untitled"))
        title.setWordWrap(True)
        title.setMaximumHeight(36)
        title.setStyleSheet(
            "color:#e5e2e1;font-size:12px;font-weight:bold;background:transparent;padding-left:10px;")
        lay.addWidget(title)

        if v.get("thumb"):
            load_image(v["thumb"], self._on_img)

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
        self.setStyleSheet("QFrame{background:#1e1e1e;border-radius:6px;border:1px solid #f26411;}")
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self.setStyleSheet("QFrame{background:#181818;border-radius:6px;border:1px solid #232323;}")
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._scale > 1.0:
            p.translate(self.width()/2, self.height()/2)
            p.scale(self._scale, self._scale)
            p.translate(-self.width()/2, -self.height()/2)
        super().paintEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self._v)
        super().mousePressEvent(e)


# ── Grid favorite card ────────────────────────────────────────────────────────
class HubFavCard(QFrame):
    clicked = Signal(dict)
    removed = Signal(dict)

    def __init__(self, v: dict, parent=None):
        super().__init__(parent)
        self._v = v
        self.setFixedSize(220, 210)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame{background:#181818;border-radius:6px;border:1px solid #232323;}
        """)
        self._scale = 1.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 10)
        lay.setSpacing(6)

        self._thumb = QLabel()
        self._thumb.setFixedHeight(120)
        self._thumb.setStyleSheet("background:#131313;border-radius:5px 5px 0 0;")
        self._thumb.setScaledContents(True)
        lay.addWidget(self._thumb)

        self._remove_btn = QPushButton("✕", self._thumb)
        self._remove_btn.setFixedSize(24, 24)
        self._remove_btn.move(188, 8)
        self._remove_btn.setCursor(Qt.PointingHandCursor)
        self._remove_btn.setStyleSheet("""
            QPushButton{background:rgba(180,0,0,0.8);color:white;border:none;border-radius:12px;font-size:12px;font-weight:bold;}
            QPushButton:hover{background:red;}
        """)
        self._remove_btn.hide()
        self._remove_btn.clicked.connect(self._on_remove)

        tag = QLabel("★  " + v.get("tag", "FAVORITED"))
        tag.setStyleSheet(
            "color:#f26411;font-size:8px;font-weight:bold;letter-spacing:2px;"
            "background:transparent;padding-left:10px;")
        lay.addWidget(tag)

        title = QLabel(v.get("title", "Untitled"))
        title.setWordWrap(True)
        title.setMaximumHeight(40)
        title.setStyleSheet(
            "color:#e5e2e1;font-size:12px;font-weight:bold;background:transparent;padding-left:10px;")
        lay.addWidget(title)

        if v.get("thumb") or v.get("img"):
            load_image(v.get("thumb") or v["img"], self._on_img)

    def _on_remove(self):
        self.removed.emit(self._v)

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
        self.setStyleSheet("QFrame{background:#1e1e1e;border-radius:6px;border:1px solid #f26411;}")
        self._remove_btn.show()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self.setStyleSheet("QFrame{background:#181818;border-radius:6px;border:1px solid #232323;}")
        self._remove_btn.hide()
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._scale > 1.0:
            p.translate(self.width()/2, self.height()/2)
            p.scale(self._scale, self._scale)
            p.translate(-self.width()/2, -self.height()/2)
        super().paintEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self._v)
        super().mousePressEvent(e)


# ── Folder card ───────────────────────────────────────────────────────────────
class HubFolderCard(QFrame):
    clicked = Signal(dict)

    def __init__(self, folder: dict, parent=None):
        super().__init__(parent)
        self._d = folder
        self.setFixedSize(190, 190)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame{background:#181818;border-radius:6px;border:1px solid #232323;}
        """)
        self._scale = 1.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 12)
        lay.setSpacing(6)

        self._thumb = QLabel()
        self._thumb.setFixedHeight(110)
        self._thumb.setStyleSheet("background:#131313;border-radius:5px 5px 0 0;")
        self._thumb.setScaledContents(True)
        lay.addWidget(self._thumb)

        cnt = len(folder.get("items", []))
        badge = QLabel(f"{cnt} videos")
        badge.setStyleSheet(
            "color:#737373;font-size:8px;font-weight:bold;letter-spacing:2px;"
            "background:transparent;padding-left:10px;")
        lay.addWidget(badge)

        name = QLabel(folder.get("name", "Folder"))
        name.setWordWrap(True)
        name.setStyleSheet(
            "color:#e5e2e1;font-size:12px;font-weight:bold;background:transparent;padding-left:10px;")
        lay.addWidget(name)

        img_url = folder.get("hero_img") or folder.get("img", "")
        if img_url:
            if img_url.startswith("http"):
                load_image(img_url, self._on_img)
            else:
                from PySide6.QtGui import QPixmap
                pm = QPixmap(img_url)
                if not pm.isNull():
                    self._on_img(pm)

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
        self.setStyleSheet("QFrame{background:#1e1e1e;border-radius:6px;border:1px solid #f26411;}")
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._scale)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self.setStyleSheet("QFrame{background:#181818;border-radius:6px;border:1px solid #232323;}")
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._scale > 1.0:
            p.translate(self.width()/2, self.height()/2)
            p.scale(self._scale, self._scale)
            p.translate(-self.width()/2, -self.height()/2)
        super().paintEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self._d)
        super().mousePressEvent(e)


# ── Empty-state placeholder ───────────────────────────────────────────────────
def _empty_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setFixedHeight(90)
    lbl.setStyleSheet(
        "color:rgba(229,226,225,0.20);font-size:12px;font-style:italic;"
        "border:1px dashed rgba(255,255,255,0.06);border-radius:6px;background:transparent;")
    return lbl


# ── Horizontal strip (scroll) ─────────────────────────────────────────────────
def _h_scroll() -> tuple[QScrollArea, QWidget, QHBoxLayout]:
    area = QScrollArea()
    area.setFrameShape(QFrame.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    area.setFixedHeight(215)
    area.setStyleSheet("QScrollArea{background:transparent;border:none;}")

    w = QWidget()
    w.setStyleSheet("background:transparent;")
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 4, 0, 4)
    h.setSpacing(14)
    area.setWidget(w)
    area.setWidgetResizable(True)
    return area, w, h


# ── Edit Profile dialog ───────────────────────────────────────────────────────

class _UserIcon(QWidget):
    """Draws a simple user silhouette (head + shoulders arc) in white."""
    def __init__(self, size=24, parent=None):
        super().__init__(parent)
        self._sz = size
        self.setFixedSize(size, size)
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(242, 100, 17))  # orange accent
        s = self._sz
        # head circle
        p.drawEllipse(s//4, 1, s//2, s//2)
        # shoulder arc
        path = QPainterPath()
        path.moveTo(0, s)
        path.arcTo(0, s//2, s, s, 0, 180)
        p.drawPath(path)
        p.end()

class _CameraIcon(QWidget):
    """Draws a minimal camera outline icon."""
    def __init__(self, size=28, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._sz = size
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self._sz
        pen = QPen(QColor(180, 180, 180), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        # camera body
        p.drawRoundedRect(2, 6, s-4, s-10, 3, 3)
        # lens
        p.drawEllipse(s//2-5, 9, 10, 10)
        # viewfinder bump
        p.drawRect(s//2-3, 3, 6, 3)
        p.end()

class _ImageIcon(QWidget):
    """Draws a minimal landscape/image placeholder icon."""
    def __init__(self, size=20, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._sz = size
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self._sz
        pen = QPen(QColor(180, 180, 180), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        # frame
        p.drawRoundedRect(1, 1, s-2, s-2, 2, 2)
        # mountain silhouette lines
        p.drawLine(1, s-4, s//3, s//2)
        p.drawLine(s//3, s//2, s*2//3, s*3//4)
        p.drawLine(s*2//3, s*3//4, s-1, s//3)
        # sun circle
        p.drawEllipse(s-7, 3, 4, 4)
        p.end()


class EditProfileDialog(QDialog):
    saved = Signal(str, str, str, str)  # (display_name, bio, avatar_path, header_path)

    def __init__(self, username, display_name, bio, avatar_path="", header_path="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Profile")
        self.setFixedWidth(520)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.setStyleSheet("""
            QDialog{background:#1c1b1b;border-radius:12px;}
            QLabel{color:#e5e2e1;background:transparent;}
            QLineEdit,QTextEdit{
                background:#131313;color:#e5e2e1;
                border:1px solid #353534;border-radius:6px;
                padding:10px;font-size:13px;
            }
            QLineEdit:focus,QTextEdit:focus{border-color:#f26411;}
        """)

        self._avatar_path = avatar_path
        self._header_path = header_path

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        # ── Title row ────────────────────────────────────────────────────────
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title_row.addWidget(_UserIcon(24))

        t_col = QVBoxLayout()
        t_col.setSpacing(2)
        t1 = QLabel("Edit Profile")
        t1.setStyleSheet("font-size:18px;font-weight:bold;color:#ffffff;background:transparent;")
        t2 = QLabel("Update your archive identity")
        t2.setStyleSheet("font-size:11px;color:rgba(255,255,255,0.4);background:transparent;")
        t_col.addWidget(t1)
        t_col.addWidget(t2)
        title_row.addLayout(t_col)
        title_row.addStretch()
        root.addLayout(title_row)

        # ── Avatar upload ─────────────────────────────────────────────────────
        avatar_row = QHBoxLayout()
        avatar_row.setAlignment(Qt.AlignCenter)

        # Use a custom painted button that draws camera icon in center
        self._avatar_btn = _AvatarPickButton(80, avatar_path)
        self._avatar_btn.clicked.connect(self._pick_avatar)
        avatar_row.addWidget(self._avatar_btn)
        root.addLayout(avatar_row)

        # ── Header background upload ─────────────────────────────────────────
        hdr_lbl = QLabel("HEADER BACKGROUND")
        hdr_lbl.setStyleSheet("color:rgba(255,255,255,0.35);font-size:9px;font-weight:bold;letter-spacing:3px;background:transparent;")
        root.addWidget(hdr_lbl)

        self._header_btn = _HeaderPickButton(header_path)
        self._header_btn.clicked.connect(self._pick_header)
        root.addWidget(self._header_btn)

        # ── Display Name ──────────────────────────────────────────────────────
        dn_lbl = QLabel("DISPLAY NAME")
        dn_lbl.setStyleSheet("color:rgba(255,255,255,0.35);font-size:9px;font-weight:bold;letter-spacing:3px;background:transparent;")
        root.addWidget(dn_lbl)
        self._name = QLineEdit(display_name or username)
        self._name.setMaxLength(30)
        root.addWidget(self._name)

        # ── Bio ────────────────────────────────────────────────────────────────
        bio_lbl = QLabel("BIO")
        bio_lbl.setStyleSheet("color:rgba(255,255,255,0.35);font-size:9px;font-weight:bold;letter-spacing:3px;background:transparent;")
        root.addWidget(bio_lbl)
        self._bio = QTextEdit(bio)
        self._bio.setFixedHeight(72)
        root.addWidget(self._bio)

        # ── Buttons ────────────────────────────────────────────────────────────
        btns = QHBoxLayout()
        btns.setSpacing(12)

        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(42)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#a0a0a0;border:none;"
            "border-radius:8px;font-weight:bold;font-size:13px;}"
            "QPushButton:hover{background:#333;color:#fff;}")
        cancel.clicked.connect(self.reject)

        apply = QPushButton("APPLY CHANGES")
        apply.setFixedHeight(42)
        apply.setCursor(Qt.PointingHandCursor)
        apply.setStyleSheet(
            "QPushButton{background:#f26411;color:#fff;border:none;"
            "border-radius:8px;font-weight:bold;font-size:13px;}"
            "QPushButton:hover{background:#ff7326;}")
        apply.clicked.connect(self._save)

        btns.addWidget(cancel, 1)
        btns.addWidget(apply, 2)
        root.addLayout(btns)

    def _pick_avatar(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Profile Picture", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self._avatar_path = path
            self._avatar_btn.set_image(path)

    def _pick_header(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Header Background", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self._header_path = path
            self._header_btn.set_image(path)

    def _save(self):
        self.saved.emit(
            self._name.text().strip(),
            self._bio.toPlainText().strip(),
            self._avatar_path,
            self._header_path,
        )
        self.accept()


class _AvatarPickButton(QWidget):
    clicked = Signal()
    def __init__(self, size=80, img_path="", parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self._sz = size
        self._pm = None
        self._hov = False
        if img_path:
            pm = QPixmap(img_path)
            if not pm.isNull():
                self._pm = pm.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    def set_image(self, path):
        pm = QPixmap(path)
        if not pm.isNull():
            self._pm = pm.scaled(self._sz, self._sz, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()

    def enterEvent(self, e): self._hov = True; self.update()
    def leaveEvent(self, e): self._hov = False; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self._sz
        border_col = QColor("#f26411") if self._hov else QColor(255, 255, 255, 50)
        if self._pm:
            # Draw image clipped to rounded rect
            path = QPainterPath()
            from PySide6.QtCore import QRectF
            path.addRoundedRect(QRectF(0, 0, s, s), 12, 12)
            p.setClipPath(path)
            p.drawPixmap(0, 0, self._pm)
            p.setClipping(False)
        else:
            p.setBrush(QColor("#131313"))
            p.setPen(QPen(border_col, 2, Qt.DashLine))
            p.drawRoundedRect(0, 0, s, s, 12, 12)
            # Draw camera icon centered
            p.setPen(QPen(border_col, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            cx, cy = s//2, s//2
            # body
            p.drawRoundedRect(cx-14, cy-8, 28, 18, 3, 3)
            # lens circle
            p.drawEllipse(cx-6, cy-5, 12, 12)
            # bump
            p.drawRect(cx-4, cy-13, 8, 5)
        # Border
        p.setClipping(False)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(border_col, 2, Qt.DashLine))
        p.drawRoundedRect(0, 0, s, s, 12, 12)
        p.end()


class _HeaderPickButton(QWidget):
    clicked = Signal()
    def __init__(self, img_path="", parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self.setCursor(Qt.PointingHandCursor)
        self._pm = None
        self._hov = False
        if img_path:
            pm = QPixmap(img_path)
            if not pm.isNull():
                self._pm = pm

    def set_image(self, path):
        pm = QPixmap(path)
        if not pm.isNull():
            self._pm = pm
            self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()

    def enterEvent(self, e): self._hov = True; self.update()
    def leaveEvent(self, e): self._hov = False; self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        border_col = QColor("#f26411") if self._hov else QColor(255, 255, 255, 38)
        if self._pm:
            path = QPainterPath()
            from PySide6.QtCore import QRectF
            path.addRoundedRect(QRectF(0, 0, w, h), 8, 8)
            p.setClipPath(path)
            scaled = self._pm.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            p.drawPixmap(0, 0, scaled)
            p.setClipping(False)
        else:
            p.setBrush(QColor("#131313"))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(0, 0, w, h, 8, 8)

            # Draw image icon + text
            ic = _ImageIcon(20)
            # Draw landscape icon inline
            p.setPen(QPen(border_col, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            cx = w//2 - 50
            cy = h//2 - 8
            p.drawRoundedRect(cx, cy, 18, 16, 2, 2)
            p.drawLine(cx, cy+12, cx+6, cy+6)
            p.drawLine(cx+6, cy+6, cx+12, cy+10)
            p.drawLine(cx+12, cy+10, cx+18, cy+4)
            p.drawEllipse(cx+13, cy+2, 4, 4)

            # Text
            p.setPen(border_col)
            from PySide6.QtGui import QFont as _F
            f = _F()
            f.setPointSize(10)
            f.setLetterSpacing(_F.AbsoluteSpacing, 2)
            p.setFont(f)
            p.drawText(cx+26, cy, 200, 16, Qt.AlignVCenter | Qt.AlignLeft, "BROWSE CONTENT")

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(border_col, 1, Qt.DashLine))
        p.drawRoundedRect(0, 0, w, h, 8, 8)
        p.end()

# ── Main Personal Hub View ────────────────────────────────────────────────────
class PersonalHubView(QWidget):
    video_selected = Signal(dict)
    folder_selected = Signal(dict)
    view_all_history = Signal()
    view_all_favorites = Signal()
    manage_folders = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._username = ""
        self._settings = QSettings("WoL", "PersonalHub")
        self.setStyleSheet("background:#0e0e0e;")
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Hero ──────────────────────────────────────────────────────────
        self._hero = HeroBanner()
        self._hero.edit_clicked.connect(self._open_edit)
        root.addWidget(self._hero)

        # ── Scrollable content ────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        content = QWidget()
        content.setStyleSheet("background:transparent;")
        self._cl = QVBoxLayout(content)
        self._cl.setContentsMargins(48, 28, 48, 60)
        self._cl.setSpacing(32)

        # WATCH HISTORY
        wh = SectionHeader("WATCH", "History", "View All")
        wh.action_clicked.connect(self.view_all_history.emit)
        self._cl.addWidget(wh)
        self._hist_area, self._hist_w, self._hist_lay = _h_scroll()
        self._hist_lay.addWidget(_empty_label("No recent activity in the temporal stream."))
        self._hist_lay.addStretch()
        self._cl.addWidget(self._hist_area)

        # USER FAVORITES
        uf = SectionHeader("USER", "Favorites", "View All")
        uf.action_clicked.connect(self.view_all_favorites.emit)
        self._cl.addWidget(uf)
        self._fav_area, self._fav_w, self._fav_lay = _h_scroll()
        self._fav_lay.addWidget(_empty_label("No curated favorites found in your selection."))
        self._fav_lay.addStretch()
        self._cl.addWidget(self._fav_area)

        # PERSONAL PLAYLISTS
        pp = SectionHeader("PERSONAL", "Folders", "Manage Folders")
        pp.action_clicked.connect(self.manage_folders.emit)
        self._cl.addWidget(pp)
        self._pl_area, self._pl_w, self._pl_lay = _h_scroll()
        self._pl_lay.addWidget(_empty_label("No personal folders found."))
        self._pl_lay.addStretch()
        self._cl.addWidget(self._pl_area)

        self._cl.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    # ── Public ────────────────────────────────────────────────────────────────
    def load_data(self, username: str = ""):
        if username:
            self._username = username

        # Restore saved profile
        key = self._username
        dn = self._settings.value(f"{key}/display_name", self._username)
        bio = self._settings.value(
            f"{key}/bio", "Initiate your domains to unlock the true potential of the Global Archive.")
        self._hero.set_name(dn or self._username)
        self._hero.set_bio(bio)

        # Avatar
        av_path = self._settings.value(f"{key}/avatar_path", "")
        if av_path:
            pm = QPixmap(av_path)
            if not pm.isNull():
                self._hero.set_avatar(pm)

        # Header Background
        hdr_path = self._settings.value(f"{key}/header_path", "")
        if hdr_path:
            pm = QPixmap(hdr_path)
            if not pm.isNull():
                self._hero.set_bg(pm)
            else:
                # Fallback to default if local file fails
                bg_url = "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?q=80&w=1920&auto=format&fit=crop"
                load_image(bg_url, self._on_bg)
        else:
            # Default hero bg asynchronously (coding image)
            bg_url = "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?q=80&w=1920&auto=format&fit=crop"
            load_image(bg_url, self._on_bg)

        # Fetch profile from API
        client.get_profile(self._on_profile, lambda e: print(f"Hub profile error: {e}"))

    def _on_bg(self, pm: QPixmap):
        self._hero.set_bg(pm)

    def _on_profile(self, data: dict):
        username = data.get("username", self._username)
        key = self._username
        dn = self._settings.value(f"{key}/display_name", username)
        self._hero.set_name(dn or username)

        self._populate_history(data.get("history", []))
        self._populate_favorites(data.get("favorites", []))
        
        from ui.folder_store import get_user_folders
        folders = get_user_folders(self._username)
        self._populate_playlists(folders)

    # ── Populate sections ─────────────────────────────────────────────────────
    def _clear_layout(self, lay):
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

    def _populate_history(self, videos: list):
        self._clear_layout(self._hist_lay)
        if not videos:
            self._hist_lay.addWidget(
                _empty_label("No recent activity in the temporal stream."))
        else:
            for v in videos[:10]:
                card = HubVideoCard(v)
                card.clicked.connect(self.video_selected)
                self._hist_lay.addWidget(card)
        self._hist_lay.addStretch()

    def _populate_favorites(self, videos: list):
        self._clear_layout(self._fav_lay)
        if not videos:
            self._fav_lay.addWidget(
                _empty_label("No curated favorites found in your selection."))
        else:
            for v in videos[:12]:
                card = HubFavCard(v)
                card.clicked.connect(self.video_selected)
                card.removed.connect(self._on_favorite_removed)
                self._fav_lay.addWidget(card)
        self._fav_lay.addStretch()

    def _on_favorite_removed(self, video_data: dict):
        slug = video_data.get("slug")
        if slug:
            client.remove_favorite(slug, lambda _: self.load_data(), lambda e: print(f"Remove fav error: {e}"))

    def _populate_playlists(self, playlists: list):
        self._clear_layout(self._pl_lay)
        
        # Always add the Create New Folder button at the start
        create_btn = QFrame()
        create_btn.setFixedSize(190, 190)
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setStyleSheet("QFrame{background:rgba(255,255,255,0.02);border:2px dashed rgba(255,255,255,0.1);border-radius:12px;} QFrame:hover{border-color:#f26411;background:rgba(242,100,17,0.05);}")
        c_lay = QVBoxLayout(create_btn)
        c_lay.setAlignment(Qt.AlignCenter)
        c_icon = QLabel("+")
        c_icon.setAlignment(Qt.AlignCenter)
        c_icon.setFixedSize(36, 36)
        c_icon.setStyleSheet("background:#1c1b1b;color:#ffffff;font-size:20px;border-radius:6px;")
        c_lay.addWidget(c_icon, 0, Qt.AlignCenter)
        c_lay.addSpacing(12)
        c_lbl = QLabel("CREATE NEW FOLDER")
        c_lbl.setStyleSheet("color:#f26411;font-size:9px;font-weight:bold;letter-spacing:1px;")
        c_lay.addWidget(c_lbl, 0, Qt.AlignCenter)
        create_btn.mousePressEvent = self._on_create_folder_click
        self._pl_lay.addWidget(create_btn)

        if playlists:
            for pl in playlists:
                card = HubFolderCard(pl)
                card.clicked.connect(self.folder_selected)
                self._pl_lay.addWidget(card)
        self._pl_lay.addStretch()

    def _on_create_folder_click(self, e):
        if e.button() == Qt.LeftButton:
            from ui.views.folders_view import CreateFolderDialog
            from ui.folder_store import save_user_folders, get_user_folders
            import uuid, datetime
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
                    folders = get_user_folders(self._username)
                    folders.append(new_f)
                    save_user_folders(self._username, folders)
                    # Refresh the UI
                    self._populate_playlists(folders)

    # ── Edit Profile ──────────────────────────────────────────────────────────
    def _open_edit(self):
        key = self._username
        dn = self._settings.value(f"{key}/display_name", self._username)
        bio = self._settings.value(f"{key}/bio", "")
        avatar = self._settings.value(f"{key}/avatar_path", "")
        header = self._settings.value(f"{key}/header_path", "")
        dlg = EditProfileDialog(self._username, dn, bio, avatar, header, self)
        dlg.saved.connect(self._apply_profile)
        dlg.exec()

    def _apply_profile(self, name: str, bio: str, avatar_path: str, header_path: str):
        key = self._username
        if name:
            self._settings.setValue(f"{key}/display_name", name)
            self._hero.set_name(name)
        if bio:
            self._settings.setValue(f"{key}/bio", bio)
            self._hero.set_bio(bio)
        if avatar_path:
            self._settings.setValue(f"{key}/avatar_path", avatar_path)
            pm = QPixmap(avatar_path)
            if not pm.isNull():
                self._hero.set_avatar(pm)
        if header_path:
            self._settings.setValue(f"{key}/header_path", header_path)
            pm = QPixmap(header_path)
            if not pm.isNull():
                self._hero.set_bg(pm)

