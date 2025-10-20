"""
data_utility.py
CSV 导入导出工具模块
支持库存和交易记录的导入导出功能
"""

import csv
import logging
from typing import List, Dict, Union, Optional
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CSVError(Exception):
    """CSV 操作基础异常类"""
    pass


class CSVExportError(CSVError):
    """CSV 导出异常"""
    pass


class CSVImportError(CSVError):
    """CSV 导入异常"""
    pass


def export_to_csv(
    data: List[Dict], 
    filepath: str, 
    headers: Optional[List[str]] = None
) -> bool:
    """
    将字典列表导出到 CSV 文件。
    
    :param data: 要导出的数据列表，每个元素是一个字典。
    :param filepath: 目标 CSV 文件路径。
    :param headers: CSV 文件的表头/列名列表。如果为 None，使用第一个字典的键。
    :return: 成功返回 True，失败返回 False。
    :raises CSVExportError: 当导出过程中发生严重错误时。
    """
    if not data:
        logger.warning("数据列表为空，无法导出。")
        return False
    
    # 如果没有提供 headers，使用第一个字典的键
    if headers is None:
        headers = list(data[0].keys())
    
    filepath = Path(filepath)
    
    try:
        # 确保父目录存在
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # 使用 utf-8-sig 编码，确保 Excel 正确显示中文
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(
                csvfile, 
                fieldnames=headers,
                extrasaction='ignore'  # 忽略字典中多余的键
            )
            
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"成功导出 {len(data)} 条记录到 {filepath}")
        return True
        
    except (IOError, OSError) as e:
        logger.error(f"无法写入文件 {filepath}: {e}")
        return False
    except Exception as e:
        logger.error(f"导出 CSV 失败: {e}")
        return False


def import_from_csv(filepath: str) -> List[Dict[str, Union[str, int]]]:
    """
    从 CSV 文件导入库存数据，返回一个字典列表。
    
    支持的字段:
    - 必需: name, reference, unit, min_stock, location
    - 可选: category, current_stock
    
    :param filepath: 源 CSV 文件路径。
    :return: 包含导入数据的字典列表。空列表表示导入失败或无有效数据。
    """
    items = []
    # 必需字段列表（与 db_manager.py 中的 batch_import_inventory 对应）
    required_headers = ['name', 'reference', 'unit', 'min_stock', 'location']
    
    filepath = Path(filepath)
    
    try:
        if not filepath.exists():
            logger.error(f"文件未找到: {filepath}")
            return []
        
        # 尝试多种编码方式
        encoding = _detect_encoding(filepath)
        logger.info(f"检测到文件编码: {encoding}")
        
        with open(filepath, 'r', encoding=encoding) as csvfile:
            reader = csv.DictReader(csvfile)
            
            # 去除 BOM 和空格的表头
            if reader.fieldnames:
                reader.fieldnames = [field.strip() for field in reader.fieldnames]
            
            # 验证表头是否包含所有必需字段
            missing_headers = [h for h in required_headers if h not in reader.fieldnames]
            if missing_headers:
                logger.error(f"CSV 文件缺少必需的字段: {', '.join(missing_headers)}")
                raise CSVImportError(
                    f"CSV 文件缺少必需的字段: {', '.join(missing_headers)}\n"
                    f"需要的字段: {', '.join(required_headers)}"
                )
            
            row_num = 1  # 用于错误报告（不含表头）
            skipped_rows = 0
            
            for row in reader:
                row_num += 1
                try:
                    # 处理数字字段：current_stock 和 min_stock
                    current_stock = int(row.get('current_stock', 0) or 0)
                    min_stock_str = row.get('min_stock', '0').strip()
                    
                    # 防止空字符串导致 ValueError
                    if not min_stock_str:
                        min_stock_str = '0'
                    
                    min_stock = int(min_stock_str)
                    
                    # 验证数值合法性
                    if current_stock < 0:
                        logger.warning(f"第 {row_num} 行: current_stock 为负数，已设为 0")
                        current_stock = 0
                    
                    if min_stock < 0:
                        logger.warning(f"第 {row_num} 行: min_stock 为负数，已设为 0")
                        min_stock = 0
                    
                    # 处理 category 字段（可选，默认为 '其他'）
                    category = row.get('category', '其他').strip()
                    if not category:
                        category = '其他'
                    
                    # 验证必需字段不为空
                    name = row['name'].strip()
                    reference = row['reference'].strip()
                    unit = row['unit'].strip()
                    location = row['location'].strip()
                    
                    if not all([name, reference, unit, location]):
                        logger.warning(f"第 {row_num} 行: 必需字段不能为空，已跳过")
                        skipped_rows += 1
                        continue
                    
                    # 构建物品字典（与 db_manager.batch_import_inventory 期望的格式一致）
                    item = {
                        'name': name,
                        'reference': reference,
                        'category': category,  # 新增：支持类别字段
                        'unit': unit,
                        'current_stock': current_stock,
                        'min_stock': min_stock,
                        'location': location
                    }
                    items.append(item)
                    
                except KeyError as e:
                    logger.warning(f"第 {row_num} 行: 缺少关键字段 {e}，已跳过")
                    skipped_rows += 1
                except ValueError as e:
                    logger.warning(f"第 {row_num} 行: 数据类型转换错误 ({e})，已跳过")
                    skipped_rows += 1
                except Exception as e:
                    logger.warning(f"第 {row_num} 行: 未知错误 ({e})，已跳过")
                    skipped_rows += 1
            
            # 导入总结
            if items:
                logger.info(f"成功读取 {len(items)} 条记录，跳过 {skipped_rows} 条无效记录")
            else:
                logger.warning(f"未读取到有效数据，跳过 {skipped_rows} 条无效记录")
                
        return items
        
    except FileNotFoundError:
        logger.error(f"文件未找到: {filepath}")
        return []
    except CSVImportError as e:
        logger.error(f"导入验证失败: {e}")
        return []
    except Exception as e:
        logger.error(f"导入 CSV 失败: {e}")
        return []


