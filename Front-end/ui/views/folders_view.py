import uuid
import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QGridLayout, QLineEdit, QDialog, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPainter, QPixmap

from ui.folder_store import get_user_folders, save_user_folders
from image_cache import load_image


class CreateFolderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Folder")
        self.setFixedSize(440, 450)
        self.setStyleSheet("""
            QDialog{background:#1c1b1b;}
            QLabel{color:#e5e2e1;background:transparent;}
            QLineEdit{background:#131313;color:#e5e2e1;border:1px solid #353534;
                border-radius:6px;padding:12px;font-size:13px;font-weight:bold;}
            QLineEdit:focus{border-color:#f26411;}
        """)
        
        self.hero_b64 = None
        self.selected_color = "#f26411"
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        title = QLabel("Create New Folder")
        title.setStyleSheet("font-size:18px;font-weight:900;color:#ffffff;background:transparent;")
        lay.addWidget(title)

        # Name
        lay.addWidget(QLabel("FOLDER NAME"))
        self._name = QLineEdit()
        self._name.setPlaceholderText("e.g. Ancient Philosophy")
        lay.addWidget(self._name)

        # Image
        lay.addSpacing(6)
        lay.addWidget(QLabel("FOLDER IMAGE"))
        self._img_btn = QPushButton("Browse Image")
        self._img_btn.setFixedHeight(80)
        self._img_btn.setCursor(Qt.PointingHandCursor)
        self._img_btn.setStyleSheet("""
            QPushButton{background:#131313;color:rgba(255,255,255,0.4);border:2px dashed rgba(255,255,255,0.1);border-radius:6px;font-weight:bold;}
            QPushButton:hover{border-color:#f26411;color:#f26411;}
        """)
        self._img_btn.clicked.connect(self._browse_image)
        lay.addWidget(self._img_btn)

        # Color
        lay.addSpacing(14)
        lay.addWidget(QLabel("COLOR"))
        color_lay = QHBoxLayout()
        color_lay.setSpacing(12)
        self._color_btns = []
        colors = ["#f26411", "#3b82f6", "#10b981", "#8b5cf6", "#ec4899", "#f59e0b"]
        for c in colors:
            btn = QPushButton()
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"background:{c}; border-radius:16px; border: 2px solid {'#ffffff' if c == self.selected_color else 'transparent'};")
            btn.clicked.connect(lambda _, col=c, b=btn: self._select_color(col, b))
            self._color_btns.append((c, btn))
            color_lay.addWidget(btn)
        color_lay.addStretch()
        lay.addLayout(color_lay)

        lay.addStretch()

        # Buttons
        btns = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(44)
        cancel.setStyleSheet("QPushButton{background:#2a2a2a;color:#a0a0a0;border:none;border-radius:6px;font-weight:bold;}QPushButton:hover{background:#333;}")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Create Folder")
        save.setFixedHeight(44)
        save.setStyleSheet("QPushButton{background:#f26411;color:#1a0800;border:none;border-radius:6px;font-weight:bold;}QPushButton:hover{background:#ff7326;}")
        save.clicked.connect(self.accept)

        btns.addWidget(cancel)
        btns.addWidget(save)
        lay.addLayout(btns)

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.hero_b64 = path
            self._img_btn.setText(path.split("/")[-1])

    def _select_color(self, color, btn):
        self.selected_color = color
        for c, b in self._color_btns:
            b.setStyleSheet(f"background:{c}; border-radius:16px; border: 2px solid {'#ffffff' if c == self.selected_color else 'transparent'};")

    def get_data(self):
        return {
            "name": self._name.text().strip(),
            "color": self.selected_color,
            "hero_img": self.hero_b64 or "https://images.unsplash.com/photo-1614850523459-c2f4c699c52e?auto=format&fit=crop&q=80&w=1200"
        }


