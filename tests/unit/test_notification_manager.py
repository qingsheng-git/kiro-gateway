"""
Unit tests for NotificationManager.

Tests Windows notification functionality including rate limiting,
error notifications, and action buttons.
"""

import pytest
import time
from kiro.notification_manager import NotificationManager


class TestNotificationManagerInitialization:
    """Tests for NotificationManager initialization."""
    
    def test_initialization_stores_rate_limit(self):
        """Test that initialization stores rate limit configuration."""
        rate_limit = 30.0
        
        manager = NotificationManager(rate_limit=rate_limit)
        
        assert manager.rate_limit == rate_limit
    
    def test_default_rate_limit(self):
        """Test that default rate limit is 60 seconds."""
        manager = NotificationManager()
        
        assert manager.rate_limit == 60.0
    
    def test_initial_last_notification_time_is_zero(self):
        """Test that initial last notification time is 0."""
        manager = NotificationManager()
        
        assert manager._last_notification_time == 0.0


class TestNotificationManagerRateLimiting:
    """Tests for NotificationManager rate limiting."""
    
    def test_can_notify_returns_true_initially(self):
        """Test that can_notify returns True when no notifications have been sent."""
        manager = NotificationManager(rate_limit=60.0)
        
        assert manager.can_notify() is True
    
    def test_can_notify_returns_false_within_rate_limit(self):
        """Test that can_notify returns False within rate limit period."""
        manager = NotificationManager(rate_limit=1.0)
        manager._last_notification_time = time.time()
        
        assert manager.can_notify() is False
    
    def test_can_notify_returns_true_after_rate_limit(self):
        """Test that can_notify returns True after rate limit period."""
        manager = NotificationManager(rate_limit=0.1)
        manager._last_notification_time = time.time() - 0.2
        
        assert manager.can_notify() is True


class TestNotificationManagerMethods:
    """Tests for NotificationManager notification methods."""
    
    def test_notify_error_method_exists(self):
        """Test that notify_error method exists and is callable."""
        manager = NotificationManager()
        assert callable(manager.notify_error)
    
    def test_notify_info_method_exists(self):
        """Test that notify_info method exists and is callable."""
        manager = NotificationManager()
        assert callable(manager.notify_info)
    
    def test_notify_error_updates_last_notification_time(self):
        """Test that notify_error updates last notification time."""
        manager = NotificationManager(rate_limit=60.0)
        initial_time = manager._last_notification_time
        
        manager.notify_error("Test Error", "Test message")
        
        assert manager._last_notification_time > initial_time
    
    def test_notify_info_updates_last_notification_time(self):
        """Test that notify_info updates last notification time."""
        manager = NotificationManager(rate_limit=60.0)
        initial_time = manager._last_notification_time
        
        manager.notify_info("Test Info", "Test message")
        
        assert manager._last_notification_time > initial_time
    
    def test_notify_error_respects_rate_limit(self):
        """Test that notify_error respects rate limiting."""
        manager = NotificationManager(rate_limit=1.0)
        
        # First notification should succeed
        manager.notify_error("Error 1", "Message 1")
        first_time = manager._last_notification_time
        
        # Second notification should be rate limited (time not updated)
        manager.notify_error("Error 2", "Message 2")
        second_time = manager._last_notification_time
        
        assert first_time == second_time
    
    def test_notify_info_respects_rate_limit(self):
        """Test that notify_info respects rate limiting."""
        manager = NotificationManager(rate_limit=1.0)
        
        # First notification should succeed
        manager.notify_info("Info 1", "Message 1")
        first_time = manager._last_notification_time
        
        # Second notification should be rate limited (time not updated)
        manager.notify_info("Info 2", "Message 2")
        second_time = manager._last_notification_time
        
        assert first_time == second_time


class TestNotificationManagerHelperMethods:
    """Tests for NotificationManager helper methods."""
    
    def test_notify_startup_failure_with_port_error(self):
        """Test that notify_startup_failure generates appropriate message for port errors."""
        manager = NotificationManager(rate_limit=60.0)
        
        # Should not raise exception
        manager.notify_startup_failure("Error: port 8000 already in use")
        
        # Verify last notification time was updated
        assert manager._last_notification_time > 0
    
    def test_notify_startup_failure_with_credential_error(self):
        """Test that notify_startup_failure generates appropriate message for credential errors."""
        manager = NotificationManager(rate_limit=60.0)
        
        # Should not raise exception
        manager.notify_startup_failure("Authentication failed: invalid credentials")
        
        # Verify last notification time was updated
        assert manager._last_notification_time > 0
    
    def test_notify_startup_failure_with_import_error(self):
        """Test that notify_startup_failure generates appropriate message for import errors."""
        manager = NotificationManager(rate_limit=60.0)
        
        # Should not raise exception
        manager.notify_startup_failure("ImportError: No module named 'fastapi'")
        
        # Verify last notification time was updated
        assert manager._last_notification_time > 0
    
    def test_notify_startup_failure_with_generic_error(self):
        """Test that notify_startup_failure handles generic errors."""
        manager = NotificationManager(rate_limit=60.0)
        
        # Should not raise exception
        manager.notify_startup_failure("Unknown error occurred")
        
        # Verify last notification time was updated
        assert manager._last_notification_time > 0
    
    def test_notify_service_crash(self):
        """Test that notify_service_crash displays crash notification."""
        manager = NotificationManager(rate_limit=60.0)
        
        # Should not raise exception
        manager.notify_service_crash(exit_code=1)
        
        # Verify last notification time was updated
        assert manager._last_notification_time > 0
    
    def test_notify_auth_failure(self):
        """Test that notify_auth_failure displays auth failure notification."""
        manager = NotificationManager(rate_limit=60.0)
        
        # Should not raise exception
        manager.notify_auth_failure()
        
        # Verify last notification time was updated
        assert manager._last_notification_time > 0
    
    def test_notify_health_check_failure(self):
        """Test that notify_health_check_failure displays health check notification."""
        manager = NotificationManager(rate_limit=60.0)
        
        # Should not raise exception
        manager.notify_health_check_failure()
        
        # Verify last notification time was updated
        assert manager._last_notification_time > 0
    
    def test_set_on_view_logs_callback(self):
        """Test that set_on_view_logs_callback stores callback."""
        manager = NotificationManager(rate_limit=60.0)
        callback_called = []
        
        def test_callback():
            callback_called.append(True)
        
        # Should not raise exception
        manager.set_on_view_logs_callback(test_callback)
        
        # Verify callback was stored
        assert manager._on_view_logs is not None
        assert callable(manager._on_view_logs)


class TestNotificationManagerWithIcon:
    """Tests for NotificationManager with pystray icon."""
    
    def test_initialization_with_icon(self):
        """Test that initialization accepts icon parameter."""
        # Mock icon object
        class MockIcon:
            def notify(self, title, message):
                pass
        
        mock_icon = MockIcon()
        manager = NotificationManager(icon=mock_icon, rate_limit=60.0)
        
        assert manager.icon is mock_icon
    
    def test_initialization_without_icon(self):
        """Test that initialization works without icon parameter."""
        manager = NotificationManager(rate_limit=60.0)
        
        assert manager.icon is None
