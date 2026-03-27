# -*- coding: utf-8 -*-

"""
Tests for the CredentialManager and CredentialProfile classes.

Covers:
- Profile creation from various JSON formats
- Round-robin selection across enabled profiles
- Enable/disable toggling
- Persistence (save/load) to JSON file
- Validation of credential profiles
- Edge cases: empty profiles, missing fields, malformed JSON
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from kiro.credential_manager import CredentialManager, CredentialProfile
from kiro.auth import KiroAuthManager, AuthType


# =============================================================================
# CredentialProfile Tests
# =============================================================================


class TestCredentialProfile:
    """Tests for the CredentialProfile dataclass-like object."""

    def test_profile_stores_basic_fields(self):
        """Profile stores id, name, enabled, and created_at."""
        auth = KiroAuthManager(refresh_token="tok", region="us-east-1")
        profile = CredentialProfile(
            profile_id="abc123",
            name="Test User",
            auth_manager=auth,
            enabled=True,
        )
        assert profile.id == "abc123"
        assert profile.name == "Test User"
        assert profile.enabled is True
        assert profile.created_at is not None

    def test_profile_auth_type_label_kiro_desktop(self):
        """auth_type_label returns 'kiro_desktop' for desktop auth."""
        auth = KiroAuthManager(refresh_token="tok", region="us-east-1")
        profile = CredentialProfile("id1", "name", auth)
        assert profile.auth_type_label == "kiro_desktop"

    def test_profile_auth_type_label_aws_sso(self):
        """auth_type_label returns 'aws_sso_oidc' when client credentials present."""
        auth = KiroAuthManager(
            refresh_token="tok",
            region="us-east-1",
            client_id="cid",
            client_secret="csec",
        )
        profile = CredentialProfile("id2", "name", auth)
        assert profile.auth_type_label == "aws_sso_oidc"

    def test_profile_to_dict_contains_required_keys(self):
        """to_dict includes id, name, enabled, created_at, raw_json."""
        auth = KiroAuthManager(refresh_token="tok", region="us-east-1")
        raw = {"refreshToken": "tok"}
        profile = CredentialProfile("id3", "My Profile", auth, raw_json=raw)
        d = profile.to_dict()
        assert d["id"] == "id3"
        assert d["name"] == "My Profile"
        assert d["enabled"] is True
        assert d["raw_json"] == raw
        assert "created_at" in d

    def test_profile_disabled_by_default_false(self):
        """Profile is enabled by default."""
        auth = KiroAuthManager(refresh_token="tok", region="us-east-1")
        profile = CredentialProfile("id4", "name", auth)
        assert profile.enabled is True

    def test_profile_custom_created_at(self):
        """Profile accepts a custom created_at timestamp."""
        auth = KiroAuthManager(refresh_token="tok", region="us-east-1")
        ts = "2025-01-01T00:00:00+00:00"
        profile = CredentialProfile("id5", "name", auth, created_at=ts)
        assert profile.created_at == ts


# =============================================================================
# CredentialManager - Add Profile Tests
# =============================================================================


class TestCredentialManagerAddProfile:
    """Tests for adding credential profiles."""

    @pytest.mark.asyncio
    async def test_add_profile_kiro_desktop(self, tmp_path):
        """Adding a profile with only refreshToken creates Kiro Desktop auth."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        profile = await mgr.add_profile("User A", {"refreshToken": "tok_a"})

        assert profile.name == "User A"
        assert profile.auth_manager.auth_type == AuthType.KIRO_DESKTOP
        assert profile.enabled is True
        assert mgr.profile_count == 1

    @pytest.mark.asyncio
    async def test_add_profile_aws_sso_oidc(self, tmp_path):
        """Adding a profile with clientId/clientSecret creates AWS SSO auth."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        cred_json = {
            "refreshToken": "tok_b",
            "clientId": "cid",
            "clientSecret": "csec",
            "region": "eu-central-1",
        }
        profile = await mgr.add_profile("User B", cred_json)

        assert profile.auth_manager.auth_type == AuthType.AWS_SSO_OIDC
        assert profile.auth_manager.region == "eu-central-1"

    @pytest.mark.asyncio
    async def test_add_profile_missing_refresh_token_raises(self, tmp_path):
        """Adding a profile without refreshToken raises ValueError."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        with pytest.raises(ValueError, match="refreshToken"):
            await mgr.add_profile("Bad", {"region": "us-east-1"})

    @pytest.mark.asyncio
    async def test_add_profile_snake_case_refresh_token(self, tmp_path):
        """Supports snake_case 'refresh_token' field name."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        profile = await mgr.add_profile("Snake", {"refresh_token": "tok_snake"})
        assert profile is not None
        assert mgr.profile_count == 1

    @pytest.mark.asyncio
    async def test_add_profile_persists_to_file(self, tmp_path):
        """Adding a profile writes to the credentials file."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        await mgr.add_profile("Persist", {"refreshToken": "tok_p"})

        assert creds_file.exists()
        data = json.loads(creds_file.read_text())
        assert len(data) == 1
        assert data[0]["name"] == "Persist"

    @pytest.mark.asyncio
    async def test_add_multiple_profiles(self, tmp_path):
        """Multiple profiles can be added."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        await mgr.add_profile("A", {"refreshToken": "tok_a"})
        await mgr.add_profile("B", {"refreshToken": "tok_b"})
        await mgr.add_profile("C", {"refreshToken": "tok_c"})

        assert mgr.profile_count == 3
        data = json.loads(creds_file.read_text())
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_add_profile_uses_default_region(self, tmp_path):
        """Profile uses default region when not specified in JSON."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file, default_region="ap-southeast-1")

        profile = await mgr.add_profile("Default Region", {"refreshToken": "tok"})
        assert profile.auth_manager.region == "ap-southeast-1"

    @pytest.mark.asyncio
    async def test_add_profile_unique_ids(self, tmp_path):
        """Each profile gets a unique ID."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        p1 = await mgr.add_profile("A", {"refreshToken": "tok_a"})
        p2 = await mgr.add_profile("B", {"refreshToken": "tok_b"})

        assert p1.id != p2.id


# =============================================================================
# CredentialManager - Remove Profile Tests
# =============================================================================


class TestCredentialManagerRemoveProfile:
    """Tests for removing credential profiles."""

    @pytest.mark.asyncio
    async def test_remove_existing_profile(self, tmp_path):
        """Removing an existing profile returns True and decrements count."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)
        profile = await mgr.add_profile("ToRemove", {"refreshToken": "tok"})

        result = await mgr.remove_profile(profile.id)

        assert result is True
        assert mgr.profile_count == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_profile(self, tmp_path):
        """Removing a nonexistent profile returns False."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        result = await mgr.remove_profile("nonexistent_id")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_persists_change(self, tmp_path):
        """Removal is persisted to the credentials file."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)
        p1 = await mgr.add_profile("Keep", {"refreshToken": "tok_keep"})
        p2 = await mgr.add_profile("Remove", {"refreshToken": "tok_rm"})

        await mgr.remove_profile(p2.id)

        data = json.loads(creds_file.read_text())
        assert len(data) == 1
        assert data[0]["id"] == p1.id

    @pytest.mark.asyncio
    async def test_remove_does_not_affect_other_profiles(self, tmp_path):
        """Removing one profile leaves others intact."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)
        p1 = await mgr.add_profile("A", {"refreshToken": "tok_a"})
        p2 = await mgr.add_profile("B", {"refreshToken": "tok_b"})
        p3 = await mgr.add_profile("C", {"refreshToken": "tok_c"})

        await mgr.remove_profile(p2.id)

        assert mgr.profile_count == 2
        ids = [p.id for p in mgr.profiles]
        assert p1.id in ids
        assert p3.id in ids
        assert p2.id not in ids


# =============================================================================
# CredentialManager - Toggle Profile Tests
# =============================================================================


class TestCredentialManagerToggleProfile:
    """Tests for enabling/disabling credential profiles."""

    @pytest.mark.asyncio
    async def test_disable_profile(self, tmp_path):
        """Disabling a profile sets enabled=False."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)
        profile = await mgr.add_profile("Toggle", {"refreshToken": "tok"})

        result = await mgr.toggle_profile(profile.id, False)

        assert result is True
        assert mgr.profiles[0].enabled is False

    @pytest.mark.asyncio
    async def test_enable_profile(self, tmp_path):
        """Re-enabling a disabled profile sets enabled=True."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)
        profile = await mgr.add_profile("Toggle", {"refreshToken": "tok"})
        await mgr.toggle_profile(profile.id, False)

        result = await mgr.toggle_profile(profile.id, True)

        assert result is True
        assert mgr.profiles[0].enabled is True

    @pytest.mark.asyncio
    async def test_toggle_nonexistent_profile(self, tmp_path):
        """Toggling a nonexistent profile returns False."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        result = await mgr.toggle_profile("nonexistent", True)
        assert result is False

    @pytest.mark.asyncio
    async def test_toggle_persists_change(self, tmp_path):
        """Toggle state is persisted to the credentials file."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)
        profile = await mgr.add_profile("Persist", {"refreshToken": "tok"})

        await mgr.toggle_profile(profile.id, False)

        data = json.loads(creds_file.read_text())
        assert data[0]["enabled"] is False


# =============================================================================
# CredentialManager - Round Robin Tests
# =============================================================================


class TestCredentialManagerRoundRobin:
    """Tests for round-robin auth manager selection."""

    @pytest.mark.asyncio
    async def test_round_robin_cycles_through_enabled(self, tmp_path):
        """Round-robin returns each enabled profile in order, then wraps."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        p1 = await mgr.add_profile("A", {"refreshToken": "tok_a"})
        p2 = await mgr.add_profile("B", {"refreshToken": "tok_b"})
        p3 = await mgr.add_profile("C", {"refreshToken": "tok_c"})

        am1 = mgr.get_next_auth_manager()
        am2 = mgr.get_next_auth_manager()
        am3 = mgr.get_next_auth_manager()
        am4 = mgr.get_next_auth_manager()  # wraps to first

        assert am1 is p1.auth_manager
        assert am2 is p2.auth_manager
        assert am3 is p3.auth_manager
        assert am4 is p1.auth_manager

    @pytest.mark.asyncio
    async def test_round_robin_skips_disabled(self, tmp_path):
        """Round-robin only returns enabled profiles."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        p1 = await mgr.add_profile("A", {"refreshToken": "tok_a"})
        p2 = await mgr.add_profile("B", {"refreshToken": "tok_b"})
        p3 = await mgr.add_profile("C", {"refreshToken": "tok_c"})

        await mgr.toggle_profile(p2.id, False)

        am1 = mgr.get_next_auth_manager()
        am2 = mgr.get_next_auth_manager()
        am3 = mgr.get_next_auth_manager()

        assert am1 is p1.auth_manager
        assert am2 is p3.auth_manager
        assert am3 is p1.auth_manager  # wraps

    def test_round_robin_no_profiles_returns_none(self, tmp_path):
        """Returns None when no profiles exist."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        assert mgr.get_next_auth_manager() is None

    @pytest.mark.asyncio
    async def test_round_robin_all_disabled_returns_none(self, tmp_path):
        """Returns None when all profiles are disabled."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        p1 = await mgr.add_profile("A", {"refreshToken": "tok_a"})
        await mgr.toggle_profile(p1.id, False)

        assert mgr.get_next_auth_manager() is None

    @pytest.mark.asyncio
    async def test_round_robin_single_profile(self, tmp_path):
        """Single profile always returns the same auth manager."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        p1 = await mgr.add_profile("Solo", {"refreshToken": "tok"})

        for _ in range(5):
            assert mgr.get_next_auth_manager() is p1.auth_manager


