import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(override=True)
load_dotenv("youtube_api.env", override=True) 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    genai.configure(api_key=GEMINI_API_KEY)
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Supported model: {m.name}")
except Exception as e:
    import traceback
    print("Error listing models:")
    traceback.print_exc()
