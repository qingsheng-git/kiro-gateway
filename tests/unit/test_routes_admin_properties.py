# -*- coding: utf-8 -*-

"""
Property-based tests for Admin Panel API routes.

Uses Hypothesis to verify correctness properties defined in the design document
for the web-admin-panel feature. All tests are network-isolated and use the
FastAPI TestClient with mocked SettingsManager.

Properties tested:
- Property 1: 认证门控 (Authentication gating)
- Property 2: 别名 CRUD 往返 (Alias CRUD round-trip)
- Property 3: ModelResolver 实时反映别名变更 (ModelResolver reflects changes)
- Property 5: 重复别名拒绝 (Duplicate alias rejection)
- Property 6: 空白别名拒绝 (Whitespace alias rejection)
- Property 7: 模型名称冲突警告 (Model name conflict warning)
- Property 8: 可用模型列表完整性 (Available models completeness)
- Property 9: 成功响应格式一致性 (Success response format consistency)
"""

import pytest
from unittest.mock import Mock

from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st

from kiro.config import PROXY_API_KEY, HIDDEN_MODELS, HIDDEN_FROM_LIST
from kiro.settings_manager import TraySettings


# =============================================================================
# Strategies
# =============================================================================

# Valid alias names: ASCII letters, digits, hyphens, underscores — URL-safe
valid_alias_names = st.from_regex(r"[A-Za-z0-9][A-Za-z0-9_\-\.]{0,39}", fullmatch=True)

# Model IDs: simple ASCII identifiers
valid_model_ids = st.from_regex(r"[A-Za-z0-9][A-Za-z0-9_\-\.]{0,59}", fullmatch=True)

# Random API keys: ASCII-only printable (httpx headers require ASCII)
random_api_keys = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126),
    min_size=0,
    max_size=80,
)

# Whitespace-only strings for blank alias testing
whitespace_strings = st.from_regex(r"[\s\t\n\r ]{0,20}", fullmatch=True)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def admin_test_client(test_client):
    """Extend the standard test_client with a mock SettingsManager on app.state.

    Also saves and restores the original resolver aliases so that Hypothesis
    examples don't leak state into each other.

    Yields:
        The same TestClient, but with ``app.state.settings_manager`` set.
    """
    mock_sm = Mock()
    mock_sm.load.return_value = TraySettings()
    mock_sm.save.return_value = None

    test_client.app.state.settings_manager = mock_sm

    # Snapshot original aliases so we can restore after the test
    resolver = test_client.app.state.model_resolver
    original_aliases = dict(resolver.aliases)

    yield test_client

    # Restore original aliases to prevent state leakage
    resolver.update_aliases(dict(original_aliases))


def _auth_headers() -> dict:
    """Return valid Bearer auth headers."""
    return {"Authorization": f"Bearer {PROXY_API_KEY}"}


def _reset_aliases(client, original: dict) -> None:
    """Reset resolver aliases to a known state."""
    client.app.state.model_resolver.update_aliases(dict(original))


# =============================================================================
# Property 1: 认证门控
# =============================================================================