# =============================================================================
# CredentialManager - Persistence (Load) Tests
# =============================================================================


class TestCredentialManagerLoad:
    """Tests for loading credential profiles from file."""

    def test_load_from_nonexistent_file(self, tmp_path):
        """Loading from a nonexistent file starts with empty profiles."""
        creds_file = tmp_path / "nonexistent.json"
        mgr = CredentialManager(credentials_file=creds_file)
        mgr.load()
        assert mgr.profile_count == 0

    @pytest.mark.asyncio
    async def test_load_restores_profiles(self, tmp_path):
        """Profiles saved by one manager can be loaded by another."""
        creds_file = tmp_path / "creds.json"

        # Save profiles
        mgr1 = CredentialManager(credentials_file=creds_file)
        await mgr1.add_profile("User A", {"refreshToken": "tok_a", "region": "eu-central-1"})
        await mgr1.add_profile("User B", {
            "refreshToken": "tok_b",
            "clientId": "cid",
            "clientSecret": "csec",
        })

        # Load in a new manager
        mgr2 = CredentialManager(credentials_file=creds_file)
        mgr2.load()

        assert mgr2.profile_count == 2
        names = [p.name for p in mgr2.profiles]
        assert "User A" in names
        assert "User B" in names

    @pytest.mark.asyncio
    async def test_load_restores_enabled_state(self, tmp_path):
        """Disabled state is preserved across save/load."""
        creds_file = tmp_path / "creds.json"

        mgr1 = CredentialManager(credentials_file=creds_file)
        p = await mgr1.add_profile("Disabled", {"refreshToken": "tok"})
        await mgr1.toggle_profile(p.id, False)

        mgr2 = CredentialManager(credentials_file=creds_file)
        mgr2.load()

        assert mgr2.profiles[0].enabled is False

    @pytest.mark.asyncio
    async def test_load_restores_auth_type(self, tmp_path):
        """Auth type is correctly detected after load."""
        creds_file = tmp_path / "creds.json"

        mgr1 = CredentialManager(credentials_file=creds_file)
        await mgr1.add_profile("SSO", {
            "refreshToken": "tok",
            "clientId": "cid",
            "clientSecret": "csec",
        })

        mgr2 = CredentialManager(credentials_file=creds_file)
        mgr2.load()

        assert mgr2.profiles[0].auth_manager.auth_type == AuthType.AWS_SSO_OIDC

    def test_load_corrupted_file_skips_bad_entries(self, tmp_path):
        """Corrupted entries are skipped, valid ones are loaded."""
        creds_file = tmp_path / "creds.json"
        data = [
            {"id": "good", "name": "Good", "enabled": True, "raw_json": {"refreshToken": "tok"}},
            {"id": "bad", "name": "Bad", "enabled": True, "raw_json": {}},  # missing refreshToken
        ]
        creds_file.write_text(json.dumps(data))

        mgr = CredentialManager(credentials_file=creds_file)
        mgr.load()

        assert mgr.profile_count == 1
        assert mgr.profiles[0].name == "Good"

    def test_load_invalid_json_file(self, tmp_path):
        """Invalid JSON file is handled gracefully."""
        creds_file = tmp_path / "creds.json"
        creds_file.write_text("not valid json {{{")

        mgr = CredentialManager(credentials_file=creds_file)
        mgr.load()

        assert mgr.profile_count == 0

    def test_load_non_array_json(self, tmp_path):
        """Non-array JSON is handled gracefully."""
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"not": "an array"}')

        mgr = CredentialManager(credentials_file=creds_file)
        mgr.load()

        assert mgr.profile_count == 0


