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
Admin panel HTML page module.

Provides a self-contained HTML page (embedded CSS + JavaScript) for the
Kiro Gateway web administration interface. No external dependencies are
required — everything is inlined into a single HTML string.
"""


def get_admin_html(version: str) -> str:
    """Return the complete admin panel HTML page.

    The page includes:
    - Dark header bar with "Kiro Gateway Admin" and version number
    - Tab navigation ("模型管理", "凭证管理", and "系统设置")
    - Model management UI: alias form, alias table, available models list
    - Credential management UI: add credentials via JSON paste, profile list
    - System settings UI: API Key configuration with localStorage persistence
    - Toast notifications for success/error feedback
    - Responsive CSS layout

    Args:
        version: Application version string displayed in the header.

    Returns:
        Complete HTML string ready to serve as an HTMLResponse.
    """
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kiro Gateway Admin</title>
<style>
/* ===== Reset & Base ===== */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: #f5f7fa;
    color: #333;
    line-height: 1.6;
}}

/* ===== Header ===== */
.header {{
    background: #1a1a2e;
    color: #fff;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}}
.header h1 {{
    font-size: 20px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}
.header .version {{
    font-size: 13px;
    opacity: 0.7;
    margin-left: 10px;
    font-weight: 400;
}}

/* ===== Tabs ===== */
.tabs {{
    display: flex;
    background: #fff;
    border-bottom: 2px solid #e2e8f0;
    padding: 0 24px;
}}
.tab-btn {{
    padding: 12px 24px;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 15px;
    color: #64748b;
    border-bottom: 3px solid transparent;
    margin-bottom: -2px;
    transition: color 0.2s, border-color 0.2s;
}}
.tab-btn:hover {{
    color: #334155;
}}
.tab-btn.active {{
    color: #2563eb;
    border-bottom-color: #2563eb;
    font-weight: 600;
}}

/* ===== Tab Content ===== */
.tab-content {{
    display: none;
    padding: 24px;
    max-width: 1100px;
    margin: 0 auto;
}}
.tab-content.active {{
    display: block;
}}

/* ===== Card ===== */
.card {{
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    padding: 20px;
    margin-bottom: 20px;
}}
.card h2 {{
    font-size: 16px;
    margin-bottom: 16px;
    color: #1e293b;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 8px;
}}

/* ===== Form ===== */
.form-row {{
    display: flex;
    gap: 12px;
    align-items: flex-end;
    flex-wrap: wrap;
}}
.form-group {{
    display: flex;
    flex-direction: column;
    flex: 1;
    min-width: 180px;
}}
.form-group label {{
    font-size: 13px;
    color: #64748b;
    margin-bottom: 4px;
    font-weight: 500;
}}
.form-group input,
.form-group select {{
    padding: 8px 12px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
}}
.form-group input:focus,
.form-group select:focus {{
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgba(37,99,235,0.15);
}}
.btn {{
    padding: 8px 20px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
    font-weight: 500;
    transition: background 0.2s, opacity 0.2s;
    white-space: nowrap;
}}
.btn-primary {{
    background: #2563eb;
    color: #fff;
}}
.btn-primary:hover {{
    background: #1d4ed8;
}}
.btn-danger {{
    background: #ef4444;
    color: #fff;
    padding: 4px 12px;
    font-size: 13px;
}}
.btn-danger:hover {{
    background: #dc2626;
}}

/* ===== Table ===== */
.alias-table {{
    width: 100%;
    border-collapse: collapse;
}}
.alias-table th,
.alias-table td {{
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid #e2e8f0;
    font-size: 14px;
}}
.alias-table th {{
    background: #f8fafc;
    color: #64748b;
    font-weight: 600;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.alias-table tr:hover {{
    background: #f8fafc;
}}
.empty-msg {{
    text-align: center;
    color: #94a3b8;
    padding: 24px;
    font-size: 14px;
}}

/* ===== Models Grid ===== */
.models-grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}}
.model-tag {{
    background: #e0e7ff;
    color: #3730a3;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 13px;
    font-weight: 500;
}}

/* ===== Toast ===== */
.toast-container {{
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 8px;
}}
.toast {{
    padding: 12px 20px;
    border-radius: 8px;
    color: #fff;
    font-size: 14px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    animation: slideIn 0.3s ease;
    max-width: 400px;
    word-break: break-word;
}}
.toast.success {{ background: #16a34a; }}
.toast.error {{ background: #dc2626; }}
.toast.warning {{ background: #d97706; }}
@keyframes slideIn {{
    from {{ transform: translateX(100%); opacity: 0; }}
    to {{ transform: translateX(0); opacity: 1; }}
}}

/* ===== Status Badge ===== */
.status-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 13px;
    font-weight: 500;
}}
.status-badge.connected {{
    background: #dcfce7;
    color: #166534;
}}
.status-badge.disconnected {{
    background: #fee2e2;
    color: #991b1b;
}}
.status-badge.enabled {{
    background: #dcfce7;
    color: #166534;
}}
.status-badge.disabled {{
    background: #fef3c7;
    color: #92400e;
}}
.status-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
}}
.status-badge.connected .status-dot {{
    background: #16a34a;
}}
.status-badge.disconnected .status-dot {{
    background: #dc2626;
}}
.apikey-display {{
    font-family: monospace;
    font-size: 14px;
    color: #64748b;
    margin-top: 8px;
}}
.settings-hint {{
    font-size: 13px;
    color: #94a3b8;
    margin-top: 8px;
}}

/* ===== Credential Card ===== */
.cred-card {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: box-shadow 0.2s;
}}
.cred-card:hover {{
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}}
.cred-info {{
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
}}
.cred-name {{
    font-size: 15px;
    font-weight: 600;
    color: #1e293b;
}}
.cred-meta {{
    font-size: 13px;
    color: #64748b;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
}}
.cred-actions {{
    display: flex;
    gap: 8px;
    align-items: center;
    flex-shrink: 0;
}}
.btn-sm {{
    padding: 4px 12px;
    font-size: 13px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    transition: background 0.2s;
}}
.btn-success {{
    background: #16a34a;
    color: #fff;
}}
.btn-success:hover {{
    background: #15803d;
}}
.btn-warning {{
    background: #d97706;
    color: #fff;
}}
.btn-warning:hover {{
    background: #b45309;
}}
.btn-outline {{
    background: #f1f5f9;
    color: #475569;
    border: 1px solid #cbd5e1;
}}
.btn-outline:hover {{
    background: #e2e8f0;
}}
textarea.cred-json {{
    width: 100%;
    min-height: 120px;
    padding: 10px 12px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-family: "SF Mono", "Fira Code", "Consolas", monospace;
    font-size: 13px;
    line-height: 1.5;
    resize: vertical;
    outline: none;
    transition: border-color 0.2s;
}}
textarea.cred-json:focus {{
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgba(37,99,235,0.15);
}}

/* ===== Responsive ===== */
@media (max-width: 640px) {{
    .header {{ padding: 12px 16px; }}
    .header h1 {{ font-size: 17px; }}
    .tabs {{ padding: 0 12px; }}
    .tab-btn {{ padding: 10px 16px; font-size: 14px; }}
    .tab-content {{ padding: 16px; }}
    .form-row {{ flex-direction: column; }}
    .form-group {{ min-width: 100%; }}
}}

/* ===== Chat Playground ===== */

/* Layout: sidebar + main area */
.chat-playground {{
    display: flex;
    height: calc(100vh - 110px);
    background: #f5f7fa;
}}

/* Session sidebar */
.chat-sessions {{
    width: 220px;
    min-width: 180px;
    background: #fff;
    border-right: 1px solid #e2e8f0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}}
.chat-sessions-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px;
    border-bottom: 1px solid #e2e8f0;
    font-size: 14px;
    font-weight: 600;
    color: #1e293b;
}}
.chat-sessions-header button {{
    padding: 4px 10px;
    font-size: 13px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    background: #2563eb;
    color: #fff;
    font-weight: 500;
    transition: background 0.2s;
}}
.chat-sessions-header button:hover {{
    background: #1d4ed8;
}}
.chat-session-list {{
    flex: 1;
    overflow-y: auto;
    padding: 8px;
}}
.chat-session-item {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 10px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    color: #475569;
    transition: background 0.15s;
    margin-bottom: 2px;
}}
.chat-session-item:hover {{
    background: #f1f5f9;
}}
.chat-session-item.active {{
    background: #e0e7ff;
    color: #2563eb;
    font-weight: 600;
}}
.chat-session-item .session-delete {{
    display: none;
    padding: 2px 6px;
    font-size: 12px;
    border: none;
    background: transparent;
    color: #94a3b8;
    cursor: pointer;
    border-radius: 4px;
}}
.chat-session-item:hover .session-delete {{
    display: inline-block;
}}
.chat-session-item .session-delete:hover {{
    color: #ef4444;
    background: #fee2e2;
}}

/* Main content area */
.chat-main {{
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    overflow: hidden;
}}

/* Toolbar above chat area */
.chat-toolbar {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    background: #fff;
    border-bottom: 1px solid #e2e8f0;
    flex-wrap: wrap;
}}
.chat-toolbar select,
.chat-toolbar input[type="text"] {{
    padding: 6px 10px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-size: 13px;
    outline: none;
    transition: border-color 0.2s;
}}
.chat-toolbar select:focus,
.chat-toolbar input[type="text"]:focus {{
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgba(37,99,235,0.15);
}}
.chat-toolbar-actions {{
    margin-left: auto;
    display: flex;
    gap: 6px;
    align-items: center;
    position: relative;
}}
.chat-toolbar-actions button {{
    padding: 5px 12px;
    font-size: 13px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    background: #fff;
    color: #475569;
    cursor: pointer;
    transition: background 0.15s;
}}
.chat-toolbar-actions button:hover {{
    background: #f1f5f9;
}}

/* Chat area (scrollable messages) */
.chat-area {{
    flex: 1;
    overflow-y: auto;
    padding: 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}}

/* Message bubbles */
.chat-msg {{
    max-width: 80%;
    padding: 10px 16px;
    border-radius: 12px;
    font-size: 14px;
    line-height: 1.7;
    word-break: break-word;
    position: relative;
}}
.chat-msg-user {{
    align-self: flex-end;
    background: #2563eb;
    color: #fff;
    border-bottom-right-radius: 4px;
}}
.chat-msg-assistant {{
    align-self: flex-start;
    background: #fff;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-bottom-left-radius: 4px;
}}
.chat-msg-error {{
    align-self: flex-start;
    background: #fef2f2;
    color: #991b1b;
    border: 1px solid #fecaca;
    border-bottom-left-radius: 4px;
}}

/* Parameter panel (collapsible) */
.chat-params {{
    background: #fff;
    border-bottom: 1px solid #e2e8f0;
    overflow: hidden;
    transition: max-height 0.25s ease;
}}
.chat-params.collapsed {{
    max-height: 0;
    border-bottom: none;
}}
.chat-params-inner {{
    padding: 12px 16px;
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    align-items: center;
}}
.chat-param-group {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: #475569;
}}
.chat-param-group label {{
    font-weight: 500;
    min-width: 90px;
}}
.chat-param-group input[type="range"] {{
    width: 120px;
    accent-color: #2563eb;
}}
.chat-param-group input[type="number"] {{
    width: 80px;
    padding: 4px 8px;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
}}
.chat-param-group input[type="number"]:focus {{
    border-color: #2563eb;
}}
.chat-param-group .param-value {{
    min-width: 36px;
    text-align: center;
    font-weight: 600;
    color: #2563eb;
}}
.chat-params-inner .btn {{
    padding: 5px 14px;
    font-size: 13px;
}}

/* System Prompt editor (collapsible) */
.chat-system-prompt {{
    background: #fff;
    border-bottom: 1px solid #e2e8f0;
    overflow: hidden;
    transition: max-height 0.25s ease;
}}
.chat-system-prompt.collapsed {{
    max-height: 0;
    border-bottom: none;
}}
.chat-system-prompt-inner {{
    padding: 12px 16px;
}}
.chat-system-prompt-inner textarea {{
    width: 100%;
    min-height: 80px;
    max-height: 200px;
    padding: 8px 12px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-size: 13px;
    line-height: 1.5;
    resize: vertical;
    outline: none;
    font-family: inherit;
    transition: border-color 0.2s;
}}
.chat-system-prompt-inner textarea:focus {{
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgba(37,99,235,0.15);
}}
.chat-system-prompt-preview {{
    font-size: 12px;
    color: #94a3b8;
    padding: 4px 0;
    font-style: italic;
}}

/* Input area */
.chat-input-area {{
    display: flex;
    align-items: flex-end;
    gap: 10px;
    padding: 12px 16px;
    background: #fff;
    border-top: 1px solid #e2e8f0;
}}
.chat-input-area textarea {{
    flex: 1;
    padding: 10px 14px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font-size: 14px;
    line-height: 1.5;
    resize: none;
    outline: none;
    font-family: inherit;
    min-height: 42px;
    max-height: 150px;
    overflow-y: auto;
    transition: border-color 0.2s;
}}
.chat-input-area textarea:focus {{
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgba(37,99,235,0.15);
}}
.chat-input-area button {{
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s, opacity 0.2s;
    white-space: nowrap;
}}
.chat-send-btn {{
    background: #2563eb;
    color: #fff;
}}
.chat-send-btn:hover {{
    background: #1d4ed8;
}}
.chat-send-btn:disabled {{
    opacity: 0.5;
    cursor: not-allowed;
}}
.chat-stop-btn {{
    background: #ef4444;
    color: #fff;
}}
.chat-stop-btn:hover {{
    background: #dc2626;
}}

/* Thinking block (collapsible) */
.chat-thinking {{
    background: #f8fafc;
    border-left: 3px solid #cbd5e1;
    padding: 8px 12px;
    margin-bottom: 8px;
    border-radius: 0 6px 6px 0;
    font-style: italic;
    color: #64748b;
    font-size: 13px;
    line-height: 1.6;
}}
.chat-thinking-toggle {{
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    font-size: 12px;
    color: #94a3b8;
    font-weight: 500;
    user-select: none;
    padding: 4px 0;
}}
.chat-thinking-toggle:hover {{
    color: #64748b;
}}
.chat-thinking-content {{
    display: none;
    margin-top: 6px;
}}
.chat-thinking-content.expanded {{
    display: block;
}}

/* Token usage */
.chat-token-usage {{
    font-size: 12px;
    color: #94a3b8;
    margin-top: 6px;
    padding-top: 4px;
}}

/* Export menu (dropdown) */
.chat-export-menu {{
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 4px;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    z-index: 100;
    min-width: 160px;
    display: none;
}}
.chat-export-menu.show {{
    display: block;
}}
.chat-export-menu button {{
    display: block;
    width: 100%;
    padding: 8px 14px;
    border: none;
    background: none;
    text-align: left;
    font-size: 13px;
    color: #475569;
    cursor: pointer;
    transition: background 0.15s;
}}
.chat-export-menu button:first-child {{
    border-radius: 8px 8px 0 0;
}}
.chat-export-menu button:last-child {{
    border-radius: 0 0 8px 8px;
}}
.chat-export-menu button:hover {{
    background: #f1f5f9;
}}

/* Content preview container */
.chat-preview-container {{
    max-height: 400px;
    overflow-y: auto;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    margin-top: 8px;
    background: #fff;
}}
.chat-preview-container iframe {{
    width: 100%;
    border: none;
    min-height: 200px;
}}

/* Code blocks */
.chat-code-block {{
    font-family: "SF Mono", "Fira Code", "Consolas", monospace;
    background: #1e293b;
    color: #e2e8f0;
    padding: 12px 16px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.5;
    margin: 8px 0;
    position: relative;
}}
.chat-code-block .code-lang {{
    position: absolute;
    top: 6px;
    right: 10px;
    font-size: 11px;
    color: #64748b;
    text-transform: uppercase;
}}

/* Copy button (on hover) */
.chat-copy-btn {{
    display: none;
    position: absolute;
    top: 8px;
    right: 8px;
    padding: 4px 10px;
    font-size: 12px;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    background: #fff;
    color: #475569;
    cursor: pointer;
    z-index: 10;
    transition: background 0.15s;
}}
.chat-copy-btn:hover {{
    background: #f1f5f9;
}}
.chat-msg:hover .chat-copy-btn {{
    display: inline-block;
}}

/* Loading indicator */
.chat-loading {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    font-size: 13px;
    color: #94a3b8;
}}
.chat-loading-dots {{
    display: flex;
    gap: 4px;
}}
.chat-loading-dots span {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #94a3b8;
    animation: chatBounce 1.2s infinite;
}}
.chat-loading-dots span:nth-child(2) {{
    animation-delay: 0.2s;
}}
.chat-loading-dots span:nth-child(3) {{
    animation-delay: 0.4s;
}}
@keyframes chatBounce {{
    0%, 80%, 100% {{ transform: scale(0.6); opacity: 0.4; }}
    40% {{ transform: scale(1); opacity: 1; }}
}}

/* Preview button */
.chat-preview-btn {{
    display: inline-block;
    margin-top: 4px;
    padding: 3px 10px;
    font-size: 12px;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    background: #f8fafc;
    color: #475569;
    cursor: pointer;
    transition: background 0.15s;
}}
.chat-preview-btn:hover {{
    background: #e2e8f0;
}}

/* Empty state */
.chat-empty-state {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    color: #94a3b8;
    font-size: 15px;
    gap: 8px;
}}

/* Responsive adjustments for Chat Playground */
@media (max-width: 768px) {{
    .chat-playground {{
        flex-direction: column;
        height: calc(100vh - 110px);
    }}
    .chat-sessions {{
        width: 100%;
        min-width: unset;
        max-height: 120px;
        border-right: none;
        border-bottom: 1px solid #e2e8f0;
    }}
    .chat-session-list {{
        display: flex;
        overflow-x: auto;
        overflow-y: hidden;
        padding: 6px 8px;
        gap: 4px;
    }}
    .chat-session-item {{
        white-space: nowrap;
        margin-bottom: 0;
    }}
    .chat-msg {{
        max-width: 92%;
    }}
    .chat-params-inner {{
        flex-direction: column;
        gap: 10px;
    }}
    .chat-toolbar {{
        flex-wrap: wrap;
        gap: 6px;
    }}
}}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
    <h1>Kiro Gateway Admin <span class="version">v{version}</span></h1>
</div>

<!-- Tabs -->
<div class="tabs">
    <button class="tab-btn active" data-tab="models" onclick="switchTab('models')">模型管理</button>
    <button class="tab-btn" data-tab="credentials" onclick="switchTab('credentials')">凭证管理</button>
    <button class="tab-btn" data-tab="settings" onclick="switchTab('settings')">系统设置</button>
    <button class="tab-btn" data-tab="chat" onclick="switchTab('chat')">对话测试</button>
</div>

<!-- Tab: 模型管理 -->
<div id="tab-models" class="tab-content active">
    <!-- Add Alias Form -->
    <div class="card">
        <h2>添加映射</h2>
        <div class="form-row">
            <div class="form-group">
                <label for="alias-input">别名</label>
                <input type="text" id="alias-input" placeholder="例如: my-opus">
            </div>
            <div class="form-group">
                <label for="model-input">目标模型</label>
                <input type="text" id="model-input" list="model-list" placeholder="选择或输入模型 ID">
                <datalist id="model-list"></datalist>
            </div>
            <button class="btn btn-primary" onclick="addAlias()">添加</button>
        </div>
    </div>

    <!-- Alias Table -->
    <div class="card">
        <h2>已有映射</h2>
        <table class="alias-table">
            <thead>
                <tr>
                    <th>别名</th>
                    <th>目标模型</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody id="alias-tbody">
                <tr><td colspan="3" class="empty-msg">加载中...</td></tr>
            </tbody>
        </table>
    </div>

    <!-- Available Models -->
    <div class="card">
        <h2>可用模型</h2>
        <div id="models-container" class="models-grid">
            <span class="empty-msg">加载中...</span>
        </div>
    </div>
</div>

<!-- Tab: 凭证管理 -->
<div id="tab-credentials" class="tab-content">
    <!-- Add Credential Form -->
    <div class="card">
        <h2>添加凭证</h2>
        <div class="form-group" style="margin-bottom:12px;">
            <label for="cred-name-input">配置名称</label>
            <input type="text" id="cred-name-input" placeholder="例如: 用户A、团队共享账号">
        </div>
        <div style="margin-bottom:12px;">
            <label style="font-size:13px;color:#64748b;font-weight:500;display:block;margin-bottom:8px;">添加方式</label>
            <div style="display:flex;gap:12px;">
                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:14px;">
                    <input type="radio" name="cred-mode" value="file" checked onchange="toggleCredMode()"> 凭证文件路径（推荐）
                </label>
                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:14px;">
                    <input type="radio" name="cred-mode" value="json" onchange="toggleCredMode()"> 粘贴 JSON
                </label>
            </div>
        </div>
        <div id="cred-file-mode" class="form-group" style="margin-bottom:12px;">
            <label for="cred-file-input">凭证文件路径</label>
            <input type="text" id="cred-file-input" placeholder="例如: C:\\Users\\你的用户名\\.aws\\sso\\cache\\kiro-auth-token.json">
            <p class="settings-hint">指向 Kiro IDE 凭证 JSON 文件。支持 Enterprise IDE（自动加载 clientIdHash 对应的设备注册文件）。</p>
        </div>
        <div id="cred-json-mode" class="form-group" style="margin-bottom:12px;display:none;">
            <label for="cred-json-input">凭证 JSON（粘贴 Kiro 凭证文件内容）</label>
            <textarea class="cred-json" id="cred-json-input" placeholder='{{
  "refreshToken": "your_refresh_token_here",
  "region": "us-east-1"
}}' oninput="detectEnterprise()"></textarea>
            <p class="settings-hint">支持格式：Kiro IDE 凭证文件 JSON、包含 refreshToken 的 JSON。可选字段：region、profileArn、clientId、clientSecret。</p>
        </div>
        <div id="cred-device-reg-mode" class="form-group" style="margin-bottom:12px;display:none;">
            <label for="cred-device-reg-input" style="color:#d97706;font-weight:600;">设备注册文件 JSON（Enterprise 必填）</label>
            <textarea class="cred-json" id="cred-device-reg-input" placeholder='粘贴 ~/.aws/sso/cache/{{clientIdHash}}.json 的内容
{{
  "clientId": "...",
  "clientSecret": "...",
  ...
}}'></textarea>
            <p class="settings-hint">检测到 Enterprise 凭证。请粘贴对应的设备注册文件内容（包含 clientId 和 clientSecret）。该文件通常位于 ~/.aws/sso/cache/ 目录下，文件名为凭证中 clientIdHash 的值。</p>
        </div>
        <button class="btn btn-primary" onclick="addCredential()">添加凭证</button>
    </div>

    <!-- Credential List -->
    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <h2>已有凭证 <span id="cred-count" style="font-size:13px;color:#64748b;font-weight:400;"></span></h2>
            <button class="btn-sm btn-outline" onclick="queryAllQuotas()">查询全部额度</button>
        </div>
        <div id="cred-list">
            <div class="empty-msg">加载中...</div>
        </div>
    </div>
</div>

<!-- Tab: 系统设置 -->
<div id="tab-settings" class="tab-content">
    <div class="card">
        <h2>API Key 配置</h2>
        <div id="apikey-status"></div>
        <div class="form-row" style="margin-top:16px;">
            <div class="form-group">
                <label for="settings-apikey-input">API Key (PROXY_API_KEY)</label>
                <input type="password" id="settings-apikey-input" placeholder="设置接入密钥，客户端连接时使用此密钥" autocomplete="off">
            </div>
            <button class="btn btn-primary" onclick="saveApiKey()">设置并生效</button>
        </div>
        <p class="settings-hint">设置后，所有客户端（Claude Code、Cursor 等）连接网关时需使用此密钥进行认证。密钥会持久化保存在服务端。</p>
    </div>
    <div class="card" style="margin-top:16px;">
        <h2>响应缓存</h2>
        <div id="cache-status"></div>
        <div class="form-row" style="margin-top:12px;gap:8px;">
            <button class="btn btn-primary" id="cache-toggle-btn" onclick="toggleCache()">加载中...</button>
            <button class="btn btn-danger" onclick="clearCache()" style="padding:8px 16px;font-size:14px;">清除缓存</button>
        </div>
        <p class="settings-hint">启用后，相同的请求（模型、消息、参数完全一致）将返回缓存结果，减少 API 调用。仅对非流式请求生效。</p>
    </div>
</div>

<!-- Tab: 对话测试 (Chat Playground) -->
<div id="tab-chat" class="tab-content">
    <div class="chat-playground">
        <!-- Session sidebar -->
        <div class="chat-sessions">
            <div class="chat-sessions-header">
                <span>会话列表</span>
                <button onclick="createSession()">+ 新建</button>
            </div>
            <div class="chat-session-list" id="chat-session-list"></div>
        </div>
        <!-- Main content area -->
        <div class="chat-main">
            <!-- Toolbar: model selector, params toggle, export -->
            <div class="chat-toolbar">
                <select id="chat-model-select" title="选择模型"></select>
                <input type="text" id="chat-model-input" placeholder="手动输入模型 ID" style="display:none;width:200px;">
                <button class="tab-btn" style="padding:5px 12px;font-size:13px;border:1px solid #cbd5e1;border-radius:6px;margin:0;" onclick="toggleChatParams()">参数</button>
                <button class="tab-btn" style="padding:5px 12px;font-size:13px;border:1px solid #cbd5e1;border-radius:6px;margin:0;" onclick="toggleSystemPrompt()">System Prompt <span id="chat-sp-preview" style="font-size:11px;color:#94a3b8;margin-left:4px;">未设置</span></button>
                <div class="chat-toolbar-actions">
                    <button onclick="clearConversation()">清除对话</button>
                    <button onclick="toggleExportMenu()">导出 ▾</button>
                    <div class="chat-export-menu" id="chat-export-menu">
                        <button onclick="exportAsJSON()">导出为 JSON</button>
                        <button onclick="exportAsPNG()">导出为图片</button>
                    </div>
                </div>
            </div>
            <!-- Parameter panel (collapsible) -->
            <div class="chat-params collapsed" id="chat-params-panel">
                <div class="chat-params-inner">
                    <div class="chat-param-group">
                        <label>Temperature</label>
                        <input type="range" min="0" max="2" step="0.1" value="0.7" id="chat-param-temp" oninput="updateParamDisplay('temp')">
                        <span class="param-value" id="chat-param-temp-val">0.7</span>
                    </div>
                    <div class="chat-param-group">
                        <label>Top P</label>
                        <input type="range" min="0" max="1" step="0.05" value="1.0" id="chat-param-topp" oninput="updateParamDisplay('topp')">
                        <span class="param-value" id="chat-param-topp-val">1.0</span>
                    </div>
                    <div class="chat-param-group">
                        <label>Max Tokens</label>
                        <input type="number" min="1" max="32000" value="4096" id="chat-param-maxtokens">
                    </div>
                    <button class="btn btn-primary" onclick="resetChatParams()">重置默认</button>
                </div>
            </div>
            <!-- System Prompt editor (collapsible) -->
            <div class="chat-system-prompt collapsed" id="chat-system-prompt-panel">
                <div class="chat-system-prompt-inner">
                    <textarea id="chat-system-prompt-input" placeholder="输入 System Prompt（可选）..." oninput="onSystemPromptChange()"></textarea>
                </div>
            </div>
            <!-- Chat messages area -->
            <div class="chat-area" id="chat-area">
                <div class="chat-empty-state" id="chat-empty-state">
                    <span style="font-size:32px;">💬</span>
                    <span>开始一段新对话</span>
                </div>
            </div>
            <!-- Input area -->
            <div class="chat-input-area">
                <textarea id="chat-input" placeholder="输入消息... (Enter 发送, Shift+Enter 换行)" rows="1" oninput="autoResizeInput(this)"></textarea>
                <button class="chat-send-btn" id="chat-send-btn" onclick="sendMessage()">发送</button>
            </div>
        </div>
    </div>
</div>

<!-- Toast Container -->
<div class="toast-container" id="toast-container"></div>

<script>
/* ===== State ===== */
let apiKey = localStorage.getItem('admin_api_key') || '';
let availableModels = [];
const quotaCache = {{}};

/* ===== Tab Switching ===== */
let chatPlaygroundInitialized = false;

function switchTab(tabId) {{
    document.querySelectorAll('.tab-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    }});
    document.querySelectorAll('.tab-content').forEach(content => {{
        content.classList.toggle('active', content.id === 'tab-' + tabId);
    }});
    if (tabId === 'chat' && !chatPlaygroundInitialized) {{
        chatPlaygroundInitialized = true;
        initChatPlayground();
    }}
}}

/* ===== Toast Notifications ===== */
function showToast(message, type) {{
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {{
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }}, 3500);
}}

/* ===== API Key Status ===== */
function renderApiKeyStatus(connected) {{
    const el = document.getElementById('apikey-status');
    if (connected) {{
        const masked = apiKey.length > 4
            ? '*'.repeat(apiKey.length - 4) + apiKey.slice(-4)
            : '****';
        el.innerHTML =
            '<span class="status-badge connected"><span class="status-dot"></span>已生效</span>' +
            '<div class="apikey-display">当前密钥: ' + escapeHtml(masked) + '</div>';
    }} else {{
        el.innerHTML =
            '<span class="status-badge disconnected"><span class="status-dot"></span>未配置</span>' +
            '<div class="settings-hint">请设置 API Key，客户端连接网关时需使用此密钥</div>';
    }}
}}

function renderApiKeyInvalid() {{
    const el = document.getElementById('apikey-status');
    el.innerHTML =
        '<span class="status-badge disconnected"><span class="status-dot"></span>密钥无效</span>' +
        '<div class="settings-hint">当前浏览器保存的 API Key 与服务端不匹配，请输入正确的 API Key 后点击「验证并登录」</div>' +
        '<div class="form-row" style="margin-top:12px;">' +
            '<div class="form-group">' +
                '<label for="current-apikey-input">输入当前有效的 API Key</label>' +
                '<input type="password" id="current-apikey-input" placeholder="输入服务端当前生效的密钥" autocomplete="off">' +
            '</div>' +
            '<button class="btn btn-primary" onclick="loginWithKey()">验证并登录</button>' +
        '</div>';
}}

/* ===== API Key Settings Actions ===== */
async function loginWithKey() {{
    const input = document.getElementById('current-apikey-input');
    const key = input.value.trim();
    if (!key) {{
        showToast('请输入 API Key', 'error');
        input.focus();
        return;
    }}
    // Try to validate this key against the server
    apiKey = key;
    const result = await apiFetch('/admin/api/models');
    if (result) {{
        localStorage.setItem('admin_api_key', apiKey);
        showToast('验证成功', 'success');
        renderApiKeyStatus(true);
        availableModels = result.data || [];
        updateModelsUI();
        await loadAliases();
        await loadCredentials();
        await loadCacheStats();
    }} else {{
        apiKey = '';
        renderApiKeyInvalid();
    }}
}}

async function saveApiKey() {{
    const input = document.getElementById('settings-apikey-input');
    const key = input.value.trim();
    if (!key) {{
        showToast('请输入 API Key', 'error');
        input.focus();
        return;
    }}
    // Check server-side status first to decide whether auth is needed
    let serverConfigured = false;
    try {{
        const statusResp = await fetch('/admin/api/settings/apikey/status');
        const statusData = await statusResp.json();
        serverConfigured = statusData.data && statusData.data.configured;
    }} catch (e) {{
        console.error('Failed to check apikey status:', e);
    }}

    const headers = {{
        'Content-Type': 'application/json',
    }};
    // Only send auth header when the server actually has a key configured
    // This avoids the deadlock where localStorage has a stale key but
    // the server reports "unconfigured" (using default key).
    if (serverConfigured && apiKey) {{
        headers['Authorization'] = 'Bearer ' + apiKey;
    }}
    try {{
        const resp = await fetch('/admin/api/settings/apikey', {{
            method: 'POST',
            headers: headers,
            body: JSON.stringify({{ api_key: key }})
        }});
        const data = await resp.json();
        if (!resp.ok) {{
            showToast(data.detail || '设置失败', 'error');
            return;
        }}
        // Success — update local state
        apiKey = key;
        localStorage.setItem('admin_api_key', apiKey);
        input.value = '';
        showToast('API Key 已设置并生效', 'success');
        renderApiKeyStatus(true);
        // Reload data with new key
        await validateAndLoad();
    }} catch (err) {{
        console.error('saveApiKey error:', err);
        showToast('网络连接失败', 'error');
    }}
}}

/* ===== Cache Management ===== */
async function loadCacheStats() {{
    const statusEl = document.getElementById('cache-status');
    const btnEl = document.getElementById('cache-toggle-btn');
    const result = await apiFetch('/admin/api/cache/stats');
    if (!result) {{
        statusEl.innerHTML = '<span class="status-badge disconnected"><span class="status-dot"></span>无法加载</span>';
        btnEl.textContent = '启用缓存';
        return;
    }}
    const d = result.data;
    const badge = d.enabled
        ? '<span class="status-badge connected"><span class="status-dot"></span>已启用</span>'
        : '<span class="status-badge disconnected"><span class="status-dot"></span>已禁用</span>';
    const stats = d.enabled
        ? '<div class="apikey-display">缓存条目: ' + d.size + '/' + d.max_size +
          ' | 命中: ' + d.hits + ' | 未命中: ' + d.misses +
          ' | 命中率: ' + (d.hit_rate * 100).toFixed(1) + '% | TTL: ' + d.ttl + 's</div>'
        : '';
    statusEl.innerHTML = badge + stats;
    btnEl.textContent = d.enabled ? '禁用缓存' : '启用缓存';
    btnEl.dataset.enabled = d.enabled ? 'true' : 'false';
}}

async function toggleCache() {{
    const btnEl = document.getElementById('cache-toggle-btn');
    const currentlyEnabled = btnEl.dataset.enabled === 'true';
    const result = await apiFetch('/admin/api/cache/toggle', {{
        method: 'PUT',
        body: JSON.stringify({{ enabled: !currentlyEnabled }})
    }});
    if (result) {{
        showToast(result.message, 'success');
        await loadCacheStats();
    }}
}}

async function clearCache() {{
    const result = await apiFetch('/admin/api/cache', {{
        method: 'DELETE'
    }});
    if (result) {{
        showToast(result.message, 'success');
        await loadCacheStats();
    }}
}}

/* ===== API Helpers ===== */
async function apiFetch(url, options) {{
    const headers = {{
        'Authorization': 'Bearer ' + apiKey,
        'Content-Type': 'application/json',
        ...(options && options.headers || {{}})
    }};
    try {{
        const resp = await fetch(url, {{ ...options, headers }});
        if (resp.status === 401) {{
            renderApiKeyStatus(false);
            showToast('API Key 无效或已变更，请在系统设置中重新设置', 'error');
            return null;
        }}
        const data = await resp.json();
        if (!resp.ok) {{
            const msg = data.detail || data.message || '请求失败';
            showToast(msg, 'error');
            return null;
        }}
        return data;
    }} catch (err) {{
        console.error('apiFetch error:', err);
        showToast('网络连接失败，请检查服务是否运行', 'error');
        return null;
    }}
}}

/* ===== Validate Key & Load Data ===== */
async function validateAndLoad() {{
    if (!apiKey) {{
        renderApiKeyStatus(false);
        return;
    }}
    // Use a lightweight API call to validate the key
    const result = await apiFetch('/admin/api/models');
    if (result) {{
        renderApiKeyStatus(true);
        availableModels = result.data || [];
        updateModelsUI();
        await loadAliases();
        await loadCredentials();
        await loadCacheStats();
    }} else {{
        // Key exists locally but server rejected it — show "invalid" instead of "unconfigured"
        renderApiKeyInvalid();
    }}
}}

/* ===== Load Data ===== */
async function loadData() {{
    await Promise.all([loadAliases(), loadModels()]);
}}

async function loadAliases() {{
    const tbody = document.getElementById('alias-tbody');
    try {{
        const result = await apiFetch('/admin/api/aliases');
        if (!result) {{
            tbody.innerHTML = '<tr><td colspan="3" class="empty-msg">加载失败，请检查 API Key</td></tr>';
            return;
        }}
        const aliases = result.data || [];
        if (aliases.length === 0) {{
            tbody.innerHTML = '<tr><td colspan="3" class="empty-msg">暂无映射，请添加</td></tr>';
            return;
        }}
        tbody.innerHTML = aliases.map(a =>
            '<tr>' +
            '<td>' + escapeHtml(a.alias_name) + '</td>' +
            '<td>' + escapeHtml(a.real_model_id) + '</td>' +
            '<td><button class="btn btn-danger" onclick="deleteAlias(\\'' + escapeHtml(a.alias_name) + '\\')">删除</button></td>' +
            '</tr>'
        ).join('');
    }} catch (err) {{
        console.error('loadAliases error:', err);
        tbody.innerHTML = '<tr><td colspan="3" class="empty-msg">加载失败</td></tr>';
    }}
}}

async function loadModels() {{
    const container = document.getElementById('models-container');
    try {{
        const result = await apiFetch('/admin/api/models');
        if (!result) {{
            container.innerHTML = '<span class="empty-msg">加载失败，请检查 API Key</span>';
            return;
        }}
        availableModels = result.data || [];
        updateModelsUI();
    }} catch (err) {{
        console.error('loadModels error:', err);
        container.innerHTML = '<span class="empty-msg">加载失败</span>';
    }}
}}

function updateModelsUI() {{
    const container = document.getElementById('models-container');
    const datalist = document.getElementById('model-list');
    datalist.innerHTML = availableModels.map(m =>
        '<option value="' + escapeHtml(m) + '">'
    ).join('');
    if (availableModels.length === 0) {{
        container.innerHTML = '<span class="empty-msg">暂无可用模型</span>';
        return;
    }}
    container.innerHTML = availableModels.map(m =>
        '<span class="model-tag">' + escapeHtml(m) + '</span>'
    ).join('');
}}

/* ===== Add Alias ===== */
async function addAlias() {{
    const aliasInput = document.getElementById('alias-input');
    const modelInput = document.getElementById('model-input');
    const alias = aliasInput.value.trim();
    const model = modelInput.value.trim();

    if (!alias) {{
        showToast('别名不能为空', 'error');
        aliasInput.focus();
        return;
    }}
    if (!model) {{
        showToast('请选择或输入目标模型', 'error');
        modelInput.focus();
        return;
    }}

    try {{
        const result = await apiFetch('/admin/api/aliases', {{
            method: 'POST',
            body: JSON.stringify({{ alias_name: alias, real_model_id: model }})
        }});
        if (!result) return;
        const msg = result.message || '添加成功';
        const type = msg.includes('警告') ? 'warning' : 'success';
        showToast(msg, type);
        aliasInput.value = '';
        modelInput.value = '';
        await loadAliases();
    }} catch (err) {{
        console.error('addAlias error:', err);
        showToast('添加失败: ' + err.message, 'error');
    }}
}}

/* ===== Delete Alias ===== */
async function deleteAlias(aliasName) {{
    if (!confirm('确定要删除别名 "' + aliasName + '" 吗？')) return;
    try {{
        const result = await apiFetch('/admin/api/aliases/' + encodeURIComponent(aliasName), {{
            method: 'DELETE'
        }});
        if (!result) return;
        showToast(result.message || '删除成功', 'success');
        await loadAliases();
    }} catch (err) {{
        console.error('deleteAlias error:', err);
        showToast('删除失败: ' + err.message, 'error');
    }}
}}

/* ===== Credentials Management ===== */
async function loadCredentials() {{
    const container = document.getElementById('cred-list');
    const countEl = document.getElementById('cred-count');
    try {{
        const result = await apiFetch('/admin/api/credentials');
        if (!result) {{
            container.innerHTML = '<div class="empty-msg">加载失败，请检查 API Key</div>';
            return;
        }}
        const creds = result.data || [];
        countEl.textContent = creds.length > 0 ? '(' + creds.length + ' 个)' : '';
        if (creds.length === 0) {{
            container.innerHTML = '<div class="empty-msg">暂无额外凭证，使用默认配置。点击上方添加多用户凭证。</div>';
            return;
        }}
        container.innerHTML = creds.map(function(c) {{
            const statusClass = c.enabled ? 'enabled' : 'disabled';
            const statusText = c.enabled ? '已启用' : '已禁用';
            const toggleBtnClass = c.enabled ? 'btn-sm btn-warning' : 'btn-sm btn-success';
            const toggleBtnText = c.enabled ? '禁用' : '启用';
            const authLabel = c.auth_type === 'aws_sso_oidc' ? 'AWS SSO OIDC' : 'Kiro Desktop';
            const reqCount = c.request_count || 0;
            const lastUsed = c.last_used ? new Date(c.last_used).toLocaleString() : '从未使用';
            return '<div class="cred-card">' +
                '<div class="cred-info">' +
                    '<div class="cred-name">' + escapeHtml(c.name) + '</div>' +
                    '<div class="cred-meta">' +
                        '<span class="status-badge ' + statusClass + '">' + statusText + '</span>' +
                        '<span>类型: ' + escapeHtml(authLabel) + '</span>' +
                        '<span>区域: ' + escapeHtml(c.region) + '</span>' +
                        '<span>已用: <b>' + reqCount + '</b> 次</span>' +
                        '<span>最后: ' + escapeHtml(lastUsed) + '</span>' +
                    '</div>' +
                    '<div id="quota-' + c.id + '" style="margin-top:6px;font-size:13px;color:#64748b;"></div>' +
                '</div>' +
                '<div class="cred-actions">' +
                    '<button class="btn-sm btn-outline" onclick="queryQuota(\\'' + c.id + '\\')">查询额度</button>' +
                    '<button class="btn-sm btn-outline" onclick="validateCredential(\\'' + c.id + '\\')">验证</button>' +
                    '<button class="' + toggleBtnClass + '" onclick="toggleCredential(\\'' + c.id + '\\',' + !c.enabled + ')">' + toggleBtnText + '</button>' +
                    '<button class="btn-sm btn-danger" style="padding:4px 12px;font-size:13px;" onclick="deleteCredential(\\'' + c.id + '\\',\\'' + escapeHtml(c.name) + '\\')">删除</button>' +
                '</div>' +
            '</div>';
        }}).join('');
        // Restore cached quota data after rebuilding the credential list
        Object.keys(quotaCache).forEach(function(pid) {{
            const el = document.getElementById('quota-' + pid);
            if (el && quotaCache[pid]) el.innerHTML = quotaCache[pid];
        }});
    }} catch (err) {{
        console.error('loadCredentials error:', err);
        container.innerHTML = '<div class="empty-msg">加载失败</div>';
    }}
}}

async function addCredential() {{
    const nameInput = document.getElementById('cred-name-input');
    const name = nameInput.value.trim();

    if (!name) {{
        showToast('请输入配置名称', 'error');
        nameInput.focus();
        return;
    }}

    const mode = document.querySelector('input[name="cred-mode"]:checked').value;
    let body;

    if (mode === 'file') {{
        const fileInput = document.getElementById('cred-file-input');
        const filePath = fileInput.value.trim();
        if (!filePath) {{
            showToast('请输入凭证文件路径', 'error');
            fileInput.focus();
            return;
        }}
        body = {{ name: name, credential_file: filePath }};
    }} else {{
        const jsonInput = document.getElementById('cred-json-input');
        const jsonStr = jsonInput.value.trim();
        if (!jsonStr) {{
            showToast('请粘贴凭证 JSON', 'error');
            jsonInput.focus();
            return;
        }}
        try {{
            JSON.parse(jsonStr);
        }} catch (e) {{
            showToast('凭证 JSON 格式无效: ' + e.message, 'error');
            jsonInput.focus();
            return;
        }}
        body = {{ name: name, credential_json: jsonStr }};

        // Include device registration JSON if visible and filled
        const deviceRegEl = document.getElementById('cred-device-reg-mode');
        if (deviceRegEl.style.display !== 'none') {{
            const deviceRegInput = document.getElementById('cred-device-reg-input');
            const deviceRegStr = deviceRegInput.value.trim();
            if (!deviceRegStr) {{
                showToast('Enterprise 凭证需要粘贴设备注册文件 JSON', 'error');
                deviceRegInput.focus();
                return;
            }}
            try {{
                JSON.parse(deviceRegStr);
            }} catch (e) {{
                showToast('设备注册 JSON 格式无效: ' + e.message, 'error');
                deviceRegInput.focus();
                return;
            }}
            body.device_registration_json = deviceRegStr;
        }}
    }}

    const result = await apiFetch('/admin/api/credentials', {{
        method: 'POST',
        body: JSON.stringify(body)
    }});
    if (!result) return;
    showToast(result.message || '添加成功', 'success');
    nameInput.value = '';
    document.getElementById('cred-file-input').value = '';
    document.getElementById('cred-json-input').value = '';
    document.getElementById('cred-device-reg-input').value = '';
    document.getElementById('cred-device-reg-mode').style.display = 'none';
    await loadCredentials();
}}

function toggleCredMode() {{
    const mode = document.querySelector('input[name="cred-mode"]:checked').value;
    document.getElementById('cred-file-mode').style.display = mode === 'file' ? 'flex' : 'none';
    document.getElementById('cred-json-mode').style.display = mode === 'json' ? 'flex' : 'none';
    if (mode !== 'json') {{
        document.getElementById('cred-device-reg-mode').style.display = 'none';
    }}
}}

function detectEnterprise() {{
    const jsonStr = document.getElementById('cred-json-input').value.trim();
    const deviceRegEl = document.getElementById('cred-device-reg-mode');
    if (!jsonStr) {{
        deviceRegEl.style.display = 'none';
        return;
    }}
    try {{
        const obj = JSON.parse(jsonStr);
        const isEnterprise = obj.clientIdHash || (obj.provider && obj.provider.toLowerCase().includes('enterprise'));
        deviceRegEl.style.display = isEnterprise ? 'flex' : 'none';
    }} catch (e) {{
        // Not valid JSON yet, hide device reg
        deviceRegEl.style.display = 'none';
    }}
}}

async function deleteCredential(id, name) {{
    if (!confirm('确定要删除凭证 "' + name + '" 吗？')) return;
    const result = await apiFetch('/admin/api/credentials/' + encodeURIComponent(id), {{
        method: 'DELETE'
    }});
    if (!result) return;
    showToast(result.message || '删除成功', 'success');
    await loadCredentials();
}}

async function toggleCredential(id, enabled) {{
    const result = await apiFetch('/admin/api/credentials/' + encodeURIComponent(id) + '/toggle', {{
        method: 'PUT',
        body: JSON.stringify({{ enabled: enabled }})
    }});
    if (!result) return;
    showToast(result.message || '操作成功', 'success');
    await loadCredentials();
}}

async function validateCredential(id) {{
    showToast('正在验证...', 'success');
    const result = await apiFetch('/admin/api/credentials/' + encodeURIComponent(id) + '/validate', {{
        method: 'POST'
    }});
    if (!result) return;
    const type = result.success ? 'success' : 'error';
    showToast(result.message, type);
}}

async function queryQuota(id) {{
    const quotaEl = document.getElementById('quota-' + id);
    if (quotaEl) quotaEl.innerHTML = '<span style="color:#2563eb;">正在查询...</span>';

    const result = await apiFetch('/admin/api/credentials/' + encodeURIComponent(id) + '/quota', {{
        method: 'POST'
    }});
    if (!result || !quotaEl) return;

    const data = result.data || {{}};
    if (!result.success) {{
        const errorHtml = '<span style="color:#dc2626;">' + escapeHtml(result.message) + '</span>';
        quotaEl.innerHTML = errorHtml;
        quotaCache[id] = errorHtml;
        return;
    }}

    let html = '';
    const usage = data.usage;

    if (usage) {{
        // Subscription info
        const sub = usage.subscriptionInfo;
        if (sub) {{
            const title = sub.subscriptionTitle || sub.type || 'unknown';
            const isPro = title.toLowerCase().includes('pro') || title.toLowerCase().includes('paid');
            const tierColor = isPro ? '#16a34a' : '#d97706';
            html += '<div style="margin-bottom:6px;"><b>订阅:</b> <span style="color:' + tierColor + ';font-weight:600;">' + escapeHtml(title) + '</span></div>';
        }}

        // Usage breakdown
        const breakdowns = usage.usageBreakdownList || [];
        if (breakdowns.length > 0) {{
            breakdowns.forEach(function(b) {{
                const current = b.currentUsageWithPrecision != null ? b.currentUsageWithPrecision : b.currentUsage;
                const limit = b.usageLimitWithPrecision != null ? b.usageLimitWithPrecision : b.usageLimit;
                const pct = limit > 0 ? Math.min(100, (current / limit) * 100) : 0;
                const barColor = pct >= 90 ? '#dc2626' : pct >= 70 ? '#d97706' : '#2563eb';
                const displayName = b.displayNamePlural || b.displayName || b.resourceType;

                html += '<div style="margin-bottom:8px;">';
                html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">';
                html += '<b>' + escapeHtml(displayName) + '</b>';
                html += '<span style="font-weight:600;color:' + barColor + ';">' + current.toFixed(1) + ' / ' + limit.toFixed(1) + '</span>';
                html += '</div>';
                html += '<div style="background:#e2e8f0;border-radius:4px;height:8px;overflow:hidden;">';
                html += '<div style="background:' + barColor + ';height:100%;width:' + pct.toFixed(1) + '%;border-radius:4px;transition:width 0.3s;"></div>';
                html += '</div>';

                // Free trial info
                const trial = b.freeTrialInfo;
                if (trial && trial.freeTrialStatus) {{
                    const trialCurrent = trial.currentUsageWithPrecision != null ? trial.currentUsageWithPrecision : trial.currentUsage;
                    const trialLimit = trial.usageLimitWithPrecision != null ? trial.usageLimitWithPrecision : trial.usageLimit;
                    const statusColor = trial.freeTrialStatus === 'EXPIRED' ? '#dc2626' : '#16a34a';
                    html += '<div style="margin-top:3px;font-size:12px;color:#64748b;">';
                    html += '免费试用: <span style="color:' + statusColor + ';">' + escapeHtml(trial.freeTrialStatus) + '</span>';
                    html += ' (' + trialCurrent.toFixed(1) + ' / ' + trialLimit.toFixed(1) + ')';
                    html += '</div>';
                }}

                html += '</div>';
            }});
        }}

        // Reset info
        if (usage.nextDateReset) {{
            const resetDate = new Date(usage.nextDateReset * 1000);
            html += '<div style="font-size:12px;color:#94a3b8;margin-top:4px;">下次重置时间: ' + resetDate.toLocaleDateString() + '</div>';
        }}

        // User email
        if (usage.userInfo && usage.userInfo.email) {{
            html += '<div style="font-size:12px;color:#94a3b8;">账号: ' + escapeHtml(usage.userInfo.email) + '</div>';
        }}
    }}

    if (!html) {{
        html = '<span style="color:#94a3b8;">' + escapeHtml(result.message) + '</span>';
    }}

    quotaEl.innerHTML = html;
    quotaCache[id] = html;
}}

async function queryAllQuotas() {{
    const container = document.getElementById('cred-list');
    if (!container) return;

    // Find all quota elements
    const quotaEls = container.querySelectorAll('[id^="quota-"]');
    if (quotaEls.length === 0) {{
        showToast('暂无凭证可查询', 'error');
        return;
    }}

    // Extract profile IDs and trigger queries in parallel
    const ids = [];
    quotaEls.forEach(function(el) {{
        const id = el.id.replace('quota-', '');
        if (id) ids.push(id);
    }});

    showToast('正在查询全部额度 (' + ids.length + ' 个)...', 'success');
    await Promise.all(ids.map(function(id) {{ return queryQuota(id); }}));
    showToast('全部额度查询完成', 'success');
}}

/* ===== Utilities ===== */
function escapeHtml(str) {{
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}}

/* ===== Init ===== */
document.addEventListener('DOMContentLoaded', async function() {{
    // Check server-side API key status first
    let serverConfigured = false;
    try {{
        const resp = await fetch('/admin/api/settings/apikey/status');
        const data = await resp.json();
        serverConfigured = data.data && data.data.configured;
    }} catch (err) {{
        console.error('Failed to check API key status:', err);
    }}

    if (!serverConfigured && !apiKey) {{
        // First-time setup: no key on server, no local key
        renderApiKeyStatus(false);
        switchTab('settings');
        document.getElementById('alias-tbody').innerHTML =
            '<tr><td colspan="3" class="empty-msg">请先在系统设置中设置 API Key</td></tr>';
        document.getElementById('models-container').innerHTML =
            '<span class="empty-msg">请先在系统设置中设置 API Key</span>';
        document.getElementById('cred-list').innerHTML =
            '<div class="empty-msg">请先在系统设置中设置 API Key</div>';
        return;
    }}

    if (!serverConfigured && apiKey) {{
        // Server has no real key yet but localStorage has a stale one — clear it
        // so the first-time setup flow works cleanly.
        apiKey = '';
        localStorage.removeItem('admin_api_key');
        renderApiKeyStatus(false);
        switchTab('settings');
        document.getElementById('alias-tbody').innerHTML =
            '<tr><td colspan="3" class="empty-msg">请先在系统设置中设置 API Key</td></tr>';
        document.getElementById('models-container').innerHTML =
            '<span class="empty-msg">请先在系统设置中设置 API Key</span>';
        document.getElementById('cred-list').innerHTML =
            '<div class="empty-msg">请先在系统设置中设置 API Key</div>';
        return;
    }}

    if (apiKey) {{
        // Local key exists and server is configured — validate
        await validateAndLoad().catch(function(err) {{
            console.error('Initial validateAndLoad failed:', err);
        }});
    }} else {{
        // Server has a key but browser doesn't — prompt user to enter it
        renderApiKeyInvalid();
        switchTab('settings');
    }}
    
    // Auto-refresh credential usage stats every 15 seconds
    setInterval(function() {{
        if (apiKey && document.getElementById('tab-credentials').classList.contains('active')) {{
            loadCredentials();
        }}
    }}, 15000);
}});

/* ===== Chat Playground: Constants & State ===== */
const CHAT_DEFAULT_PARAMS = {{temperature: 0.7, top_p: 1.0, max_tokens: 4096}};

const chatState = {{
    sessions: [],
    activeSessionId: null,
    isGenerating: false,
    abortController: null,
    selectedModel: '',
    params: {{temperature: 0.7, top_p: 1.0, max_tokens: 4096}},
    systemPrompt: ''
}};

function generateChatUUID() {{
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {{
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    }});
}}

/* ===== Chat Playground: Session Manager ===== */
function getActiveSession() {{
    if (!chatState.activeSessionId) return null;
    return chatState.sessions.find(function(s) {{ return s.id === chatState.activeSessionId; }}) || null;
}}

function createSession() {{
    const sessionNumber = chatState.sessions.length + 1;
    const now = Date.now();
    const session = {{
        id: generateChatUUID(),
        title: '新对话 ' + sessionNumber,
        messages: [],
        model: chatState.selectedModel || '',
        params: Object.assign({{}}, chatState.params),
        systemPrompt: chatState.systemPrompt || '',
        createdAt: now,
        updatedAt: now
    }};
    chatState.sessions.push(session);
    chatState.activeSessionId = session.id;
    saveToStorage();
    renderSessionList();
    renderChatArea();
    return session;
}}

function switchSession(sessionId) {{
    const session = chatState.sessions.find(function(s) {{ return s.id === sessionId; }});
    if (!session) return;
    chatState.activeSessionId = sessionId;

    // Restore session params to UI
    chatState.params = Object.assign({{}}, session.params);
    chatState.systemPrompt = session.systemPrompt || '';

    // Update param sliders
    const tempSlider = document.getElementById('chat-param-temp');
    const toppSlider = document.getElementById('chat-param-topp');
    const maxTokensInput = document.getElementById('chat-param-maxtokens');
    if (tempSlider) {{
        tempSlider.value = chatState.params.temperature;
        const tempVal = document.getElementById('chat-param-temp-val');
        if (tempVal) tempVal.textContent = chatState.params.temperature;
    }}
    if (toppSlider) {{
        toppSlider.value = chatState.params.top_p;
        const toppVal = document.getElementById('chat-param-topp-val');
        if (toppVal) toppVal.textContent = chatState.params.top_p;
    }}
    if (maxTokensInput) {{
        maxTokensInput.value = chatState.params.max_tokens;
    }}

    // Update system prompt textarea
    const spInput = document.getElementById('chat-system-prompt-input');
    if (spInput) spInput.value = chatState.systemPrompt;
    const spPreview = document.getElementById('chat-sp-preview');
    if (spPreview) {{
        spPreview.textContent = chatState.systemPrompt
            ? (chatState.systemPrompt.length > 50 ? chatState.systemPrompt.substring(0, 50) + '...' : chatState.systemPrompt)
            : '未设置';
    }}

    saveToStorage();
    renderSessionList();
    renderChatArea();
}}

function deleteSession(sessionId) {{
    const idx = chatState.sessions.findIndex(function(s) {{ return s.id === sessionId; }});
    if (idx === -1) return;
    chatState.sessions.splice(idx, 1);

    if (chatState.activeSessionId === sessionId) {{
        if (chatState.sessions.length > 0) {{
            // Switch to the most recent session
            const mostRecent = chatState.sessions.reduce(function(a, b) {{
                return a.updatedAt >= b.updatedAt ? a : b;
            }});
            switchSession(mostRecent.id);
            return; // switchSession already saves and renders
        }} else {{
            createSession();
            return; // createSession already saves and renders
        }}
    }}

    saveToStorage();
    renderSessionList();
}}

function saveToStorage() {{
    try {{
        const data = {{
            sessions: chatState.sessions,
            activeSessionId: chatState.activeSessionId,
            version: 1
        }};
        localStorage.setItem('kiro_chat_sessions', JSON.stringify(data));
    }} catch (e) {{
        console.error('saveToStorage error:', e);
        showToast('会话保存失败，请检查浏览器存储空间', 'warning');
    }}
}}

function loadFromStorage() {{
    try {{
        const raw = localStorage.getItem('kiro_chat_sessions');
        if (!raw) return [];
        const data = JSON.parse(raw);
        if (data && Array.isArray(data.sessions)) {{
            if (data.activeSessionId) {{
                chatState.activeSessionId = data.activeSessionId;
            }}
            return data.sessions;
        }}
        return [];
    }} catch (e) {{
        console.error('loadFromStorage error:', e);
        showToast('会话数据恢复失败，已创建新会话', 'warning');
        return [];
    }}
}}

function renderSessionList() {{
    const container = document.getElementById('chat-session-list');
    if (!container) return;
    if (chatState.sessions.length === 0) {{
        container.innerHTML = '<div class="empty-msg">暂无会话</div>';
        return;
    }}
    container.innerHTML = chatState.sessions.map(function(s) {{
        const activeClass = s.id === chatState.activeSessionId ? ' active' : '';
        return '<div class="chat-session-item' + activeClass + '" onclick="switchSession(\\'' + s.id + '\\')">' +
            '<span class="session-title">' + escapeHtml(s.title) + '</span>' +
            '<button class="session-delete" onclick="event.stopPropagation();deleteSession(\\'' + s.id + '\\')" title="删除会话">&times;</button>' +
        '</div>';
    }}).join('');
}}

function renderChatArea() {{
    const chatArea = document.getElementById('chat-area');
    const emptyState = document.getElementById('chat-empty-state');
    if (!chatArea) return;
    const session = getActiveSession();
    if (!session || session.messages.length === 0) {{
        chatArea.innerHTML = '';
        if (emptyState) {{
            chatArea.appendChild(emptyState);
            emptyState.style.display = 'flex';
        }}
        return;
    }}
    chatArea.innerHTML = '';
    if (emptyState) emptyState.style.display = 'none';
    session.messages.forEach(function(msg) {{
        chatArea.appendChild(renderMessage(msg));
    }});
    scrollChatToBottom();
}}

/* ===== Chat Playground: Parameter Panel ===== */
function clampValue(value, min, max) {{
    if (typeof value !== 'number' || isNaN(value)) return min;
    if (value < min) return min;
    if (value > max) return max;
    return value;
}}

function updateParamDisplay(paramName) {{
    if (paramName === 'temp') {{
        const slider = document.getElementById('chat-param-temp');
        const display = document.getElementById('chat-param-temp-val');
        if (slider && display) {{
            const val = parseFloat(slider.value);
            display.textContent = val.toFixed(1);
            chatState.params.temperature = val;
        }}
    }} else if (paramName === 'topp') {{
        const slider = document.getElementById('chat-param-topp');
        const display = document.getElementById('chat-param-topp-val');
        if (slider && display) {{
            const val = parseFloat(slider.value);
            display.textContent = val.toFixed(2);
            chatState.params.top_p = val;
        }}
    }}
    const session = getActiveSession();
    if (session) {{
        session.params = Object.assign({{}}, chatState.params);
        session.updatedAt = Date.now();
        saveToStorage();
    }}
}}

function toggleChatParams() {{
    const panel = document.getElementById('chat-params-panel');
    if (panel) panel.classList.toggle('collapsed');
}}

function resetChatParams() {{
    chatState.params = Object.assign({{}}, CHAT_DEFAULT_PARAMS);
    const tempSlider = document.getElementById('chat-param-temp');
    const toppSlider = document.getElementById('chat-param-topp');
    const maxTokensInput = document.getElementById('chat-param-maxtokens');
    const tempVal = document.getElementById('chat-param-temp-val');
    const toppVal = document.getElementById('chat-param-topp-val');
    if (tempSlider) tempSlider.value = CHAT_DEFAULT_PARAMS.temperature;
    if (toppSlider) toppSlider.value = CHAT_DEFAULT_PARAMS.top_p;
    if (maxTokensInput) maxTokensInput.value = CHAT_DEFAULT_PARAMS.max_tokens;
    if (tempVal) tempVal.textContent = CHAT_DEFAULT_PARAMS.temperature.toFixed(1);
    if (toppVal) toppVal.textContent = CHAT_DEFAULT_PARAMS.top_p.toFixed(2);
    const session = getActiveSession();
    if (session) {{
        session.params = Object.assign({{}}, chatState.params);
        session.updatedAt = Date.now();
        saveToStorage();
    }}
}}

// Max tokens onchange handler
(function() {{
    const el = document.getElementById('chat-param-maxtokens');
    if (el) {{
        el.addEventListener('change', function() {{
            let val = parseInt(el.value, 10);
            val = clampValue(val, 1, 32000);
            el.value = val;
            chatState.params.max_tokens = val;
            const session = getActiveSession();
            if (session) {{
                session.params = Object.assign({{}}, chatState.params);
                session.updatedAt = Date.now();
                saveToStorage();
            }}
        }});
    }}
}})();

/* ===== Chat Playground: System Prompt Editor ===== */
function toggleSystemPrompt() {{
    const panel = document.getElementById('chat-system-prompt-panel');
    if (panel) panel.classList.toggle('collapsed');
}}

function getSystemPromptPreview(text) {{
    if (!text || text.length === 0) return '未设置';
    if (text.length <= 50) return text;
    return text.substring(0, 50) + '...';
}}

function onSystemPromptChange() {{
    const textarea = document.getElementById('chat-system-prompt-input');
    if (!textarea) return;
    chatState.systemPrompt = textarea.value;
    const preview = document.getElementById('chat-sp-preview');
    if (preview) {{
        preview.textContent = getSystemPromptPreview(chatState.systemPrompt);
    }}
    const session = getActiveSession();
    if (session) {{
        session.systemPrompt = chatState.systemPrompt;
        session.updatedAt = Date.now();
        saveToStorage();
    }}
}}

/* ===== Chat Playground: Model Selector ===== */
async function loadChatModels() {{
    const selectEl = document.getElementById('chat-model-select');
    const inputEl = document.getElementById('chat-model-input');
    try {{
        const result = await apiFetch('/admin/api/models');
        if (!result || !result.data || result.data.length === 0) {{
            if (selectEl) selectEl.style.display = 'none';
            if (inputEl) inputEl.style.display = '';
            showToast('模型列表加载失败，请手动输入模型 ID', 'error');
            return;
        }}
        const models = result.data;
        if (selectEl) {{
            selectEl.innerHTML = models.map(function(m) {{
                return '<option value="' + escapeHtml(m) + '">' + escapeHtml(m) + '</option>';
            }}).join('');
            selectEl.style.display = '';
            chatState.selectedModel = models[0];
            const session = getActiveSession();
            if (session && !session.model) {{
                session.model = chatState.selectedModel;
                saveToStorage();
            }}
        }}
        if (inputEl) inputEl.style.display = 'none';
    }} catch (e) {{
        console.error('loadChatModels error:', e);
        if (selectEl) selectEl.style.display = 'none';
        if (inputEl) inputEl.style.display = '';
        showToast('模型列表加载失败，请手动输入模型 ID', 'error');
    }}
}}

// Model selector onchange handler
(function() {{
    const selectEl = document.getElementById('chat-model-select');
    if (selectEl) {{
        selectEl.addEventListener('change', function() {{
            chatState.selectedModel = selectEl.value;
            const session = getActiveSession();
            if (session) {{
                session.model = chatState.selectedModel;
                session.updatedAt = Date.now();
                saveToStorage();
            }}
        }});
    }}
}})();

/* ===== Chat Playground: StreamHandler ===== */
function parseSSELine(line) {{
    if (!line || line.trim() === '') return null;
    if (!line.startsWith('data: ')) return null;
    const data = line.substring(6);
    if (data === '[DONE]') return {{ done: true }};
    try {{
        return JSON.parse(data);
    }} catch (e) {{
        return null;
    }}
}}

async function startStream(url, payload, callbacks) {{
    const controller = new AbortController();
    chatState.abortController = controller;
    try {{
        const resp = await fetch(url, {{
            method: 'POST',
            headers: {{
                'Authorization': 'Bearer ' + apiKey,
                'Content-Type': 'application/json'
            }},
            body: JSON.stringify(payload),
            signal: controller.signal
        }});
        if (!resp.ok) {{
            let errorMsg = '请求失败（' + resp.status + '）';
            try {{
                const errBody = await resp.text();
                const errJson = JSON.parse(errBody);
                errorMsg += '：' + (errJson.error && errJson.error.message ? errJson.error.message : errJson.detail || errJson.message || errBody);
            }} catch (e) {{
                // use default errorMsg
            }}
            if (callbacks.onError) callbacks.onError(errorMsg);
            return;
        }}
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {{
            const {{ done, value }} = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, {{ stream: true }});
            const lines = buffer.split('\\n');
            buffer = lines.pop() || '';
            for (let i = 0; i < lines.length; i++) {{
                const parsed = parseSSELine(lines[i]);
                if (!parsed) continue;
                if (parsed.done) {{
                    if (callbacks.onDone) callbacks.onDone();
                    return;
                }}
                if (parsed.choices && parsed.choices.length > 0) {{
                    const delta = parsed.choices[0].delta;
                    if (delta) {{
                        if (delta.reasoning_content && callbacks.onThinking) {{
                            callbacks.onThinking(delta.reasoning_content);
                        }}
                        if (delta.content && callbacks.onContent) {{
                            callbacks.onContent(delta.content);
                        }}
                    }}
                }}
                if (parsed.usage && callbacks.onUsage) {{
                    callbacks.onUsage(parsed.usage);
                }}
            }}
        }}
        // Process remaining buffer
        if (buffer.trim()) {{
            const parsed = parseSSELine(buffer.trim());
            if (parsed) {{
                if (parsed.done) {{
                    if (callbacks.onDone) callbacks.onDone();
                }} else {{
                    if (parsed.choices && parsed.choices.length > 0) {{
                        const delta = parsed.choices[0].delta;
                        if (delta) {{
                            if (delta.reasoning_content && callbacks.onThinking) callbacks.onThinking(delta.reasoning_content);
                            if (delta.content && callbacks.onContent) callbacks.onContent(delta.content);
                        }}
                    }}
                    if (parsed.usage && callbacks.onUsage) callbacks.onUsage(parsed.usage);
                }}
            }}
        }}
        if (callbacks.onDone) callbacks.onDone();
    }} catch (err) {{
        if (err.name === 'AbortError') {{
            // User aborted — not an error
            return;
        }}
        if (callbacks.onError) callbacks.onError(err.message || '网络连接失败，请检查网关是否运行');
    }} finally {{
        chatState.abortController = null;
    }}
}}

/* ===== Chat Playground: MessageRenderer ===== */
function renderMarkdown(text) {{
    if (!text) return '';
    // Extract code blocks first to protect them
    const codeBlocks = [];
    let result = text.replace(/```(\\w*)\\n([\\s\\S]*?)```/g, function(match, lang, code) {{
        const idx = codeBlocks.length;
        const langLabel = lang ? '<span class="code-lang">' + escapeHtml(lang) + '</span>' : '';
        codeBlocks.push('<pre class="chat-code-block">' + langLabel + '<code>' + escapeHtml(code) + '</code></pre>');
        return '%%CODEBLOCK_' + idx + '%%';
    }});
    // Inline code
    result = result.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold
    result = result.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
    // Italic (single *)
    result = result.replace(/\\*(.+?)\\*/g, '<em>$1</em>');
    // Links
    result = result.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, '<a href="$2" target="_blank">$1</a>');
    // Unordered lists
    result = result.replace(/(^|\\n)(- .+(?:\\n- .+)*)/g, function(match, prefix, listBlock) {{
        const items = listBlock.split('\\n').map(function(line) {{
            return '<li>' + line.replace(/^- /, '') + '</li>';
        }}).join('');
        return prefix + '<ul>' + items + '</ul>';
    }});
    // Ordered lists
    result = result.replace(/(^|\\n)(\\d+\\. .+(?:\\n\\d+\\. .+)*)/g, function(match, prefix, listBlock) {{
        const items = listBlock.split('\\n').map(function(line) {{
            return '<li>' + line.replace(/^\\d+\\. /, '') + '</li>';
        }}).join('');
        return prefix + '<ol>' + items + '</ol>';
    }});
    // Line breaks (outside code blocks)
    result = result.replace(/\\n/g, '<br>');
    // Restore code blocks
    for (let i = 0; i < codeBlocks.length; i++) {{
        result = result.replace('%%CODEBLOCK_' + i + '%%', codeBlocks[i]);
    }}
    return result;
}}

function renderMessage(message) {{
    const div = document.createElement('div');
    if (message.role === 'user') {{
        div.className = 'chat-msg chat-msg-user';
        div.textContent = message.content;
    }} else if (message.role === 'error') {{
        div.className = 'chat-msg chat-msg-error';
        div.textContent = message.content;
    }} else {{
        div.className = 'chat-msg chat-msg-assistant';
        // Thinking block
        if (message.thinkingContent) {{
            const thinkingBlock = document.createElement('div');
            thinkingBlock.className = 'chat-thinking';
            const toggle = document.createElement('div');
            toggle.className = 'chat-thinking-toggle';
            toggle.innerHTML = '💭 思考过程 ▸';
            const content = document.createElement('div');
            content.className = 'chat-thinking-content';
            content.innerHTML = renderMarkdown(message.thinkingContent);
            toggle.addEventListener('click', function() {{
                content.classList.toggle('expanded');
                toggle.innerHTML = content.classList.contains('expanded') ? '💭 思考过程 ▾' : '💭 思考过程 ▸';
            }});
            thinkingBlock.appendChild(toggle);
            thinkingBlock.appendChild(content);
            div.appendChild(thinkingBlock);
        }}
        // Main content
        const contentDiv = document.createElement('div');
        contentDiv.className = 'chat-msg-content';
        contentDiv.innerHTML = renderMarkdown(message.content);
        div.appendChild(contentDiv);
        // Token usage
        if (message.usage) {{
            const usageDiv = document.createElement('div');
            usageDiv.className = 'chat-token-usage';
            usageDiv.textContent = 'Tokens: ' + message.usage.prompt_tokens + ' prompt + ' + message.usage.completion_tokens + ' completion = ' + message.usage.total_tokens + ' total';
            div.appendChild(usageDiv);
        }}
        // Attach preview buttons for html/svg code blocks
        attachPreviewButtons(div);
    }}
    // Copy button
    const copyBtn = document.createElement('button');
    copyBtn.className = 'chat-copy-btn';
    copyBtn.textContent = '复制';
    copyBtn.addEventListener('click', function() {{
        const textToCopy = message.role === 'assistant' ? message.content : message.content;
        navigator.clipboard.writeText(textToCopy).then(function() {{
            copyBtn.textContent = '已复制';
            setTimeout(function() {{ copyBtn.textContent = '复制'; }}, 1500);
        }}).catch(function() {{
            showToast('复制失败', 'error');
        }});
    }});
    div.appendChild(copyBtn);
    return div;
}}

function appendStreamChunk(messageEl, fullContent) {{
    const contentDiv = messageEl.querySelector('.chat-msg-content');
    if (contentDiv) {{
        contentDiv.innerHTML = renderMarkdown(fullContent);
        attachPreviewButtons(messageEl);
    }}
}}

function scrollChatToBottom() {{
    const chatArea = document.getElementById('chat-area');
    if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;
}}

/* ===== Chat Playground: sendMessage / stopGeneration ===== */
function autoResizeInput(textarea) {{
    textarea.style.height = 'auto';
    const newHeight = Math.min(Math.max(textarea.scrollHeight, 42), 150);
    textarea.style.height = newHeight + 'px';
}}

function sendMessage() {{
    const inputEl = document.getElementById('chat-input');
    if (!inputEl) return;
    const text = inputEl.value.trim();
    if (!text) return;

    const session = getActiveSession();
    if (!session) return;

    // Create user message
    const userMsg = {{
        id: generateChatUUID(),
        role: 'user',
        content: text,
        timestamp: Date.now()
    }};
    session.messages.push(userMsg);

    // Render user message
    const chatArea = document.getElementById('chat-area');
    const emptyState = document.getElementById('chat-empty-state');
    if (emptyState) emptyState.style.display = 'none';
    chatArea.appendChild(renderMessage(userMsg));

    // Clear input
    inputEl.value = '';
    autoResizeInput(inputEl);

    // Set generating state
    chatState.isGenerating = true;
    const sendBtn = document.getElementById('chat-send-btn');
    if (sendBtn) {{
        sendBtn.textContent = '停止';
        sendBtn.className = 'chat-stop-btn';
        sendBtn.onclick = stopGeneration;
    }}

    // Build messages array
    const messages = [];
    if (chatState.systemPrompt && chatState.systemPrompt.trim()) {{
        messages.push({{ role: 'system', content: chatState.systemPrompt.trim() }});
    }}
    session.messages.forEach(function(m) {{
        if (m.role === 'user' || m.role === 'assistant') {{
            messages.push({{ role: m.role, content: m.content }});
        }}
    }});

    // Get model
    const selectEl = document.getElementById('chat-model-select');
    const manualInput = document.getElementById('chat-model-input');
    const model = chatState.selectedModel || (selectEl && selectEl.value) || (manualInput && manualInput.value) || '';

    // Build payload
    const payload = {{
        model: model,
        messages: messages,
        stream: true,
        temperature: chatState.params.temperature,
        top_p: chatState.params.top_p,
        max_tokens: chatState.params.max_tokens
    }};

    // Create assistant message placeholder
    const assistantMsg = {{
        id: generateChatUUID(),
        role: 'assistant',
        content: '',
        thinkingContent: '',
        usage: null,
        timestamp: Date.now()
    }};

    // Create assistant bubble in DOM
    const assistantEl = document.createElement('div');
    assistantEl.className = 'chat-msg chat-msg-assistant';
    const thinkingBlock = document.createElement('div');
    thinkingBlock.className = 'chat-thinking';
    thinkingBlock.style.display = 'none';
    const thinkingToggle = document.createElement('div');
    thinkingToggle.className = 'chat-thinking-toggle';
    thinkingToggle.innerHTML = '💭 思考过程 ▾';
    const thinkingContent = document.createElement('div');
    thinkingContent.className = 'chat-thinking-content expanded';
    thinkingToggle.addEventListener('click', function() {{
        thinkingContent.classList.toggle('expanded');
        thinkingToggle.innerHTML = thinkingContent.classList.contains('expanded') ? '💭 思考过程 ▾' : '💭 思考过程 ▸';
    }});
    thinkingBlock.appendChild(thinkingToggle);
    thinkingBlock.appendChild(thinkingContent);
    assistantEl.appendChild(thinkingBlock);
    const contentDiv = document.createElement('div');
    contentDiv.className = 'chat-msg-content';
    assistantEl.appendChild(contentDiv);
    chatArea.appendChild(assistantEl);
    scrollChatToBottom();

    // Start streaming
    startStream('/v1/chat/completions', payload, {{
        onThinking: function(chunk) {{
            assistantMsg.thinkingContent += chunk;
            thinkingBlock.style.display = '';
            thinkingContent.innerHTML = renderMarkdown(assistantMsg.thinkingContent);
            scrollChatToBottom();
        }},
        onContent: function(chunk) {{
            assistantMsg.content += chunk;
            appendStreamChunk(assistantEl, assistantMsg.content);
            scrollChatToBottom();
        }},
        onUsage: function(usage) {{
            assistantMsg.usage = usage;
            // Render token usage
            let usageDiv = assistantEl.querySelector('.chat-token-usage');
            if (!usageDiv) {{
                usageDiv = document.createElement('div');
                usageDiv.className = 'chat-token-usage';
                assistantEl.appendChild(usageDiv);
            }}
            usageDiv.textContent = 'Tokens: ' + usage.prompt_tokens + ' prompt + ' + usage.completion_tokens + ' completion = ' + usage.total_tokens + ' total';
        }},
        onDone: function() {{
            assistantMsg.timestamp = Date.now();
            session.messages.push(assistantMsg);
            session.updatedAt = Date.now();
            saveToStorage();
            chatState.isGenerating = false;
            const btn = document.getElementById('chat-send-btn');
            if (btn) {{
                btn.textContent = '发送';
                btn.className = 'chat-send-btn';
                btn.onclick = sendMessage;
            }}
        }},
        onError: function(error) {{
            // Show error in chat area
            const errorMsg = {{
                id: generateChatUUID(),
                role: 'error',
                content: error,
                timestamp: Date.now()
            }};
            session.messages.push(errorMsg);
            chatArea.appendChild(renderMessage(errorMsg));
            scrollChatToBottom();
            saveToStorage();
            chatState.isGenerating = false;
            const btn = document.getElementById('chat-send-btn');
            if (btn) {{
                btn.textContent = '发送';
                btn.className = 'chat-send-btn';
                btn.onclick = sendMessage;
            }}
        }}
    }});
}}

function stopGeneration() {{
    if (chatState.abortController) {{
        chatState.abortController.abort();
    }}
    // Keep partial content — it's already in the DOM
    chatState.isGenerating = false;
    const btn = document.getElementById('chat-send-btn');
    if (btn) {{
        btn.textContent = '发送';
        btn.className = 'chat-send-btn';
        btn.onclick = sendMessage;
    }}
}}

/* ===== Chat Playground: Clear Conversation ===== */
function clearConversation() {{
    const session = getActiveSession();
    if (!session) return;
    session.messages = [];
    session.updatedAt = Date.now();
    saveToStorage();
    renderChatArea();
}}

/* ===== Chat Playground: Keyboard Shortcuts ===== */
(function() {{
    const inputEl = document.getElementById('chat-input');
    if (inputEl) {{
        inputEl.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter' && !e.shiftKey) {{
                e.preventDefault();
                if (!chatState.isGenerating) {{
                    sendMessage();
                }}
            }}
        }});
    }}
}})();

/* ===== Chat Playground: Export ===== */
function toggleExportMenu() {{
    const menu = document.getElementById('chat-export-menu');
    if (!menu) return;
    menu.classList.toggle('show');
    // Close on click outside
    if (menu.classList.contains('show')) {{
        setTimeout(function() {{
            function closeHandler(e) {{
                if (!menu.contains(e.target) && !e.target.closest('.chat-toolbar-actions')) {{
                    menu.classList.remove('show');
                    document.removeEventListener('click', closeHandler);
                }}
            }}
            document.addEventListener('click', closeHandler);
        }}, 0);
    }}
}}

function exportAsJSON() {{
    const session = getActiveSession();
    if (!session || session.messages.length === 0) {{
        showToast('当前会话无消息可导出', 'warning');
        return;
    }}
    const exportData = {{
        exportVersion: 1,
        exportedAt: new Date().toISOString(),
        session: {{
            title: session.title,
            model: session.model,
            params: session.params,
            systemPrompt: session.systemPrompt,
            messages: session.messages.map(function(m) {{
                const msg = {{ role: m.role, content: m.content, timestamp: m.timestamp }};
                if (m.thinkingContent) msg.thinkingContent = m.thinkingContent;
                return msg;
            }})
        }}
    }};
    const jsonStr = JSON.stringify(exportData, null, 2);
    const blob = new Blob([jsonStr], {{ type: 'application/json' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'chat-export-' + session.title + '-' + Date.now() + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    const menu = document.getElementById('chat-export-menu');
    if (menu) menu.classList.remove('show');
}}

function exportAsPNG() {{
    const session = getActiveSession();
    if (!session || session.messages.length === 0) {{
        showToast('当前会话无消息可导出', 'warning');
        return;
    }}
    const chatAreaEl = document.getElementById('chat-area');
    if (!chatAreaEl) return;
    // Show loading state on button
    const exportBtn = document.querySelector('.chat-export-menu button:last-child');
    const origText = exportBtn ? exportBtn.textContent : '';
    if (exportBtn) {{
        exportBtn.textContent = '导出中...';
        exportBtn.disabled = true;
    }}
    function doCapture() {{
        html2canvas(chatAreaEl).then(function(canvas) {{
            canvas.toBlob(function(blob) {{
                if (!blob) {{
                    showToast('截图导出失败，请重试', 'error');
                    return;
                }}
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'chat-screenshot-' + session.title + '-' + Date.now() + '.png';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }}, 'image/png');
        }}).catch(function(err) {{
            console.error('exportAsPNG error:', err);
            showToast('截图导出失败，请重试', 'error');
        }}).finally(function() {{
            if (exportBtn) {{
                exportBtn.textContent = origText;
                exportBtn.disabled = false;
            }}
            const menu = document.getElementById('chat-export-menu');
            if (menu) menu.classList.remove('show');
        }});
    }}
    // Load html2canvas from CDN if not already loaded
    if (typeof html2canvas !== 'undefined') {{
        doCapture();
    }} else {{
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
        script.onload = function() {{
            doCapture();
        }};
        script.onerror = function() {{
            showToast('截图组件加载失败，请检查网络连接', 'error');
            if (exportBtn) {{
                exportBtn.textContent = origText;
                exportBtn.disabled = false;
            }}
        }};
        document.head.appendChild(script);
    }}
}}

/* ===== Chat Playground: Content Previewer ===== */
function attachPreviewButtons(messageEl) {{
    if (!messageEl) return;
    const codeBlocks = messageEl.querySelectorAll('pre.chat-code-block');
    codeBlocks.forEach(function(pre) {{
        const langSpan = pre.querySelector('.code-lang');
        if (!langSpan) return;
        const lang = langSpan.textContent.trim().toLowerCase();
        if (lang !== 'html' && lang !== 'svg') return;
        // Avoid adding duplicate preview buttons
        if (pre.nextElementSibling && pre.nextElementSibling.classList.contains('chat-preview-btn')) return;
        const codeEl = pre.querySelector('code');
        if (!codeEl) return;
        const code = codeEl.textContent;
        const btn = document.createElement('button');
        btn.className = 'chat-preview-btn';
        btn.textContent = '预览';
        btn.addEventListener('click', function() {{
            togglePreview(btn, code, lang);
        }});
        pre.parentNode.insertBefore(btn, pre.nextSibling);
    }});
}}

function togglePreview(button, code, language) {{
    // If preview container already exists next to button, remove it
    const existing = button.nextElementSibling;
    if (existing && existing.classList.contains('chat-preview-container')) {{
        existing.remove();
        button.textContent = '预览';
        return;
    }}
    // Create preview container
    const container = document.createElement('div');
    container.className = 'chat-preview-container';
    try {{
        if (language === 'svg') {{
            container.innerHTML = code;
        }} else {{
            // HTML: use sandboxed iframe with srcdoc
            const iframe = document.createElement('iframe');
            iframe.sandbox = 'allow-same-origin';
            iframe.srcdoc = code;
            container.appendChild(iframe);
        }}
        button.textContent = '隐藏预览';
    }} catch (e) {{
        container.innerHTML = '<div style="padding:12px;color:#dc2626;font-size:13px;">内容渲染失败，请检查代码格式</div>';
    }}
    button.parentNode.insertBefore(container, button.nextSibling);
}}

/* ===== Chat Playground: Initialization ===== */
async function initChatPlayground() {{
    const sessions = loadFromStorage();
    if (sessions.length > 0) {{
        chatState.sessions = sessions;
        // Switch to the last active session (activeSessionId was restored by loadFromStorage)
        if (chatState.activeSessionId) {{
            switchSession(chatState.activeSessionId);
        }} else {{
            switchSession(sessions[sessions.length - 1].id);
        }}
    }} else {{
        createSession();
    }}
    await loadChatModels();
    renderSessionList();
    renderChatArea();
    if (!apiKey) {{
        const chatArea = document.getElementById('chat-area');
        if (chatArea) {{
            chatArea.innerHTML = '<div class="chat-empty-state" style="display:flex;"><span style="font-size:32px;">🔑</span><span>请先在系统设置中配置 API Key</span></div>';
        }}
    }}
}}
</script>
</body>
</html>"""
