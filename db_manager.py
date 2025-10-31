# db_manager.py
# 数据库管理模块，包含所有与 SQLite 数据库交互的函数。
# 负责初始化数据库、CRUD 操作、交易记录等功能。
import sqlite3
import hashlib
from typing import List, Dict, Union, Optional
from datetime import datetime
import os

# 假设项目中存在 data_utility.py 用于处理文件IO (用于导入导出功能)
try:
    import data_utility 
except ImportError:
    pass # 仅在 db_manager 中忽略导入错误，因为它的核心是数据库操作

# 默认数据库文件名
DB_NAME = 'inventory_system.db' # 建议更改为您实际使用的文件名

# --- 辅助函数 ---

def hash_password(password: str) -> str:
    """对密码进行 SHA256 哈希处理"""
    # 注意：此方法用于 settings_page.py 的密码存储（SHA256）
    return hashlib.sha256(password.encode()).hexdigest()

def _connect_db(db_path: str = DB_NAME) -> sqlite3.Connection:
    """内部函数：连接到 SQLite 数据库并设置行工厂。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # 使查询结果以字典形式返回
    return conn

# --- 数据库初始化和用户管理 ---

def initialize_database(db_path: str):
    """创建数据库文件，初始化 Inventory, Transactions, admin_user 和 config 表"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 管理员用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_user (
                id INTEGER PRIMARY PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        """)
        
        # 2. Inventory 表 (物品库存)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                reference TEXT UNIQUE,
                category TEXT,
                domain TEXT,
                unit TEXT,
                current_stock INTEGER NOT NULL DEFAULT 0,
                min_stock INTEGER NOT NULL DEFAULT 0,
                location TEXT
            )
        """)
        
        # 2.1. 检查并添加 'category' 字段 (用于迁移旧数据库)
        try:
            cursor.execute("SELECT category FROM inventory LIMIT 1")
        except sqlite3.OperationalError:
            # print("Detected old inventory schema. Running migration: ADD COLUMN category.")
            try:
                cursor.execute("ALTER TABLE inventory ADD COLUMN category TEXT DEFAULT '其他'")
            except sqlite3.OperationalError:
                pass 
        
        # 2.2. 检查并添加 'domain' 字段 (用于迁移旧数据库)
        try:
            cursor.execute("SELECT domain FROM inventory LIMIT 1")
        except sqlite3.OperationalError:
            # print("Detected old inventory schema. Running migration: ADD COLUMN domain.")
            try:
                cursor.execute("ALTER TABLE inventory ADD COLUMN domain TEXT DEFAULT '其他'")
            except sqlite3.OperationalError:
                pass
        
        # 3. Transactions 表 (交易记录)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('IN', 'OUT', 'REVERSAL-IN', 'REVERSAL-OUT')), 
                quantity INTEGER NOT NULL,
                recipient_source TEXT,
                project_ref TEXT,
                FOREIGN KEY (item_id) REFERENCES inventory(id)
            )
        """)

        # 4. Config 表 (存放自定义配置，如 Location, Unit, Project, Category, Domain 选项)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                domain TEXT, 
                value TEXT NOT NULL,
                UNIQUE(category, value) 
            )
        """)

        # 检查并插入初始管理员用户 (如果不存在)
        cursor.execute("SELECT id FROM admin_user WHERE username = 'admin'")
        if cursor.fetchone() is None:
            initial_password_hash = hash_password('123456') 
            cursor.execute("INSERT INTO admin_user (username, password) VALUES (?, ?)", 
                             ('admin', initial_password_hash))
            
        # 检查并插入默认配置选项
        default_configs = {
            'LOCATION': ["基地仓库", "大仓库", "别墅", "办公楼", "公寓", "其他"],
            'CATEGORY': ["电子元件", "机械零件", "工具", "耗材", "其他"],
            'DOMAIN': ["强电", "弱电", "给排水", "暖通", "土建", "精装", "其他"],
            'PROJECT': ["项目A", "项目B", "维护保养", "行政采购"] # 新增默认项目
        }
        for cat, values in default_configs.items():
            for val in values:
                 try:
                    cursor.execute("INSERT INTO config (category, value) VALUES (?, ?)", (cat, val,))
                 except sqlite3.IntegrityError:
                     pass
                     
        conn.commit()
    except sqlite3.Error as e:
        print(f"数据库初始化错误: {e}")
    finally:
        if conn:
            conn.close()


