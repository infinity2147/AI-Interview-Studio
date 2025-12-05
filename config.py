# config.py
import os
from dotenv import load_dotenv
load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")
MURF_VOICE_ID = os.getenv("MURF_VOICE_ID", "en-US-natalie")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en-US")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
