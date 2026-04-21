from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from models import User, LearningVideo, Playlist, Folder
from database import db
import os
import json
import requests
import re
import google.generativeai as genai
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


YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not YOUTUBE_API_KEY or not GEMINI_API_KEY:
    print("\n--- WARNING ---")
    print("API Keys are missing from your environment. Please ensure they are defined in your .env file.")
    print("AI features will not function without valid keys.")
    print("----------------\n")


if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]

model = None
api_key_leaked = False
def _init_gemini_model():
    global model, api_key_leaked
    if not GEMINI_API_KEY:
        model = genai.GenerativeModel(model_name='gemini-pro', safety_settings=safety_settings)
        return
    try:
        valid_models = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        preferred = ["gemma-3-27b-it", "gemma-3-12b-it", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-1.5-pro"]
        chosen = next((m for m in preferred if m in valid_models), None)
        if not chosen and valid_models:
            chosen = valid_models[0]
            
        final_target = chosen if chosen else "gemma-3-27b-it"
        model = genai.GenerativeModel(model_name=final_target, safety_settings=safety_settings)
        print(f"\n--- AI System Connected [Model: {final_target}] ---\n")
    except Exception as e:
        error_msg = str(e).lower()
        if "leaked" in error_msg or "permission" in error_msg or "403" in error_msg:
            api_key_leaked = True
            print(f"\n--- CRITICAL: API KEY LEAKED OR BLOCKED ---\n")
        else:
            print(f"\n--- AI Init Error: {e} ---\n")
        model = genai.GenerativeModel(model_name='gemini-1.5-pro', safety_settings=safety_settings)

_init_gemini_model()

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

class ChatPayload(BaseModel):
    message: str

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

@app.post("/api/playlists/create")
async def create_playlist(data: PlaylistCreatePayload):
    user = db.root['users'].get(data.username)
    if user:
        success = user.createPlaylist(data.playlist_name, data.is_public)
        if success:
            db.commit()
            return {"message": f"Playlist '{data.playlist_name}' created"}
        raise HTTPException(status_code=400, detail="Playlist already exists")
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/api/playlists/add")
async def add_to_playlist(data: PlaylistVideoPayload):
    user = db.root['users'].get(data.username)
    if user and data.playlist_name in user.playlists:
        playlist = user.playlists[data.playlist_name]
        playlist.addVideo(data.video_data)
        db.commit()
        return {"message": "Video added to playlist"}
    raise HTTPException(status_code=404, detail="User or Playlist not found")

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
        serialized_playlists = [
            {"name": name, "is_public": getattr(p, 'isPublic', False), "videos": getattr(p, 'videos', [])} 
            for name, p in getattr(user, 'playlists', {}).items()
        ]
    except Exception as e:
        print(f"Profile playlist serialization error: {e}")
        serialized_playlists = []
    
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
        "playlists": serialized_playlists,
        "folders": serialized_folders
    }



@app.post("/api/youtube/fetch")
def fetch_youtube_data(data: YouTubeRequest):
    if YOUTUBE_API_KEY == "REPLACE_WITH_YOUR_ACTUAL_API_KEY":
        raise HTTPException(status_code=500, detail="YouTube API key not configured on backend.")
    
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&id={data.video_id}&key={YOUTUBE_API_KEY}"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch data from YouTube")
        
    yt_data = response.json()
    if not yt_data.get("items"):
        raise HTTPException(status_code=404, detail="Video not found")
        
    item = yt_data["items"][0]
    snippet = item["snippet"]
    content_details = item["contentDetails"]
    

    thumbnails = snippet.get("thumbnails", {})
    best_thumb = thumbnails.get("maxres", thumbnails.get("high", thumbnails.get("default", {}))).get("url", "")
    
    formatted_duration = parse_yt_duration(content_details.get("duration", ""))
    
    return {
        "slug": data.video_id,
        "title": snippet.get("title", "Unknown Title"),
        "desc": formatted_duration,
        "tag": "Imported Video", 
        "thumb": best_thumb,
        "parent_slug": "/home" 
    }

class StreamRequest(BaseModel):
    video_id: str
    resolution: str = "1080p"

@app.post("/api/youtube/stream-url")
async def get_stream_url(data: StreamRequest):
    """Use yt-dlp to extract a direct stream URL for native video playback."""
    import yt_dlp

    res_map = {
        "1080p": "[height<=1080]",
        "720p": "[height<=720]",
        "480p": "[height<=480]",
        "360p": "[height<=360]",
        "best": ""
    }
    res_filter = res_map.get(data.resolution, "[height<=1080]")

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'format': f'best[ext=mp4]{res_filter}/best[ext=mp4]/best',
        'socket_timeout': 15,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={data.video_id}",
                download=False
            )
            video_url = info.get('url')
            if not video_url:
                # Try formats list
                formats = info.get('formats', [])
                # Pick best mp4 with both video+audio
                best = None
                target_h = 2160
                if data.resolution == '1080p': target_h = 1080
                elif data.resolution == '720p': target_h = 720
                elif data.resolution == '480p': target_h = 480
                elif data.resolution == '360p': target_h = 360
                for f in reversed(formats):
                    h = f.get('height') or 0
                    if f.get('ext') == 'mp4' and f.get('acodec') != 'none' and f.get('vcodec') != 'none' and h <= target_h:
                        best = f
                        break
                if not best:
                    # Fallback: any format with video+audio
                    for f in reversed(formats):
                        if f.get('acodec') != 'none' and f.get('vcodec') != 'none':
                            best = f
                            break
                if not best and formats:
                    best = formats[-1]
                video_url = best.get('url') if best else None

            if not video_url:
                raise HTTPException(status_code=404, detail="Could not extract stream URL")

            return {
                "stream_url": video_url,
                "title": info.get('title', ''),
                "duration": info.get('duration', 0),
                "thumbnail": info.get('thumbnail', ''),
            }
    except yt_dlp.utils.DownloadError as e:
        print(f"yt-dlp error: {e}")
        raise HTTPException(status_code=400, detail=f"Could not extract video: {str(e)[:200]}")
    except Exception as e:
        print(f"Stream URL error: {e}")
        raise HTTPException(status_code=500, detail=str(e)[:200])


