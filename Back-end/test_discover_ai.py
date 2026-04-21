import os
import google.generativeai as genai
from dotenv import load_dotenv
import json

load_dotenv("youtube_api.env", override=True)
load_dotenv(override=True)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel(model_name='gemini-2.5-flash')
user_interests = "CRITICAL REQUIREMENT: The user has selected the following interests: Technology, Nature."
query_prompt = f"""Generate exactly 4 highly unique, creative, and distinct educational Domain names based on the user's interests.
{user_interests}

Inside each Domain, generate exactly 4 distinct Sub-Folders with creative names.
For each Sub-Folder, provide a highly specific search_query targeting YouTube.

CRITICAL RULES:
1. The domain names MUST be highly unique and creative. They MUST NOT be the exact broad names of the user's selected interests.
2. The sub-folder names MUST be distinct and creative.
3. The search_query MUST be highly specific to yield great YouTube educational results.
4. Do NOT output anything similar to previously used queries: None.
5. Return ONLY a valid JSON array of exactly 4 objects.
Format: [
  {{
    "domain_name": "Creative Domain Name",
    "sub_folders": [
      {{"name": "Creative Sub-Folder Name", "search_query": "Specific precise youtube search query"}}
    ]
  }}
]
No markdown, no quotes outside the array."""

try:
    response = model.generate_content(query_prompt)
    print("RAW REPONSE:", response.text)
    clean_topics = response.text.strip()
    start = clean_topics.find('[')
    end = clean_topics.rfind(']') + 1
    if start != -1 and end != -1:
        generated_items = json.loads(clean_topics[start:end])
        print("JSON OUTPUT:", json.dumps(generated_items, indent=2))
    else:
        print("NO JSON ARRAY FOUND")
except Exception as e:
    print(f"Error: {e}")
