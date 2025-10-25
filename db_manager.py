# db_manager.py
# 数据库管理模块，包含所有与 SQLite 数据库交互的函数。
# 负责初始化数据库、CRUD 操作、交易记录等功能。
import sqlite3
import hashlib
from typing import List, Dict, Union, Optional
from datetime import datetime # 导入 datetime 用于事务记录
# 假设项目中存在 data_utility.py 用于处理文件IO (用于导入导出功能)
try:
    import data_utility 
except ImportError:
    pass # 仅在 db_manager 中忽略导入错误，因为它的核心是数据库操作

# --- 辅助函数 ---

def hash_password(password: str) -> str:
    """对密码进行 SHA256 哈希处理"""
    # 注意：此方法用于 settings_page.py 的密码存储（SHA256）
    return hashlib.sha256(password.encode()).hexdigest()

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
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        """)
        
        # 2. Inventory 表 (物品库存)
        # 优化: 在 CREATE TABLE 中直接包含 category 字段，以便于新建数据库
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                reference TEXT UNIQUE,
                category TEXT,
                unit TEXT,
                current_stock INTEGER NOT NULL DEFAULT 0,
                min_stock INTEGER NOT NULL DEFAULT 0,
                location TEXT
            )
        """)
        
        # 2.1. 检查并添加 'category' 字段 (用于迁移旧数据库)
        # 如果数据库是旧版本，上面的 CREATE TABLE IF NOT EXISTS 会跳过，这里尝试添加缺失的列
        try:
            cursor.execute("SELECT category FROM inventory LIMIT 1")
        except sqlite3.OperationalError:
            # 只有当 SELECT category 失败 (即列不存在) 时，才执行 ALTER TABLE
            print("Detected old inventory schema. Running migration: ADD COLUMN category.")
            try:
                cursor.execute("ALTER TABLE inventory ADD COLUMN category TEXT DEFAULT '其他'")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise # 抛出其他错误
                pass # 忽略已存在的列错误
        
        # 3. Transactions 表 (交易记录)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('IN', 'OUT', 'REVERSAL')),
                quantity INTEGER NOT NULL,
                recipient_source TEXT,
                project_ref TEXT,
                FOREIGN KEY (item_id) REFERENCES inventory(id)
            )
        """)

        # 4. 新增: Config 表 (存放自定义配置，如 Location, Unit, Project, Category 选项)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                UNIQUE(category, value) 
            )
        """)

        # 检查并插入初始管理员用户 (如果不存在)
        cursor.execute("SELECT id FROM admin_user WHERE username = 'admin'")
        if cursor.fetchone() is None:
            initial_password_hash = hash_password('123456') # 默认密码
            cursor.execute("INSERT INTO admin_user (username, password) VALUES (?, ?)", 
                            ('admin', initial_password_hash))
            
        # 检查并插入默认存放位置选项
        default_locations = ["基地仓库", "大仓库", "别墅", "办公楼", "公寓", "其他"]
        for loc in default_locations:
             try:
                 cursor.execute("INSERT INTO config (category, value) VALUES ('LOCATION', ?)", (loc,))
             except sqlite3.IntegrityError:
                 pass # 忽略已存在的项
                 
        # 检查并插入默认材料类别选项
        default_categories = ["电子元件", "机械零件", "工具", "耗材", "其他"]
        for cat in default_categories:
             try:
                 cursor.execute("INSERT INTO config (category, value) VALUES ('CATEGORY', ?)", (cat,))
             except sqlite3.IntegrityError:
                 pass # 忽略已存在的项
            
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
    """
    更新数据库中的管理员密码。假设管理员 ID 为 1。
    """
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
            
# --- Config 表管理函数 (新增) ---