def validate_inventory_data(items: List[Dict]) -> tuple[List[Dict], List[str]]:
    """
    验证导入的库存数据，返回有效数据和错误信息列表。
    
    :param items: 待验证的物品列表
    :return: (有效物品列表, 错误信息列表)
    """
    valid_items = []
    errors = []
    
    seen_references = set()
    seen_names = set()
    
    for idx, item in enumerate(items, 1):
        # 检查重复的参考编号
        if item['reference'] in seen_references:
            errors.append(f"第 {idx} 项: 参考编号 '{item['reference']}' 重复")
            continue
        
        # 检查重复的名称
        if item['name'] in seen_names:
            errors.append(f"第 {idx} 项: 名称 '{item['name']}' 重复")
            continue
        
        seen_references.add(item['reference'])
        seen_names.add(item['name'])
        valid_items.append(item)
    
    return valid_items, errors


def _detect_encoding(filepath: Path) -> str:
    """
    自动检测 CSV 文件编码。
    
    尝试顺序: utf-8-sig -> utf-8 -> gbk -> gb2312 -> latin1
    
    :param filepath: 文件路径
    :return: 检测到的编码名称
    """
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1']
    
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                # 尝试读取前几行来验证编码
                for _ in range(10):
                    line = f.readline()
                    if not line:
                        break
                return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    # 如果所有编码都失败，返回 latin1（几乎不会失败但可能乱码）
    logger.warning("无法检测文件编码，使用 latin1")
    return 'latin1'


def get_csv_preview(filepath: str, max_rows: int = 5) -> Optional[List[Dict]]:
    """
    预览 CSV 文件的前几行数据。
    
    :param filepath: CSV 文件路径
    :param max_rows: 最大预览行数
    :return: 预览数据列表，失败返回 None
    """
    filepath = Path(filepath)
    
    try:
        encoding = _detect_encoding(filepath)
        with open(filepath, 'r', encoding=encoding) as csvfile:
            reader = csv.DictReader(csvfile)
            
            if reader.fieldnames:
                reader.fieldnames = [field.strip() for field in reader.fieldnames]
            
            preview = []
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                preview.append(dict(row))
            
            return preview
    except Exception as e:
        logger.error(f"预览 CSV 失败: {e}")
        return None