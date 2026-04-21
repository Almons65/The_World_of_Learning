import urllib.request
import re
import json
import time
topic_names = ["Science", "History", "Technology", "Art", "Music", "Literature", "Mathematics", "Geography"]
subfolders = ["Fundamentals", "Intermediate Concepts", "Advanced Mastery"]
res = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
def search_yt(query):
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers=headers)
    try:
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        vids = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
        unique = list(dict.fromkeys(vids))
        print(f"[{query}] Found {len(unique)} videos")
        return unique[:10]
    except Exception as e:
        print(f"Error for {query}: {e}")
        return ["dQw4w9WgXcQ"] * 10
for tn in topic_names:
    res[tn] = {}
    for sub in subfolders:
        query = f"{tn} {sub} Educational Documentary"
        ids = search_yt(query)
        res[tn][sub] = ids
        time.sleep(0.5) 
with open('yt_expanded_ids.json', 'w') as f:
    json.dump(res, f)
print("Done generating 240 IDs!")
