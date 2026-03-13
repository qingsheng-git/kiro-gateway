"""
Windows System Tray Application for Kiro Gateway.

This module provides the main TrayApplication class that orchestrates the system tray
functionality, including menu management, icon updates, and integration with service
management, health monitoring, and notifications.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from pathlib import Path
from loguru import logger

try:
    import pystray
    from pystray import MenuItem as Item
    from PIL import Image
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    logger.warning("pystray not available - tray functionality disabled")

from kiro.service_manager import ServiceManager, ServiceState
from kiro.settings_manager import SettingsManager
from kiro.icon_manager import IconManager
from kiro.notification_manager import NotificationManager
from kiro.health_monitor import HealthMonitor
from kiro.platform_utils import open_file_explorer

if TYPE_CHECKING:
    import pystray


class TrayApplication:
    """
    Main orchestrator for Windows system tray functionality.
    
    Manages the pystray icon, builds and updates the tray menu dynamically,
    coordinates between ServiceManager, SettingsManager, and HealthMonitor,
    and handles user interactions from menu items.
    """
    
    def __init__(
        self,
        service_manager: ServiceManager,
        settings_manager: SettingsManager,
        icon_manager: IconManager,
        notification_manager: NotificationManager,
        health_monitor: HealthMonitor
    ):
        """
        Initialize tray application with all required managers.
        
        Args:
            service_manager: ServiceManager instance for controlling the service
            settings_manager: SettingsManager instance for configuration
            icon_manager: IconManager instance for icon assets
            notification_manager: NotificationManager instance for notifications
            health_monitor: HealthMonitor instance for health checks
        """
        if not PYSTRAY_AVAILABLE:
            raise ImportError("pystray is required for tray functionality")
        
        self.service_manager = service_manager
        self.settings_manager = settings_manager
        self.icon_manager = icon_manager
        self.notification_manager = notification_manager
        self.health_monitor = health_monitor
        
        # Get initial icon
        initial_icon = self.icon_manager.get_icon("stopped")
        if initial_icon is None:
            raise RuntimeError("Failed to load initial icon")
        
        # Create pystray icon
        self.icon = pystray.Icon(
            "kiro_gateway",
            initial_icon,
            "Kiro Gateway - Stopped",
            menu=self.build_menu()
        )
        
        # Register health monitor callback
        self.health_monitor.on_health_change(self._on_health_change)
        
        # Set notification manager icon
        self.notification_manager.icon = self.icon
        
        # Set view logs callback
        self.notification_manager.set_on_view_logs_callback(self.on_open_logs)
        
        logger.info(f"TrayApplication initialized for {service_manager.host}:{service_manager.port}")
    
    def build_menu(self) -> pystray.Menu:
        """
        Build the tray menu with current state.
        
        Creates a pystray.Menu with all required items:
        - Status display (disabled, shows current state)
        - Start Service
        - Restart Service
        - Stop Service
        - Separator
        - Start with Windows (checkbox)
        - Open Logs
        - Separator
        - Exit
        
        Menu items are enabled/disabled based on current service state.
        Uses lambda functions for dynamic enabled/checked states.
        
        Returns:
            pystray.Menu instance
        """
        # Build menu with dynamic enabled states
        menu = pystray.Menu(
            # Status display (disabled, shows current state)
            Item(
                lambda item: f"Status: {self.service_manager.get_state().value.title()}",
                lambda: None,
                enabled=False,
                default=True
            ),
            
            # Service control items with dynamic enabled states
            Item(
                "Start Service",
                self.on_start_service,
                enabled=lambda item: self.service_manager.get_state() == ServiceState.STOPPED
            ),
            Item(
                "Restart Service",
                self.on_restart_service,
                enabled=lambda item: self.service_manager.get_state() == ServiceState.RUNNING
            ),
            Item(
                "Stop Service",
                self.on_stop_service,
                enabled=lambda item: self.service_manager.get_state() == ServiceState.RUNNING
            ),
            
            # Separator
            pystray.Menu.SEPARATOR,
            
            # Settings
            Item(
                "Start with Windows",
                self.on_toggle_auto_start,
                checked=lambda item: self.settings_manager.is_auto_start_enabled()
            ),
            
            # Logs
            Item(
                "Open Logs",
                self.on_open_logs
            ),
            
            # Separator
            pystray.Menu.SEPARATOR,
            
            # Exit
            Item(
                "Exit",
                self.on_exit
            )
        )
        
        state = self.service_manager.get_state()
        auto_start_enabled = self.settings_manager.is_auto_start_enabled()
        logger.debug(f"Menu built with state={state.value}, "
                    f"auto_start={auto_start_enabled}")
        
        return menu
    
    def update_icon(self, state: ServiceState) -> None:
        """
        Update tray icon based on service state.
        
        Args:
            state: Current ServiceState
        """
        icon_image = self.icon_manager.get_icon(state.value)
        if icon_image:
            self.icon.icon = icon_image
            logger.debug(f"Icon updated for state: {state.value}")
        else:
            logger.warning(f"Failed to get icon for state: {state.value}")
    
    def update_tooltip(self) -> None:
        """
        Update tooltip text based on current state.
        
        Displays "Kiro Gateway - {state}" and includes server URL when running.
        """
        state = self.service_manager.get_state()
        
        if state == ServiceState.RUNNING:
            tooltip = f"Kiro Gateway - {state.value.title()}\n{self.service_manager.host}:{self.service_manager.port}"
        else:
            tooltip = f"Kiro Gateway - {state.value.title()}"
        
        self.icon.title = tooltip
        logger.debug(f"Tooltip updated: {tooltip}")
    
    def on_start_service(self, icon=None, item=None) -> None:
        """Handle Start Service menu action."""
        logger.info("User action: Start Service")
        
        # Start the service
        success = self.service_manager.start()
        
        if success:
            # Start health monitoring
            self.health_monitor.start()
            
            # Update UI
            self.update_icon(ServiceState.RUNNING)
            self.update_tooltip()
            self.icon.update_menu()
            
            # Notify user
            self.notification_manager.notify_info(
                "Kiro Gateway",
                "Service started successfully"
            )
        else:
            # Service failed to start - get error details
            error_type, error_text = self.service_manager.get_last_error()
            logger.error(f"Service startup failed: type={error_type}")
            
            # Update UI
            self.update_icon(ServiceState.ERROR)
            self.update_tooltip()
            self.icon.update_menu()
            
            # Notify user with specific error guidance
            self._notify_startup_error(error_type, error_text)
    
    def on_stop_service(self, icon=None, item=None) -> None:
        """Handle Stop Service menu action."""
        logger.info("User action: Stop Service")
        
        # Stop health monitoring first
        self.health_monitor.stop()
        
        # Stop the service
        success = self.service_manager.stop()
        
        # Update UI
        state = self.service_manager.get_state()
        self.update_icon(state)
        self.update_tooltip()
        self.icon.update_menu()
        
        if success:
            # Notify user
            self.notification_manager.notify_info(
                "Kiro Gateway",
                "Service stopped successfully"
            )
        else:
            # Service failed to stop cleanly
            self.notification_manager.notify_error(
                "Kiro Gateway",
                "Service stop encountered errors"
            )
    
    def on_restart_service(self, icon=None, item=None) -> None:
        """Handle Restart Service menu action."""
        logger.info("User action: Restart Service")
        
        # Stop health monitoring
        self.health_monitor.stop()
        
        # Restart the service
        success = self.service_manager.restart()
        
        if success:
            # Start health monitoring
            self.health_monitor.start()
            
            # Update UI
            self.update_icon(ServiceState.RUNNING)
            self.update_tooltip()
            self.icon.update_menu()
            
            # Notify user
            self.notification_manager.notify_info(
                "Kiro Gateway",
                "Service restarted successfully"
            )
        else:
            # Service failed to restart
            state = self.service_manager.get_state()
            self.update_icon(state)
            self.update_tooltip()
            self.icon.update_menu()
            
            # Notify user with error
            self.notification_manager.notify_error(
                "Kiro Gateway",
                "Service restart failed"
            )
    
    def on_toggle_auto_start(self, icon=None, item=None) -> None:
        """Handle Start with Windows toggle action."""
        logger.info("User action: Toggle Auto-Start")
        
        # Check current state
        is_enabled = self.settings_manager.is_auto_start_enabled()
        
        if is_enabled:
            # Disable auto-start
            success = self.settings_manager.disable_auto_start()
            if success:
                logger.info("Auto-start disabled")
                self.notification_manager.notify_info(
                    "Kiro Gateway",
                    "Auto-start disabled"
                )
            else:
                logger.error("Failed to disable auto-start")
                self.notification_manager.notify_error(
                    "Kiro Gateway",
                    "Failed to disable auto-start. Check permissions."
                )
        else:
            # Enable auto-start
            success = self.settings_manager.enable_auto_start()
            if success:
                logger.info("Auto-start enabled")
                self.notification_manager.notify_info(
                    "Kiro Gateway",
                    "Auto-start enabled"
                )
            else:
                logger.error("Failed to enable auto-start")
                self.notification_manager.notify_error(
                    "Kiro Gateway",
                    "Failed to enable auto-start. Check permissions."
                )
        
        # Update menu to reflect new state
        self.icon.update_menu()
    
    def on_open_logs(self, icon=None, item=None) -> None:
        """Handle Open Logs menu action."""
        logger.info("User action: Open Logs")
        
        try:
            # Get log directory
            log_dir = self.service_manager.log_file.parent
            
            # Open in file explorer
            open_file_explorer(log_dir)
            
            logger.info(f"Opened log directory: {log_dir}")
        except Exception as e:
            logger.error(f"Failed to open log directory: {e}")
            self.notification_manager.notify_error(
                "Kiro Gateway",
                f"Failed to open log directory: {e}"
            )
    
    def on_exit(self, icon=None, item=None) -> None:
        """Handle Exit menu action."""
        logger.info("User action: Exit")
        
        # Stop the tray application
        self.stop()
    
    def run(self) -> None:
        """
        Start the tray application (blocking call).
        
        Starts the pystray event loop, which blocks until stop() is called.
        """
        logger.info("Starting tray application")
        
        # Run the pystray event loop (blocking)
        self.icon.run()
        
        logger.info("Tray application event loop exited")
    
    def stop(self) -> None:
        """
        Stop the tray application and cleanup resources.
        
        Stops the service if running, stops health monitoring,
        and removes the tray icon.
        """
        logger.info("Stopping tray application")
        
        try:
            # Stop health monitoring
            if self.health_monitor:
                self.health_monitor.stop()
            
            # Stop service if running
            if self.service_manager and self.service_manager.is_running():
                logger.info("Stopping service before exit")
                self.service_manager.stop()
            
            # Stop the tray icon
            if self.icon:
                self.icon.stop()
                logger.info("Tray icon removed")
        
        except Exception as e:
            logger.error(f"Error during tray application shutdown: {e}")
    
    def _on_health_change(self, is_healthy: bool) -> None:
        """
        Callback for health status changes.
        
        Args:
            is_healthy: Current health status
        """
        logger.info(f"Health status changed: is_healthy={is_healthy}")
        
        if not is_healthy:
            # Check if this is a crash (process exited unexpectedly)
            if self.service_manager._process and self.service_manager._process.poll() is not None:
                exit_code = self.service_manager._process.returncode
                if exit_code != 0:
                    logger.error(f"Service crashed with exit code {exit_code}")
                    
                    # Transition to ERROR state
                    self.service_manager._set_state(ServiceState.ERROR)
                    
                    # Update UI
                    self.update_icon(ServiceState.ERROR)
                    self.update_tooltip()
                    self.icon.update_menu()
                    
                    # Notify user about crash
                    self.notification_manager.notify_service_crash(exit_code)
                    return
            
            # Check if this is an authentication failure
            if self.service_manager.detect_auth_failure_in_logs():
                logger.error("Authentication failure detected in logs")
                
                # Transition to ERROR state
                self.service_manager._set_state(ServiceState.ERROR)
                
                # Update UI
                self.update_icon(ServiceState.ERROR)
                self.update_tooltip()
                self.icon.update_menu()
                
                # Notify user about auth failure
                self.notification_manager.notify_auth_failure()
                return
            
            # Generic health check failure
            self.service_manager._set_state(ServiceState.ERROR)
            
            # Update icon to warning/error state
            self.update_icon(ServiceState.ERROR)
            self.update_tooltip()
            self.icon.update_menu()
            
            # Notify user
            self.notification_manager.notify_health_check_failure()
        else:
            # Health restored - transition back to RUNNING
            if self.service_manager.get_state() == ServiceState.ERROR:
                self.service_manager._set_state(ServiceState.RUNNING)
                
                # Update icon to normal state
                self.update_icon(ServiceState.RUNNING)
                self.update_tooltip()
                self.icon.update_menu()
                
                # Notify user
                self.notification_manager.notify_info(
                    "Kiro Gateway",
                    "Service health restored"
                )
    
    def _notify_startup_error(self, error_type: str, error_text: str) -> None:
        """
        Notify user about startup error with specific guidance.
        
        Args:
            error_type: Type of error (port_in_use, auth_failure, import_error, unknown)
            error_text: Full error text from logs
        """
        if error_type == "port_in_use":
            message = (
                "Port is already in use.\n\n"
                "Solutions:\n"
                "1. Stop other services using the port\n"
                "2. Change the port in settings\n"
                "3. Check for other Kiro Gateway instances"
            )
        elif error_type == "auth_failure":
            message = (
                "Authentication failed.\n\n"
                "Please check:\n"
                "1. Refresh token in .env file\n"
                "2. Credentials file location\n"
                "3. AWS SSO session validity"
            )
        elif error_type == "import_error":
            message = (
                "Missing dependencies detected.\n\n"
                "Please run:\n"
                "pip install -r requirements.txt"
            )
        else:
            # Extract first error line for display
            error_lines = error_text.strip().split('\n')
            error_summary = error_lines[-1] if error_lines else "Unknown error"
            message = f"Service failed to start.\n\nError: {error_summary[:100]}"
        
        self.notification_manager.notify_error(
            "Kiro Gateway - Startup Failed",
            message,
            show_logs_action=True
        )
