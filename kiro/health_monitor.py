"""
Health Monitor for Kiro Gateway service.

This module monitors the service health via HTTP endpoint checks,
detects failures, and triggers notifications on health status changes.
"""

from typing import Callable, Optional
import threading
import time
import httpx
from loguru import logger


class HealthMonitor:
    """
    Monitors service health via HTTP endpoint.
    
    Periodically checks the /health endpoint, detects service failures,
    and triggers callbacks on health status changes.
    """
    
    def __init__(self, host: str, port: int, check_interval: float = 30.0):
        """
        Initialize health monitor with server configuration.
        
        Args:
            host: Server host address
            port: Server port number
            check_interval: Time between health checks in seconds (default: 30.0)
        """
        self.host = host
        self.port = port
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable[[bool], None]] = []
        self._last_health_status: Optional[bool] = None
        self._consecutive_failures = 0
        self._max_failures = 3
        logger.info(f"HealthMonitor initialized for {host}:{port} with interval={check_interval}s")
    
    def start(self) -> None:
        """Start health monitoring in background thread."""
        if self._running:
            logger.warning("Health monitoring is already running")
            return
        
        logger.info("Starting health monitoring")
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """Stop health monitoring."""
        if not self._running:
            logger.warning("Health monitoring is not running")
            return
        
        logger.info("Stopping health monitoring")
        self._running = False
        
        # Wait for thread to finish (with timeout)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("Health monitoring thread did not stop gracefully")
    
    def check_health(self) -> bool:
        """
        Perform single health check.
        
        Makes an HTTP GET request to /health endpoint and checks for 200 response.
        Handles connection errors, timeouts, and non-200 responses.
        
        Returns:
            True if healthy (200 response), False otherwise
        """
        url = f"http://{self.host}:{self.port}/health"
        
        try:
            # Use a short timeout for health checks
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                
                if response.status_code == 200:
                    logger.debug(f"Health check passed: {url}")
                    return True
                else:
                    logger.warning(f"Health check failed with status {response.status_code}: {url}")
                    return False
                    
        except httpx.ConnectError as e:
            logger.warning(f"Health check connection error: {e}")
            return False
        except httpx.TimeoutException as e:
            logger.warning(f"Health check timeout: {e}")
            return False
        except Exception as e:
            logger.error(f"Health check unexpected error: {e}")
            return False
    
    def on_health_change(self, callback: Callable[[bool], None]) -> None:
        """
        Register callback for health status changes.
        
        Args:
            callback: Function to call when health status changes (receives bool: is_healthy)
        """
        self._callbacks.append(callback)
        logger.debug(f"Registered health change callback: {callback.__name__}")
    
    def _monitor_loop(self) -> None:
        """
        Background monitoring loop.
        
        Runs in a separate thread, performing periodic health checks
        and invoking callbacks when health status changes.
        """
        logger.info("Health monitoring loop started")
        
        while self._running:
            try:
                # Perform health check
                is_healthy = self.check_health()
                
                # Track consecutive failures
                if is_healthy:
                    self._consecutive_failures = 0
                else:
                    self._consecutive_failures += 1
                
                # Determine overall health status (allow up to 3 failures)
                current_status = self._consecutive_failures < self._max_failures
                
                # Check if status changed
                if self._last_health_status is not None and current_status != self._last_health_status:
                    logger.info(f"Health status changed: {self._last_health_status} -> {current_status}")
                    self._invoke_callbacks(current_status)
                
                # Update last status
                self._last_health_status = current_status
                
                # Wait for next check interval (with early exit support)
                for _ in range(int(self.check_interval * 10)):
                    if not self._running:
                        break
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(1.0)  # Brief pause before retry
        
        logger.info("Health monitoring loop stopped")
    
    def _invoke_callbacks(self, is_healthy: bool) -> None:
        """
        Invoke all registered callbacks with health status.
        
        Args:
            is_healthy: Current health status
        """
        for callback in self._callbacks:
            try:
                callback(is_healthy)
            except Exception as e:
                logger.error(f"Error invoking health callback {callback.__name__}: {e}")