class TestAuthGating:
    """
    Feature: web-admin-panel, Property 1: 认证门控

    For any admin API endpoint, a valid PROXY_API_KEY yields 2xx,
    while an invalid or missing key yields 401.

    **Validates: Requirements 1.4, 1.5**
    """

    ENDPOINTS = [
        ("GET", "/admin/api/models"),
        ("GET", "/admin/api/aliases"),
    ]

    @given(api_key=random_api_keys)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_key_returns_401(self, api_key, admin_test_client):
        """
        Any API key that does not match PROXY_API_KEY must be rejected with 401.

        **Validates: Requirements 1.4, 1.5**
        """
        assume(api_key != PROXY_API_KEY)

        for method, path in self.ENDPOINTS:
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = admin_test_client.get(path, headers=headers)
            assert resp.status_code == 401

        # POST /admin/api/aliases
        resp = admin_test_client.post(
            "/admin/api/aliases",
            json={"alias_name": "test", "real_model_id": "test"},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp.status_code == 401

        # DELETE /admin/api/aliases/test
        resp = admin_test_client.delete(
            "/admin/api/aliases/test",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp.status_code == 401

    @given(api_key=random_api_keys)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_missing_auth_returns_401(self, api_key, admin_test_client):
        """
        Requests with no auth headers at all must be rejected with 401.

        **Validates: Requirements 1.4, 1.5**
        """
        for _, path in self.ENDPOINTS:
            resp = admin_test_client.get(path)
            assert resp.status_code == 401

        resp = admin_test_client.post(
            "/admin/api/aliases",
            json={"alias_name": "test", "real_model_id": "test"},
        )
        assert resp.status_code == 401

        resp = admin_test_client.delete("/admin/api/aliases/test")
        assert resp.status_code == 401

    def test_valid_key_returns_2xx(self, admin_test_client):
        """
        The correct PROXY_API_KEY must be accepted (2xx) on all endpoints.

        **Validates: Requirements 1.4, 1.5**
        """
        headers = _auth_headers()
        resolver = admin_test_client.app.state.model_resolver
        original = dict(resolver.aliases)

        resp = admin_test_client.get("/admin/api/models", headers=headers)
        assert 200 <= resp.status_code < 300

        resp = admin_test_client.get("/admin/api/aliases", headers=headers)
        assert 200 <= resp.status_code < 300

        # POST with valid data
        resp = admin_test_client.post(
            "/admin/api/aliases",
            json={"alias_name": "prop1-test", "real_model_id": "some-model"},
            headers=headers,
        )
        assert 200 <= resp.status_code < 300

        # DELETE (404 is expected for non-existent, but auth passes)
        resp = admin_test_client.delete(
            "/admin/api/aliases/nonexistent-alias",
            headers=headers,
        )
        # 404 means auth passed but alias not found — still not 401
        assert resp.status_code != 401

        _reset_aliases(admin_test_client, original)


# =============================================================================
# Property 2: 别名 CRUD 往返
# =============================================================================


class TestAliasCrudRoundTrip:
    """
    Feature: web-admin-panel, Property 2: 别名 CRUD 往返

    For any valid alias name and model ID, POST creates the mapping,
    GET contains it, DELETE removes it, and GET no longer contains it.

    **Validates: Requirements 4.3, 5.3, 3.1, 8.2, 8.3, 8.4**
    """

    @given(alias_name=valid_alias_names, model_id=valid_model_ids)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_create_read_delete_roundtrip(self, alias_name, model_id, admin_test_client):
        """
        POST → GET contains → DELETE → GET does not contain.

        **Validates: Requirements 4.3, 5.3, 3.1, 8.2, 8.3, 8.4**
        """
        headers = _auth_headers()
        resolver = admin_test_client.app.state.model_resolver
        original = dict(resolver.aliases)

        # Ensure clean state for this alias
        assume(alias_name not in original)

        try:
            # CREATE
            resp = admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": alias_name, "real_model_id": model_id},
                headers=headers,
            )
            assert resp.status_code == 200
            assert resp.json()["success"] is True

            # READ — alias must be present
            resp = admin_test_client.get("/admin/api/aliases", headers=headers)
            assert resp.status_code == 200
            aliases_list = resp.json()["data"]
            alias_names_list = [a["alias_name"] for a in aliases_list]
            assert alias_name in alias_names_list

            # Verify target model
            mapping = next(a for a in aliases_list if a["alias_name"] == alias_name)
            assert mapping["real_model_id"] == model_id

            # DELETE
            resp = admin_test_client.delete(
                f"/admin/api/aliases/{alias_name}",
                headers=headers,
            )
            assert resp.status_code == 200

            # READ — alias must be gone
            resp = admin_test_client.get("/admin/api/aliases", headers=headers)
            assert resp.status_code == 200
            aliases_list = resp.json()["data"]
            alias_names_list = [a["alias_name"] for a in aliases_list]
            assert alias_name not in alias_names_list

        finally:
            _reset_aliases(admin_test_client, original)


# =============================================================================
# Property 3: ModelResolver 实时反映别名变更
# =============================================================================


class TestModelResolverReflectsChanges:
    """
    Feature: web-admin-panel, Property 3: ModelResolver 实时反映别名变更

    After POST, resolver.resolve(alias_name) returns the target model.
    After DELETE, resolver no longer resolves to that target.

    **Validates: Requirements 4.4, 5.4**
    """

    @given(alias_name=valid_alias_names, model_id=valid_model_ids)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_resolver_reflects_create_and_delete(self, alias_name, model_id, admin_test_client):
        """
        ModelResolver immediately reflects alias creation and deletion.

        **Validates: Requirements 4.4, 5.4**
        """
        headers = _auth_headers()
        resolver = admin_test_client.app.state.model_resolver
        original = dict(resolver.aliases)

        assume(alias_name not in original)

        try:
            # CREATE alias via API
            resp = admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": alias_name, "real_model_id": model_id},
                headers=headers,
            )
            assert resp.status_code == 200

            # Resolver must now map alias_name → model_id
            assert alias_name in resolver.aliases
            assert resolver.aliases[alias_name] == model_id

            # DELETE alias via API
            resp = admin_test_client.delete(
                f"/admin/api/aliases/{alias_name}",
                headers=headers,
            )
            assert resp.status_code == 200

            # Resolver must no longer contain the alias
            assert alias_name not in resolver.aliases

        finally:
            _reset_aliases(admin_test_client, original)


