"""Voice service: STT (transcription) and TTS (speech synthesis) via OpenAI API.

Uses the TTS_OPENAI_API_KEY env var for authentication. Both transcription and
TTS use httpx to call OpenAI's REST API directly — no SDK dependency needed.
"""
from __future__ import annotations

import logging
import os
from typing import AsyncIterator

import httpx

logger = logging.getLogger(__name__)

_OPENAI_BASE = "https://api.openai.com/v1"
_STT_MODEL = "gpt-4o-mini-transcribe"
_TTS_MODEL = "tts-1"
_DEFAULT_VOICE = "onyx"

# Supported voices for reference:
# alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse
AVAILABLE_VOICES = [
    "alloy", "ash", "ballad", "coral", "echo",
    "fable", "nova", "onyx", "sage", "shimmer", "verse",
]


def _get_api_key() -> str:
    key = os.environ.get("TTS_OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("TTS_OPENAI_API_KEY is not set")
    return key


# Accepted audio MIME types for the transcribe endpoint.
ALLOWED_AUDIO_TYPES = {
    "audio/webm", "audio/mp4", "audio/mpeg", "audio/wav",
    "audio/x-wav", "audio/ogg", "audio/flac",
}

# Map MIME types to file extensions OpenAI accepts.
_EXT_MAP = {
    "audio/webm": "webm",
    "audio/mp4": "mp4",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
}


async def transcribe(audio_bytes: bytes, content_type: str = "audio/webm") -> dict:
    """Transcribe audio to text using OpenAI's transcription API.

    Args:
        audio_bytes: Raw audio data.
        content_type: MIME type of the audio (audio/webm, audio/mp4, audio/wav, etc.)

    Returns:
        dict with keys: text (str), duration_s (float|None)
    """
    api_key = _get_api_key()

    ext = _EXT_MAP.get(content_type, "webm")
    filename = f"audio.{ext}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_OPENAI_BASE}/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (filename, audio_bytes, content_type)},
            data={
                "model": _STT_MODEL,
                "response_format": "verbose_json",
            },
            timeout=30,
        )

    if resp.status_code != 200:
        logger.error(f"STT API error {resp.status_code}: {resp.text[:500]}")
        raise RuntimeError(f"Transcription failed: HTTP {resp.status_code}")

    result = resp.json()
    return {
        "text": result.get("text", "").strip(),
        "duration_s": result.get("duration"),
    }


async def tts_stream(text: str, voice: str = _DEFAULT_VOICE) -> AsyncIterator[bytes]:
    """Stream TTS audio chunks for lower time-to-first-byte.

    Yields MP3 audio chunks as they arrive from the OpenAI API.
    """
    api_key = _get_api_key()

    if voice not in AVAILABLE_VOICES:
        voice = _DEFAULT_VOICE

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{_OPENAI_BASE}/audio/speech",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": _TTS_MODEL,
                "input": text,
                "voice": voice,
                "response_format": "mp3",
            },
            timeout=30,
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                logger.error(f"TTS stream error {resp.status_code}: {body[:500]}")
                raise RuntimeError(f"TTS stream failed: HTTP {resp.status_code}")

            async for chunk in resp.aiter_bytes(chunk_size=4096):
                yield chunk
