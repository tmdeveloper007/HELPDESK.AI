import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.modules['sentence_transformers'] = MagicMock()

from backend.services.duplicate_service import DuplicateService


class TestDuplicateServiceCheckDuplicate:
    """Tests for DuplicateService.check_duplicate method"""

    def test_check_duplicate_threshold_override(self):
        """Test that threshold override works correctly"""
        svc = DuplicateService()
        mock_model = MagicMock()
        mock_emb = MagicMock()
        mock_model.encode.return_value = mock_emb
        svc.model = mock_model
        svc._loaded = True

        stored_emb = MagicMock()
        util_mock = MagicMock()
        util_mock.cos_sim.return_value.item.return_value = 0.75
        with patch('backend.services.duplicate_service.util', util_mock):
            util_mock.cos_sim.return_value.item.return_value = 0.75
            svc._tickets = [("TICKET-1", stored_emb, "stored text")]
            result = svc.check_duplicate("query text", threshold=0.7)
        assert result["is_duplicate"] is True

    def test_check_duplicate_empty_ticket_store(self):
        """Test behavior with empty ticket store"""
        svc = DuplicateService()
        mock_model = MagicMock()
        svc.model = mock_model
        svc._loaded = True
        svc._tickets = []

        result = svc.check_duplicate("some text")
        assert result["is_duplicate"] is False
        assert result["duplicate_ticket_id"] is None
        assert result["similarity"] == 0.0

    def test_check_duplicate_degraded_mode(self):
        """Test behavior when model is not available"""
        svc = DuplicateService()
        svc._loaded = False
        svc._load_failed = True

        result = svc.check_duplicate("some text")
        assert result["is_duplicate"] is False
        assert result["duplicate_ticket_id"] is None
        assert result["similarity"] == 0.0

    def test_check_duplicate_empty_text_returns_early(self):
        """Test that empty text returns no duplicate without model call"""
        svc = DuplicateService()
        svc._loaded = True
        svc._load_failed = False

        result = svc.check_duplicate("")
        assert result["is_duplicate"] is False
        assert result["duplicate_ticket_id"] is None
        assert result["similarity"] == 0.0

        result = svc.check_duplicate("   ")
        assert result["is_duplicate"] is False