def check_admin_credentials(db_path: str, username: str, password: str) -> bool:
    """检查管理员用户名和密码是否匹配"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT password FROM admin_user WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if result:
            stored_password_hash = result[0]
            input_password_hash = hash_password(password)
            return stored_password_hash == input_password_hash
        return False
    except sqlite3.Error as e:
        print(f"数据库错误：认证检查失败：{e}")
        return False
    finally:
        if conn:
            conn.close()


def update_admin_password(db_path: str, new_password: str) -> bool:
    """更新数据库中的管理员密码。假设管理员 ID 为 1。"""
    hashed_password = hash_password(new_password)
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE admin_user SET password = ? WHERE id = 1
        """, (hashed_password,))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"数据库错误：更新密码失败：{e}")
        return False
    finally:
        if conn:
            conn.close()
            
# --- Config 表管理函数 ---

def get_config_options(db_path: str, category: str) -> List[str]:
    """根据 category 获取配置项列表 (例如: 'LOCATION', 'UNIT', 'CATEGORY', 'DOMAIN', 'PROJECT')"""
    conn = None
    try:
        conn = _connect_db(db_path) # 使用内部连接函数
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM config WHERE category = ? ORDER BY value", (category,))
        
        return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"数据库错误：获取配置选项失败：{e}")
        return []
    finally:
        if conn:
            conn.close()

def insert_config_option(db_path: str, category: str, value: str) -> bool:
    """插入新的配置选项"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO config (category, value) VALUES (?, ?)", (category, value.strip()))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        print(f"数据库错误：插入配置选项失败：{e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_config_option(db_path: str, category: str, value: str) -> bool:
    """删除配置选项"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM config WHERE category = ? AND value = ?", (category, value))
        
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"数据库错误：删除配置选项失败：{e}")
        return False
    finally:
        if conn:
            conn.close()
            
# --- Inventory CRUD 操作 ---

def insert_inventory_item(
    db_path: str, 
    name: str, 
    reference: str, 
    category: str,
    domain: str,
    unit: str, 
    current_stock: int, 
    min_stock: int, 
    location: str
) -> Optional[int]:
    """插入新的库存物品。"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inventory (name, reference, category, domain, unit, current_stock, min_stock, location) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, reference, category, domain, unit, current_stock, min_stock, location))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # print("错误：名称或参考编号已存在。")
        return None 
    except sqlite3.Error as e:
        print(f"数据库错误：插入物品失败：{e}")
        return None
    finally:
        if conn:
            conn.close()

def update_inventory_item(
    db_path: str, 
    item_id: int, 
    name: str, 
    reference: str, 
    category: str,
    domain: str,
    unit: str, 
    min_stock: int, 
    location: str
) -> bool:
    """更新库存物品的非库存字段。"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE inventory SET name=?, reference=?, category=?, domain=?, unit=?, min_stock=?, location=?
            WHERE id=?
        """, (name, reference, category, domain, unit, min_stock, location, item_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # print("错误：名称或参考编号已存在。")
        return False
    except sqlite3.Error as e:
        print(f"数据库错误：更新物品失败：{e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_inventory_item(db_path: str, item_id: int) -> bool:
    """删除库存物品及所有相关交易记录。"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 删除关联的交易记录
        cursor.execute("DELETE FROM transactions WHERE item_id=?", (item_id,))
        # 2. 删除库存项
        cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
        
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"数据库错误：删除物品失败：{e}")
        return False
    finally:
        if conn:
            conn.close()

def get_all_inventory(db_path: str) -> List[Dict[str, Union[int, str]]]:
    """获取所有库存物品数据"""
    conn = None
    try:
        conn = _connect_db(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"数据库错误：获取库存失败：{e}")
        return []
    finally:
        if conn:
            conn.close()
            
