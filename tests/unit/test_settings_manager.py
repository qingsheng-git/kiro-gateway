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


# =============================================================================
# Model Aliases Extension Tests (Task 1.4)
# Validates: Requirements 6.1, 6.5
# =============================================================================


class TestTraySettingsModelAliases:
    """Tests for TraySettings model_aliases field serialization/deserialization."""

    def test_default_model_aliases_is_empty_dict(self):
        """
        Test that TraySettings defaults model_aliases to an empty dict.

        What it does: Creates TraySettings with no arguments and checks model_aliases.
        Purpose: Ensure backward-compatible default for the new field.
        """
        settings = TraySettings()

        assert settings.model_aliases == {}
        assert isinstance(settings.model_aliases, dict)

    def test_to_dict_includes_model_aliases(self):
        """
        Test that to_dict() includes model_aliases in the output.

        What it does: Creates TraySettings with aliases and serializes via to_dict().
        Purpose: Ensure model_aliases is persisted during serialization.
        """
        aliases = {"my-opus": "claude-opus-4.5", "fast": "claude-haiku-4.5"}
        settings = TraySettings(model_aliases=aliases)

        result = settings.to_dict()

        assert "model_aliases" in result
        assert result["model_aliases"] == aliases

    def test_to_dict_with_empty_aliases(self):
        """
        Test that to_dict() correctly serializes empty model_aliases.

        What it does: Creates TraySettings with default (empty) aliases and serializes.
        Purpose: Ensure empty dict is preserved, not omitted.
        """
        settings = TraySettings()

        result = settings.to_dict()

        assert "model_aliases" in result
        assert result["model_aliases"] == {}

    def test_from_dict_with_model_aliases(self):
        """
        Test that from_dict() correctly restores model_aliases.

        What it does: Creates TraySettings from a dict containing model_aliases.
        Purpose: Ensure deserialization correctly populates the field.
        """
        data = {
            "auto_start": False,
            "server_host": "0.0.0.0",
            "server_port": 8000,
            "last_state": "stopped",
            "model_aliases": {"gpt4": "claude-opus-4.5", "fast": "claude-haiku-4.5"},
        }

        settings = TraySettings.from_dict(data)

        assert settings.model_aliases == {"gpt4": "claude-opus-4.5", "fast": "claude-haiku-4.5"}

    def test_from_dict_old_format_no_model_aliases(self):
        """
        Test backward compatibility: from_dict() with old format (no model_aliases key).

        What it does: Creates TraySettings from a dict that lacks model_aliases.
        Purpose: Ensure old settings files without model_aliases load correctly.
        """
        old_format_data = {
            "auto_start": True,
            "server_host": "127.0.0.1",
            "server_port": 9000,
            "last_state": "running",
        }

        settings = TraySettings.from_dict(old_format_data)

        assert settings.model_aliases == {}
        assert settings.auto_start is True
        assert settings.server_host == "127.0.0.1"

    def test_to_dict_from_dict_roundtrip_with_aliases(self):
        """
        Test that to_dict/from_dict round-trip preserves model_aliases.

        What it does: Serializes and deserializes TraySettings with aliases.
        Purpose: Ensure no data loss during the conversion cycle.
        """
        original = TraySettings(
            auto_start=True,
            server_host="localhost",
            server_port=3000,
            last_state="running",
            model_aliases={"alias-a": "model-a", "alias-b": "model-b"},
        )

        restored = TraySettings.from_dict(original.to_dict())

        assert restored.model_aliases == original.model_aliases
        assert restored.auto_start == original.auto_start
        assert restored.server_host == original.server_host
        assert restored.server_port == original.server_port
        assert restored.last_state == original.last_state


class TestSettingsManagerModelAliasesPersistence:
    """Tests for SettingsManager save/load with model_aliases."""

    def test_save_and_load_with_model_aliases(self, tmp_path):
        """
        Test that SettingsManager correctly persists and loads model_aliases.

        What it does: Saves settings with aliases to a temp file, loads them back.
        Purpose: Ensure the full file I/O cycle preserves alias data.
        """
        settings_file = tmp_path / "settings.json"
        manager = SettingsManager(settings_file=settings_file)
        aliases = {"my-model": "claude-sonnet-4", "quick": "claude-haiku-4.5"}

        original = TraySettings(model_aliases=aliases)
        manager.save(original)
        loaded = manager.load()

        assert loaded.model_aliases == aliases

    def test_save_and_load_with_empty_aliases(self, tmp_path):
        """
        Test that SettingsManager handles empty model_aliases correctly.

        What it does: Saves settings with empty aliases, loads them back.
        Purpose: Ensure empty dict survives the persistence cycle.
        """
        settings_file = tmp_path / "settings.json"
        manager = SettingsManager(settings_file=settings_file)

        original = TraySettings(model_aliases={})
        manager.save(original)
        loaded = manager.load()

        assert loaded.model_aliases == {}

    def test_load_old_format_file_without_model_aliases(self, tmp_path):
        """
        Test loading a settings file written in old format (no model_aliases key).

        What it does: Writes a JSON file without model_aliases, loads via SettingsManager.
        Purpose: Ensure backward compatibility with pre-alias settings files.
        """
        settings_file = tmp_path / "settings.json"
        # Simulate an old-format file written before model_aliases existed
        import json
        old_data = {
            "auto_start": True,
            "server_host": "192.168.1.1",
            "server_port": 7000,
            "last_state": "stopped",
        }
        settings_file.write_text(json.dumps(old_data), encoding="utf-8")

        manager = SettingsManager(settings_file=settings_file)
        loaded = manager.load()

        assert loaded.model_aliases == {}
        assert loaded.auto_start is True
        assert loaded.server_host == "192.168.1.1"
        assert loaded.server_port == 7000

    def test_corrupted_file_recovery_preserves_model_aliases_default(self, tmp_path):
        """
        Test that corrupted file recovery returns default TraySettings with empty model_aliases.

        What it does: Writes corrupted JSON, loads via SettingsManager.
        Purpose: Ensure recovery from corruption still includes model_aliases field.
        """
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{{{{not valid json at all!!!!", encoding="utf-8")

        manager = SettingsManager(settings_file=settings_file)
        loaded = manager.load()

        # Should recover with defaults, including empty model_aliases
        assert loaded.model_aliases == {}
        assert loaded.auto_start is False
        assert loaded.server_host == "0.0.0.0"
        assert loaded.server_port == 8000

        # Backup should have been created
        backup_file = tmp_path / "settings.json.bak"
        assert backup_file.exists()

    def test_corrupted_file_recovery_then_save_with_aliases(self, tmp_path):
        """
        Test that after recovering from corruption, aliases can be saved and loaded.

        What it does: Recovers from corrupted file, saves new settings with aliases, loads again.
        Purpose: Ensure the recovery path doesn't break subsequent alias persistence.
        """
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("not json", encoding="utf-8")

        manager = SettingsManager(settings_file=settings_file)
        # First load triggers recovery
        recovered = manager.load()
        assert recovered.model_aliases == {}

        # Now save with aliases
        new_settings = TraySettings(model_aliases={"test-alias": "test-model"})
        manager.save(new_settings)

        # Load again and verify aliases persisted
        reloaded = manager.load()
        assert reloaded.model_aliases == {"test-alias": "test-model"}
