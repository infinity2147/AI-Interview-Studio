import requests
import os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("MURF_API_KEY")

headers_list = [
    {"api-key": key},
    {"token": key},
    {"Authorization": key},
]

url_list = [
    "https://api.murf.ai/v1/speech/generate",
    "https://api.murf.ai/api/v1/speech/generate",
    "https://api.murf.ai/v1/tts/speech",
    "https://murf.ai/v1/speech/generate",
]

payload = {
    "text": "Testing Murf API authentication",
    "voiceId": "natalie",
    "format": "wav"
}

print("\n=== START TEST ===\n")

for url in url_list:
    for headers in headers_list:
        print(f"URL: {url}")
        print(f"HEADERS SENT: {headers}")
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            print("STATUS:", resp.status_code)
            print("RESPONSE:", resp.text[:300])
        except Exception as e:
            print("ERROR:", e)
        print("\n---------------------------------\n")

print("\n=== END TEST ===\n")
