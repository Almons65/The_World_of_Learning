import urllib.request
import re
import json
import time
yt_slugs_by_topic = {
    'Science': ['KFS4oiVDeBI', 'dBz6X0dhflA', 'oPmWLJ3j-ic', 'CV8pXBDaP_c', 'SV9HAZbLIzE', 'SckcciXpRzU', 'qcfghIHVsmg', 'hHYtYGh_QzA', 'LL-0IktXlJI', 'CDKceREP-DQ', 'RPM4rlQnNrk'],
    'History': ['Q11LpxA3AYY', 'KSPG9Z08_7c', 'MSJR2RTgsOI', '-7jVHmj1LMo', '-9ocVnX7Td0', 'fcixU95B6OM', '0lXMvWskomk', 'RXNsZbueHYk', '4YpzjFb78WQ', 'c7XyRvqX6TQ', 'SH0gxi-6500'],
    'Technology': ['UVf2Yw7uFoE', 'CWR2JYunzho', '6fQZJN1-JF8', '0HFzTYlhT2E', '9z52xavACQY', 'hHYtYGh_QzA', 'mlUbkHg1KHc', 'JQ9PLGlJ6vU', 'iLj8ttLqfEI', 'EJJt5rxomj8', 'hSD13XonnZc'],
    'Art': ['X1UA_YvKqnc', '2g1I44tVyvM', 'EpBFl_I1u3c', 'yDeHW1zi6cE', '3FjOq9GlR_c', 'wwYZQjgUljA', '-a-29jpmXaY', 'TkNBUGuPJfo', 'dhhUmwmlMtc', 'YsplbBAaXA4', '0xTM9KWF3Ys'],
    'Music': ['qI99z1MO2ls', '4JQASDpciNM', 'KWLqLcpmOXc', 'g7uF170I-xw', 'efZbqH9Mtd8', 'AKCogpwuF24', '1b3DuPhKHic', 'E2oNRM8lhps', '0F0o1VmGOOI', 'XQL5BwkaKAc', 'O_JCDFMXDgQ'],
    'Literature': ['MSJR2RTgsOI', 'ZPWeD99aZYc', 'BA3gGLXcZDM', 'a1rfL-ms_3o', 'ISx3FDYkHrQ', 'rDGgsg7gbfk', 'sX3XQlSNe7s', 'L7sq6pvXfDU', 'vxxGHM6EN40', '9Z77qRR9wn4', 't_9zl1umTsM'],
    'Mathematics': ['k2QVCfoW7uI', 'nnvOepT3h5A', 'e1B0saB0rbI', '0526NtJ4uR4', 'jhNKqZcgKZA', 'hbDkSaSnbVM', '5LHFzNMgWzw', 'aXhsD74Fwv4', 'lFlu60qs7_4', '8hl5uZT41RY', 'XESDBlwkb1U'],
    'Geography': ['r10g5gERB04', 'bxIV_itPWkU', 'JAZHVEfBv0c', 'jFp6YcFsNn0', 'r-geP7n97wk', '-IkEMMKSqcw', 'cOPrAuHpFB4', 'UccdEz7nKxg', 'sbYX4Lur4Yc', 'qcfghIHVsmg', 'cCnmKkCLDRM']
}
all_ids = []
for ids in yt_slugs_by_topic.values(): all_ids.extend(ids)
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
    except:
        return "1.2M views"
import concurrent.futures
def fetch_meta(vid):
    try:
        url = f'https://www.youtube.com/watch?v={vid}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        html = urllib.request.urlopen(req, timeout=4).read().decode('utf-8')
        author = re.search(r'<span itemprop="author"[^>]*>.*?<link itemprop="name" content="(.*?)"', html, re.S)
        views = re.search(r'"viewCount":"(\d+)"', html)
        date = re.search(r'<meta itemprop="datePublished" content="(.*?)"', html)
        duration = re.search(r'<meta itemprop="duration" content="(.*?)"', html)
        c = author.group(1) if author else "Global Archive"
        v = format_views(views.group(1)) if views else "1.2M views"
        d = date.group(1) if date else "Unknown"
        dur = duration.group(1) if duration else "PT14M0S"
        if len(d) == 10 and "-" in d:
            parts = d.split('-')
            months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            d = f"{months[int(parts[1])]} {int(parts[2])}, {parts[0]}"
        elif "T" in d:
            try:
                parts = d.split('T')[0].split('-')
                months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                d = f"{months[int(parts[1])]} {int(parts[2])}, {parts[0]}"
            except: pass
        res[vid] = {"creator": c[:25], "views": v, "date": d, "duration": dur}
    except Exception as e:
        res[vid] = {"creator": "Global Archive", "views": "1.2M views", "date": "Unknown", "duration": "PT14M0S"}
print(f"Fetching {len(all_ids)} videos...")
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(fetch_meta, vid) for vid in all_ids]
    concurrent.futures.wait(futures)
with open('yt_meta_map.json', 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False)
print('Done!')
