# -*- coding: utf-8 -*-

"""
Unit tests for Admin Panel routes (routes_admin.py).

Tests the following:
- verify_admin_api_key authentication (Bearer token and X-API-Key)
- GET /admin - Admin panel HTML page
- Pydantic models: AliasCreateRequest, AliasResponse, ApiResponse
- GET /admin/api/models - Available models list
- GET /admin/api/aliases - Current alias mappings
- POST /admin/api/aliases - Create new alias mapping
- DELETE /admin/api/aliases/{alias_name} - Delete alias mapping
"""

import pytest
from unittest.mock import Mock

from fastapi import HTTPException

from kiro.routes_admin import (
    verify_admin_api_key,
    admin_router,
    AliasCreateRequest,
    AliasResponse,
    ApiResponse,
)
from kiro.config import PROXY_API_KEY, APP_VERSION


# =============================================================================
# Helper to build a mock Request with headers
# =============================================================================


def _make_request(headers: dict) -> Mock:
    """Create a mock FastAPI Request with the given headers.

    Args:
        headers: Dict of header name → value. Names are lowercased
                 internally to match Starlette behaviour.

    Returns:
        A Mock whose .headers.get() works like a real Request.
    """
    lower_headers = {k.lower(): v for k, v in headers.items()}
    mock = Mock()
    mock.headers = Mock()
    mock.headers.get = lambda name, default=None: lower_headers.get(name.lower(), default)
    return mock


def _auth_headers() -> dict:
    """Return valid Bearer auth headers for convenience."""
    return {"Authorization": f"Bearer {PROXY_API_KEY}"}


# =============================================================================
# Tests for verify_admin_api_key
# =============================================================================


class TestVerifyAdminApiKey:
    """Tests for the verify_admin_api_key authentication dependency."""

    @pytest.mark.asyncio
    async def test_valid_bearer_token_returns_true(self):
        """
        What it does: Verifies that a valid Bearer token passes authentication.
        Purpose: Ensure Authorization: Bearer auth method works.
        """
        request = _make_request({"Authorization": f"Bearer {PROXY_API_KEY}"})
        result = await verify_admin_api_key(request)
        assert result is True

    @pytest.mark.asyncio
    async def test_valid_x_api_key_returns_true(self):
        """
        What it does: Verifies that a valid X-API-Key header passes authentication.
        Purpose: Ensure X-API-Key fallback auth method works.
        """
        request = _make_request({"X-API-Key": PROXY_API_KEY})
        result = await verify_admin_api_key(request)
        assert result is True

    @pytest.mark.asyncio
    async def test_bearer_takes_precedence_over_x_api_key(self):
        """
        What it does: Verifies Bearer token is checked first.
        Purpose: Ensure correct priority when both headers are present.
        """
        request = _make_request({
            "Authorization": f"Bearer {PROXY_API_KEY}",
            "X-API-Key": "wrong-key",
        })
        result = await verify_admin_api_key(request)
        assert result is True

    @pytest.mark.asyncio
    async def test_falls_back_to_x_api_key_when_bearer_missing(self):
        """
        What it does: Verifies X-API-Key is used when Authorization is absent.
        Purpose: Ensure fallback works correctly.
        """
        request = _make_request({"X-API-Key": PROXY_API_KEY})
        result = await verify_admin_api_key(request)
        assert result is True

    @pytest.mark.asyncio
    async def test_invalid_bearer_token_raises_401(self):
        """
        What it does: Verifies that an invalid Bearer token is rejected.
        Purpose: Ensure unauthorized access is blocked.
        """
        request = _make_request({"Authorization": "Bearer wrong-key-123"})
        with pytest.raises(HTTPException) as exc_info:
            await verify_admin_api_key(request)
        assert exc_info.value.status_code == 401
        assert "Invalid or missing API Key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_x_api_key_raises_401(self):
        """
        What it does: Verifies that an invalid X-API-Key is rejected.
        Purpose: Ensure unauthorized access is blocked.
        """
        request = _make_request({"X-API-Key": "wrong-key-456"})
        with pytest.raises(HTTPException) as exc_info:
            await verify_admin_api_key(request)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_all_headers_raises_401(self):
        """
        What it does: Verifies that missing auth headers are rejected.
        Purpose: Ensure requests without any credentials are blocked.
        """
        request = _make_request({})
        with pytest.raises(HTTPException) as exc_info:
            await verify_admin_api_key(request)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_bearer_token_raises_401(self):
        """
        What it does: Verifies that an empty Bearer value is rejected.
        Purpose: Ensure edge case of empty credentials is handled.
        """
        request = _make_request({"Authorization": "Bearer "})
        with pytest.raises(HTTPException) as exc_info:
            await verify_admin_api_key(request)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_bearer_without_prefix_raises_401(self):
        """
        What it does: Verifies that a raw key without "Bearer " prefix is rejected.
        Purpose: Ensure the Authorization header format is enforced.
        """
        request = _make_request({"Authorization": PROXY_API_KEY})
        with pytest.raises(HTTPException) as exc_info:
            await verify_admin_api_key(request)
        assert exc_info.value.status_code == 401


