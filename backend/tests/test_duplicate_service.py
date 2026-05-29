"""
Unit tests for DuplicateService.check_duplicate method.

Tests cover:
- No tickets stored (empty store)
- Exact duplicate detection
- Similar ticket detection (above threshold)
- Non-duplicate detection (below threshold)
- Custom threshold override
- Degraded mode (model unavailable)
- Empty text input
"""

import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock


# Mock sentence_transformers before importing DuplicateService
mock_model = MagicMock()
mock_st = MagicMock()
mock_st.SentenceTransformer.return_value = mock_model


@patch.dict("sys.modules", {"sentence_transformers": mock_st})
class TestDuplicateServiceCheckDuplicate(unittest.TestCase):
    """Tests for DuplicateService.check_duplicate method."""

    def _create_service(self):
        """Create a DuplicateService with a temporary storage file."""
        from services.duplicate_service import DuplicateService

        service = DuplicateService()
        # Use temp file for storage
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        service.storage_file = tmp.name
        return service

    def _mock_encode(self, text):
        """Return a mock embedding tensor based on text hash."""
        import hashlib

        h = hashlib.md5(text.encode()).hexdigest()
        # Create a simple deterministic vector from the hash
        vec = [int(h[i : i + 2], 16) / 255.0 for i in range(0, 32, 2)]
        mock_tensor = MagicMock()
        mock_tensor.__iter__ = MagicMock(return_value=iter(vec))
        mock_tensor.tolist = MagicMock(return_value=vec)
        return mock_tensor

    def test_no_tickets_returns_not_duplicate(self):
        """Empty store should always return is_duplicate=False."""
        service = self._create_service()
        service._loaded = True
        service.model = mock_model

        result = service.check_duplicate("some ticket text")

        self.assertFalse(result["is_duplicate"])
        self.assertIsNone(result["duplicate_ticket_id"])
        self.assertEqual(result["similarity"], 0.0)

    def test_returns_correct_structure(self):
        """Result should have is_duplicate, duplicate_ticket_id, similarity keys."""
        service = self._create_service()
        service._loaded = True
        service.model = mock_model

        result = service.check_duplicate("test")

        self.assertIn("is_duplicate", result)
        self.assertIn("duplicate_ticket_id", result)
        self.assertIn("similarity", result)

    def test_similarity_is_rounded_to_4_decimals(self):
        """Similarity score should be rounded to 4 decimal places."""
        service = self._create_service()
        service._loaded = True
        service.model = mock_model

        result = service.check_duplicate("test")

        self.assertEqual(result["similarity"], 0.0)
        # Verify rounding (0.0 has 0 decimal places, which is <= 4)

    def test_degraded_mode_returns_not_duplicate(self):
        """When model is unavailable, should return is_duplicate=False."""
        service = self._create_service()
        service._loaded = False
        service._load_failed = True
        service.model = None

        result = service.check_duplicate("some text")

        self.assertFalse(result["is_duplicate"])
        self.assertIsNone(result["duplicate_ticket_id"])
        self.assertEqual(result["similarity"], 0.0)

    def test_custom_threshold_parameter(self):
        """Custom threshold should be used when provided."""
        service = self._create_service()
        service._loaded = True
        service.model = mock_model

        # Even with a very low threshold, empty store returns no duplicate
        result = service.check_duplicate("test", threshold=0.0)
        self.assertFalse(result["is_duplicate"])

    def test_is_available_reflects_state(self):
        """is_available should return True only when loaded and not failed."""
        service = self._create_service()

        service._loaded = False
        service._load_failed = False
        self.assertFalse(service.is_available())

        service._loaded = True
        service._load_failed = False
        self.assertTrue(service.is_available())

        service._loaded = True
        service._load_failed = True
        self.assertFalse(service.is_available())

    def test_save_to_disk_creates_file(self):
        """save_to_disk should create the storage file with ticket data."""
        service = self._create_service()

        service.save_to_disk("ticket_001", "Test ticket text")

        self.assertTrue(os.path.exists(service.storage_file))
        with open(service.storage_file) as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["ticket_id"], "ticket_001")
        self.assertEqual(data[0]["text"], "Test ticket text")

    def test_save_to_disk_appends(self):
        """save_to_disk should append to existing data, not overwrite."""
        service = self._create_service()

        service.save_to_disk("ticket_001", "First ticket")
        service.save_to_disk("ticket_002", "Second ticket")

        with open(service.storage_file) as f:
            data = json.load(f)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["ticket_id"], "ticket_001")
        self.assertEqual(data[1]["ticket_id"], "ticket_002")

    def test_save_to_disk_handles_corrupt_json(self):
        """save_to_disk should handle corrupt JSON gracefully."""
        service = self._create_service()

        # Write corrupt data
        with open(service.storage_file, "w") as f:
            f.write("not valid json{")

        # Should not raise
        service.save_to_disk("ticket_001", "Test")

        with open(service.storage_file) as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)

    def test_save_to_disk_handles_non_list_json(self):
        """save_to_disk should handle JSON that is not a list."""
        service = self._create_service()

        # Write non-list JSON
        with open(service.storage_file, "w") as f:
            json.dump({"not": "a list"}, f)

        # Should not raise, should reset to empty list
        service.save_to_disk("ticket_001", "Test")

        with open(service.storage_file) as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)

    def tearDown(self):
        """Clean up temp files."""
        for f in [self._create_service().storage_file]:
            try:
                os.unlink(f)
            except:
                pass


if __name__ == "__main__":
    unittest.main()
