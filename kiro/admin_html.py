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
</div>

<!-- Toast Container -->
<div class="toast-container" id="toast-container"></div>

<script>
/* ===== State ===== */
let apiKey = localStorage.getItem('admin_api_key') || '';
let availableModels = [];

/* ===== Tab Switching ===== */
function switchTab(tabId) {{
    document.querySelectorAll('.tab-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    }});
    document.querySelectorAll('.tab-content').forEach(content => {{
        content.classList.toggle('active', content.id === 'tab-' + tabId);
    }});
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

/* ===== API Key Settings Actions ===== */
async function saveApiKey() {{
    const input = document.getElementById('settings-apikey-input');
    const key = input.value.trim();
    if (!key) {{
        showToast('请输入 API Key', 'error');
        input.focus();
        return;
    }}
    // Call server to set the API key
    const headers = {{
        'Content-Type': 'application/json',
    }};
    // If we already have a key, send it for authorization
    if (apiKey) {{
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
    }} else {{
        renderApiKeyStatus(false);
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
        quotaEl.innerHTML = '<span style="color:#dc2626;">' + escapeHtml(result.message) + '</span>';
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
    try {{
        const resp = await fetch('/admin/api/settings/apikey/status');
        const data = await resp.json();
        const serverConfigured = data.data && data.data.configured;
        
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
    }} catch (err) {{
        console.error('Failed to check API key status:', err);
    }}
    
    if (apiKey) {{
        // Local key exists — validate and load data
        await validateAndLoad().catch(function(err) {{
            console.error('Initial validateAndLoad failed:', err);
        }});
    }} else {{
        // Server has a key but browser doesn't — prompt for key
        renderApiKeyStatus(false);
        switchTab('settings');
    }}
}});
</script>
</body>
</html>"""
