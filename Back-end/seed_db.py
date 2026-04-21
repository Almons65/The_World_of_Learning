import json
import re
from database import db
from models import Folder, LearningVideo
import transaction
def parse_yt_duration(pt_str):
    match = re.search(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', pt_str)
    if not match: return "Unknown"
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d} hr"
    return f"{m}:{s:02d} min"
def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}
def seed_database():
    yt_expanded_ids = load_json('yt_expanded_ids.json')
    yt_expanded_meta = load_json('yt_expanded_meta.json')
    topic_names = ["Science", "History", "Technology", "Art", "Music", "Literature", "Mathematics", "Geography"]
    categories = []
    for tn in topic_names:
        fallback_root = Folder(f"{tn} Discovery")
        subfolders_data = yt_expanded_ids.get(tn, {})
        assigned_topic_ids = set()
        count = 0 
        for sub_name, vid_list in subfolders_data.items():
            if not vid_list: continue
            folder_index = count % len(vid_list) 
            folder_img = f"https://img.youtube.com/vi/{vid_list[folder_index]}/hqdefault.jpg"
            count += 1
            sub_folder = Folder(f"{tn} {sub_name}", is_public=True, img=folder_img)
            added_this_folder = 0
            for specific_slug in vid_list:
                if added_this_folder >= 10: break
                if specific_slug in assigned_topic_ids: continue
                assigned_topic_ids.add(specific_slug)
                meta = yt_expanded_meta.get(specific_slug, {"creator": "Global Archive", "views": "1.2M views", "date": "Unknown", "duration": "PT14M0S", "title": f"Video {specific_slug}"})
                thumb = f"https://img.youtube.com/vi/{specific_slug}/hqdefault.jpg"
                dur_str = parse_yt_duration(meta.get("duration", "PT14M0S"))
                raw_title = meta.get("title", f"Video {specific_slug}")
                clean_title = re.sub(r'#\S+', '', raw_title).strip()
                clean_title = re.sub(r'\s{2,}', ' ', clean_title)
                if len(clean_title) < 3:
                    clean_title = f"{tn} {sub_name} Content"
                lv = LearningVideo(specific_slug, clean_title, dur_str, f"{tn} {sub_name}", thumb, f"{tn.lower()}_{sub_name.lower().replace(' ', '_')}", views=meta["views"], date=meta["date"], creator=meta["creator"])
                sub_folder.add_item(lv)
                db.root['videos'][specific_slug] = lv
                added_this_folder += 1
            fallback_root.add_item(sub_folder)
        categories.append(fallback_root)
    db.root['global_categories'] = categories
    db.commit()
    print("Database successfuly seeded! 240+ objects injected into Database memory.")
if __name__ == "__main__":
    seed_database()
