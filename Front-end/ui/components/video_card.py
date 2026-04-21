from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from image_cache import load_image

class VideoCard(QFrame):
    clicked = Signal(dict)

    def __init__(self, video_data):
        super().__init__()
        self.video_data = video_data
        self.setObjectName("videoCard")
        self.setFixedSize(280, 260)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(260, 146)
        self.thumb_label.setStyleSheet("background-color: #131313; border-radius: 4px;")
        self.thumb_label.setScaledContents(True)

        if "thumb" in video_data:
            load_image(video_data["thumb"], self.set_image)

        self.title_label = QLabel(video_data.get("title", "Unknown Video"))
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 5px;")
        
        details_str = f"{video_data.get('creator', '')} • {video_data.get('views', '')}"
        self.details_label = QLabel(details_str)
        self.details_label.setStyleSheet("color: #a98a7e; font-size: 12px;")

        layout.addWidget(self.thumb_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.details_label)
        layout.addStretch()

    def set_image(self, pm: QPixmap):
        self.thumb_label.setPixmap(pm)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.video_data)
        super().mousePressEvent(event)
