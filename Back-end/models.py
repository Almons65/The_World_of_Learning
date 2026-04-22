import persistent
import re
from abc import ABC, abstractmethod
from datetime import datetime

class MediaItem(persistent.Persistent, ABC):
    @abstractmethod
    def to_dict(self):
        pass

class UserFolders(MediaItem):
    def __init__(self, name: str, is_public: bool = False, img: str = ""):
        self.name = name
        self.isPublic = is_public
        self.img = img
        self.items = [] 
    def add_item(self, item: MediaItem):
        self.items.append(item)
    def remove_item(self, item: MediaItem):
        if item in self.items:
            self.items.remove(item)
    def to_dict(self):
        serialized_items = []
        for item in self.items:
            if hasattr(item, 'to_dict'):
                serialized_items.append(item.to_dict())
            else:
                serialized_items.append(item)
        derived_img = self.img
        if not derived_img:
            for item in serialized_items:
                if isinstance(item, dict):
                    if item.get("thumb"):
                        derived_img = item["thumb"]
                        break
                    if item.get("img"):
                        derived_img = item["img"]
                        break
        return {
            "type": "folder",
            "name": self.name,
            "img": derived_img,
            "is_public": self.isPublic,
            "items": serialized_items
        }
class VideoClip(MediaItem):
    def __init__(self, slug: str, title: str, desc: str, tag: str, img: str, parent_slug: str, views: str = "0 views", date: str = "Unknown", creator: str = "Creator"):
        self.slug = slug
        self.title = title
        self.desc = desc          
        self.tag = tag            
        self.img = img            
        self.parent_slug = parent_slug
        self.views = views
        self.date = date
        self.creator = creator
        self.view_count = 0
    @abstractmethod
    def to_dict(self):
        pass
class Video(VideoClip):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local_path = None
        self.is_downloaded = False

    def to_dict(self):
        return {
            "type": "file",
            "slug": getattr(self, 'slug', ''),
            "title": getattr(self, 'title', 'Unknown Title'),
            "desc": getattr(self, 'desc', ''),
            "tag": getattr(self, 'tag', ''),
            "thumb": getattr(self, 'img', ''),
            "parent_slug": getattr(self, 'parent_slug', '/home'),
            "views": getattr(self, 'views', '0 views'),
            "date": getattr(self, 'date', 'Unknown'),
            "creator": getattr(self, 'creator', 'Creator'),
            "local_path": getattr(self, 'local_path', None),
            "is_downloaded": getattr(self, 'is_downloaded', False)
        }
class User(persistent.Persistent):
    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password
        self.register_date = datetime.now()
        self.interests = [] 
        self.favorites = [] 
        self.history = []   
        self.discovery_feed = [] # Persistent storage for the initial AI Discovery results
        self.expanded_feed = [] # Persistent storage for "Explore Deeper" results
        self.folders = {}   # Consolidating all collections (Folders/Playlists) here
        
    def createFolder(self, name: str, is_public: bool = False):
        if name not in self.folders:
            self.folders[name] = UserFolders(name, is_public)
            return True
        return False
    
    def createPlaylist(self, name: str, is_public: bool = False):
        # Map Playlist creation to UserFolders for a unified experience
        return self.createFolder(name, is_public)
    @staticmethod
    def validate_password(password: str) -> bool:
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", password))
        return len(password) >= 8 and has_upper and has_digit and has_special