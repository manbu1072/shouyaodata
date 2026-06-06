/**
 * Electron主进程 - 国家兽药基础数据库爬虫
 * 负责窗口管理、系统菜单、进程间通信
 */

const { app, BrowserWindow, Menu, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const log = require('electron-log');

// 配置日志
log.transports.file.level = 'debug';
log.transports.console.level = 'debug';
log.info('应用启动中...');

// 全局变量
let mainWindow = null;
let pythonProcess = null;
let crawlProcess = null;
let isCrawling = false;

// 开发模式检测
const isDev = !app.isPackaged;

// 查找 Python 可执行文件
function findPythonExecutable() {
    const { execSync } = require('child_process');
    
    // 首先尝试常见的 Python 命令
    const commands = process.platform === 'win32' 
        ? ['python', 'python3', 'py']
        : ['python3', 'python'];
    
    for (const cmd of commands) {
        try {
            execSync(`${cmd} --version`, { stdio: 'pipe' });
            log.info(`找到 Python: ${cmd}`);
            return cmd;
        } catch (e) {
            continue;
        }
    }
    
    // 在 Windows 上尝试从注册表或常见路径查找
    if (process.platform === 'win32') {
        const commonPaths = [
            'C:\\Python39\\python.exe',
            'C:\\Python310\\python.exe',
            'C:\\Python311\\python.exe',
            'C:\\Python312\\python.exe',
            'C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python39\\python.exe',
            'C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python310\\python.exe',
            'C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311\\python.exe',
            'C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python312\\python.exe',
        ];
        
        for (const pyPath of commonPaths) {
            if (fs.existsSync(pyPath)) {
                log.info(`找到 Python: ${pyPath}`);
                return pyPath;
            }
        }
    }
    
    log.warn('未找到 Python，将使用默认命令');
    return process.platform === 'win32' ? 'python' : 'python3';
}

// 获取 Python 命令（缓存结果）
let pythonCmdCache = null;
function getPythonCommand() {
    if (!pythonCmdCache) {
        pythonCmdCache = findPythonExecutable();
    }
    return pythonCmdCache;
}

// 单实例检查 - 确保只有一个应用实例在运行
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
    // 如果已经有实例在运行，退出当前实例
    log.info('检测到已有实例在运行，退出当前实例');
    app.quit();
} else {
    // 当有另一个实例试图启动时
    app.on('second-instance', (event, commandLine, workingDirectory) => {
        log.info('检测到第二个实例试图启动，聚焦到主窗口');
        
        // 如果窗口被最小化或隐藏，恢复它
        if (mainWindow) {
            if (mainWindow.isMinimized()) {
                mainWindow.restore();
            }
            // 聚焦到主窗口
            if (mainWindow.isVisible()) {
                mainWindow.focus();
            } else {
                mainWindow.show();
            }
        }
    });
}

function createWindow() {
    log.info('创建主窗口...');
    
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 900,
        minHeight: 600,
        title: '兽药数据爬虫',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        show: false,
        autoHideMenuBar: false
    });

    // 创建应用菜单
    createMenu();

    // 加载页面
    const htmlPath = path.join(__dirname, 'index.html');
    log.info(`加载HTML: ${htmlPath}`);
    mainWindow.loadFile(htmlPath);

    // 窗口准备好再显示
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        log.info('主窗口已显示');
    });

    // 窗口关闭时
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function createMenu() {
    const template = [
        {
            label: '文件',
            submenu: [
                {
                    label: '打开数据目录',
                    click: () => openDataDirectory()
                },
                { type: 'separator' },
                {
                    label: '退出',
                    accelerator: 'CmdOrCtrl+Q',
                    click: () => app.quit()
                }
            ]
        },
        {
            label: '编辑',
            submenu: [
                { role: 'undo' },
                { role: 'redo' },
                { type: 'separator' },
                { role: 'cut' },
                { role: 'copy' },
                { role: 'paste' },
                { role: 'selectAll' }
            ]
        },
        {
            label: '视图',
            submenu: [
                { role: 'reload' },
                { role: 'forceReload' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'resetZoom' },
                { role: 'zoomIn' },
                { role: 'zoomOut' },
                { type: 'separator' },
                { role: 'togglefullscreen' }
            ]
        },
        {
            label: '帮助',
            submenu: [
                {
                    label: '关于',
                    click: () => showAbout()
                }
            ]
        }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
}

function openDataDirectory() {
    let dataDir;
    if (isDev) {
        dataDir = path.join(__dirname, 'data');
    } else {
        // 打包后使用用户数据目录
        dataDir = path.join(app.getPath('userData'), 'data');
    }
    if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir, { recursive: true });
    }
    shell.openPath(dataDir);
}

