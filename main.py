import sys
import os
import subprocess
import time
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import QUrl, Qt, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView

class WebContainerWindow(QMainWindow):
    def __init__(self, backend_proc, frontend_proc):
        super().__init__()
        self.backend_proc = backend_proc
        self.frontend_proc = frontend_proc
        
        self.setWindowTitle("The World of Learning")
        self.resize(1280, 720)
        
        # You can optionally make it frameless for a full modern desktop feel:
        # self.setWindowFlag(Qt.FramelessWindowHint)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Show loading screen initially
        self.loading_label = QLabel("Initializing the Global Archive...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("background-color: #0e0e0e; color: #ffb596; font-size: 24px; font-family: sans-serif;")
        self.layout.addWidget(self.loading_label)
        
        self.web_view = QWebEngineView()
        self.web_view.hide()
        self.layout.addWidget(self.web_view)
        
        # Wait a moment for Vite and FastAPI to start, then load URL
        QTimer.singleShot(3000, self.load_webapp)
        
    def load_webapp(self):
        self.loading_label.hide()
        self.web_view.show()
        self.web_view.setUrl(QUrl("http://127.0.0.1:8003/"))

    def closeEvent(self, event):
        """Ensure subprocesses are killed when the window is closed."""
        print("Shutting down servers...")
        try:
            # Kill the process trees on Windows
            if self.backend_proc:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.backend_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if self.frontend_proc:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.frontend_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Error terminating processes: {e}")
        event.accept()

def start_servers():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "Back-end")
    frontend_dir = os.path.join(base_dir, "Front-end")
    
    print("Starting Backend (FastAPI)...")
    # Need to use python -m uvicorn on Windows to avoid path issues
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=backend_dir,
        shell=False
    )
    
    print("Starting Frontend (Vite)...")
    frontend_proc = subprocess.Popen(
        "npm run dev -- --port 8003",
        cwd=frontend_dir,
        shell=True
    )
    
    return backend_proc, frontend_proc

def main():
    app = QApplication(sys.argv)
    
    # Start the background servers
    backend_proc, frontend_proc = start_servers()
    
    window = WebContainerWindow(backend_proc, frontend_proc)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