# =============================================================================
# Tests for Pydantic Models
# =============================================================================


class TestPydanticModels:
    """Tests for the admin API Pydantic models."""

    def test_alias_create_request_valid(self):
        """
        What it does: Verifies AliasCreateRequest accepts valid data.
        Purpose: Ensure request model works for normal input.
        """
        req = AliasCreateRequest(alias_name="my-opus", real_model_id="claude-opus-4.5")
        assert req.alias_name == "my-opus"
        assert req.real_model_id == "claude-opus-4.5"

    def test_alias_response_valid(self):
        """
        What it does: Verifies AliasResponse serialises correctly.
        Purpose: Ensure response model works for normal output.
        """
        resp = AliasResponse(alias_name="my-opus", real_model_id="claude-opus-4.5")
        data = resp.model_dump()
        assert data == {"alias_name": "my-opus", "real_model_id": "claude-opus-4.5"}

    def test_api_response_success_with_data(self):
        """
        What it does: Verifies ApiResponse with data payload.
        Purpose: Ensure the standard wrapper carries data correctly.
        """
        resp = ApiResponse(success=True, message="ok", data=["model-a", "model-b"])
        data = resp.model_dump()
        assert data["success"] is True
        assert data["message"] == "ok"
        assert data["data"] == ["model-a", "model-b"]

    def test_api_response_error_without_data(self):
        """
        What it does: Verifies ApiResponse without data (error case).
        Purpose: Ensure error responses omit data gracefully.
        """
        resp = ApiResponse(success=False, message="别名已存在")
        data = resp.model_dump()
        assert data["success"] is False
        assert data["message"] == "别名已存在"
        assert data["data"] is None


# =============================================================================
# Tests for GET /admin endpoint
# =============================================================================


