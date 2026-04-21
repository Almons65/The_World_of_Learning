"""
folder_store.py — Personal Folders backed by ZODB via API.
Falls back to QSettings cache so the UI works even when the API is unavailable.
"""
import json
import requests
from PySide6.QtCore import QSettings

API_BASE = "http://127.0.0.1:8002/api"
_SETTINGS = QSettings("WoL", "PersonalFolders")


def _cache_key(username: str) -> str:
    return f"ARC_PERSONAL_FOLDERS_{username or '_guest'}"


# ── Read ──────────────────────────────────────────────────────────────────────

def get_user_folders(username: str = "") -> list:
    """Fetch folders from ZODB backend; fall back to local QSettings cache."""
    if username:
        try:
            # Very short timeout to prevent UI freeze. 
            # If it fails, we use the local cache immediately.
            r = requests.get(f"{API_BASE}/user/{username}/personal-folders", timeout=1.5)
            if r.status_code == 200:
                folders = r.json().get("folders", [])
                _SETTINGS.setValue(_cache_key(username), json.dumps(folders))
                return folders
        except Exception:
            # Silent fallback to cache for better UX
            pass

    # Fall back to local cache
    val = _SETTINGS.value(_cache_key(username))
    if val:
        try:
            return json.loads(val)
        except Exception as e:
            print(f"[folder_store] Cache parse error: {e}")
    return []


# ── Write ─────────────────────────────────────────────────────────────────────

def save_user_folders(username: str, data: list) -> None:
    """Save the full folders list to ZODB backend and local QSettings cache."""
    # Always update local cache immediately (fast)
    _SETTINGS.setValue(_cache_key(username), json.dumps(data))

    if username:
        try:
            requests.post(
                f"{API_BASE}/personal-folders/save",
                json={"username": username, "folders": data},
                timeout=5,
            )
        except Exception as e:
            print(f"[folder_store] Failed to persist to ZODB: {e}")
