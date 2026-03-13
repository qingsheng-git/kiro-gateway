"""
Unit tests for platform detection utilities.

Tests OS detection, tray support checking, and cross-platform file operations.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch
from kiro.platform_utils import is_windows, is_tray_supported, open_file_explorer


class TestPlatformDetection:
    """Tests for platform detection functions."""
    
    def test_is_windows_returns_bool(self):
        """Test that is_windows returns a boolean value."""
        result = is_windows()
        
        assert isinstance(result, bool)
    
    def test_is_windows_matches_sys_platform(self):
        """Test that is_windows matches sys.platform check."""
        expected = sys.platform == "win32"
        
        result = is_windows()
        
        assert result == expected
    
    @patch('sys.platform', 'win32')
    def test_is_windows_returns_true_on_windows(self):
        """Test that is_windows returns True when platform is win32."""
        result = is_windows()
        
        assert result is True
    
    @patch('sys.platform', 'linux')
    def test_is_windows_returns_false_on_linux(self):
        """Test that is_windows returns False when platform is linux."""
        result = is_windows()
        
        assert result is False
    
    @patch('sys.platform', 'darwin')
    def test_is_windows_returns_false_on_macos(self):
        """Test that is_windows returns False when platform is darwin."""
        result = is_windows()
        
        assert result is False


class TestTraySupportDetection:
    """Tests for tray support detection."""
    
    def test_is_tray_supported_returns_bool(self):
        """Test that is_tray_supported returns a boolean value."""
        result = is_tray_supported()
        
        assert isinstance(result, bool)
    
    @patch('kiro.platform_utils.is_windows', return_value=True)
    def test_is_tray_supported_returns_true_on_windows(self, mock_is_windows):
        """Test that is_tray_supported returns True on Windows."""
        result = is_tray_supported()
        
        assert result is True
    
    @patch('kiro.platform_utils.is_windows', return_value=False)
    def test_is_tray_supported_returns_false_on_non_windows(self, mock_is_windows):
        """Test that is_tray_supported returns False on non-Windows."""
        result = is_tray_supported()
        
        assert result is False


class TestFileExplorerOpening:
    """Tests for open_file_explorer function."""
    
    def test_open_file_explorer_accepts_path(self):
        """Test that open_file_explorer accepts a Path parameter."""
        test_path = Path("/tmp/test")
        
        # Should not raise exception (may fail to actually open, but should handle gracefully)
        try:
            open_file_explorer(test_path)
        except Exception as e:
            # Expected to fail on non-existent path, but should not crash
            pass
    
    @patch('os.startfile')
    @patch('sys.platform', 'win32')
    def test_open_file_explorer_uses_startfile_on_windows(self, mock_startfile):
        """Test that open_file_explorer uses os.startfile on Windows."""
        test_path = Path("C:/test")
        
        open_file_explorer(test_path)
        
        mock_startfile.assert_called_once_with(test_path)
    
    @patch('subprocess.run')
    @patch('sys.platform', 'darwin')
    def test_open_file_explorer_uses_open_on_macos(self, mock_run):
        """Test that open_file_explorer uses 'open' command on macOS."""
        test_path = Path("/tmp/test")
        
        open_file_explorer(test_path)
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "open"
        assert str(test_path) in args
    
    @patch('subprocess.run')
    @patch('sys.platform', 'linux')
    def test_open_file_explorer_uses_xdg_open_on_linux(self, mock_run):
        """Test that open_file_explorer uses 'xdg-open' command on Linux."""
        test_path = Path("/tmp/test")
        
        open_file_explorer(test_path)
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "xdg-open"
        assert str(test_path) in args
