"""
Settings Manager for Kiro Gateway tray application.

This module manages persistent configuration including auto-start preferences,
server settings, and Windows registry integration for startup.
"""

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, Optional
import json
import sys
import shutil
from loguru import logger


@dataclass
class TraySettings:
    """Persistent tray application settings."""
    auto_start: bool = False
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    last_state: str = "stopped"
    model_aliases: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of settings including model_aliases
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TraySettings':
        """
        Create from dictionary (JSON deserialization).
        
        Backward-compatible: if model_aliases is missing from the data
        (old format), defaults to an empty dictionary.
        
        Args:
            data: Dictionary containing settings data
        
        Returns:
            TraySettings instance
        """
        # Ensure model_aliases exists for backward compatibility with old format
        if 'model_aliases' not in data:
            data = {**data, 'model_aliases': {}}
        return cls(**data)


class SettingsManager:
    """
    Manages persistent configuration for tray application.
    
    Handles loading/saving settings from JSON file, managing auto-start
    registry entries, and providing default values for missing settings.
    """
    
    def __init__(self, settings_file: Path):
        """
        Initialize settings manager with file path.
        
        Args:
            settings_file: Path to settings JSON file
        """
        self.settings_file = settings_file
        logger.info(f"SettingsManager initialized with file: {settings_file}")
    
    def load(self) -> TraySettings:
        """
        Load settings from file, create with defaults if missing.
        
        If the file doesn't exist, creates it with default values.
        If the file is corrupted, backs it up and creates a new one with defaults.
        
        Returns:
            TraySettings instance
        """
        logger.info(f"Loading settings from {self.settings_file}")
        
        # If file doesn't exist, create with defaults
        if not self.settings_file.exists():
            logger.info("Settings file not found, creating with defaults")
            settings = TraySettings()
            self.save(settings)
            return settings
        
        # Try to load existing file
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate that we have a dictionary
            if not isinstance(data, dict):
                raise ValueError("Settings file does not contain a JSON object")
            
            settings = TraySettings.from_dict(data)
            logger.info(f"Settings loaded successfully: auto_start={settings.auto_start}, "
                       f"host={settings.server_host}, port={settings.server_port}")
            return settings
            
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
            # File is corrupted, backup and recreate
            logger.error(f"Settings file is corrupted: {e}")
            
            # Create backup
            backup_path = self.settings_file.with_suffix('.json.bak')
            try:
                shutil.copy2(self.settings_file, backup_path)
                logger.info(f"Corrupted settings backed up to {backup_path}")
            except Exception as backup_error:
                logger.warning(f"Failed to backup corrupted settings: {backup_error}")
            
            # Create new file with defaults
            settings = TraySettings()
            self.save(settings)
            logger.info("Created new settings file with defaults")
            return settings
            
        except Exception as e:
            # Unexpected error, log and return defaults
            logger.error(f"Unexpected error loading settings: {e}")
            return TraySettings()
    
    def save(self, settings: TraySettings) -> None:
        """
        Save settings to file immediately.
        
        Creates the parent directory if it doesn't exist.
        Implements retry logic for write failures.
        
        Args:
            settings: TraySettings instance to save
        """
        logger.info(f"Saving settings to {self.settings_file}")
        
        # Ensure parent directory exists
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert settings to dictionary
        data = settings.to_dict()
        
        # Try to save with retry logic
        max_retries = 2
        retry_delay = 1.0  # seconds
        
        for attempt in range(max_retries):
            try:
                # Write to temporary file first
                temp_file = self.settings_file.with_suffix('.json.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # Atomic rename (on Windows, need to remove target first)
                if temp_file.exists():
                    if self.settings_file.exists():
                        self.settings_file.unlink()
                    temp_file.rename(self.settings_file)
                
                logger.info(f"Settings saved successfully: auto_start={settings.auto_start}, "
                           f"host={settings.server_host}, port={settings.server_port}")
                return
                
            except Exception as e:
                logger.error(f"Failed to save settings (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    # Retry after delay
                    import time
                    time.sleep(retry_delay)
                else:
                    # Final attempt failed
                    logger.error("All save attempts failed, settings not persisted")
                    raise
    
    def enable_auto_start(self) -> bool:
        """
        Add registry entry for Windows startup.
        
        Creates a registry entry at HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
        with the command to launch Kiro Gateway in tray mode.
        
        Returns:
            True on success, False on failure
        """
        # Only supported on Windows
        if sys.platform != "win32":
            logger.warning("Auto-start is only supported on Windows")
            return False
        
        try:
            import winreg
            
            # Get the command to run
            command = self._get_auto_start_command()
            if not command:
                logger.error("Failed to determine auto-start command")
                return False
            
            logger.info(f"Enabling auto-start with command: {command}")
            
            # Open registry key
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            
            # Set the value
            winreg.SetValueEx(key, "KiroGateway", 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)
            
            logger.info("Auto-start enabled successfully")
            return True
            
        except PermissionError as e:
            logger.error(f"Permission denied when accessing registry: {e}")
            logger.error("You may need administrator rights to modify startup settings")
            return False
            
        except Exception as e:
            logger.error(f"Failed to enable auto-start: {e}")
            return False
    
    def disable_auto_start(self) -> bool:
        """
        Remove registry entry.
        
        Removes the registry entry at HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
        
        Returns:
            True on success, False on failure
        """
        # Only supported on Windows
        if sys.platform != "win32":
            logger.warning("Auto-start is only supported on Windows")
            return False
        
        try:
            import winreg
            
            logger.info("Disabling auto-start")
            
            # Open registry key
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            
            # Try to delete the value
            try:
                winreg.DeleteValue(key, "KiroGateway")
                logger.info("Auto-start disabled successfully")
                result = True
            except FileNotFoundError:
                # Value doesn't exist, that's fine
                logger.info("Auto-start was not enabled")
                result = True
            finally:
                winreg.CloseKey(key)
            
            return result
            
        except PermissionError as e:
            logger.error(f"Permission denied when accessing registry: {e}")
            logger.error("You may need administrator rights to modify startup settings")
            return False
            
        except Exception as e:
            logger.error(f"Failed to disable auto-start: {e}")
            return False
    
    def is_auto_start_enabled(self) -> bool:
        """
        Check if auto-start is currently enabled.
        
        Checks if the registry entry exists and is valid.
        
        Returns:
            True if enabled, False otherwise
        """
        # Only supported on Windows
        if sys.platform != "win32":
            return False
        
        try:
            import winreg
            
            # Open registry key
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            
            # Try to read the value
            try:
                value, _ = winreg.QueryValueEx(key, "KiroGateway")
                winreg.CloseKey(key)
                
                # Validate that the value is a non-empty string
                if isinstance(value, str) and value.strip():
                    logger.debug(f"Auto-start is enabled with command: {value}")
                    return True
                else:
                    logger.debug("Auto-start registry entry is invalid")
                    return False
                    
            except FileNotFoundError:
                # Value doesn't exist
                winreg.CloseKey(key)
                return False
                
        except Exception as e:
            logger.debug(f"Error checking auto-start status: {e}")
            return False
    
    def _get_auto_start_command(self) -> Optional[str]:
        """
        Get the command string for auto-start registry entry.
        
        Returns:
            Command string or None if it cannot be determined
        """
        try:
            # Get the Python executable path
            python_exe = sys.executable
            
            # Get the main.py path (assuming it's in the parent directory of kiro/)
            # This file is in kiro/settings_manager.py, so go up two levels
            current_file = Path(__file__).resolve()
            main_py = current_file.parent.parent / "main.py"
            
            if not main_py.exists():
                logger.error(f"main.py not found at {main_py}")
                return None
            
            # Build the command: "python.exe" "path/to/main.py" --tray
            command = f'"{python_exe}" "{main_py}" --tray'
            return command
            
        except Exception as e:
            logger.error(f"Failed to build auto-start command: {e}")
            return None
