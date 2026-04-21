from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, 
                               QPushButton, QHBoxLayout, QMessageBox, QFrame,
                               QApplication, QStackedLayout, QStyleOptionFrame, QStyle,
                               QGraphicsOpacityEffect)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QTimer, QPoint, QRectF, QVariantAnimation
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QKeySequence, QPainterPath, QPen
import os
from api_client import client

class Toast(QWidget):
    def __init__(self, parent, message, color="#4caf50"):
        super().__init__(parent)
        self.message = message
        self.color = color
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedSize(300, 50)
        self.hide()

    def show_toast(self):
        parent_rect = self.parent().rect()
        start_y = parent_rect.height()
        end_y = parent_rect.height() - 80
        
        self.move((parent_rect.width() - self.width()) // 2, start_y)
        self.show()
        self.raise_()
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.anim_group = QParallelAnimationGroup(self)
        
        self.pos_anim = QPropertyAnimation(self, b"pos")
        self.pos_anim.setDuration(400)
        self.pos_anim.setStartValue(QPoint(self.x(), start_y))
        self.pos_anim.setEndValue(QPoint(self.x(), end_y))
        self.pos_anim.setEasingCurve(QEasingCurve.OutBack)
        
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(400)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        
        self.anim_group.addAnimation(self.pos_anim)
        self.anim_group.addAnimation(self.fade_anim)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_toast)
        self.anim_group.finished.connect(lambda: self.timer.start(2000))
        
        self.anim_group.start()
        
    def hide_toast(self):
        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(300)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.finished.connect(self.hide)
        self.fade_out.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 25, 25)
        painter.fillPath(path, QColor(self.color))
        
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self.message)


class PasswordInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("webInput")
        self.setFont(QFont("Segoe UI", 14))
        self._is_password = True
        self.setAttribute(Qt.WA_MacShowFocusRect, 0)
        self.textChanged.connect(self.update)
        # Lock into Password mode so Windows never clears the text
        self.setEchoMode(QLineEdit.Password)

    def setPasswordMode(self, is_password):
        # We only change our internal boolean, NEVER the Qt EchoMode!
        # This completely bypasses the Windows bug that clears text.
        self._is_password = is_password
        self.update()

    def paintEvent(self, event):
        # Draw background and borders natively via QSS
        panel = QStyleOptionFrame()
        self.initStyleOption(panel)
        self.style().drawPrimitive(QStyle.PE_PanelLineEdit, panel, QPainter(self), self)

        if not self.text():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#e5e2e1"))
        painter.setPen(QColor("#e5e2e1"))

        margin_left = 2
        cy = self.rect().center().y()
        text_len = len(self.text())

        if self._is_password:
            # Draw dots physically
            dot_radius = 4
            spacing = 14
            for i in range(text_len):
                cx = margin_left + (i * spacing) + dot_radius
                painter.drawEllipse(cx - dot_radius, cy - dot_radius, dot_radius * 2, dot_radius * 2)
            
            if self.hasFocus():
                cursor_x = margin_left + (text_len * spacing) + 2
                painter.drawLine(cursor_x, cy - 8, cursor_x, cy + 8)
        else:
            # Draw raw text physically, ignoring Qt's EchoMode!
            rect = self.rect()
            rect.setLeft(margin_left)
            painter.setFont(self.font())
            painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, self.text())
            
            if self.hasFocus():
                fm = self.fontMetrics()
                text_width = fm.horizontalAdvance(self.text())
                cursor_x = margin_left + text_width + 2
                painter.drawLine(cursor_x, cy - 8, cursor_x, cy + 8)

    @property
    def is_masked(self):
        return self._is_password




class ClickableLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class VerticalLabel(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.setFixedWidth(40)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QColor("#4d1900"))
        font = painter.font()
        font.setPointSize(10)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 4)
        font.setBold(True)
        painter.setFont(font)
        
        # Rotate text
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(self.text)
        start_y = (self.height() / 2) + (text_width / 2)
        
        painter.translate(self.width() / 2 + 5, start_y)
        painter.rotate(-90)
        painter.drawText(0, 0, self.text)

