import csv
from typing import List, Dict, Union

def export_to_csv(data: List[Dict], filepath: str, headers: List[str]) -> bool:
    """
    将字典列表导出到 CSV 文件。
    
    :param data: 要导出的数据列表，每个元素是一个字典。
    :param filepath: 目标 CSV 文件路径。
    :param headers: CSV 文件的表头/列名列表。
    :return: 成功返回 True，失败返回 False。
    """
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            # 确保 data 中的字典键与 headers 匹配
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            
            writer.writeheader()
            writer.writerows(data)
        return True
    except Exception as e:
        print(f"导出 CSV 失败: {e}")
        return False

def import_from_csv(filepath: str) -> List[Dict[str, Union[str, int]]]:
    """
    从 CSV 文件导入数据，返回一个字典列表。
    用于导入库存数据，字段应为: name, reference, unit, current_stock, min_stock, location
    
    :param filepath: 源 CSV 文件路径。
    :return: 包含导入数据的字典列表。
    """
    items = []
    required_headers = ['name', 'reference', 'unit', 'min_stock', 'location']
    
    try:
        with open(filepath, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # 简单验证表头是否包含所有必需字段
            if not all(header in reader.fieldnames for header in required_headers):
                raise ValueError("CSV 文件缺少必需的字段 (name, reference, unit, min_stock, location)。")

            for row in reader:
                try:
                    # 尝试将 stock 字段转换为整数
                    row['current_stock'] = int(row.get('current_stock', 0)) # 默认为 0
                    row['min_stock'] = int(row['min_stock'])
                    
                    # 只保留所需的字段并添加到列表中
                    item = {
                        'name': row['name'].strip(),
                        'reference': row['reference'].strip(),
                        'unit': row['unit'].strip(),
                        'current_stock': row['current_stock'],
                        'min_stock': row['min_stock'],
                        'location': row['location'].strip()
                    }
                    items.append(item)
                except KeyError as e:
                    print(f"警告: CSV 行缺少关键字段: {e}")
                    continue # 跳过无效行
                except ValueError as e:
                    print(f"警告: 数据类型转换错误: {e}")
                    continue # 跳过包含非数字库存值的行
                    
        return items
    except FileNotFoundError:
        print(f"错误: 文件未找到 - {filepath}")
        return []
    except Exception as e:
        print(f"导入 CSV 失败: {e}")
        return []
