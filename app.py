#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国家兽药基础数据库爬虫 - Web界面
"""

import os
import sys
import threading
import logging
import subprocess
import platform
import webbrowser
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# 获取资源目录（兼容打包后的路径）
def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的路径
        base_path = sys._MEIPASS
    else:
        # 开发环境路径
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# 将当前目录加入path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from veterinary_drug_crawler import VeterinaryDrugCrawler

app = Flask(__name__, static_folder=get_resource_path('.'))
CORS(app)  # 允许跨域请求

# 存储日志到内存
log_history = []
# 爬虫实例
crawler = None
# 运行状态
is_running = False


class MemoryLogHandler(logging.Handler):
    """日志处理器，将日志保存到内存列表"""
    def emit(self, record):
        try:
            msg = self.format(record)
            log_entry = {
                'type': record.levelname.lower(),
                'message': msg,
                'time': datetime.now().strftime('%H:%M:%S')
            }
            log_history.append(log_entry)
            # 只保留最近1000条
            if len(log_history) > 1000:
                log_history.pop(0)
        except Exception:
            pass


# 配置日志handler
memory_handler = MemoryLogHandler()
memory_handler.setLevel(logging.INFO)


@app.route('/')
def index():
    """主页 - 返回静态HTML文件"""
    return send_from_directory(get_resource_path('.'), 'index.html')


@app.route('/modules', methods=['GET'])
def get_modules():
    """获取模块列表"""
    if crawler:
        return jsonify(crawler.data_modules)
    return jsonify({})


@app.route('/logs', methods=['GET'])
def get_logs():
    """获取日志（支持增量获取）"""
    since = request.args.get('since', '0')
    try:
        since_idx = int(since)
    except:
        since_idx = 0
    
    return jsonify({
        'logs': log_history[since_idx:],
        'next_since': len(log_history)
    })


@app.route('/crawl', methods=['POST'])
def crawl():
    """开始爬取"""
    global is_running
    
    if is_running:
        return jsonify({'success': False, 'message': '任务正在运行中'})
    
    data = request.json
    selected_modules = data.get('modules', [])
    incremental = data.get('incremental', True)
    
    if not selected_modules:
        return jsonify({'success': False, 'message': '请至少选择一个模块'})
    
    # 在新线程中运行爬虫
    def run_crawler():
        global is_running
        is_running = True
        
        # 添加日志handler
        root_logger = logging.getLogger()
        root_logger.addHandler(memory_handler)
        
        try:
            log_entry = {
                'type': 'info',
                'message': f'开始爬取模块: {", ".join([crawler.data_modules[code] for code in selected_modules])}',
                'time': datetime.now().strftime('%H:%M:%S')
            }
            log_history.append(log_entry)
            
            results = {}
            for code in selected_modules:
                if code in crawler.data_modules:
                    log_entry = {
                        'type': 'info',
                        'message': f'处理模块: {crawler.data_modules[code]} ({code})',
                        'time': datetime.now().strftime('%H:%M:%S')
                    }
                    log_history.append(log_entry)
                    
                    data = crawler.crawl_module(code, batch_size=1000, delay=1, export_format='both', incremental=incremental)
                    results[code] = len(data) if data else 0
            
            log_entry = {
                'type': 'info',
                'message': f'爬取完成！结果: {results}',
                'time': datetime.now().strftime('%H:%M:%S')
            }
            log_history.append(log_entry)
            
        except Exception as e:
            log_entry = {
                'type': 'error',
                'message': f'爬取出错: {str(e)}',
                'time': datetime.now().strftime('%H:%M:%S')
            }
            log_history.append(log_entry)
        finally:
            is_running = False
            root_logger.removeHandler(memory_handler)
    
    thread = threading.Thread(target=run_crawler)
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': '任务已启动'})


@app.route('/status', methods=['GET'])
def get_status():
    """获取运行状态"""
    return jsonify({'running': is_running})


@app.route('/open-dir', methods=['POST'])
def open_dir():
    """打开数据目录"""
    try:
        data_dir = os.path.abspath('data')
        
        if platform.system() == 'Windows':
            os.startfile(data_dir)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.call(['open', data_dir])
        else:  # Linux
            subprocess.call(['xdg-open', data_dir])
            
        return jsonify({'success': True, 'message': '目录已打开', 'path': data_dir})
    except Exception as e:
        return jsonify({'success': False, 'message': f'打开失败: {str(e)}'})


def start_server():
    """启动服务器"""
    # 初始化爬虫
    crawler = VeterinaryDrugCrawler()
    
    print("="*60)
    print("国家兽药基础数据库爬虫 - Web界面")
    print("访问地址: http://127.0.0.1:5000")
    print("="*60)
    print("提示: 请通过 Electron 应用界面使用爬虫")
    print("如需通过浏览器访问，请访问: http://127.0.0.1:5000")
    print("="*60)
    
    # 不自动打开浏览器，因为 Electron 应用已经提供了界面
    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    start_server()
