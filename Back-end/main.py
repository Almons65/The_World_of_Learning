from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from models import User, Video, UserFolders
from database import db
# from services import GeminiAI, YouTubeAPI (Imported via system)
import os
import json
import requests
import re
import concurrent.futures
from dotenv import load_dotenv


load_dotenv(override=True)
load_dotenv("youtube_api.env", override=True) 

app = FastAPI(title="The World of Learning API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Services are now managed by the System class

GLOBAL_AI_HISTORY = []

def parse_yt_duration(duration: str) -> str:
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return duration
    
    hours, minutes, seconds = match.groups()
    hours = int(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    seconds = int(seconds) if seconds else 0
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d} hr"
    else:
        return f"{minutes}:{seconds:02d} min"


class AuthPayload(BaseModel):
    email: str = None
    username: str = None
    password: str

class VideoPayload(BaseModel):
    username: str
    video_data: dict

class InterestPayload(BaseModel):
    username: str
    categories: list[str]

class PlaylistCreatePayload(BaseModel):
    username: str
    playlist_name: str
    is_public: bool = False

class PlaylistVideoPayload(BaseModel):
    username: str
    playlist_name: str
    video_data: dict

class YouTubeRequest(BaseModel):
    video_id: str

class PredictPayload(BaseModel):
    username: str
    prompt: str


class VideoChatPayload(BaseModel):
    video_id: str
    video_title: str
    video_desc: str
    duration: str = "14:00"
    question: str

class VideoSuggestPayload(BaseModel):
    video_title: str
    video_desc: str

class SearchDomainsPayload(BaseModel):
    query: str
    username: str = None

class ExploreAppendPayload(BaseModel):
    username: str = None
    current_domain_names: list[str] = []
    page: int = 0

@app.get("/api/test")
async def test_api():
    return {"status": "ok", "message": "The World of Learning API is online"}

@app.on_event("startup")
async def startup_event():
    import seed_db

    if not db.root.get('global_categories'):
        print("Global categories missing. Seeding Database...")
        try:
            seed_db.seed_database()
        except Exception as e:
            print(f"Error seeding database: {e}")
            

    if 'demo' not in db.root['users']:
        print("Demo user missing. Creating `demo` account...")
        db.root['users']['demo'] = User('demo', 'demo@worldoflearning.org', 'Demo!123')
        db.commit()


@app.post("/api/register")
async def register_user(data: AuthPayload):
    username = data.username or data.email 
    
    if not User.validate_password(data.password):
        raise HTTPException(status_code=400, detail="Password must contain uppercase, numeric, and special character")
        
    if username in db.root['users']:
        raise HTTPException(status_code=400, detail="User already exists")
        
    db.root['users'][username] = User(username, data.email, data.password)
    db.commit()
    return {"message": "Registration successful", "username": username}

@app.post("/api/login")
async def login_user(data: AuthPayload):
    username = data.username or data.email
    user = db.root['users'].get(username)
    
    if not user or user.password != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    needs_interests = len(getattr(user, 'interests', [])) == 0
    return {"message": "Login successful", "username": username, "needs_interests": needs_interests}

@app.post("/api/user/interests")
async def save_interests(data: InterestPayload):
    user = db.root['users'].get(data.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.interests = data.categories
    db.commit()
    return {"message": "Interests saved successfully"}

@app.post("/api/favorites/add")
async def add_favorite(data: VideoPayload):
    user = db.root['users'].get(data.username)
    if user:
        if not any(f['slug'] == data.video_data.get('slug') for f in user.favorites):
            user.favorites.append(data.video_data)
            db.commit()
        return {"message": "Added to favorites"}
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/api/history/add")
async def add_history(data: VideoPayload):
    user = db.root['users'].get(data.username)
    if user:
        slug = data.video_data.get('slug', '')
        user.history = [h for h in user.history if h.get('slug') != slug]
        user.history.insert(0, data.video_data)
        user.history = user.history[:100]
        db.commit()
        return {"message": "History updated"}
    raise HTTPException(status_code=404, detail="User not found")

@app.delete("/api/user/{username}/history")
async def clear_history(username: str):
    user = db.root['users'].get(username)
    if user:
        user.history = []
        db.commit()
        return {"message": "History cleared"}
    raise HTTPException(status_code=404, detail="User not found")

@app.delete("/api/favorites/remove/{username}/{slug}")
async def remove_favorite(username: str, slug: str):
    user = db.root['users'].get(username)
    if user:
        original_len = len(user.favorites)
        user.favorites = [f for f in user.favorites if f.get('slug') != slug]
        if len(user.favorites) < original_len:
            db.commit()
            return {"message": f"Removed '{slug}' from favorites"}
        return {"message": "Video was not in favorites"}
    raise HTTPException(status_code=404, detail="User not found")

# Consolidated: Playlists are now Folders. Use /api/personal-folders endpoints.

# ── Personal Folders CRUD ──────────────────────────────────────────────────────
class PersonalFolderPayload(BaseModel):
    username: str
    folder_id: str
    name: str
    color: str = "#f26411"
    hero_img: str = ""

class PersonalFolderVideoPayload(BaseModel):
    username: str
    folder_id: str
    video_data: dict

class PersonalFolderSavePayload(BaseModel):
    username: str
    folders: list  # full list as dicts

@app.get("/api/user/{username}/personal-folders")
async def get_personal_folders(username: str):
    user = db.root['users'].get(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    pf = getattr(user, 'personal_folders', [])
    return {"folders": pf}

@app.post("/api/personal-folders/save")
async def save_personal_folders(data: PersonalFolderSavePayload):
    user = db.root['users'].get(data.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not hasattr(user, 'personal_folders'):
        user.personal_folders = []
    user.personal_folders = list(data.folders)
    user._p_changed = True
    db.commit()
    return {"message": "Folders saved", "count": len(data.folders)}

@app.post("/api/personal-folders/add-video")
async def add_video_to_personal_folder(data: PersonalFolderVideoPayload):
    user = db.root['users'].get(data.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not hasattr(user, 'personal_folders'):
        user.personal_folders = []
    for f in user.personal_folders:
        if isinstance(f, dict) and f.get("id") == data.folder_id:
            items = f.setdefault("items", [])
            slug = data.video_data.get("slug", "")
            if not any(v.get("slug") == slug for v in items):
                items.append(data.video_data)
            user._p_changed = True
            db.commit()
            return {"message": "Video added to folder"}
    raise HTTPException(status_code=404, detail="Folder not found")

@app.delete("/api/personal-folders/{username}/{folder_id}/video/{slug}")
async def remove_video_from_personal_folder(username: str, folder_id: str, slug: str):
    user = db.root['users'].get(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not hasattr(user, 'personal_folders'):
        raise HTTPException(status_code=404, detail="No folders found")
    for f in user.personal_folders:
        if isinstance(f, dict) and f.get("id") == folder_id:
            f["items"] = [v for v in f.get("items", []) if v.get("slug") != slug]
            user._p_changed = True
            db.commit()
            return {"message": "Video removed"}
    raise HTTPException(status_code=404, detail="Folder not found")



@app.get("/api/user/{username}/profile")
async def get_user_profile(username: str):
    user = db.root['users'].get(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        serialized_folders = []
        for f in getattr(user, 'folders', {}).values():
            if hasattr(f, 'to_dict'):
                serialized_folders.append(f.to_dict())
            elif isinstance(f, dict):
                serialized_folders.append(f)
    except Exception as e:
        print(f"Profile folder serialization error: {e}")
        serialized_folders = []

    return {
        "username": getattr(user, 'username', username),
        "interests": getattr(user, 'interests', []),
        "history": getattr(user, 'history', []),
        "favorites": getattr(user, 'favorites', []),
        "folders": serialized_folders
    }



@app.post("/api/youtube/fetch")
def fetch_youtube_data(data: YouTubeRequest):
    result = system.yt.fetch_video_data(data.video_id)
    if not result:
        raise HTTPException(status_code=404, detail="Video not found or API key error")
    return result

class DownloadRequest(BaseModel):
    video_id: str
    username: str = None
    save_path: str = None

@app.post("/api/youtube/download")
async def download_video(data: DownloadRequest):
    result = system.download(data.video_id, data.username, data.save_path)
    if result["status"] == "success":
        return result
    raise HTTPException(status_code=500, detail=result.get("error", "Download failed"))

class StreamRequest(BaseModel):
    video_id: str
    resolution: str = "1080p"

@app.post("/api/youtube/stream-url")
async def get_stream_url(data: StreamRequest):
    result = system.yt.get_stream_url(data.video_id, data.resolution)
    if not result:
        raise HTTPException(status_code=404, detail="Could not extract stream URL")
    return result

from system import system

@app.get("/api/youtube/explore")
async def fetch_youtube_explore(username: str = None, page: int = 0):
    try:
        categories = system.explore(username, page)
        return {"categories": categories, "theme": f"Advanced Exploration Vol. {page + 1}"}
    except Exception as e:
        print(f"Explore Error: {e}")
        return {"categories": [], "theme": "Offline Mode"}
        
@app.post("/api/youtube/explore-append")
async def explore_append(data: ExploreAppendPayload):
    try:
        categories = system.explore_append(data.current_domain_names, data.username)
        return {"categories": categories[:8]}
    except Exception as e:
        print(f"Explore-append error: {e}")
        return {"categories": []}

@app.post("/api/youtube/search-domains")
async def search_domains(data: SearchDomainsPayload):
    query = data.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    try:
        categories = system.search_domains(query, data.username)
        return {"categories": categories, "query": query}
    except Exception as e:
        print(f"Search domains error: {e}")
        return {"categories": []}



@app.get("/api/youtube/discover")
async def fetch_youtube_discover(username: str = None):
    try:
        categories = system.discover(username)
        return {"categories": categories}
    except Exception as e:
        print(f"Discover error: {e}")
        return {"categories": []}


@app.post("/api/ai/predict")
async def ai_predict(data: PredictPayload):
    user = db.root['users'].get(data.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    interests = getattr(user, 'interests', [])
    reply = system.ai.predict(data.prompt, interests)
    return {"response": reply}


@app.post("/api/ai/video_suggest")
async def ai_video_suggest(data: VideoSuggestPayload):
    questions = system.ai.suggest_questions(data.video_title, data.video_desc)
    if not questions:
        return {"questions": [f"Key points of {data.video_title}", f"Explain {data.video_title}", "Similar videos"]}
    return {"questions": questions}

@app.post("/api/ai/video_chat")
async def ai_video_chat(data: VideoChatPayload):
    reply = system.ai.video_chat(data.video_title, data.video_desc, data.duration, data.question)
    return {"reply": reply}



@app.get("/api/youtube/search")
def youtube_search(q: str, username: str = None):
    vids = system.yt.scrape_query(q, limit=20, tag="Search Result")
    return {"categories": [{"name": "Search Results", "items": vids}]}

@app.get("/api/youtube/related")
def get_youtube_related(video_title: str, video_id: str):
    vids = system.yt.get_related_videos(video_title, video_id)
    return {"videos": vids}
