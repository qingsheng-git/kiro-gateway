# Kiro Gateway - 打包指南

本指南说明如何将Kiro Gateway打包成Windows可执行文件（.exe）。

## 前置要求

1. Python 3.10 或更高版本
2. 已安装所有依赖：`pip install -r requirements.txt`
3. PyInstaller：`pip install pyinstaller`

## 快速打包

### 方法1：使用批处理脚本（推荐）

```bash
# 双击运行或在命令行执行
build.bat
```

这个脚本会：
- 自动检查并安装PyInstaller
- 清理之前的构建文件
- 使用配置文件打包应用
- 生成独立的exe文件

### 方法2：手动打包

```bash
# 安装PyInstaller
pip install pyinstaller

# 清理旧文件
rmdir /s /q build dist

# 使用spec文件打包
pyinstaller kiro_gateway.spec
```

## 打包配置说明

### kiro_gateway.spec 配置

- **console=False**: 无控制台窗口（托盘模式）
- **onefile**: 单文件可执行程序
- **icon**: 使用托盘图标作为应用图标
- **hiddenimports**: 包含所有必需的隐藏依赖
- **datas**: 打包图标资源文件

### 包含的资源

- 所有托盘图标（9个PNG文件）
- tiktoken数据文件
- uvicorn运行时文件

## 输出文件

打包完成后，可执行文件位于：

```
dist/KiroGateway.exe
```

文件大小约：50-80 MB（包含所有依赖）

## 使用打包后的程序

### 1. 首次运行

```bash
# 直接双击运行（默认托盘模式）
KiroGateway.exe

# 或使用命令行参数
KiroGateway.exe --help
KiroGateway.exe --port 9000
```

### 2. 配置文件

程序会在以下位置查找配置：

- **环境变量**：系统环境变量
- **凭证文件**：`~/.aws/sso/cache/kiro-auth-token.json`
- **设置文件**：`~/.kiro-gateway/tray_settings.json`
- **日志文件**：`~/.kiro-gateway/tray.log` 和 `service.log`

### 3. 创建快捷方式

右键点击 `KiroGateway.exe` → 发送到 → 桌面快捷方式

### 4. 开机自启动

运行程序后，右键托盘图标 → 勾选"Start with Windows"

## 命令行参数

即使打包成exe，仍然支持所有命令行参数：

```bash
KiroGateway.exe --help              # 显示帮助
KiroGateway.exe --port 9000         # 指定端口
KiroGateway.exe --host 127.0.0.1    # 指定主机
KiroGateway.exe --version           # 显示版本
```

**注意**：打包后的exe默认以托盘模式运行（无控制台窗口）

## 分发说明

### 单文件分发

只需分发 `dist/KiroGateway.exe` 文件即可，无需其他依赖。

### 完整分发包

如果需要包含配置文件示例，可以创建如下结构：

```
KiroGateway/
├── KiroGateway.exe
├── .env.example          # 配置示例
├── README.md             # 使用说明
└── TRAY_MODE.md          # 托盘模式说明
```

## 故障排除

### 问题1：打包失败 - 缺少模块

**解决方案**：在 `kiro_gateway.spec` 的 `hiddenimports` 中添加缺失的模块

```python
hiddenimports += [
    'missing_module_name',
]
```

### 问题2：运行时找不到资源文件

**解决方案**：确保资源文件在 `datas` 中正确配置

```python
datas += [
    ('source_path', 'dest_folder'),
]
```

### 问题3：exe文件过大

**解决方案**：

1. 使用UPX压缩（已在spec中启用）
2. 排除不必要的模块：

```python
excludes=[
    'pytest',
    'hypothesis',
    'matplotlib',  # 如果不需要
]
```

### 问题4：杀毒软件误报

**原因**：PyInstaller打包的exe可能被某些杀毒软件误报

**解决方案**：
1. 添加到杀毒软件白名单
2. 使用代码签名证书签名exe文件
3. 向杀毒软件厂商报告误报

### 问题5：运行时出现错误

**调试方法**：

1. 临时启用控制台窗口查看错误：
   ```python
   # 在 kiro_gateway.spec 中修改
   console=True,  # 改为 True
   ```

2. 重新打包并运行，查看错误信息

3. 检查日志文件：`%USERPROFILE%\.kiro-gateway\tray.log`

## 高级配置

### 自定义图标

替换 `assets/tray_icon.png` 为你的图标，然后重新打包。

图标要求：
- 格式：PNG 或 ICO
- 尺寸：至少 48x48 像素
- 建议提供多个尺寸：16x16, 32x32, 48x48

### 添加版本信息

创建 `version_info.txt`：

```
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(2, 3, 0, 0),
    prodvers=(2, 3, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Kiro Gateway'),
        StringStruct(u'FileDescription', u'Kiro Gateway - OpenAI/Anthropic Compatible Proxy'),
        StringStruct(u'FileVersion', u'2.3.0.0'),
        StringStruct(u'InternalName', u'KiroGateway'),
        StringStruct(u'LegalCopyright', u'AGPL-3.0'),
        StringStruct(u'OriginalFilename', u'KiroGateway.exe'),
        StringStruct(u'ProductName', u'Kiro Gateway'),
        StringStruct(u'ProductVersion', u'2.3.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
```

然后在spec文件中添加：

```python
exe = EXE(
    ...
    version='version_info.txt',
    ...
)
```

### 减小文件大小

1. **使用虚拟环境**：只安装必需的包
2. **排除测试依赖**：
   ```python
   excludes=['pytest', 'hypothesis', 'test']
   ```
3. **启用UPX压缩**（已启用）
4. **使用onedir模式**（如果不需要单文件）

## 性能优化

### 启动速度优化

1. 使用 `--onedir` 模式（多文件）而不是 `--onefile`
2. 减少隐藏导入
3. 使用延迟导入

### 运行时优化

打包后的程序性能与Python脚本相同，无额外开销。

## 持续集成

可以将打包过程集成到CI/CD流程：

```yaml
# GitHub Actions 示例
- name: Build executable
  run: |
    pip install pyinstaller
    pyinstaller kiro_gateway.spec
    
- name: Upload artifact
  uses: actions/upload-artifact@v3
  with:
    name: KiroGateway-Windows
    path: dist/KiroGateway.exe
```

## 许可证说明

打包后的可执行文件仍然遵循AGPL-3.0许可证。

分发时请确保：
1. 包含LICENSE文件
2. 提供源代码访问方式
3. 说明AGPL-3.0许可条款

## 总结

使用PyInstaller打包后：

✅ 无需Python环境即可运行  
✅ 无控制台窗口（托盘模式）  
✅ 单文件分发，方便部署  
✅ 支持所有命令行参数  
✅ 自动包含所有依赖  
✅ 支持开机自启动  

现在你可以将 `KiroGateway.exe` 分发给其他用户使用！
