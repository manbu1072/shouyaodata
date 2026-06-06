
# 兽药数据爬虫 - 桌面版

两个方案可选：

| 方案 | 优点 | 缺点 |
|------|------|------|
| **Electron** | 真正的桌面应用，体验好 | 依赖Node.js，打包体积大(~150MB) |
| **PyInstaller** | 简单可靠，Python用户友好 | 需要浏览器访问 |

---

## 快速开始（推荐：PyInstaller）

最简单的方案，只需要Python环境：

```bash
# 双击运行
PyInstaller打包.bat

# 或手动执行
pip install flask requests beautifulsoup4 lxml pandas pyinstaller
pyinstaller --onefile --windowed --name "兽药数据爬虫" --add-data "app.py;." --add-data "veterinary_drug_crawler.py;." --add-data "index.html;." 启动器.py
```

然后运行 `dist\兽药数据爬虫.exe` 即可！

---

## 方案一：Electron

跨平台桌面应用，基于Electron + Python实现。

## 项目结构

```
veterinary-electron/
├── package.json              # npm配置
├── main.js                   # Electron主进程
├── preload.js                # 预加载脚本
├── index.html                # 前端页面
├── veterinary_drug_crawler.py # 爬虫核心
├── app.py                    # Flask后端
├── data/                     # 数据存储目录
└── .github/workflows/build.yml # CI/CD配置
```

## 部署步骤

### 1. 环境准备

- Node.js 18+
- Python 3.8+

### 2. 快速开始（Windows）

双击运行 `部署.bat`，或手动执行：

```bash
# 设置镜像源
npm config set registry https://registry.npmmirror.com
set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
set ELECTRON_BUILDER_BINARIES_MIRROR=https://npmmirror.com/mirrors/electron-builder-binaries/

# 安装依赖
npm install --no-audit

# 复制爬虫文件
copy ..\6a2160ee1ce211e28ededf22\veterinary_drug_crawler.py .
copy ..\6a2160ee1ce211e28ededf22\app.py .
copy ..\6a2160ee1ce211e28ededf22\index.html .

# 测试运行
npm start
```

### 3. 快速开始（macOS/Linux）

```bash
# 设置镜像源
npm config set registry https://registry.npmmirror.com
export ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
export ELECTRON_BUILDER_BINARIES_MIRROR=https://npmmirror.com/mirrors/electron-builder-binaries/

# 安装依赖
npm install --no-audit

# 复制爬虫文件
cp ../6a2160ee1ce211e28ededf22/veterinary_drug_crawler.py .
cp ../6a2160ee1ce211e28ededf22/app.py .
cp ../6a2160ee1ce211e28ededf22/index.html .

# 测试运行
npm start
```

## 打包发布

### 本地打包

```bash
# Windows打包
npm run build:win

# macOS打包（需要macOS）
npm run build:mac

# Linux打包
npm run build:linux
```

### 跨平台打包（推荐）

使用GitHub Actions自动构建：

1. 将代码推送到GitHub仓库
2. 创建Release tag
3. Actions会自动构建Windows/macOS/Linux三个版本
4. 下载发布包即可使用

## 使用说明

1. 启动应用
2. 选择需要的模块
3. 点击"开始下载"
4. 查看实时日志
5. 点击文件路径可打开数据目录

## 技术说明

### Electron架构

```
┌─────────────────────────────────┐
│         渲染进程                │
│  (index.html + 前端JS)          │
└──────────────┬──────────────────┘
               │ IPC通信
               ▼
┌─────────────────────────────────┐
│         主进程                  │
│  (main.js + 系统菜单)           │
└──────────────┬──────────────────┘
               │ 子进程
               ▼
┌─────────────────────────────────┐
│      Python爬虫进程             │
│  (veterinary_drug_crawler.py)   │
└─────────────────────────────────┘
```

### 跨平台打包原理

- **Electron应用是跨平台的** - 一套代码
- **但打包需要在对应系统上执行**
  - Windows打包Windows
  - macOS打包macOS
  - Linux打包Linux

- **GitHub Actions解决跨平台打包问题**
  - 提供Windows/macOS/Linux虚拟机
  - 自动构建所有平台版本

## 常见问题

### 1. Electron下载慢

使用淘宝镜像（已在部署脚本中配置）：
```bash
set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
```

### 2. npm install失败

清理后重试：
```bash
rmdir /s /q node_modules
del package-lock.json
npm install --no-audit
```

### 3. 如何打包macOS版本？

- 方案1：在macOS电脑上执行 `npm run build:mac`
- 方案2：使用GitHub Actions（推荐，免费）

## 项目状态

- ✅ 爬虫核心代码
- ✅ Electron应用框架
- ✅ GitHub Actions CI/CD配置
- ⏳ 待测试运行
- ⏳ 待实际打包
