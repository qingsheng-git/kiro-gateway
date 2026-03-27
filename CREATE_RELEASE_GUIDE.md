# 创建 GitHub Release 指南

## 方法 1: 通过 GitHub 网页界面（推荐）

### 步骤 1: 访问 Release 页面
打开浏览器，访问：
```
https://github.com/qingsheng-git/kiro-gateway/releases/new
```

### 步骤 2: 填写 Release 信息

**Tag version（标签版本）:**
```
v2.3.0
```

**Release title（发布标题）:**
```
Kiro Gateway v2.3.0 - Windows 独立可执行文件
```

**Description（描述）:**
复制粘贴以下内容：

```markdown
# 🎉 Windows 独立可执行文件版本

## 新功能

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

下载 `KiroGateway.exe` 文件即可使用！

**系统要求**: Windows 10/11 (64位)

## 🚀 快速开始

1. 下载 `KiroGateway.exe`
2. 配置凭据（环境变量或 .env 文件）
3. 双击运行
4. 右键托盘图标 → 点击 "Start Service"

## 配置示例

创建 `.env` 文件（与 exe 同目录）：

```env
PROXY_API_KEY=my-super-secret-password-123
REFRESH_TOKEN=your_refresh_token
KIRO_REGION=us-east-1
```

## 📚 完整文档

- [README](https://github.com/qingsheng-git/kiro-gateway/blob/main/README.md)
- [构建指南](https://github.com/qingsheng-git/kiro-gateway/blob/main/BUILD_GUIDE.md)
- [托盘模式详解](https://github.com/qingsheng-git/kiro-gateway/blob/main/TRAY_MODE.md)

## 🔧 故障排除

| 问题 | 解决方案 |
|------|---------|
| 双击无反应 | 检查系统托盘（右下角） |
| 杀毒软件报毒 | 误报，添加到白名单 |
| 服务启动失败 | 查看日志：`%USERPROFILE%\.kiro-gateway\service.log` |

---

**注意**: 首次运行可能需要几秒钟启动时间。
```

### 步骤 3: 上传文件

在 "Attach binaries" 区域：
1. 点击 "Attach binaries by dropping them here or selecting them"
2. 选择文件：`dist\KiroGateway.exe`
3. 等待上传完成（约 38 MB，可能需要几分钟）

### 步骤 4: 发布

1. 确认所有信息正确
2. 勾选 "Set as the latest release"（设为最新版本）
3. 点击 "Publish release" 按钮

---

## 方法 2: 使用 GitHub CLI（需要先安装）

### 安装 GitHub CLI

访问：https://cli.github.com/
或使用 winget：
```powershell
winget install --id GitHub.cli
```

### 创建 Release

```powershell
# 登录 GitHub
gh auth login

# 创建 Release 并上传文件
gh release create v2.3.0 `
  dist\KiroGateway.exe `
  --title "Kiro Gateway v2.3.0 - Windows 独立可执行文件" `
  --notes-file RELEASE_NOTES.md `
  --repo qingsheng-git/kiro-gateway
```

---

## 验证 Release

创建完成后，访问：
```
https://github.com/qingsheng-git/kiro-gateway/releases
```

确认：
- ✅ Release 已创建
- ✅ 标签为 v2.3.0
- ✅ KiroGateway.exe 文件已上传
- ✅ 描述信息完整
- ✅ 标记为最新版本

---

## 下载链接

Release 创建后，下载链接将是：
```
https://github.com/qingsheng-git/kiro-gateway/releases/download/v2.3.0/KiroGateway.exe
```

你可以在 README 中添加这个链接，方便用户下载。