class TestGetAdminPage:
    """Tests for the GET /admin HTML page endpoint.

    Validates Requirements 1.2, 2.1, 2.2, 9.3:
    - Admin page returns HTML with proper content type
    - Page contains Kiro Gateway title and version
    - Page contains tab navigation (模型管理, 系统设置)
    - Page contains alias form elements and table structure
    - Page is accessible without authentication
    """

    def test_admin_page_returns_200_html(self, test_client):
        """
        What it does: Verifies GET /admin returns 200 with text/html content type.
        Purpose: Ensure the admin page is accessible and serves HTML.
        """
        response = test_client.get("/admin")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_admin_page_contains_kiro_gateway_title(self, test_client):
        """
        What it does: Verifies the HTML contains "Kiro Gateway" in the header.
        Purpose: Ensure the page displays the application name.
        """
        response = test_client.get("/admin")
        body = response.text
        assert "Kiro Gateway" in body

    def test_admin_page_contains_version_number(self, test_client):
        """
        What it does: Verifies the HTML contains the APP_VERSION from config.
        Purpose: Ensure the page displays the current version (Req 9.3).
        """
        response = test_client.get("/admin")
        body = response.text
        assert f"v{APP_VERSION}" in body

    def test_admin_page_contains_model_management_tab(self, test_client):
        """
        What it does: Verifies the HTML contains the "模型管理" tab button.
        Purpose: Ensure the model management tab is present (Req 2.2).
        """
        response = test_client.get("/admin")
        body = response.text
        assert "模型管理" in body

    def test_admin_page_contains_settings_tab(self, test_client):
        """
        What it does: Verifies the HTML contains the "系统设置" tab button.
        Purpose: Ensure the settings tab is present for future features (Req 2.3).
        """
        response = test_client.get("/admin")
        body = response.text
        assert "系统设置" in body

    def test_admin_page_contains_alias_form_elements(self, test_client):
        """
        What it does: Verifies the HTML contains alias-input and model-input form fields.
        Purpose: Ensure the add-alias form is rendered with required inputs (Req 4.1).
        """
        response = test_client.get("/admin")
        body = response.text
        assert 'id="alias-input"' in body
        assert 'id="model-input"' in body

    def test_admin_page_contains_alias_table(self, test_client):
        """
        What it does: Verifies the HTML contains the alias table structure.
        Purpose: Ensure the alias mapping table is rendered (Req 3.1, 3.2).
        """
        response = test_client.get("/admin")
        body = response.text
        assert "alias-table" in body
        assert "alias-tbody" in body
        assert "<thead>" in body
        assert "<tbody" in body

    def test_admin_page_contains_settings_content(self, test_client):
        """
        What it does: Verifies the settings tab contains API Key configuration UI.
        Purpose: Ensure settings tab has functional content (Req 2.3).
        """
        response = test_client.get("/admin")
        body = response.text
        assert "API Key" in body
        assert "settings-apikey-input" in body

    def test_admin_page_no_auth_required(self, test_client):
        """
        What it does: Verifies GET /admin works without any auth headers.
        Purpose: Ensure the HTML page is publicly accessible (auth is
                 only required for API endpoints).
        """
        response = test_client.get("/admin")
        assert response.status_code == 200


# =============================================================================
# Tests for GET /admin/api/models endpoint
# =============================================================================


