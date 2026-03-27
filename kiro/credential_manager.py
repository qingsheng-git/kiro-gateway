# -*- coding: utf-8 -*-

# Kiro Gateway
# https://github.com/jwadow/kiro-gateway
# Copyright (C) 2025 Jwadow
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Multi-user credential manager for Kiro Gateway.

Manages multiple Kiro credential profiles that can be added via the admin
web UI. Each profile creates its own KiroAuthManager instance. Requests
are distributed across active profiles using round-robin selection.

Credential profiles are persisted to a JSON file at:
    ~/.kiro-gateway/credentials.json

Supported input modes:
    1. File path: Point to a JSON credential file on disk (recommended).
       KiroAuthManager handles clientIdHash, device registration, etc.
    2. Pasted JSON: Paste credential JSON directly in the admin UI.
       Supports refreshToken, accessToken, expiresAt, clientIdHash, etc.
"""

import asyncio
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from kiro.auth import KiroAuthManager, AuthType
from kiro.config import REGION, SSL_VERIFY


# Default file path for persisted credentials
DEFAULT_CREDENTIALS_FILE = Path.home() / ".kiro-gateway" / "credentials.json"


class CredentialProfile:
    """
    A single credential profile with its own KiroAuthManager.

    Attributes:
        id: Unique identifier for this profile.
        name: Human-readable display name.
        auth_manager: KiroAuthManager instance for this profile.
        enabled: Whether this profile is active for request routing.
        created_at: ISO 8601 creation timestamp.
        auth_type_label: Detected authentication type label.
    """

    def __init__(
        self,
        profile_id: str,
        name: str,
        auth_manager: KiroAuthManager,
        enabled: bool = True,
        created_at: Optional[str] = None,
        raw_json: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a credential profile.

        Args:
            profile_id: Unique identifier.
            name: Display name.
            auth_manager: Configured KiroAuthManager.
            enabled: Whether the profile is active.
            created_at: ISO 8601 timestamp (auto-generated if None).
            raw_json: Original JSON data used to create this profile (stored for persistence).
        """
        self.id = profile_id
        self.name = name
        self.auth_manager = auth_manager
        self.enabled = enabled
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.raw_json = raw_json or {}

    @property
    def auth_type_label(self) -> str:
        """Human-readable authentication type label."""
        return self.auth_manager.auth_type.value

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize profile metadata for persistence.

        The raw credential JSON is stored so the profile can be
        reconstructed on restart. Sensitive tokens are included
        because the file is local-only.

        Returns:
            Dictionary suitable for JSON serialization.
        """
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "raw_json": self.raw_json,
        }


class CredentialManager:
    """
    Manages multiple credential profiles with round-robin selection.

    Profiles are persisted to a JSON file and each profile owns a
    KiroAuthManager instance. The ``get_next_auth_manager`` method
    returns the next enabled profile's auth manager in round-robin order.

    Thread-safety: profile mutations are protected by an asyncio.Lock.

    Attributes:
        profiles: Ordered list of credential profiles.
        credentials_file: Path to the persistence file.
    """

    def __init__(
        self,
        credentials_file: Optional[Path] = None,
        default_region: str = "us-east-1",
    ):
        """
        Initialize the credential manager.

        Args:
            credentials_file: Path to JSON persistence file.
                              Defaults to ~/.kiro-gateway/credentials.json.
            default_region: Default AWS region for new profiles.
        """
        self.credentials_file = credentials_file or DEFAULT_CREDENTIALS_FILE
        self._default_region = default_region
        self._profiles: List[CredentialProfile] = []
        self._round_robin_index: int = 0
        self._lock = asyncio.Lock()

        # Usage tracking: maps auth_manager id() → {request_count, last_used}
        self._usage_stats: Dict[int, Dict[str, Any]] = {}

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def profiles(self) -> List[CredentialProfile]:
        """All credential profiles (enabled and disabled)."""
        return list(self._profiles)

    @property
    def enabled_profiles(self) -> List[CredentialProfile]:
        """Only enabled credential profiles."""
        return [p for p in self._profiles if p.enabled]

    @property
    def profile_count(self) -> int:
        """Total number of profiles."""
        return len(self._profiles)

    # -------------------------------------------------------------------------
    # Round-robin selection
    # -------------------------------------------------------------------------

    def get_next_auth_manager(self) -> Optional[KiroAuthManager]:
        """
        Return the next enabled profile's auth manager using round-robin.

        Returns:
            KiroAuthManager for the next enabled profile, or None if no
            enabled profiles exist.
        """
        enabled = self.enabled_profiles
        if not enabled:
            return None

        # Wrap index if it exceeds the list length
        idx = self._round_robin_index % len(enabled)
        self._round_robin_index = idx + 1
        return enabled[idx].auth_manager

    # -------------------------------------------------------------------------
    # Usage tracking
    # -------------------------------------------------------------------------

    def record_usage(self, auth_manager: KiroAuthManager) -> None:
        """
        Record a request for the given auth manager.

        Called by route handlers after each successful API request.

        Args:
            auth_manager: The auth manager that was used for the request.
        """
        key = id(auth_manager)
        stats = self._usage_stats.get(key)
        if stats is None:
            self._usage_stats[key] = {
                "request_count": 1,
                "last_used": datetime.now(timezone.utc).isoformat(),
            }
        else:
            stats["request_count"] += 1
            stats["last_used"] = datetime.now(timezone.utc).isoformat()

    def get_profile_usage(self, profile_id: str) -> Dict[str, Any]:
        """
        Get usage stats for a specific profile.

        Args:
            profile_id: The profile's unique identifier.

        Returns:
            Dict with request_count and last_used, or zeros if no usage.
        """
        profile = self._get_profile_by_id(profile_id)
        if not profile:
            return {"request_count": 0, "last_used": None}

        key = id(profile.auth_manager)
        stats = self._usage_stats.get(key)
        if stats:
            return dict(stats)
        return {"request_count": 0, "last_used": None}

    # -------------------------------------------------------------------------
    # CRUD operations
    # -------------------------------------------------------------------------

    async def add_profile(
        self,
        name: str,
        credential_json: Dict[str, Any],
    ) -> CredentialProfile:
        """
        Create a new credential profile from pasted JSON.

        Delegates to KiroAuthManager's ``creds_file`` path when the JSON
        contains ``clientIdHash`` (Enterprise Kiro IDE) so that device
        registration files are loaded automatically. Otherwise builds the
        auth manager from individual fields.

        Args:
            name: Human-readable display name.
            credential_json: Parsed JSON dict with credential fields.

        Returns:
            The newly created CredentialProfile.

        Raises:
            ValueError: If the JSON is missing required fields.
        """
        async with self._lock:
            auth_manager = self._build_auth_manager(credential_json)

            profile_id = uuid.uuid4().hex[:12]
            profile = CredentialProfile(
                profile_id=profile_id,
                name=name,
                auth_manager=auth_manager,
                enabled=True,
                raw_json=credential_json,
            )

            self._profiles.append(profile)
            self._save()

            logger.info(
                f"Credential profile added: id={profile_id}, name={name}, "
                f"auth_type={auth_manager.auth_type.value}"
            )
            return profile

    async def add_profile_from_file(
        self,
        name: str,
        file_path: str,
    ) -> CredentialProfile:
        """
        Create a new credential profile from a credential file path.

        Uses KiroAuthManager's built-in ``creds_file`` loading which
        handles all credential formats including Enterprise Kiro IDE
        (clientIdHash → device registration) automatically.

        The file content is also read and stored as ``raw_json`` for
        persistence so the profile can be reconstructed on restart.

        Args:
            name: Human-readable display name.
            file_path: Absolute or ~ path to a JSON credential file.

        Returns:
            The newly created CredentialProfile.

        Raises:
            ValueError: If the file does not exist or is not valid JSON.
        """
        async with self._lock:
            path = Path(file_path).expanduser()
            if not path.exists():
                raise ValueError(f"凭证文件不存在: {file_path}")

            # Read file content for persistence
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw_json = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"凭证文件 JSON 格式无效: {e}")

            if not isinstance(raw_json, dict):
                raise ValueError("凭证文件内容必须是 JSON 对象")

            # Store the file path so we can reload on restart
            raw_json["_creds_file_path"] = str(path)

            region = raw_json.get("region") or self._default_region

            # Use creds_file mode — KiroAuthManager handles everything
            auth_manager = KiroAuthManager(
                region=region,
                creds_file=str(path),
            )

            profile_id = uuid.uuid4().hex[:12]
            profile = CredentialProfile(
                profile_id=profile_id,
                name=name,
                auth_manager=auth_manager,
                enabled=True,
                raw_json=raw_json,
            )

            self._profiles.append(profile)
            self._save()

            logger.info(
                f"Credential profile added from file: id={profile_id}, name={name}, "
                f"file={file_path}, auth_type={auth_manager.auth_type.value}"
            )
            return profile

    def _build_auth_manager(self, credential_json: Dict[str, Any]) -> KiroAuthManager:
        """
        Build a KiroAuthManager from credential JSON.

        Handles two scenarios:
        1. ``_creds_file_path`` present → use ``creds_file`` mode (file-based profile reload)
        2. Otherwise → construct from individual fields (clientId/clientSecret
           are expected to be already merged from device registration by the API layer)

        Args:
            credential_json: Parsed credential dict.

        Returns:
            Configured KiroAuthManager instance.

        Raises:
            ValueError: If required fields are missing.
        """
        # --- Mode 1: reload from original file path (persisted profiles) ---
        creds_file_path = credential_json.get("_creds_file_path")
        if creds_file_path:
            path = Path(creds_file_path).expanduser()
            if path.exists():
                region = credential_json.get("region") or self._default_region
                return KiroAuthManager(region=region, creds_file=str(path))
            else:
                logger.warning(f"Saved creds_file_path no longer exists: {creds_file_path}, falling back to JSON fields")

        # --- Mode 2: construct from individual fields ---
        refresh_token = credential_json.get("refreshToken") or credential_json.get("refresh_token")
        if not refresh_token:
            raise ValueError("凭证 JSON 缺少 refreshToken 字段")

        region = (
            credential_json.get("region")
            or credential_json.get("ssoRegion")
            or self._default_region
        )
        profile_arn = credential_json.get("profileArn") or credential_json.get("profile_arn") or ""
        client_id = credential_json.get("clientId") or credential_json.get("client_id") or None
        client_secret = credential_json.get("clientSecret") or credential_json.get("client_secret") or None

        auth_manager = KiroAuthManager(
            refresh_token=refresh_token,
            profile_arn=profile_arn,
            region=region,
            client_id=client_id,
            client_secret=client_secret,
        )

        # If the pasted JSON has accessToken + expiresAt, set them directly
        # so the auth manager can use the existing token without refreshing
        access_token = credential_json.get("accessToken")
        if access_token:
            auth_manager._access_token = access_token

        expires_at_str = credential_json.get("expiresAt")
        if expires_at_str:
            try:
                if expires_at_str.endswith("Z"):
                    auth_manager._expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                else:
                    auth_manager._expires_at = datetime.fromisoformat(expires_at_str)
            except Exception as e:
                logger.warning(f"Failed to parse expiresAt: {e}")

        return auth_manager

    async def remove_profile(self, profile_id: str) -> bool:
        """
        Remove a credential profile by ID.

        Args:
            profile_id: The profile's unique identifier.

        Returns:
            True if the profile was found and removed, False otherwise.
        """
        async with self._lock:
            before = len(self._profiles)
            self._profiles = [p for p in self._profiles if p.id != profile_id]
            removed = len(self._profiles) < before

            if removed:
                self._save()
                logger.info(f"Credential profile removed: id={profile_id}")
            else:
                logger.warning(f"Credential profile not found for removal: id={profile_id}")

            return removed

    async def toggle_profile(self, profile_id: str, enabled: bool) -> bool:
        """
        Enable or disable a credential profile.

        Args:
            profile_id: The profile's unique identifier.
            enabled: New enabled state.

        Returns:
            True if the profile was found and updated, False otherwise.
        """
        async with self._lock:
            for profile in self._profiles:
                if profile.id == profile_id:
                    profile.enabled = enabled
                    self._save()
                    state = "enabled" if enabled else "disabled"
                    logger.info(f"Credential profile {state}: id={profile_id}")
                    return True

            logger.warning(f"Credential profile not found for toggle: id={profile_id}")
            return False

    async def validate_profile(self, profile_id: str) -> Dict[str, Any]:
        """
        Validate a credential profile by attempting to get an access token.

        Args:
            profile_id: The profile's unique identifier.

        Returns:
            Dict with 'valid' (bool) and 'message' (str) fields.
        """
        profile = self._get_profile_by_id(profile_id)
        if not profile:
            return {"valid": False, "message": "凭证配置不存在"}

        try:
            token = await profile.auth_manager.get_access_token()
            if token:
                return {"valid": True, "message": "凭证有效，连接成功"}
            return {"valid": False, "message": "获取 token 失败"}
        except ValueError as e:
            return {"valid": False, "message": f"凭证无效: {e}"}
        except Exception as e:
            return {"valid": False, "message": f"验证失败: {e}"}

    async def query_quota(self, profile_id: str) -> Dict[str, Any]:
        """
        Query quota/usage information for a credential profile.

        Calls Kiro API getUsageLimits endpoint to retrieve usage limits,
        current usage, and subscription information.

        Args:
            profile_id: The profile's unique identifier.

        Returns:
            Dict with quota information or error details.
        """
        profile = self._get_profile_by_id(profile_id)
        if not profile:
            return {"success": False, "message": "凭证配置不存在"}

        am = profile.auth_manager
        try:
            token = await am.get_access_token()
        except Exception as e:
            return {"success": False, "message": f"获取 token 失败: {e}"}

        from kiro.utils import get_kiro_headers
        headers = get_kiro_headers(am, token)

        result: Dict[str, Any] = {
            "success": True,
            "message": "查询成功",
            "auth_type": am.auth_type.value,
            "region": am.region,
            "usage": None,
        }

        # --- getUsageLimits ---
        try:
            usage_host = f"https://codewhisperer.{am.region}.amazonaws.com"
            params: Dict[str, str] = {
                "isEmailRequired": "true",
                "origin": "AI_EDITOR",
                "resourceType": "AGENTIC_REQUEST",
            }
            if am.profile_arn:
                params["profileArn"] = am.profile_arn

            async with httpx.AsyncClient(timeout=15, verify=SSL_VERIFY) as client:
                resp = await client.get(
                    f"{usage_host}/getUsageLimits",
                    headers=headers,
                    params=params,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    result["usage"] = data
                    logger.info(f"getUsageLimits succeeded for profile {profile_id}")
                else:
                    logger.warning(f"getUsageLimits returned {resp.status_code}: {resp.text}")
                    result["success"] = False
                    result["message"] = f"查询额度失败 (HTTP {resp.status_code})"
        except Exception as e:
            logger.warning(f"getUsageLimits failed: {e}")
            result["success"] = False
            result["message"] = f"查询额度失败: {e}"

        return result


    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def load(self) -> None:
        """
        Load credential profiles from the persistence file.

        Reconstructs KiroAuthManager instances from stored raw JSON.
        Profiles that fail to load are skipped with a warning.
        """
        if not self.credentials_file.exists():
            logger.info(f"No credentials file found at {self.credentials_file}, starting empty")
            return

        try:
            with open(self.credentials_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                logger.error("Credentials file is not a JSON array, ignoring")
                return

            loaded = 0
            for entry in data:
                try:
                    raw_json = entry.get("raw_json", {})

                    auth_manager = self._build_auth_manager(raw_json)

                    profile = CredentialProfile(
                        profile_id=entry["id"],
                        name=entry.get("name", "Unnamed"),
                        auth_manager=auth_manager,
                        enabled=entry.get("enabled", True),
                        created_at=entry.get("created_at"),
                        raw_json=raw_json,
                    )
                    self._profiles.append(profile)
                    loaded += 1
                except Exception as e:
                    logger.warning(f"Failed to load credential profile {entry.get('id', '?')}: {e}")

            logger.info(f"Loaded {loaded} credential profile(s) from {self.credentials_file}")

        except json.JSONDecodeError as e:
            logger.error(f"Credentials file is not valid JSON: {e}")
        except Exception as e:
            logger.error(f"Error loading credentials file: {e}")

    def _save(self) -> None:
        """
        Persist all profiles to the credentials file.

        Uses atomic write (temp file + rename) to prevent corruption.
        """
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)

        data = [p.to_dict() for p in self._profiles]
        temp_file = self.credentials_file.with_suffix(".json.tmp")

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic rename (Windows needs target removed first)
            if self.credentials_file.exists():
                self.credentials_file.unlink()
            temp_file.rename(self.credentials_file)

            logger.debug(f"Credentials saved: {len(data)} profile(s)")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            # Clean up temp file on failure
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_profile_by_id(self, profile_id: str) -> Optional[CredentialProfile]:
        """
        Find a profile by its unique ID.

        Args:
            profile_id: The profile's unique identifier.

        Returns:
            The matching CredentialProfile, or None.
        """
        for profile in self._profiles:
            if profile.id == profile_id:
                return profile
        return None

    def get_summary(self) -> List[Dict[str, Any]]:
        """
        Return a summary of all profiles for the admin API.

        Sensitive fields (tokens, secrets) are excluded.
        Includes per-profile usage statistics.

        Returns:
            List of profile summary dicts.
        """
        result = []
        for p in self._profiles:
            usage = self.get_profile_usage(p.id)
            result.append({
                "id": p.id,
                "name": p.name,
                "enabled": p.enabled,
                "auth_type": p.auth_type_label,
                "region": p.auth_manager.region,
                "created_at": p.created_at,
                "request_count": usage["request_count"],
                "last_used": usage["last_used"],
            })
        return result
