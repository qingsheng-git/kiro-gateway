# -*- coding: utf-8 -*-

"""
Unit tests for Chat Playground integration in the Admin Panel.

Verifies that get_admin_html() produces HTML containing all required
Chat Playground elements: tab button, DOM structure, JavaScript functions,
CSS styles, and feature integration points.

Requirements: 1.1, 1.2, 1.4, 2.1, 3.1, 4.2, 5.1, 6.1, 7.1, 8.1,
              9.1, 10.1, 11.1, 12.1, 13.1, 14.1
"""

import pytest

from kiro.admin_html import get_admin_html


@pytest.fixture(scope="module")
def html() -> str:
    """Generate the admin HTML once for all tests in this module."""
    return get_admin_html("test")


# =========================================================================
# Tab Integration
# =========================================================================


class TestChatPlaygroundTabIntegration:
    """Verify the Chat Playground tab is properly integrated into the Admin Panel."""

    def test_tab_button_exists(self, html: str) -> None:
        """Tab bar contains a button with data-tab='chat' and text '对话测试'."""
        assert 'data-tab="chat"' in html
        assert "对话测试" in html

    def test_tab_content_container_exists(self, html: str) -> None:
        """A tab-content div with id='tab-chat' exists."""
        assert 'id="tab-chat"' in html

    def test_tab_has_chat_playground_class(self, html: str) -> None:
        """The chat playground root container uses the correct CSS class."""
        assert 'class="chat-playground"' in html


# =========================================================================
# DOM Structure
# =========================================================================


class TestChatPlaygroundDOMStructure:
    """Verify all critical DOM elements are present in the HTML output."""

    def test_session_sidebar_exists(self, html: str) -> None:
        """Session sidebar with class 'chat-sessions' and list container exist."""
        assert 'class="chat-sessions"' in html
        assert 'id="chat-session-list"' in html

    def test_chat_area_exists(self, html: str) -> None:
        """The scrollable chat message area exists."""
        assert 'id="chat-area"' in html

    def test_input_area_exists(self, html: str) -> None:
        """The message input textarea exists."""
        assert 'id="chat-input"' in html

    def test_send_button_exists(self, html: str) -> None:
        """The send button exists."""
        assert 'id="chat-send-btn"' in html

    def test_model_selector_exists(self, html: str) -> None:
        """The model selector dropdown exists."""
        assert 'id="chat-model-select"' in html

    def test_param_panel_exists(self, html: str) -> None:
        """The collapsible parameter panel exists."""
        assert 'id="chat-params-panel"' in html

    def test_system_prompt_panel_exists(self, html: str) -> None:
        """The collapsible system prompt editor panel exists."""
        assert 'id="chat-system-prompt-panel"' in html

    def test_export_menu_exists(self, html: str) -> None:
        """The export dropdown menu exists."""
        assert 'id="chat-export-menu"' in html


# =========================================================================
# JavaScript Functions
# =========================================================================


class TestChatPlaygroundJavaScriptFunctions:
    """Verify all required JavaScript functions are defined in the HTML."""

    def test_sendMessage_defined(self, html: str) -> None:
        assert "function sendMessage()" in html

    def test_stopGeneration_defined(self, html: str) -> None:
        assert "function stopGeneration()" in html

    def test_switchSession_defined(self, html: str) -> None:
        assert "function switchSession(" in html

    def test_createSession_defined(self, html: str) -> None:
        assert "function createSession()" in html

    def test_deleteSession_defined(self, html: str) -> None:
        assert "function deleteSession(" in html

    def test_exportAsJSON_defined(self, html: str) -> None:
        assert "function exportAsJSON()" in html

    def test_exportAsPNG_defined(self, html: str) -> None:
        assert "function exportAsPNG()" in html

    def test_renderMarkdown_defined(self, html: str) -> None:
        assert "function renderMarkdown(" in html

    def test_parseSSELine_defined(self, html: str) -> None:
        assert "function parseSSELine(" in html

    def test_clampValue_defined(self, html: str) -> None:
        assert "function clampValue(" in html

    def test_initChatPlayground_defined(self, html: str) -> None:
        assert "function initChatPlayground()" in html

    def test_renderMessage_defined(self, html: str) -> None:
        assert "function renderMessage(" in html

    def test_attachPreviewButtons_defined(self, html: str) -> None:
        assert "function attachPreviewButtons(" in html

    def test_togglePreview_defined(self, html: str) -> None:
        assert "function togglePreview(" in html


# =========================================================================
# CSS Styles
# =========================================================================


class TestChatPlaygroundCSS:
    """Verify key CSS classes are defined in the embedded stylesheet."""

    def test_message_bubble_styles(self, html: str) -> None:
        """User, assistant, and error message bubble styles exist."""
        assert ".chat-msg-user" in html
        assert ".chat-msg-assistant" in html
        assert ".chat-msg-error" in html

    def test_thinking_block_styles(self, html: str) -> None:
        """Thinking block CSS class is defined."""
        assert ".chat-thinking" in html

    def test_token_usage_styles(self, html: str) -> None:
        """Token usage display CSS class is defined."""
        assert ".chat-token-usage" in html

    def test_code_block_styles(self, html: str) -> None:
        """Code block CSS class is defined."""
        assert ".chat-code-block" in html

    def test_preview_container_styles(self, html: str) -> None:
        """Content preview container CSS class is defined."""
        assert ".chat-preview-container" in html

    def test_loading_styles(self, html: str) -> None:
        """Loading indicator CSS class is defined."""
        assert ".chat-loading" in html


# =========================================================================
# Feature Integration
# =========================================================================


class TestChatPlaygroundFeatureIntegration:
    """Verify cross-cutting feature integration points in the HTML."""

    def test_localStorage_key_used(self, html: str) -> None:
        """The localStorage key 'kiro_chat_sessions' is referenced."""
        assert "kiro_chat_sessions" in html

    def test_keyboard_shortcuts(self, html: str) -> None:
        """Shift+Enter keyboard handling code exists."""
        assert "shiftKey" in html
        assert "Enter" in html

    def test_html2canvas_cdn_url(self, html: str) -> None:
        """html2canvas CDN URL is present for PNG export."""
        assert "html2canvas" in html

    def test_sandbox_iframe(self, html: str) -> None:
        """Sandbox attribute is used for HTML preview iframes."""
        assert "sandbox" in html

    def test_stream_true_in_payload(self, html: str) -> None:
        """stream: true is set in the sendMessage payload construction."""
        assert "stream: true" in html

    def test_reasoning_content_handling(self, html: str) -> None:
        """reasoning_content field is handled for thinking blocks."""
        assert "reasoning_content" in html

    def test_export_filename_format(self, html: str) -> None:
        """Export filename patterns for JSON and PNG are present."""
        assert "chat-export-" in html
        assert "chat-screenshot-" in html