class AnimatedEyeToggle(QLabel):
    clicked = Signal()
    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedWidth(32)
        self.setFixedHeight(32)
        
        self.is_masked = True
        
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(150)
        self.anim.valueChanged.connect(self._on_color_changed)
        self.current_color = QColor("#737373")

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self.current_color)
        self.anim.setEndValue(QColor("#f26411"))
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self.current_color)
        self.anim.setEndValue(QColor("#737373"))
        self.anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _on_color_changed(self, color):
        self.current_color = color
        self.update()

    def toggle_state(self, is_masked):
        self.is_masked = is_masked
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        
        pen = QPen(self.current_color, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        # Eye shape
        path = QPainterPath()
        path.moveTo(cx - 9, cy)
        path.quadTo(cx, cy - 6, cx + 9, cy)
        path.quadTo(cx, cy + 6, cx - 9, cy)
        painter.drawPath(path)
        
        # Pupil/Iris
        if not self.is_masked:
            painter.setBrush(self.current_color)
            painter.drawEllipse(QRectF(cx - 2.5, cy - 2.5, 5, 5))
        else:
            painter.drawEllipse(QRectF(cx - 2.5, cy - 2.5, 5, 5))
            # Slash through the eye
            painter.drawLine(cx + 6, cy - 6, cx - 6, cy + 6)

class LiftWrapper(QWidget):
    def __init__(self, child, parent=None):
        super().__init__(parent)
        self.child = child
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.child)
        
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._on_anim_changed)
        
        self.child.installEventFilter(self)
        self.y_offset = 0.0

    def eventFilter(self, obj, event):
        if obj == self.child:
            if event.type() == event.Type.Enter:
                if self.child.isEnabled() and self.child.objectName() != "authTabActive":
                    self.anim.stop()
                    self.anim.setStartValue(self.y_offset)
                    self.anim.setEndValue(3.0)
                    self.anim.start()
            elif event.type() == event.Type.Leave:
                if self.child.isEnabled() and self.child.objectName() != "authTabActive":
                    self.anim.stop()
                    self.anim.setStartValue(self.y_offset)
                    self.anim.setEndValue(0.0)
                    self.anim.start()
        return super().eventFilter(obj, event)

    def _on_anim_changed(self, offset):
        self.y_offset = offset
        mt = 3 - int(round(offset))
        mb = int(round(offset))
        self.layout().setContentsMargins(0, mt, 0, mb)

class AnimatedTabButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._on_anim_changed)
        self.current_color = QColor("#737373")

    def enterEvent(self, event):
        if self.objectName() != "authTabActive":
            self.anim.stop()
            self.anim.setStartValue(self.current_color)
            self.anim.setEndValue(QColor("#a6a6a6"))
            self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.objectName() != "authTabActive":
            self.anim.stop()
            self.anim.setStartValue(self.current_color)
            self.anim.setEndValue(QColor("#737373"))
            self.anim.start()
        super().leaveEvent(event)

    def _on_anim_changed(self, color):
        if isinstance(color, QColor):
            self.current_color = color
            if self.objectName() != "authTabActive":
                self.setStyleSheet(f"QPushButton {{ color: {self.current_color.name()}; background: transparent; border: none; border-bottom: 2px solid transparent; font-weight: bold; text-transform: uppercase; font-size: 11px; padding-bottom: 8px; }}")

class AnimatedSubmitButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._on_anim_changed)
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

    def _on_anim_changed(self, color):
        if isinstance(color, QColor):
            self.current_bg = color
            self.setStyleSheet(f"QPushButton {{ background-color: {self.current_bg.name()}; color: #1a0800; font-weight: bold; font-size: 13px; text-transform: uppercase; letter-spacing: 3px; border: none; border-radius: 4px; padding: 14px; text-align: left; padding-left: 20px; }}")


