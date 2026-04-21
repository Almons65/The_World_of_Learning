import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("youtube_api.env", override=True)
load_dotenv(".env", override=True)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
print("Supported models:", valid_models)