def get_inventory_item_by_id(db_path: str, item_id: int) -> Optional[Dict]:
    """根据 ID 获取单个库存物品详情"""
    conn = None
    try:
        conn = _connect_db(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory WHERE id=?", (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"数据库错误：获取单个库存项失败：{e}")
        return None
    finally:
        if conn:
            conn.close()

def get_inventory_names(db_path: str) -> List[Dict[str, Union[int, str]]]:
    """获取所有物品的 ID, Name, Reference, Unit, Current_Stock，用于对话框下拉列表"""
    conn = None
    try:
        conn = _connect_db(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, reference, unit, current_stock FROM inventory ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"数据库错误：获取物品名称失败：{e}")
        return []
    finally:
        if conn:
            conn.close()

def get_inventory_for_export(db_path: str) -> List[Dict[str, Union[int, str]]]:
    """获取所有库存物品数据，用于导出 CSV。"""
    conn = None
    try:
        conn = _connect_db(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, reference, category, domain, unit, current_stock, min_stock, location
            FROM inventory 
            ORDER BY name
        """)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"数据库错误：获取库存失败：{e}")
        return []
    finally:
        if conn:
            conn.close()

def get_transactions_for_export(db_path: str) -> List[Dict[str, Union[int, str]]]:
    """获取所有交易记录，包含关联的物品信息，用于导出 CSV。"""
    conn = None
    try:
        conn = _connect_db(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                t.id, t.date, t.type, t.quantity, t.recipient_source, t.project_ref,
                i.name AS item_name, i.reference AS item_reference, i.domain AS item_domain
            FROM transactions t
            JOIN inventory i ON t.item_id = i.id
            ORDER BY t.date DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"数据库错误：获取交易历史失败：{e}")
        return []
    finally:
        if conn:
            conn.close()

# --- 用于批量导入的数据库方法 ---

def batch_import_inventory(db_path: str, items: List[Dict]) -> Dict[str, int]:
    """
    批量导入或更新库存物品。使用 'reference' 作为唯一键。
    如果 'reference' 存在，则更新名称、类别、专业、单位、最小库存、位置。
    如果 'reference' 不存在，则插入新记录 (current_stock 设为 0)。
    返回包含操作统计的字典。
    """
    conn = None
    stats = {'inserted': 0, 'updated': 0, 'failed': 0}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # SQL for UPDATE
        update_sql = """
            UPDATE inventory 
            SET name=?, category=?, domain=?, unit=?, min_stock=?, location=?
            WHERE reference=?
        """
        # SQL for INSERT
        insert_sql = """
            INSERT INTO inventory (name, reference, category, domain, unit, current_stock, min_stock, location) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for item in items:
            try:
                item_category = item.get('category', '其他')
                item_domain = item.get('domain', '其他')
                
                # 1. 尝试更新
                cursor.execute(
                    update_sql, 
                    (item['name'], item_category, item_domain, item['unit'], item['min_stock'], item['location'], item['reference'])
                )
                
                if cursor.rowcount > 0:
                    stats['updated'] += 1
                else:
                    # 2. 如果没有更新任何行，则插入新行 
                    initial_stock = item.get('current_stock', 0) 
                    
                    cursor.execute(
                        insert_sql, 
                        (item['name'], item['reference'], item_category, item_domain, item['unit'], initial_stock, item['min_stock'], item['location'])
                    )
                    stats['inserted'] += 1

            except sqlite3.IntegrityError:
                stats['failed'] += 1
            except Exception:
                stats['failed'] += 1
        
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        stats['failed'] = len(items) - stats['inserted'] - stats['updated']
        print(f"数据库批量导入错误: {e}")
    finally:
        if conn:
            conn.close()
            
    return stats


# --- Transactions CRUD/业务逻辑 ---

def record_transaction(db_path: str, item_id: int, date: str, type: str, quantity: int, recipient_source: str, project_ref: str) -> bool:
    """
    记录交易并原子性地更新库存 (单笔)。
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 检查库存 (仅限 OUT 类型)
        if type == 'OUT':
            cursor.execute("SELECT current_stock FROM inventory WHERE id = ?", (item_id,))
            current_stock = cursor.fetchone()
            if current_stock is None or current_stock[0] < quantity:
                return False # 库存不足
        
        # 2. 更新库存
        stock_change = quantity if type == 'IN' else -quantity
        cursor.execute("""
            UPDATE inventory SET current_stock = current_stock + ? WHERE id = ?
        """, (stock_change, item_id))

        # 3. 记录交易
        cursor.execute("""
            INSERT INTO transactions (item_id, date, type, quantity, recipient_source, project_ref)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item_id, date, type, quantity, recipient_source, project_ref))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"数据库错误：交易记录失败：{e}")
        if conn:
            conn.rollback() 
        return False
    finally:
        if conn:
            conn.close()


