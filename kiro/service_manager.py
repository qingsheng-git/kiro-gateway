"""
Service Manager for Kiro Gateway subprocess lifecycle.

This module manages the uvicorn subprocess that runs the FastAPI application,
including start/stop/restart operations, state tracking, and graceful shutdown.
"""

from enum import Enum
from pathlib import Path
from typing import Optional
import threading
import subprocess
import sys
import time
from loguru import logger


class ServiceState(Enum):
    """Service operational states."""
    STOPPED = "stopped"      # Service not running
    STARTING = "starting"    # Service starting up
    RUNNING = "running"      # Service operational
    STOPPING = "stopping"    # Service shutting down
    ERROR = "error"          # Service failed or unhealthy


class ServiceManager:
    """
    Manages the uvicorn subprocess lifecycle.
    
    Handles starting, stopping, and restarting the uvicorn server process,
    tracks service state, and implements graceful and forced shutdown.
    """
    
    def __init__(self, host: str, port: int, log_file: Path):
        """
        Initialize service manager with server configuration.
        
        Args:
            host: Server host address
            port: Server port number
            log_file: Path to log file for subprocess output
        """
        self.host = host
        self.port = port
        self.log_file = log_file
        self._state = ServiceState.STOPPED
        self._lock = threading.Lock()
        self._process: Optional[object] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False
        logger.info(f"ServiceManager initialized for {host}:{port}")
    
    def start(self) -> bool:
        """
        Start the uvicorn subprocess.
        
        Creates a subprocess running uvicorn with the FastAPI application.
        On Windows, uses CREATE_NO_WINDOW flag to hide the console window.
        Captures stdout/stderr to the configured log file.
        
        State transitions:
        - STOPPED → STARTING → RUNNING (on success)
        - STOPPED → STARTING → ERROR (on failure)
        
        Returns:
            True on success, False on failure
        """
        with self._lock:
            if self._state != ServiceState.STOPPED:
                logger.warning(f"Cannot start service in state {self._state.value}")
                return False
            
            self._state = ServiceState.STARTING
            logger.info("Service state: STOPPED → STARTING")
        
        try:
            # Ensure log file directory exists
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Build command based on environment
            is_frozen = getattr(sys, 'frozen', False)
            
            if is_frozen:
                # Packaged executable: run KiroGateway.exe --no-tray
                command = [
                    sys.executable,
                    "--no-tray",
                    "--host",
                    self.host,
                    "--port",
                    str(self.port)
                ]
            else:
                # Development mode: python -m uvicorn main:app
                command = [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "main:app",
                    "--host",
                    self.host,
                    "--port",
                    str(self.port)
                ]
            
            logger.info(f"Starting subprocess: {' '.join(command)}")
            
            # Open log file for subprocess output
            log_handle = open(self.log_file, 'a', encoding='utf-8')
            
            # Configure subprocess creation based on platform
            kwargs = {
                'stdout': log_handle,
                'stderr': subprocess.STDOUT,  # Merge stderr into stdout
                'stdin': subprocess.DEVNULL,
            }
            
            # Windows-specific: hide console window
            if sys.platform == "win32":
                CREATE_NO_WINDOW = 0x08000000
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                kwargs['creationflags'] = CREATE_NO_WINDOW
                kwargs['startupinfo'] = startupinfo
                logger.debug("Using CREATE_NO_WINDOW flag for Windows")
            
            # Start the subprocess
            self._process = subprocess.Popen(command, **kwargs)
            
            # Give the process a moment to start and check if it's still running
            time.sleep(0.5)
            
            if self._process.poll() is not None:
                # Process exited immediately - startup failed
                exit_code = self._process.returncode
                logger.error(f"Service process exited immediately with code {exit_code}")
                
                # Capture stderr/error details from log file
                error_details = self._capture_startup_error()
                logger.error(f"Startup error details: {error_details}")
                
                with self._lock:
                    self._state = ServiceState.ERROR
                    logger.info("Service state: STARTING → ERROR")
                
                # Close log file handle
                log_handle.close()
                return False
            
            # Process is running
            with self._lock:
                self._state = ServiceState.RUNNING
                logger.info("Service state: STARTING → RUNNING")
            
            # Start monitoring thread for crash detection
            self._start_crash_monitor()
            
            logger.info(f"Service started successfully (PID: {self._process.pid})")
            return True
            
        except FileNotFoundError as e:
            logger.error(f"Failed to start service: uvicorn not found. {e}")
            with self._lock:
                self._state = ServiceState.ERROR
                logger.info("Service state: STARTING → ERROR")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            with self._lock:
                self._state = ServiceState.ERROR
                logger.info("Service state: STARTING → ERROR")
            return False
    
    def stop(self, timeout: float = 10.0) -> bool:
        """
        Stop the subprocess gracefully.

        Sends SIGTERM to the subprocess and waits up to timeout seconds
        for graceful shutdown. If the process doesn't terminate within
        the timeout, force_kill() is called.

        State transitions:
        - RUNNING → STOPPING → STOPPED (on success)
        - RUNNING → STOPPING → ERROR (on timeout/failure)

        Args:
            timeout: Maximum time to wait for graceful shutdown (seconds)

        Returns:
            True on success, False on failure
        """
        # Stop crash monitoring first
        self._stop_crash_monitor()
        
        with self._lock:
            if self._state not in (ServiceState.RUNNING, ServiceState.ERROR):
                logger.warning(f"Cannot stop service in state {self._state.value}")
                return False

            if self._process is None:
                logger.warning("No process to stop")
                self._state = ServiceState.STOPPED
                return True

            self._state = ServiceState.STOPPING
            logger.info("Service state: RUNNING → STOPPING")

        try:
            logger.info(f"Stopping service (PID: {self._process.pid}) with timeout={timeout}s")

            # Send termination signal
            self._process.terminate()
            logger.debug("Sent SIGTERM to subprocess")

            # Wait for graceful shutdown
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self._process.poll() is not None:
                    # Process has terminated
                    exit_code = self._process.returncode
                    logger.info(f"Service stopped gracefully (exit code: {exit_code})")

                    with self._lock:
                        self._state = ServiceState.STOPPED
                        logger.info("Service state: STOPPING → STOPPED")

                    # Log shutdown event
                    logger.info(f"Shutdown event: graceful termination after {time.time() - start_time:.2f}s")
                    return True

                # Check every 0.1 seconds
                time.sleep(0.1)

            # Timeout reached - force kill
            logger.warning(f"Graceful shutdown timeout ({timeout}s) exceeded, forcing termination")
            self.force_kill()

            # Log shutdown event
            logger.warning(f"Shutdown event: forced termination after timeout ({timeout}s)")

            with self._lock:
                self._state = ServiceState.STOPPED
                logger.info("Service state: STOPPING → STOPPED (forced)")

            return True

        except Exception as e:
            logger.error(f"Error during service stop: {e}")

            with self._lock:
                self._state = ServiceState.ERROR
                logger.info("Service state: STOPPING → ERROR")

            return False


    
    def restart(self) -> bool:
        """
        Restart the service (stop then start).
        
        Performs a complete restart cycle: stops the service gracefully,
        then starts it again. This is useful for applying configuration
        changes or recovering from errors.
        
        State transitions:
        - RUNNING → STOPPING → STOPPED → STARTING → RUNNING (on success)
        - RUNNING → STOPPING → STOPPED → STARTING → ERROR (on start failure)
        
        Returns:
            True on success, False on failure
        """
        logger.info("Restarting service")
        
        # Stop the service first
        if not self.stop():
            logger.error("Failed to stop service during restart")
            return False
        
        # Start the service
        if not self.start():
            logger.error("Failed to start service during restart")
            return False
        
        logger.info("Service restarted successfully")
        return True
    
    def get_state(self) -> ServiceState:
        """
        Get current service state.
        
        Thread-safe access to the current service state.
        
        Returns:
            Current ServiceState
        """
        with self._lock:
            return self._state
    
    def _set_state(self, state: ServiceState) -> None:
        """
        Set service state (private method).
        
        Thread-safe state mutation. This is a private method used internally
        by the ServiceManager. External callers should use public methods
        (start, stop, restart) which handle state transitions.
        
        Args:
            state: New ServiceState to set
        """
        with self._lock:
            old_state = self._state
            self._state = state
            logger.debug(f"Service state changed: {old_state.value} → {state.value}")
    
    def is_running(self) -> bool:
        """
        Check if subprocess is running.
        
        Returns:
            True if running, False otherwise
        """
        return self.get_state() == ServiceState.RUNNING
    
    def force_kill(self) -> None:
        """
        Force terminate the subprocess.
        
        Uses SIGKILL (kill -9) to immediately terminate the process.
        This method should only be called when graceful shutdown fails.
        Does not change service state - caller is responsible for state management.
        """
        if self._process is None:
            logger.warning("No process to force kill")
            return
        
        try:
            logger.warning(f"Force killing service process (PID: {self._process.pid})")
            self._process.kill()  # SIGKILL on Unix, TerminateProcess on Windows
            
            # Wait briefly for process to die
            try:
                self._process.wait(timeout=2.0)
                logger.info(f"Process {self._process.pid} force-killed successfully")
            except subprocess.TimeoutExpired:
                logger.error(f"Process {self._process.pid} did not terminate even after SIGKILL")
            
        except Exception as e:
            logger.error(f"Error during force kill: {e}")
    
    def _capture_startup_error(self) -> str:
        """
        Capture error details from log file after startup failure.
        
        Reads the last 50 lines of the log file to capture startup errors.
        
        Returns:
            Error details as string
        """
        try:
            if not self.log_file.exists():
                return "Log file not found"
            
            # Read last 50 lines from log file
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                last_lines = lines[-50:] if len(lines) > 50 else lines
                return ''.join(last_lines)
        
        except Exception as e:
            logger.error(f"Failed to capture startup error: {e}")
            return f"Failed to read log file: {e}"
    
    def _parse_error_type(self, error_text: str) -> str:
        """
        Parse error text to determine error type.
        
        Detects common error patterns:
        - Port already in use
        - Missing credentials / authentication errors
        - Import errors / missing dependencies
        
        Args:
            error_text: Error text from log file
        
        Returns:
            Error type string
        """
        error_lower = error_text.lower()
        
        # Check for port in use
        if "address already in use" in error_lower or "port" in error_lower and "use" in error_lower:
            return "port_in_use"
        
        # Check for authentication errors
        if any(keyword in error_lower for keyword in ["credential", "auth", "token", "permission denied"]):
            return "auth_failure"
        
        # Check for import errors
        if "importerror" in error_lower or "modulenotfounderror" in error_lower or "no module named" in error_lower:
            return "import_error"
        
        # Generic error
        return "unknown"
    
    def get_last_error(self) -> tuple[str, str]:
        """
        Get the last error details from the log file.
        
        Returns:
            Tuple of (error_type, error_message)
        """
        error_text = self._capture_startup_error()
        error_type = self._parse_error_type(error_text)
        return (error_type, error_text)
    
    def _start_crash_monitor(self) -> None:
        """Start background thread to monitor for service crashes."""
        if self._monitoring:
            logger.warning("Crash monitoring already running")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._crash_monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.debug("Crash monitoring started")
    
    def _stop_crash_monitor(self) -> None:
        """Stop crash monitoring thread."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        logger.debug("Crash monitoring stopped")
    
    def _crash_monitor_loop(self) -> None:
        """
        Background loop to monitor for unexpected process termination.
        
        Checks if the subprocess has exited unexpectedly (exit code != 0)
        and transitions to ERROR state if detected.
        """
        logger.debug("Crash monitor loop started")
        
        while self._monitoring:
            try:
                # Check if process is still running
                if self._process and self._process.poll() is not None:
                    exit_code = self._process.returncode
                    
                    # Check if this was an unexpected termination
                    current_state = self.get_state()
                    if current_state == ServiceState.RUNNING and exit_code != 0:
                        logger.error(f"Service crashed unexpectedly with exit code {exit_code}")
                        
                        # Capture last lines of log for context
                        error_context = self._capture_crash_context()
                        logger.error(f"Crash context: {error_context}")
                        
                        # Transition to ERROR state
                        with self._lock:
                            self._state = ServiceState.ERROR
                            logger.info("Service state: RUNNING → ERROR (crash detected)")
                        
                        # Stop monitoring
                        self._monitoring = False
                        break
                
                # Sleep briefly before next check
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in crash monitor loop: {e}")
                time.sleep(1.0)
        
        logger.debug("Crash monitor loop stopped")
    
    def _capture_crash_context(self) -> str:
        """
        Capture last N lines of log file for crash context.
        
        Returns:
            Last 20 lines of log file as string
        """
        try:
            if not self.log_file.exists():
                return "Log file not found"
            
            # Read last 20 lines from log file
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                last_lines = lines[-20:] if len(lines) > 20 else lines
                return ''.join(last_lines)
        
        except Exception as e:
            logger.error(f"Failed to capture crash context: {e}")
            return f"Failed to read log file: {e}"
    
    def detect_auth_failure_in_logs(self) -> bool:
        """
        Detect authentication failures in service logs.
        
        Scans the log file for authentication error patterns.
        
        Returns:
            True if authentication failure detected, False otherwise
        """
        try:
            if not self.log_file.exists():
                return False
            
            # Read last 100 lines from log file
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                last_lines = lines[-100:] if len(lines) > 100 else lines
                log_text = ''.join(last_lines).lower()
            
            # Check for authentication error patterns
            auth_patterns = [
                "authentication failed",
                "invalid credentials",
                "unauthorized",
                "401",
                "403 forbidden",
                "token expired",
                "refresh token",
                "invalid api key"
            ]
            
            return any(pattern in log_text for pattern in auth_patterns)
        
        except Exception as e:
            logger.error(f"Failed to detect auth failure: {e}")
            return False