# =============================================================================
# CredentialManager - Summary Tests
# =============================================================================


class TestCredentialManagerSummary:
    """Tests for the get_summary method."""

    @pytest.mark.asyncio
    async def test_summary_contains_expected_fields(self, tmp_path):
        """Summary includes id, name, enabled, auth_type, region, created_at."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)
        await mgr.add_profile("Summary Test", {"refreshToken": "tok", "region": "eu-west-1"})

        summaries = mgr.get_summary()

        assert len(summaries) == 1
        s = summaries[0]
        assert "id" in s
        assert s["name"] == "Summary Test"
        assert s["enabled"] is True
        assert s["auth_type"] == "kiro_desktop"
        assert s["region"] == "eu-west-1"
        assert "created_at" in s

    @pytest.mark.asyncio
    async def test_summary_excludes_sensitive_data(self, tmp_path):
        """Summary does not contain tokens or secrets."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)
        await mgr.add_profile("Sensitive", {
            "refreshToken": "secret_token",
            "clientId": "secret_id",
            "clientSecret": "secret_secret",
        })

        summaries = mgr.get_summary()
        s = summaries[0]

        assert "refreshToken" not in str(s)
        assert "secret_token" not in str(s)
        assert "clientSecret" not in str(s)
        assert "raw_json" not in s

    def test_summary_empty_when_no_profiles(self, tmp_path):
        """Summary returns empty list when no profiles exist."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        assert mgr.get_summary() == []


# =============================================================================
# CredentialManager - Validate Profile Tests
# =============================================================================


class TestCredentialManagerValidate:
    """Tests for the validate_profile method."""

    @pytest.mark.asyncio
    async def test_validate_nonexistent_profile(self, tmp_path):
        """Validating a nonexistent profile returns invalid."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        result = await mgr.validate_profile("nonexistent")
        assert result["valid"] is False
        assert "不存在" in result["message"]

    @pytest.mark.asyncio
    async def test_validate_profile_token_error(self, tmp_path):
        """Validation returns invalid when token refresh fails."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)
        profile = await mgr.add_profile("Fail", {"refreshToken": "bad_tok"})

        # The auth manager will try to refresh and fail (network blocked in tests)
        result = await mgr.validate_profile(profile.id)
        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_validate_profile_with_valid_token(self, tmp_path):
        """Validation returns valid when auth manager has a valid token."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)
        profile = await mgr.add_profile("Valid", {"refreshToken": "tok"})

        # Manually set a valid token to bypass refresh
        profile.auth_manager._access_token = "valid_token"
        profile.auth_manager._expires_at = datetime(2099, 1, 1, tzinfo=timezone.utc)

        result = await mgr.validate_profile(profile.id)
        assert result["valid"] is True
        assert "成功" in result["message"]


