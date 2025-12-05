# stt_handler.py
import os
import logging
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Ensure env vars are loaded
load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def transcribe_file(filepath: str, language: str = "en", punctuate: bool = True) -> Dict[str, Any]:
    """
    Transcribe audio using OpenAI Whisper (replacing Deepgram).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY is missing.")
        raise RuntimeError("OPENAI_API_KEY is not set in .env file")

    client = OpenAI(api_key=api_key)

    try:
        # OpenAI language codes are 2-letter (e.g., "en" not "en-US")
        # We strip the region code just in case "en-US" is passed
        iso_language = language[:2] if language else "en"

        with open(filepath, "rb") as audio_file:
            # Call OpenAI Whisper
            transcript_obj = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=iso_language
            )

        # Extract text
        transcript_text = transcript_obj.text.strip()

        # Log for debugging
        logger.info(f"Whisper Transcribed: {transcript_text[:50]}...")

        # Return format matching what main.py expects
        # Note: Whisper API standard response doesn't give per-word confidence, so we default to 1.0
        return {
            "transcript": transcript_text,
            "confidence": 1.0, 
            "raw": transcript_obj
        }

    except Exception as e:
        logger.exception(f"OpenAI STT Error: {e}")
        raise RuntimeError(f"OpenAI Transcription failed: {e}")