function showAbout() {
    dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: '关于',
        message: '兽药数据爬虫',
        detail: '版本: 1.0.0\n\n国家兽药基础数据库爬虫\n支持Windows、macOS、Linux系统'
    });
}

// IPC处理器
ipcMain.handle('start-crawl', async (event, modules, incremental) => {
    log.info(`开始爬取模块: ${modules.join(', ')}, 增量: ${incremental}`);
    
    if (isCrawling) {
        return { success: false, error: '任务正在运行中，请等待...' };
    }
    
    // 检查是否有正在运行的服务进程
    if (!pythonProcess || pythonProcess.killed) {
        return { success: false, error: '请先启动爬虫服务！' };
    }
    
    isCrawling = true;
    
    try {
        // 使用打包好的爬虫可执行文件
        // 根据平台选择正确的可执行文件扩展名
        const exeExt = process.platform === 'win32' ? '.exe' : '';
        let crawlerExe;
        
        if (isDev) {
            crawlerExe = path.join(__dirname, 'dist', `crawler${exeExt}`);
        } else {
            // 打包后，dist 在 resources 目录下，而不是 app 目录下
            crawlerExe = path.join(process.resourcesPath, 'dist', `crawler${exeExt}`);
        }
        
        log.info(`检查爬虫可执行文件是否存在: ${crawlerExe}`);
        log.info(`process.resourcesPath: ${process.resourcesPath}`);
        log.info(`__dirname: ${__dirname}`);
        
        // 检查可执行文件是否存在
        if (!fs.existsSync(crawlerExe)) {
            // 列出 resources 目录内容
            let resourcesDir = process.resourcesPath;
            log.error(`resources 目录: ${resourcesDir}`);
            try {
                if (fs.existsSync(resourcesDir)) {
                    let contents = fs.readdirSync(resourcesDir);
                    log.error(`resources 目录内容: ${JSON.stringify(contents)}`);
                    
                    let distPath = path.join(resourcesDir, 'dist');
                    if (fs.existsSync(distPath)) {
                        let distContents = fs.readdirSync(distPath);
                        log.error(`dist 目录内容: ${JSON.stringify(distContents)}`);
                    } else {
                        log.error(`dist 目录不存在: ${distPath}`);
                    }
                } else {
                    log.error(`resources 目录不存在: ${resourcesDir}`);
                }
            } catch (e) {
                log.error(`检查目录失败: ${e.message}`);
            }
            
            throw new Error(`爬虫可执行文件不存在: ${crawlerExe}\n\n请检查安装是否完整，或尝试重新安装应用。`);
        }
        
        // 设置数据目录
        let dataDir;
        if (isDev) {
            dataDir = path.join(__dirname, 'data');
        } else {
            dataDir = path.join(app.getPath('userData'), 'data');
        }
        if (!fs.existsSync(dataDir)) {
            fs.mkdirSync(dataDir, { recursive: true });
        }
        
        // 构造参数（不再需要传递脚本路径）
        const args = [];
        if (incremental) {
            args.push('--incremental');
        }
        args.push('--modules');
        args.push(...modules);
        
        log.info(`执行命令: ${crawlerExe} ${args.join(' ')}`);
        
        crawlProcess = spawn(crawlerExe, args, {
            cwd: isDev ? __dirname : app.getPath('userData'),
            env: { ...process.env, DATA_DIR: dataDir },
            stdio: ['pipe', 'pipe', 'pipe']
        });
        
        // 设置编码为 utf8
        crawlProcess.stdout.setEncoding('utf8');
        crawlProcess.stderr.setEncoding('utf8');
        
        crawlProcess.stdout.on('data', (data) => {
            const output = data.toString().trim();
            if (output) {
                log.info('Crawler: ' + output);
                if (mainWindow && !mainWindow.isDestroyed()) {
                    mainWindow.webContents.send('crawler-log', { type: 'info', message: output });
                }
            }
        });
        
        crawlProcess.stderr.on('data', (data) => {
            const output = data.toString().trim();
            if (output) {
                log.error('Crawler Error: ' + output);
                if (mainWindow && !mainWindow.isDestroyed()) {
                    mainWindow.webContents.send('crawler-log', { type: 'error', message: output });
                }
            }
        });
        
        crawlProcess.on('close', (code) => {
            log.info(`爬虫进程退出，代码: ${code}`);
            isCrawling = false;
            crawlProcess = null;
            if (mainWindow && !mainWindow.isDestroyed()) {
                // 只有正常退出（不是手动停止）时才发送完成日志
                // 但实际上 Python 脚本已经会输出"爬取完成！"
                // 所以这里只发送状态更新
                mainWindow.webContents.send('crawler-status', { running: false });
            }
        });
        
        crawlProcess.on('error', (error) => {
            log.error('爬虫进程错误:', error);
            isCrawling = false;
            crawlProcess = null;
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.webContents.send('crawler-log', { 
                    type: 'error', 
                    message: `爬虫进程错误: ${error.message}` 
                });
                mainWindow.webContents.send('crawler-status', { running: false });
            }
        });
        
        return { success: true, message: '任务已启动' };
        
    } catch (error) {
        log.error('启动爬虫失败:', error);
        isCrawling = false;
        crawlProcess = null;
        return { success: false, error: error.message };
    }
});