@app.get("/api/youtube/explore")
async def fetch_youtube_explore(username: str = None, page: int = 0):
    import concurrent.futures, re, urllib.parse, urllib.request

    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_real_gemini_key_here":
        return await fetch_youtube_discover(username)

    global GLOBAL_AI_HISTORY
    import concurrent.futures
    import json
    import re
    import urllib.parse
    import urllib.request

    try:
        history_str = ", ".join(GLOBAL_AI_HISTORY[-8:]) if GLOBAL_AI_HISTORY else "None"
        query_prompt = f"""Based on the user's recently explored topic domains: {history_str}
        
Generate exactly 8 clear, descriptive Topic Categories that branch off from these recent topics.

Inside each Category, generate exactly 4 distinct Sub-Folders with clear, informative names.
For each Sub-Folder, provide a highly specific search_query targeting YouTube.

CRITICAL RULES:
1. The category titles MUST be clear, human-readable, and highly descriptive of the actual video contents. DO NOT use pretentious or abstract words.
2. The sub-folder names MUST clearly describe their specific search queries so the user knows exactly what videos to expect.
3. The search_query MUST be highly specific to yield great YouTube educational results related exactly to the sub-folder name.
4. Return ONLY a valid JSON array of exactly 8 objects.
Format: [
  {{
    "domain_name": "Clear Descriptive Title",
    "sub_folders": [
      {{"name": "Informative Sub-Folder Name", "search_query": "Specific precise youtube search query"}}
    ]
  }}
]
No markdown."""
        
        response = model.generate_content(query_prompt)
        clean_topics = response.text.strip()
        start = clean_topics.find('[')
        end = clean_topics.rfind(']') + 1
        if start != -1 and end != -1:
            generated_items = json.loads(clean_topics[start:end])
        else:
            raise Exception("No JSON array found")
            
        yt_queries = []
        for d in generated_items:
            for sub in d.get("sub_folders", []):
                yt_queries.append(sub.get("search_query", ""))
        GLOBAL_AI_HISTORY.extend(yt_queries)
        if len(GLOBAL_AI_HISTORY) > 100: GLOBAL_AI_HISTORY = GLOBAL_AI_HISTORY[50:]
        
    except Exception as e:
        print(f"Explore Gemini Query Error: {e}")
        return await fetch_youtube_discover(username)

    def scrape_youtube_query(query):
        try:
            q = urllib.parse.quote(query)
            url = f'https://www.youtube.com/results?search_query={q}'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.9'})
            html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
            match = re.search(r'var ytInitialData = ({.*?});</script>', html)
            if not match: return []
            data = json.loads(match.group(1))
            contents = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
            vids = []
            for sec in contents:
                if 'itemSectionRenderer' in sec:
                    for item in sec['itemSectionRenderer']['contents']:
                        if 'videoRenderer' in item:
                            vr = item['videoRenderer']
                            vid = vr.get('videoId')
                            if not vid: continue
                            title = vr.get('title', {}).get('runs', [{}])[0].get('text', '')
                            thumb = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
                            duration = vr.get('lengthText', {}).get('simpleText', '14:00')
                            creator = vr.get('ownerText', {}).get('runs', [{}])[0].get('text', 'Global Archive')
                            raw_views = vr.get('viewCountText', {}).get('simpleText', '')
                            try:
                                digits = re.sub(r'\D', '', raw_views)
                                if digits:
                                    v_count = int(digits)
                                    views = f"{v_count/1000000:.1f}M views" if v_count >= 1000000 else (f"{v_count/1000:.1f}K views" if v_count >= 1000 else f"{v_count} views")
                                else: views = raw_views
                            except: views = raw_views
                            raw_date = vr.get('publishedTimeText', {}).get('simpleText', '')
                            date = raw_date
                            try:
                                import datetime
                                dm = re.search(r'(\d+)\s+(year|month|week|day|hour)s?\s+ago', raw_date)
                                if dm:
                                    n2, u2 = int(dm.group(1)), dm.group(2).lower()
                                    now2 = datetime.datetime.now()
                                    if u2 in ['y', 'year']: now2 -= datetime.timedelta(days=n2*365)
                                    elif u2 in ['mo', 'month']: now2 -= datetime.timedelta(days=n2*30)
                                    elif u2 in ['w', 'week']: now2 -= datetime.timedelta(days=n2*7)
                                    elif u2 in ['d', 'day']: now2 -= datetime.timedelta(days=n2)
                                    date = now2.strftime("%b %d, %Y")
                            except: pass
                            vids.append({"slug": vid, "title": title[:70] + "..." if len(title) > 70 else title,
                                         "desc": duration + " min" if ":" in duration and "min" not in duration else duration,
                                         "tag": "Deeper Insight", "thumb": thumb, "parent_slug": "/home",
                                         "views": views, "date": date, "creator": creator, "type": "video"})
                            if len(vids) >= 4: return vids
            return vids
        except Exception as e:
            print(f"Explore Scrape Error ({query}): {e}")
            return []

    def scrape_bundle(item):
        domain = item["domain_name"]
        domain_slug = f"explore-{page}-{domain[:15].lower().replace(' ', '')}"
        subs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            queries = [sub["search_query"] for sub in item["sub_folders"]]
            results = list(executor.map(scrape_youtube_query, queries))
            for sub_info, vids in zip(item["sub_folders"], results):
                if vids:
                    subs.append({
                        "name": sub_info["name"][:35], "title": sub_info["name"][:35], "type": "folder",
                        "slug": f"sub-{sub_info['name'][:10].lower().replace(' ', '')}",
                        "img": vids[0]["thumb"], "items": vids
                    })
        return {"name": domain, "title": domain, "type": "folder", "slug": domain_slug, "img": subs[0]["img"] if subs else "", "items": subs}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        cats = list(executor.map(scrape_bundle, generated_items))
        
    cats = [c for c in cats if c.get("items")]
    vol_label = f"Vol. {page + 1}"

    return {"categories": cats, "theme": f"Advanced Exploration {vol_label}"}


