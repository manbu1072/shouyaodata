#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国家兽药基础数据库爬虫
URL: http://vdts.ivdc.org.cn:8099/cx/#/

合并说明：
1. 保留现有爬虫的接口调用方法和数据保存方法
2. 补充新代码中定义的7个核心模块配置
3. 使用统一的字段结构
4. 仅保存文件（JSON/CSV），不保存到数据库
"""

# 设置编码为 UTF-8
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests
import json
import time
import os
import csv
import argparse
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class VeterinaryDrugCrawler:
    """国家兽药基础数据库爬虫"""
    
    def __init__(self, data_dir=None):
        self.base_url = "http://vdts.ivdc.org.cn:8099/api/api/cx/h5"
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Origin': 'http://vdts.ivdc.org.cn:8099',
            'Referer': 'http://vdts.ivdc.org.cn:8099/cx/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 设置数据目录
        if data_dir:
            self.data_dir = data_dir
        else:
            self.data_dir = os.environ.get('DATA_DIR', 'data')
        
        # 确保数据目录存在
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
        
        # 数据模块配置（合并新旧代码，保留14个模块）
        # 7个核心模块（来自新代码） + 其他扩展模块
        self.data_modules = {
            # ========== 核心模块（7个，与Oracle数据库表对应） ==========
            'syscqyinfo': '兽药生产企业数据',
            'sycppzwh': '兽药产品批准文号数据',
            'jksyby': '进口兽用生物制品批签发数据',
            'syswzppqfgl': '国产兽用生物制品批签发数据',
            'lcsysp': '临床试验审批数据',
            'gnxsyzc': '国内新兽药注册数据',
            'jksyzc': '进口兽药注册数据',
            # ========== 扩展模块（7个） ==========
            'distributor': '兽药经营企业数据',
            'hyjdcjjg': '化药监督抽检结果数据',
            'syjdcjjg': '生药监督抽检结果数据',
            'gnsybqsms': '国内兽药说明书数据',
            'jksybqsms': '进口兽药说明书数据',
            'sygjbz': '兽药国家标准数据',
            'companyIntegrityRecord': '兽用抗菌药使用减量化达标养殖场'
        }
        
        # 模块字段映射（来自新代码的Oracle表结构）
        self.module_fields = {
            'syscqyinfo': [
                'itemid', 'qydm', 'xkzh', 'qymc', 'gmpZsh', 'cym', 'shren', 'shrq',
                'qylx', 'qyjb', 'qyzt', 'qyaddr', 'fddbr', 'lxdh', 'scfw', 'sfscjg'
            ],
            'sycppzwh': [
                'itemid', 'qydm', 'qymc', 'cpph', 'cppzwh', 'cpmc', 'cpgg', 'cpdw',
                'cpsx', 'yxq', 'scqymc', 'shren', 'shrq', 'sfyp'
            ],
            'jksyby': [
                'itemid', 'jlbh', 'spmc', 'ggxh', 'dw', 'scrq', 'yxq', 'sl',
                'fbrq', 'fbbm', 'shren', 'shrq'
            ],
            'syswzppqfgl': [
                'itemid', 'jlbh', 'spmc', 'ggxh', 'dw', 'scrq', 'yxq', 'sl',
                'fbrq', 'fbbm', 'shren', 'shrq'
            ],
            'lcsysp': [
                'itemid', 'sbh', 'sbmc', 'sbxr', 'sbxrq', 'zt', 'shren', 'shrq'
            ],
            'gnxsyzc': [
                'itemid', 'spmc', 'ggxh', 'dw', 'sfh', 'fbrq', 'shren', 'shrq'
            ],
            'jksyzc': [
                'itemid', 'spmc', 'ggxh', 'dw', 'sfh', 'fbrq', 'shren', 'shrq'
            ],
            # 扩展模块字段（通用）
            'distributor': [],
            'hyjdcjjg': [],
            'syjdcjjg': [],
            'gnsybqsms': [],
            'jksybqsms': [],
            'sygjbz': [],
            'companyIntegrityRecord': []
        }

    def get_service_list(self):
        """获取服务列表"""
        url = f"{self.base_url}/sysSjkfwll/list"
        data = {
            "page": 1,
            "rows": 100,
            "conditionItems": []
        }
        
        try:
            response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取服务列表失败: {e}")
            return None

    def get_data_list(self, code, page=1, rows=20, conditions=None):
        """
        获取数据列表
        
        Args:
            code: 数据模块代码
            page: 页码
            rows: 每页条数
            conditions: 查询条件
        """
        url = f"{self.base_url}/{code}/list"
        data = {
            "page": page,
            "rows": rows,
            "conditionItems": conditions or []
        }
        
        try:
            response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取数据失败 [{code}]: {e}")
            return None

    def get_all_data(self, code, batch_size=1000, delay=1):
        """
        获取指定模块的所有数据
        
        Args:
            code: 数据模块代码
            batch_size: 每页条数
            delay: 请求间隔(秒)
        """
        all_data = []
        
        # 获取第一页，确定总记录数
        first_page = self.get_data_list(code, page=1, rows=batch_size)
        if not first_page:
            logger.error(f"无法获取数据: {code}")
            return []
        
        # 检查返回码 - 有些接口返回code字段，有些不返回
        return_code = first_page.get('code')
        if return_code is not None and return_code != 0:
            logger.error(f"获取数据返回错误码 [{code}]: {return_code}, msg: {first_page.get('errMsg', '')}")
            return []
        
        total_records = first_page.get('records', 0)
        logger.info(f"[{code}] 总记录数: {total_records}")
        
        if total_records == 0:
            return []
        
        # 添加第一页数据
        all_data.extend(first_page.get('rows', []))
        logger.info(f"[{code}] 已获取: {len(all_data)}/{total_records}")
        
        # 计算总页数
        total_pages = (total_records + batch_size - 1) // batch_size
        
        # 获取剩余页面
        for page in range(2, total_pages + 1):
            time.sleep(delay)  # 请求间隔
            
            result = self.get_data_list(code, page=page, rows=batch_size)
            if result:
                rows = result.get('rows', [])
                if rows:
                    all_data.extend(rows)
                    logger.info(f"[{code}] 已获取: {len(all_data)}/{total_records} (第{page}/{total_pages}页)")
                else:
                    logger.warning(f"[{code}] 第{page}页无数据")
                    break
            else:
                logger.error(f"[{code}] 获取第{page}页失败")
                break
        
        return all_data

    def clean_data(self, code, data):
        """
        清洗数据，提取纯文本（移除HTML标签）
        
        Args:
            code: 模块代码
            data: 原始数据列表
            
        Returns:
            list: 清洗后的数据
        """
        if not data:
            return []
        
        cleaned_data = []
        for item in data:
            cleaned_item = {}
            for key, value in item.items():
                if isinstance(value, str):
                    # 移除HTML标签
                    import re
                    cleaned_value = re.sub(r'<[^>]+>', '', value)
                    cleaned_item[key] = cleaned_value.strip()
                else:
                    cleaned_item[key] = value
            cleaned_data.append(cleaned_item)
        
        logger.info(f"[{code}] 数据清洗完成，共 {len(cleaned_data)} 条")
        return cleaned_data

    def save_to_json(self, code, data, output_dir=None):
        """保存数据到JSON文件"""
        output_dir = output_dir or self.data_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 使用中文模块名作为文件名
        module_name = self.data_modules.get(code, code)
        filename = os.path.join(output_dir, f"{module_name}.json")
        
        # 获取定义的字段列表
        defined_fields = self.module_fields.get(code, [])
        
        # 构建输出数据结构（与新代码兼容）
        output_data = {
            'code': code,
            'name': module_name,
            'count': len(data),
            'crawl_time': datetime.now().isoformat(),
            'fields': defined_fields if defined_fields else self._extract_fields(data),
            'rows': data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"数据已保存: {filename}")
        return filename

    def _extract_fields(self, data):
        """从数据中提取字段列表"""
        if not data:
            return []
        return sorted(list(data[0].keys()))

    def save_to_csv(self, code, data, output_dir=None):
        """保存数据到CSV文件"""
        output_dir = output_dir or self.data_dir
        if not data:
            return None
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 使用中文模块名作为文件名
        module_name = self.data_modules.get(code, code)
        filename = os.path.join(output_dir, f"{module_name}.csv")
        
        # 获取所有字段
        fieldnames = set()
        for item in data:
            fieldnames.update(item.keys())
        fieldnames = sorted(list(fieldnames))
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"数据已保存到CSV: {filename}")
        return filename

    def load_existing_data(self, code, output_dir=None):
        """
        加载已有的JSON数据
        
        Args:
            code: 模块代码
            output_dir: 输出目录
            
        Returns:
            dict: 包含data和latest_date
        """
        output_dir = output_dir or self.data_dir
        module_name = self.data_modules.get(code, code)
        json_file = os.path.join(output_dir, f"{module_name}.json")
        
        if not os.path.exists(json_file):
            logger.info(f"[{code}] 现有数据文件不存在")
            return {'data': [], 'latest_date': None}
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                result = json.load(f)
                # 兼容新旧格式
                data = result.get('data', result.get('rows', []))
                logger.info(f"[{code}] 已加载现有数据: {len(data)} 条")
                return {'data': data, 'latest_date': None}
        except Exception as e:
            logger.error(f"[{code}] 加载现有数据失败: {e}")
            return {'data': [], 'latest_date': None}

    def find_latest_date(self, data):
        """
        从数据中查找最新日期
        
        Args:
            data: 数据列表
            
        Returns:
            datetime: 最新日期，或None
        """
        if not data:
            return None
        
        # 常见的日期字段名（更新为实际字段名）
        date_fields = [
            'createDate', 'updateTime', 'createTime',  # 通用字段
            'issueDate', 'approvalDate', 'effectiveDate', 'terminationDate',  # 业务字段
            'ggrq',  # 公告日期
            'cjsj', 'xgsj', 'gxsj', 'pzrq', 'shrq',  # 中文拼音缩写
            'date', 'time', 'created', 'updated',  # 英文字段
            # 补充实际数据中存在的日期字段
            'qfrq',  # 签发日期
            'yxqx', 'yxqks', 'yxqjz',  # 有效期相关
            'cprq', 'scrq', 'yxq', 'fbrq',  # 生产日期、有效期、发布日期
        ]
        
        latest_date = None
        for item in data:
            for field in date_fields:
                if field in item and item[field]:
                    try:
                        date_str = str(item[field]).strip()
                        # 常见格式: 2026-06-05 或 2026/06/05 或 2026.01.29 或 20260605
                        if '-' in date_str:
                            dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
                        elif '/' in date_str:
                            dt = datetime.strptime(date_str[:10], '%Y/%m/%d')
                        elif '.' in date_str:
                            # 处理 "2026.01.29" 或 "2026.1.6" 格式
                            parts = date_str.split('.')
                            if len(parts) >= 3:
                                year = int(parts[0])
                                month = int(parts[1])
                                day = int(parts[2].split()[0])  # 处理可能的时间部分
                                dt = datetime(year, month, day)
                            else:
                                continue
                        elif len(date_str) >= 8:
                            dt = datetime.strptime(date_str[:8], '%Y%m%d')
                        else:
                            continue
                        
                        if latest_date is None or dt > latest_date:
                            latest_date = dt
                    except:
                        continue
        
        return latest_date

    def filter_data_by_date(self, data, cutoff_date):
        """
        过滤掉截止日期及之后的数据
        
        Args:
            data: 数据列表
            cutoff_date: 截止日期（datetime对象）
            
        Returns:
            list: 过滤后的数据
        """
        if not data or cutoff_date is None:
            return data
        
        filtered = []
        # 更新为实际的日期字段名
        date_fields = [
            'createDate', 'updateTime', 'createTime',  # 通用字段
            'issueDate', 'approvalDate', 'effectiveDate', 'terminationDate',  # 业务字段
            'ggrq',  # 公告日期
            'cjsj', 'xgsj', 'gxsj', 'pzrq', 'shrq',  # 中文拼音缩写
            'date', 'time', 'created', 'updated',  # 英文字段
            # 补充实际数据中存在的日期字段
            'qfrq',  # 签发日期
            'yxqx', 'yxqks', 'yxqjz',  # 有效期相关
            'cprq', 'scrq', 'yxq', 'fbrq',  # 生产日期、有效期、发布日期
        ]
        
        for item in data:
            keep_item = True
            for field in date_fields:
                if field in item and item[field]:
                    try:
                        date_str = str(item[field]).strip()
                        if '-' in date_str:
                            dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
                        elif '/' in date_str:
                            dt = datetime.strptime(date_str[:10], '%Y/%m/%d')
                        elif '.' in date_str:
                            # 处理 "2026.01.29" 或 "2026.1.6" 格式
                            parts = date_str.split('.')
                            if len(parts) >= 3:
                                year = int(parts[0])
                                month = int(parts[1])
                                day = int(parts[2].split()[0])  # 处理可能的时间部分
                                dt = datetime(year, month, day)
                            else:
                                continue
                        elif len(date_str) >= 8:
                            dt = datetime.strptime(date_str[:8], '%Y%m%d')
                        else:
                            continue
                        
                        if dt >= cutoff_date:
                            keep_item = False
                            break
                    except:
                        continue
            
            if keep_item:
                filtered.append(item)
        
        logger.info(f"过滤前: {len(data)} 条, 过滤后: {len(filtered)} 条 (移除 {cutoff_date.strftime('%Y-%m-%d')} 及之后的数据)")
        return filtered
    
    def filter_new_data(self, new_data, existing_data):
        """
        过滤掉已存在的数据（根据ID或唯一标识）
        
        Args:
            new_data: 新下载的数据列表
            existing_data: 已存在的数据列表
            
        Returns:
            list: 过滤后的新数据
        """
        if not new_data or not existing_data:
            return new_data
        
        # 提取已存在数据的ID集合
        existing_ids = set()
        id_fields = ['itemid', 'id', 'ID', 'Id', 'uuid', 'UUID', 'code', 'CODE']
        
        for item in existing_data:
            for field in id_fields:
                if field in item and item[field]:
                    existing_ids.add(str(item[field]))
                    break
        
        # 过滤新数据
        filtered = []
        for item in new_data:
            is_new = True
            for field in id_fields:
                if field in item and item[field]:
                    if str(item[field]) in existing_ids:
                        is_new = False
                    break
            
            if is_new:
                filtered.append(item)
        
        logger.info(f"去重前: {len(new_data)} 条, 去重后: {len(filtered)} 条 (移除 {len(new_data) - len(filtered)} 条重复数据)")
        return filtered

    def crawl_module(self, code, batch_size=1000, delay=1, export_format='both', incremental=True):
        """
        爬取单个模块
        
        Args:
            code: 模块代码
            batch_size: 每页条数
            delay: 请求间隔
            export_format: 导出格式 json/csv/both
            incremental: 是否增量更新
        """
        logger.info(f"开始爬取模块: {self.data_modules.get(code, code)}")
        
        # 增量更新逻辑
        final_data = []
        latest_date = None  # 初始化 latest_date
        if incremental:
            # 加载现有数据
            existing = self.load_existing_data(code)
            existing_data = existing['data']
            
            if existing_data:
                # 查找最新日期
                latest_date = self.find_latest_date(existing_data)
                # 计算当月月初作为截止日期（每次更新从当月1号重新下载）
                today = datetime.now()
                cutoff_date = datetime(today.year, today.month, 1)
                logger.info(f"[{code}] 截止日期（删除从此日及之后的数据）: {cutoff_date.strftime('%Y-%m-%d')}")
                # 过滤现有数据
                filtered_data = self.filter_data_by_date(existing_data, cutoff_date)
                final_data = filtered_data

        # 获取新数据
        new_data = self.get_all_data(code, batch_size=batch_size, delay=delay)
        
        if new_data:
            # 清洗数据（移除HTML标签）
            cleaned_data = self.clean_data(code, new_data)
            
            # 增量模式下，过滤掉已存在的数据
            if incremental and final_data:
                cleaned_data = self.filter_new_data(cleaned_data, final_data)
                logger.info(f"[{code}] 过滤后新增数据: {len(cleaned_data)} 条")
            
            # 合并数据
            final_data.extend(cleaned_data)
            logger.info(f"[{code}] 新增数据: {len(cleaned_data)} 条, 总计: {len(final_data)} 条")
            
            # 保存
            if export_format in ('json', 'both'):
                self.save_to_json(code, final_data)
            if export_format in ('csv', 'both'):
                self.save_to_csv(code, final_data)
            
            logger.info(f"[{code}] 爬取完成，共 {len(final_data)} 条数据")
        else:
            logger.warning(f"[{code}] 未获取到新数据")
            # 如果有现有数据且获取新数据失败，保存现有数据
            if final_data:
                logger.info(f"[{code}] 保存现有数据: {len(final_data)} 条")
                if export_format in ('json', 'both'):
                    self.save_to_json(code, final_data)
                if export_format in ('csv', 'both'):
                    self.save_to_csv(code, final_data)
        
        return final_data

    def crawl_all_modules(self, delay=1, batch_size=1000, export_format='both', incremental=True):
        """爬取所有数据模块"""
        results = {}
        
        for code, name in self.data_modules.items():
            logger.info(f"\n开始爬取: {name} ({code})")
            
            data = self.crawl_module(code, batch_size=batch_size, delay=delay, export_format=export_format, incremental=incremental)
            results[code] = {
                'name': name,
                'count': len(data) if data else 0
            }
        
        return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='国家兽药基础数据库爬虫')
    parser.add_argument('--modules', nargs='+', help='指定要爬取的模块代码，例如：syscqyinfo sycppzwh')
    parser.add_argument('--incremental', action='store_true', help='启用增量更新（保留历史数据）')
    parser.add_argument('--data-dir', help='数据保存目录')
    parser.add_argument('--list-modules', action='store_true', help='列出所有可用模块')
    
    args = parser.parse_args()
    
    crawler = VeterinaryDrugCrawler(data_dir=args.data_dir)
    
    # 列出模块
    if args.list_modules:
        print("=" * 60)
        print("可用模块列表：")
        print("=" * 60)
        for code, name in crawler.data_modules.items():
            print(f"  {code}: {name}")
        return
    
    print("=" * 60)
    print("国家兽药基础数据库爬虫")
    print("=" * 60)
    
    # 获取服务列表
    print("\n【1】获取服务列表...")
    service_list = crawler.get_service_list()
    if service_list:
        print(f"服务数量: {service_list.get('records', 0)}")
        if service_list.get('rows'):
            for item in service_list['rows'][:5]:
                print(f"  - {item.get('sjkmc', '')}: {item.get('fwll', 0)}条")
    
    # 爬取指定模块或所有模块
    print("\n【2】开始爬取数据...")
    if args.modules:
        # 验证模块
        valid_modules = []
        for code in args.modules:
            if code in crawler.data_modules:
                valid_modules.append(code)
            else:
                print(f"警告: 模块 '{code}' 不存在，已跳过")
        
        if not valid_modules:
            print("错误: 没有有效的模块可爬取")
            return
        
        results = {}
        for code in valid_modules:
            print(f"\n开始爬取: {crawler.data_modules[code]} ({code})")
            data = crawler.crawl_module(code, batch_size=1000, delay=1, export_format='both', incremental=args.incremental)
            results[code] = {
                'name': crawler.data_modules[code],
                'count': len(data) if data else 0
            }
    else:
        # 爬取所有模块
        results = crawler.crawl_all_modules(batch_size=1000, delay=1, export_format='both', incremental=args.incremental)
    
    # 输出汇总
    print("\n" + "=" * 60)
    print("爬取完成！汇总如下：")
    print("=" * 60)
    total = 0
    for code, info in results.items():
        print(f"  {info['name']}: {info['count']} 条")
        total += info['count']
    print(f"\n总计: {total} 条数据")
    print(f"文件保存目录: {crawler.data_dir}/")


if __name__ == '__main__':
    main()