class FolderCard(QFrame):
    clicked = Signal(dict)
    
    def __init__(self, fd: dict, parent=None):
        super().__init__(parent)
        self._fd = fd
        self.setFixedSize(280, 280)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QFrame{background:#181818;border-radius:12px;border:2px solid transparent;} QFrame:hover{border-color:rgba(255,255,255,0.1); background:#1c1b1b;}")
        
        self._hero = QLabel(self)
        self._hero.setFixedSize(276, 276)
        self._hero.move(2, 2)
        self._hero.setStyleSheet("border-radius:10px;")
        
        overlay = QFrame(self._hero)
        overlay.setFixedSize(276, 276)
        overlay.setStyleSheet("background:rgba(0,0,0,0.6);border-radius:10px;")
        
        count = len(fd.get("items", []))
        self.badge = QLabel(f"{count} VIDEOS", self)
        self.badge.setFixedSize(80, 24)
        self.badge.move(280 - 80 - 16, 16)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setStyleSheet("background:rgba(255,255,255,0.1); color:rgba(255,255,255,0.8); border-radius:6px; font-weight:bold; font-size:10px;")
        
        self.name_lbl = QLabel(fd.get("name", ""), self)
        self.name_lbl.setFixedSize(240, 30)
        self.name_lbl.move(20, 280 - 60)
        self.name_lbl.setStyleSheet("color:#ffffff; font-size:18px; font-weight:bold; background:transparent;")
        
        self.upd_lbl = QLabel(fd.get("updated", ""), self)
        self.upd_lbl.setFixedSize(240, 20)
        self.upd_lbl.move(20, 280 - 30)
        self.upd_lbl.setStyleSheet("color:rgba(255,255,255,0.4); font-size:10px; font-weight:bold; background:transparent;")
        
        self.check_btn = QPushButton("✓", self)
        self.check_btn.setFixedSize(24, 24)
        self.check_btn.move(16, 16)
        self.check_btn.setStyleSheet("QPushButton{background:rgba(0,0,0,0.5);color:transparent;border:2px solid rgba(255,255,255,0.5);border-radius:6px;font-weight:bold;font-size:14px;}")
        self.check_btn.hide()
        
        if fd.get("hero_img"):
            img_path = fd["hero_img"]
            if img_path.startswith("http"):
                load_image(img_path, self._on_img)
            else:
                pm = QPixmap(img_path)
                self._on_img(pm)

    def _on_img(self, pm):
        if pm and not pm.isNull():
            self._hero.setPixmap(pm.scaled(276, 276, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))

    def set_checked(self, checked):
        if checked:
            self.check_btn.setStyleSheet("QPushButton{background:#f26411;color:#fff;border:none;border-radius:6px;font-weight:bold;font-size:14px;}")
            self.setStyleSheet("QFrame{background:#181818;border-radius:12px;border:2px solid #f26411;}")
        else:
            self.check_btn.setStyleSheet("QPushButton{background:rgba(0,0,0,0.5);color:transparent;border:2px solid rgba(255,255,255,0.5);border-radius:6px;font-weight:bold;font-size:14px;}")
            self.setStyleSheet("QFrame{background:#181818;border-radius:12px;border:2px solid transparent;} QFrame:hover{border-color:rgba(255,255,255,0.1); background:#1c1b1b;}")

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self._fd)
        super().mousePressEvent(e)


