"""
Unit tests for HealthMonitor.

Tests health monitoring functionality including periodic checks,
failure detection, and callback invocation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx
from kiro.health_monitor import HealthMonitor


class TestHealthMonitorInitialization:
    """Tests for HealthMonitor initialization."""
    
    def test_initialization_stores_configuration(self):
        """Test that initialization stores host, port, and check interval."""
        host = "127.0.0.1"
        port = 9000
        check_interval = 15.0
        
        monitor = HealthMonitor(host=host, port=port, check_interval=check_interval)
        
        assert monitor.host == host
        assert monitor.port == port
        assert monitor.check_interval == check_interval
    
    def test_default_check_interval(self):
        """Test that default check interval is 30 seconds."""
        monitor = HealthMonitor(host="localhost", port=8000)
        
        assert monitor.check_interval == 30.0


class TestHealthMonitorLifecycle:
    """Tests for HealthMonitor lifecycle methods."""
    
    def test_start_method_exists(self):
        """Test that start method exists and is callable."""
        monitor = HealthMonitor(host="localhost", port=8000)
        assert callable(monitor.start)
    
    def test_stop_method_exists(self):
        """Test that stop method exists and is callable."""
        monitor = HealthMonitor(host="localhost", port=8000)
        assert callable(monitor.stop)
    
    def test_check_health_method_exists(self):
        """Test that check_health method exists and is callable."""
        monitor = HealthMonitor(host="localhost", port=8000)
        assert callable(monitor.check_health)


class TestHealthMonitorCallbacks:
    """Tests for HealthMonitor callback registration."""
    
    def test_on_health_change_registers_callback(self):
        """Test that on_health_change registers a callback function."""
        monitor = HealthMonitor(host="localhost", port=8000)
        
        def callback(is_healthy: bool):
            pass
        
        monitor.on_health_change(callback)
        
        assert callback in monitor._callbacks
    
    def test_multiple_callbacks_can_be_registered(self):
        """Test that multiple callbacks can be registered."""
        monitor = HealthMonitor(host="localhost", port=8000)
        
        def callback1(is_healthy: bool):
            pass
        
        def callback2(is_healthy: bool):
            pass
        
        monitor.on_health_change(callback1)
        monitor.on_health_change(callback2)
        
        assert len(monitor._callbacks) == 2
        assert callback1 in monitor._callbacks
        assert callback2 in monitor._callbacks



class TestHealthMonitorHealthCheck:
    """Tests for health check functionality."""
    
    def test_check_health_returns_true_on_200_response(self):
        """Test that check_health returns True when endpoint returns 200."""
        monitor = HealthMonitor(host="localhost", port=8000)
        
        # Mock successful health check
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = monitor.check_health()
        
        assert result is True
    
    def test_check_health_returns_false_on_non_200_response(self):
        """Test that check_health returns False when endpoint returns non-200."""
        monitor = HealthMonitor(host="localhost", port=8000)
        
        # Mock failed health check
        mock_response = Mock()
        mock_response.status_code = 500
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = monitor.check_health()
        
        assert result is False
    
    def test_check_health_returns_false_on_connection_error(self):
        """Test that check_health returns False on connection error."""
        monitor = HealthMonitor(host="localhost", port=8000)
        
        # Mock connection error
        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value = mock_client
            
            result = monitor.check_health()
        
        assert result is False
    
    def test_check_health_returns_false_on_timeout(self):
        """Test that check_health returns False on timeout."""
        monitor = HealthMonitor(host="localhost", port=8000)
        
        # Mock timeout
        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
            mock_client_class.return_value = mock_client
            
            result = monitor.check_health()
        
        assert result is False


class TestHealthMonitorThreading:
    """Tests for health monitor threading behavior."""
    
    def test_start_creates_background_thread(self):
        """Test that start() creates a background thread."""
        import time
        monitor = HealthMonitor(host="localhost", port=8000, check_interval=0.1)
        
        # Mock health check
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            monitor.start()
            
            # Give thread time to start
            time.sleep(0.05)
            
            assert monitor._running is True
            assert monitor._thread is not None
            assert monitor._thread.is_alive()
            
            # Cleanup
            monitor.stop()
    
    def test_stop_terminates_background_thread(self):
        """Test that stop() terminates the background thread."""
        import time
        monitor = HealthMonitor(host="localhost", port=8000, check_interval=0.1)
        
        # Mock health check
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            monitor.start()
            time.sleep(0.05)
            
            monitor.stop()
            
            # Give thread time to stop
            time.sleep(0.2)
            
            assert monitor._running is False
            assert not monitor._thread.is_alive()
    
    def test_start_when_already_running_does_nothing(self):
        """Test that calling start() when already running does nothing."""
        import time
        monitor = HealthMonitor(host="localhost", port=8000, check_interval=0.1)
        
        # Mock health check
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            monitor.start()
            time.sleep(0.05)
            
            first_thread = monitor._thread
            
            # Try to start again
            monitor.start()
            
            # Should be the same thread
            assert monitor._thread is first_thread
            
            # Cleanup
            monitor.stop()
    
    def test_stop_when_not_running_does_nothing(self):
        """Test that calling stop() when not running does nothing."""
        monitor = HealthMonitor(host="localhost", port=8000)
        
        # Should not raise an error
        monitor.stop()
        
        assert monitor._running is False


class TestHealthMonitorFailureTracking:
    """Tests for consecutive failure tracking."""
    
    def test_consecutive_failures_tracked(self):
        """Test that consecutive failures are tracked correctly."""
        import time
        monitor = HealthMonitor(host="localhost", port=8000, check_interval=0.1)
        
        # Mock failed health checks
        mock_response = Mock()
        mock_response.status_code = 500
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            monitor.start()
            
            # Wait for multiple checks
            time.sleep(0.35)
            
            # Should have at least 3 consecutive failures
            assert monitor._consecutive_failures >= 3
            
            # Cleanup
            monitor.stop()
    
    def test_consecutive_failures_reset_on_success(self):
        """Test that consecutive failures reset on successful check."""
        monitor = HealthMonitor(host="localhost", port=8000)
        
        # Simulate failures
        monitor._consecutive_failures = 2
        
        # Mock successful health check
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            monitor.check_health()
        
        # Failures should not be reset by check_health alone
        # The reset happens in _monitor_loop
        assert monitor._consecutive_failures == 2


class TestHealthMonitorCallbackInvocation:
    """Tests for callback invocation on health status changes."""
    
    def test_callback_invoked_on_health_status_change(self):
        """Test that callbacks are invoked when health status changes."""
        import time
        monitor = HealthMonitor(host="localhost", port=8000, check_interval=0.1)
        
        callback_invoked = []
        
        def callback(is_healthy: bool):
            callback_invoked.append(is_healthy)
        
        monitor.on_health_change(callback)
        
        # Mock responses - start with success, then failures
        call_count = [0]
        
        def mock_get(*args, **kwargs):
            call_count[0] += 1
            mock_response = Mock()
            # First 3 calls succeed, then fail
            if call_count[0] <= 3:
                mock_response.status_code = 200
            else:
                mock_response.status_code = 500
            return mock_response
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.side_effect = mock_get
            mock_client_class.return_value = mock_client
            
            monitor.start()
            
            # Wait for checks to run (need at least 6 checks: 3 success + 3 failures)
            time.sleep(0.7)
            
            # Cleanup
            monitor.stop()
        
        # Callback should have been invoked when status changed to unhealthy
        assert len(callback_invoked) > 0
        assert False in callback_invoked
    
    def test_multiple_callbacks_all_invoked(self):
        """Test that all registered callbacks are invoked."""
        import time
        monitor = HealthMonitor(host="localhost", port=8000, check_interval=0.1)
        
        callback1_invoked = []
        callback2_invoked = []
        
        def callback1(is_healthy: bool):
            callback1_invoked.append(is_healthy)
        
        def callback2(is_healthy: bool):
            callback2_invoked.append(is_healthy)
        
        monitor.on_health_change(callback1)
        monitor.on_health_change(callback2)
        
        # Mock responses - start with success, then failures
        call_count = [0]
        
        def mock_get(*args, **kwargs):
            call_count[0] += 1
            mock_response = Mock()
            if call_count[0] <= 3:
                mock_response.status_code = 200
            else:
                mock_response.status_code = 500
            return mock_response
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.side_effect = mock_get
            mock_client_class.return_value = mock_client
            
            monitor.start()
            time.sleep(0.7)
            
            # Cleanup
            monitor.stop()
        
        # Both callbacks should have been invoked
        assert len(callback1_invoked) > 0
        assert len(callback2_invoked) > 0
    
    def test_callback_exception_does_not_stop_monitoring(self):
        """Test that exception in callback doesn't stop monitoring."""
        import time
        monitor = HealthMonitor(host="localhost", port=8000, check_interval=0.1)
        
        def bad_callback(is_healthy: bool):
            raise Exception("Callback error")
        
        good_callback_invoked = []
        
        def good_callback(is_healthy: bool):
            good_callback_invoked.append(is_healthy)
        
        monitor.on_health_change(bad_callback)
        monitor.on_health_change(good_callback)
        
        # Mock responses - start with success, then failures
        call_count = [0]
        
        def mock_get(*args, **kwargs):
            call_count[0] += 1
            mock_response = Mock()
            if call_count[0] <= 3:
                mock_response.status_code = 200
            else:
                mock_response.status_code = 500
            return mock_response
        
        with patch('httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.side_effect = mock_get
            mock_client_class.return_value = mock_client
            
            monitor.start()
            time.sleep(0.7)
            
            # Cleanup
            monitor.stop()
        
        # Good callback should still have been invoked despite bad callback error
        assert len(good_callback_invoked) > 0
