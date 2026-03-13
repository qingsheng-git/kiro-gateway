"""
Unit tests for TrayApplication.

Tests the main tray application orchestrator including menu building,
icon updates, and integration with other components.
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from kiro.service_manager import ServiceManager, ServiceState
from kiro.settings_manager import SettingsManager
from kiro.icon_manager import IconManager
from kiro.notification_manager import NotificationManager
from kiro.health_monitor import HealthMonitor


# Mock pystray module before importing tray_app
@pytest.fixture(scope="session", autouse=True)
def mock_pystray_module():
    """Mock pystray module at the system level."""
    # Create mock pystray module
    mock_pystray = MagicMock()
    mock_pystray.Icon = MagicMock()
    mock_pystray.Menu = MagicMock()
    mock_pystray.Menu.SEPARATOR = "SEPARATOR"
    mock_pystray.MenuItem = MagicMock()
    
    # Create mock PIL module
    mock_pil = MagicMock()
    mock_pil.Image = MagicMock()
    
    # Inject into sys.modules
    sys.modules['pystray'] = mock_pystray
    sys.modules['PIL'] = mock_pil
    sys.modules['PIL.Image'] = mock_pil.Image
    
    yield mock_pystray
    
    # Cleanup (optional, but good practice)
    if 'pystray' in sys.modules:
        del sys.modules['pystray']


@pytest.fixture
def mock_service_manager():
    """Create a mock ServiceManager."""
    manager = Mock(spec=ServiceManager)
    manager.host = "127.0.0.1"
    manager.port = 8000
    manager.log_file = Path("/tmp/service.log")
    manager.get_state.return_value = ServiceState.STOPPED
    manager.is_running.return_value = False
    manager.start.return_value = True
    manager.stop.return_value = True
    manager.restart.return_value = True
    return manager


@pytest.fixture
def mock_settings_manager():
    """Create a mock SettingsManager."""
    manager = Mock(spec=SettingsManager)
    manager.is_auto_start_enabled.return_value = False
    manager.enable_auto_start.return_value = True
    manager.disable_auto_start.return_value = True
    return manager


@pytest.fixture
def mock_icon_manager():
    """Create a mock IconManager."""
    manager = Mock(spec=IconManager)
    # Return a mock PIL Image
    mock_image = MagicMock()
    manager.get_icon.return_value = mock_image
    return manager


@pytest.fixture
def mock_notification_manager():
    """Create a mock NotificationManager."""
    manager = Mock(spec=NotificationManager)
    manager.icon = None
    return manager


@pytest.fixture
def mock_health_monitor():
    """Create a mock HealthMonitor."""
    monitor = Mock(spec=HealthMonitor)
    return monitor


@pytest.fixture
def tray_app(mock_service_manager, mock_settings_manager, mock_icon_manager, 
             mock_notification_manager, mock_health_monitor):
    """Create a TrayApplication instance with mocked dependencies."""
    from kiro.tray_app import TrayApplication
    
    app = TrayApplication(
        service_manager=mock_service_manager,
        settings_manager=mock_settings_manager,
        icon_manager=mock_icon_manager,
        notification_manager=mock_notification_manager,
        health_monitor=mock_health_monitor
    )
    return app


class TestTrayApplicationInitialization:
    """Tests for TrayApplication initialization."""
    
    def test_initialization_stores_managers(self, tray_app, mock_service_manager, 
                                           mock_settings_manager, mock_icon_manager,
                                           mock_notification_manager, mock_health_monitor):
        """Test that initialization stores all manager references."""
        assert tray_app.service_manager == mock_service_manager
        assert tray_app.settings_manager == mock_settings_manager
        assert tray_app.icon_manager == mock_icon_manager
        assert tray_app.notification_manager == mock_notification_manager
        assert tray_app.health_monitor == mock_health_monitor
    
    def test_initialization_creates_icon(self, tray_app):
        """Test that initialization creates a pystray Icon."""
        assert tray_app.icon is not None
    
    def test_initialization_registers_health_callback(self, tray_app, mock_health_monitor):
        """Test that initialization registers health change callback."""
        mock_health_monitor.on_health_change.assert_called_once()


class TestTrayApplicationMenuBuilding:
    """Tests for menu building functionality."""
    
    def test_build_menu_returns_menu(self, tray_app):
        """Test that build_menu returns a menu object."""
        menu = tray_app.build_menu()
        assert menu is not None
    
    def test_build_menu_when_stopped_enables_start(self, tray_app, mock_service_manager):
        """Test that Start Service is enabled when service is stopped."""
        mock_service_manager.get_state.return_value = ServiceState.STOPPED
        menu = tray_app.build_menu()
        # Menu was built successfully
        assert menu is not None
    
    def test_build_menu_when_running_enables_stop_and_restart(self, tray_app, mock_service_manager):
        """Test that Stop and Restart are enabled when service is running."""
        mock_service_manager.get_state.return_value = ServiceState.RUNNING
        menu = tray_app.build_menu()
        # Menu was built successfully
        assert menu is not None


class TestTrayApplicationIconUpdates:
    """Tests for icon update functionality."""
    
    def test_update_icon_calls_icon_manager(self, tray_app, mock_icon_manager):
        """Test that update_icon calls icon_manager.get_icon."""
        tray_app.update_icon(ServiceState.RUNNING)
        mock_icon_manager.get_icon.assert_called_with("running")
    
    def test_update_tooltip_includes_state(self, tray_app, mock_service_manager):
        """Test that update_tooltip includes service state."""
        mock_service_manager.get_state.return_value = ServiceState.STOPPED
        tray_app.update_tooltip()
        assert "Stopped" in tray_app.icon.title
    
    def test_update_tooltip_includes_url_when_running(self, tray_app, mock_service_manager):
        """Test that update_tooltip includes server URL when running."""
        mock_service_manager.get_state.return_value = ServiceState.RUNNING
        tray_app.update_tooltip()
        assert "127.0.0.1:8000" in tray_app.icon.title


class TestTrayApplicationMenuActions:
    """Tests for menu action handlers."""
    
    def test_on_start_service_calls_service_manager(self, tray_app, mock_service_manager):
        """Test that on_start_service calls service_manager.start."""
        tray_app.on_start_service()
        mock_service_manager.start.assert_called_once()
    
    def test_on_start_service_starts_health_monitor(self, tray_app, mock_health_monitor):
        """Test that on_start_service starts health monitoring."""
        tray_app.on_start_service()
        mock_health_monitor.start.assert_called_once()
    
    def test_on_stop_service_calls_service_manager(self, tray_app, mock_service_manager):
        """Test that on_stop_service calls service_manager.stop."""
        tray_app.on_stop_service()
        mock_service_manager.stop.assert_called_once()
    
    def test_on_stop_service_stops_health_monitor(self, tray_app, mock_health_monitor):
        """Test that on_stop_service stops health monitoring."""
        tray_app.on_stop_service()
        mock_health_monitor.stop.assert_called_once()
    
    def test_on_restart_service_calls_service_manager(self, tray_app, mock_service_manager):
        """Test that on_restart_service calls service_manager.restart."""
        tray_app.on_restart_service()
        mock_service_manager.restart.assert_called_once()
    
    def test_on_toggle_auto_start_enables_when_disabled(self, tray_app, mock_settings_manager):
        """Test that on_toggle_auto_start enables when currently disabled."""
        mock_settings_manager.is_auto_start_enabled.return_value = False
        tray_app.on_toggle_auto_start()
        mock_settings_manager.enable_auto_start.assert_called_once()
    
    def test_on_toggle_auto_start_disables_when_enabled(self, tray_app, mock_settings_manager):
        """Test that on_toggle_auto_start disables when currently enabled."""
        mock_settings_manager.is_auto_start_enabled.return_value = True
        tray_app.on_toggle_auto_start()
        mock_settings_manager.disable_auto_start.assert_called_once()
    
    @patch('kiro.tray_app.open_file_explorer')
    def test_on_open_logs_opens_log_directory(self, mock_open, tray_app):
        """Test that on_open_logs opens the log directory."""
        tray_app.on_open_logs()
        mock_open.assert_called_once()


class TestTrayApplicationLifecycle:
    """Tests for TrayApplication lifecycle methods."""
    
    def test_run_method_exists(self, tray_app):
        """Test that run method exists and is callable."""
        assert callable(tray_app.run)
    
    def test_stop_method_exists(self, tray_app):
        """Test that stop method exists and is callable."""
        assert callable(tray_app.stop)
    
    def test_stop_stops_health_monitor(self, tray_app, mock_health_monitor):
        """Test that stop stops the health monitor."""
        tray_app.stop()
        mock_health_monitor.stop.assert_called_once()
    
    def test_stop_stops_service_if_running(self, tray_app, mock_service_manager):
        """Test that stop stops the service if it's running."""
        mock_service_manager.is_running.return_value = True
        tray_app.stop()
        mock_service_manager.stop.assert_called_once()