# =============================================================================
# Property 5: 重复别名拒绝
# =============================================================================


class TestDuplicateAliasRejection:
    """
    Feature: web-admin-panel, Property 5: 重复别名拒绝

    Creating an alias that already exists returns 409 and the original
    mapping remains unchanged.

    **Validates: Requirements 4.5**
    """

    @given(alias_name=valid_alias_names, model_id=valid_model_ids, other_model=valid_model_ids)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_duplicate_alias_returns_409(self, alias_name, model_id, other_model, admin_test_client):
        """
        Second POST with same alias_name returns 409; original mapping intact.

        **Validates: Requirements 4.5**
        """
        headers = _auth_headers()
        resolver = admin_test_client.app.state.model_resolver
        original = dict(resolver.aliases)

        assume(alias_name not in original)

        try:
            # First create
            resp = admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": alias_name, "real_model_id": model_id},
                headers=headers,
            )
            assert resp.status_code == 200

            # Duplicate create
            resp = admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": alias_name, "real_model_id": other_model},
                headers=headers,
            )
            assert resp.status_code == 409

            # Original mapping unchanged
            assert resolver.aliases[alias_name] == model_id

        finally:
            _reset_aliases(admin_test_client, original)


# =============================================================================
# Property 6: 空白别名拒绝
# =============================================================================


class TestWhitespaceAliasRejection:
    """
    Feature: web-admin-panel, Property 6: 空白别名拒绝

    Whitespace-only or empty alias names are rejected with 400 and the
    alias list remains unchanged.

    **Validates: Requirements 4.6**
    """

    @given(blank=whitespace_strings)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_whitespace_alias_returns_400(self, blank, admin_test_client):
        """
        Whitespace-only strings as alias_name yield 400; alias list unchanged.

        **Validates: Requirements 4.6**
        """
        headers = _auth_headers()
        resolver = admin_test_client.app.state.model_resolver

        # Snapshot current aliases
        aliases_before = dict(resolver.aliases)

        resp = admin_test_client.post(
            "/admin/api/aliases",
            json={"alias_name": blank, "real_model_id": "some-model"},
            headers=headers,
        )
        assert resp.status_code == 400

        # Aliases unchanged
        assert resolver.aliases == aliases_before


