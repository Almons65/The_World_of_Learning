import os
import json
import re
import requests
import concurrent.futures
import urllib.parse
import urllib.request
import datetime
import google.generativeai as genai
from dotenv import load_dotenv

class YouTubeAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        
    def parse_duration(self, duration: str) -> str:
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

    def fetch_video_data(self, video_id: str):
        if not self.api_key or self.api_key == "REPLACE_WITH_YOUR_ACTUAL_API_KEY":
            return None
        
        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails&id={video_id}&key={self.api_key}"
        response = requests.get(url)
        
        if response.status_code != 200:
            return None
            
        yt_data = response.json()
        if not yt_data.get("items"):
            return None
            
        item = yt_data["items"][0]
        snippet = item["snippet"]
        content_details = item["contentDetails"]
        
        thumbnails = snippet.get("thumbnails", {})
        best_thumb = thumbnails.get("maxres", thumbnails.get("high", thumbnails.get("default", {}))).get("url", "")
        formatted_duration = self.parse_duration(content_details.get("duration", ""))
        
        return {
            "slug": video_id,
            "title": snippet.get("title", "Unknown Title"),
            "desc": formatted_duration,
            "tag": "Imported Video", 
            "thumb": best_thumb,
            "parent_slug": "/home" 
        }

    def scrape_query(self, query: str, limit: int = 4, tag="Deeper Insight"):
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
                            vids.append({
                                "slug": vid, 
                                "title": title[:70] + "..." if len(title) > 70 else title,
                                "desc": duration + " min" if ":" in duration and "min" not in duration else duration,
                                "tag": tag, 
                                "thumb": thumb, 
                                "parent_slug": "/home",
                                "views": views, 
                                "date": date, 
                                "creator": creator, 
                                "type": "video"
                            })
                            if len(vids) >= limit: return vids
            return vids
        except Exception as e:
            print(f"Scrape Error ({query}): {e}")
            return []

    def get_stream_url(self, video_id: str, resolution: str = "1080p"):
        import yt_dlp
        res_map = {
            "1080p": "[height<=1080]", "720p": "[height<=720]", "480p": "[height<=480]", "360p": "[height<=360]", "best": ""
        }
        res_filter = res_map.get(resolution, "[height<=1080]")
        ydl_opts = {
            'quiet': True, 'no_warnings': True, 'skip_download': True,
            'format': f'best[ext=mp4]{res_filter}/best[ext=mp4]/best', 'socket_timeout': 15,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                video_url = info.get('url')
                if not video_url:
                    formats = info.get('formats', [])
                    best = None
                    target_h = 1080
                    if resolution == '720p': target_h = 720
                    elif resolution == '480p': target_h = 480
                    elif resolution == '360p': target_h = 360
                    for f in reversed(formats):
                        h = f.get('height') or 0
                        if f.get('ext') == 'mp4' and f.get('acodec') != 'none' and f.get('vcodec') != 'none' and h <= target_h:
                            best = f
                            break
                    if not best:
                        for f in reversed(formats):
                            if f.get('acodec') != 'none' and f.get('vcodec') != 'none':
                                best = f
                                break
                    video_url = best.get('url') if best else None
                if not video_url: return None
                return {
                    "stream_url": video_url, "title": info.get('title', ''),
                    "duration": info.get('duration', 0), "thumbnail": info.get('thumbnail', ''),
                }
        except Exception as e:
            print(f"Stream URL error: {e}")
            return None

    def get_related_videos(self, video_title: str, video_id: str):
        return self.scrape_query(video_title, limit=10, tag="Related Video")

    def download_video(self, video_id: str, save_path: str = None):
        import yt_dlp
        
        # Use the provided save_path or default to the video ID if none is given
        outtmpl = save_path if save_path else f'%(id)s.%(ext)s'
            
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': outtmpl,
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
                filename = ydl.prepare_filename(info)
                return {
                    "status": "success",
                    "local_path": filename,
                    "title": info.get('title'),
                    "ext": info.get('ext')
                }
        except Exception as e:
            print(f"Download error: {e}")
            return {"status": "error", "message": str(e)}


class GeminiAI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ]
        self.model = None
        self.api_key_leaked = False
        self.history = []
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self._init_model()

    def _init_model(self):
        try:
            valid_models = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            preferred = ["gemma-3-27b-it", "gemma-3-12b-it", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-1.5-pro"]
            chosen = next((m for m in preferred if m in valid_models), None)
            if not chosen and valid_models: chosen = valid_models[0]
            final_target = chosen if chosen else "gemini-1.5-flash"
            self.model = genai.GenerativeModel(model_name=final_target, safety_settings=self.safety_settings)
            print(f"--- AI System Connected [Model: {final_target}] ---")
        except Exception as e:
            error_msg = str(e).lower()
            if "leaked" in error_msg or "permission" in error_msg or "403" in error_msg:
                self.api_key_leaked = True
            self.model = genai.GenerativeModel(model_name='gemini-1.5-pro', safety_settings=self.safety_settings)

    def generate_content(self, prompt):
        if not self.model: return None
        try:
            return self.model.generate_content(prompt)
        except Exception as e:
            error_msg = str(e).lower()
            if "leaked" in error_msg or "permission" in error_msg or "403" in error_msg:
                self.api_key_leaked = True
            raise e

    def generate_explore_topics(self, history, exclude_list=None):
        exclude_str = f" DO NOT include any of these topics: {', '.join(exclude_list)}." if exclude_list else ""
        prompt = f"""Generate 8 highly specific educational Categories for an 'Explore' feed based on history: {history}.{exclude_str}
Inside each Category, generate exactly 4 distinct Sub-Folders with a search_query targeting YouTube.
Return ONLY a valid JSON array of exactly 8 objects.
Format: [{{"domain_name": "Title", "sub_folders": [{{"name": "SubName", "search_query": "query"}}]}}]"""
        response = self.generate_content(prompt)
        if not response: return []
        clean = response.text.strip()
        start, end = clean.find('['), clean.rfind(']') + 1
        return json.loads(clean[start:end])

    def generate_append_topics(self, user_interests, current_domains, history_list):
        interest_str = ', '.join(user_interests) if user_interests else 'general education'
        shown_str = ', '.join(current_domains) if current_domains else 'None'
        history_str = ', '.join(history_list[-12:]) if history_list else 'None'
        prompt = f"""User interests: {interest_str}. Shown: {shown_str}. History: {history_str}.
Generate exactly 8 NEW Topic Categories. No duplicates.
Return ONLY JSON array. Format: [{{"domain_name": "Title", "sub_folders": [{{"name": "SubName", "search_query": "query"}}]}}]"""
        response = self.generate_content(prompt)
        if not response: return []
        clean = response.text.strip()
        start, end = clean.find('['), clean.rfind(']') + 1
        return json.loads(clean[start:end])

    def generate_search_domains(self, query, history_list):
        history_str = ', '.join(history_list[-12:]) if history_list else 'None'
        prompt = f"""User searched for: "{query}". History: {history_str}.
Generate themed learning categories specifically about this. 8 if broad, 3-4 if specific.
Return ONLY JSON array. Format: [{{"domain_name": "Title", "sub_folders": [{{"name": "SubName", "search_query": "query"}}]}}]"""
        response = self.generate_content(prompt)
        if not response: return []
        clean = response.text.strip()
        start, end = clean.find('['), clean.rfind(']') + 1
        return json.loads(clean[start:end])

    def generate_discover_topics(self, interests, history, exclude_list=None):
        exclude_str = f" DO NOT include any of these topics: {', '.join(exclude_list)}." if exclude_list else ""
        prompt = f"""Generate exactly 8 highly specific, diverse educational Categories based on: Interests: {interests}, History: {history}.{exclude_str}
Each Category must be unique and have a distinct 'domain_name' and 'search_query' targeting YouTube.
Return ONLY a valid JSON array of exactly 8 objects.
Format: [{{ "domain_name": "Title", "sub_folders": [{{ "name": "SubName", "search_query": "query" }}] }}]"""
        response = self.generate_content(prompt)
        if not response: return []
        clean = response.text.strip()
        start, end = clean.find('['), clean.rfind(']') + 1
        return json.loads(clean[start:end])


    def predict(self, prompt, interests):
        context = f"Interests: {', '.join(interests)}."
        full_prompt = f"You are 'Monolith'. Respond conversationally to: {prompt}. Context: {context}"
        response = self.generate_content(full_prompt)
        return response.text.replace('```', '').strip() if response else "Archive busy."

    def suggest_questions(self, title, desc):
        prompt = f"""Generate exactly 3 short, fascinating questions for video: "{title}" ("{desc}").
Output exactly 3 questions separated by newlines. No bullet points or JSON."""
        response = self.generate_content(prompt)
        if not response: return []
        lines = [line.strip().lstrip('-*0123456789. ').strip() for line in response.text.split('\n') if line.strip()]
        return lines[:3]

    def video_chat(self, title, desc, duration, question):
        prompt = f"""Answer question about video. Title: {title}. Desc: {desc}. Duration: {duration}. 
Question: {question}. Include exactly one (MM:SS) timestamp. Max 3 sentences."""
        response = self.generate_content(prompt)
        return response.text.replace('```', '').strip() if response else "Archive logs highlight correlation at (1:15)."