@app.post("/api/youtube/explore-append")
async def explore_append(data: ExploreAppendPayload):
    """Append more domains based on user interests + currently displayed domains."""
    import concurrent.futures, re, urllib.parse, urllib.request, json as json_mod

    global GLOBAL_AI_HISTORY

    user_interests = []
    if data.username:
        user = db.root['users'].get(data.username)
        if user:
            user_interests = getattr(user, 'interests', [])

    context_domains = data.current_domain_names
    interest_str = ', '.join(user_interests) if user_interests else 'general education'
    shown_str = ', '.join(context_domains) if context_domains else 'None'
    history_str = ', '.join(GLOBAL_AI_HISTORY[-12:]) if GLOBAL_AI_HISTORY else 'None'

    prompt = f"""Generate exactly 8 clear, straightforward, and highly descriptive Topic Categories for a learning platform.

User interests: {interest_str}
Domains currently displayed on screen (DO NOT repeat these or anything similar): {shown_str}
Previously generated topics (avoid duplicating): {history_str}

Inside each Category, generate exactly 4 distinct Sub-Folders. For each Sub-Folder, provide a specific YouTube search_query.

RULES:
1. Categories MUST meaningfully expand or branch from the user's interests. The Category and Sub-Folder names MUST be clear, simple, and accurately describe the subject matter. Avoid overly abstract or pretentious words.
2. NEVER duplicate anything in the shown or history lists.
3. Return ONLY a valid JSON array of exactly 8 objects.
Format: [{{"domain_name": "Clear Descriptive Title", "sub_folders": [{{"name": "Informative Name", "search_query": "query"}}]}}]
No markdown."""

    try:
        response = model.generate_content(prompt)
        clean = response.text.strip()
        start, end = clean.find('['), clean.rfind(']') + 1
        generated_items = json.loads(clean[start:end])
    except Exception as e:
        print(f"explore-append Gemini error: {e}")
        return await fetch_youtube_explore(data.username, data.page)

    def scrape_yt(query):
        try:
            q = urllib.parse.quote(query)
            url = f'https://www.youtube.com/results?search_query={q}'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.9'})
            html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
            match = re.search(r'var ytInitialData = ({.*?});</script>', html)
            if not match: return []
            data_json = json.loads(match.group(1))
            contents = data_json['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
            vids = []
            for sec in contents:
                if 'itemSectionRenderer' in sec:
                    for item in sec['itemSectionRenderer']['contents']:
                        if 'videoRenderer' in item:
                            vr = item['videoRenderer']
                            vid = vr.get('videoId')
                            if not vid: continue
                            title = vr.get('title', {}).get('runs', [{}])[0].get('text', '')
                            thumb = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
                            duration = vr.get('lengthText', {}).get('simpleText', '14:00')
                            creator = vr.get('ownerText', {}).get('runs', [{}])[0].get('text', 'Unknown')
                            raw_views = vr.get('viewCountText', {}).get('simpleText', '')
                            try:
                                digits = re.sub(r'\D', '', raw_views)
                                if digits:
                                    v = int(digits)
                                    if v >= 1000000: views = f"{v/1000000:.1f}M views"
                                    elif v >= 1000: views = f"{v/1000:.1f}K views"
                                    else: views = f"{v} views"
                                else: views = raw_views or "N/A"
                            except: views = raw_views or "N/A"
                            raw_date = vr.get('publishedTimeText', {}).get('simpleText', '')
                            date = raw_date
                            try:
                                import datetime
                                d_match = re.search(r'(\d+)\s+(year|month|week|day|hour)s?\s+ago', raw_date)
                                if d_match:
                                    n, unit = int(d_match.group(1)), d_match.group(2)
                                    now = datetime.datetime.now()
                                    if unit == 'year': now -= datetime.timedelta(days=n * 365)
                                    elif unit == 'month': now -= datetime.timedelta(days=n * 30)
                                    elif unit == 'week': now -= datetime.timedelta(days=n * 7)
                                    elif unit == 'day': now -= datetime.timedelta(days=n)
                                    date = now.strftime("%b %d, %Y")
                            except: pass
                            vids.append({"slug": vid, "title": title[:70], "desc": duration, "tag": "Deeper Insight",
                                         "thumb": thumb, "parent_slug": "/home", "creator": creator,
                                         "views": views, "date": date, "type": "video"})
                            if len(vids) >= 15: return vids
            return vids
        except Exception as e:
            print(f"explore-append scrape error ({query}): {e}")
            return []

    def scrape_bundle(item):
        domain = item["domain_name"]
        domain_slug = f"xp-{domain[:15].lower().replace(' ', '-')}"
        subs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            queries = [s["search_query"] for s in item["sub_folders"]]
            results = list(ex.map(scrape_yt, queries))
            for sub_info, vids in zip(item["sub_folders"], results):
                if vids:
                    subs.append({"name": sub_info["name"][:35], "title": sub_info["name"][:35], "type": "folder",
                                 "slug": f"sub-{sub_info['name'][:10].lower().replace(' ', '-')}",
                                 "img": vids[0]["thumb"], "items": vids})
        return {"name": domain, "title": domain, "type": "folder", "slug": domain_slug,
                "img": subs[0]["img"] if subs else "", "items": subs}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        cats = list(ex.map(scrape_bundle, generated_items))
    cats = [c for c in cats if c.get("items")]

    qs = [s["search_query"] for d in generated_items for s in d.get("sub_folders", [])]
    GLOBAL_AI_HISTORY.extend(qs)
    if len(GLOBAL_AI_HISTORY) > 100: GLOBAL_AI_HISTORY = GLOBAL_AI_HISTORY[50:]

    return {"categories": cats[:8]}


@app.post("/api/youtube/search-domains")
async def search_domains(data: SearchDomainsPayload):
    """Generate AI-curated domains specifically themed around the user's search query."""
    import concurrent.futures, re, urllib.parse, urllib.request

    global GLOBAL_AI_HISTORY

    query = data.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    history_str = ', '.join(GLOBAL_AI_HISTORY[-12:]) if GLOBAL_AI_HISTORY else 'None'

    prompt = f"""A user searched for: \"{query}\"

Generate themed learning domain categories specifically about this topic. The number of categories should reflect the breadth of the query:
- If the query is very broad (e.g. 'science'), generate 8 categories exploring different facets.
- If the query is specific (e.g. 'Quantum Entanglement'), generate 3-4 deeply focused categories.

Inside each Category, generate 4 Sub-Folders with a specific YouTube search_query.

RULES:
1. Every domain MUST be directly thematically connected to the search query: \"{query}\".
2. Names MUST be clear, simple, and highly descriptive of the actual video contents. DO NOT use pretentious or abstract words.
3. Avoid duplicating: {history_str}
4. Return ONLY a valid JSON array. No markdown.
Format: [{{"domain_name": "Clear Descriptive Title", "sub_folders": [{{"name": "Informative Name", "search_query": "precise youtube query"}}]}}]"""

    try:
        response = model.generate_content(prompt)
        clean = response.text.strip()
        start, end = clean.find('['), clean.rfind(']') + 1
        generated_items = json.loads(clean[start:end])
        if not isinstance(generated_items, list) or len(generated_items) == 0:
            raise Exception("Invalid JSON")
    except Exception as e:
        print(f"search-domains Gemini error: {e}")
        # Fallback: create basic domains from the query
        generated_items = [
            {"domain_name": f"{query.title()} — Core Concepts",
             "sub_folders": [{"name": "Overview", "search_query": f"{query} explained"},
                             {"name": "Deep Dive", "search_query": f"{query} in depth documentary"},
                             {"name": "History", "search_query": f"history of {query}"},
                             {"name": "Future", "search_query": f"future of {query}"}]},
            {"domain_name": f"{query.title()} — Applications",
             "sub_folders": [{"name": "Real World Uses", "search_query": f"{query} real world applications"},
                             {"name": "Case Studies", "search_query": f"{query} case study documentary"},
                             {"name": "Research", "search_query": f"{query} academic research explained"},
                             {"name": "Debates", "search_query": f"{query} debate controversy"}]},
        ]

    def scrape_yt(search_query):
        try:
            q = urllib.parse.quote(search_query)
            url = f'https://www.youtube.com/results?search_query={q}'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.9'})
            html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
            match = re.search(r'var ytInitialData = ({.*?});</script>', html)
            if not match: return []
            data_json = json.loads(match.group(1))
            contents = data_json['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
            vids = []
            for sec in contents:
                if 'itemSectionRenderer' in sec:
                    for item in sec['itemSectionRenderer']['contents']:
                        if 'videoRenderer' in item:
                            vr = item['videoRenderer']
                            vid = vr.get('videoId')
                            if not vid: continue
                            title = vr.get('title', {}).get('runs', [{}])[0].get('text', '')
                            thumb = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
                            duration = vr.get('lengthText', {}).get('simpleText', '14:00')
                            creator = vr.get('ownerText', {}).get('runs', [{}])[0].get('text', 'Unknown')
                            raw_views = vr.get('viewCountText', {}).get('simpleText', '')
                            try:
                                digits = re.sub(r'\D', '', raw_views)
                                if digits:
                                    v = int(digits)
                                    if v >= 1000000: views = f"{v/1000000:.1f}M views"
                                    elif v >= 1000: views = f"{v/1000:.1f}K views"
                                    else: views = f"{v} views"
                                else: views = raw_views or "N/A"
                            except: views = raw_views or "N/A"
                            raw_date = vr.get('publishedTimeText', {}).get('simpleText', '')
                            date = raw_date
                            try:
                                import datetime
                                d_match = re.search(r'(\d+)\s+(year|month|week|day|hour)s?\s+ago', raw_date)
                                if d_match:
                                    n, unit = int(d_match.group(1)), d_match.group(2)
                                    now = datetime.datetime.now()
                                    if unit == 'year': now -= datetime.timedelta(days=n * 365)
                                    elif unit == 'month': now -= datetime.timedelta(days=n * 30)
                                    elif unit == 'week': now -= datetime.timedelta(days=n * 7)
                                    elif unit == 'day': now -= datetime.timedelta(days=n)
                                    date = now.strftime("%b %d, %Y")
                            except: pass
                            vids.append({"slug": vid, "title": title[:70], "desc": duration, "tag": "Search Result",
                                         "thumb": thumb, "parent_slug": "/home", "creator": creator,
                                         "views": views, "date": date, "type": "video"})
                            if len(vids) >= 15: return vids
            return vids
        except Exception as e:
            print(f"search-domains scrape error ({search_query}): {e}")
            return []

    def build_domain(item):
        domain_name = item["domain_name"]
        subs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            queries = [s["search_query"] for s in item["sub_folders"]]
            results = list(ex.map(scrape_yt, queries))
            for sub_info, vids in zip(item["sub_folders"], results):
                if vids:
                    subs.append({"name": sub_info["name"][:35], "title": sub_info["name"][:35], "type": "folder",
                                 "slug": f"sr-{sub_info['name'][:10].lower().replace(' ', '-')}",
                                 "img": vids[0]["thumb"], "items": vids})
        slug = "".join([c if c.isalnum() else "-" for c in domain_name.lower()])
        return {"name": domain_name, "title": domain_name, "type": "folder", "slug": slug,
                "img": subs[0]["img"] if subs else "", "items": subs}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        cats = list(ex.map(build_domain, generated_items))
    cats = [c for c in cats if c.get("items")]

    qs = [s["search_query"] for d in generated_items for s in d.get("sub_folders", [])]
    GLOBAL_AI_HISTORY.extend(qs)
    if len(GLOBAL_AI_HISTORY) > 100: GLOBAL_AI_HISTORY = GLOBAL_AI_HISTORY[50:]

    return {"categories": cats, "query": query}


@app.get("/api/youtube/discover")
def fetch_youtube_discover(username: str = None):
    def get_db_fallback():
        cats = db.root.get('global_categories', [])
        return {"categories": [c.to_dict() for c in cats]}


    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_real_gemini_key_here":
        return get_db_fallback()
    
    global GLOBAL_AI_HISTORY
    
    import concurrent.futures
    import re
    import random
    

    INTEREST_QUERY_MAP = {
        "History":          ["ancient Rome history documentary", "World War II untold stories"],
        "Computer Science": ["how computers work explained", "history of the internet documentary"],
        "Astrophysics":     ["black hole physics explained", "dark matter universe documentary"],
        "Neuroscience":     ["human brain structure explained", "memory and learning neuroscience"],
        "Philosophy":       ["Stoicism philosophy explained", "existentialism Sartre documentary"],
        "Architecture":     ["ancient Roman architecture", "modernist architecture history"],
        "Marine Biology":   ["deep sea creatures documentary", "coral reef ecosystem explained"],
        "Geopolitics":      ["Southeast Asia geopolitics explained", "Middle East conflict history"],
        "Mathematics":      ["chaos theory explained", "history of mathematics documentary"],
        "Film & Cinema":    ["Kubrick filmmaking technique analysis", "history of cinema documentary"],
        "Economics":        ["1929 Great Depression explained", "behavioral economics documentary"],
        "Archaeology":      ["ancient Egyptian archaeology discoveries", "Pompeii excavation documentary"],
        "Photography":      ["history of photography documentary", "famous photographers techniques"],
        "Neuroscience":     ["brain plasticity science explained", "consciousness neuroscience documentary"],
    }
    DEFAULT_QUERIES = [
        "Buddhism History documentary", "Cold War Space Race details",
        "Ancient Rome Architecture", "Deep Sea Exploration",
        "Japanese Shogunate history", "Quantum Physics mechanics",
        "philosophy of mind documentary", "Geopolitics of Southeast Asia"
    ]

    def get_interest_queries(interests_list):
        queries = []
        for interest in interests_list:
            queries.extend(INTEREST_QUERY_MAP.get(interest, [f"{interest} documentary", f"{interest} explained"]))
        return queries if queries else DEFAULT_QUERIES

    user_interests_list = []
    user_interests = ""
    if username:
        user = db.root['users'].get(username)
        if user and getattr(user, 'interests', []):
            user_interests_list = user.interests
            user_interests = f"CRITICAL REQUIREMENT: The user has selected the following interests: {', '.join(user.interests)}. You MUST generate queries revolving around these specific domains. You MUST generate EXACTLY 8 categories total, regardless of how many interests the user selected. Do NOT limit your output to the number of interests."


    try:
        import random, time
        history_list = list(GLOBAL_AI_HISTORY)
        random.shuffle(history_list)
        history_str = ", ".join(history_list[-12:]) if history_list else "None"
        seed_phrase = f"[Session seed: {int(time.time() * 1000) % 99991}]"
        query_prompt = f"""Generate exactly 8 clear, specific, and highly descriptive Topic Categories based on the user's interests. {seed_phrase}
{user_interests}

Inside each Category, generate exactly 4 distinct Sub-Folders with clear, informative names.
For each Sub-Folder, provide a highly specific search_query targeting YouTube.

CRITICAL RULES:
1. The category titles MUST be clear, human-readable, and highly descriptive of the actual video contents. DO NOT use pretentious, abstract, or confusing terms (e.g., use 'Neural Implants' instead of 'Bio-Digital Interfaces'). Do NOT generate internet web domains.
2. The sub-folder names MUST clearly and simply describe their specific search queries so the user knows exactly what videos to expect. Never use repetitive naming conventions.
3. The search_query MUST be highly specific to yield great YouTube educational results.
4. Do NOT output anything remotely similar to these previously used queries: {history_str}.
5. Return ONLY a valid JSON array of exactly 8 objects.
Format: [
  {{
    "domain_name": "Clear Descriptive Category Name",
    "sub_folders": [
      {{"name": "Specific Informative Sub-Folder Name", "search_query": "Specific precise youtube search query"}}
    ]
  }}
]
No markdown, no quotes outside the array."""
        
        response = model.generate_content(query_prompt)
        clean_topics = response.text.strip()
        start = clean_topics.find('[')
        end = clean_topics.rfind(']') + 1
        if start != -1 and end != -1:
            generated_items = json.loads(clean_topics[start:end])
            if not isinstance(generated_items, list) or len(generated_items) == 0:
                raise Exception("Invalid JSON format")
        else:
            raise Exception("No JSON array found")
            
        yt_queries = []
        for d in generated_items:
            for sub in d.get("sub_folders", []):
                yt_queries.append(sub.get("search_query", ""))
        GLOBAL_AI_HISTORY.extend(yt_queries)

        if len(GLOBAL_AI_HISTORY) > 100: GLOBAL_AI_HISTORY = GLOBAL_AI_HISTORY[50:]
    except Exception as e:
        print(f"Gemini Query Error: {e}")
        
        base_queries = get_interest_queries(user_interests_list)
        chosen_domains = base_queries[:8]
        while len(chosen_domains) < 8:
            chosen_domains.extend(DEFAULT_QUERIES)
        chosen_domains = chosen_domains[:8]
            
        generated_items = []
        for d in chosen_domains:
            domain_name = d.replace(" documentary", "").replace(" explained", "").title()
            
            sub_folders = [
                {"name": f"Origins & Basics of {domain_name}", "search_query": f"{domain_name} core concepts explained"},
                {"name": f"The {domain_name} Story", "search_query": f"{domain_name} full documentary"},
                {"name": f"Exploring {domain_name} In Depth", "search_query": f"deep dive into {domain_name}"},
                {"name": f"Advanced {domain_name} Studies", "search_query": f"advanced {domain_name} lecture or analysis"}
            ]
            
            generated_items.append({"domain_name": domain_name, "sub_folders": sub_folders})
        print(f"Using mapped unique fallback domains: {[item['domain_name'] for item in generated_items]}")


    import urllib.parse
    import urllib.request
    
    def scrape_youtube_query(query):
        try:
            q = urllib.parse.quote(query)
            url = f'https://www.youtube.com/results?search_query={q}'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.9'})
            html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
            
            match = re.search(r'var ytInitialData = ({.*?});</script>', html)
            if not match: return []
            data = json.loads(match.group(1))
            
            contents = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
            vids = []
            for sec in contents:
                if 'itemSectionRenderer' in sec:
                    for item in sec['itemSectionRenderer']['contents']:
                        if 'videoRenderer' in item:
                            vr = item['videoRenderer']
                            vid = vr.get('videoId')
                            if not vid: continue
                            title = vr.get('title', {}).get('runs', [{}])[0].get('text', '')
                            thumb = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
                            duration = vr.get('lengthText', {}).get('simpleText', '14:00')
                            creator = vr.get('ownerText', {}).get('runs', [{}])[0].get('text', 'Global Archive')
                            
                            raw_views = vr.get('viewCountText', {}).get('simpleText', '1.2M views')
                            try:
                                digits = re.sub(r'\D', '', raw_views)
                                if digits:
                                    v = int(digits)
                                    if v >= 1000000: views = f"{v/1000000:.1f}M views"
                                    elif v >= 1000: views = f"{v/1000:.1f}K views"
                                    else: views = f"{v} views"
                                else: views = raw_views
                            except: views = raw_views
                                
                            if " views" not in views and " view" in views: views = views.replace(" view", " views")
                            if " views" not in views: views += " views"
                                
                            raw_date = vr.get('publishedTimeText', {}).get('simpleText', 'Unknown')
                            date = raw_date
                            try:
                                import datetime
                                d_match = re.search(r'(\d+)\s+(year|month|week|day|hour)s?\s+ago', raw_date)
                                if d_match:
                                    n, unit = int(d_match.group(1)), d_match.group(2)
                                    now = datetime.datetime.now()
                                    if unit == 'year': now -= datetime.timedelta(days=n * 365)
                                    elif unit == 'month': now -= datetime.timedelta(days=n * 30)
                                    elif unit == 'week': now -= datetime.timedelta(days=n * 7)
                                    elif unit == 'day': now -= datetime.timedelta(days=n)
                                    date = now.strftime("%b %d, %Y")
                            except Exception as e: pass

                            vids.append({
                                "slug": vid,
                                "title": title[:70] + "..." if len(title) > 70 else title,
                                "desc": duration + " min" if ":" in duration and "min" not in duration else duration,
                                "tag": "Daily Discovery Feed",
                                "thumb": thumb,
                                "parent_slug": "/home",
                                "views": views,
                                "date": date,
                                "creator": creator
                            })
                            if len(vids) >= 15:
                                return vids
            return vids
        except Exception as e:
            print(f"Scrape error for {query}: {e}")
            return []

    def scrape_wrapper(task):
        domain_name = task["domain_name"]
        sub_name = task["sub_name"]
        query = task["query"]
        vids = scrape_youtube_query(query)
        return {"domain_name": domain_name, "sub_name": sub_name, "query": query, "items": vids}

    all_tasks = []
    for domain in generated_items:
        domain_name = domain.get("domain_name", "Unknown Domain")
        for sub in domain.get("sub_folders", []):
            all_tasks.append({
                "domain_name": domain_name,
                "sub_name": sub.get("name", "Unknown Folder"),
                "query": sub.get("search_query", "")
            })
            
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(scrape_wrapper, all_tasks))

    from collections import OrderedDict
    domain_map = OrderedDict()
    seen_slugs = set()
    for res in results:
        d_name = res["domain_name"]
        if d_name not in domain_map:
            domain_map[d_name] = []
        
        unique_vids = []
        for v in res.get("items", []):
            if v["slug"] not in seen_slugs:
                seen_slugs.add(v["slug"])
                unique_vids.append(v)
                
        if unique_vids:
            # Need a safe slug
            safe_slug = "".join([c if c.isalnum() else "-" for c in res['sub_name'].lower()])
            safe_slug = re.sub(r'-+', '-', safe_slug).strip('-')
            domain_map[d_name].append({
                "name": res["sub_name"],
                "title": res["sub_name"],
                "type": "folder",
                "slug": f"{safe_slug}-{len(domain_map[d_name])}",
                "img": unique_vids[0]["thumb"],
                "items": unique_vids
            })

    final_categories = []
    for d_name, sub_folders in domain_map.items():
        if sub_folders:
            safe_slug_domain = "".join([c if c.isalnum() else "-" for c in d_name.lower()])
            safe_slug_domain = re.sub(r'-+', '-', safe_slug_domain).strip('-')
            final_categories.append({
                "name": d_name,
                "title": d_name,
                "type": "folder",
                "slug": f"{safe_slug_domain}-{len(final_categories)}",
                "img": sub_folders[0]["img"],
                "items": sub_folders
            })

    if not final_categories:
        cats = db.root.get('global_categories', [])
        return {"categories": [c.to_dict() for c in cats]}

    return {"categories": final_categories[:8]}


@app.post("/api/ai/predict")
async def ai_predict(data: PredictPayload):
    user = db.root['users'].get(data.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        if not GEMINI_API_KEY or GEMINI_API_KEY == "your_real_gemini_key_here":
            return {"response": f"Offline Simulator response for: '{data.prompt}'. Add your Google Gemini Key to enable true AI generation."}

        user_context = f"Interests: {', '.join(user.interests)}."
        prompt = f"""You are 'Monolith', an extremely intelligent AI archivist organizing a vast multimedia repository. 
Respond Conversationally to the user's input below, acting helpful and brilliant.
User Input: {data.prompt}
Background Context: {user_context}
Output your response as standard text, no json formatting."""
        
        response = model.generate_content(prompt)
        text_reply = response.text.replace('```', '').strip()
        
        return {"response": text_reply}

    except Exception as e:
        print(f"Gemini Conversational Chat Error: {e}")
        return {"response": "The Global Archives are currently busy organizing standard intelligence. Please hold."}


@app.post("/api/ai/chat")
async def ai_chat(data: ChatPayload):
    try:
        if not GEMINI_API_KEY or GEMINI_API_KEY == "your_real_gemini_key_here":
            return {"reply": f"Hi! I am currently running in offline simulation mode. Please configure your API key to access full AI capabilities. You asked: '{data.message}'"}

        chat_prompt = f"""You are the 'Monolith', a wise AI assistant for 'The World of Learning'. Your tone is premium, cinematic, and helpful. You guide users through their learning archive.
User inquiry: {data.message}"""
        
        response = model.generate_content(chat_prompt)
        reply = response.text.replace('```', '').strip()
            
        return {"reply": reply}
    except Exception as e:
        print(f"Chat Neural Error: {e}")
        return {"reply": "Connection with the Monolith's core was interrupted. Please try again."}

@app.post("/api/ai/video_suggest")
async def ai_video_suggest(data: VideoSuggestPayload):
    try:
        if api_key_leaked:
            return {"questions": ["⚠ ERROR: Your Gemini API Key is blocked/leaked.", "Please replace it in your .env file.", "Get a new key at Google AI Studio"]}

        if not GEMINI_API_KEY or GEMINI_API_KEY == "your_real_gemini_key_here":
            return {"questions": [
                f"What are the main takeaways from {data.video_title}?",
                f"Explain the context behind {data.video_title}",
                "Provide related topics"
            ]}

        prompt = f"""Analyze the provided Video Title and infer its specific educational or topical context. 
Generate exactly 3 short, fascinating, and highly specific questions a curious viewer might ask an expert while watching this exact video.
Video Title: "{data.video_title}"
Video Description: "{data.video_desc}"

CRITICAL INSTRUCTIONS:
1. Keep each question SHORT and conversational (under 12 words max). They should sound like something a casual viewer would naturally ask.
2. Use simple, accessible language. Avoid complex academic terminology or overly detailed multi-part questions.
3. The questions should still be highly relevant to the specific topic of the video, but framed simply (e.g. 'What happened to the missing fleet?' instead of a complex historical analysis).
4. Output exactly 3 questions separated by newlines. No bullet points, no numbering, no markdown, no JSON."""
        
        response = model.generate_content(prompt)
        clean_text = response.text.replace('```', '').strip()
        lines = [line.strip().lstrip('-').lstrip('*').lstrip('1234567890.').strip() for line in clean_text.split('\n') if line.strip()]
        
        if len(lines) >= 1:
            return {"questions": lines[:3]}
        return {"questions": [f"What are the key points of {data.video_title}?", f"Explain {data.video_title}", "Recommend similar videos"]}
    except Exception as e:
        error_msg = str(e).lower()
        if "leaked" in error_msg or "permission" in error_msg or "403" in error_msg:
            return {"questions": ["⚠ ERROR: Your Gemini API Key is blocked/leaked.", "Please replace it in your .env file.", "Get a new key at Google AI Studio"]}
            
        print(f"Video Suggest Error ({type(e).__name__}): {e}")
        return {"questions": [f"What are the key points of {data.video_title}?", f"Explain {data.video_title}", "Recommend similar videos"]}

@app.post("/api/ai/video_chat")
async def ai_video_chat(data: VideoChatPayload):
    try:
        if api_key_leaked:
            return {"reply": "⚠ **API Key Error**: Google has blocked your `GEMINI_API_KEY` because it was leaked or is invalid. Please generate a new key and update your `Back-end/.env` file to restore AI capabilities."}

        if not GEMINI_API_KEY or GEMINI_API_KEY == "your_real_gemini_key_here":
            return {"reply": f"Offline mode. You asked about '{data.video_title}': {data.question} (0:30)"}

        prompt = f"""You are a helpful AI assistant answering a user's question about a YouTube video.
Video Title: {data.video_title}
Video Description: {data.video_desc}
Video Duration: {data.duration}

User Question: {data.question}

Answer the question factually based on the title and description, and invent a plausible, single timestamp (e.g., "1:24") that falls within the video duration that supports your answer. Make sure to include the exact timestamp string anywhere in your text wrapped in parentheses like exactly this format: (MM:SS). Keep the answer under 3 sentences."""
        
        response = model.generate_content(prompt)
        reply = response.text.replace('```', '').strip()
        return {"reply": reply}

    except Exception as e:
        error_msg = str(e).lower()
        if "leaked" in error_msg or "permission" in error_msg or "403" in error_msg:
            return {"reply": "⚠ **API Key Error**: Google has blocked your `GEMINI_API_KEY` because it was leaked or is invalid. Please generate a new key and update your `Back-end/.env` file to restore AI capabilities."}
            
        print(f"Video Chat Error: {e}")
        question = data.question.lower()
        if "key points" in question or "explain" in question or "summarize" in question:
            return {"reply": f"**(Offline Summary Protocol)**\n\nBased on the meta-archive, **{data.video_title}** fundamentally delves into the topics mentioned in your inquiry.\n\n**Core Premise:** {data.video_desc}\n\nFor the primary analysis, scrub the timeline forward to (2:15)."}
        elif "recommend" in question or "similar" in question:
            return {"reply": f"**(Offline Recommendation Engine)**\n\nIf you enjoyed **{data.video_title}**, we highly suggest exploring the 'Deep Dive' or 'Advanced Topics' sub-folders within the same overarching Domain on your home feed. The central premise laid out at (0:45) is expanded upon extensively in those sections."}
        else:
            return {"reply": f"**(Offline Archive Record)**\n\nRegarding your inquiry: *'{data.question}'*\n\nThe archival logs highlight a strong correlation with the material presented around (1:15) into **{data.video_title}**. Feel free to skip to that timestamp to verify the theoretical points while the primary AI neural link is in cooldown!"}



@app.get("/api/youtube/search")
def youtube_search(q: str, username: str = None):
    import concurrent.futures, re, urllib.parse, urllib.request

    TOPIC_EXPANSIONS = {
        "philosophy":    ["Stoicism philosophy", "Existentialism philosophy", "Ethics and morality", "Epistemology and knowledge"],
        "history":       ["Ancient civilizations history", "Medieval history documentary", "World War history", "Modern history revolutions"],
        "science":       ["Physics science explained", "Chemistry science documentary", "Biology evolution", "Earth science geology"],
        "mathematics":   ["Algebra and equations", "Calculus and analysis", "Number theory mathematics", "Geometry and topology"],
        "politics":      ["Democracy and governance history", "Geopolitics world order", "Political philosophy documentary", "Cold War history"],
        "art":           ["Renaissance art history", "Modern art movements", "Photography art documentary", "Architecture art history"],
        "economics":     ["Microeconomics explained", "Macroeconomics monetary policy", "History of capitalism trade", "Behavioral economics"],
        "religion":      ["Buddhism history explained", "Christianity history documentary", "Islam history culture", "Hinduism Vedic philosophy"],
        "psychology":    ["Cognitive psychology explained", "Social psychology documentary", "Sigmund Freud psychoanalysis", "Behavioral psychology"],
        "technology":    ["Computer science history", "Artificial intelligence explained", "Internet history documentary", "Biotechnology future"],
        "literature":    ["Shakespeare plays explained", "Victorian literature documentary", "World literature movements", "Poetry and spoken word"],
        "music":         ["Classical music composers history", "Jazz music origins", "Music theory explained", "World music cultures"],
        "cinema":        ["Film noir history documentary", "French New Wave cinema", "Kubrick and auteur filmmaking", "History of Hollywood"],
        "astronomy":     ["Black holes explained", "Solar system formation", "Galaxy and universe documentary", "Dark matter dark energy"],
        "biology":       ["Evolution Darwin explained", "Genetics and DNA science", "Marine biology documentary", "Microbiology and viruses"],
        "culture":       ["Ancient Greek culture mythology", "Chinese culture dynasties", "African history culture", "Norse mythology explained"],
        "war":           ["World War I causes", "World War II Pacific Europe", "Vietnam War history", "Cold War proxy conflicts"],
        "ancient":       ["Ancient Egypt pharaohs documentary", "Ancient Greece philosophers", "Ancient Rome republic empire", "Ancient Mesopotamia Sumer"],
        "architecture":  ["Gothic medieval architecture", "Modernist Bauhaus architecture", "Ancient Roman Greek architecture", "Sustainable green architecture"],
        "language":      ["Etymology word origins history", "Linguistics documentary", "Dead languages Latin Sanskrit", "Writing systems history"],
        "geography":     ["Mountain ranges formation geology", "Ocean currents climate", "Deserts of the world documentary", "River civilizations history"],
        "sports":        ["Ancient Olympic games history", "Football soccer history", "Martial arts history documentary", "Psychology of sport performance"],
        "food":          ["History of food and cuisine", "Fermentation science food", "Spice trade history documentary", "Agriculture revolution food"],
        "medicine":      ["History of medicine surgery", "Infectious disease epidemics", "Neurology brain medicine", "Ancient medicine healing"],
        "law":           ["History of law courts", "Constitutional law explained", "International law human rights", "Criminal justice systems"],
    }


    MEDIUM_TOPICS = {
        "stoicism", "existentialism", "quantum", "evolution", "democracy", "capitalism",
        "colonialism", "renaissance", "baroque", "romanticism", "impressionism", "surrealism",
        "feudalism", "imperialism", "enlightenment", "reformation", "darwinism", "marxism",
        "fascism", "nationalism", "socialism", "anarchism", "liberalism", "conservatism",
        "buddhism", "christianity", "islam", "hinduism", "judaism", "taoism", "confucianism",
        "jazz", "classical music", "hip hop", "baroque music", "opera",
        "mythology", "folklore", "symbolism", "romanticism",
        "relativity", "thermodynamics", "electromagnetism", "mechanics", "optics",
    }

    def _make_title(s):
        return s.title().replace(" And ", " and ").replace(" Of ", " of ").replace(" The ", " the ").replace(" In ", " in ")

    def _make_slug(s, suffix=""):
        return f"{s[:35].lower().replace(' ', '-')}{suffix}"


    q_lower = q.lower().strip()

    top_domains = None
    for key, sub_topics in TOPIC_EXPANSIONS.items():
        if key == q_lower or key in q_lower or q_lower in key:
            top_domains = sub_topics   
            break

    if top_domains is None:
        for term in MEDIUM_TOPICS:
            if term == q_lower or term in q_lower or q_lower in term:
                top_domains = [q, f"{q} history documentary"] 
                break

    if top_domains is None:
        top_domains = [q]   

   
    SUB_VARIATIONS = ["", " documentary", " explained", " history lecture"]
    all_tasks = []   
    for domain_label in top_domains:
        for var in SUB_VARIATIONS:
            all_tasks.append((domain_label, f"{domain_label}{var}".strip()))

    def scrape_task(task):
        domain_label, query = task
        try:
            encoded = urllib.parse.quote(query)
            url = f'https://www.youtube.com/results?search_query={encoded}'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.9'})
            html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
            match = re.search(r'var ytInitialData = ({.*?});</script>', html)
            if not match: return (domain_label, query, [])
            data = json.loads(match.group(1))
            contents = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
            vids = []
            for sec in contents:
                if 'itemSectionRenderer' in sec:
                    for item in sec['itemSectionRenderer']['contents']:
                        if 'videoRenderer' in item:
                            vr = item['videoRenderer']
                            vid = vr.get('videoId')
                            if not vid: continue
                            title = vr.get('title', {}).get('runs', [{}])[0].get('text', '')
                            thumb = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
                            duration = vr.get('lengthText', {}).get('simpleText', '14:00')
                            creator = vr.get('ownerText', {}).get('runs', [{}])[0].get('text', 'Global Archive')
                            raw_views = vr.get('viewCountText', {}).get('simpleText', '')
                            try:
                                digs = re.sub(r'\D', '', raw_views)
                                if digs:
                                    vc = int(digs)
                                    views = f"{vc/1000000:.1f}M views" if vc >= 1000000 else (f"{vc/1000:.1f}K views" if vc >= 1000 else f"{vc} views")
                                else: views = raw_views
                            except: views = raw_views
                            raw_date = vr.get('publishedTimeText', {}).get('simpleText', '')
                            date = raw_date
                            try:
                                import datetime
                                dm = re.search(r'(\d+)\s+(year|month|week|day|hour)s?\s+ago', raw_date)
                                if dm:
                                    n2, u2 = int(dm.group(1)), dm.group(2).lower()
                                    now2 = datetime.datetime.now()
                                    if u2 in ['y', 'year']: now2 -= datetime.timedelta(days=n2*365)
                                    elif u2 in ['mo', 'month']: now2 -= datetime.timedelta(days=n2*30)
                                    elif u2 in ['w', 'week']: now2 -= datetime.timedelta(days=n2*7)
                                    elif u2 in ['d', 'day']: now2 -= datetime.timedelta(days=n2)
                                    date = now2.strftime("%b %d, %Y")
                            except: pass
                            vids.append({"slug": vid,
                                         "title": title[:70] + "..." if len(title) > 70 else title,
                                         "desc": duration + " min" if ":" in duration and "min" not in duration else duration,
                                         "tag": "Search Result", "thumb": thumb, "parent_slug": "/home",
                                         "views": views, "date": date, "creator": creator, "type": "video"})
                            if len(vids) >= 4: return (domain_label, query, vids)
            return (domain_label, query, vids)
        except Exception as e:
            print(f"Search scrape error [{query}]: {e}")
            return (domain_label, query, [])

    max_workers = min(16, len(all_tasks))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        raw_results = list(executor.map(scrape_task, all_tasks))

    from collections import OrderedDict
    domain_buckets = OrderedDict()
    for label in top_domains:
        domain_buckets[label] = []

    seen_slugs = set()
    for domain_label, query, vids in raw_results:
        unique_vids = [v for v in vids if v['slug'] not in seen_slugs]
        for v in unique_vids:
            seen_slugs.add(v['slug'])
        if not unique_vids or domain_label not in domain_buckets:
            continue
        sub_name = unique_vids[0]['title'][:50].rstrip() + ("..." if len(unique_vids[0]['title']) > 50 else "")
        sub_slug = _make_slug(query, "-search")
        domain_buckets[domain_label].append({
            "name": sub_name, "title": sub_name, "type": "folder",
            "slug": sub_slug, "img": unique_vids[0]["thumb"], "items": unique_vids
        })

    categories = []
    for domain_label, sub_folders in domain_buckets.items():
        if not sub_folders:
            continue
        top_name = _make_title(domain_label)
        top_slug = _make_slug(domain_label, "-result")
        categories.append({
            "name": top_name, "title": top_name, "type": "folder",
            "slug": top_slug, "img": sub_folders[0]["img"], "items": sub_folders
        })

    return {"categories": categories}


@app.get("/api/youtube/related")
def get_youtube_related(video_title: str, video_id: str):
    import urllib.parse, urllib.request, re, json, datetime
    try:
        q = urllib.parse.quote(video_title)
        url = f'https://www.youtube.com/results?search_query={q}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        match = re.search(r'var ytInitialData = ({.*?});</script>', html)
        if not match: return {"videos": []}
        data = json.loads(match.group(1))
        contents = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
        vids = []
        for sec in contents:
            if 'itemSectionRenderer' in sec:
                for item in sec['itemSectionRenderer']['contents']:
                    if 'videoRenderer' in item:
                        vr = item['videoRenderer']
                        vid = vr.get('videoId')
                        if not vid or vid == video_id: continue
                        title = vr.get('title', {}).get('runs', [{}])[0].get('text', '')
                        thumb = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
                        duration = vr.get('lengthText', {}).get('simpleText', '14:00')
                        creator = vr.get('ownerText', {}).get('runs', [{}])[0].get('text', 'Unknown')
                        
                        raw_views = vr.get('viewCountText', {}).get('simpleText', '')
                        try:
                            digs = re.sub(r'\D', '', raw_views)
                            if digs:
                                vc = int(digs)
                                views = f"{vc/1000000:.1f}M views" if vc >= 1000000 else (f"{vc/1000:.1f}K views" if vc >= 1000 else f"{vc} views")
                            else: views = raw_views
                        except: views = raw_views
                        
                        raw_date = vr.get('publishedTimeText', {}).get('simpleText', '')
                        date = raw_date
                        try:
                            dm = re.search(r'(\d+)\s*(y|year|mo|month|w|week|d|day|h|hour)s?\s+ago', raw_date, re.IGNORECASE)
                            if dm:
                                n2, u2 = int(dm.group(1)), dm.group(2).lower()
                                now2 = datetime.datetime.now()
                                if u2 in ['y', 'year']: now2 -= datetime.timedelta(days=n2*365)
                                elif u2 in ['mo', 'month']: now2 -= datetime.timedelta(days=n2*30)
                                elif u2 in ['w', 'week']: now2 -= datetime.timedelta(days=n2*7)
                                elif u2 in ['d', 'day']: now2 -= datetime.timedelta(days=n2)
                                date = now2.strftime("%b %d, %Y")
                        except: pass
                        
                        vids.append({"slug": vid,
                                     "title": title[:70] + "..." if len(title) > 70 else title,
                                     "desc": duration + " min" if ":" in duration and "min" not in duration else duration,
                                     "tag": "Related Video", "thumb": thumb, "parent_slug": "/home",
                                     "views": views, "date": date, "creator": creator, "type": "video"})
                        if len(vids) >= 10: return {"videos": vids}
        return {"videos": vids}
    except Exception as e:
        print(f"Related error: {e}")
        return {"videos": []}
