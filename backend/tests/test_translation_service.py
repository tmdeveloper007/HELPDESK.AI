"""Tests for translation_service.py"""

import pytest
from unittest.mock import patch, MagicMock

from backend.services.translation_service import (
    detect_language,
    get_supported_languages,
    _get_model_name,
    translate_text,
    translate_ticket,
    clear_cache,
    SUPPORTED_LANGUAGES,
    _translation_cache,
    _model_cache,
)


class TestDetectLanguage:
    def test_detect_language_returns_string(self):
        with patch("langdetect.detect", return_value="en"):
            result = detect_language("Hello world")
            assert result == "en"

    def test_detect_language_empty_string(self):
        result = detect_language("")
        assert result is None

    def test_detect_language_whitespace_only(self):
        result = detect_language("   ")
        assert result is None

    def test_detect_language_short_text(self):
        result = detect_language("ab")
        assert result is None

    def test_detect_language_exception_handling(self):
        with patch("langdetect.detect", side_effect=Exception("detect failed")):
            result = detect_language("Some text here")
            assert result is None


class TestGetSupportedLanguages:
    def test_returns_dict(self):
        result = get_supported_languages()
        assert isinstance(result, dict)

    def test_contains_common_languages(self):
        result = get_supported_languages()
        assert "en" in result
        assert "es" in result
        assert "fr" in result
        assert "de" in result

    def test_values_are_language_names(self):
        result = get_supported_languages()
        for code, name in result.items():
            assert isinstance(name, str)
            assert len(name) > 0

    def test_returns_copy(self):
        result = get_supported_languages()
        original = SUPPORTED_LANGUAGES.copy()
        result["en"] = "Changed"
        assert original["en"] == "English"


class TestGetModelName:
    def test_format(self):
        result = _get_model_name("en", "es")
        assert result == "Helsinki-NLP/opus-mt-en-es"

    def test_different_languages(self):
        result = _get_model_name("fr", "de")
        assert result == "Helsinki-NLP/opus-mt-fr-de"

    def test_same_language(self):
        result = _get_model_name("en", "en")
        assert result == "Helsinki-NLP/opus-mt-en-en"


class TestTranslateText:
    def setup_method(self):
        clear_cache()

    def test_empty_text_returns_empty(self):
        result = translate_text("")
        assert result["translated"] == ""
        assert result["cached"] is False

    def test_whitespace_only_returns_empty(self):
        result = translate_text("   ")
        assert result["translated"] == ""
        assert result["cached"] is False

    def test_same_source_target_returns_original(self):
        result = translate_text("Hello world", target_lang="en", source_lang="en")
        assert result["translated"] == "Hello world"
        assert result["cached"] is False

    def test_max_text_length_truncation(self, monkeypatch):
        monkeypatch.setattr("backend.services.translation_service.MAX_TEXT_LENGTH", 10)
        long_text = "This is a very long text that should be truncated"
        result = translate_text(long_text, target_lang="es")
        assert result["translated"].endswith("...")

    def test_translate_text_no_source_lang_and_unknown(self):
        with patch("backend.services.translation_service.detect_language", return_value=None):
            result = translate_text("Some text", target_lang="es")
            assert result["translated"] == "Some text"
            assert result["source_lang"] == "unknown"

    def test_translate_text_loads_model_and_translates(self):
        with patch("backend.services.translation_service._load_translation_model") as mock_load:
            mock_load.return_value = (MagicMock(), MagicMock())
            mock_model = mock_load.return_value[0]
            mock_tokenizer = mock_load.return_value[1]
            mock_tokenizer.return_value = {"input_ids": MagicMock()}
            mock_model.generate.return_value = [MagicMock()]
            mock_tokenizer.decode.side_effect = lambda x, **kw: "translated text"
            result = translate_text("Hello world", target_lang="es", source_lang="en")
            assert result["target_lang"] == "es"
            assert result["source_lang"] == "en"

    def test_translate_text_model_load_failure(self):
        with patch("backend.services.translation_service._load_translation_model", return_value=None):
            result = translate_text("Hello world", target_lang="es", source_lang="en")
            assert result["translated"] == "Hello world"
            assert result["cached"] is False


class TestTranslateTicket:
    def setup_method(self):
        clear_cache()

    def test_empty_ticket_data(self):
        result = translate_ticket({})
        assert result["original_language"] is None
        assert result["target_language"] == "en"
        assert result["translations"] == {}

    def test_translate_subject(self):
        with patch("backend.services.translation_service.translate_text") as mock_t:
            mock_t.return_value = {
                "translated": "translated subject",
                "source_lang": "es",
                "target_lang": "en",
                "cached": False,
            }
            result = translate_ticket({"subject": "asunto"}, target_lang="en")
            assert result["original_language"] == "es"
            assert "subject" in result["translations"]

    def test_translate_description(self):
        with patch("backend.services.translation_service.translate_text") as mock_t:
            mock_t.return_value = {
                "translated": "translated desc",
                "source_lang": "fr",
                "target_lang": "en",
                "cached": False,
            }
            result = translate_ticket({"description": "description francaise"}, target_lang="en")
            assert result["original_language"] == "fr"
            assert "description" in result["translations"]

    def test_translate_messages(self):
        with patch("backend.services.translation_service.translate_text") as mock_t:
            mock_t.return_value = {
                "translated": "translated msg",
                "source_lang": "de",
                "target_lang": "en",
                "cached": False,
            }
            result = translate_ticket(
                {"messages": [{"content": "German message"}]},
                target_lang="en"
            )
            assert "messages" in result["translations"]
            assert len(result["translations"]["messages"]) == 1
            assert result["translations"]["messages"][0]["original"] == "German message"

    def test_original_language_first_detected(self):
        with patch("backend.services.translation_service.translate_text") as mock_t:
            mock_t.side_effect = [
                {"translated": "subj", "source_lang": "es", "target_lang": "en", "cached": False},
                {"translated": "desc", "source_lang": "fr", "target_lang": "en", "cached": False},
            ]
            result = translate_ticket({"subject": "asunto", "description": "descripcion"}, target_lang="en")
            assert result["original_language"] == "es"


class TestClearCache:
    def test_clears_translation_cache(self):
        _translation_cache["test_key"] = "test_value"
        clear_cache()
        assert len(_translation_cache) == 0

    def test_clears_model_cache(self):
        _model_cache["test_model"] = "test_value"
        clear_cache()
        assert len(_model_cache) == 0

    def test_clear_cache_idempotent(self):
        clear_cache()
        clear_cache()
        assert len(_translation_cache) == 0
        assert len(_model_cache) == 0