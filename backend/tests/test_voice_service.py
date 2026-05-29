"""
Tests for the Voice-to-Ticket service and API endpoints.

Covers:
- Audio validation (empty, too large, wrong format)
- Transcription pipeline (mocked Whisper model)
- API endpoint responses and error handling
- Title extraction helper

Issue #207: Voice-to-Ticket Feature
"""

import pytest
import asyncio
import os
import struct
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------

class TestAudioValidation:
    """Test _validate_audio_bytes helper."""

    def test_empty_audio_returns_error(self):
        from backend.services.voice_service import _validate_audio_bytes

        result = _validate_audio_bytes(b"", "test.webm")
        assert result is not None
        assert "Empty" in result

    def test_oversized_audio_returns_error(self):
        from backend.services.voice_service import _validate_audio_bytes

        big = b"\x00" * (26 * 1024 * 1024)  # 26 MB
        result = _validate_audio_bytes(big, "test.webm")
        assert result is not None
        assert "too large" in result

    def test_unsupported_extension_returns_error(self):
        from backend.services.voice_service import _validate_audio_bytes

        result = _validate_audio_bytes(b"\x00" * 100, "test.xyz")
        assert result is not None
        assert "Unsupported" in result

    def test_valid_audio_returns_none(self):
        from backend.services.voice_service import _validate_audio_bytes

        result = _validate_audio_bytes(b"\x00" * 100, "test.webm")
        assert result is None

    def test_no_filename_passes(self):
        from backend.services.voice_service import _validate_audio_bytes

        result = _validate_audio_bytes(b"\x00" * 100, "")
        assert result is None


class TestGuessSuffix:
    """Test _guess_suffix helper."""

    def test_known_extension(self):
        from backend.services.voice_service import _guess_suffix

        assert _guess_suffix("recording.wav") == ".wav"
        assert _guess_suffix("audio.mp3") == ".mp3"

    def test_unknown_extension_defaults_to_webm(self):
        from backend.services.voice_service import _guess_suffix

        assert _guess_suffix("file.xyz") == ".webm"
        assert _guess_suffix("") == ".webm"


class TestTitleExtraction:
    """Test _extract_title helper."""

    def test_empty_text(self):
        from backend.routes.voice import _extract_title

        assert _extract_title("") == "Voice Support Request"

    def test_short_text(self):
        from backend.routes.voice import _extract_title

        assert _extract_title("My VPN is broken") == "My VPN is broken"

    def test_first_sentence(self):
        from backend.routes.voice import _extract_title

        text = "My VPN is broken. It has been down for two days now."
        assert _extract_title(text) == "My VPN is broken"

    def test_long_text_truncated(self):
        from backend.routes.voice import _extract_title

        text = "A" * 200
        result = _extract_title(text, max_length=80)
        assert len(result) <= 83  # 80 + "..."
        assert result.endswith("...")


# ---------------------------------------------------------------------------
# Transcription pipeline tests (mocked)
# ---------------------------------------------------------------------------

class TestTranscriptionPipeline:
    """Test transcribe_audio_async with a mocked Whisper model."""

    @pytest.mark.asyncio
    async def test_transcribe_success(self):
        from backend.services import voice_service

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "My laptop won't connect to the VPN",
            "language": "en",
        }

        with patch.object(voice_service, "_whisper_model", mock_model):
            result = await voice_service.transcribe_audio_async(
                file_bytes=b"\x1a\x45\xdf\xa3" + b"\x00" * 100,
                filename="test.webm",
            )

        assert result["transcribed_text"] == "My laptop won't connect to the VPN"
        assert result["detected_language"] == "en"
        assert result["confidence"] > 0

    @pytest.mark.asyncio
    async def test_transcribe_empty_audio_raises(self):
        from backend.services.voice_service import transcribe_audio_async

        with pytest.raises(ValueError, match="Empty"):
            await transcribe_audio_async(b"", "test.webm")

    @pytest.mark.asyncio
    async def test_transcribe_with_language_hint(self):
        from backend.services import voice_service

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "Mi laptop no se conecta a la VPN",
            "language": "es",
        }

        with patch.object(voice_service, "_whisper_model", mock_model):
            result = await voice_service.transcribe_audio_async(
                file_bytes=b"\x1a\x45\xdf\xa3" + b"\x00" * 100,
                filename="test.webm",
                language="es",
            )

        assert result["detected_language"] == "es"
        mock_model.transcribe.assert_called_once()
        call_kwargs = mock_model.transcribe.call_args
        assert call_kwargs[1].get("language") == "es"

    @pytest.mark.asyncio
    async def test_transcribe_no_text_returns_zero_confidence(self):
        from backend.services import voice_service

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "   ",
            "language": "en",
        }

        with patch.object(voice_service, "_whisper_model", mock_model):
            result = await voice_service.transcribe_audio_async(
                file_bytes=b"\x1a\x45\xdf\xa3" + b"\x00" * 100,
                filename="test.webm",
            )

        assert result["confidence"] == 0.0


# ---------------------------------------------------------------------------
# API endpoint tests (uses httpx test client)
# ---------------------------------------------------------------------------

class TestVoiceEndpoints:
    """Test the /api/voice FastAPI endpoints."""

    @pytest.fixture
    def client(self):
        from httpx import AsyncClient, ASGITransport
        # We need to import the app to test
        import sys
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        from backend.main import app

        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        resp = await client.get("/api/voice/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "supported_formats" in data

    @pytest.mark.asyncio
    async def test_transcribe_no_file_returns_422(self, client):
        resp = await client.post("/api/voice/transcribe")
        assert resp.status_code == 422  # FastAPI validation error

    @pytest.mark.asyncio
    async def test_transcribe_empty_file_returns_400(self, client):
        resp = await client.post(
            "/api/voice/transcribe",
            files={"audio": ("test.webm", b"", "audio/webm")},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_ticket_no_file_returns_422(self, client):
        resp = await client.post("/api/voice/create-ticket")
        assert resp.status_code == 422
