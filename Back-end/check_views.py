import urllib.request
import re
url = 'https://www.youtube.com/watch?v=XESDBlwkb1U'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')
match1 = re.search(r'interactionCount', html)
print('interactionCount found:', bool(match1))
match2 = re.search(r'"viewCount":"(\d+)"', html)
if match2:
    print('viewCount json:', match2.group(1))
match3 = re.search(r'(\d+(?:,\d+)*) views', html)
if match3:
    print('comma views:', match3.group(1))
