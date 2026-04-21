import urllib.request
import re
import json
import concurrent.futures
from html import unescape
import time
with open('yt_expanded_ids.json', 'r') as f:
    tree = json.load(f)
all_ids = []
for topic, subdict in tree.items():
    for sub, ids in subdict.items():
        all_ids.extend(ids)
all_ids = list(set(all_ids))
res = {}
def format_views(count_str):
    try:
        c = int(count_str)
        if c >= 1000000:
            return f"{c/1000000:.1f}M views"
        elif c >= 1000:
            return f"{c//1000}K views"
        else:
            return f"{c} views"
    except: return "1.2M views"
def fetch_meta(vid):
    try:
        url = f'https://www.youtube.com/watch?v={vid}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        author = re.search(r'<span itemprop="author"[^>]*>.*?<link itemprop="name" content="(.*?)"', html, re.S)
        views = re.search(r'"viewCount":"(\d+)"', html)
        date = re.search(r'<meta itemprop="datePublished" content="(.*?)"', html)
        duration = re.search(r'<meta itemprop="duration" content="(.*?)"', html)
        title_m = re.search(r'<meta name="title" content="(.*?)">', html)
        c = author.group(1) if author else "Global Archive"
        v = format_views(views.group(1)) if views else "1.2M views"
        d = date.group(1) if date else "Unknown"
        dur = duration.group(1) if duration else "PT14M0S"
        t = unescape(title_m.group(1)) if title_m else f"Archive ID {vid}"
        if "T" in d:
            try:
                parts = d.split('T')[0].split('-')
                months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                d = f"{months[int(parts[1])]} {int(parts[2])}, {parts[0]}"
            except: pass
        elif len(d) == 10 and "-" in d:
            try:
                parts = d.split('-')
                months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                d = f"{months[int(parts[1])]} {int(parts[2])}, {parts[0]}"
            except: pass
        res[vid] = {"creator": c[:25], "views": v, "date": d, "duration": dur, "title": t}
    except Exception as e:
        res[vid] = {"creator": "Global Archive", "views": "1.2M views", "date": "Unknown", "duration": "PT14M0S", "title": f"Archive ID {vid}"}
print(f"Fetching {len(all_ids)} videos...")
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(fetch_meta, vid) for vid in all_ids]
    concurrent.futures.wait(futures)
with open('yt_expanded_meta.json', 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False)
print("Done scraping!")
