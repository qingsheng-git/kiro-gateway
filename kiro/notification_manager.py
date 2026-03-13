"""
Notification Manager for Windows toast notifications.

This module handles displaying Windows notifications for errors and events,
with rate limiting to prevent notification spam.
"""

from typing import Optional, Callable
import time
from loguru import logger

try:
    import pystray
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    logger.warning("pystray not available - notifications will be logged only")


class NotificationManager:
    """
    Handles Windows toast notifications.
    
    Displays Windows notifications for errors and events, implements rate limiting
    (max 1 per minute), and provides action buttons in notifications.
    """
    
    def __init__(self, icon: Optional['pystray.Icon'] = None, rate_limit: float = 60.0):
        """
        Initialize notification manager with rate limiting.
        
        Args:
            icon: pystray.Icon instance for displaying notifications (optional)
            rate_limit: Minimum time between notifications in seconds (default: 60.0)
        """
        self.icon = icon
        self.rate_limit = rate_limit
        self._last_notification_time: float = 0.0
        self._on_view_logs: Optional[Callable[[], None]] = None
        logger.info(f"NotificationManager initialized with rate_limit={rate_limit}s")
    
    def notify_error(self, title: str, message: str, show_logs_action: bool = True) -> None:
        """
        Display error notification with optional logs action.
        
        Args:
            title: Notification title
            message: Notification message
            show_logs_action: Whether to show "View Logs" action button (default: True)
        """
        if not self.can_notify():
            logger.debug(f"Notification rate limited: {title}")
            return
        
        logger.info(f"Displaying error notification: {title} - {message}")
        
        # Display notification using pystray if available
        if PYSTRAY_AVAILABLE and self.icon is not None:
            try:
                self.icon.notify(
                    title=title,
                    message=message
                )
                logger.debug("Notification displayed successfully")
            except Exception as e:
                logger.error(f"Failed to display notification: {e}")
        else:
            logger.warning(f"Notification (not displayed): {title} - {message}")
        
        self._last_notification_time = time.time()
    
    def notify_info(self, title: str, message: str) -> None:
        """
        Display informational notification.
        
        Args:
            title: Notification title
            message: Notification message
        """
        if not self.can_notify():
            logger.debug(f"Notification rate limited: {title}")
            return
        
        logger.info(f"Displaying info notification: {title} - {message}")
        
        # Display notification using pystray if available
        if PYSTRAY_AVAILABLE and self.icon is not None:
            try:
                self.icon.notify(
                    title=title,
                    message=message
                )
                logger.debug("Notification displayed successfully")
            except Exception as e:
                logger.error(f"Failed to display notification: {e}")
        else:
            logger.warning(f"Notification (not displayed): {title} - {message}")
        
        self._last_notification_time = time.time()
    
    def can_notify(self) -> bool:
        """
        Check if notification can be sent (rate limit check).
        
        Returns:
            True if notification can be sent, False if rate limited
        """
        elapsed = time.time() - self._last_notification_time
        return elapsed >= self.rate_limit

    def set_on_view_logs_callback(self, callback: Callable[[], None]) -> None:
        """
        Set callback for "View Logs" action button.
        
        Args:
            callback: Function to call when user clicks "View Logs"
        """
        self._on_view_logs = callback
        logger.debug("View logs callback registered")
    
    def notify_startup_failure(self, error_message: str) -> None:
        """
        Display notification for service startup failure.
        
        Args:
            error_message: Error message from startup failure
        """
        self.notify_error("Kiro Gateway - Startup Failed", error_message, show_logs_action=True)
    
    def notify_service_crash(self, exit_code: int) -> None:
        """
        Display notification for unexpected service crash.
        
        Args:
            exit_code: Process exit code
        """
        message = f"Service crashed unexpectedly (exit code: {exit_code}). Check logs for details."
        self.notify_error("Kiro Gateway - Service Crashed", message, show_logs_action=True)
    
    def notify_auth_failure(self) -> None:
        """Display notification for authentication failure."""
        message = (
            "Authentication failed. Please check:\n"
            "1. Refresh token in .env file\n"
            "2. Credentials file location\n"
            "3. AWS SSO session validity"
        )
        self.notify_error("Kiro Gateway - Authentication Failed", message, show_logs_action=True)
    
    def notify_health_check_failure(self) -> None:
        """Display notification for health check failure."""
        message = "Service health check failed. The service may be unresponsive."
        self.notify_error("Kiro Gateway - Health Check Failed", message, show_logs_action=True)
