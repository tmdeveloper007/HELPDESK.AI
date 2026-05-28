import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.modules['supabase'] = MagicMock()

from backend.services.notification_routing import NotificationRoutingMiddleware, NotificationType


class TestShouldSendAdminAlert:
    """Tests for should_send_admin_alert method"""

    def test_returns_true_when_admin_alerts_enabled(self):
        """Test that should_send_admin_alert returns True when admin_alerts is True"""
        middleware = NotificationRoutingMiddleware()
        middleware._settings_cache.clear()

        with patch.object(middleware, '_fetch_system_settings', return_value={
            'email_notifications': True,
            'admin_alerts': True,
            'digest_frequency': 'daily'
        }):
            result = middleware.should_send_admin_alert('company-123')
            assert result is True

    def test_returns_false_when_admin_alerts_disabled(self):
        """Test that should_send_admin_alert returns False when admin_alerts is False"""
        middleware = NotificationRoutingMiddleware()
        middleware._settings_cache.clear()

        with patch.object(middleware, '_fetch_system_settings', return_value={
            'email_notifications': True,
            'admin_alerts': False,
            'digest_frequency': 'daily'
        }):
            result = middleware.should_send_admin_alert('company-123')
            assert result is False

    def test_returns_true_when_settings_not_found(self):
        """Test fail-open: returns True when settings not found in DB"""
        middleware = NotificationRoutingMiddleware()
        middleware._settings_cache.clear()

        with patch.object(middleware, '_fetch_system_settings', return_value={
            'email_notifications': True,
            'admin_alerts': True,
            'digest_frequency': 'daily'
        }):
            result = middleware.should_send_admin_alert('company-456')
            assert result is True

    def test_uses_cached_settings_on_subsequent_calls(self):
        """Test that cached settings are used on second call"""
        middleware = NotificationRoutingMiddleware()
        middleware._settings_cache.clear()

        cached_settings = {
            'email_notifications': True,
            'admin_alerts': False,
            'digest_frequency': 'daily'
        }
        middleware._settings_cache['company-789'] = cached_settings

        with patch.object(middleware, '_fetch_system_settings') as mock_fetch:
            result = middleware.should_send_admin_alert('company-789')
            assert result is False
            mock_fetch.assert_not_called()

    def test_notifies_when_admin_alerts_disabled_logs_warning(self):
        """Test that warning is logged when admin_alerts are disabled"""
        middleware = NotificationRoutingMiddleware()
        middleware._settings_cache.clear()
        middleware.log_level = 'warning'

        with patch.object(middleware, '_fetch_system_settings', return_value={
            'email_notifications': True,
            'admin_alerts': False,
            'digest_frequency': 'daily'
        }):
            result = middleware.should_send_admin_alert('company-123')
            assert result is False
