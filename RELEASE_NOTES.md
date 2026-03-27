# Kiro Gateway v2.3 - Windows 可执行文件版本

## 🎉 新功能

### Windows 独立可执行文件
- ✅ **无需 Python 环境** - 直接运行，开箱即用
- ✅ **单文件分发** - 仅需一个 .exe 文件（约 38 MB）
- ✅ **系统托盘模式** - 后台运行，无控制台窗口
- ✅ **开机自启动** - 可选的 Windows 启动集成
- ✅ **完整功能** - 支持所有命令行参数和配置选项

### 系统托盘功能
- 🎯 右键菜单控制服务（启动/停止/重启）
- 📊 自动健康监控
- 🔔 Windows 通知提醒
- 📁 快速访问日志文件
- 🔄 一键开机自启动设置

## 📦 下载

### Windows 可执行文件
- **文件名**: `KiroGateway.exe`
- **大小**: 约 38.4 MB
- **系统要求**: Windows 10/11 (64位)
- **无需安装**: 下载即可运行

## 🚀 快速开始

### 1. 下载文件
下载 `KiroGateway.exe` 到任意目录

### 2. 配置凭据
选择以下任一方式：

**方式 A: 环境变量（推荐）**
```
PROXY_API_KEY=your-secret-key
REFRESH_TOKEN=your-refresh-token
```

**方式 B: 凭据文件**
```
%USERPROFILE%\.aws\sso\cache\kiro-auth-token.json
```

**方式 C: .env 文件**
在 exe 同目录创建 `.env` 文件

### 3. 运行程序
双击 `KiroGateway.exe` 即可启动！

程序会：
- 自动在系统托盘显示图标
- 无控制台窗口（后台运行）
- 右键托盘图标可控制服务

### 4. 启动服务
右键托盘图标 → 点击 "Start Service"

服务将在 `http://localhost:8000` 上运行

## 💡 使用说明

### 托盘模式（默认）
```bash
# 双击运行，自动托盘模式
KiroGateway.exe
```

### 命令行模式
```bash
# 自定义端口
KiroGateway.exe --port 9000

# 显示控制台窗口
KiroGateway.exe --no-tray

# 查看帮助
KiroGateway.exe --help
```

### 开机自启动
1. 运行程序
2. 右键托盘图标
3. 勾选 "Start with Windows"

## 📝 配置示例

创建 `.env` 文件（与 exe 同目录）：

```env
# 必需：代理服务器密码（自己设置）
PROXY_API_KEY=my-super-secret-password-123

# 必需：Kiro 刷新令牌
REFRESH_TOKEN=your_refresh_token

# 可选：区域
KIRO_REGION=us-east-1

# 可选：VPN/代理（中国用户）
VPN_PROXY_URL=http://127.0.0.1:7890
```

## 🔧 故障排除

| 问题 | 解决方案 |
|------|---------|
| 双击无反应 | 检查系统托盘（右下角），图标可能被隐藏 |
| 杀毒软件报毒 | 误报，添加到白名单即可 |
| 找不到配置 | 设置环境变量或创建 .env 文件 |
| 服务启动失败 | 查看日志：`%USERPROFILE%\.kiro-gateway\service.log` |
| 端口被占用 | 使用 `--port 9000` 指定其他端口 |

## 📁 日志位置

- 托盘应用：`%USERPROFILE%\.kiro-gateway\tray.log`
- 网关服务：`%USERPROFILE%\.kiro-gateway\service.log`
- 设置文件：`%USERPROFILE%\.kiro-gateway\tray_settings.json`

## 🌟 主要特性

- 🔌 OpenAI 兼容 API
- 🔌 Anthropic 兼容 API
- 🧠 扩展思维模式（Extended Thinking）
- 👁️ 视觉支持（Vision）
- 🛠️ 工具调用（Tool Calling）
- 📡 流式传输（Streaming）
- 🌐 VPN/代理支持
- 🔄 自动重试逻辑
- 🔐 智能令牌管理

## 📚 文档

- [完整文档](https://github.com/qingsheng-git/kiro-gateway/blob/main/README.md)
- [构建指南](https://github.com/qingsheng-git/kiro-gateway/blob/main/BUILD_GUIDE.md)
- [托盘模式详解](https://github.com/qingsheng-git/kiro-gateway/blob/main/TRAY_MODE.md)

## 🐛 问题反馈

如遇到问题，请：
1. 查看日志文件
2. 在 [GitHub Issues](https://github.com/qingsheng-git/kiro-gateway/issues) 提交问题
3. 附上日志文件和错误信息

## 📜 许可证

本项目采用 AGPL-3.0 许可证

---

**注意**: 首次运行可能需要几秒钟启动时间，这是正常现象。
