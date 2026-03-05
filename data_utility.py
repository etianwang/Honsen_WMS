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
    【终极修复版】从 CSV 导入数据，专治中文乱码/问号问题。
    """
    import csv
    import io
    from pathlib import Path
    
    items = []
    filepath_obj = Path(filepath)
    
    if not filepath_obj.exists():
        print(f"❌ 文件不存在: {filepath}")
        return []

    # 1. 确定编码：只试两个最可能的，成功即停
    content = ""
    final_encoding = ""
    
    # 顺序很重要：utf-8-sig 能处理带 BOM 的 UTF-8 (Excel 另存为)，gbk 处理默认保存
    for enc in ['utf-8-sig', 'gbk', 'utf-8']:
        try:
            with open(filepath_obj, 'r', encoding=enc, newline='') as f:
                content = f.read()
                final_encoding = enc
                break
        except UnicodeDecodeError:
            continue
    
    if not content:
        print(f"❌ 无法读取文件，所有编码尝试失败: {filepath}")
        return []

    print(f"ℹ️  成功使用 [{final_encoding}] 编码读取文件。")

    # 2. 转为内存文件对象
    f_io = io.StringIO(content)
    
    # 3. 创建 Reader
    reader = csv.DictReader(f_io)
    
    # 4. 【关键】清洗表头 (去除 BOM 和空格)
    if reader.fieldnames:
        cleaned_headers = [h.strip().replace('\ufeff', '') for h in reader.fieldnames]
        reader.fieldnames = cleaned_headers
        print(f"ℹ️  识别到的表头: {reader.fieldnames}")
    else:
        print("❌ CSV 文件为空或无表头")
        return []

    # 5. 验证必需字段
    required = ['name', 'reference', 'unit', 'min_stock', 'location', 'domain']
    missing = [f for f in required if f not in reader.fieldnames]
    if missing:
        print(f"❌ 缺少必需列: {missing}")
        print(f"   当前列: {reader.fieldnames}")
        return []

    # 6. 逐行解析
    has_cabinet = 'cabinet' in reader.fieldnames
    success_count = 0
    error_count = 0

    for i, row in enumerate(reader, start=2): # 从第2行开始(第1行是表头)
        try:
            # 获取并清洗数据
            name = row.get('name', '').strip()
            reference = row.get('reference', '').strip()
            
            # 🔴 调试核心：如果读出来是问号，这里立刻就能发现！
            if '?' in name or not name:
                print(f"⚠️  第 {i} 行数据异常: name='{name}' (可能是编码错误或源文件已损坏)")
                # 如果源文件本身就是 ???，那神仙也救不了，必须检查 CSV 原文件
                error_count += 1
                continue

            domain = row.get('domain', '').strip() or '其他'
            category = row.get('category', '').strip() or '其他'
            unit = row.get('unit', '').strip()
            location = row.get('location', '').strip()
            cabinet = row.get('cabinet', '').strip() if has_cabinet else ''
            
            # 数字处理
            try:
                min_stock = int(row.get('min_stock', '0').strip() or '0')
                current_stock = int(row.get('current_stock', '0').strip() or '0')
            except ValueError:
                print(f"⚠️  第 {i} 行数字格式错误，跳过")
                error_count += 1
                continue

            # 构建对象
            item = {
                'name': name,
                'reference': reference,
                'category': category,
                'domain': domain,
                'unit': unit,
                'current_stock': current_stock,
                'min_stock': min_stock,
                'location': location,
                'cabinet': cabinet
            }
            items.append(item)
            success_count += 1
            
        except Exception as e:
            print(f"⚠️  第 {i} 行解析错误: {e}")
            error_count += 1

    print(f"✅ 导入完成：成功 {success_count} 条，跳过/错误 {error_count} 条")
    return items


# def validate_inventory_data(items: List[Dict]) -> tuple[List[Dict], List[str]]:
#     """
#     验证导入的库存数据，返回有效数据和错误信息列表。
    
#     :param items: 待验证的物品列表
#     :return: (有效物品列表, 错误信息列表)
#     """
#     valid_items = []
#     errors = []
    
#     seen_references = set()
#     seen_names = set()
    
#     for idx, item in enumerate(items, 1):
#         # 检查重复的参考编号
#         if item['reference'] in seen_references:
#             errors.append(f"第 {idx} 项: 参考编号 '{item['reference']}' 重复")
#             continue
        
#         # 检查重复的名称
#         if item['name'] in seen_names:
#             errors.append(f"第 {idx} 项: 名称 '{item['name']}' 重复")
#             continue
        
#         seen_references.add(item['reference'])
#         seen_names.add(item['name'])
#         valid_items.append(item)
    
#     return valid_items, errors

def validate_inventory_data(items: List[Dict]) -> tuple[List[Dict], List[str]]:
    """
    验证导入的库存数据。
    【已修改】移除了 name 和 reference 的唯一性检查，允许重复数据导入。
    现在仅检查必需字段是否存在且非空。
    
    :param items: 待验证的物品列表
    :return: (有效物品列表, 错误信息列表)
    """
    valid_items = []
    errors = []
    
    # 定义必需字段
    required_fields = ['name', 'reference', 'unit', 'min_stock', 'location']
    
    for idx, item in enumerate(items, 1):
        has_error = False
        
        # 1. 检查必需字段是否缺失或为空
        for field in required_fields:
            value = item.get(field, '')
            if value is None or str(value).strip() == '':
                errors.append(f"第 {idx} 项: 缺少必需字段 '{field}' 或值为空")
                has_error = True
                break
        
        if has_error:
            continue
            
        # 2. (可选) 检查数字字段格式
        try:
            int(item.get('min_stock', 0))
            # current_stock 如果存在也检查一下
            if 'current_stock' in item:
                int(item.get('current_stock', 0))
        except ValueError:
            errors.append(f"第 {idx} 项: 'min_stock' 或 'current_stock' 必须是数字")
            continue
        
        # 3. 如果没有错误，加入有效列表
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