// 停止爬虫
ipcMain.handle('stop-crawl', async () => {
    if (crawlProcess && !crawlProcess.killed) {
        log.info('正在停止爬虫进程...');
        crawlProcess.kill('SIGTERM');
        isCrawling = false;
        crawlProcess = null;
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('crawler-log', { type: 'info', message: '爬虫任务已停止' });
            mainWindow.webContents.send('crawler-status', { running: false });
        }
        return { success: true, message: '爬虫任务已停止' };
    }
    return { success: false, error: '没有正在运行的爬虫任务' };
});

// 启动服务（使用打包好的可执行文件）
ipcMain.handle('start-service', async () => {
    if (pythonProcess && !pythonProcess.killed) {
        return { success: true, message: '服务已经在运行中', running: true };
    }
    
    try {
        // 使用打包好的服务可执行文件
        // 根据平台选择正确的可执行文件扩展名
        const exeExt = process.platform === 'win32' ? '.exe' : '';
        let serviceExe;
        
        if (isDev) {
            serviceExe = path.join(__dirname, 'dist', `service${exeExt}`);
        } else {
            serviceExe = path.join(process.resourcesPath, 'dist', `service${exeExt}`);
        }
        
        log.info(`检查服务可执行文件是否存在: ${serviceExe}`);
        log.info(`process.resourcesPath: ${process.resourcesPath}`);
        log.info(`__dirname: ${__dirname}`);
        
        // 检查可执行文件是否存在
        if (!fs.existsSync(serviceExe)) {
            // 列出 resources 目录内容
            let resourcesDir = process.resourcesPath;
            log.error(`resources 目录: ${resourcesDir}`);
            try {
                if (fs.existsSync(resourcesDir)) {
                    let contents = fs.readdirSync(resourcesDir);
                    log.error(`resources 目录内容: ${JSON.stringify(contents)}`);
                    
                    let distPath = path.join(resourcesDir, 'dist');
                    if (fs.existsSync(distPath)) {
                        let distContents = fs.readdirSync(distPath);
                        log.error(`dist 目录内容: ${JSON.stringify(distContents)}`);
                    } else {
                        log.error(`dist 目录不存在: ${distPath}`);
                    }
                } else {
                    log.error(`resources 目录不存在: ${resourcesDir}`);
                }
            } catch (e) {
                log.error(`检查目录失败: ${e.message}`);
            }
            
            throw new Error(`服务可执行文件不存在: ${serviceExe}\n\n请检查安装是否完整，或尝试重新安装应用。`);
        }
        
        log.info(`启动服务: ${serviceExe}`);
        
        pythonProcess = spawn(serviceExe, [], {
            cwd: __dirname,
            stdio: ['pipe', 'pipe', 'pipe'],
            detached: false
        });
        
        pythonProcess.stdout.setEncoding('utf8');
        pythonProcess.stderr.setEncoding('utf8');
        
        pythonProcess.stdout.on('data', (data) => {
            const output = data.toString().trim();
            if (output) {
                log.info('Service: ' + output);
            }
        });
        
        pythonProcess.stderr.on('data', (data) => {
            const output = data.toString().trim();
            if (output) {
                log.error('Service Error: ' + output);
                if (mainWindow && !mainWindow.isDestroyed()) {
                    mainWindow.webContents.send('crawler-log', { 
                        type: 'error', 
                        message: `服务错误: ${output}` 
                    });
                }
            }
        });
        
        pythonProcess.on('error', (error) => {
            log.error('服务启动失败:', error);
            log.error('错误详情:', error.stack);
            pythonProcess = null;
            const errorMsg = `服务启动失败: ${error.message}\n\n详细信息:\n- 服务路径: ${serviceExe}\n- 工作目录: ${__dirname}\n\n错误类型: ${error.code}\n${error.stack ? '堆栈信息:\n' + error.stack : ''}`;
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.webContents.send('crawler-log', { 
                    type: 'error', 
                    message: errorMsg 
                });
                mainWindow.webContents.send('service-status', { running: false });
            }
        });
        
        pythonProcess.on('close', (code) => {
            log.info(`服务进程退出，代码: ${code}`);
            pythonProcess = null;
            if (mainWindow && !mainWindow.isDestroyed()) {
                // 只发送状态更新，日志由 stop-service 处理函数发送
                mainWindow.webContents.send('service-status', { running: false });
            }
        });
        
        // 给服务一点时间启动
        await new Promise(resolve => setTimeout(resolve, 500));
        
        return { success: true, message: '服务已启动', running: true };
        
    } catch (error) {
        log.error('启动服务失败:', error);
        return { success: false, error: error.message, running: false };
    }
});

