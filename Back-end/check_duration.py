import urllib.request
import re
html = urllib.request.urlopen("https://www.youtube.com/watch?v=XESDBlwkb1U").read().decode("utf-8")
match = re.search(r'<meta itemprop="duration" content="(.*?)"', html)
if match: 
    print("Duration:", match.group(1))
else:
    print("Not found")
