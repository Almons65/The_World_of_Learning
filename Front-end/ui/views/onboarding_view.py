from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                               QGridLayout, QHBoxLayout, QScrollArea, QFrame, QApplication,
                               QSizePolicy)
from PySide6.QtCore import Qt, Signal, QPoint, QVariantAnimation, QAbstractAnimation, QEasingCurve, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QPixmap, QLinearGradient, QPen, QImage
import os
from api_client import client

class LiftWrapper(QWidget):
    """Transparent wrapper that physically lifts its child widget on hover (translateY effect)."""
    def __init__(self, child, lift_px=3, parent=None):
        super().__init__(parent)
        self.child = child
        self.lift_px = lift_px

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, lift_px, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.child)

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._on_changed)

        self.child.installEventFilter(self)
        self.y_offset = 0.0

    def eventFilter(self, obj, event):
        if obj == self.child:
            if event.type() == event.Type.Enter and self.child.isEnabled():
                self.anim.stop()
                self.anim.setStartValue(self.y_offset)
                self.anim.setEndValue(float(self.lift_px))
                self.anim.start()
            elif event.type() == event.Type.Leave:
                self.anim.stop()
                self.anim.setStartValue(self.y_offset)
                self.anim.setEndValue(0.0)
                self.anim.start()
        return super().eventFilter(obj, event)

    def _on_changed(self, offset):
        self.y_offset = offset
        mt = self.lift_px - int(round(offset))
        mb = int(round(offset))
        self.layout().setContentsMargins(0, mt, 0, mb)