def batch_record_transactions(
    db_path: str, 
    transaction_type: str, 
    recipient_source: str, 
    transactions: List[Dict[str, Union[int, str]]]
) -> Dict[str, Union[int, List[Dict]]]:
    """
    🚀 【新增功能】批量记录出库 (OUT) 或入库 (IN) 交易。
    
    :param db_path: 数据库路径
    :param transaction_type: 交易类型 ('IN' 或 'OUT')
    :param recipient_source: 接收人 (OUT) 或 来源 (IN)
    :param transactions: 包含多笔交易的列表。每项字典结构: 
                         {'item_id': int, 'quantity': int, 'project_ref': str}
    :return: 包含成功/失败计数的字典，失败的交易列表会回滚。
    """
    conn = None
    type_upper = transaction_type.upper()
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    results = {'successful_count': 0, 'failed_transactions': []}
    
    if type_upper not in ['IN', 'OUT']:
        results['failed_transactions'].append({'error': '无效的交易类型'})
        return results

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 提前获取所有物品的当前库存，减少数据库查询次数
        cursor.execute("SELECT id, current_stock FROM inventory")
        inventory_stocks = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 检查是否可以执行所有交易
        for tx in transactions:
            item_id = tx['item_id']
            quantity = tx['quantity']
            
            if item_id not in inventory_stocks:
                # 物品不存在，标记失败
                results['failed_transactions'].append(tx)
                continue
                
            if type_upper == 'OUT':
                current_stock = inventory_stocks[item_id]
                if current_stock < quantity:
                    # 库存不足，标记失败，并中断整个批次提交
                    tx['error'] = '库存不足'
                    results['failed_transactions'].append(tx)
                    raise ValueError("库存不足，批量交易中断") 
                
                # 预先扣除库存（内存中）
                inventory_stocks[item_id] -= quantity
            elif type_upper == 'IN':
                 # 预先增加库存（内存中）
                 inventory_stocks[item_id] += quantity


        # 1. 批量更新 Inventory 表
        update_inventory_batch = []
        for item_id, new_stock in inventory_stocks.items():
            # 仅更新涉及本次交易的物品，避免无意义的 UPDATE
            # 简化逻辑：我们已经知道哪些物品被修改了，但为了安全和简洁，直接对所有物品更新，或者仅对交易列表中的物品更新。
            # 这里选择只更新在 transactions 列表中的物品 (如果它们成功通过检查)
            pass

        # 针对每笔交易执行数据库操作
        for tx in transactions:
            item_id = tx['item_id']
            quantity = tx['quantity']
            project_ref = tx['project_ref']
            
            # 确保只处理通过预检的交易 (虽然 ValueError 会中断，但还是保持防御性)
            if 'error' in tx:
                continue

            stock_change = quantity if type_upper == 'IN' else -quantity
            
            # 1. 更新库存
            cursor.execute("""
                UPDATE inventory SET current_stock = current_stock + ? WHERE id = ?
            """, (stock_change, item_id))

            # 2. 记录交易
            cursor.execute("""
                INSERT INTO transactions (item_id, date, type, quantity, recipient_source, project_ref)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (item_id, current_datetime, type_upper, quantity, recipient_source, project_ref))
            
            results['successful_count'] += 1

        # 3. 提交所有成功的交易
        conn.commit()
        return results
        
    except ValueError as e:
        # 库存不足导致的预检失败，回滚所有操作
        conn.rollback()
        # 确保库存不足的错误信息被返回
        if "库存不足" in str(e):
             # results['failed_transactions'] 已经包含不足的交易
            return results
        else:
            # 其他值错误，将所有未处理的交易视为失败
             all_transactions = transactions 
             results['failed_transactions'] = all_transactions
             results['successful_count'] = 0
             return results
             
    except sqlite3.Error as e:
        # 数据库错误，回滚所有操作
        conn.rollback()
        print(f"数据库批量交易失败：{e}")
        # 将所有未处理的交易视为失败
        all_transactions = transactions 
        results['failed_transactions'] = all_transactions
        results['successful_count'] = 0
        return results
        
    finally:
        if conn:
            conn.close()


def get_transactions_history(
    db_path: str, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None, 
    tx_type: Optional[str] = None, 
    item_search: Optional[str] = None,
    category: Optional[str] = None, 
    location: Optional[str] = None,
    project: Optional[str] = None,
    domain: Optional[str] = None 
) -> List[Dict[str, Union[int, str]]]:
    """
    获取交易记录，支持按日期范围、交易类型、物品名称/编号、类别、专业、地点和项目进行筛选。
    """
    conn = None
    try:
        conn = _connect_db(db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                t.id, t.date, t.type, t.quantity, t.recipient_source, t.project_ref,
                i.name AS item_name, i.reference AS item_ref, 
                i.location AS location,
                i.category AS category,
                i.domain AS domain
            FROM transactions t
            JOIN inventory i ON t.item_id = i.id
            WHERE 1=1
        """
        params = []
        
        # 1. 日期筛选
        if start_date:
            query += " AND DATE(t.date) >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND DATE(t.date) <= ?"
            params.append(end_date)
            
        # 2. 交易类型筛选
        if tx_type and tx_type.upper() != 'ALL':
            query += " AND UPPER(t.type) = ?"
            params.append(tx_type.upper())
            
        # 3. 物品名称或编号筛选
        if item_search:
            search_pattern = f'%{item_search}%'
            query += " AND (UPPER(i.name) LIKE UPPER(?) OR UPPER(i.reference) LIKE UPPER(?))"
            params.extend([search_pattern, search_pattern])

        # 4. 类别筛选
        if category:
            query += " AND i.category = ?"
            params.append(category)

        # 5. 专业筛选 (新增)
        if domain:
            query += " AND i.domain = ?"
            params.append(domain)

        # 6. 地点筛选
        if location:
            query += " AND i.location = ?"
            params.append(location)

        # 7. 项目筛选
        if project:
            query += " AND t.project_ref = ?"
            params.append(project)

        # 排序：按日期降序
        query += " ORDER BY t.date DESC"
        
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"数据库错误：获取交易历史失败：{e}")
        return []
    finally:
        if conn:
            conn.close()
            
            
