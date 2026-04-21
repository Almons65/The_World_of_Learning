"""
Global image cache shared across all views.

Usage:
    from image_cache import load_image
    load_image(url, lambda pm: self._label.setPixmap(pm))
"""
from __future__ import annotations
import requests
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool

# ── In-memory LRU-style cache (url → QPixmap) ──────────────────────────────
_cache: dict[str, QPixmap] = {}
_MAX_SIZE = 300          # max number of cached images

# ── Dedicated thread pool (more threads than the Qt default of 4) ──────────
_pool = QThreadPool()
_pool.setMaxThreadCount(16)


class _Sig(QObject):
    ready = Signal(QPixmap)


class _Loader(QRunnable):
    def __init__(self, url: str, sig: _Sig):
        super().__init__()
        self.setAutoDelete(True)
        self._url = url
        self._sig = sig

    def run(self):
        try:
            r = requests.get(self._url, timeout=12,
                             headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                img = QImage()
                img.loadFromData(r.content)
                if not img.isNull():
                    pm = QPixmap.fromImage(img)
                    # Evict oldest entry if cache is full
                    if len(_cache) >= _MAX_SIZE:
                        _cache.pop(next(iter(_cache)))
                    _cache[self._url] = pm
                    self._sig.ready.emit(pm)
        except Exception:
            pass


def load_image(url: str, callback) -> bool:
    """
    Load image from cache (instant) or download asynchronously.
    `callback` receives a single QPixmap argument.
    Returns True if served from cache immediately.
    """
    if not url:
        return False

    if url in _cache:
        callback(_cache[url])
        return True

    sig = _Sig()
    sig.ready.connect(callback)
    _pool.start(_Loader(url, sig))
    return False
