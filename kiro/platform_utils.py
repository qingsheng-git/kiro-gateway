"""
Platform detection and cross-platform utilities.

This module provides platform detection functions and cross-platform
implementations for file operations, ensuring graceful degradation on non-Windows.
"""

import sys
from pathlib import Path
from loguru import logger


def is_windows() -> bool:
    """
    Check if running on Windows.
    
    Returns:
        True if Windows, False otherwise
    """
    return sys.platform == "win32"


def is_tray_supported() -> bool:
    """
    Check if tray functionality is supported on this platform.
    
    Returns:
        True if supported, False otherwise
    """
    return is_windows()


def open_file_explorer(path: Path) -> None:
    """
    Open file explorer at given path (cross-platform).
    
    Args:
        path: Path to open in file explorer
    """
    import subprocess
    import os
    
    try:
        if sys.platform == "win32":
            # Windows: use os.startfile
            os.startfile(path)
        elif sys.platform == "darwin":
            # macOS: use open command
            subprocess.run(["open", str(path)], check=True)
        else:
            # Linux: use xdg-open
            subprocess.run(["xdg-open", str(path)], check=True)
        logger.info(f"Opened file explorer at: {path}")
    except Exception as e:
        logger.error(f"Failed to open file explorer: {e}")
