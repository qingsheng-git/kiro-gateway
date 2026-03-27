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
FastAPI routes for the Admin Panel.

Contains endpoints for the web-based administration interface:
- GET /admin: Admin panel HTML page (no auth required)
- GET /admin/api/models: Available models list
- GET /admin/api/aliases: Current alias mappings
- POST /admin/api/aliases: Create new alias mapping
- DELETE /admin/api/aliases/{alias_name}: Delete alias mapping
- GET /admin/api/credentials: List credential profiles
- POST /admin/api/credentials: Add new credential profile
- DELETE /admin/api/credentials/{profile_id}: Remove credential profile
- PUT /admin/api/credentials/{profile_id}/toggle: Enable/disable profile
- POST /admin/api/credentials/{profile_id}/validate: Validate profile
"""

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from loguru import logger
from pydantic import BaseModel

from kiro.admin_html import get_admin_html
from kiro.config import APP_VERSION, HIDDEN_FROM_LIST, HIDDEN_MODELS, PROXY_API_KEY


# --- Pydantic Models ---


class AliasCreateRequest(BaseModel):
    """Request body for creating an alias mapping.

    Attributes:
        alias_name: User-defined alias name (e.g. "my-opus").
        real_model_id: Target Kiro model ID (e.g. "claude-opus-4.5").
    """

    alias_name: str
    real_model_id: str


class AliasResponse(BaseModel):
    """Single alias mapping in API responses.

    Attributes:
        alias_name: The alias name.
        real_model_id: The target model ID the alias maps to.
    """

    alias_name: str
    real_model_id: str


class CredentialCreateRequest(BaseModel):
    """Request body for adding a new credential profile.

    Supports two modes:
    1. Paste JSON: provide ``credential_json`` with the credential content.
       For Enterprise Kiro IDE, also provide ``device_registration_json``
       with the device registration file content (contains clientId/clientSecret).
    2. File path: provide ``credential_file`` with the path to a credential file.

    At least one of ``credential_json`` or ``credential_file`` must be provided.

    Attributes:
        name: Human-readable display name for the profile.
        credential_json: Raw JSON string containing Kiro credentials (mode 1).
        device_registration_json: Raw JSON string from the device registration file
            (Enterprise Kiro IDE only, contains clientId and clientSecret).
        credential_file: Path to a credential JSON file on disk (mode 2).
    """

    name: str
    credential_json: Optional[str] = None
    device_registration_json: Optional[str] = None
    credential_file: Optional[str] = None


class CredentialToggleRequest(BaseModel):
    """Request body for enabling/disabling a credential profile.

    Attributes:
        enabled: New enabled state.
    """

    enabled: bool


class ApiResponse(BaseModel):
    """Standard API response wrapper.

    All admin API endpoints return responses in this format to ensure
    consistency (Property 9: response format consistency).

    Attributes:
        success: Whether the operation succeeded.
        message: Human-readable result description.
        data: Optional payload (list of aliases, models, etc.).
    """

    success: bool
    message: str
    data: Optional[Any] = None


# --- Authentication ---


async def verify_admin_api_key(request: Request) -> bool:
    """Verify API key for admin API endpoints.

    Supports two authentication methods for flexibility with browser-based
    JS fetch calls and CLI/automation tools:
    1. Authorization: Bearer {PROXY_API_KEY}
    2. X-API-Key: {PROXY_API_KEY}

    Args:
        request: The incoming FastAPI request.

    Returns:
        True if the key is valid.

    Raises:
        HTTPException: 401 if the key is invalid or missing.
    """
    # Try Authorization: Bearer header first
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header == f"Bearer {PROXY_API_KEY}":
        return True

    # Fall back to X-API-Key header
    x_api_key = request.headers.get("x-api-key")
    if x_api_key and x_api_key == PROXY_API_KEY:
        return True

    logger.warning("Admin panel access attempt with invalid API key")
    raise HTTPException(status_code=401, detail="Invalid or missing API Key")


# --- Router ---

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("", response_class=HTMLResponse)
async def get_admin_page() -> HTMLResponse:
    """Return the admin panel HTML page.

    This endpoint does not require authentication — the page itself is
    public so browsers can load it directly. All data-fetching API calls
    made by the page's JavaScript require a valid API key.

    Returns:
        HTMLResponse with a placeholder admin page.
    """
    return HTMLResponse(content=get_admin_html(APP_VERSION))

@admin_router.get("/api/models", response_model=ApiResponse)
async def get_available_models(
    request: Request,
    _auth: bool = Depends(verify_admin_api_key),
) -> ApiResponse:
    """Return the list of available models for the admin panel.

    Combines models from three sources:
    1. Dynamic cache (``app.state.model_cache``) — models fetched from Kiro API
    2. Hidden models (``HIDDEN_MODELS``) — undocumented but functional models
    Then filters out models listed in ``HIDDEN_FROM_LIST``.

    The result is a sorted, deduplicated list of model display names that the
    admin UI can present in its "target model" dropdown.

    Args:
        request: The incoming FastAPI request (used to access ``app.state``).
        _auth: Injected by ``verify_admin_api_key`` dependency.

    Returns:
        ApiResponse with ``data`` containing a sorted list of model ID strings.
    """
    model_cache: "ModelInfoCache" = request.app.state.model_cache  # noqa: F821

    # Collect model IDs from cache
    models: set[str] = set(model_cache.get_all_model_ids())

    # Merge hidden model display names
    models.update(HIDDEN_MODELS.keys())

    # Exclude models that should be hidden from the list
    models -= set(HIDDEN_FROM_LIST)

    sorted_models = sorted(models)
    logger.debug(f"Admin API: returning {len(sorted_models)} available models")

    return ApiResponse(success=True, message="ok", data=sorted_models)

@admin_router.get("/api/aliases", response_model=ApiResponse)
async def get_aliases(
    request: Request,
    _auth: bool = Depends(verify_admin_api_key),
) -> ApiResponse:
    """Return all current alias mappings.

    Reads the live alias dictionary from ``ModelResolver`` and returns it
    as a list of ``{alias_name, real_model_id}`` objects.

    Args:
        request: The incoming FastAPI request (used to access ``app.state``).
        _auth: Injected by ``verify_admin_api_key`` dependency.

    Returns:
        ApiResponse with ``data`` containing a list of alias mapping dicts.
    """
    model_resolver = request.app.state.model_resolver
    aliases: dict[str, str] = model_resolver.aliases

    data = [
        {"alias_name": alias, "real_model_id": real_id}
        for alias, real_id in sorted(aliases.items())
    ]

    logger.debug(f"Admin API: returning {len(data)} alias mapping(s)")
    return ApiResponse(success=True, message="ok", data=data)


@admin_router.post("/api/aliases", response_model=ApiResponse)
async def create_alias(
    request: Request,
    body: AliasCreateRequest,
    _auth: bool = Depends(verify_admin_api_key),
) -> ApiResponse:
    """Create a new alias mapping.

    Validates the alias name, persists the mapping via ``SettingsManager``,
    and updates ``ModelResolver`` so the alias takes effect immediately.

    Validation rules:
    - Empty / whitespace-only alias → 400
    - Alias already exists → 409
    - Alias collides with an available model name → success with warning

    Args:
        request: The incoming FastAPI request (used to access ``app.state``).
        body: ``AliasCreateRequest`` with ``alias_name`` and ``real_model_id``.
        _auth: Injected by ``verify_admin_api_key`` dependency.

    Returns:
        ApiResponse indicating success (possibly with a warning message).

    Raises:
        HTTPException: 400 if alias is blank, 409 if alias already exists.
    """
    alias_name = body.alias_name.strip()
    real_model_id = body.real_model_id

    # --- Validation: empty / whitespace-only ---
    if not alias_name:
        raise HTTPException(status_code=400, detail="别名不能为空")

    model_resolver = request.app.state.model_resolver
    aliases: dict[str, str] = model_resolver.aliases

    # --- Validation: duplicate ---
    if alias_name in aliases:
        raise HTTPException(status_code=409, detail="别名已存在")

    # --- Check for conflict with available models ---
    model_cache = request.app.state.model_cache
    available_models: set[str] = set(model_cache.get_all_model_ids())
    available_models.update(HIDDEN_MODELS.keys())

    warning = ""
    if alias_name in available_models:
        warning = "该别名与现有模型名称冲突，可能导致原模型无法直接访问"
        logger.warning(f"Alias '{alias_name}' conflicts with an available model name")

    # --- Persist ---
    new_aliases = {**aliases, alias_name: real_model_id}
    model_resolver.update_aliases(new_aliases)

    settings_manager = request.app.state.settings_manager
    settings = settings_manager.load()
    settings.model_aliases = new_aliases
    settings_manager.save(settings)

    message = f"别名 '{alias_name}' 已创建"
    if warning:
        message = f"{message}（警告：{warning}）"

    logger.info(f"Alias created: {alias_name} → {real_model_id}")
    return ApiResponse(success=True, message=message)


@admin_router.delete("/api/aliases/{alias_name}", response_model=ApiResponse)
async def delete_alias(
    request: Request,
    alias_name: str,
    _auth: bool = Depends(verify_admin_api_key),
) -> ApiResponse:
    """Delete an existing alias mapping.

    Removes the alias from ``ModelResolver`` and persists the change via
    ``SettingsManager``.

    Args:
        request: The incoming FastAPI request (used to access ``app.state``).
        alias_name: The alias to delete (from the URL path).
        _auth: Injected by ``verify_admin_api_key`` dependency.

    Returns:
        ApiResponse confirming deletion.

    Raises:
        HTTPException: 404 if the alias does not exist.
    """
    model_resolver = request.app.state.model_resolver
    aliases: dict[str, str] = model_resolver.aliases

    if alias_name not in aliases:
        raise HTTPException(
            status_code=404,
            detail=f"别名 '{alias_name}' 不存在",
        )

    new_aliases = {k: v for k, v in aliases.items() if k != alias_name}
    model_resolver.update_aliases(new_aliases)

    settings_manager = request.app.state.settings_manager
    settings = settings_manager.load()
    settings.model_aliases = new_aliases
    settings_manager.save(settings)

    logger.info(f"Alias deleted: {alias_name}")
    return ApiResponse(success=True, message=f"别名 '{alias_name}' 已删除")


# =============================================================================
# Credential Management Endpoints
# =============================================================================


@admin_router.get("/api/credentials", response_model=ApiResponse)
async def list_credentials(
    request: Request,
    _auth: bool = Depends(verify_admin_api_key),
) -> ApiResponse:
    """Return all credential profiles (without sensitive data).

    Args:
        request: The incoming FastAPI request.
        _auth: Injected by ``verify_admin_api_key`` dependency.

    Returns:
        ApiResponse with ``data`` containing a list of profile summaries.
    """
    credential_manager = getattr(request.app.state, "credential_manager", None)
    if credential_manager is None:
        return ApiResponse(success=True, message="ok", data=[])

    data = credential_manager.get_summary()
    logger.debug(f"Admin API: returning {len(data)} credential profile(s)")
    return ApiResponse(success=True, message="ok", data=data)


@admin_router.post("/api/credentials", response_model=ApiResponse)
async def add_credential(
    request: Request,
    body: CredentialCreateRequest,
    _auth: bool = Depends(verify_admin_api_key),
) -> ApiResponse:
    """Add a new credential profile from pasted JSON or file path.

    Supports two modes:
    1. ``credential_json``: Paste the JSON content directly.
    2. ``credential_file``: Provide a file path (e.g. ~/.aws/sso/cache/xxx.json).
       This is recommended for Enterprise Kiro IDE credentials that use
       clientIdHash → device registration files.

    Args:
        request: The incoming FastAPI request.
        body: ``CredentialCreateRequest`` with name and credential source.
        _auth: Injected by ``verify_admin_api_key`` dependency.

    Returns:
        ApiResponse with the new profile summary in ``data``.

    Raises:
        HTTPException: 400 if name is empty, JSON is invalid, or required fields are missing.
    """
    credential_manager = getattr(request.app.state, "credential_manager", None)
    if credential_manager is None:
        raise HTTPException(status_code=500, detail="凭证管理器未初始化")

    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="配置名称不能为空")

    has_json = body.credential_json and body.credential_json.strip()
    has_file = body.credential_file and body.credential_file.strip()

    if not has_json and not has_file:
        raise HTTPException(status_code=400, detail="请提供凭证 JSON 或凭证文件路径")

    try:
        if has_file:
            # File path mode — KiroAuthManager handles clientIdHash etc.
            profile = await credential_manager.add_profile_from_file(name, body.credential_file.strip())
        else:
            # Pasted JSON mode
            try:
                cred_data = json.loads(body.credential_json)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"凭证 JSON 格式无效: {e}")

            if not isinstance(cred_data, dict):
                raise HTTPException(status_code=400, detail="凭证 JSON 必须是一个对象")

            # Merge device registration JSON for Enterprise Kiro IDE
            has_device_reg = body.device_registration_json and body.device_registration_json.strip()
            if has_device_reg:
                try:
                    device_data = json.loads(body.device_registration_json)
                except json.JSONDecodeError as e:
                    raise HTTPException(status_code=400, detail=f"设备注册 JSON 格式无效: {e}")

                if not isinstance(device_data, dict):
                    raise HTTPException(status_code=400, detail="设备注册 JSON 必须是一个对象")

                # Merge clientId and clientSecret into credential data
                if "clientId" in device_data:
                    cred_data["clientId"] = device_data["clientId"]
                if "clientSecret" in device_data:
                    cred_data["clientSecret"] = device_data["clientSecret"]

                logger.debug("Merged device registration into credential JSON")

            profile = await credential_manager.add_profile(name, cred_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    summary = {
        "id": profile.id,
        "name": profile.name,
        "enabled": profile.enabled,
        "auth_type": profile.auth_type_label,
        "region": profile.auth_manager.region,
        "created_at": profile.created_at,
    }

    logger.info(f"Credential profile created via admin API: {profile.id} ({name})")
    return ApiResponse(success=True, message=f"凭证 '{name}' 已添加", data=summary)


@admin_router.delete("/api/credentials/{profile_id}", response_model=ApiResponse)
async def remove_credential(
    request: Request,
    profile_id: str,
    _auth: bool = Depends(verify_admin_api_key),
) -> ApiResponse:
    """Remove a credential profile by ID.

    Args:
        request: The incoming FastAPI request.
        profile_id: The profile's unique identifier (from URL path).
        _auth: Injected by ``verify_admin_api_key`` dependency.

    Returns:
        ApiResponse confirming deletion.

    Raises:
        HTTPException: 404 if the profile does not exist.
    """
    credential_manager = getattr(request.app.state, "credential_manager", None)
    if credential_manager is None:
        raise HTTPException(status_code=500, detail="凭证管理器未初始化")

    removed = await credential_manager.remove_profile(profile_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"凭证配置 '{profile_id}' 不存在")

    logger.info(f"Credential profile removed via admin API: {profile_id}")
    return ApiResponse(success=True, message="凭证已删除")


@admin_router.put("/api/credentials/{profile_id}/toggle", response_model=ApiResponse)
async def toggle_credential(
    request: Request,
    profile_id: str,
    body: CredentialToggleRequest,
    _auth: bool = Depends(verify_admin_api_key),
) -> ApiResponse:
    """Enable or disable a credential profile.

    Args:
        request: The incoming FastAPI request.
        profile_id: The profile's unique identifier (from URL path).
        body: ``CredentialToggleRequest`` with the new enabled state.
        _auth: Injected by ``verify_admin_api_key`` dependency.

    Returns:
        ApiResponse confirming the state change.

    Raises:
        HTTPException: 404 if the profile does not exist.
    """
    credential_manager = getattr(request.app.state, "credential_manager", None)
    if credential_manager is None:
        raise HTTPException(status_code=500, detail="凭证管理器未初始化")

    updated = await credential_manager.toggle_profile(profile_id, body.enabled)
    if not updated:
        raise HTTPException(status_code=404, detail=f"凭证配置 '{profile_id}' 不存在")

    state = "已启用" if body.enabled else "已禁用"
    return ApiResponse(success=True, message=f"凭证{state}")


@admin_router.post("/api/credentials/{profile_id}/validate", response_model=ApiResponse)
async def validate_credential(
    request: Request,
    profile_id: str,
    _auth: bool = Depends(verify_admin_api_key),
) -> ApiResponse:
    """Validate a credential profile by attempting token refresh.

    Args:
        request: The incoming FastAPI request.
        profile_id: The profile's unique identifier (from URL path).
        _auth: Injected by ``verify_admin_api_key`` dependency.

    Returns:
        ApiResponse with validation result in ``data``.
    """
    credential_manager = getattr(request.app.state, "credential_manager", None)
    if credential_manager is None:
        raise HTTPException(status_code=500, detail="凭证管理器未初始化")

    result = await credential_manager.validate_profile(profile_id)
    return ApiResponse(
        success=result["valid"],
        message=result["message"],
        data=result,
    )


@admin_router.post("/api/credentials/{profile_id}/quota", response_model=ApiResponse)
async def query_credential_quota(
    request: Request,
    profile_id: str,
    _auth: bool = Depends(verify_admin_api_key),
) -> ApiResponse:
    """Query quota and usage information for a credential profile.

    Calls Kiro API to retrieve subscription tier, available models,
    and token limits for the given credential profile.

    Args:
        request: The incoming FastAPI request.
        profile_id: The profile's unique identifier (from URL path).
        _auth: Injected by ``verify_admin_api_key`` dependency.

    Returns:
        ApiResponse with quota information in ``data``.
    """
    credential_manager = getattr(request.app.state, "credential_manager", None)
    if credential_manager is None:
        raise HTTPException(status_code=500, detail="凭证管理器未初始化")

    result = await credential_manager.query_quota(profile_id)
    return ApiResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        data=result,
    )