class FoldersView(QWidget):
    folder_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#0e0e0e;")
        self._username = ""
        self._folders = []
        self._select_mode = False
        self._selected_ids = set()
        self._cards = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 48, 48, 0)
        root.setSpacing(24)

        header = QVBoxLayout()
        header.setSpacing(8)
        
        main_title = QLabel("MY FOLDERS")
        main_title.setStyleSheet("color:#ffffff;font-size:52px;font-weight:900;letter-spacing:-2px;background:transparent;")
        header.addWidget(main_title)

        sub_title = QLabel('"Manage custom directory structures."')
        sub_title.setStyleSheet("color:rgba(255,255,255,0.4);font-size:14px;font-style:italic;background:transparent;")
        header.addWidget(sub_title)
        
        root.addLayout(header)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background:rgba(255,255,255,0.05);margin:20px 0;")
        root.addWidget(line)

        ctrl = QHBoxLayout()
        lbl = QLabel("CUSTOM FOLDERS")
        lbl.setStyleSheet("color:rgba(255,255,255,0.4);font-size:10px;font-weight:bold;letter-spacing:4px;")
        ctrl.addWidget(lbl)
        ctrl.addStretch()

        self._btn_sort = QPushButton("SORT BY ALPHABETIC")
        self._btn_sort.setCursor(Qt.PointingHandCursor)
        self._btn_sort.setStyleSheet("QPushButton{background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.5);border:1px solid rgba(255,255,255,0.1);border-radius:6px;padding:8px 16px;font-size:10px;font-weight:bold;} QPushButton:hover{color:#fff;}")
        self._btn_sort.clicked.connect(self._sort_folders)
        ctrl.addWidget(self._btn_sort)

        self._btn_select = QPushButton("SELECT")
        self._btn_select.setCursor(Qt.PointingHandCursor)
        self._btn_select.setStyleSheet("QPushButton{background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.5);border:1px solid rgba(255,255,255,0.1);border-radius:6px;padding:8px 16px;font-size:10px;font-weight:bold;} QPushButton:hover{color:#f26411;}")
        self._btn_select.clicked.connect(self._toggle_select_mode)
        ctrl.addWidget(self._btn_select)

        root.addLayout(ctrl)

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        content_w = QWidget()
        content_w.setStyleSheet("background:transparent;")
        self._grid = QGridLayout(content_w)
        self._grid.setContentsMargins(0, 0, 0, 100)
        self._grid.setSpacing(24)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll.setWidget(content_w)
        root.addWidget(scroll, 1)
        
        # Bottom Delete Bar
        self._delete_bar = QFrame(self)
        self._delete_bar.setFixedHeight(70)
        self._delete_bar.setStyleSheet("background:rgba(28,27,27,0.95);border-top:1px solid #353534;")
        db_lay = QHBoxLayout(self._delete_bar)
        db_lay.setContentsMargins(48, 0, 48, 0)
        
        self._sel_count_lbl = QLabel("0 selected")
        self._sel_count_lbl.setStyleSheet("color:#fff;font-weight:bold;font-size:14px;")
        db_lay.addWidget(self._sel_count_lbl)
        
        db_lay.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("QPushButton{background:#2a2a2a;color:#a0a0a0;border:none;border-radius:6px;padding:10px 20px;font-weight:bold;} QPushButton:hover{background:#333;color:#fff;}")
        cancel_btn.clicked.connect(self._toggle_select_mode)
        db_lay.addWidget(cancel_btn)
        
        del_btn = QPushButton("Delete Selected")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet("QPushButton{background:rgba(200,0,0,0.8);color:#fff;border:none;border-radius:6px;padding:10px 20px;font-weight:bold;} QPushButton:hover{background:red;}")
        del_btn.clicked.connect(self._delete_selected)
        db_lay.addWidget(del_btn)
        
        self._delete_bar.hide()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._delete_bar.setGeometry(0, self.height() - 70, self.width(), 70)

    def load_data(self, username: str):
        self._username = username
        self._folders = get_user_folders(username)
        self._select_mode = False
        self._selected_ids.clear()
        self._btn_select.setText("SELECT")
        self._btn_select.setStyleSheet("QPushButton{background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.5);border:1px solid rgba(255,255,255,0.1);border-radius:6px;padding:8px 16px;font-size:10px;font-weight:bold;} QPushButton:hover{color:#f26411;}")
        self._delete_bar.hide()
        self._render_grid()

    def _sort_folders(self):
        self._folders.sort(key=lambda x: x.get("name", "").lower())
        save_user_folders(self._username, self._folders)
        self._render_grid()

    def _toggle_select_mode(self):
        self._select_mode = not self._select_mode
        self._selected_ids.clear()
        
        if self._select_mode:
            self._btn_select.setText("DONE")
            self._btn_select.setStyleSheet("QPushButton{background:rgba(255,255,255,0.05);color:#f26411;border:1px solid #f26411;border-radius:6px;padding:8px 16px;font-size:10px;font-weight:bold;}")
            self._delete_bar.show()
            self._update_sel_count()
        else:
            self._btn_select.setText("SELECT")
            self._btn_select.setStyleSheet("QPushButton{background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.5);border:1px solid rgba(255,255,255,0.1);border-radius:6px;padding:8px 16px;font-size:10px;font-weight:bold;} QPushButton:hover{color:#f26411;}")
            self._delete_bar.hide()
            
        for card in self._cards:
            if self._select_mode:
                card.check_btn.show()
                card.set_checked(False)
            else:
                card.check_btn.hide()
                card.set_checked(False)

    def _on_card_clicked(self, fd: dict):
        if self._select_mode:
            fid = fd["id"]
            if fid in self._selected_ids:
                self._selected_ids.remove(fid)
            else:
                self._selected_ids.add(fid)
            self._update_sel_count()
            for card in self._cards:
                if card._fd["id"] == fid:
                    card.set_checked(fid in self._selected_ids)
        else:
            self.folder_selected.emit(fd)

    def _update_sel_count(self):
        self._sel_count_lbl.setText(f"{len(self._selected_ids)} selected")

    def _delete_selected(self):
        if not self._selected_ids: return
        self._folders = [f for f in self._folders if f["id"] not in self._selected_ids]
        save_user_folders(self._username, self._folders)
        self._toggle_select_mode()
        self._render_grid()

    def _render_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        self._cards.clear()

        create_btn = QFrame()
        create_btn.setFixedSize(280, 280)
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setStyleSheet("QFrame{background:rgba(255,255,255,0.02);border:2px dashed rgba(255,255,255,0.1);border-radius:12px;} QFrame:hover{border-color:#f26411;background:rgba(242,100,17,0.05);}")
        c_lay = QVBoxLayout(create_btn)
        c_lay.setAlignment(Qt.AlignCenter)
        c_icon = QLabel("+")
        c_icon.setAlignment(Qt.AlignCenter)
        c_icon.setFixedSize(48, 48)
        c_icon.setStyleSheet("background:#1c1b1b;color:#ffffff;font-size:24px;border-radius:8px;")
        c_lay.addWidget(c_icon, 0, Qt.AlignCenter)
        c_lay.addSpacing(16)
        c_lbl = QLabel("CREATE NEW FOLDER")
        c_lbl.setStyleSheet("color:#f26411;font-size:10px;font-weight:bold;letter-spacing:2px;")
        c_lay.addWidget(c_lbl, 0, Qt.AlignCenter)
        
        create_btn.mousePressEvent = self._on_create_click
        self._grid.addWidget(create_btn, 0, 0)

        cols = 4
        for i, f in enumerate(self._folders):
            idx = i + 1
            card = FolderCard(f)
            card.clicked.connect(self._on_card_clicked)
            if self._select_mode:
                card.check_btn.show()
                card.set_checked(f["id"] in self._selected_ids)
            self._grid.addWidget(card, idx // cols, idx % cols)
            self._cards.append(card)

    def _on_create_click(self, e):
        if e.button() == Qt.LeftButton:
            dlg = CreateFolderDialog(self)
            if dlg.exec():
                data = dlg.get_data()
                if data["name"]:
                    import uuid, datetime
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
                    self._folders.append(new_f)
                    save_user_folders(self._username, self._folders)
                    self._render_grid()
