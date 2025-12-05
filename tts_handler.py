import requests
import json
from config import MURF_API_KEY

# 1. Correct Endpoint (The one in your error log is correct: /v1/speech/generate)
MURF_URL = "https://api.murf.ai/v1/speech/generate"

# 2. UPDATED VOICE MAP 
# specific to the "AVAILABLE VOICES" list you provided.
# HR Manager -> Natalie (Female, Professional US English)
# Tech Lead -> Cooper (Male, Deep/Professional US English)
VOICE_MAP = {
    "HR Manager": "en-US-natalie",   
    "Tech Lead": "en-US-cooper",    
    "Default": "en-US-natalie"
}

def synthesize(text: str, speaker_role: str = "Default") -> bytes:
    """
    Generate speech using Murf TTS.
    Returns: Raw MP3 bytes
    """
    # Safety check for key
    if not MURF_API_KEY:
        print("❌ Error: MURF_API_KEY is missing in config.")
        return b""

    # Fallback if role doesn't exist
    voice_id = VOICE_MAP.get(speaker_role, VOICE_MAP["Default"])

    payload = {
        "voiceId": voice_id,
        "text": text,
        "format": "mp3",
        "channel": "MONO", 
        "style": "Conversational"  # Some voices support 'Promo', 'Narrative' etc.
    }

    headers = {
        "accept": "application/json",
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        # 3. Request generation (Returns JSON with a URL, not the file directly)
        response = requests.post(MURF_URL, json=payload, headers=headers)

        if response.status_code != 200:
            # Print exact error from Murf for debugging
            print(f"❌ Murf API Error ({response.status_code}): {response.text}")
            return b""

        # 4. Parse JSON to get the 'audioFile' link
        data = response.json()
        audio_url = data.get("audioFile")

        if not audio_url:
            print("❌ Murf response missing 'audioFile' URL:", data)
            return b""

        print(f"✅ Murf generated: {audio_url}")

        # 5. Download the actual audio bytes
        audio_response = requests.get(audio_url)
        
        if audio_response.status_code == 200:
            return audio_response.content
        else:
            print("❌ Failed to download audio content from Murf URL")
            return b""

    except Exception as e:
        print(f"❌ Murf TTS Exception: {e}")
        return b""