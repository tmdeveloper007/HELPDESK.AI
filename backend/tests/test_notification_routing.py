import pytest
import sys
from unittest.mock import patch, MagicMock

# Mock supabase package before importing NotificationRoutingMiddleware
sys.modules['supabase'] = MagicMock()

from backend.services.notification_routing import NotificationRoutingMiddleware, NotificationType


class TestNotificationRoutingMiddleware:
    """Unit tests for NotificationRoutingMiddleware"""

    @patch('backend.services.notification_routing.create_client')
    def test_middleware_initialization(self, mock_create_client):
        """Test that middleware initializes supabase client correctly"""
        mock_create_client.return_value = MagicMock()
        middleware = NotificationRoutingMiddleware()
        assert middleware.supabase is not None

    @patch('backend.services.notification_routing.create_client')
    def test_fetch_system_settings_success(self, mock_create_client):
        """Test fetching settings successfully from DB"""
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        # Mock supabase query execution chain
        mock_response = MagicMock()
        mock_response.data = {
            "email_notifications": False,
            "admin_alerts": True,
            "digest_frequency": "weekly"
        }
        mock_supabase.table().select().eq().single().execute.return_value = mock_response

        middleware = NotificationRoutingMiddleware()
        settings = middleware._fetch_system_settings("company-123")
        
        assert settings["email_notifications"] is False
        assert settings["admin_alerts"] is True
        assert settings["digest_frequency"] == "weekly"

    @patch('backend.services.notification_routing.create_client')
    def test_fetch_system_settings_exception_fails_open(self, mock_create_client):
        """Test that fetch settings fails open when DB raises exception"""
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        mock_supabase.table.side_effect = Exception("DB error")

        middleware = NotificationRoutingMiddleware()
        settings = middleware._fetch_system_settings("company-123")
        
        # Should return default settings
        assert settings["email_notifications"] is True
        assert settings["admin_alerts"] is True
        assert settings["digest_frequency"] == "daily"

    @patch('backend.services.notification_routing.create_client')
    def test_get_system_settings_caching(self, mock_create_client):
        """Test that settings are cached after the first fetch"""
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        mock_response = MagicMock()
        mock_response.data = {
            "email_notifications": True,
            "admin_alerts": True,
            "digest_frequency": "daily"
        }
        mock_supabase.table().select().eq().single().execute.return_value = mock_response

        middleware = NotificationRoutingMiddleware()
        
        # Reset table mock to clear call count from setup
        mock_supabase.table.reset_mock()
        
        # Fetch twice
        settings1 = middleware.get_system_settings("company-123")
        settings2 = middleware.get_system_settings("company-123")
        
        # table select should be called exactly once
        assert mock_supabase.table.call_count == 1
        assert settings1 == settings2

    @patch('backend.services.notification_routing.create_client')
    def test_should_send_email_notification(self, mock_create_client):
        """Test should_send_email_notification gating logic"""
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        middleware = NotificationRoutingMiddleware()

        # Case 1: email_notifications is False
        middleware._settings_cache["company-123"] = {
            "email_notifications": False,
            "admin_alerts": True,
            "digest_frequency": "daily"
        }
        assert middleware.should_send_email_notification("company-123", NotificationType.TICKET_ALERT) is False

        # Case 2: email_notifications is True, digest_frequency is daily, daily digest allowed
        middleware._settings_cache["company-123"] = {
            "email_notifications": True,
            "admin_alerts": True,
            "digest_frequency": "daily"
        }
        assert middleware.should_send_email_notification("company-123", NotificationType.DAILY_DIGEST) is True

        # Case 3: email_notifications is True, digest_frequency is disabled, daily digest not allowed
        middleware._settings_cache["company-123"] = {
            "email_notifications": True,
            "admin_alerts": True,
            "digest_frequency": "disabled"
        }
        assert middleware.should_send_email_notification("company-123", NotificationType.DAILY_DIGEST) is False

        # Case 4: email_notifications is True, digest_frequency is daily, weekly digest not allowed (frequency mismatch)
        middleware._settings_cache["company-123"] = {
            "email_notifications": True,
            "admin_alerts": True,
            "digest_frequency": "daily"
        }
        assert middleware.should_send_email_notification("company-123", NotificationType.WEEKLY_DIGEST) is False

    @patch('backend.services.notification_routing.create_client')
    def test_should_send_admin_alert(self, mock_create_client):
        """Test should_send_admin_alert gating logic"""
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        middleware = NotificationRoutingMiddleware()

        # Case 1: admin_alerts is False
        middleware._settings_cache["company-123"] = {
            "email_notifications": True,
            "admin_alerts": False,
            "digest_frequency": "daily"
        }
        assert middleware.should_send_admin_alert("company-123") is False

        # Case 2: admin_alerts is True
        middleware._settings_cache["company-123"] = {
            "email_notifications": True,
            "admin_alerts": True,
            "digest_frequency": "daily"
        }
        assert middleware.should_send_admin_alert("company-123") is True

    @patch('backend.services.notification_routing.create_client')
    def test_should_send_push_notification(self, mock_create_client):
        """Test should_send_push_notification gating logic"""
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        middleware = NotificationRoutingMiddleware()

        # Case 1: email_notifications is False (gates push as well)
        middleware._settings_cache["company-123"] = {
            "email_notifications": False,
            "admin_alerts": True,
            "digest_frequency": "daily"
        }
        assert middleware.should_send_push_notification("company-123") is False

        # Case 2: email_notifications is True
        middleware._settings_cache["company-123"] = {
            "email_notifications": True,
            "admin_alerts": True,
            "digest_frequency": "daily"
        }
        assert middleware.should_send_push_notification("company-123") is True

    @patch('backend.services.notification_routing.create_client')
    def test_invalidate_cache(self, mock_create_client):
        """Test that invalidate_cache removes settings from cache"""
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        middleware = NotificationRoutingMiddleware()
        middleware._settings_cache["company-123"] = {
            "email_notifications": True,
            "admin_alerts": True,
            "digest_frequency": "daily"
        }
        
        assert "company-123" in middleware._settings_cache
        middleware.invalidate_cache("company-123")
        assert "company-123" not in middleware._settings_cache
