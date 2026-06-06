/**
 * preload.js - 预加载脚本
 * 在浏览器窗口和Node.js之间建立安全的通信桥梁
 */

const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的API到渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
    // 启动爬虫
    startCrawl: (modules, incremental) => ipcRenderer.invoke('start-crawl', modules, incremental),
    
    // 停止爬虫
    stopCrawl: () => ipcRenderer.invoke('stop-crawl'),
    
    // 启动Python服务
    startService: () => ipcRenderer.invoke('start-service'),
    
    // 停止Python服务
    stopService: () => ipcRenderer.invoke('stop-service'),
    
    // 获取服务状态
    getServiceStatus: () => ipcRenderer.invoke('get-service-status'),
    
    // 打开数据目录
    openDirectory: () => ipcRenderer.invoke('open-directory'),
    
    // 获取应用路径
    getAppPath: () => ipcRenderer.invoke('get-app-path'),
    
    // 获取数据目录路径
    getDataPath: () => ipcRenderer.invoke('get-data-path'),
    
    // 监听爬虫日志
    onCrawlerLog: (callback) => {
        ipcRenderer.on('crawler-log', (event, data) => callback(data));
    },
    
    // 监听服务状态变化
    onServiceStatus: (callback) => {
        ipcRenderer.on('service-status', (event, data) => callback(data));
    },
    
    // 监听爬虫状态变化
    onCrawlerStatus: (callback) => {
        ipcRenderer.on('crawler-status', (event, data) => callback(data));
    },
    
    // 移除爬虫日志监听
    removeCrawlerLog: () => {
        ipcRenderer.removeAllListeners('crawler-log');
    },
    
    // 移除服务状态监听
    removeServiceStatus: () => {
        ipcRenderer.removeAllListeners('service-status');
    },
    
    // 移除爬虫状态监听
    removeCrawlerStatus: () => {
        ipcRenderer.removeAllListeners('crawler-status');
    },
    
    // 平台信息
    platform: process.platform
});

console.log('Preload脚本已加载');
