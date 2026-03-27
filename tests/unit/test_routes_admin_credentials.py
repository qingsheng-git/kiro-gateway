# -*- coding: utf-8 -*-

"""
Tests for the Admin Panel credential management API endpoints.

Covers:
- GET /admin/api/credentials: List credential profiles
- POST /admin/api/credentials: Add new credential profile
- DELETE /admin/api/credentials/{profile_id}: Remove credential profile
- PUT /admin/api/credentials/{profile_id}/toggle: Enable/disable profile
- POST /admin/api/credentials/{profile_id}/validate: Validate profile
- Authentication requirements for all endpoints
- Error handling: invalid JSON, missing fields, nonexistent profiles
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from kiro.config import PROXY_API_KEY
from kiro.credential_manager import CredentialManager


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cred_test_client(test_client, tmp_path):
    """Extend test_client with a CredentialManager on app.state.

    Creates a real CredentialManager backed by a temp file so that
    add/remove/toggle operations work end-to-end through the API.

    Yields:
        TestClient with credential_manager on app.state.
    """
    creds_file = tmp_path / "test_creds.json"
    mgr = CredentialManager(credentials_file=creds_file)
    test_client.app.state.credential_manager = mgr
    yield test_client


def _auth_headers():
    """Return valid Authorization headers."""
    return {"Authorization": f"Bearer {PROXY_API_KEY}"}


# =============================================================================
# GET /admin/api/credentials
# =============================================================================


class TestListCredentials:
    """Tests for the GET /admin/api/credentials endpoint."""

    def test_returns_200_with_valid_auth(self, cred_test_client):
        """Returns 200 with valid auth and empty list."""
        resp = cred_test_client.get("/admin/api/credentials", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"] == []

    def test_returns_401_without_auth(self, cred_test_client):
        """Returns 401 without authentication."""
        resp = cred_test_client.get("/admin/api/credentials")
        assert resp.status_code == 401

    def test_returns_profiles_after_add(self, cred_test_client):
        """Returns profiles after adding one."""
        # Add a profile first
        cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "Test", "credential_json": '{"refreshToken": "tok"}'},
        )

        resp = cred_test_client.get("/admin/api/credentials", headers=_auth_headers())
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name"] == "Test"
        assert data[0]["auth_type"] == "kiro_desktop"
        assert data[0]["enabled"] is True

    def test_response_excludes_sensitive_fields(self, cred_test_client):
        """Response does not contain tokens or secrets."""
        cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={
                "name": "Sensitive",
                "credential_json": '{"refreshToken": "secret_tok", "clientSecret": "secret"}',
            },
        )

        resp = cred_test_client.get("/admin/api/credentials", headers=_auth_headers())
        body = resp.text
        assert "secret_tok" not in body
        assert "secret" not in body or "clientSecret" not in body

    def test_handles_missing_credential_manager(self, test_client):
        """Returns empty list when credential_manager is not on app.state."""
        # Ensure credential_manager is not set
        if hasattr(test_client.app.state, "credential_manager"):
            delattr(test_client.app.state, "credential_manager")

        resp = test_client.get("/admin/api/credentials", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["data"] == []


# =============================================================================
# POST /admin/api/credentials
# =============================================================================


class TestAddCredential:
    """Tests for the POST /admin/api/credentials endpoint."""

    def test_add_credential_success(self, cred_test_client):
        """Successfully adds a credential profile via JSON paste."""
        resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "New User", "credential_json": '{"refreshToken": "tok_new"}'},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "已添加" in data["message"]
        assert data["data"]["name"] == "New User"
        assert "id" in data["data"]

    def test_add_credential_via_file_path(self, cred_test_client, tmp_path):
        """Successfully adds a credential profile via file path."""
        cred_file = tmp_path / "test_cred.json"
        cred_file.write_text(json.dumps({"refreshToken": "tok_file", "region": "us-east-1"}))

        resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "File User", "credential_file": str(cred_file)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["name"] == "File User"

    def test_add_credential_file_not_found_returns_400(self, cred_test_client):
        """Returns 400 when credential file does not exist."""
        resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "Missing", "credential_file": "/nonexistent/path.json"},
        )
        assert resp.status_code == 400
        assert "不存在" in resp.json()["detail"]

    def test_add_credential_no_source_returns_400(self, cred_test_client):
        """Returns 400 when neither JSON nor file path is provided."""
        resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "Empty"},
        )
        assert resp.status_code == 400
        assert "请提供" in resp.json()["detail"]

    def test_add_credential_returns_401_without_auth(self, cred_test_client):
        """Returns 401 without authentication."""
        resp = cred_test_client.post(
            "/admin/api/credentials",
            json={"name": "No Auth", "credential_json": '{"refreshToken": "tok"}'},
        )
        assert resp.status_code == 401

    def test_add_credential_empty_name_returns_400(self, cred_test_client):
        """Returns 400 when name is empty."""
        resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "  ", "credential_json": '{"refreshToken": "tok"}'},
        )
        assert resp.status_code == 400
        assert "名称" in resp.json()["detail"]

    def test_add_credential_invalid_json_returns_400(self, cred_test_client):
        """Returns 400 when credential_json is not valid JSON."""
        resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "Bad JSON", "credential_json": "not json {{{"},
        )
        assert resp.status_code == 400
        assert "JSON" in resp.json()["detail"]

    def test_add_credential_non_object_json_returns_400(self, cred_test_client):
        """Returns 400 when credential_json is not a JSON object."""
        resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "Array", "credential_json": '["not", "an", "object"]'},
        )
        assert resp.status_code == 400
        assert "对象" in resp.json()["detail"]

    def test_add_credential_missing_refresh_token_returns_400(self, cred_test_client):
        """Returns 400 when refreshToken is missing from JSON."""
        resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "No Token", "credential_json": '{"region": "us-east-1"}'},
        )
        assert resp.status_code == 400
        assert "refreshToken" in resp.json()["detail"]

    def test_add_credential_aws_sso_type(self, cred_test_client):
        """Correctly detects AWS SSO OIDC auth type."""
        cred_json = json.dumps({
            "refreshToken": "tok",
            "clientId": "cid",
            "clientSecret": "csec",
        })
        resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "SSO User", "credential_json": cred_json},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["auth_type"] == "aws_sso_oidc"

    def test_add_multiple_credentials(self, cred_test_client):
        """Multiple credentials can be added."""
        for i in range(3):
            resp = cred_test_client.post(
                "/admin/api/credentials",
                headers=_auth_headers(),
                json={"name": f"User {i}", "credential_json": f'{{"refreshToken": "tok_{i}"}}'},
            )
            assert resp.status_code == 200

        resp = cred_test_client.get("/admin/api/credentials", headers=_auth_headers())
        assert len(resp.json()["data"]) == 3

    def test_add_credential_with_device_registration(self, cred_test_client):
        """Enterprise credential with device registration merges clientId/clientSecret."""
        cred_json = json.dumps({
            "refreshToken": "tok_ent",
            "clientIdHash": "abc123",
            "region": "us-east-1",
        })
        device_json = json.dumps({
            "clientId": "enterprise_cid",
            "clientSecret": "enterprise_csec",
        })
        resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={
                "name": "Enterprise User",
                "credential_json": cred_json,
                "device_registration_json": device_json,
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["auth_type"] == "aws_sso_oidc"

    def test_add_credential_enterprise_missing_device_reg_still_works(self, cred_test_client):
        """Enterprise credential without device registration creates Kiro Desktop auth."""
        cred_json = json.dumps({
            "refreshToken": "tok_ent_no_dev",
            "clientIdHash": "abc123",
        })
        resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "No Device Reg", "credential_json": cred_json},
        )
        assert resp.status_code == 200
        # Without clientId/clientSecret, falls back to Kiro Desktop
        assert resp.json()["data"]["auth_type"] == "kiro_desktop"

    def test_add_credential_invalid_device_reg_json_returns_400(self, cred_test_client):
        """Returns 400 when device registration JSON is invalid."""
        cred_json = json.dumps({"refreshToken": "tok", "clientIdHash": "abc"})
        resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={
                "name": "Bad Device",
                "credential_json": cred_json,
                "device_registration_json": "not json {{{",
            },
        )
        assert resp.status_code == 400
        assert "设备注册" in resp.json()["detail"]


# =============================================================================
# DELETE /admin/api/credentials/{profile_id}
# =============================================================================


class TestRemoveCredential:
    """Tests for the DELETE /admin/api/credentials/{profile_id} endpoint."""

    def test_remove_credential_success(self, cred_test_client):
        """Successfully removes a credential profile."""
        # Add first
        add_resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "ToRemove", "credential_json": '{"refreshToken": "tok"}'},
        )
        profile_id = add_resp.json()["data"]["id"]

        # Remove
        resp = cred_test_client.delete(
            f"/admin/api/credentials/{profile_id}",
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert "已删除" in resp.json()["message"]

    def test_remove_credential_returns_401_without_auth(self, cred_test_client):
        """Returns 401 without authentication."""
        resp = cred_test_client.delete("/admin/api/credentials/some_id")
        assert resp.status_code == 401

    def test_remove_nonexistent_credential_returns_404(self, cred_test_client):
        """Returns 404 when profile does not exist."""
        resp = cred_test_client.delete(
            "/admin/api/credentials/nonexistent",
            headers=_auth_headers(),
        )
        assert resp.status_code == 404

    def test_remove_does_not_affect_other_profiles(self, cred_test_client):
        """Removing one profile leaves others intact."""
        # Add two profiles
        r1 = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "Keep", "credential_json": '{"refreshToken": "tok_keep"}'},
        )
        r2 = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "Remove", "credential_json": '{"refreshToken": "tok_rm"}'},
        )
        keep_id = r1.json()["data"]["id"]
        rm_id = r2.json()["data"]["id"]

        # Remove one
        cred_test_client.delete(f"/admin/api/credentials/{rm_id}", headers=_auth_headers())

        # Verify the other remains
        resp = cred_test_client.get("/admin/api/credentials", headers=_auth_headers())
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["id"] == keep_id


# =============================================================================
# PUT /admin/api/credentials/{profile_id}/toggle
# =============================================================================


class TestToggleCredential:
    """Tests for the PUT /admin/api/credentials/{profile_id}/toggle endpoint."""

    def test_disable_credential(self, cred_test_client):
        """Successfully disables a credential profile."""
        add_resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "Toggle", "credential_json": '{"refreshToken": "tok"}'},
        )
        profile_id = add_resp.json()["data"]["id"]

        resp = cred_test_client.put(
            f"/admin/api/credentials/{profile_id}/toggle",
            headers=_auth_headers(),
            json={"enabled": False},
        )
        assert resp.status_code == 200
        assert "已禁用" in resp.json()["message"]

        # Verify state
        list_resp = cred_test_client.get("/admin/api/credentials", headers=_auth_headers())
        assert list_resp.json()["data"][0]["enabled"] is False

    def test_enable_credential(self, cred_test_client):
        """Successfully re-enables a disabled credential profile."""
        add_resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "Toggle", "credential_json": '{"refreshToken": "tok"}'},
        )
        profile_id = add_resp.json()["data"]["id"]

        # Disable first
        cred_test_client.put(
            f"/admin/api/credentials/{profile_id}/toggle",
            headers=_auth_headers(),
            json={"enabled": False},
        )

        # Re-enable
        resp = cred_test_client.put(
            f"/admin/api/credentials/{profile_id}/toggle",
            headers=_auth_headers(),
            json={"enabled": True},
        )
        assert resp.status_code == 200
        assert "已启用" in resp.json()["message"]

    def test_toggle_returns_401_without_auth(self, cred_test_client):
        """Returns 401 without authentication."""
        resp = cred_test_client.put(
            "/admin/api/credentials/some_id/toggle",
            json={"enabled": False},
        )
        assert resp.status_code == 401

    def test_toggle_nonexistent_returns_404(self, cred_test_client):
        """Returns 404 when profile does not exist."""
        resp = cred_test_client.put(
            "/admin/api/credentials/nonexistent/toggle",
            headers=_auth_headers(),
            json={"enabled": False},
        )
        assert resp.status_code == 404


# =============================================================================
# POST /admin/api/credentials/{profile_id}/validate
# =============================================================================


class TestValidateCredential:
    """Tests for the POST /admin/api/credentials/{profile_id}/validate endpoint."""

    def test_validate_returns_401_without_auth(self, cred_test_client):
        """Returns 401 without authentication."""
        resp = cred_test_client.post("/admin/api/credentials/some_id/validate")
        assert resp.status_code == 401

    def test_validate_nonexistent_profile(self, cred_test_client):
        """Returns invalid for nonexistent profile."""
        resp = cred_test_client.post(
            "/admin/api/credentials/nonexistent/validate",
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "不存在" in data["message"]

    def test_validate_profile_with_preset_token(self, cred_test_client):
        """Returns valid when profile has a non-expired token."""
        # Add profile
        add_resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "Valid", "credential_json": '{"refreshToken": "tok"}'},
        )
        profile_id = add_resp.json()["data"]["id"]

        # Manually set a valid token on the auth manager
        mgr = cred_test_client.app.state.credential_manager
        profile = mgr._get_profile_by_id(profile_id)
        profile.auth_manager._access_token = "valid_token"
        profile.auth_manager._expires_at = datetime(2099, 1, 1, tzinfo=timezone.utc)

        resp = cred_test_client.post(
            f"/admin/api/credentials/{profile_id}/validate",
            headers=_auth_headers(),
        )
        data = resp.json()
        assert data["success"] is True
        assert "成功" in data["message"]


# =============================================================================
# Admin HTML - Credential Tab Tests
# =============================================================================


class TestAdminHtmlCredentialTab:
    """Tests that the admin HTML page includes credential management UI."""

    def test_admin_page_contains_credential_tab(self, test_client):
        """Admin page has a '凭证管理' tab button."""
        resp = test_client.get("/admin")
        assert resp.status_code == 200
        assert "凭证管理" in resp.text

    def test_admin_page_contains_credential_form(self, test_client):
        """Admin page has the credential add form elements."""
        resp = test_client.get("/admin")
        html = resp.text
        assert "cred-name-input" in html
        assert "cred-json-input" in html
        assert "添加凭证" in html

    def test_admin_page_contains_credential_list(self, test_client):
        """Admin page has the credential list container."""
        resp = test_client.get("/admin")
        assert "cred-list" in resp.text

    def test_admin_page_contains_credential_js_functions(self, test_client):
        """Admin page has JavaScript functions for credential management."""
        resp = test_client.get("/admin")
        html = resp.text
        assert "addCredential" in html
        assert "deleteCredential" in html
        assert "toggleCredential" in html
        assert "validateCredential" in html
        assert "loadCredentials" in html
        assert "detectEnterprise" in html

    def test_admin_page_contains_device_registration_input(self, test_client):
        """Admin page has the device registration textarea for Enterprise."""
        resp = test_client.get("/admin")
        html = resp.text
        assert "cred-device-reg-input" in html
        assert "设备注册文件" in html


# =============================================================================
# POST /admin/api/credentials/{profile_id}/quota
# =============================================================================


class TestQueryCredentialQuota:
    """Tests for the POST /admin/api/credentials/{profile_id}/quota endpoint."""

    def test_quota_returns_401_without_auth(self, cred_test_client):
        """Returns 401 without authentication."""
        resp = cred_test_client.post("/admin/api/credentials/some_id/quota")
        assert resp.status_code == 401

    def test_quota_nonexistent_profile(self, cred_test_client):
        """Returns error for nonexistent profile."""
        resp = cred_test_client.post(
            "/admin/api/credentials/nonexistent/quota",
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "不存在" in data["message"]

    def test_quota_returns_structure_with_valid_token(self, cred_test_client):
        """Returns quota structure when profile has a valid token."""
        # Add profile
        add_resp = cred_test_client.post(
            "/admin/api/credentials",
            headers=_auth_headers(),
            json={"name": "Quota", "credential_json": '{"refreshToken": "tok"}'},
        )
        profile_id = add_resp.json()["data"]["id"]

        # Set valid token
        mgr = cred_test_client.app.state.credential_manager
        profile = mgr._get_profile_by_id(profile_id)
        profile.auth_manager._access_token = "valid_token"
        profile.auth_manager._expires_at = datetime(2099, 1, 1, tzinfo=timezone.utc)

        resp = cred_test_client.post(
            f"/admin/api/credentials/{profile_id}/quota",
            headers=_auth_headers(),
        )
        data = resp.json()
        # API calls will fail (network blocked), but endpoint should return 200
        assert resp.status_code == 200
        assert "data" in data
        assert "auth_type" in data["data"]
        assert "usage" in data["data"]

    def test_admin_page_contains_quota_button(self, test_client):
        """Admin page has the quota query button."""
        resp = test_client.get("/admin")
        html = resp.text
        assert "queryQuota" in html
        assert "查询额度" in html