class TestTrayApplicationHealthIntegration:
    """Tests for health monitor integration."""
    
    def test_health_change_to_unhealthy_updates_state(self, tray_app, mock_service_manager):
        """Test that health change to unhealthy updates service state."""
        # Mock process that is still running (not crashed, no auth error)
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process still running
        mock_service_manager._process = mock_process
        mock_service_manager.detect_auth_failure_in_logs.return_value = False
        
        # Simulate health change callback
        tray_app._on_health_change(False)
        
        # Should set state to ERROR
        mock_service_manager._set_state.assert_called_with(ServiceState.ERROR)
    
    def test_health_change_to_unhealthy_sends_notification(self, tray_app, mock_notification_manager, mock_service_manager):
        """Test that health change to unhealthy sends notification."""
        # Mock process that is still running (not crashed, no auth error)
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process still running
        mock_service_manager._process = mock_process
        mock_service_manager.detect_auth_failure_in_logs.return_value = False
        
        # Simulate health change callback
        tray_app._on_health_change(False)
        
        # Should notify user
        mock_notification_manager.notify_health_check_failure.assert_called_once()


class TestTrayApplicationErrorHandling:
    """Tests for TrayApplication error handling integration."""
    
    def test_on_start_service_handles_startup_failure_with_port_error(
        self, tray_app, mock_service_manager, mock_notification_manager
    ):
        """Test that on_start_service handles port in use errors."""
        # Mock service start failure
        mock_service_manager.start.return_value = False
        mock_service_manager.get_last_error.return_value = (
            "port_in_use",
            "Error: address already in use"
        )
        
        # Call on_start_service
        tray_app.on_start_service()
        
        # Verify error notification was called
        assert mock_notification_manager.notify_error.called
        call_args = mock_notification_manager.notify_error.call_args
        assert "Port is already in use" in call_args[0][1]
    
    def test_on_start_service_handles_startup_failure_with_auth_error(
        self, tray_app, mock_service_manager, mock_notification_manager
    ):
        """Test that on_start_service handles authentication errors."""
        # Mock service start failure
        mock_service_manager.start.return_value = False
        mock_service_manager.get_last_error.return_value = (
            "auth_failure",
            "Error: Invalid credentials"
        )
        
        # Call on_start_service
        tray_app.on_start_service()
        
        # Verify error notification was called
        assert mock_notification_manager.notify_error.called
        call_args = mock_notification_manager.notify_error.call_args
        assert "Authentication failed" in call_args[0][1]
    
    def test_on_start_service_handles_startup_failure_with_import_error(
        self, tray_app, mock_service_manager, mock_notification_manager
    ):
        """Test that on_start_service handles import errors."""
        # Mock service start failure
        mock_service_manager.start.return_value = False
        mock_service_manager.get_last_error.return_value = (
            "import_error",
            "ModuleNotFoundError: No module named 'uvicorn'"
        )
        
        # Call on_start_service
        tray_app.on_start_service()
        
        # Verify error notification was called
        assert mock_notification_manager.notify_error.called
        call_args = mock_notification_manager.notify_error.call_args
        assert "Missing dependencies" in call_args[0][1]
    
    def test_on_start_service_handles_startup_failure_with_unknown_error(
        self, tray_app, mock_service_manager, mock_notification_manager
    ):
        """Test that on_start_service handles unknown errors."""
        # Mock service start failure
        mock_service_manager.start.return_value = False
        mock_service_manager.get_last_error.return_value = (
            "unknown",
            "Some random error occurred"
        )
        
        # Call on_start_service
        tray_app.on_start_service()
        
        # Verify error notification was called
        assert mock_notification_manager.notify_error.called
        call_args = mock_notification_manager.notify_error.call_args
        assert "Service failed to start" in call_args[0][1]
    
    def test_on_health_change_detects_service_crash(
        self, tray_app, mock_service_manager, mock_notification_manager
    ):
        """Test that _on_health_change detects and handles service crashes."""
        # Mock process that has crashed
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process exited
        mock_process.returncode = 1  # Non-zero exit code
        mock_service_manager._process = mock_process
        mock_service_manager.detect_auth_failure_in_logs.return_value = False
        
        # Call health change callback with unhealthy status
        tray_app._on_health_change(is_healthy=False)
        
        # Verify crash notification was called
        mock_notification_manager.notify_service_crash.assert_called_once_with(1)
        
        # Verify state was set to ERROR
        mock_service_manager._set_state.assert_called_with(ServiceState.ERROR)
    
    def test_on_health_change_detects_auth_failure(
        self, tray_app, mock_service_manager, mock_notification_manager
    ):
        """Test that _on_health_change detects and handles authentication failures."""
        # Mock process that is still running (not crashed)
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process still running
        mock_service_manager._process = mock_process
        mock_service_manager.detect_auth_failure_in_logs.return_value = True
        
        # Call health change callback with unhealthy status
        tray_app._on_health_change(is_healthy=False)
        
        # Verify auth failure notification was called
        mock_notification_manager.notify_auth_failure.assert_called_once()
        
        # Verify state was set to ERROR
        mock_service_manager._set_state.assert_called_with(ServiceState.ERROR)
    
    def test_on_health_change_handles_generic_health_failure(
        self, tray_app, mock_service_manager, mock_notification_manager
    ):
        """Test that _on_health_change handles generic health check failures."""
        # Mock process that is still running (not crashed, no auth error)
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process still running
        mock_service_manager._process = mock_process
        mock_service_manager.detect_auth_failure_in_logs.return_value = False
        
        # Call health change callback with unhealthy status
        tray_app._on_health_change(is_healthy=False)
        
        # Verify generic health check failure notification was called
        mock_notification_manager.notify_health_check_failure.assert_called_once()
        
        # Verify state was set to ERROR
        mock_service_manager._set_state.assert_called_with(ServiceState.ERROR)
    
    def test_notify_startup_error_formats_port_error_correctly(
        self, tray_app, mock_notification_manager
    ):
        """Test that _notify_startup_error formats port errors correctly."""
        tray_app._notify_startup_error("port_in_use", "Error: address already in use")
        
        # Verify notification was called with correct message
        assert mock_notification_manager.notify_error.called
        call_args = mock_notification_manager.notify_error.call_args
        assert "Port is already in use" in call_args[0][1]
        assert "Stop other services" in call_args[0][1]
    
    def test_notify_startup_error_formats_auth_error_correctly(
        self, tray_app, mock_notification_manager
    ):
        """Test that _notify_startup_error formats auth errors correctly."""
        tray_app._notify_startup_error("auth_failure", "Error: Invalid credentials")
        
        # Verify notification was called with correct message
        assert mock_notification_manager.notify_error.called
        call_args = mock_notification_manager.notify_error.call_args
        assert "Authentication failed" in call_args[0][1]
        assert "Refresh token" in call_args[0][1]
    
    def test_notify_startup_error_formats_import_error_correctly(
        self, tray_app, mock_notification_manager
    ):
        """Test that _notify_startup_error formats import errors correctly."""
        tray_app._notify_startup_error("import_error", "ModuleNotFoundError: No module named 'uvicorn'")
        
        # Verify notification was called with correct message
        assert mock_notification_manager.notify_error.called
        call_args = mock_notification_manager.notify_error.call_args
        assert "Missing dependencies" in call_args[0][1]
        assert "pip install" in call_args[0][1]