class LoginView(QWidget):
    login_successful = Signal()
    needs_onboarding = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("authBackground")
        self.current_tab = "LOGIN" # LOGIN, SIGNUP, RESET
        self._setup_ui()

    def paintEvent(self, event):
        # Just a solid dark background for the whole window
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0e0e0e"))
        super().paintEvent(event)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        self.container = QFrame()
        self.container.setFixedWidth(600)
        self.container.setObjectName("loginContainer")
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Left Orange Strip
        self.brand_panel = QFrame()
        self.brand_panel.setObjectName("authBrandPanel")
        self.brand_panel.setFixedWidth(50)
        brand_layout = QVBoxLayout(self.brand_panel)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        vert_label = VerticalLabel("THE WORLD OF LEARNING")
        brand_layout.addWidget(vert_label)

        # Right Main Panel
        self.main_panel = QFrame()
        self.main_panel.setObjectName("authMainPanel")
        main_layout_inner = QVBoxLayout(self.main_panel)
        main_layout_inner.setContentsMargins(40, 40, 40, 40)
        main_layout_inner.setSpacing(25)

        # Header
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        img_path = os.path.join(os.path.dirname(__file__), "..", "..", "imgs", "icon.png")
        if os.path.exists(img_path):
            icon_label.setPixmap(QPixmap(img_path).scaled(45, 45, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title_label = QLabel("The World of Learning")
        title_label.setObjectName("authTitle")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        main_layout_inner.addLayout(header_layout)

        # Tabs
        tabs_layout = QHBoxLayout()
        self.tab_login = AnimatedTabButton("LOGIN")
        self.tab_signup = AnimatedTabButton("SIGN UP")
        self.tab_reset = AnimatedTabButton("RESET PASSWORD")
        
        self.tab_login_wrapper = LiftWrapper(self.tab_login)
        self.tab_signup_wrapper = LiftWrapper(self.tab_signup)
        self.tab_reset_wrapper = LiftWrapper(self.tab_reset)
        
        from PySide6.QtWidgets import QSizePolicy
        for btn, wrapper in [(self.tab_login, self.tab_login_wrapper), 
                             (self.tab_signup, self.tab_signup_wrapper), 
                             (self.tab_reset, self.tab_reset_wrapper)]:
            btn.setCursor(Qt.PointingHandCursor)
            wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            tabs_layout.addWidget(wrapper)
            
        self.tab_login.clicked.connect(lambda: self.switch_mode("LOGIN"))
        self.tab_signup.clicked.connect(lambda: self.switch_mode("SIGNUP"))
        self.tab_reset.clicked.connect(lambda: self.switch_mode("RESET"))
        main_layout_inner.addLayout(tabs_layout)
        
        # Form
        self.form_layout = QVBoxLayout()
        self.form_layout.setSpacing(20)
        
        self.user_lbl = QLabel("EMAIL OR USERNAME")
        self.user_lbl.setObjectName("inputLabel")
        
        self.user_frame = QFrame()
        self.user_frame.setObjectName("inputContainer")
        self.user_input_layout = QHBoxLayout(self.user_frame)
        self.user_input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.user_input = QLineEdit()
        self.user_input.setObjectName("webInput")
        self.user_input.setFont(QFont("Segoe UI", 14))
        self.user_input.setPlaceholderText("Email or Username")
        self.user_input_layout.addWidget(self.user_input)
        
        self.pass_header_layout = QHBoxLayout()
        self.pass_lbl = QLabel("PASSWORD")
        self.pass_lbl.setObjectName("inputLabel")
        self.pass_reset_hint = ClickableLabel("RESET PASSWORD")
        self.pass_reset_hint.setObjectName("inputLabelHint")
        self.pass_reset_hint.setCursor(Qt.PointingHandCursor)
        self.pass_reset_hint.clicked.connect(lambda: self.switch_mode("RESET"))
        self.pass_header_layout.addWidget(self.pass_lbl)
        self.pass_header_layout.addStretch()
        self.pass_header_layout.addWidget(self.pass_reset_hint)
        
        # Password Input Layout with Eye
        self.pass_frame = QFrame()
        self.pass_frame.setObjectName("inputContainer")
        self.pass_input_layout = QHBoxLayout(self.pass_frame)
        self.pass_input_layout.setContentsMargins(0, 0, 0, 0)
        self.pass_input_layout.setSpacing(5)
        
        self.pass_input = PasswordInput()
        self.pass_input.setPlaceholderText("Password")
        
        self.pass_eye = AnimatedEyeToggle()
        self.pass_eye.clicked.connect(lambda: self.toggle_password_visibility(self.pass_input, self.pass_eye))
        
        self.pass_input_layout.addWidget(self.pass_input)
        self.pass_input_layout.addWidget(self.pass_eye)
        
        self.confirm_lbl = QLabel("CONFIRM PASSWORD")
        self.confirm_lbl.setObjectName("inputLabel")
        
        # Confirm Input Layout with Eye
        self.confirm_frame = QFrame()
        self.confirm_frame.setObjectName("inputContainer")
        self.confirm_input_layout = QHBoxLayout(self.confirm_frame)
        self.confirm_input_layout.setContentsMargins(0, 0, 0, 0)
        self.confirm_input_layout.setSpacing(5)
        
        self.confirm_input = PasswordInput()
        self.confirm_input.setPlaceholderText("Confirm Password")
        
        self.confirm_eye = AnimatedEyeToggle()
        self.confirm_eye.clicked.connect(lambda: self.toggle_password_visibility(self.confirm_input, self.confirm_eye))

        self.confirm_input_layout.addWidget(self.confirm_input)
        self.confirm_input_layout.addWidget(self.confirm_eye)

        # Setup focus highlighting for containers
        self.user_input.installEventFilter(self)
        self.pass_input.installEventFilter(self)
        self.confirm_input.installEventFilter(self)

        self.form_layout.addWidget(self.user_lbl)
        self.form_layout.addWidget(self.user_frame)
        
        self.pass_widget = QWidget()
        self.pass_opacity = QGraphicsOpacityEffect(self.pass_widget)
        self.pass_widget.setGraphicsEffect(self.pass_opacity)
        pw_layout = QVBoxLayout(self.pass_widget)
        pw_layout.setContentsMargins(0, 0, 0, 0)
        pw_layout.setSpacing(5)
        pw_layout.addLayout(self.pass_header_layout)
        pw_layout.addWidget(self.pass_frame)
        self.form_layout.addWidget(self.pass_widget)
        
        self.confirm_widget = QWidget()
        self.confirm_opacity = QGraphicsOpacityEffect(self.confirm_widget)
        self.confirm_widget.setGraphicsEffect(self.confirm_opacity)
        cw_layout = QVBoxLayout(self.confirm_widget)
        cw_layout.setContentsMargins(0, 0, 0, 0)
        cw_layout.setSpacing(5)
        cw_layout.addWidget(self.confirm_lbl)
        cw_layout.addWidget(self.confirm_frame)
        self.form_layout.addWidget(self.confirm_widget)

        main_layout_inner.addLayout(self.form_layout)
        # Removed stretch to tightly pack elements

        self.submit_btn = AnimatedSubmitButton()
        self.submit_btn.setObjectName("primarySolidBtn")
        self.submit_btn.setCursor(Qt.PointingHandCursor)
        self.submit_btn.setFixedHeight(45)
        
        btn_layout = QHBoxLayout(self.submit_btn)
        btn_layout.setContentsMargins(20, 0, 20, 0)
        self.btn_text_label = QLabel("LOGIN")
        self.btn_text_label.setStyleSheet("color: #1a0800; font-weight: bold; font-size: 13px; letter-spacing: 3px; background: transparent;")
        self.btn_arrow_label = QLabel("→")
        self.btn_arrow_label.setStyleSheet("color: #1a0800; font-weight: bold; font-size: 16px; background: transparent;")
        btn_layout.addWidget(self.btn_text_label)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_arrow_label)
        
        self.submit_btn.clicked.connect(self.handle_submit)
        
        self.submit_wrapper = LiftWrapper(self.submit_btn)
        main_layout_inner.addWidget(self.submit_wrapper)

        container_layout.addWidget(self.brand_panel)
        container_layout.addWidget(self.main_panel)
        main_layout.addWidget(self.container)

        self.switch_mode("LOGIN")

    def switch_mode(self, mode):
        self.current_tab = mode
        
        # Reset all tabs
        for btn in [self.tab_login, self.tab_signup, self.tab_reset]:
            btn.setObjectName("authTabInactive")
            btn.setStyleSheet("")
            btn.current_color = QColor("#737373")
            
            # Reset lift wrapper safely
            wrapper = btn.parent()
            if isinstance(wrapper, LiftWrapper):
                wrapper.y_offset = 0.0
                wrapper.layout().setContentsMargins(0, 3, 0, 0)
            
        show_pass = False
        show_confirm = False
            
        if mode == "LOGIN":
            self.tab_login.setObjectName("authTabActive")
            show_pass = True
            show_confirm = False
            self.btn_text_label.setText("LOGIN")
            self.pass_reset_hint.show()
        elif mode == "SIGNUP":
            self.tab_signup.setObjectName("authTabActive")
            show_pass = True
            show_confirm = True
            self.btn_text_label.setText("SIGN UP")
            self.pass_reset_hint.hide()
        elif mode == "RESET":
            self.tab_reset.setObjectName("authTabActive")
            show_pass = False
            show_confirm = False
            self.btn_text_label.setText("SEND RESET LINK")
            self.pass_reset_hint.hide()
            
        for btn in [self.tab_login, self.tab_signup, self.tab_reset]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # We will animate the container itself instead of the internal widgets
        # to ensure the "auth card" physically expands smoothly.
        old_height = self.container.height()
        
        self.pass_widget.setVisible(show_pass)
        self.confirm_widget.setVisible(show_confirm)
        
        # Calculate new container height after visibility changes
        self.container.setMinimumHeight(0)
        self.container.setMaximumHeight(16777215)
        QApplication.processEvents()
        new_height = self.container.sizeHint().height()
        
        # Lock container height back to old_height to start animation
        self.container.setMinimumHeight(old_height)
        self.container.setMaximumHeight(old_height)
        
        self.anim_group = QParallelAnimationGroup(self)
        
        anim_container_min = QPropertyAnimation(self.container, b"minimumHeight")
        anim_container_min.setDuration(350)
        anim_container_min.setStartValue(old_height)
        anim_container_min.setEndValue(new_height)
        anim_container_min.setEasingCurve(QEasingCurve.InOutQuad)
        
        anim_container_max = QPropertyAnimation(self.container, b"maximumHeight")
        anim_container_max.setDuration(350)
        anim_container_max.setStartValue(old_height)
        anim_container_max.setEndValue(new_height)
        anim_container_max.setEasingCurve(QEasingCurve.InOutQuad)
        
        anim_pass_op = QPropertyAnimation(self.pass_opacity, b"opacity")
        anim_pass_op.setDuration(350)
        anim_pass_op.setStartValue(self.pass_opacity.opacity())
        anim_pass_op.setEndValue(1.0 if show_pass else 0.0)
        
        anim_confirm_op = QPropertyAnimation(self.confirm_opacity, b"opacity")
        anim_confirm_op.setDuration(350)
        anim_confirm_op.setStartValue(self.confirm_opacity.opacity())
        anim_confirm_op.setEndValue(1.0 if show_confirm else 0.0)
        
        self.anim_group.addAnimation(anim_container_min)
        self.anim_group.addAnimation(anim_container_max)
        self.anim_group.addAnimation(anim_pass_op)
        self.anim_group.addAnimation(anim_confirm_op)
        
        self.anim_group.start()

    def toggle_password_visibility(self, input_widget, eye_widget):
        new_mode = not input_widget.is_masked
        input_widget.setPasswordMode(new_mode)
        eye_widget.toggle_state(new_mode)

    def eventFilter(self, obj, event):
        if event.type() == event.Type.FocusIn:
            if obj == self.user_input:
                self.user_frame.setProperty("focused", True)
                self.user_frame.style().unpolish(self.user_frame)
                self.user_frame.style().polish(self.user_frame)
            elif obj == self.pass_input:
                self.pass_frame.setProperty("focused", True)
                self.pass_frame.style().unpolish(self.pass_frame)
                self.pass_frame.style().polish(self.pass_frame)
            elif obj == self.confirm_input:
                self.confirm_frame.setProperty("focused", True)
                self.confirm_frame.style().unpolish(self.confirm_frame)
                self.confirm_frame.style().polish(self.confirm_frame)
        elif event.type() == event.Type.FocusOut:
            if obj == self.user_input:
                self.user_frame.setProperty("focused", False)
                self.user_frame.style().unpolish(self.user_frame)
                self.user_frame.style().polish(self.user_frame)
            elif obj == self.pass_input:
                self.pass_frame.setProperty("focused", False)
                self.pass_frame.style().unpolish(self.pass_frame)
                self.pass_frame.style().polish(self.pass_frame)
            elif obj == self.confirm_input:
                self.confirm_frame.setProperty("focused", False)
                self.confirm_frame.style().unpolish(self.confirm_frame)
                self.confirm_frame.style().polish(self.confirm_frame)
        return super().eventFilter(obj, event)

    def handle_submit(self):
        username = self.user_input.text()
        password = self.pass_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please fill in all fields.")
            return

        self.submit_btn.setEnabled(False)
        
        if self.current_tab == "LOGIN":
            self.btn_text_label.setText("LOGGING IN...")
            client.login(username, password, self._on_success, self._on_error)
        elif self.current_tab == "SIGNUP":
            if password != self.confirm_input.text():
                QMessageBox.warning(self, "Error", "Passwords do not match.")
                self.submit_btn.setEnabled(True)
                return
            self.btn_text_label.setText("REGISTERING...")
            client.register(username, password, self._on_success, self._on_error)
        else:
            QMessageBox.information(self, "Info", "Password reset link sent (simulated).")
            self.submit_btn.setEnabled(True)

    def _on_success(self, data):
        self.submit_btn.setEnabled(True)
        if self.current_tab == "SIGNUP":
            self.btn_text_label.setText("SIGN UP")
            self.toast = Toast(self, "Account created successfully!", color="#f26411")
            self.toast.show_toast()
            QTimer.singleShot(2500, lambda: self.switch_mode("LOGIN"))
        else:
            self.btn_text_label.setText("LOGIN")
            client.current_username = data.get("username")
            if data.get("needs_interests"):
                self.needs_onboarding.emit()
            else:
                self.login_successful.emit()

    def _on_error(self, error_msg):
        self.submit_btn.setEnabled(True)
        btn_text = "LOGIN" if self.current_tab == "LOGIN" else "SIGN UP"
        self.btn_text_label.setText(btn_text)
        QMessageBox.critical(self, "Authentication Failed", error_msg)