def reverse_transaction(db_path: str, tx_id: int) -> bool:
    """
    冲销交易：读取原交易，创建一笔反向交易，并原子性地更新库存。
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 获取原始交易详情
        cursor.execute("SELECT item_id, type, quantity, project_ref, recipient_source FROM transactions WHERE id = ?", (tx_id,))
        original_tx = cursor.fetchone()
        
        if not original_tx:
            return False 
        
        item_id, original_type, original_qty, project_ref, recipient_source = original_tx
        
        # 2. 确定反向操作类型和数量
        if original_type == 'IN':
            # 冲销 IN 记录：效果是减少库存，冲销类型标记为 REVERSAL-OUT
            reverse_type = 'REVERSAL-OUT' 
            stock_change = -original_qty
            new_recipient_source = f"冲销-入库 (原ID:{tx_id}, {recipient_source})" 
        elif original_type == 'OUT':
            # 冲销 OUT 记录：效果是增加库存，冲销类型标记为 REVERSAL-IN
            reverse_type = 'REVERSAL-IN' 
            stock_change = original_qty
            new_recipient_source = f"冲销-出库 (原ID:{tx_id}, {recipient_source})" 
        elif original_type.startswith('REVERSAL'): 
            return False # 禁止冲销冲销记录
        else:
            return False 

        # 3. 检查库存 (仅限需要减少库存时，即 REVERSAL-OUT)
        if stock_change < 0: 
            cursor.execute("SELECT current_stock FROM inventory WHERE id = ?", (item_id,))
            current_stock = cursor.fetchone()
            if current_stock is None or current_stock[0] < original_qty:
                return False # 库存不足以冲销
                
        # 4. 更新库存
        cursor.execute("""
            UPDATE inventory SET current_stock = current_stock + ? WHERE id = ?
        """, (stock_change, item_id))
        
        # 5. 记录反向交易
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S') 
        new_project_ref = f"冲销-原项目:{project_ref}"
        
        cursor.execute("""
            INSERT INTO transactions (item_id, date, type, quantity, recipient_source, project_ref)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item_id, current_datetime, reverse_type, original_qty, new_recipient_source, new_project_ref))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"数据库错误：冲销失败：{e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def delete_transaction(db_path: str, tx_id: int) -> bool:
    """
    删除交易记录并返还/扣除库存。
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 获取交易详情
        cursor.execute("""
            SELECT item_id, type, quantity 
            FROM transactions 
            WHERE id = ?
        """, (tx_id,))
        
        tx_record = cursor.fetchone()
        
        if not tx_record:
            return False
        
        item_id, tx_type, quantity = tx_record
        
        # 2. 计算需要返还的库存变化量
        if tx_type == 'IN':
            stock_change = -quantity # 撤销入库
        elif tx_type == 'OUT':
            stock_change = quantity # 撤销出库
        elif tx_type == 'REVERSAL-IN':
            stock_change = quantity # 撤销冲销出库
        elif tx_type == 'REVERSAL-OUT':
            stock_change = -quantity # 撤销冲销入库
        elif tx_type.startswith('REVERSAL'):
             # 理论上已被新的 REVERSAL-IN/OUT 取代，但为了旧数据兼容性，禁止删除
             return False 
        else:
            return False
        
        # 3. 检查删除后库存是否为负 (仅在减少库存时检查)
        if stock_change < 0:
            cursor.execute("SELECT current_stock FROM inventory WHERE id = ?", (item_id,))
            current_stock_result = cursor.fetchone()
            if not current_stock_result or current_stock_result[0] + stock_change < 0:
                # print(f"错误：删除此交易会导致库存为负")
                return False
        
        # 4. 更新库存
        cursor.execute("""
            UPDATE inventory 
            SET current_stock = current_stock + ? 
            WHERE id = ?
        """, (stock_change, item_id))
        
        # 5. 删除交易记录
        cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        print(f"数据库错误：删除交易失败：{e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_transaction_by_id(db_path: str, tx_id: int) -> Optional[Dict[str, Union[int, str]]]:
    """
    根据交易ID获取单个交易记录的详细信息
    """
    conn = None
    try:
        conn = _connect_db(db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                t.id, t.date, t.type, t.quantity, t.recipient_source, t.project_ref, t.item_id,
                i.name AS item_name, i.reference AS item_ref, 
                i.location AS location,
                i.category AS category,
                i.domain AS domain
            FROM transactions t
            JOIN inventory i ON t.item_id = i.id
            WHERE t.id = ?
        """
        
        cursor.execute(query, (tx_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
        
    except sqlite3.Error as e:
        print(f"数据库错误：获取交易记录失败：{e}")
        return None
    finally:
        if conn:
            conn.close()


def update_transaction(
    db_path: str,
    tx_id: int,
    quantity: int,
    date: str,
    recipient_source: str,
    project_ref: str = ""
) -> bool:
    """
    更新交易记录并自动调整库存
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 获取原始交易详情
        cursor.execute("SELECT item_id, type, quantity FROM transactions WHERE id = ?", (tx_id,))
        tx_record = cursor.fetchone()
        
        if not tx_record:
            return False
        
        item_id, tx_type, original_quantity = tx_record
        
        if tx_type.startswith('REVERSAL'): 
            # print(f"错误：不能修改冲销记录 (ID: {tx_id})。")
            return False
            
        # 2. 计算库存变化量 (总变化量 = 撤销原交易影响 + 应用新交易影响)
        if tx_type == 'IN':
            undo_change = -original_quantity
            apply_change = quantity
        else: # OUT
            undo_change = original_quantity
            apply_change = -quantity
        
        total_stock_change = undo_change + apply_change
        
        # 3. 检查修改后库存是否足够 (仅在总变化为负时检查)
        if total_stock_change < 0:
            cursor.execute("SELECT current_stock FROM inventory WHERE id = ?", (item_id,))
            current_stock_result = cursor.fetchone()
            if not current_stock_result or current_stock_result[0] + total_stock_change < 0:
                # print(f"错误：修改此交易会导致库存不足")
                return False
        
        # 4. 更新库存
        cursor.execute("""
            UPDATE inventory 
            SET current_stock = current_stock + ? 
            WHERE id = ?
        """, (total_stock_change, item_id))
        
        # 5. 更新交易记录
        cursor.execute("""
            UPDATE transactions 
            SET quantity = ?, 
                date = ?, 
                recipient_source = ?, 
                project_ref = ?
            WHERE id = ?
        """, (quantity, date, recipient_source, project_ref, tx_id))
        
        # 6. 提交事务
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        print(f"数据库错误：更新交易失败：{e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()