class AnimatedSolidButton(QPushButton):
    """Primary solid button with smooth color hover animation."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._on_color_changed)
        self.current_bg = QColor("#f26411")

    def enterEvent(self, event):
        if self.isEnabled():
            self.anim.stop()
            self.anim.setStartValue(self.current_bg)
            self.anim.setEndValue(QColor("#ff7326"))
            self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isEnabled():
            self.anim.stop()
            self.anim.setStartValue(self.current_bg)
            self.anim.setEndValue(QColor("#f26411"))
            self.anim.start()
        super().leaveEvent(event)

    def _on_color_changed(self, color):
        if isinstance(color, QColor):
            self.current_bg = color
            self.setStyleSheet(
                f"QPushButton {{ background-color: {color.name()}; color: #1a0800; "
                f"font-weight: bold; font-size: 13px; text-transform: uppercase; "
                f"letter-spacing: 2px; border: none; border-radius: 4px; padding: 14px 20px; }}"
            )

class CategoryCard(QWidget):
    toggled = Signal(str, bool)

    def __init__(self, title, image_filename):
        super().__init__()
        self.title = title
        self.is_selected = False
        self.is_hovered = False
        self.setMinimumHeight(200)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Load image
        img_path = os.path.join(os.path.dirname(__file__), "..", "..", "imgs", "categories", image_filename)
        self.raw_color_pixmap = QPixmap(img_path)
        
        # Create grayscale version
        img = self.raw_color_pixmap.toImage()
        img = img.convertToFormat(QImage.Format_Grayscale8)
        self.raw_gray_pixmap = QPixmap.fromImage(img)
        
        # Hover Animation (Zoom and Color)
        self.hover_progress = 0.0
        self.hover_anim = QVariantAnimation(self)
        self.hover_anim.setDuration(250)
        self.hover_anim.setStartValue(0.0)
        self.hover_anim.setEndValue(1.0)
        self.hover_anim.valueChanged.connect(self._on_hover_changed)
        
        # Select Animation (Checkmark pop and Border)
        self.select_progress = 0.0
        self.select_anim = QVariantAnimation(self)
        self.select_anim.setDuration(250)
        self.select_anim.setStartValue(0.0)
        self.select_anim.setEndValue(1.0)
        self.select_anim.setEasingCurve(QEasingCurve.OutBack)
        self.select_anim.valueChanged.connect(self._on_select_changed)
        
        # Press Animation (Physical push down)
        self.is_pressed = False
        self.press_progress = 0.0
        self.press_anim = QVariantAnimation(self)
        self.press_anim.setDuration(150)
        self.press_anim.setStartValue(0.0)
        self.press_anim.setEndValue(1.0)
        self.press_anim.setEasingCurve(QEasingCurve.OutQuad)
        self.press_anim.valueChanged.connect(self._on_press_changed)

    def _on_hover_changed(self, val):
        self.hover_progress = val
        self.update()
        
    def _on_select_changed(self, val):
        self.select_progress = val
        self.update()

    def _on_press_changed(self, val):
        self.press_progress = val
        self.update()

    def enterEvent(self, event):
        self.is_hovered = True
        self.hover_anim.setDirection(QAbstractAnimation.Forward)
        self.hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.hover_anim.setDirection(QAbstractAnimation.Backward)
        self.hover_anim.start()
        if getattr(self, 'is_pressed', False):
            self.is_pressed = False
            self.press_anim.setDirection(QAbstractAnimation.Backward)
            self.press_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_pressed = True
            self.press_anim.setDirection(QAbstractAnimation.Forward)
            self.press_anim.start()
            
            self.is_selected = not self.is_selected
            self.select_anim.setDirection(QAbstractAnimation.Forward if self.is_selected else QAbstractAnimation.Backward)
            self.select_anim.start()
            self.toggled.emit(self.title, self.is_selected)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and getattr(self, 'is_pressed', False):
            self.is_pressed = False
            self.press_anim.setDirection(QAbstractAnimation.Backward)
            self.press_anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        if getattr(self, 'press_progress', 0.0) > 0:
            press_scale = 1.0 - (0.05 * self.press_progress)
            painter.translate(self.width() / 2, self.height() / 2)
            painter.scale(press_scale, press_scale)
            painter.translate(-self.width() / 2, -self.height() / 2)
        
        # We need to draw a source rect from the pixmap that matches the aspect ratio of our current size
        pr_w, pr_h = self.raw_color_pixmap.width(), self.raw_color_pixmap.height()
        w, h = self.width(), self.height()
        
        # target aspect ratio
        target_ar = w / h if h > 0 else 1
        pix_ar = pr_w / pr_h if pr_h > 0 else 1
        
        if pix_ar > target_ar:
            # Pixmap is wider than target. Crop left/right.
            crop_w = pr_h * target_ar
            crop_h = pr_h
        else:
            # Pixmap is taller than target. Crop top/bottom.
            crop_w = pr_w
            crop_h = pr_w / target_ar
            
        sx = (pr_w - crop_w) / 2
        sy = (pr_h - crop_h) / 2
        source_rect = QRectF(sx, sy, crop_w, crop_h)
        
        # Calculate zoomed rect based on hover progress (max 10% zoom)
        zoom_factor = 1.0 + (0.1 * self.hover_progress)
        zw = w * zoom_factor
        zh = h * zoom_factor
        tx = (w - zw) / 2
        ty = (h - zh) / 2
        target_rect = QRectF(tx, ty, zw, zh)
        
        # Draw Grayscale Base
        painter.drawPixmap(target_rect, self.raw_gray_pixmap, source_rect)

        # Draw Colored Overlay based on hover or select state
        color_opacity = max(self.hover_progress, self.select_progress)
        if color_opacity > 0:
            painter.setOpacity(color_opacity)
            painter.drawPixmap(target_rect, self.raw_color_pixmap, source_rect)
            painter.setOpacity(1.0)

        # Draw Gradient Overlay
        gradient = QLinearGradient(0, self.height() / 2, 0, self.height())
        gradient.setColorAt(0, QColor(0, 0, 0, 0))
        gradient.setColorAt(1, QColor(0, 0, 0, 240))
        painter.fillRect(self.rect(), gradient)

        # Draw Orange Border and Checkmark with animation progress
        if self.select_progress > 0:
            # Border
            pen = QPen(QColor(242, 100, 17, int(255 * self.select_progress))) # f26411
            pen.setWidth(6)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.rect())
            
            # Checkmark Circle (scales up)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(242, 100, 17, int(255 * self.select_progress)))
            cx, cy = self.width() - 25, 25
            r = 12 * self.select_progress
            painter.drawEllipse(QPoint(cx, cy), r, r)
            
            # Checkmark Icon
            if self.select_progress > 0.3:
                # Fade in the icon over the remaining progress
                icon_opacity = min(1.0, (self.select_progress - 0.3) * 1.5)
                painter.setOpacity(icon_opacity)
                painter.setPen(QPen(QColor("white"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.drawLine(cx - 4 * self.select_progress, cy + 1 * self.select_progress, 
                                 cx - 1 * self.select_progress, cy + 4 * self.select_progress)
                painter.drawLine(cx - 1 * self.select_progress, cy + 4 * self.select_progress, 
                                 cx + 5 * self.select_progress, cy - 3 * self.select_progress)
                painter.setOpacity(1.0)
            
        # Draw Title
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(20, self.height() - 25, self.title)


class OnboardingView(QWidget):
    interests_saved = Signal()

    def __init__(self):
        super().__init__()
        self.selected_interests = set()
        self.categories = [
            ("History", "history.jpg"),
            ("Computer Science", "computer_science.jpg"),
            ("Astrophysics", "astrophysics.jpg"),
            ("Neuroscience", "neuroscience.jpg"),
            ("Philosophy", "philosophy.jpg"),
            ("Architecture", "architecture.jpg"),
            ("Marine Biology", "marine_biology.jpg"),
            ("Geopolitics", "geopolitics.jpg"),
            ("Mathematics", "mathematics.jpg"),
            ("Film & Cinema", "film_and_cinema.jpg"),
            ("Economics", "economics.jpg"),
            ("Archaeology", "archaeology.jpg")
        ]
        self._setup_ui()

    def paintEvent(self, event):
        # Dark premium background
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#111111"))
        super().paintEvent(event)

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(80, 60, 80, 0)
        self.layout.setSpacing(0)

        # --- Header ---
        header_layout = QHBoxLayout()
        header_vbox = QVBoxLayout()
        
        title_label = QLabel()
        title_label.setText('<span style="color: white;">Initialize Your</span> <span style="color: #f26411;">Discovery</span>')
        font = title_label.font()
        font.setPointSize(36)
        font.setBold(True)
        title_label.setFont(font)
        
        subtitle_label = QLabel("Select the Archive Categories that suit your interest")
        subtitle_label.setStyleSheet("color: #a98a7e; font-size: 16px;")
        
        header_vbox.addWidget(title_label)
        header_vbox.addWidget(subtitle_label)
        
        req_label = QLabel("AT LEAST 2 CATEGORIES ARE REQUIRED")
        req_label.setStyleSheet("color: #f26411; font-size: 11px; font-weight: bold; letter-spacing: 2px;")
        req_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        
        header_layout.addLayout(header_vbox)
        header_layout.addStretch()
        header_layout.addWidget(req_label)
        
        self.layout.addLayout(header_layout)
        self.layout.addSpacing(40)

        # --- Grid ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QWidget#gridWidget { background: transparent; }")
        
        grid_widget = QWidget()
        grid_widget.setObjectName("gridWidget")
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        row, col = 0, 0
        for title, img in self.categories:
            card = CategoryCard(title, img)
            card.toggled.connect(self.toggle_interest)
            grid_layout.addWidget(card, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        scroll.setWidget(grid_widget)
        self.layout.addWidget(scroll)

        # --- Footer ---
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 30, 0, 30)
        
        skip_btn = QPushButton("SKIP FOR NOW")
        skip_btn.setStyleSheet("color: #a98a7e; background: transparent; border: none; font-size: 12px; font-weight: bold; letter-spacing: 2px;")
        skip_btn.setCursor(Qt.PointingHandCursor)
        skip_btn.clicked.connect(self.skip_onboarding)
        
        self.selection_label = QLabel("CURRENT SELECTION\n0 Categories Selected")
        self.selection_label.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        self.selection_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.continue_btn = AnimatedSolidButton("CONTINUE DISCOVERY →")
        self.continue_btn.setObjectName("primarySolidBtn")
        self.continue_btn.setFixedHeight(50)
        self.continue_btn.setFixedWidth(280)
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.setEnabled(False)
        self.continue_btn.clicked.connect(self.save_and_continue)

        self.continue_wrapper = LiftWrapper(self.continue_btn, lift_px=3)
        self.continue_wrapper.setFixedWidth(280)
        
        footer_layout.addWidget(skip_btn)
        footer_layout.addStretch()
        footer_layout.addWidget(self.selection_label)
        footer_layout.addSpacing(30)
        footer_layout.addWidget(self.continue_wrapper)
        
        self.layout.addLayout(footer_layout)

    def skip_onboarding(self):
        self.interests_saved.emit()

    def toggle_interest(self, interest, is_checked):
        if is_checked:
            self.selected_interests.add(interest)
        else:
            self.selected_interests.discard(interest)
            
        count = len(self.selected_interests)
        self.selection_label.setText(f"CURRENT SELECTION\n{count} Categories Selected")
        enabled = count >= 2
        self.continue_btn.setEnabled(enabled)
        # Reset lift when disabled so it starts at rest next time it's enabled
        if not enabled:
            self.continue_wrapper.anim.stop()
            self.continue_wrapper.y_offset = 0.0
            self.continue_wrapper.layout().setContentsMargins(0, self.continue_wrapper.lift_px, 0, 0)

    def save_and_continue(self):
        self.continue_btn.setEnabled(False)
        self.continue_btn.setText("INITIALIZING...")
        
        categories = list(self.selected_interests)
        client.save_interests(categories, self._on_save_success, self._on_save_error)

    def _on_save_success(self, data):
        self.continue_btn.setText("CONTINUE DISCOVERY →")
        self.interests_saved.emit()

    def _on_save_error(self, error_msg):
        self.continue_btn.setEnabled(True)
        self.continue_btn.setText("CONTINUE DISCOVERY →")
