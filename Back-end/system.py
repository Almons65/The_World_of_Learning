import os
from dotenv import load_dotenv
from database import db
from services import GeminiAI, YouTubeAPI
from models import Video
import concurrent.futures

load_dotenv(override=True)
load_dotenv("youtube_api.env", override=True)

class System:
    def __init__(self):
        self.db = db
        self.ai = GeminiAI(api_key=os.getenv("GEMINI_API_KEY"))
        self.yt = YouTubeAPI(api_key=os.getenv("YOUTUBE_API_KEY"))
        self.seen_topics = []

    def get_user(self, username):
        return self.db.root.get('users', {}).get(username)

    def discover(self, username=None):
        interests = "general educational and fascinating topics"
        history = []
        
        if username:
            user = self.get_user(username)
            if user:
                # If we already have a saved discovery feed, return it (plus any expansions)
                saved_disc = getattr(user, 'discovery_feed', [])
                if saved_disc:
                    return saved_disc + getattr(user, 'expanded_feed', [])
                
                # Otherwise, continue to generate fresh AI content
                interests = ", ".join(user.interests) if user.interests else interests
                history = [h.get('title', '') for h in user.history[-10:]]

        # Use AI to generate unique topics
        topics = self.ai.generate_discover_topics(interests, history, exclude_list=self.seen_topics[-24:])
        
        if not topics:
            return self.db.root.get('global_categories', [])

        # Update seen tracking
        for t in topics:
            if t.get('domain_name'):
                self.seen_topics.append(t['domain_name'])

        # Scrape data in parallel
        scraped = self._scrape_topics(topics, "disc")
        
        # Persist the initial discovery feed if user exists
        if username:
            user = self.get_user(username)
            if user:
                user.discovery_feed = scraped
                self.db.commit()

        return scraped

    def explore(self, username=None, page=0):
        # Tracking history for context
        history_list = [] # You could pull this from global history if needed
        
        topics = self.ai.generate_explore_topics(history_list, exclude_list=self.seen_topics[-24:])
        
        if not topics: return []

        for t in topics:
            if t.get('domain_name'):
                self.seen_topics.append(t['domain_name'])

        return self._scrape_topics(topics, "exp")

    def explore_append(self, current_domains, username=None):
        user_interests = "general educational and fascinating topics"
        if username:
            user = self.get_user(username)
            if user:
                user_interests = ", ".join(user.interests) if user.interests else user_interests

        # Use AI to branch out from current domains
        # Passing empty history for now as it's a quick branch
        topics = self.ai.generate_append_topics(user_interests, current_domains, history_list=[])
        
        if not topics: return []

        for t in topics:
            if t.get('domain_name'):
                self.seen_topics.append(t['domain_name'])

        results = self._scrape_topics(topics, "xp")

        # Persist to ZODB if user exists
        if username:
            user = self.get_user(username)
            if user:
                if not hasattr(user, 'expanded_feed'):
                    user.expanded_feed = []
                user.expanded_feed.extend(results)
                self.db.commit()
                
        return results

    def search_domains(self, query, username=None):
        topics = self.ai.generate_search_domains(query, history_list=[])
        
        if not topics: return []

        for t in topics:
            if t.get('domain_name'):
                self.seen_topics.append(t['domain_name'])

        results = self._scrape_topics(topics, "search")

        # Persist to ZODB if user exists
        if username:
            user = self.get_user(username)
            if user:
                if not hasattr(user, 'expanded_feed'):
                    user.expanded_feed = []
                user.expanded_feed.extend(results)
                self.db.commit()

        return results

    def download(self, video_id, username=None, save_path=None):
        video_obj = self.db.root.get('videos', {}).get(video_id)
        result = self.yt.download_video(video_id, save_path)
        
        if result["status"] == "success":
            if video_obj:
                video_obj.local_path = result["local_path"]
                video_obj.is_downloaded = True
                self.db.commit()
            return result
        return result

    def _scrape_topics(self, topics, slug_prefix):
        def scrape_bundle(item):
            domain = item["domain_name"]
            subs = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                queries = [s["search_query"] for s in item["sub_folders"]]
                results = list(ex.map(self.yt.scrape_query, queries))
                for sub_info, vids in zip(item["sub_folders"], results):
                    if vids:
                        subs.append({
                            "name": sub_info["name"], "title": sub_info["name"], "type": "folder",
                            "slug": f"sub-{sub_info['name'][:10].lower().replace(' ', '')}",
                            "img": vids[0]["thumb"], "items": vids
                        })
            return {
                "name": domain, "title": domain, "type": "folder", 
                "slug": f"{slug_prefix}-{domain[:10].lower().replace(' ', '')}",
                "img": subs[0]["img"] if subs else "", "items": subs
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            cats = list(ex.map(scrape_bundle, topics))
        
        return [c for c in cats if c.get("items")]

# Create a single instance of the System
system = System()
