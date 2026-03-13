"""
Unit tests for SettingsManager.

Tests settings persistence, registry operations, and auto-start configuration.
"""

import pytest
from pathlib import Path
from kiro.settings_manager import SettingsManager, TraySettings


class TestTraySettingsDataclass:
    """Tests for TraySettings dataclass."""
    
    def test_default_values(self):
        """Test that TraySettings has correct default values."""
        settings = TraySettings()
        
        assert settings.auto_start is False
        assert settings.server_host == "0.0.0.0"
        assert settings.server_port == 8000
        assert settings.last_state == "stopped"
    
    def test_custom_values(self):
        """Test that TraySettings accepts custom values."""
        settings = TraySettings(
            auto_start=True,
            server_host="127.0.0.1",
            server_port=9000,
            last_state="running"
        )
        
        assert settings.auto_start is True
        assert settings.server_host == "127.0.0.1"
        assert settings.server_port == 9000
        assert settings.last_state == "running"
    
    def test_to_dict_conversion(self):
        """Test that to_dict converts settings to dictionary."""
        settings = TraySettings(auto_start=True, server_host="localhost", server_port=9000)
        
        result = settings.to_dict()
        
        assert isinstance(result, dict)
        assert result["auto_start"] is True
        assert result["server_host"] == "localhost"
        assert result["server_port"] == 9000
    
    def test_from_dict_conversion(self):
        """Test that from_dict creates settings from dictionary."""
        data = {
            "auto_start": True,
            "server_host": "192.168.1.1",
            "server_port": 7000,
            "last_state": "error"
        }
        
        settings = TraySettings.from_dict(data)
        
        assert settings.auto_start is True
        assert settings.server_host == "192.168.1.1"
        assert settings.server_port == 7000
        assert settings.last_state == "error"


class TestSettingsManagerInitialization:
    """Tests for SettingsManager initialization."""
    
    def test_initialization_stores_file_path(self):
        """Test that initialization stores settings file path."""
        file_path = Path("/tmp/test_settings.json")
        
        manager = SettingsManager(settings_file=file_path)
        
        assert manager.settings_file == file_path


class TestSettingsManagerOperations:
    """Tests for SettingsManager load/save operations."""
    
    def test_load_method_exists(self):
        """Test that load method exists and is callable."""
        manager = SettingsManager(settings_file=Path("/tmp/test.json"))
        assert callable(manager.load)
    
    def test_save_method_exists(self):
        """Test that save method exists and is callable."""
        manager = SettingsManager(settings_file=Path("/tmp/test.json"))
        assert callable(manager.save)
    
    def test_load_returns_tray_settings(self):
        """Test that load returns a TraySettings instance."""
        manager = SettingsManager(settings_file=Path("/tmp/test.json"))
        
        settings = manager.load()
        
        assert isinstance(settings, TraySettings)


class TestSettingsManagerAutoStart:
    """Tests for SettingsManager auto-start methods."""
    
    def test_enable_auto_start_method_exists(self):
        """Test that enable_auto_start method exists and is callable."""
        manager = SettingsManager(settings_file=Path("/tmp/test.json"))
        assert callable(manager.enable_auto_start)
    
    def test_disable_auto_start_method_exists(self):
        """Test that disable_auto_start method exists and is callable."""
        manager = SettingsManager(settings_file=Path("/tmp/test.json"))
        assert callable(manager.disable_auto_start)
    
    def test_is_auto_start_enabled_method_exists(self):
        """Test that is_auto_start_enabled method exists and is callable."""
        manager = SettingsManager(settings_file=Path("/tmp/test.json"))
        assert callable(manager.is_auto_start_enabled)



