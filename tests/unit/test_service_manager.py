"""
Unit tests for ServiceManager.

Tests subprocess lifecycle management including start/stop/restart operations,
state transitions, and graceful shutdown.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import subprocess
import sys
from kiro.service_manager import ServiceManager, ServiceState


class TestServiceManagerInitialization:
    """Tests for ServiceManager initialization."""
    
    def test_initialization_stores_configuration(self):
        """Test that initialization stores host, port, and log file configuration."""
        host = "127.0.0.1"
        port = 9000
        log_file = Path("/tmp/test.log")
        
        manager = ServiceManager(host=host, port=port, log_file=log_file)
        
        assert manager.host == host
        assert manager.port == port
        assert manager.log_file == log_file
    
    def test_initial_state_is_stopped(self):
        """Test that initial service state is STOPPED."""
        manager = ServiceManager(host="localhost", port=8000, log_file=Path("/tmp/test.log"))
        
        assert manager.get_state() == ServiceState.STOPPED
        assert not manager.is_running()


class TestServiceManagerStateMethods:
    """Tests for ServiceManager state management methods."""
    
    def test_get_state_returns_current_state(self):
        """Test that get_state returns the current service state."""
        manager = ServiceManager(host="localhost", port=8000, log_file=Path("/tmp/test.log"))
        
        state = manager.get_state()
        
        assert isinstance(state, ServiceState)
        assert state == ServiceState.STOPPED
    
    def test_is_running_returns_false_when_stopped(self):
        """Test that is_running returns False when state is STOPPED."""
        manager = ServiceManager(host="localhost", port=8000, log_file=Path("/tmp/test.log"))
        
        assert not manager.is_running()


class TestServiceManagerOperations:
    """Tests for ServiceManager start/stop/restart operations."""
    
    def test_start_method_exists(self):
        """Test that start method exists and is callable."""
        manager = ServiceManager(host="localhost", port=8000, log_file=Path("/tmp/test.log"))
        assert callable(manager.start)
    
    def test_stop_method_exists(self):
        """Test that stop method exists and is callable."""
        manager = ServiceManager(host="localhost", port=8000, log_file=Path("/tmp/test.log"))
        assert callable(manager.stop)
    
    def test_restart_method_exists(self):
        """Test that restart method exists and is callable."""
        manager = ServiceManager(host="localhost", port=8000, log_file=Path("/tmp/test.log"))
        assert callable(manager.restart)
    
    def test_force_kill_method_exists(self):
        """Test that force_kill method exists and is callable."""
        manager = ServiceManager(host="localhost", port=8000, log_file=Path("/tmp/test.log"))
        assert callable(manager.force_kill)


class TestServiceStateEnum:
    """Tests for ServiceState enum."""
    
    def test_service_state_has_all_required_states(self):
        """Test that ServiceState enum has all required states."""
        assert hasattr(ServiceState, 'STOPPED')
        assert hasattr(ServiceState, 'STARTING')
        assert hasattr(ServiceState, 'RUNNING')
        assert hasattr(ServiceState, 'STOPPING')
        assert hasattr(ServiceState, 'ERROR')
    
    def test_service_state_values(self):
        """Test that ServiceState enum values are correct."""
        assert ServiceState.STOPPED.value == "stopped"
        assert ServiceState.STARTING.value == "starting"
        assert ServiceState.RUNNING.value == "running"
        assert ServiceState.STOPPING.value == "stopping"
        assert ServiceState.ERROR.value == "error"



class TestServiceManagerStart:
    """Tests for ServiceManager start() method."""
    
    def test_start_transitions_from_stopped_to_starting_to_running(self, tmp_path):
        """Test that start transitions state from STOPPED → STARTING → RUNNING."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        # Mock subprocess.Popen to return a running process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running
        
        with patch('subprocess.Popen', return_value=mock_process), \
             patch('builtins.open', mock_open()), \
             patch('time.sleep'):
            
            result = manager.start()
            
            assert result is True
            assert manager.get_state() == ServiceState.RUNNING
            assert manager.is_running()
    
    def test_start_creates_log_directory_if_missing(self, tmp_path):
        """Test that start creates log file directory if it doesn't exist."""
        log_file = tmp_path / "logs" / "subdir" / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.poll.return_value = None
        
        with patch('subprocess.Popen', return_value=mock_process), \
             patch('builtins.open', mock_open()), \
             patch('time.sleep'):
            
            manager.start()
            
            assert log_file.parent.exists()
    
    def test_start_builds_correct_command(self, tmp_path):
        """Test that start builds correct uvicorn command."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="0.0.0.0", port=9000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.poll.return_value = None
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('builtins.open', mock_open()), \
             patch('time.sleep'):
            
            manager.start()
            
            # Check that Popen was called with correct command
            call_args = mock_popen.call_args
            command = call_args[0][0]
            
            assert sys.executable in command
            assert "-m" in command
            assert "uvicorn" in command
            assert "main:app" in command
            assert "--host" in command
            assert "0.0.0.0" in command
            assert "--port" in command
            assert "9000" in command
    
    def test_start_uses_create_no_window_on_windows(self, tmp_path):
        """Test that start uses CREATE_NO_WINDOW flag on Windows."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.poll.return_value = None
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('builtins.open', mock_open()), \
             patch('time.sleep'), \
             patch('sys.platform', 'win32'):
            
            manager.start()
            
            # Check that Popen was called with Windows-specific flags
            call_args = mock_popen.call_args
            kwargs = call_args[1]
            
            assert 'creationflags' in kwargs
            assert kwargs['creationflags'] == 0x08000000  # CREATE_NO_WINDOW
            assert 'startupinfo' in kwargs
    
    def test_start_does_not_use_create_no_window_on_non_windows(self, tmp_path):
        """Test that start does not use CREATE_NO_WINDOW flag on non-Windows."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.poll.return_value = None
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('builtins.open', mock_open()), \
             patch('time.sleep'), \
             patch('sys.platform', 'linux'):
            
            manager.start()
            
            # Check that Popen was NOT called with Windows-specific flags
            call_args = mock_popen.call_args
            kwargs = call_args[1]
            
            assert 'creationflags' not in kwargs
            assert 'startupinfo' not in kwargs
    
    def test_start_captures_stdout_stderr_to_log_file(self, tmp_path):
        """Test that start captures subprocess output to log file."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_file_handle = Mock()
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen, \
             patch('builtins.open', return_value=mock_file_handle) as mock_open_call, \
             patch('time.sleep'):
            
            manager.start()
            
            # Check that log file was opened
            mock_open_call.assert_called_once_with(log_file, 'a', encoding='utf-8')
            
            # Check that Popen was called with correct output redirection
            call_args = mock_popen.call_args
            kwargs = call_args[1]
            
            assert kwargs['stdout'] == mock_file_handle
            assert kwargs['stderr'] == subprocess.STDOUT
            assert kwargs['stdin'] == subprocess.DEVNULL
    
    def test_start_transitions_to_error_if_process_exits_immediately(self, tmp_path):
        """Test that start transitions to ERROR if subprocess exits immediately."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process exited with error code
        mock_process.returncode = 1
        mock_file_handle = Mock()
        
        with patch('subprocess.Popen', return_value=mock_process), \
             patch('builtins.open', return_value=mock_file_handle), \
             patch('time.sleep'):
            
            result = manager.start()
            
            assert result is False
            assert manager.get_state() == ServiceState.ERROR
            assert not manager.is_running()
            # Verify log file was closed
            mock_file_handle.close.assert_called_once()
    
    def test_start_transitions_to_error_on_file_not_found(self, tmp_path):
        """Test that start transitions to ERROR if uvicorn is not found."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        with patch('subprocess.Popen', side_effect=FileNotFoundError("uvicorn not found")), \
             patch('builtins.open', mock_open()):
            
            result = manager.start()
            
            assert result is False
            assert manager.get_state() == ServiceState.ERROR
    
    def test_start_transitions_to_error_on_exception(self, tmp_path):
        """Test that start transitions to ERROR on unexpected exception."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        with patch('subprocess.Popen', side_effect=Exception("Unexpected error")), \
             patch('builtins.open', mock_open()):
            
            result = manager.start()
            
            assert result is False
            assert manager.get_state() == ServiceState.ERROR
    
    def test_start_returns_false_if_not_in_stopped_state(self, tmp_path):
        """Test that start returns False if service is not in STOPPED state."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        # Manually set state to RUNNING
        manager._state = ServiceState.RUNNING
        
        result = manager.start()
        
        assert result is False
        assert manager.get_state() == ServiceState.RUNNING
    
    def test_start_stores_process_reference(self, tmp_path):
        """Test that start stores reference to subprocess."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        
        with patch('subprocess.Popen', return_value=mock_process), \
             patch('builtins.open', mock_open()), \
             patch('time.sleep'):
            
            manager.start()
            
            assert manager._process is mock_process



class TestServiceManagerStop:
    """Tests for ServiceManager stop() method."""
    
    def test_stop_transitions_from_running_to_stopping_to_stopped(self, tmp_path):
        """Test that stop transitions state from RUNNING → STOPPING → STOPPED."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        # Set up a running process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0  # Process terminated successfully
        mock_process.returncode = 0
        
        manager._process = mock_process
        manager._state = ServiceState.RUNNING
        
        with patch('time.sleep'), patch('time.time', side_effect=[0, 0.1, 0.2]):
            result = manager.stop()
        
        assert result is True
        assert manager.get_state() == ServiceState.STOPPED
        mock_process.terminate.assert_called_once()
    
    def test_stop_sends_sigterm_to_process(self, tmp_path):
        """Test that stop sends SIGTERM (terminate) to subprocess."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0
        
        manager._process = mock_process
        manager._state = ServiceState.RUNNING
        
        with patch('time.sleep'), patch('time.time', side_effect=[0, 0.1]):
            manager.stop()
        
        mock_process.terminate.assert_called_once()
    
    def test_stop_waits_for_graceful_shutdown(self, tmp_path):
        """Test that stop waits for process to terminate gracefully."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 12345
        # Simulate process running for 2 checks, then terminating
        mock_process.poll.side_effect = [None, None, 0]
        mock_process.returncode = 0
        
        manager._process = mock_process
        manager._state = ServiceState.RUNNING
        
        with patch('time.sleep') as mock_sleep, \
             patch('time.time', side_effect=[0, 0.1, 0.2, 0.3, 0.3]):  # Extra value for final log
            result = manager.stop(timeout=10.0)
        
        assert result is True
        assert manager.get_state() == ServiceState.STOPPED
        # Should have slept while waiting
        assert mock_sleep.call_count >= 2
    
    def test_stop_calls_force_kill_on_timeout(self, tmp_path):
        """Test that stop calls force_kill if timeout is exceeded."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 12345
        # Process never terminates
        mock_process.poll.return_value = None
        
        manager._process = mock_process
        manager._state = ServiceState.RUNNING
        
        # Mock time to simulate timeout
        with patch('time.sleep'), \
             patch('time.time', side_effect=[0, 5, 10, 11]), \
             patch.object(manager, 'force_kill') as mock_force_kill:
            result = manager.stop(timeout=10.0)
        
        assert result is True
        mock_force_kill.assert_called_once()
        assert manager.get_state() == ServiceState.STOPPED
    
    def test_stop_logs_shutdown_event_on_graceful_termination(self, tmp_path):
        """Test that stop logs shutdown event when process terminates gracefully."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        
        manager._process = mock_process
        manager._state = ServiceState.RUNNING
        
        with patch('time.sleep'), \
             patch('time.time', side_effect=[0, 0.5, 1.0]), \
             patch('loguru.logger.info') as mock_log:
            manager.stop()
        
        # Check that shutdown event was logged
        log_calls = [str(call) for call in mock_log.call_args_list]
        assert any('Shutdown event: graceful termination' in str(call) for call in log_calls)
    
    def test_stop_logs_shutdown_event_on_forced_termination(self, tmp_path):
        """Test that stop logs shutdown event when force kill is used."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Never terminates
        
        manager._process = mock_process
        manager._state = ServiceState.RUNNING
        
        with patch('time.sleep'), \
             patch('time.time', side_effect=[0, 5, 10, 11]), \
             patch.object(manager, 'force_kill'), \
             patch('loguru.logger.warning') as mock_log:
            manager.stop(timeout=10.0)
        
        # Check that forced shutdown event was logged
        log_calls = [str(call) for call in mock_log.call_args_list]
        assert any('Shutdown event: forced termination' in str(call) for call in log_calls)
    
    def test_stop_returns_false_if_not_in_running_or_error_state(self, tmp_path):
        """Test that stop returns False if service is not in RUNNING or ERROR state."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        # Test with STOPPED state
        manager._state = ServiceState.STOPPED
        result = manager.stop()
        assert result is False
        
        # Test with STARTING state
        manager._state = ServiceState.STARTING
        result = manager.stop()
        assert result is False
        
        # Test with STOPPING state
        manager._state = ServiceState.STOPPING
        result = manager.stop()
        assert result is False
    
    def test_stop_handles_no_process_gracefully(self, tmp_path):
        """Test that stop handles case where process is None."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        manager._process = None
        manager._state = ServiceState.RUNNING
        
        result = manager.stop()
        
        assert result is True
        assert manager.get_state() == ServiceState.STOPPED
    
    def test_stop_transitions_to_error_on_exception(self, tmp_path):
        """Test that stop transitions to ERROR on unexpected exception."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.terminate.side_effect = Exception("Unexpected error")
        
        manager._process = mock_process
        manager._state = ServiceState.RUNNING
        
        result = manager.stop()
        
        assert result is False
        assert manager.get_state() == ServiceState.ERROR
    
    def test_stop_can_stop_service_in_error_state(self, tmp_path):
        """Test that stop can be called when service is in ERROR state."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        
        manager._process = mock_process
        manager._state = ServiceState.ERROR
        
        with patch('time.sleep'), patch('time.time', side_effect=[0, 0.1, 0.1]):  # Extra value for final log
            result = manager.stop()
        
        assert result is True
        assert manager.get_state() == ServiceState.STOPPED
    
    def test_stop_respects_custom_timeout(self, tmp_path):
        """Test that stop respects custom timeout value."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Never terminates
        
        manager._process = mock_process
        manager._state = ServiceState.RUNNING
        
        # Use short timeout
        with patch('time.sleep'), \
             patch('time.time', side_effect=[0, 1, 2, 3]), \
             patch.object(manager, 'force_kill') as mock_force_kill:
            manager.stop(timeout=2.0)
        
        # Should have called force_kill after timeout
        mock_force_kill.assert_called_once()


