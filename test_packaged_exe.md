# Kiro Gateway 打包测试指南

## ✅ 已修复的问题

1. **NoneType 日志错误** - 修复了打包环境中 `sys.stderr` 为 `None` 的问题
2. **服务启动命令错误** - 修复了打包环境中使用错误的 uvicorn 启动命令
3. **Unicode 编码错误** - 修复了 Windows GBK 环境下无法显示所有 Unicode 字符的问题
   - 👻 (ghost emoji)
   - 💬 (chat emoji)
   - ➜ (arrow symbol)
   - ─ (horizontal line)

## 🎯 测试步骤

### 1. 检查托盘图标

- 查看系统托盘（右下角）
- 应该能看到 Kiro Gateway 图标
- 图标状态应该是"正常"（蓝色/灰色）

### 2. 测试服务启动

1. 右键点击托盘图标
2. 点击 "Start Service"
3. 等待 3-5 秒
4. 图标应该变为"运行中"状态
5. 菜单中 "Stop Service" 和 "Restart Service" 应该可用

### 3. 测试 API 功能

打开命令行，运行：

```bash
# 测试健康检查
curl http://localhost:8000/health

# 测试 API（需要配置凭证）
curl http://localhost:8000/v1/messages -H "x-api-key: qskiroproxy" -H "Content-Type: application/json" -d "{\"model\": \"claude-sonnet-4-5\", \"max_tokens\": 100, \"messages\":[{\"role\": \"user\", \"content\": \"Hello!\"}]}"
```

### 4. 测试其他功能

- **Stop Service**: 停止服务
- **Restart Service**: 重启服务
- **Open Logs**: 打开日志文件夹
- **Start with Windows**: 开机自启动（勾选/取消）
- **Exit**: 退出程序

## 📝 日志位置

所有日志文件位于：`%USERPROFILE%\.kiro-gateway\`

- `tray.log` - 托盘应用日志
- `service.log` - 服务日志
- `main.log` - 主程序日志（打包环境）

## 🐛 如果遇到问题

### 问题：托盘图标没有出现

**解决方案**：
1. 检查进程是否运行：`Get-Process KiroGateway`
2. 查看日志：`Get-Content "$env:USERPROFILE\.kiro-gateway\tray.log" -Tail 20`
3. 尝试重启程序

### 问题：服务启动失败

**可能原因**：
1. 端口被占用（8000）
2. 凭证未配置
3. 权限问题

**解决方案**：
1. 检查端口：`netstat -ano | findstr :8000`
2. 配置凭证（环境变量或 .env 文件）
3. 查看服务日志：`Get-Content "$env:USERPROFILE\.kiro-gateway\service.log" -Tail 30`

### 问题：API 调用失败

**解决方案**：
1. 确认服务已启动
2. 检查凭证配置（REFRESH_TOKEN 或 KIRO_CREDS_FILE）
3. 查看服务日志中的错误信息

## 🎉 成功标志

如果一切正常，你应该看到：

✅ 托盘图标正常显示  
✅ 右键菜单功能正常  
✅ 服务可以启动/停止/重启  
✅ API 调用返回正确响应  
✅ 日志文件正常记录  
✅ 无控制台窗口（后台运行）  

## 📦 分发说明

现在你可以：

1. 将 `dist\KiroGateway.exe` 复制到任何位置
2. 双击运行（自动托盘模式）
3. 无需 Python 环境
4. 文件大小约 40 MB

## 🔧 高级配置

### 修改端口

创建 `.env` 文件（与 exe 同目录）：

```env
SERVER_PORT=9000
```

### 配置凭证

方法 1 - 环境变量：
```
PROXY_API_KEY=your-secret-key
REFRESH_TOKEN=your-refresh-token
```

方法 2 - .env 文件：
```env
PROXY_API_KEY=your-secret-key
REFRESH_TOKEN=your-refresh-token
KIRO_REGION=us-east-1
```

方法 3 - 凭证文件（自动检测）：
```
%USERPROFILE%\.aws\sso\cache\kiro-auth-token.json
```

## 🎊 完成！

你的 Kiro Gateway 现在已经成功打包为独立的 Windows 可执行文件！

享受无需 Python 环境的便捷体验吧！ 🚀