# =============================================================================
# CredentialManager - Build Auth Manager Tests
# =============================================================================


class TestBuildAuthManager:
    """Tests for the _build_auth_manager helper method."""

    def test_sets_access_token_from_json(self, tmp_path):
        """accessToken from JSON is set on the auth manager."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        cred = {
            "refreshToken": "tok",
            "accessToken": "existing_access_token",
            "expiresAt": "2099-01-01T00:00:00Z",
        }
        am = mgr._build_auth_manager(cred)

        assert am._access_token == "existing_access_token"
        assert am._expires_at is not None
        assert am._expires_at.year == 2099

    def test_sets_expires_at_iso_format(self, tmp_path):
        """expiresAt in ISO format is parsed correctly."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        cred = {
            "refreshToken": "tok",
            "expiresAt": "2099-06-15T12:30:00+00:00",
        }
        am = mgr._build_auth_manager(cred)

        assert am._expires_at is not None
        assert am._expires_at.month == 6
        assert am._expires_at.day == 15

    def test_handles_invalid_expires_at_gracefully(self, tmp_path):
        """Invalid expiresAt does not crash, just warns."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        cred = {
            "refreshToken": "tok",
            "expiresAt": "not-a-date",
        }
        am = mgr._build_auth_manager(cred)
        # Should not crash, expires_at remains None
        assert am._expires_at is None

    def test_client_id_hash_with_merged_client_credentials(self, tmp_path):
        """clientIdHash + merged clientId/clientSecret creates AWS SSO auth."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        cred = {
            "refreshToken": "tok",
            "clientIdHash": "somehash123",
            "clientId": "merged_cid",
            "clientSecret": "merged_csec",
            "region": "us-east-1",
        }
        am = mgr._build_auth_manager(cred)
        assert am is not None
        assert am.auth_type == AuthType.AWS_SSO_OIDC

    def test_creds_file_path_reloads_from_file(self, tmp_path):
        """_creds_file_path triggers reload from the original file."""
        # Create a credential file
        cred_file = tmp_path / "my_cred.json"
        cred_file.write_text(json.dumps({
            "refreshToken": "tok_from_file",
            "region": "eu-central-1",
        }))

        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        cred = {"_creds_file_path": str(cred_file)}
        am = mgr._build_auth_manager(cred)

        assert am is not None
        assert am.region == "eu-central-1"

    def test_missing_creds_file_path_falls_back(self, tmp_path):
        """Missing _creds_file_path falls back to field-based construction."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        cred = {
            "_creds_file_path": "/nonexistent/path.json",
            "refreshToken": "fallback_tok",
        }
        am = mgr._build_auth_manager(cred)
        assert am is not None


# =============================================================================
# CredentialManager - Add Profile From File Tests
# =============================================================================


class TestAddProfileFromFile:
    """Tests for the add_profile_from_file method."""

    @pytest.mark.asyncio
    async def test_add_from_file_success(self, tmp_path):
        """Successfully adds a profile from a credential file."""
        cred_file = tmp_path / "kiro_cred.json"
        cred_file.write_text(json.dumps({
            "refreshToken": "tok_file",
            "region": "us-east-1",
            "profileArn": "arn:test",
        }))

        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        profile = await mgr.add_profile_from_file("File User", str(cred_file))

        assert profile.name == "File User"
        assert profile.auth_manager.region == "us-east-1"
        assert mgr.profile_count == 1

    @pytest.mark.asyncio
    async def test_add_from_file_nonexistent_raises(self, tmp_path):
        """Raises ValueError when file does not exist."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        with pytest.raises(ValueError, match="不存在"):
            await mgr.add_profile_from_file("Missing", "/nonexistent/file.json")

    @pytest.mark.asyncio
    async def test_add_from_file_invalid_json_raises(self, tmp_path):
        """Raises ValueError when file is not valid JSON."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json {{{")

        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        with pytest.raises(ValueError, match="JSON"):
            await mgr.add_profile_from_file("Bad", str(bad_file))

    @pytest.mark.asyncio
    async def test_add_from_file_stores_path_for_reload(self, tmp_path):
        """File path is stored in raw_json for reload on restart."""
        cred_file = tmp_path / "kiro_cred.json"
        cred_file.write_text(json.dumps({"refreshToken": "tok"}))

        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        profile = await mgr.add_profile_from_file("Path Test", str(cred_file))

        assert "_creds_file_path" in profile.raw_json
        assert profile.raw_json["_creds_file_path"] == str(cred_file)

    @pytest.mark.asyncio
    async def test_add_from_file_persists_and_reloads(self, tmp_path):
        """Profile added from file can be reloaded by a new manager."""
        cred_file = tmp_path / "kiro_cred.json"
        cred_file.write_text(json.dumps({
            "refreshToken": "tok_persist",
            "region": "eu-west-1",
        }))

        creds_file = tmp_path / "creds.json"
        mgr1 = CredentialManager(credentials_file=creds_file)
        await mgr1.add_profile_from_file("Persist", str(cred_file))

        # Reload in new manager
        mgr2 = CredentialManager(credentials_file=creds_file)
        mgr2.load()

        assert mgr2.profile_count == 1
        assert mgr2.profiles[0].name == "Persist"
        assert mgr2.profiles[0].auth_manager.region == "eu-west-1"


# =============================================================================
# CredentialManager - Query Quota Tests
# =============================================================================


class TestCredentialManagerQueryQuota:
    """Tests for the query_quota method."""

    @pytest.mark.asyncio
    async def test_quota_nonexistent_profile(self, tmp_path):
        """Returns error for nonexistent profile."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)

        result = await mgr.query_quota("nonexistent")
        assert result["success"] is False
        assert "不存在" in result["message"]

    @pytest.mark.asyncio
    async def test_quota_returns_structure(self, tmp_path):
        """Quota result contains expected keys even when API calls fail."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)
        profile = await mgr.add_profile("Quota Test", {"refreshToken": "tok"})

        # Set a valid token to bypass refresh (network is blocked in tests)
        profile.auth_manager._access_token = "valid_token"
        profile.auth_manager._expires_at = datetime(2099, 1, 1, tzinfo=timezone.utc)

        result = await mgr.query_quota(profile.id)
        # API calls will fail (network blocked), but structure should be present
        assert "success" in result
        assert "auth_type" in result
        assert "region" in result
        assert "usage" in result

    @pytest.mark.asyncio
    async def test_quota_token_failure(self, tmp_path):
        """Returns error when token refresh fails."""
        creds_file = tmp_path / "creds.json"
        mgr = CredentialManager(credentials_file=creds_file)
        profile = await mgr.add_profile("Bad Token", {"refreshToken": "bad"})

        # Don't set a valid token — refresh will fail
        result = await mgr.query_quota(profile.id)
        assert result["success"] is False
        assert "token" in result["message"].lower() or "失败" in result["message"]