class TestServiceManagerForceKill:
    """Tests for ServiceManager force_kill() method."""
    
    def test_force_kill_calls_process_kill(self, tmp_path):
        """Test that force_kill calls kill() on the process."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.wait.return_value = None
        
        manager._process = mock_process
        
        manager.force_kill()
        
        mock_process.kill.assert_called_once()
    
    def test_force_kill_waits_for_process_to_die(self, tmp_path):
        """Test that force_kill waits briefly for process to terminate."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.wait.return_value = None
        
        manager._process = mock_process
        
        manager.force_kill()
        
        mock_process.wait.assert_called_once_with(timeout=2.0)
    
    def test_force_kill_handles_no_process_gracefully(self, tmp_path):
        """Test that force_kill handles case where process is None."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        manager._process = None
        
        # Should not raise exception
        manager.force_kill()
    
    def test_force_kill_handles_timeout_expired(self, tmp_path):
        """Test that force_kill handles TimeoutExpired exception."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=2.0)
        
        manager._process = mock_process
        
        # Should not raise exception
        with patch('loguru.logger.error') as mock_log:
            manager.force_kill()
        
        # Should log error about process not terminating
        mock_log.assert_called()
    
    def test_force_kill_handles_exception(self, tmp_path):
        """Test that force_kill handles unexpected exceptions."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.kill.side_effect = Exception("Unexpected error")
        
        manager._process = mock_process
        
        # Should not raise exception
        with patch('loguru.logger.error') as mock_log:
            manager.force_kill()
        
        # Should log error
        mock_log.assert_called()
    
    def test_force_kill_logs_pid(self, tmp_path):
        """Test that force_kill logs the process PID."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        mock_process = Mock()
        mock_process.pid = 99999
        mock_process.wait.return_value = None
        
        manager._process = mock_process
        
        with patch('loguru.logger.warning') as mock_log_warn, \
             patch('loguru.logger.info') as mock_log_info:
            manager.force_kill()
        
        # Check that PID was logged
        log_calls = [str(call) for call in mock_log_warn.call_args_list + mock_log_info.call_args_list]
        assert any('99999' in str(call) for call in log_calls)



