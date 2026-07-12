# -*- coding: utf-8 -*-

"""
Unit tests for kiro.model_loader.reload_model_cache.

These tests exercise the orchestration logic (union merge, fallback, per-source
error isolation, hidden-model re-add) with the network layer mocked out via
patching ``fetch_models_from_auth``. No real HTTP calls are made.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from kiro.cache import ModelInfoCache
from kiro import model_loader


FALLBACK = [{"modelId": "fallback-a"}, {"modelId": "fallback-b"}]
HIDDEN = {"hidden-x": "INTERNAL_X"}


def _profile(name, auth):
    """Build a stand-in credential profile exposing .name and .auth_manager."""
    return SimpleNamespace(name=name, auth_manager=auth)


def _cred_manager(profiles):
    """Build a stand-in credential manager exposing .enabled_profiles."""
    return SimpleNamespace(enabled_profiles=profiles)


@pytest.mark.asyncio
async def test_union_merge_and_hidden_readded():
    """Primary + profile models are merged (deduped) and hidden models re-added."""
    cache = ModelInfoCache()
    primary = SimpleNamespace(tag="primary")
    prof_auth = SimpleNamespace(tag="prof")

    async def fake_fetch(auth, ssl_verify, timeout=30.0):
        if auth is primary:
            return [{"modelId": "shared"}, {"modelId": "only-primary"}]
        return [{"modelId": "shared"}, {"modelId": "only-prof"}]  # 'shared' is a dupe

    with patch.object(model_loader, "fetch_models_from_auth", side_effect=fake_fetch):
        summary = await model_loader.reload_model_cache(
            model_cache=cache,
            auth_manager=primary,
            credential_manager=_cred_manager([_profile("teamB", prof_auth)]),
            hidden_models=HIDDEN,
            fallback_models=FALLBACK,
            ssl_verify=True,
            use_primary_auth=True,
        )

    ids = set(cache.get_all_model_ids())
    assert ids == {"shared", "only-primary", "only-prof", "hidden-x"}
    assert summary["sources"] == 2
    assert summary["errors"] == []
    assert summary["used_fallback"] is False
    assert summary["total"] == 4


@pytest.mark.asyncio
async def test_fallback_when_no_sources():
    """With no primary auth and no profiles, the fallback list is used."""
    cache = ModelInfoCache()

    with patch.object(model_loader, "fetch_models_from_auth") as mocked:
        summary = await model_loader.reload_model_cache(
            model_cache=cache,
            auth_manager=None,
            credential_manager=None,
            hidden_models=HIDDEN,
            fallback_models=FALLBACK,
            ssl_verify=True,
            use_primary_auth=False,
        )
        mocked.assert_not_called()

    ids = set(cache.get_all_model_ids())
    assert ids == {"fallback-a", "fallback-b", "hidden-x"}
    assert summary["used_fallback"] is True
    assert summary["sources"] == 0


@pytest.mark.asyncio
async def test_one_profile_failure_isolated():
    """A failing profile is recorded in errors but does not block healthy sources."""
    cache = ModelInfoCache()
    good_auth = SimpleNamespace(tag="good")
    bad_auth = SimpleNamespace(tag="bad")

    async def fake_fetch(auth, ssl_verify, timeout=30.0):
        if auth is bad_auth:
            raise RuntimeError("HTTP 403")
        return [{"modelId": "good-model"}]

    with patch.object(model_loader, "fetch_models_from_auth", side_effect=fake_fetch):
        summary = await model_loader.reload_model_cache(
            model_cache=cache,
            auth_manager=None,
            credential_manager=_cred_manager([
                _profile("good", good_auth),
                _profile("bad", bad_auth),
            ]),
            hidden_models={},
            fallback_models=FALLBACK,
            ssl_verify=True,
            use_primary_auth=False,
        )

    assert "good-model" in cache.get_all_model_ids()
    assert summary["sources"] == 1
    assert len(summary["errors"]) == 1
    assert "bad" in summary["errors"][0]
    assert summary["used_fallback"] is False


@pytest.mark.asyncio
async def test_primary_fails_but_profile_succeeds_no_fallback():
    """If the primary errors but a profile returns models, fallback is not used."""
    cache = ModelInfoCache()
    primary = SimpleNamespace(tag="primary")
    prof_auth = SimpleNamespace(tag="prof")

    async def fake_fetch(auth, ssl_verify, timeout=30.0):
        if auth is primary:
            raise RuntimeError("HTTP 500")
        return [{"modelId": "prof-model"}]

    with patch.object(model_loader, "fetch_models_from_auth", side_effect=fake_fetch):
        summary = await model_loader.reload_model_cache(
            model_cache=cache,
            auth_manager=primary,
            credential_manager=_cred_manager([_profile("teamB", prof_auth)]),
            hidden_models={},
            fallback_models=FALLBACK,
            ssl_verify=True,
            use_primary_auth=True,
        )

    assert set(cache.get_all_model_ids()) == {"prof-model"}
    assert summary["used_fallback"] is False
    assert summary["sources"] == 1
    assert len(summary["errors"]) == 1  # primary failure recorded
