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
Shared model-loading logic for Kiro Gateway.

Provides a single place to fetch the available model list from Kiro's
``/ListAvailableModels`` endpoint. Used both at startup (``main.py`` lifespan)
and by the admin panel's "refresh models" button so the two paths never drift.

The model list is the union of models available to every configured credential
source (the primary ``.env`` credential plus each enabled credential profile).
Credentials come from configuration files (``~/.kiro-gateway/credentials.json``,
Kiro IDE JSON, kiro-cli SQLite) — hence "get the latest model list from config".
"""

from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from kiro.auth import AuthType, KiroAuthManager
from kiro.cache import ModelInfoCache
from kiro.utils import get_kiro_headers


async def fetch_models_from_auth(
    auth_manager: KiroAuthManager,
    ssl_verify: Any,
    timeout: float = 30.0,
) -> List[Dict[str, Any]]:
    """Fetch the raw model list from Kiro ``/ListAvailableModels`` for one credential.

    Args:
        auth_manager: An authenticated Kiro auth manager to fetch models with.
        ssl_verify: httpx ``verify`` setting (``True``/``False`` or CA bundle path).
        timeout: Request timeout in seconds.

    Returns:
        List of model metadata dicts as returned by Kiro (each contains ``modelId``).

    Raises:
        RuntimeError: If Kiro API responds with a non-200 status.
        httpx.HTTPError: On network/transport failures.
    """
    token = await auth_manager.get_access_token()
    headers = get_kiro_headers(auth_manager, token)

    # profileArn is only meaningful for Kiro Desktop auth
    params: Dict[str, str] = {"origin": "AI_EDITOR"}
    if auth_manager.auth_type == AuthType.KIRO_DESKTOP and auth_manager.profile_arn:
        params["profileArn"] = auth_manager.profile_arn

    url = f"{auth_manager.q_host}/ListAvailableModels"
    logger.debug(f"Fetching models from: {url}")

    async with httpx.AsyncClient(timeout=timeout, verify=ssl_verify) as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}")
        return response.json().get("models", [])


async def reload_model_cache(
    *,
    model_cache: ModelInfoCache,
    auth_manager: Optional[KiroAuthManager],
    credential_manager: Any,
    hidden_models: Dict[str, str],
    fallback_models: List[Dict[str, Any]],
    ssl_verify: Any,
    use_primary_auth: bool,
) -> Dict[str, Any]:
    """Rebuild the model cache from every configured credential source.

    Fetches the union of models available to the primary (``.env``) credential and
    each enabled credential profile, then replaces the cache contents. Falls back to
    the built-in list when no source returns any models. Hidden models are always
    re-added afterwards (``ModelInfoCache.update`` replaces the whole cache).

    Args:
        model_cache: The cache instance to rebuild.
        auth_manager: Primary auth manager, or ``None`` if unavailable.
        credential_manager: ``CredentialManager`` with extra profiles, or ``None``.
        hidden_models: Mapping of hidden display name -> internal id to re-add.
        fallback_models: Built-in model list used when no source succeeds.
        ssl_verify: httpx ``verify`` setting.
        use_primary_auth: Whether the primary auth manager has real credentials.

    Returns:
        Summary dict with keys:
            ``total`` (int): total models in cache after reload,
            ``sources`` (int): number of credential sources that succeeded,
            ``errors`` (list[str]): per-source error messages,
            ``used_fallback`` (bool): whether the fallback list was used.
    """
    collected: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []
    sources = 0

    # --- Primary (.env) credential ---
    if use_primary_auth and auth_manager is not None:
        try:
            models = await fetch_models_from_auth(auth_manager, ssl_verify)
            for model in models:
                model_id = model.get("modelId")
                if model_id:
                    collected[model_id] = model
            sources += 1
            logger.debug(f"Fetched {len(models)} models from primary credential")
        except Exception as e:  # noqa: BLE001 - report every source, never abort reload
            errors.append(f"主凭证: {e}")
            logger.error(f"Failed to fetch models from primary credential: {e}")

    # --- Extra credential profiles (union, additive) ---
    if credential_manager is not None:
        for profile in credential_manager.enabled_profiles:
            try:
                models = await fetch_models_from_auth(profile.auth_manager, ssl_verify)
                for model in models:
                    model_id = model.get("modelId")
                    if model_id and model_id not in collected:
                        collected[model_id] = model
                sources += 1
                logger.info(f"Merged {len(models)} models from credential '{profile.name}'")
            except Exception as e:  # noqa: BLE001 - one bad profile must not block others
                errors.append(f"{profile.name}: {e}")
                logger.warning(f"Failed to fetch models for credential '{profile.name}': {e}")

    # --- Fallback when nothing was fetched ---
    used_fallback = False
    if not collected:
        used_fallback = True
        for model in fallback_models:
            model_id = model.get("modelId")
            if model_id:
                collected[model_id] = model
        logger.warning(
            "No models fetched from any credential; using pre-configured fallback list"
        )

    await model_cache.update(list(collected.values()))

    # Re-add hidden models — update() replaced the entire cache above
    for display_name, internal_id in hidden_models.items():
        model_cache.add_hidden_model(display_name, internal_id)

    total = len(model_cache.get_all_model_ids())
    logger.info(f"Model cache reloaded: {total} models total from {sources} source(s)")

    return {
        "total": total,
        "sources": sources,
        "errors": errors,
        "used_fallback": used_fallback,
    }
