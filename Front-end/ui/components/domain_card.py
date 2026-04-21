from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QVariantAnimation, QEasingCurve, QRectF
from PySide6.QtGui import (QPainter, QColor, QPixmap, QImage,
                            QLinearGradient, QFont, QPainterPath, QPen)
from image_cache import load_image


class DomainCard(QWidget):
    """Dark grayscale image card — colors + zooms in on hover."""
    clicked = Signal(dict)

    def __init__(self, data, card_width=220, card_height=260,
                 show_badge=True, badge_text="ARCHIVE DATA", parent=None):
        super().__init__(parent)
        self.data = data
        self.show_badge = show_badge
        self.badge_text = badge_text
        self.base_width = card_width
        self.base_height = card_height
        self.setMinimumSize(120, 90)  # allow layout to stretch freely
        self.setCursor(Qt.PointingHandCursor)

        self._gray   = None
        self._color  = None
        self._hovered = False
        self._scale   = 1.0   # animated 1.0 → 1.08

        # Scale animation
        self._sanim = QVariantAnimation(self)
        self._sanim.setDuration(300)
        self._sanim.setEasingCurve(QEasingCurve.OutCubic)
        self._sanim.valueChanged.connect(self._on_scale)

        # Color blend animation (0.0 = grayscale, 1.0 = full color)
        self._blend = 0.0
        self._banim = QVariantAnimation(self)
        self._banim.setDuration(300)
        self._banim.setEasingCurve(QEasingCurve.OutCubic)
        self._banim.valueChanged.connect(self._on_blend)

        url = data.get("img", "")
        if url:
            load_image(url, self._on_pixmap)

    def _on_pixmap(self, pm: QPixmap):
        img = pm.toImage()


        if img.isNull(): return
        def _sc(pix):
            return pix.scaled(self.width(), self.height(),
                              Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        # Store 2× the card size so we have room to zoom
        big_w = int(self.width()  * 1.20)
        big_h = int(self.height() * 1.20)
        def _sc2(pix):
            return pix.scaled(big_w, big_h,
                              Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self._color = _sc2(QPixmap.fromImage(img))
        self._gray  = _sc2(QPixmap.fromImage(img.convertToFormat(QImage.Format_Grayscale8)))
        self.update()

    def _on_scale(self, v):
        self._scale = v; self.update()

    def _on_blend(self, v):
        self._blend = v; self.update()

    def _animate(self, enter: bool):
        for anim, start, end in [
            (self._sanim, self._scale, 1.08 if enter else 1.0),
            (self._banim, self._blend, 1.0  if enter else 0.0),
        ]:
            anim.stop()
            anim.setStartValue(start)
            anim.setEndValue(end)
            anim.start()

    def enterEvent(self, e):
        self._hovered = True
        self._animate(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self._animate(False)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.data)
        super().mousePressEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = self.rect()

        p.fillRect(r, QColor("#141414"))

        if self._gray and self._color:
            # Clip to card rect
            clip = QPainterPath(); clip.addRect(QRectF(r))
            p.setClipPath(clip)

            # Compute zoomed size from the stored large pixmap
            zoom_factor = self._scale  # e.g. 1.0 … 1.08
            # The stored pixmaps are already 1.20× card size
            # so display at (1.20 * zoom_factor) scaled → crop to card
            base_w = int(r.width()  * 1.20 * zoom_factor)
            base_h = int(r.height() * 1.20 * zoom_factor)

            # Blend: draw gray first, then color on top with blend opacity
            def _draw(px, opacity):
                scaled = px.scaled(base_w, base_h,
                                   Qt.KeepAspectRatioByExpanding,
                                   Qt.SmoothTransformation)
                x = (r.width()  - scaled.width())  // 2
                y = (r.height() - scaled.height()) // 2
                p.setOpacity(opacity)
                p.drawPixmap(x, y, scaled)

            base_opacity = 0.72 if not self._hovered else 0.85
            _draw(self._gray,  base_opacity * (1.0 - self._blend * 0.6))
            if self._blend > 0.01:
                _draw(self._color, base_opacity * self._blend * 0.65)

            p.setOpacity(1.0)
            p.setClipping(False)

        # Dark gradient overlay
        grad = QLinearGradient(0, r.height() * 0.30, 0, r.height())
        grad.setColorAt(0.0, QColor(0, 0, 0, 15))
        grad.setColorAt(1.0, QColor(0, 0, 0, 215))
        p.fillRect(r, grad)

        # ARCHIVE DATA badge
        if self.show_badge:
            bf = QFont("Segoe UI", 7); bf.setBold(True)
            bf.setLetterSpacing(QFont.AbsoluteSpacing, 1)
            p.setFont(bf)
            tw = p.fontMetrics().horizontalAdvance(self.badge_text)
            bw, bh = tw + 14, 18
            bx, by = r.width() - bw - 8, 8
            p.setBrush(QColor(20, 20, 20, 200)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(bx, by, bw, bh), 3, 3)
            p.setPen(QColor("#e5e2e1"))
            p.drawText(int(bx), int(by), bw, bh, Qt.AlignCenter, self.badge_text)

        # Title
        name = self.data.get("name", self.data.get("title", ""))
        tf = QFont("Segoe UI", 12); tf.setBold(True)
        p.setFont(tf); p.setPen(QColor("#ffffff"))
        p.drawText(r.adjusted(14, r.height() - 80, -14, -34),
                   Qt.AlignLeft | Qt.AlignBottom | Qt.TextWordWrap, name)

        # Tag / count — detect videos vs sub-folders
        tag = self.data.get("tag", "")
        if not tag:
            items = self.data.get("items", [])
            cnt = len(items)
            if cnt:
                # If first item is a folder type → sub-folders, else → videos
                first_type = items[0].get("type", "video") if items else "video"
                label = "SUB-FOLDER" if first_type == "folder" else "VIDEO"
                tag = f"{cnt} {label}{'S' if cnt != 1 else ''}"
        if tag:
            sf = QFont("Segoe UI", 8)
            sf.setLetterSpacing(QFont.AbsoluteSpacing, 1)
            p.setFont(sf); p.setPen(QColor("#f26411"))
            p.drawText(r.adjusted(14, r.height() - 30, -14, -8),
                       Qt.AlignLeft | Qt.AlignVCenter, tag.upper())

        # Hover border fade-in
        if self._blend > 0.01:
            p.setPen(QPen(QColor(242, 100, 17, int(200 * self._blend)), 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawRect(r.adjusted(0, 0, -1, -1))