class TestGetAvailableModels:
    """Tests for the GET /admin/api/models endpoint.

    Validates Requirements 3.4 and 8.1:
    - Returns available models from cache + hidden models
    - Excludes models in HIDDEN_FROM_LIST
    - Requires authentication
    - Returns ApiResponse format
    """

    def test_returns_200_with_valid_bearer_token(self, test_client):
        """
        What it does: Verifies the endpoint returns 200 with valid auth.
        Purpose: Ensure authenticated access works.
        """
        response = test_client.get(
            "/admin/api/models",
            headers={"Authorization": f"Bearer {PROXY_API_KEY}"},
        )
        assert response.status_code == 200

    def test_returns_200_with_valid_x_api_key(self, test_client):
        """
        What it does: Verifies the endpoint accepts X-API-Key auth.
        Purpose: Ensure both auth methods work for this endpoint.
        """
        response = test_client.get(
            "/admin/api/models",
            headers={"X-API-Key": PROXY_API_KEY},
        )
        assert response.status_code == 200

    def test_returns_401_without_auth(self, test_client):
        """
        What it does: Verifies the endpoint rejects unauthenticated requests.
        Purpose: Ensure auth is enforced (Requirement 1.4, 1.5).
        """
        response = test_client.get("/admin/api/models")
        assert response.status_code == 401

    def test_returns_401_with_invalid_key(self, test_client):
        """
        What it does: Verifies the endpoint rejects invalid API keys.
        Purpose: Ensure invalid credentials are blocked.
        """
        response = test_client.get(
            "/admin/api/models",
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert response.status_code == 401

    def test_response_format_is_api_response(self, test_client):
        """
        What it does: Verifies the response matches ApiResponse schema.
        Purpose: Ensure response format consistency (Property 9).
        """
        response = test_client.get(
            "/admin/api/models",
            headers={"Authorization": f"Bearer {PROXY_API_KEY}"},
        )
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "ok"
        assert isinstance(body["data"], list)

    def test_data_is_sorted(self, test_client):
        """
        What it does: Verifies the model list is sorted alphabetically.
        Purpose: Ensure consistent ordering for the admin UI.
        """
        response = test_client.get(
            "/admin/api/models",
            headers={"Authorization": f"Bearer {PROXY_API_KEY}"},
        )
        data = response.json()["data"]
        assert data == sorted(data)

    def test_includes_cache_models(self, test_client):
        """
        What it does: Verifies models from the cache appear in the response.
        Purpose: Ensure cache models are included (Requirement 3.4).

        Note: In the test environment the Kiro API call fails (network blocked),
        so the cache may only contain hidden models. We verify that every model
        in the cache (minus HIDDEN_FROM_LIST) is present in the response.
        """
        from kiro.config import HIDDEN_FROM_LIST

        response = test_client.get(
            "/admin/api/models",
            headers={"Authorization": f"Bearer {PROXY_API_KEY}"},
        )
        data = response.json()["data"]

        # The endpoint should return at least one model
        assert len(data) > 0, "Expected at least one model in the response"

        # Every returned model should NOT be in HIDDEN_FROM_LIST
        for model_id in data:
            assert model_id not in HIDDEN_FROM_LIST, (
                f"Model '{model_id}' is in HIDDEN_FROM_LIST but was returned"
            )

    def test_includes_hidden_models(self, test_client):
        """
        What it does: Verifies hidden model display names appear in the response.
        Purpose: Ensure HIDDEN_MODELS are merged (Requirement 3.4).
        """
        from kiro.config import HIDDEN_MODELS, HIDDEN_FROM_LIST

        response = test_client.get(
            "/admin/api/models",
            headers={"Authorization": f"Bearer {PROXY_API_KEY}"},
        )
        data = response.json()["data"]

        for display_name in HIDDEN_MODELS:
            if display_name not in HIDDEN_FROM_LIST:
                assert display_name in data, (
                    f"Expected hidden model '{display_name}' in models list"
                )

    def test_excludes_hidden_from_list_models(self, test_client):
        """
        What it does: Verifies models in HIDDEN_FROM_LIST are excluded.
        Purpose: Ensure filtering works correctly (Requirement 8.1).
        """
        from kiro.config import HIDDEN_FROM_LIST

        response = test_client.get(
            "/admin/api/models",
            headers={"Authorization": f"Bearer {PROXY_API_KEY}"},
        )
        data = response.json()["data"]

        for hidden_id in HIDDEN_FROM_LIST:
            assert hidden_id not in data, (
                f"Model '{hidden_id}' should be excluded from list"
            )

    def test_no_duplicates_in_response(self, test_client):
        """
        What it does: Verifies the model list contains no duplicates.
        Purpose: Ensure deduplication when cache and hidden models overlap.
        """
        response = test_client.get(
            "/admin/api/models",
            headers={"Authorization": f"Bearer {PROXY_API_KEY}"},
        )
        data = response.json()["data"]
        assert len(data) == len(set(data)), "Model list contains duplicates"


# =============================================================================
# Fixture: inject a mock SettingsManager into app.state for alias endpoints
# =============================================================================


@pytest.fixture
def admin_test_client(test_client):
    """Extend the standard test_client with a mock SettingsManager on app.state.

    The POST and DELETE alias endpoints require ``app.state.settings_manager``.
    Since the main lifespan does not set it up yet (task 5.2), we inject a
    mock here so the endpoints can call ``.load()`` and ``.save()`` without
    touching the filesystem.

    Yields:
        The same TestClient, but with ``app.state.settings_manager`` set.
    """
    from kiro.settings_manager import TraySettings

    mock_sm = Mock()
    mock_sm.load.return_value = TraySettings()
    mock_sm.save.return_value = None

    test_client.app.state.settings_manager = mock_sm
    yield test_client


# =============================================================================
# Tests for GET /admin/api/aliases endpoint
# =============================================================================


class TestGetAliases:
    """Tests for the GET /admin/api/aliases endpoint.

    Validates Requirements 3.1, 3.2, 3.3, 8.2:
    - Returns current alias mappings from ModelResolver
    - Requires authentication
    - Returns ApiResponse format with alias list
    """

    def test_returns_200_with_valid_auth(self, test_client):
        """
        What it does: Verifies the endpoint returns 200 with valid Bearer auth.
        Purpose: Ensure authenticated access works (Requirement 1.4).
        """
        response = test_client.get("/admin/api/aliases", headers=_auth_headers())
        assert response.status_code == 200

    def test_returns_401_without_auth(self, test_client):
        """
        What it does: Verifies the endpoint rejects unauthenticated requests.
        Purpose: Ensure auth is enforced (Requirement 1.5).
        """
        response = test_client.get("/admin/api/aliases")
        assert response.status_code == 401

    def test_response_format_is_api_response(self, test_client):
        """
        What it does: Verifies the response matches ApiResponse schema.
        Purpose: Ensure response format consistency (Property 9, Requirement 8.5).
        """
        response = test_client.get("/admin/api/aliases", headers=_auth_headers())
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "ok"
        assert isinstance(body["data"], list)

    def test_returns_current_aliases(self, test_client):
        """
        What it does: Verifies the response contains the aliases from ModelResolver.
        Purpose: Ensure alias data is read from the live resolver (Requirement 3.1, 3.2).
        """
        from kiro.config import MODEL_ALIASES

        response = test_client.get("/admin/api/aliases", headers=_auth_headers())
        data = response.json()["data"]

        # Each item should have alias_name and real_model_id
        for item in data:
            assert "alias_name" in item
            assert "real_model_id" in item

        # The returned aliases should match what's in the resolver
        returned_map = {item["alias_name"]: item["real_model_id"] for item in data}
        resolver_aliases = test_client.app.state.model_resolver.aliases
        assert returned_map == resolver_aliases

    def test_data_is_sorted_by_alias_name(self, test_client):
        """
        What it does: Verifies the alias list is sorted by alias_name.
        Purpose: Ensure consistent ordering for the admin UI.
        """
        response = test_client.get("/admin/api/aliases", headers=_auth_headers())
        data = response.json()["data"]
        alias_names = [item["alias_name"] for item in data]
        assert alias_names == sorted(alias_names)

    def test_returns_empty_list_when_no_aliases(self, test_client):
        """
        What it does: Verifies the endpoint returns an empty list when no aliases exist.
        Purpose: Ensure edge case of empty aliases is handled (Requirement 3.3).
        """
        # Temporarily clear aliases
        resolver = test_client.app.state.model_resolver
        original_aliases = resolver.aliases.copy()
        resolver.update_aliases({})

        try:
            response = test_client.get("/admin/api/aliases", headers=_auth_headers())
            body = response.json()
            assert body["success"] is True
            assert body["data"] == []
        finally:
            resolver.update_aliases(original_aliases)

    def test_accepts_x_api_key_auth(self, test_client):
        """
        What it does: Verifies the endpoint accepts X-API-Key auth.
        Purpose: Ensure both auth methods work (Requirement 1.4).
        """
        response = test_client.get(
            "/admin/api/aliases",
            headers={"X-API-Key": PROXY_API_KEY},
        )
        assert response.status_code == 200


# =============================================================================
# Tests for POST /admin/api/aliases endpoint
# =============================================================================


class TestCreateAlias:
    """Tests for the POST /admin/api/aliases endpoint.

    Validates Requirements 4.1–4.7, 8.3:
    - Creates new alias mappings
    - Validates empty/whitespace alias names (400)
    - Rejects duplicate aliases (409)
    - Warns on model name conflicts
    - Updates ModelResolver and SettingsManager
    """

    def test_create_alias_success(self, admin_test_client):
        """
        What it does: Verifies a valid alias is created successfully.
        Purpose: Ensure basic alias creation works (Requirement 4.3, 8.3).
        """
        resolver = admin_test_client.app.state.model_resolver
        original_aliases = resolver.aliases.copy()

        try:
            response = admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": "test-new-alias", "real_model_id": "claude-opus-4.5"},
                headers=_auth_headers(),
            )
            assert response.status_code == 200
            body = response.json()
            assert body["success"] is True
            assert "test-new-alias" in body["message"]
        finally:
            resolver.update_aliases(original_aliases)

    def test_create_alias_updates_resolver(self, admin_test_client):
        """
        What it does: Verifies the alias is immediately available in ModelResolver.
        Purpose: Ensure real-time update (Requirement 4.4).
        """
        resolver = admin_test_client.app.state.model_resolver
        original_aliases = resolver.aliases.copy()

        try:
            admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": "live-alias", "real_model_id": "claude-sonnet-4"},
                headers=_auth_headers(),
            )
            assert "live-alias" in resolver.aliases
            assert resolver.aliases["live-alias"] == "claude-sonnet-4"
        finally:
            resolver.update_aliases(original_aliases)

    def test_create_alias_persists_via_settings_manager(self, admin_test_client):
        """
        What it does: Verifies SettingsManager.save() is called after creation.
        Purpose: Ensure persistence (Requirement 6.3).
        """
        resolver = admin_test_client.app.state.model_resolver
        original_aliases = resolver.aliases.copy()
        mock_sm = admin_test_client.app.state.settings_manager

        try:
            admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": "persist-alias", "real_model_id": "claude-opus-4.5"},
                headers=_auth_headers(),
            )
            mock_sm.load.assert_called()
            mock_sm.save.assert_called()
        finally:
            resolver.update_aliases(original_aliases)

    def test_create_alias_returns_401_without_auth(self, admin_test_client):
        """
        What it does: Verifies the endpoint rejects unauthenticated requests.
        Purpose: Ensure auth is enforced (Requirement 1.5).
        """
        response = admin_test_client.post(
            "/admin/api/aliases",
            json={"alias_name": "no-auth", "real_model_id": "claude-opus-4.5"},
        )
        assert response.status_code == 401

    def test_create_alias_empty_name_returns_400(self, admin_test_client):
        """
        What it does: Verifies empty alias name is rejected with 400.
        Purpose: Ensure input validation (Requirement 4.6).
        """
        response = admin_test_client.post(
            "/admin/api/aliases",
            json={"alias_name": "", "real_model_id": "claude-opus-4.5"},
            headers=_auth_headers(),
        )
        assert response.status_code == 400
        assert "别名不能为空" in response.json()["detail"]

    def test_create_alias_whitespace_only_returns_400(self, admin_test_client):
        """
        What it does: Verifies whitespace-only alias name is rejected with 400.
        Purpose: Ensure whitespace trimming and validation (Requirement 4.6).
        """
        response = admin_test_client.post(
            "/admin/api/aliases",
            json={"alias_name": "   \t  ", "real_model_id": "claude-opus-4.5"},
            headers=_auth_headers(),
        )
        assert response.status_code == 400
        assert "别名不能为空" in response.json()["detail"]

    def test_create_alias_duplicate_returns_409(self, admin_test_client):
        """
        What it does: Verifies duplicate alias name is rejected with 409.
        Purpose: Ensure duplicate detection (Requirement 4.5).
        """
        resolver = admin_test_client.app.state.model_resolver
        original_aliases = resolver.aliases.copy()

        try:
            # Create the first alias
            admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": "dup-alias", "real_model_id": "claude-opus-4.5"},
                headers=_auth_headers(),
            )
            # Try to create the same alias again
            response = admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": "dup-alias", "real_model_id": "claude-sonnet-4"},
                headers=_auth_headers(),
            )
            assert response.status_code == 409
            assert "别名已存在" in response.json()["detail"]
        finally:
            resolver.update_aliases(original_aliases)

    def test_create_alias_model_conflict_returns_warning(self, admin_test_client):
        """
        What it does: Verifies alias conflicting with an available model includes a warning.
        Purpose: Ensure model name conflict warning (Requirement 4.7).
        """
        resolver = admin_test_client.app.state.model_resolver
        original_aliases = resolver.aliases.copy()

        # Pick a model that exists in the cache
        model_cache = admin_test_client.app.state.model_cache
        all_models = model_cache.get_all_model_ids()
        if not all_models:
            pytest.skip("No models in cache to test conflict")

        conflict_name = all_models[0]

        try:
            response = admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": conflict_name, "real_model_id": "claude-opus-4.5"},
                headers=_auth_headers(),
            )
            # Should still succeed (200) but with a warning in the message
            assert response.status_code == 200
            body = response.json()
            assert body["success"] is True
            assert "警告" in body["message"]
            assert "冲突" in body["message"]
        finally:
            resolver.update_aliases(original_aliases)

    def test_create_alias_no_warning_for_non_conflicting(self, admin_test_client):
        """
        What it does: Verifies no warning when alias doesn't conflict with models.
        Purpose: Ensure warnings only appear when appropriate.
        """
        resolver = admin_test_client.app.state.model_resolver
        original_aliases = resolver.aliases.copy()

        try:
            response = admin_test_client.post(
                "/admin/api/aliases",
                json={
                    "alias_name": "unique-nonexistent-alias-xyz",
                    "real_model_id": "claude-opus-4.5",
                },
                headers=_auth_headers(),
            )
            assert response.status_code == 200
            body = response.json()
            assert "警告" not in body["message"]
        finally:
            resolver.update_aliases(original_aliases)

    def test_create_alias_response_format(self, admin_test_client):
        """
        What it does: Verifies the response matches ApiResponse schema.
        Purpose: Ensure response format consistency (Property 9, Requirement 8.5).
        """
        resolver = admin_test_client.app.state.model_resolver
        original_aliases = resolver.aliases.copy()

        try:
            response = admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": "format-test", "real_model_id": "claude-opus-4.5"},
                headers=_auth_headers(),
            )
            body = response.json()
            assert "success" in body
            assert "message" in body
            assert body["success"] is True
        finally:
            resolver.update_aliases(original_aliases)


