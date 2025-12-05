# audio_utils.py
import subprocess
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def record_wav(out_path: str, duration: float = 5.0, fs: int = 44100, channels: int = 1) -> str:
    """
    Record using external FFmpeg process.
    Prevents Python segmentation faults by offloading recording to the OS.
    """
    logger.info("Recording for %.2f seconds using FFmpeg...", duration)
    
    # Ensure output directory exists
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    
    # macOS FFmpeg command: -f avfoundation -i "none:0" (Video=none, Audio=Device 0)
    # Device 0 is usually the default system microphone.
    cmd = [
        "ffmpeg",
        "-y",               # Overwrite output
        "-f", "avfoundation",
        "-i", "none:0",     # Use default audio input
        "-t", str(duration),
        "-ac", str(channels),
        "-ar", str(fs),
        "-v", "error",      # Suppress logs
        out_path
    ]

    try:
        subprocess.run(cmd, check=True)
        logger.info("Saved recording to %s", out_path)
        return str(out_path)
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg recording failed. Ensure you have granted Terminal microphone access.")
        logger.error("Try running: ffmpeg -f avfoundation -list_devices true -i \"\"")
        raise RuntimeError("Recording failed") from e

def play_bytes(audio_bytes: bytes):
    """
    Safe audio playback using macOS native 'afplay'.
    Zero risk of Python segfaults.
    """
    try:
        # Save to a temp file first
        temp_path = "temp_playback.wav"
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)
            
        # Use macOS built-in audio player
        subprocess.run(["afplay", temp_path], check=True)
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    except Exception as e:
        logger.exception("Playback failed: %s", e)
        raise