# =============================================================================
# Property 7: 模型名称冲突警告
# =============================================================================


class TestModelNameConflictWarning:
    """
    Feature: web-admin-panel, Property 7: 模型名称冲突警告

    Using an available model name as an alias succeeds but the response
    message contains a warning (警告).

    **Validates: Requirements 4.7**
    """

    @given(model_id=valid_model_ids)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_conflict_alias_contains_warning(self, model_id, admin_test_client):
        """
        Alias matching an available model name → success with '警告' in message.

        **Validates: Requirements 4.7**
        """
        headers = _auth_headers()
        cache = admin_test_client.app.state.model_cache
        resolver = admin_test_client.app.state.model_resolver
        original = dict(resolver.aliases)

        # Pick an actual available model name from the cache
        available = set(cache.get_all_model_ids()) | set(HIDDEN_MODELS.keys())
        assume(len(available) > 0)

        # Use the first available model name as the alias
        conflict_name = sorted(available)[0]
        assume(conflict_name not in original)

        try:
            resp = admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": conflict_name, "real_model_id": model_id},
                headers=headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert "警告" in data["message"]

        finally:
            _reset_aliases(admin_test_client, original)


# =============================================================================
# Property 8: 可用模型列表完整性
# =============================================================================


class TestAvailableModelsCompleteness:
    """
    Feature: web-admin-panel, Property 8: 可用模型列表完整性

    GET /admin/api/models returns all cache models + hidden models
    minus HIDDEN_FROM_LIST.

    **Validates: Requirements 3.4, 8.1**
    """

    @given(data=st.data())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_models_endpoint_completeness(self, data, admin_test_client):
        """
        The models endpoint returns (cache ∪ HIDDEN_MODELS) - HIDDEN_FROM_LIST.

        **Validates: Requirements 3.4, 8.1**
        """
        headers = _auth_headers()
        cache = admin_test_client.app.state.model_cache

        # Compute expected set
        expected = set(cache.get_all_model_ids())
        expected.update(HIDDEN_MODELS.keys())
        expected -= set(HIDDEN_FROM_LIST)

        resp = admin_test_client.get("/admin/api/models", headers=headers)
        assert resp.status_code == 200

        returned = set(resp.json()["data"])

        assert expected == returned


# =============================================================================
# Property 9: 成功响应格式一致性
# =============================================================================


class TestSuccessResponseFormatConsistency:
    """
    Feature: web-admin-panel, Property 9: 成功响应格式一致性

    All successful operations return JSON with success=true and a message field.

    **Validates: Requirements 8.5**
    """

    @given(alias_name=valid_alias_names, model_id=valid_model_ids)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_all_success_responses_have_correct_format(
        self, alias_name, model_id, admin_test_client
    ):
        """
        Every 2xx response contains {success: true, message: <str>}.

        **Validates: Requirements 8.5**
        """
        headers = _auth_headers()
        resolver = admin_test_client.app.state.model_resolver
        original = dict(resolver.aliases)

        assume(alias_name not in original)

        try:
            # GET /admin/api/models
            resp = admin_test_client.get("/admin/api/models", headers=headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert isinstance(body["message"], str)

            # GET /admin/api/aliases
            resp = admin_test_client.get("/admin/api/aliases", headers=headers)
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert isinstance(body["message"], str)

            # POST /admin/api/aliases
            resp = admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": alias_name, "real_model_id": model_id},
                headers=headers,
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert isinstance(body["message"], str)

            # DELETE /admin/api/aliases/{alias_name}
            resp = admin_test_client.delete(
                f"/admin/api/aliases/{alias_name}",
                headers=headers,
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert isinstance(body["message"], str)

        finally:
            _reset_aliases(admin_test_client, original)