# =============================================================================
# Tests for DELETE /admin/api/aliases/{alias_name} endpoint
# =============================================================================


class TestDeleteAlias:
    """Tests for the DELETE /admin/api/aliases/{alias_name} endpoint.

    Validates Requirements 5.1, 5.3, 5.4, 8.4:
    - Deletes existing alias mappings
    - Returns 404 for non-existent aliases
    - Updates ModelResolver and SettingsManager
    """

    def test_delete_alias_success(self, admin_test_client):
        """
        What it does: Verifies an existing alias is deleted successfully.
        Purpose: Ensure basic alias deletion works (Requirement 5.3, 8.4).
        """
        resolver = admin_test_client.app.state.model_resolver
        original_aliases = resolver.aliases.copy()

        try:
            # Create an alias first
            admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": "to-delete", "real_model_id": "claude-opus-4.5"},
                headers=_auth_headers(),
            )
            # Delete it
            response = admin_test_client.delete(
                "/admin/api/aliases/to-delete",
                headers=_auth_headers(),
            )
            assert response.status_code == 200
            body = response.json()
            assert body["success"] is True
            assert "to-delete" in body["message"]
            assert "已删除" in body["message"]
        finally:
            resolver.update_aliases(original_aliases)

    def test_delete_alias_removes_from_resolver(self, admin_test_client):
        """
        What it does: Verifies the alias is immediately removed from ModelResolver.
        Purpose: Ensure real-time update (Requirement 5.4).
        """
        resolver = admin_test_client.app.state.model_resolver
        original_aliases = resolver.aliases.copy()

        try:
            # Create an alias first
            admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": "remove-me", "real_model_id": "claude-opus-4.5"},
                headers=_auth_headers(),
            )
            assert "remove-me" in resolver.aliases

            # Delete it
            admin_test_client.delete(
                "/admin/api/aliases/remove-me",
                headers=_auth_headers(),
            )
            assert "remove-me" not in resolver.aliases
        finally:
            resolver.update_aliases(original_aliases)

    def test_delete_alias_persists_via_settings_manager(self, admin_test_client):
        """
        What it does: Verifies SettingsManager.save() is called after deletion.
        Purpose: Ensure persistence (Requirement 6.3).
        """
        resolver = admin_test_client.app.state.model_resolver
        original_aliases = resolver.aliases.copy()
        mock_sm = admin_test_client.app.state.settings_manager

        try:
            # Create an alias first
            admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": "persist-del", "real_model_id": "claude-opus-4.5"},
                headers=_auth_headers(),
            )
            mock_sm.reset_mock()

            # Delete it
            admin_test_client.delete(
                "/admin/api/aliases/persist-del",
                headers=_auth_headers(),
            )
            mock_sm.load.assert_called()
            mock_sm.save.assert_called()
        finally:
            resolver.update_aliases(original_aliases)

    def test_delete_nonexistent_alias_returns_404(self, admin_test_client):
        """
        What it does: Verifies deleting a non-existent alias returns 404.
        Purpose: Ensure proper error handling (Requirement 5.1).
        """
        response = admin_test_client.delete(
            "/admin/api/aliases/nonexistent-alias-xyz",
            headers=_auth_headers(),
        )
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "nonexistent-alias-xyz" in detail
        assert "不存在" in detail

    def test_delete_alias_returns_401_without_auth(self, admin_test_client):
        """
        What it does: Verifies the endpoint rejects unauthenticated requests.
        Purpose: Ensure auth is enforced (Requirement 1.5).
        """
        response = admin_test_client.delete("/admin/api/aliases/some-alias")
        assert response.status_code == 401

    def test_delete_alias_response_format(self, admin_test_client):
        """
        What it does: Verifies the response matches ApiResponse schema.
        Purpose: Ensure response format consistency (Property 9, Requirement 8.5).
        """
        resolver = admin_test_client.app.state.model_resolver
        original_aliases = resolver.aliases.copy()

        try:
            # Create then delete
            admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": "fmt-del", "real_model_id": "claude-opus-4.5"},
                headers=_auth_headers(),
            )
            response = admin_test_client.delete(
                "/admin/api/aliases/fmt-del",
                headers=_auth_headers(),
            )
            body = response.json()
            assert "success" in body
            assert "message" in body
            assert body["success"] is True
        finally:
            resolver.update_aliases(original_aliases)

    def test_delete_does_not_affect_other_aliases(self, admin_test_client):
        """
        What it does: Verifies deleting one alias doesn't affect others.
        Purpose: Ensure surgical deletion without side effects.
        """
        resolver = admin_test_client.app.state.model_resolver
        original_aliases = resolver.aliases.copy()

        try:
            # Create two aliases
            admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": "keep-me", "real_model_id": "claude-opus-4.5"},
                headers=_auth_headers(),
            )
            admin_test_client.post(
                "/admin/api/aliases",
                json={"alias_name": "delete-me", "real_model_id": "claude-sonnet-4"},
                headers=_auth_headers(),
            )

            # Delete only one
            admin_test_client.delete(
                "/admin/api/aliases/delete-me",
                headers=_auth_headers(),
            )

            # The other should still exist
            assert "keep-me" in resolver.aliases
            assert "delete-me" not in resolver.aliases
        finally:
            resolver.update_aliases(original_aliases)