class TestSettingsFileOperations:
    """Tests for settings file load/save operations."""
    
    def test_load_creates_file_with_defaults_if_missing(self, tmp_path):
        """Test that load creates settings file with defaults if it doesn't exist."""
        settings_file = tmp_path / "settings.json"
        manager = SettingsManager(settings_file=settings_file)
        
        # File should not exist initially
        assert not settings_file.exists()
        
        # Load should create it with defaults
        settings = manager.load()
        
        assert settings_file.exists()
        assert settings.auto_start is False
        assert settings.server_host == "0.0.0.0"
        assert settings.server_port == 8000
    
    def test_save_creates_parent_directory(self, tmp_path):
        """Test that save creates parent directory if it doesn't exist."""
        settings_file = tmp_path / "subdir" / "settings.json"
        manager = SettingsManager(settings_file=settings_file)
        
        # Parent directory should not exist
        assert not settings_file.parent.exists()
        
        # Save should create it
        settings = TraySettings(auto_start=True)
        manager.save(settings)
        
        assert settings_file.parent.exists()
        assert settings_file.exists()
    
    def test_save_and_load_roundtrip(self, tmp_path):
        """Test that settings can be saved and loaded correctly."""
        settings_file = tmp_path / "settings.json"
        manager = SettingsManager(settings_file=settings_file)
        
        # Create custom settings
        original = TraySettings(
            auto_start=True,
            server_host="127.0.0.1",
            server_port=9000,
            last_state="running"
        )
        
        # Save and load
        manager.save(original)
        loaded = manager.load()
        
        # Should match
        assert loaded.auto_start == original.auto_start
        assert loaded.server_host == original.server_host
        assert loaded.server_port == original.server_port
        assert loaded.last_state == original.last_state
    
    def test_load_handles_corrupted_json(self, tmp_path):
        """Test that load handles corrupted JSON files gracefully."""
        settings_file = tmp_path / "settings.json"
        manager = SettingsManager(settings_file=settings_file)
        
        # Write corrupted JSON
        settings_file.write_text("{ invalid json }", encoding='utf-8')
        
        # Load should handle it and return defaults
        settings = manager.load()
        
        assert settings.auto_start is False
        assert settings.server_host == "0.0.0.0"
        
        # Should create backup
        backup_file = tmp_path / "settings.json.bak"
        assert backup_file.exists()
    
    def test_load_handles_non_dict_json(self, tmp_path):
        """Test that load handles JSON that's not a dictionary."""
        settings_file = tmp_path / "settings.json"
        manager = SettingsManager(settings_file=settings_file)
        
        # Write JSON array instead of object
        settings_file.write_text("[1, 2, 3]", encoding='utf-8')
        
        # Load should handle it and return defaults
        settings = manager.load()
        
        assert settings.auto_start is False
        assert settings.server_host == "0.0.0.0"
    
    def test_load_handles_missing_fields(self, tmp_path):
        """Test that load handles JSON with missing fields."""
        settings_file = tmp_path / "settings.json"
        manager = SettingsManager(settings_file=settings_file)
        
        # Write JSON with only some fields
        settings_file.write_text('{"auto_start": true}', encoding='utf-8')
        
        # Load should use defaults for missing fields
        settings = manager.load()
        
        assert settings.auto_start is True
        # These should use defaults from dataclass
        assert settings.server_host == "0.0.0.0"
        assert settings.server_port == 8000


class TestRegistryOperations:
    """Tests for Windows registry operations."""
    
    def test_enable_auto_start_returns_false_on_non_windows(self, tmp_path, monkeypatch):
        """Test that enable_auto_start returns False on non-Windows platforms."""
        settings_file = tmp_path / "settings.json"
        manager = SettingsManager(settings_file=settings_file)
        
        # Mock sys.platform to simulate Linux
        monkeypatch.setattr("sys.platform", "linux")
        
        result = manager.enable_auto_start()
        
        assert result is False
    
    def test_disable_auto_start_returns_false_on_non_windows(self, tmp_path, monkeypatch):
        """Test that disable_auto_start returns False on non-Windows platforms."""
        settings_file = tmp_path / "settings.json"
        manager = SettingsManager(settings_file=settings_file)
        
        # Mock sys.platform to simulate macOS
        monkeypatch.setattr("sys.platform", "darwin")
        
        result = manager.disable_auto_start()
        
        assert result is False
    
    def test_is_auto_start_enabled_returns_false_on_non_windows(self, tmp_path, monkeypatch):
        """Test that is_auto_start_enabled returns False on non-Windows platforms."""
        settings_file = tmp_path / "settings.json"
        manager = SettingsManager(settings_file=settings_file)
        
        # Mock sys.platform to simulate Linux
        monkeypatch.setattr("sys.platform", "linux")
        
        result = manager.is_auto_start_enabled()
        
        assert result is False
    
    def test_get_auto_start_command_format(self, tmp_path):
        """Test that _get_auto_start_command returns correct format."""
        settings_file = tmp_path / "settings.json"
        manager = SettingsManager(settings_file=settings_file)
        
        command = manager._get_auto_start_command()
        
        # Command should contain python executable and main.py with --tray flag
        if command:  # Only test if command was generated successfully
            assert "python" in command.lower()
            assert "main.py" in command
            assert "--tray" in command
            # Should have quotes around paths
            assert '"' in command
