import persistent
import re
from abc import ABC, abstractmethod
from datetime import datetime
class AbstractFolderItem(persistent.Persistent, ABC):
    @abstractmethod
    def to_dict(self):
        pass
class Folder(AbstractFolderItem):
    def __init__(self, name: str, is_public: bool = False, img: str = ""):
        self.name = name
        self.isPublic = is_public
        self.img = img
        self.items = [] 
    def add_item(self, item):
        self.items.append(item)
    def remove_item(self, item):
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
class VideoClip(AbstractFolderItem):
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
class LearningVideo(VideoClip):
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
            "creator": getattr(self, 'creator', 'Creator')
        }
class Playlist(persistent.Persistent):
    def __init__(self, name: str, is_public: bool = False):
        self.playlistName = name
        self.isPublic = is_public
        self.videos = [] 
    def addVideo(self, video_data: dict):
        if not any(v.get('slug') == video_data.get('slug') for v in self.videos):
            self.videos.append(video_data)
    def removeVideo(self, slug: str):
        self.videos = [v for v in self.videos if v.get('slug') != slug]
class User(persistent.Persistent):
    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password
        self.register_date = datetime.now()
        self.interests = [] 
        self.favorites = [] 
        self.history = []   
        self.playlists = {} 
        self.folders = {}   
    def createFolder(self, name: str, is_public: bool = False):
        if name not in self.folders:
            self.folders[name] = Folder(name, is_public)
            return True
        return False
    def createPlaylist(self, name: str, is_public: bool = False):
        if name not in self.playlists:
            self.playlists[name] = Playlist(name, is_public)
            return True
        return False
    @staticmethod
    def validate_password(password: str) -> bool:
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", password))
        return len(password) >= 8 and has_upper and has_digit and has_special