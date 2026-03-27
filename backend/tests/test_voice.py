"""Tests for the voice service (STT + TTS) and API endpoints."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json


class TestVoiceService:
    """Unit tests for services/voice.py"""

    @pytest.mark.asyncio
    async def test_transcribe_success(self):
        """transcribe() returns text and duration from OpenAI API."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "text": "What ships are near Hormuz",
            "duration": 3.2,
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch.dict("os.environ", {"TTS_OPENAI_API_KEY": "sk-test"}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                from services.voice import transcribe

                result = await transcribe(b"fake-audio", "audio/webm")

                assert result["text"] == "What ships are near Hormuz"
                assert result["duration_s"] == 3.2
                mock_client.post.assert_called_once()
                call_kwargs = mock_client.post.call_args
                assert "audio/transcriptions" in call_kwargs[0][0]

    @pytest.mark.asyncio
    async def test_transcribe_no_api_key(self):
        """transcribe() raises RuntimeError when API key is missing."""
        with patch.dict("os.environ", {}, clear=True):
            import importlib
            import services.voice as voice_mod
            importlib.reload(voice_mod)

            with pytest.raises(RuntimeError, match="TTS_OPENAI_API_KEY"):
                await voice_mod.transcribe(b"fake-audio", "audio/webm")

    @pytest.mark.asyncio
    async def test_transcribe_api_error(self):
        """transcribe() raises RuntimeError on API failure."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch.dict("os.environ", {"TTS_OPENAI_API_KEY": "sk-test"}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                from services.voice import transcribe

                with pytest.raises(RuntimeError, match="HTTP 500"):
                    await transcribe(b"fake-audio", "audio/webm")

    def test_get_api_key_missing(self):
        """_get_api_key() raises RuntimeError when key is missing."""
        with patch.dict("os.environ", {}, clear=True):
            import importlib
            import services.voice as voice_mod
            importlib.reload(voice_mod)

            with pytest.raises(RuntimeError, match="TTS_OPENAI_API_KEY"):
                voice_mod._get_api_key()

    def test_get_api_key_present(self):
        """_get_api_key() returns the key when set."""
        with patch.dict("os.environ", {"TTS_OPENAI_API_KEY": "sk-test"}):
            from services.voice import _get_api_key
            assert _get_api_key() == "sk-test"

    def test_allowed_audio_types(self):
        """ALLOWED_AUDIO_TYPES contains expected formats."""
        from services.voice import ALLOWED_AUDIO_TYPES
        assert "audio/webm" in ALLOWED_AUDIO_TYPES
        assert "audio/wav" in ALLOWED_AUDIO_TYPES
        assert "audio/mpeg" in ALLOWED_AUDIO_TYPES
        assert "text/html" not in ALLOWED_AUDIO_TYPES


class TestVoiceEndpoints:
    """API endpoint tests (require the FastAPI test client)."""

    def test_transcribe_endpoint_empty_file(self, client):
        """POST /api/assistant/transcribe rejects empty files."""
        r = client.post(
            "/api/assistant/transcribe",
            files={"file": ("audio.webm", b"", "audio/webm")},
        )
        assert r.status_code == 400

    def test_transcribe_endpoint_bad_content_type(self, client):
        """POST /api/assistant/transcribe rejects non-audio content types."""
        r = client.post(
            "/api/assistant/transcribe",
            files={"file": ("doc.pdf", b"fake-data", "application/pdf")},
        )
        assert r.status_code == 400
        assert "Unsupported audio format" in r.json()["detail"]

    def test_transcribe_endpoint_success(self, client):
        """POST /api/assistant/transcribe returns transcription."""
        mock_result = {"text": "Hello world", "duration_s": 1.5}

        with patch("main.transcribe", new_callable=AsyncMock, return_value=mock_result):
            r = client.post(
                "/api/assistant/transcribe",
                files={"file": ("audio.webm", b"fake-audio-data", "audio/webm")},
            )
            assert r.status_code == 200
            data = r.json()
            assert data["text"] == "Hello world"

    def test_tts_endpoint_empty_text(self, client):
        """POST /api/assistant/tts rejects empty text."""
        r = client.post(
            "/api/assistant/tts",
            json={"text": "", "voice": "onyx"},
        )
        assert r.status_code == 400 or r.status_code == 422

    def test_tts_endpoint_too_long(self, client):
        """POST /api/assistant/tts rejects text over 4096 chars."""
        r = client.post(
            "/api/assistant/tts",
            json={"text": "x" * 5000, "voice": "onyx"},
        )
        assert r.status_code == 400

    def test_tts_endpoint_no_api_key(self, client):
        """POST /api/assistant/tts returns 503 when API key is missing."""
        with patch("main._get_api_key", side_effect=RuntimeError("TTS_OPENAI_API_KEY is not set")):
            r = client.post(
                "/api/assistant/tts",
                json={"text": "Hello", "voice": "onyx"},
            )
            assert r.status_code == 503

    def test_voices_endpoint(self, client):
        """GET /api/assistant/voices lists available voices."""
        r = client.get("/api/assistant/voices")
        assert r.status_code == 200
        data = r.json()
        assert "voices" in data
        assert "onyx" in data["voices"]
        assert data["default"] == "onyx"
