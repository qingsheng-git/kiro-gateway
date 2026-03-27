# -*- coding: utf-8 -*-

"""
Unit tests for startup alias loading in main.py lifespan.

Tests that the lifespan function correctly loads persisted aliases from
SettingsManager and falls back to MODEL_ALIASES from config.py when
no saved aliases exist.

Validates Requirements 6.2, 6.4:
- 6.2: On startup, ModelResolver loads saved aliases from settings file
- 6.4: If settings file doesn't exist, uses MODEL_ALIASES defaults
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from kiro.settings_manager import TraySettings, SettingsManager
from kiro.config import MODEL_ALIASES


class TestStartupAliasLoading:
    """Tests for alias loading during application startup (lifespan).

    Validates Requirements 6.2 and 6.4:
    - Settings file with aliases → aliases loaded into ModelResolver
    - Settings file without aliases → MODEL_ALIASES from config.py used
    """

    def test_loads_aliases_from_settings_file(self, tmp_path):
        """
        What it does: Verifies that when a settings file contains saved aliases,
                      those aliases are used by ModelResolver at startup.
        Purpose: Ensure persisted aliases survive restarts (Requirement 6.2).
        """
        saved_aliases = {"my-opus": "claude-opus-4.5", "fast": "claude-haiku-4.5"}

        mock_settings = TraySettings(model_aliases=saved_aliases)
        mock_sm = MagicMock(spec=SettingsManager)
        mock_sm.load.return_value = mock_settings

        with patch("main.SettingsManager", return_value=mock_sm):
            from main import app
            from fastapi.testclient import TestClient

            with TestClient(app) as client:
                resolver = client.app.state.model_resolver
                assert resolver.aliases == saved_aliases
                assert "my-opus" in resolver.aliases
                assert resolver.aliases["my-opus"] == "claude-opus-4.5"
                assert resolver.aliases["fast"] == "claude-haiku-4.5"

                # Verify settings_manager is stored on app.state
                assert client.app.state.settings_manager is mock_sm

    def test_uses_config_defaults_when_no_saved_aliases(self, tmp_path):
        """
        What it does: Verifies that when the settings file has no saved aliases
                      (empty dict), MODEL_ALIASES from config.py is used.
        Purpose: Ensure fallback to defaults on fresh install (Requirement 6.4).
        """
        mock_settings = TraySettings(model_aliases={})
        mock_sm = MagicMock(spec=SettingsManager)
        mock_sm.load.return_value = mock_settings

        with patch("main.SettingsManager", return_value=mock_sm):
            from main import app
            from fastapi.testclient import TestClient

            with TestClient(app) as client:
                resolver = client.app.state.model_resolver
                assert resolver.aliases == MODEL_ALIASES

                # Verify settings_manager is still stored on app.state
                assert client.app.state.settings_manager is mock_sm

    def test_settings_manager_stored_on_app_state(self, tmp_path):
        """
        What it does: Verifies that SettingsManager instance is accessible
                      via app.state.settings_manager after startup.
        Purpose: Ensure admin API endpoints can access SettingsManager for
                 persisting alias changes.
        """
        mock_sm = MagicMock(spec=SettingsManager)
        mock_sm.load.return_value = TraySettings()

        with patch("main.SettingsManager", return_value=mock_sm):
            from main import app
            from fastapi.testclient import TestClient

            with TestClient(app) as client:
                sm = client.app.state.settings_manager
                assert sm is mock_sm
                mock_sm.load.assert_called_once()

    def test_settings_file_not_found_uses_defaults(self, tmp_path):
        """
        What it does: Verifies that when SettingsManager.load() returns default
                      settings (file doesn't exist), MODEL_ALIASES is used.
        Purpose: Ensure clean first-run experience (Requirement 6.4).
        """
        # SettingsManager.load() returns TraySettings() with empty model_aliases
        # when the file doesn't exist — this triggers the fallback
        mock_sm = MagicMock(spec=SettingsManager)
        mock_sm.load.return_value = TraySettings()  # defaults: model_aliases={}

        with patch("main.SettingsManager", return_value=mock_sm):
            from main import app
            from fastapi.testclient import TestClient

            with TestClient(app) as client:
                resolver = client.app.state.model_resolver
                # Empty saved aliases → falls back to MODEL_ALIASES
                assert resolver.aliases == MODEL_ALIASES
