"""
Property-based tests for SettingsManager alias persistence.

Uses Hypothesis to verify that model alias mappings survive serialization
round-trips through TraySettings and SettingsManager.
"""

import pytest
from pathlib import Path
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from kiro.settings_manager import SettingsManager, TraySettings


# Strategy: generate alias mappings as Dict[str, str] with printable keys/values
alias_mappings = st.dictionaries(
    keys=st.text(min_size=1, max_size=50),
    values=st.text(min_size=1, max_size=100),
    max_size=30,
)


class TestAliasPersistenceRoundTrip:
    """
    Feature: web-admin-panel, Property 4: 别名持久化往返

    For any alias mapping set, serializing via TraySettings.to_dict() then
    deserializing via TraySettings.from_dict() should yield the same mapping.
    Additionally, the full SettingsManager save/load cycle should preserve
    alias mappings identically.

    **Validates: Requirements 6.1, 6.2, 6.3, 6.5**
    """

    @given(aliases=alias_mappings)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_tray_settings_to_dict_from_dict_roundtrip(self, aliases):
        """
        Verify TraySettings serialization round-trip preserves model_aliases.

        What it does: Creates TraySettings with random aliases, converts to dict
        then back, and asserts equality.
        Purpose: Ensures to_dict/from_dict are inverse operations for aliases.

        **Validates: Requirements 6.1, 6.5**
        """
        # Arrange
        original = TraySettings(model_aliases=aliases)

        # Act
        serialized = original.to_dict()
        restored = TraySettings.from_dict(serialized)

        # Assert
        assert restored.model_aliases == original.model_aliases

    @given(aliases=alias_mappings)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_settings_manager_save_load_roundtrip(self, aliases, tmp_path):
        """
        Verify full SettingsManager save/load cycle preserves model_aliases.

        What it does: Saves TraySettings with random aliases to a temp file via
        SettingsManager, loads them back, and asserts equality.
        Purpose: Ensures the JSON file persistence layer preserves aliases end-to-end.

        **Validates: Requirements 6.1, 6.2, 6.3, 6.5**
        """
        # Arrange
        settings_file = tmp_path / "settings.json"
        manager = SettingsManager(settings_file=settings_file)
        original = TraySettings(model_aliases=aliases)

        # Act
        manager.save(original)
        loaded = manager.load()

        # Assert
        assert loaded.model_aliases == original.model_aliases