def get_config_options(db_path: str, category: str) -> List[str]:
    """根据 category 获取配置项列表 (例如: 'LOCATION', 'UNIT' 或 'CATEGORY')"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE category = ? ORDER BY value", (category,))
        # 返回一个包含所有 'value' 的列表
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
        # print(f"错误：配置项 '{value}' 已存在于 '{category}' 中。")
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
    category: str, # 新增 category 参数
    unit: str, 
    current_stock: int, 
    min_stock: int, 
    location: str
) -> Optional[int]:
    """
    插入新的库存物品。
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # SQL 中新增 category 字段
        cursor.execute("""
            INSERT INTO inventory (name, reference, category, unit, current_stock, min_stock, location) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, reference, category, unit, current_stock, min_stock, location))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        print("错误：名称或参考编号已存在。")
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
    category: str, # 新增 category 参数
    unit: str, 
    min_stock: int, 
    location: str
) -> bool:
    """
    更新库存物品的非库存字段。
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # SQL 中新增 category 字段
        cursor.execute("""
            UPDATE inventory SET name=?, reference=?, category=?, unit=?, min_stock=?, location=?
            WHERE id=?
        """, (name, reference, category, unit, min_stock, location, item_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print("错误：名称或参考编号已存在。")
        return False
    except sqlite3.Error as e:
        print(f"数据库错误：更新物品失败：{e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_inventory_item(db_path: str, item_id: int) -> bool:
    """
    删除库存物品及所有相关交易记录。
    修复：确保先删除交易记录以避免外键冲突。
    """
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
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # SELECT * 语句可以安全地运行
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
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
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
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
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
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # 导出需要的列，新增 category 字段
        cursor.execute("""
            SELECT name, reference, category, unit, current_stock, min_stock, location
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
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # 导出需要的列
        cursor.execute("""
            SELECT 
                t.id, t.date, t.type, t.quantity, t.recipient_source, t.project_ref,
                i.name AS item_name, i.reference AS item_reference
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
    如果 'reference' 存在，则更新名称、类别、单位、最小库存、位置。
    如果 'reference' 不存在，则插入新记录 (current_stock 设为 0)。
    返回包含操作统计的字典。
    """
    conn = None
    stats = {'inserted': 0, 'updated': 0, 'failed': 0}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # SQL for UPDATE (基于 reference) - 新增 category
        update_sql = """
            UPDATE inventory 
            SET name=?, category=?, unit=?, min_stock=?, location=?
            WHERE reference=?
        """
        # SQL for INSERT (如果 reference 不存在) - 新增 category
        insert_sql = """
            INSERT INTO inventory (name, reference, category, unit, current_stock, min_stock, location) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        for item in items:
            try:
                # 导入时，如果 CSV/Dict 中没有 category，则默认为 '其他'
                item_category = item.get('category', '其他') 
                
                # 1. 尝试更新
                cursor.execute(
                    update_sql, 
                    (item['name'], item_category, item['unit'], item['min_stock'], item['location'], item['reference'])
                )
                
                if cursor.rowcount > 0:
                    stats['updated'] += 1
                else:
                    # 2. 如果没有更新任何行，则插入新行 
                    initial_stock = item.get('current_stock', 0) 
                    
                    cursor.execute(
                        insert_sql, 
                        (item['name'], item['reference'], item_category, item['unit'], initial_stock, item['min_stock'], item['location'])
                    )
                    stats['inserted'] += 1

            except sqlite3.IntegrityError as e:
                print(f"导入失败的项目 ({item.get('reference', 'N/A')}) - 完整性错误: {e}")
                stats['failed'] += 1
            except Exception as e:
                print(f"导入失败的项目 ({item.get('reference', 'N/A')}) - 其他错误: {e}")
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
    记录交易并原子性地更新库存。
    返回 False 如果库存不足 (OUT) 或发生数据库错误。
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
            conn.rollback() # 失败时回滚所有操作
        return False
    finally:
        if conn:
            conn.close()


def get_transactions_history(
    db_path: str, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None, 
    tx_type: Optional[str] = None, 
    item_search: Optional[str] = None,
    # --- 新增的筛选参数：类别、地点和项目 ---
    category: Optional[str] = None, 
    location: Optional[str] = None,
    project: Optional[str] = None
    # ------------------------------------
) -> List[Dict[str, Union[int, str]]]:
    """
    获取交易记录，支持按日期范围、交易类型、物品名称/编号、类别、地点和项目进行筛选。
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 基本查询语句：连接 transactions 和 inventory 表
        query = """
            SELECT 
                t.id, t.date, t.type, t.quantity, t.recipient_source, t.project_ref,
                i.name AS item_name, i.reference AS item_ref, 
                i.location AS location,
                i.category AS category
            FROM transactions t
            JOIN inventory i ON t.item_id = i.id
            WHERE 1=1
        """
        params = []
        
        # 1. 日期筛选 (使用 DATE() 函数确保精确比较日期部分)
        if start_date:
            query += " AND DATE(t.date) >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND DATE(t.date) <= ?"
            params.append(end_date)
            
        # 2. 交易类型筛选 (转换为大写进行比较)
        if tx_type and tx_type.upper() != 'ALL':
            query += " AND UPPER(t.type) = ?"
            params.append(tx_type.upper())
            
        # 3. 物品名称或编号筛选
        if item_search:
            search_pattern = f'%{item_search}%'
            query += " AND (UPPER(i.name) LIKE UPPER(?) OR UPPER(i.reference) LIKE UPPER(?))"
            params.extend([search_pattern, search_pattern])

        # 4. 类别筛选 (来自 Inventory 表)
        if category:
            query += " AND i.category = ?"
            params.append(category)

        # 5. 地点筛选 (来自 Inventory 表)
        if location:
            query += " AND i.location = ?"
            params.append(location)

        # 6. 项目筛选 (来自 Transactions 表)
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
        cursor.execute("SELECT item_id, type, quantity FROM transactions WHERE id = ?", (tx_id,))
        original_tx = cursor.fetchone()
        
        if not original_tx:
            return False 
        
        item_id, original_type, original_qty = original_tx
        
        # 2. 确定反向操作类型和数量
        if original_type == 'IN':
            reverse_type = 'REVERSAL'
            stock_change = -original_qty
            recipient_source = "冲销-IN"
        elif original_type == 'OUT':
            reverse_type = 'REVERSAL'
            stock_change = original_qty
            recipient_source = "冲销-OUT"
        else: # 避免冲销冲销记录
            return False 

        # 3. 检查库存 (仅限需要减少库存时，即冲销入库记录)
        if stock_change < 0:  # stock_change < 0 表示需要减少库存
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
        project_ref = f"Reversed TX:{tx_id}" # 记录被冲销的交易ID
        
        cursor.execute("""
            INSERT INTO transactions (item_id, date, type, quantity, recipient_source, project_ref)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item_id, current_datetime, reverse_type, original_qty, recipient_source, project_ref))
        
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
    删除交易记录并返还库存。
    - 如果是 IN 记录：从库存中减去相应数量（因为入库被取消）
    - 如果是 OUT 记录：向库存中增加相应数量（因为出库被取消）
    - 如果是 REVERSAL 记录：不建议删除，应该删除原始交易
    
    :param db_path: 数据库路径
    :param tx_id: 要删除的交易记录 ID
    :return: 成功返回 True，失败返回 False
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
            print(f"错误：交易记录 ID {tx_id} 不存在")
            return False
        
        item_id, tx_type, quantity = tx_record
        
        # 2. 计算需要返还的库存变化量
        # IN 记录删除时：减少库存（因为入库被取消）
        # OUT 记录删除时：增加库存（因为出库被取消）
        if tx_type == 'IN':
            stock_change = -quantity  # 减少库存
        elif tx_type == 'OUT':
            stock_change = quantity   # 增加库存
        elif tx_type == 'REVERSAL':
            # REVERSAL 记录的删除需要特殊处理
            # 这里简单处理：按照其类型反向操作
            # 实际上不建议删除 REVERSAL 记录
            print(f"警告：尝试删除冲销记录 (ID: {tx_id})，建议删除原始交易记录")
            # 暂时按照记录类型处理
            stock_change = -quantity if tx_type == 'IN' else quantity
        else:
            print(f"错误：未知的交易类型 {tx_type}")
            return False
        
        # 3. 检查删除后库存是否为负（仅当需要减少库存时）
        if stock_change < 0:
            cursor.execute("""
                SELECT current_stock 
                FROM inventory 
                WHERE id = ?
            """, (item_id,))
            
            current_stock_result = cursor.fetchone()
            if not current_stock_result:
                print(f"错误：物品 ID {item_id} 不存在")
                return False
                
            current_stock = current_stock_result[0]
            
            # 检查删除后库存是否足够
            if current_stock + stock_change < 0:
                print(f"错误：删除此交易会导致库存为负 (当前: {current_stock}, 变化: {stock_change})")
                return False
        
        # 4. 更新库存
        cursor.execute("""
            UPDATE inventory 
            SET current_stock = current_stock + ? 
            WHERE id = ?
        """, (stock_change, item_id))
        
        # 5. 删除交易记录
        cursor.execute("""
            DELETE FROM transactions 
            WHERE id = ?
        """, (tx_id,))
        
        # 6. 提交事务
        conn.commit()
        
        print(f"成功删除交易记录 ID {tx_id}，库存已返还 (变化: {stock_change})")
        return True
        
    except sqlite3.Error as e:
        print(f"数据库错误：删除交易失败：{e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"未知错误：删除交易失败：{e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_transaction_by_id(db_path: str, tx_id: int) -> Optional[Dict[str, Union[int, str]]]:
    """
    根据交易ID获取单个交易记录的详细信息
    
    :param db_path: 数据库路径
    :param tx_id: 交易记录 ID
    :return: 交易记录字典，如果不存在返回 None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT 
                t.id, t.date, t.type, t.quantity, t.recipient_source, t.project_ref, t.item_id,
                i.name AS item_name, i.reference AS item_ref, 
                i.location AS location,
                i.category AS category
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
    
    工作原理：
    1. 先撤销原交易对库存的影响（反向操作）
    2. 再应用新交易对库存的影响（正向操作）
    
    :param db_path: 数据库路径
    :param tx_id: 要更新的交易记录 ID
    :param quantity: 新的数量
    :param date: 新的日期时间
    :param recipient_source: 新的接收人/来源
    :param project_ref: 新的项目参考（仅出库时使用）
    :return: 成功返回 True，失败返回 False
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 获取原始交易详情
        cursor.execute("""
            SELECT item_id, type, quantity 
            FROM transactions 
            WHERE id = ?
        """, (tx_id,))
        
        tx_record = cursor.fetchone()
        
        if not tx_record:
            print(f"错误：交易记录 ID {tx_id} 不存在")
            return False
        
        item_id, tx_type, original_quantity = tx_record
        
        # 2. 计算库存变化量
        # 步骤A: 先撤销原交易的影响
        if tx_type == 'IN':
            undo_change = -original_quantity  # 撤销入库：减少库存
        else:  # OUT
            undo_change = original_quantity   # 撤销出库：增加库存
        
        # 步骤B: 再应用新交易的影响
        if tx_type == 'IN':
            apply_change = quantity  # 应用新入库：增加库存
        else:  # OUT
            apply_change = -quantity  # 应用新出库：减少库存
        
        # 总变化量 = 撤销 + 应用
        total_stock_change = undo_change + apply_change
        
        # 3. 检查修改后库存是否足够（仅当总变化量为负时）
        if total_stock_change < 0:
            cursor.execute("""
                SELECT current_stock 
                FROM inventory 
                WHERE id = ?
            """, (item_id,))
            
            current_stock_result = cursor.fetchone()
            if not current_stock_result:
                print(f"错误：物品 ID {item_id} 不存在")
                return False
                
            current_stock = current_stock_result[0]
            
            # 检查修改后库存是否足够
            if current_stock + total_stock_change < 0:
                print(f"错误：修改此交易会导致库存不足 (当前: {current_stock}, 需要变化: {total_stock_change})")
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
        
        print(f"成功更新交易记录 ID {tx_id}，库存变化: {total_stock_change}")
        return True
        
    except sqlite3.Error as e:
        print(f"数据库错误：更新交易失败：{e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"未知错误：更新交易失败：{e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()