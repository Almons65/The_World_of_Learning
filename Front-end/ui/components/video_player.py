"""Native video player widget using QMediaPlayer + custom controls."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QSizePolicy, QGraphicsOpacityEffect, QComboBox
)
from PySide6.QtCore import Qt, QUrl, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtGui import QCursor


def _fmt_time(ms):
    s = max(0, ms // 1000)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class VolumeIconWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)

    def paintEvent(self, e):
        from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(170, 170, 170))
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)

        path = QPainterPath()
        path.moveTo(8, 9)
        path.lineTo(4, 9)
        path.lineTo(4, 15)
        path.lineTo(8, 15)
        path.lineTo(13, 20)
        path.lineTo(13, 4)
        path.closeSubpath()
        p.drawPath(path)

        path2 = QPainterPath()
        path2.moveTo(17, 8)
        path2.quadTo(20, 12, 17, 16)
        p.drawPath(path2)


class PlayPauseButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.is_playing = False
        self._hovered = False

    def set_playing(self, playing):
        self.is_playing = playing
        self.update()

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, e):
        from PySide6.QtGui import QPainter, QBrush, QColor, QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Draw background circle
        bg_color = QColor(220, 220, 220) if self._hovered else QColor(255, 255, 255)
        p.setBrush(QBrush(bg_color))
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, 32, 32)

        # Draw icon
        p.setBrush(QBrush(QColor(0, 0, 0)))
        if self.is_playing:
            # Draw pause bars
            p.drawRect(10, 10, 4, 12)
            p.drawRect(18, 10, 4, 12)
        else:
            # Draw play triangle
            path = QPainterPath()
            path.moveTo(13, 10)
            path.lineTo(23, 16)
            path.lineTo(13, 22)
            path.closeSubpath()
            p.drawPath(path)


class LoadingSpinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)

    def showEvent(self, e):
        self._timer.start(16)
        super().showEvent(e)

    def hideEvent(self, e):
        self._timer.stop()
        super().hideEvent(e)

    def _rotate(self):
        self._angle = (self._angle + 8) % 360
        self.update()

    def paintEvent(self, e):
        from PySide6.QtGui import QPainter, QPen, QColor, QBrush
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Dark circular background
        p.setBrush(QBrush(QColor(0, 0, 0, 160)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, self.width(), self.height())

        # Spinner parameters
        margin = 16
        rect = self.rect().adjusted(margin, margin, -margin, -margin)

        # Draw background track
        bg_pen = QPen(QColor(255, 255, 255, 40))
        bg_pen.setWidth(4)
        p.setPen(bg_pen)
        p.drawArc(rect, 0, 360 * 16)

        # Draw spinning arc
        pen = QPen(QColor(242, 100, 17)) # #f26411
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, -self._angle * 16, 120 * 16)


class VideoPlayerWidget(QWidget):
    """Custom native video player with overlay controls."""
    playback_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(720)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background: #000; border-radius: 20px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video surface
        self._video_widget = QVideoWidget()
        self._video_widget.setStyleSheet("background: #000;")
        layout.addWidget(self._video_widget, 1)

        # Media player
        self._audio = QAudioOutput()
        self._audio.setVolume(0.7)
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video_widget)
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.errorOccurred.connect(self._on_error)
        self._player.playbackStateChanged.connect(self._on_state_change)

        # Controls overlay
        self._controls = self._build_controls()
        layout.addWidget(self._controls)

        # Loading spinner (centered overlay)
        self._loading = LoadingSpinner(self)
        self._loading.hide()

        self._seeking = False

    def _build_controls(self):
        frame = QFrame()
        frame.setFixedHeight(50)
        frame.setObjectName("PlayerControlsFrame")
        frame.setStyleSheet(
            "#PlayerControlsFrame { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(0,0,0,0), stop:1 rgba(0,0,0,0.8)); "
            "border-bottom-left-radius: 20px; border-bottom-right-radius: 20px; border: none; }")

        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(16)

        # Play/Pause
        self._play_btn = PlayPauseButton()
        self._play_btn.clicked.connect(self._toggle_play)
        lay.addWidget(self._play_btn)

        # Time
        self._time_lbl = QLabel("0:00")
        self._time_lbl.setObjectName("PlayerTimeLbl")
        self._time_lbl.setStyleSheet("#PlayerTimeLbl { color: white; font-size: 12px; font-weight: bold; background-color: transparent; border: none; padding: 0; margin: 0; }")
        self._time_lbl.setFixedWidth(45)
        lay.addWidget(self._time_lbl)

        # Seek slider
        self._seek = QSlider(Qt.Horizontal)
        self._seek.setRange(0, 0)
        self._seek.setCursor(QCursor(Qt.PointingHandCursor))
        self._seek.setStyleSheet("""
            QSlider::groove:horizontal { background-color: rgba(255,255,255,0.3); height: 4px; border-radius: 2px; border: none; }
            QSlider::handle:horizontal { background-color: #f26411; width: 12px; height: 12px;
                margin: -4px 0; border-radius: 6px; border: none; }
            QSlider::sub-page:horizontal { background-color: #f26411; border-radius: 2px; }
        """)
        self._seek.sliderPressed.connect(lambda: setattr(self, '_seeking', True))
        self._seek.sliderReleased.connect(self._on_seek_release)
        lay.addWidget(self._seek, 1)

        # Duration
        self._dur_lbl = QLabel("0:00")
        self._dur_lbl.setObjectName("PlayerDurLbl")
        self._dur_lbl.setStyleSheet("#PlayerDurLbl { color: white; font-size: 12px; font-weight: bold; background-color: transparent; border: none; padding: 0; margin: 0; }")
        self._dur_lbl.setFixedWidth(45)
        lay.addWidget(self._dur_lbl)

        # Volume
        vol_icon = VolumeIconWidget()
        lay.addWidget(vol_icon)

        self._vol = QSlider(Qt.Horizontal)
        self._vol.setFixedWidth(80)
        self._vol.setRange(0, 100)
        self._vol.setValue(70)
        self._vol.setCursor(QCursor(Qt.PointingHandCursor))
        self._vol.setStyleSheet("""
            QSlider::groove:horizontal { background-color: transparent; height: 4px; border: none; }
            QSlider::sub-page:horizontal { background-color: white; border-radius: 2px; }
            QSlider::add-page:horizontal { background-color: rgba(255,255,255,0.3); border-radius: 2px; }
            QSlider::handle:horizontal { background-color: transparent; width: 14px; height: 14px; margin: -5px 0; border: none; }
        """)
        self._vol.valueChanged.connect(lambda v: self._audio.setVolume(v / 100.0))
        lay.addWidget(self._vol)

        return frame

    def current_resolution(self):
        return "1080p"

    # -- Public API --
    def play_url(self, url: str):
        """Load and play a direct stream URL."""
        self._show_loading(True)
        self._player.setSource(QUrl(url))
        self._player.play()

    def stop(self):
        self._player.stop()
        self._player.setSource(QUrl())
        
    def pause(self):
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()

    def seek_to(self, ms: int):
        self._player.setPosition(ms)

    # -- Private --
    def _show_loading(self, show):
        if show:
            self._loading.move(
                (self.width() - self._loading.width()) // 2,
                (self.height() - self._loading.height()) // 2 - 30)
            self._loading.show()
        else:
            self._loading.hide()

    def _toggle_play(self):
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_state_change(self, state):
        if state == QMediaPlayer.PlayingState:
            self._play_btn.set_playing(True)
            self._show_loading(False)
        elif state == QMediaPlayer.PausedState:
            self._play_btn.set_playing(False)
        else:
            self._play_btn.set_playing(False)

    def _on_position(self, pos):
        if not self._seeking:
            self._seek.setValue(pos)
        self._time_lbl.setText(_fmt_time(pos))

    def _on_duration(self, dur):
        self._seek.setRange(0, dur)
        self._dur_lbl.setText(_fmt_time(dur))

    def _on_seek_release(self):
        self._seeking = False
        self._player.setPosition(self._seek.value())

    def _on_error(self, error, msg=""):
        self._show_loading(False)
        err_text = self._player.errorString() or str(msg)
        self.playback_error.emit(err_text)
        print(f"Player error: {error} - {err_text}")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._loading.isVisible():
            self._show_loading(True)
            
    def hasHeightForWidth(self):
        return True
        
    def heightForWidth(self, w):
        return int(w * 9 / 16)