// 停止Python服务
ipcMain.handle('stop-service', async () => {
    let stoppedSomething = false;
    
    // 先停止爬虫
    if (crawlProcess && !crawlProcess.killed) {
        crawlProcess.kill('SIGTERM');
        crawlProcess = null;
        isCrawling = false;
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('crawler-log', { type: 'info', message: '爬虫任务已停止' });
            mainWindow.webContents.send('crawler-status', { running: false });
        }
        stoppedSomething = true;
    }
    
    // 停止服务
    if (pythonProcess && !pythonProcess.killed) {
        log.info('正在停止服务...');
        pythonProcess.kill('SIGTERM');
        pythonProcess = null;
        
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('crawler-log', { type: 'info', message: '服务已停止' });
            mainWindow.webContents.send('service-status', { running: false });
        }
        stoppedSomething = true;
        return { success: true, message: '服务已停止' };
    }
    
    if (!stoppedSomething) {
        return { success: false, error: '服务未运行' };
    }
    return { success: true, message: '已停止' };
});

// 获取服务状态
ipcMain.handle('get-service-status', () => {
    return { 
        running: pythonProcess && !pythonProcess.killed,
        crawling: isCrawling
    };
});

ipcMain.handle('open-directory', async () => {
    openDataDirectory();
    return { success: true };
});

ipcMain.handle('get-app-path', () => {
    return app.getAppPath();
});

ipcMain.handle('get-data-path', () => {
    let dataPath;
    if (isDev) {
        dataPath = path.join(__dirname, 'data');
    } else {
        dataPath = path.join(app.getPath('userData'), 'data');
    }
    if (!fs.existsSync(dataPath)) {
        fs.mkdirSync(dataPath, { recursive: true });
    }
    return dataPath;
});

ipcMain.handle('get-status', () => {
    return { running: isCrawling };
});

// 应用事件
app.whenReady().then(() => {
    log.info('应用已就绪');
    // 只有在获取到单实例锁时才创建窗口
    if (gotTheLock) {
        createWindow();
    }
});

app.on('window-all-closed', () => {
    log.info('所有窗口已关闭');
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    // 在 macOS 上，当点击 dock 图标且没有窗口时，重新显示窗口
    if (BrowserWindow.getAllWindows().length === 0 && gotTheLock) {
        createWindow();
    } else if (mainWindow) {
        // 如果窗口存在但被隐藏，显示它
        if (!mainWindow.isVisible()) {
            mainWindow.show();
        }
        mainWindow.focus();
    }
});

app.on('before-quit', () => {
    log.info('应用即将退出');
    // 清理进程
    if (crawlProcess && !crawlProcess.killed) {
        log.info('停止爬虫进程...');
        crawlProcess.kill('SIGTERM');
    }
    if (pythonProcess && !pythonProcess.killed) {
        log.info('停止Python服务...');
        pythonProcess.kill('SIGTERM');
    }
});

app.on('will-quit', () => {
    log.info('应用即将完全退出');
    // 确保进程已停止
    if (crawlProcess) {
        crawlProcess.kill();
    }
    if (pythonProcess) {
        pythonProcess.kill();
    }
});

process.on('uncaughtException', (error) => {
    log.error('未捕获的异常:', error);
});

process.on('unhandledRejection', (reason, promise) => {
    log.error('未处理的Promise拒绝:', reason);
});

log.info('主进程初始化完成');