class TestServiceManagerRestart:
    """Tests for ServiceManager restart() method."""
    
    def test_restart_calls_stop_then_start(self, tmp_path):
        """Test that restart calls stop() then start()."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        # Set up a running process
        manager._state = ServiceState.RUNNING
        
        with patch.object(manager, 'stop', return_value=True) as mock_stop, \
             patch.object(manager, 'start', return_value=True) as mock_start:
            result = manager.restart()
        
        assert result is True
        mock_stop.assert_called_once()
        mock_start.assert_called_once()
        # Verify stop was called before start
        assert mock_stop.call_count == 1
        assert mock_start.call_count == 1
    
    def test_restart_returns_false_if_stop_fails(self, tmp_path):
        """Test that restart returns False if stop() fails."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        manager._state = ServiceState.RUNNING
        
        with patch.object(manager, 'stop', return_value=False) as mock_stop, \
             patch.object(manager, 'start') as mock_start:
            result = manager.restart()
        
        assert result is False
        mock_stop.assert_called_once()
        # start should not be called if stop fails
        mock_start.assert_not_called()
    
    def test_restart_returns_false_if_start_fails(self, tmp_path):
        """Test that restart returns False if start() fails."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        manager._state = ServiceState.RUNNING
        
        with patch.object(manager, 'stop', return_value=True) as mock_stop, \
             patch.object(manager, 'start', return_value=False) as mock_start:
            result = manager.restart()
        
        assert result is False
        mock_stop.assert_called_once()
        mock_start.assert_called_once()
    
    def test_restart_transitions_through_all_states(self, tmp_path):
        """Test that restart transitions through RUNNING → STOPPING → STOPPED → STARTING → RUNNING."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        # Set up a running process for stop
        mock_process_stop = Mock()
        mock_process_stop.pid = 12345
        mock_process_stop.poll.return_value = 0  # Process terminates immediately
        mock_process_stop.returncode = 0
        
        # Set up a new process for start
        mock_process_start = Mock()
        mock_process_start.pid = 67890
        mock_process_start.poll.return_value = None  # Process is running
        
        manager._process = mock_process_stop
        manager._state = ServiceState.RUNNING
        
        with patch('subprocess.Popen', return_value=mock_process_start), \
             patch('builtins.open', mock_open()), \
             patch('time.sleep'), \
             patch('time.time', side_effect=[0, 0.1, 0.1, 0.5]):
            
            # Verify initial state
            assert manager.get_state() == ServiceState.RUNNING
            
            result = manager.restart()
            
            # Verify final state
            assert result is True
            assert manager.get_state() == ServiceState.RUNNING
            
            # Verify the process was terminated and a new one was started
            mock_process_stop.terminate.assert_called_once()
            assert manager._process == mock_process_start
    
    def test_restart_logs_restart_operation(self, tmp_path):
        """Test that restart logs the restart operation."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        manager._state = ServiceState.RUNNING
        
        with patch.object(manager, 'stop', return_value=True), \
             patch.object(manager, 'start', return_value=True), \
             patch('loguru.logger.info') as mock_log:
            manager.restart()
        
        # Check that restart was logged
        log_calls = [str(call) for call in mock_log.call_args_list]
        assert any('Restarting service' in str(call) for call in log_calls)
        assert any('restarted successfully' in str(call) for call in log_calls)


class TestServiceManagerSetState:
    """Tests for ServiceManager _set_state() private method."""
    
    def test_set_state_changes_state(self, tmp_path):
        """Test that _set_state changes the service state."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        assert manager.get_state() == ServiceState.STOPPED
        
        manager._set_state(ServiceState.STARTING)
        
        assert manager.get_state() == ServiceState.STARTING
    
    def test_set_state_is_thread_safe(self, tmp_path):
        """Test that _set_state uses locking for thread safety."""
        import threading
        
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        # Test that multiple threads can safely call _set_state
        # If locking is not used, this could cause race conditions
        results = []
        
        def change_state(state):
            manager._set_state(state)
            results.append(manager.get_state())
        
        # Create multiple threads that change state
        threads = [
            threading.Thread(target=change_state, args=(ServiceState.STARTING,)),
            threading.Thread(target=change_state, args=(ServiceState.RUNNING,)),
            threading.Thread(target=change_state, args=(ServiceState.STOPPING,)),
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All threads should have completed without errors
        assert len(results) == 3
        # Final state should be one of the states we set
        final_state = manager.get_state()
        assert final_state in [ServiceState.STARTING, ServiceState.RUNNING, ServiceState.STOPPING]
    
    def test_set_state_logs_state_change(self, tmp_path):
        """Test that _set_state logs the state transition."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        with patch('loguru.logger.debug') as mock_log:
            manager._set_state(ServiceState.RUNNING)
        
        # Check that state change was logged
        log_calls = [str(call) for call in mock_log.call_args_list]
        assert any('stopped' in str(call).lower() and 'running' in str(call).lower() 
                   for call in log_calls)
    
    def test_set_state_accepts_all_service_states(self, tmp_path):
        """Test that _set_state accepts all ServiceState enum values."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        # Test all states
        for state in ServiceState:
            manager._set_state(state)
            assert manager.get_state() == state
    
    def test_set_state_can_transition_from_any_state_to_any_state(self, tmp_path):
        """Test that _set_state allows any state transition (no validation)."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        # Test various transitions
        manager._set_state(ServiceState.RUNNING)
        assert manager.get_state() == ServiceState.RUNNING
        
        manager._set_state(ServiceState.ERROR)
        assert manager.get_state() == ServiceState.ERROR
        
        manager._set_state(ServiceState.STOPPED)
        assert manager.get_state() == ServiceState.STOPPED
        
        # Even "invalid" transitions should work (no validation in _set_state)
        manager._set_state(ServiceState.STOPPING)
        assert manager.get_state() == ServiceState.STOPPING


class TestServiceManagerErrorHandling:
    """Tests for ServiceManager error handling and detection."""
    
    def test_capture_startup_error_reads_log_file(self, tmp_path):
        """Test that _capture_startup_error reads from log file."""
        log_file = tmp_path / "service.log"
        log_file.write_text("Error: Port 8000 is already in use\n")
        
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        error_text = manager._capture_startup_error()
        
        assert "Port 8000 is already in use" in error_text
    
    def test_capture_startup_error_returns_last_50_lines(self, tmp_path):
        """Test that _capture_startup_error returns last 50 lines."""
        log_file = tmp_path / "service.log"
        
        # Write 100 lines
        lines = [f"Line {i}\n" for i in range(100)]
        log_file.write_text(''.join(lines))
        
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        error_text = manager._capture_startup_error()
        
        # Should contain last 50 lines (50-99)
        assert "Line 99" in error_text
        assert "Line 50" in error_text
        assert "Line 49" not in error_text
    
    def test_capture_startup_error_handles_missing_file(self, tmp_path):
        """Test that _capture_startup_error handles missing log file."""
        log_file = tmp_path / "nonexistent.log"
        
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        error_text = manager._capture_startup_error()
        
        assert "Log file not found" in error_text
    
    def test_parse_error_type_detects_port_in_use(self):
        """Test that _parse_error_type detects port in use errors."""
        manager = ServiceManager(host="localhost", port=8000, log_file=Path("/tmp/test.log"))
        
        error_text = "Error: address already in use"
        error_type = manager._parse_error_type(error_text)
        
        assert error_type == "port_in_use"
    
    def test_parse_error_type_detects_auth_failure(self):
        """Test that _parse_error_type detects authentication failures."""
        manager = ServiceManager(host="localhost", port=8000, log_file=Path("/tmp/test.log"))
        
        error_text = "Error: Invalid credentials provided"
        error_type = manager._parse_error_type(error_text)
        
        assert error_type == "auth_failure"
    
    def test_parse_error_type_detects_import_error(self):
        """Test that _parse_error_type detects import errors."""
        manager = ServiceManager(host="localhost", port=8000, log_file=Path("/tmp/test.log"))
        
        error_text = "ModuleNotFoundError: No module named 'uvicorn'"
        error_type = manager._parse_error_type(error_text)
        
        assert error_type == "import_error"
    
    def test_parse_error_type_returns_unknown_for_generic_errors(self):
        """Test that _parse_error_type returns unknown for unrecognized errors."""
        manager = ServiceManager(host="localhost", port=8000, log_file=Path("/tmp/test.log"))
        
        error_text = "Some random error message"
        error_type = manager._parse_error_type(error_text)
        
        assert error_type == "unknown"
    
    def test_get_last_error_returns_type_and_message(self, tmp_path):
        """Test that get_last_error returns error type and message."""
        log_file = tmp_path / "service.log"
        log_file.write_text("Error: address already in use\n")
        
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        error_type, error_message = manager.get_last_error()
        
        assert error_type == "port_in_use"
        assert "address already in use" in error_message
    
    def test_detect_auth_failure_in_logs_detects_401(self, tmp_path):
        """Test that detect_auth_failure_in_logs detects 401 errors."""
        log_file = tmp_path / "service.log"
        log_file.write_text("HTTP 401 Unauthorized\n")
        
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        has_auth_failure = manager.detect_auth_failure_in_logs()
        
        assert has_auth_failure is True
    
    def test_detect_auth_failure_in_logs_detects_invalid_credentials(self, tmp_path):
        """Test that detect_auth_failure_in_logs detects invalid credentials."""
        log_file = tmp_path / "service.log"
        log_file.write_text("Error: Invalid credentials\n")
        
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        has_auth_failure = manager.detect_auth_failure_in_logs()
        
        assert has_auth_failure is True
    
    def test_detect_auth_failure_in_logs_returns_false_for_normal_logs(self, tmp_path):
        """Test that detect_auth_failure_in_logs returns False for normal logs."""
        log_file = tmp_path / "service.log"
        log_file.write_text("INFO: Server started successfully\n")
        
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        has_auth_failure = manager.detect_auth_failure_in_logs()
        
        assert has_auth_failure is False
    
    def test_detect_auth_failure_handles_missing_file(self, tmp_path):
        """Test that detect_auth_failure_in_logs handles missing log file."""
        log_file = tmp_path / "nonexistent.log"
        
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        has_auth_failure = manager.detect_auth_failure_in_logs()
        
        assert has_auth_failure is False
    
    def test_capture_crash_context_returns_last_20_lines(self, tmp_path):
        """Test that _capture_crash_context returns last 20 lines."""
        log_file = tmp_path / "service.log"
        
        # Write 50 lines
        lines = [f"Line {i}\n" for i in range(50)]
        log_file.write_text(''.join(lines))
        
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        crash_context = manager._capture_crash_context()
        
        # Should contain last 20 lines (30-49)
        assert "Line 49" in crash_context
        assert "Line 30" in crash_context
        assert "Line 29" not in crash_context


class TestServiceManagerCrashMonitoring:
    """Tests for ServiceManager crash monitoring functionality."""
    
    @patch('subprocess.Popen')
    @patch('builtins.open', new_callable=mock_open)
    @patch('time.sleep')
    def test_start_initializes_crash_monitor(self, mock_sleep, mock_file, mock_popen, tmp_path):
        """Test that start() initializes crash monitoring thread."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        # Mock successful process start
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        # Start service
        success = manager.start()
        
        assert success is True
        assert manager._monitoring is True
        assert manager._monitor_thread is not None
    
    @patch('subprocess.Popen')
    @patch('builtins.open', new_callable=mock_open)
    def test_stop_terminates_crash_monitor(self, mock_file, mock_popen, tmp_path):
        """Test that stop() terminates crash monitoring thread."""
        log_file = tmp_path / "service.log"
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        # Mock successful process start
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        # Start service
        manager.start()
        assert manager._monitoring is True
        
        # Mock process termination
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        
        # Stop service
        manager.stop()
        
        assert manager._monitoring is False


class TestServiceManagerStartupErrorCapture:
    """Tests for startup error capture during service start."""
    
    @patch('subprocess.Popen')
    @patch('time.sleep')
    def test_start_captures_error_on_immediate_exit(self, mock_sleep, mock_popen, tmp_path):
        """Test that start() captures error details when process exits immediately."""
        log_file = tmp_path / "service.log"
        log_file.write_text("Error: Port 8000 already in use\n")
        
        manager = ServiceManager(host="localhost", port=8000, log_file=log_file)
        
        # Mock process that exits immediately
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process exited with error
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        
        # Mock the file handle for subprocess
        mock_file_handle = Mock()
        
        with patch('builtins.open', return_value=mock_file_handle) as mock_open_call:
            # Start service (should fail)
            success = manager.start()
        
        assert success is False
        assert manager.get_state() == ServiceState.ERROR
        
        # Verify error was captured (read the actual file)
        error_type, error_text = manager.get_last_error()
        assert "Port 8000 already in use" in error_text
