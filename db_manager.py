# db_manager.py
# 数据库管理模块，包含所有与 SQLite 数据库交互的函数。
# 负责初始化数据库、CRUD 操作、交易记录等功能。
import sqlite3
import hashlib
from typing import List, Dict, Union, Optional
from datetime import datetime
import os
import time

# 假设项目中存在 data_utility.py 用于处理文件IO (用于导入导出功能)
try:
    import data_utility 
except ImportError:
    pass # 仅在 db_manager 中忽略导入错误，因为它的核心是数据库操作

# 默认数据库文件名
DB_NAME = 'db/honsen_storage.db' # 建议更改为您实际使用的文件名

# --- 辅助函数 ---

def hash_password(password: str) -> str:
    """对密码进行 SHA256 哈希处理"""
    # 注意：此方法用于 settings_page.py 的密码存储（SHA256）
    return hashlib.sha256(password.encode()).hexdigest()

def _connect_db(db_path: str = DB_NAME) -> sqlite3.Connection:
    """内部函数：连接到 SQLite 数据库并设置行工厂。"""
    conn = sqlite3.connect(db_path)
    conn = sqlite3.connect(db_path, timeout=5000)
    conn.row_factory = sqlite3.Row # 使查询结果以字典形式返回
    return conn

# --- 数据库初始化和用户管理 ---

def initialize_database(db_path: str):
    """
    创建数据库文件，初始化 Inventory, Transactions, admin_user 和 config 表。
    【已修复】Inventory 表直接包含 cabinet 和 initial_cabinet 字段。
    【已修复】修复了 admin_user 表中 'PRIMARY PRIMARY KEY' 的拼写错误。
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 管理员用户表
        # 【修复】移除了重复的 PRIMARY
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        """)
        
        # 2. Inventory 表 (物品库存)
        # 【核心修改】直接在 CREATE TABLE 中定义 cabinet 和 initial_cabinet
        # 这样新创建的数据库天生就拥有完整结构，无需依赖后续的 ALTER TABLE 迁移
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL ,
                reference TEXT NOT NULL,
                category TEXT,
                domain TEXT,
                unit TEXT,
                current_stock INTEGER NOT NULL DEFAULT 0,
                min_stock INTEGER NOT NULL DEFAULT 0,
                location TEXT,
                cabinet TEXT DEFAULT ''          -- 【新增】当前柜号
            )
        """)

    # --- [迁移逻辑调整] ---
    # 如果旧库有 initial_cabinet，我们可以选择忽略它，或者把它的值合并到 cabinet
    # 这里我们只确保 cabinet 存在。如果用户想保留 initial_cabinet 的数据，需手动运行一次合并 SQL
    
        try:
            cursor.execute("SELECT cabinet FROM Inventory LIMIT 1")
        except sqlite3.OperationalError:
            try:
                cursor.execute("ALTER TABLE Inventory ADD COLUMN cabinet TEXT DEFAULT ''")
                print("[DB Migration] 成功添加列: cabinet")
                
                # 【可选】如果想把 old initial_cabinet 的数据合并过来，取消下面注释
                # cursor.execute("UPDATE Inventory SET cabinet = initial_cabinet WHERE cabinet = '' AND initial_cabinet != ''")
                
            except sqlite3.OperationalError as e:
                print(f"[DB Migration Error] 添加 cabinet 失败：{e}")
    
    # initial_cabinet 的迁移检查已移除，因为不再需要该列
        # ---------------------------------------
        
        # 2.1. 检查并添加 'category' 字段 (用于迁移更旧的数据库)
        try:
            cursor.execute("SELECT category FROM Inventory LIMIT 1")
        except sqlite3.OperationalError:
            try:
                cursor.execute("ALTER TABLE Inventory ADD COLUMN category TEXT DEFAULT '其他'")
            except sqlite3.OperationalError:
                pass 
        
        # 2.2. 检查并添加 'domain' 字段
        try:
            cursor.execute("SELECT domain FROM Inventory LIMIT 1")
        except sqlite3.OperationalError:
            try:
                cursor.execute("ALTER TABLE Inventory ADD COLUMN domain TEXT DEFAULT '其他'")
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
                FOREIGN KEY (item_id) REFERENCES Inventory(id)
            )
        """)

        # 4. Config 表
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
        # 注意：这里默认用户名是 'admin'，密码是 '123456'
        # 如果您的 login.py 使用的是 'Honsen_Admin' / '66778899HONSEN'，请确保只在一个地方初始化用户
        # 通常建议以 login.py 的初始化为准，或者在这里检查用户名是否存在再插入
        cursor.execute("SELECT id FROM admin_user WHERE username = 'admin'")
        if cursor.fetchone() is None:
            # 只有当 'admin' 用户不存在时才创建默认用户
            # 如果您的系统主要使用 Honsen_Admin，这段代码可能不会触发，或者会创建一个备用账号
            initial_password_hash = hash_password('123456') 
            try:
                cursor.execute("INSERT INTO admin_user (username, password) VALUES (?, ?)", 
                                 ('admin', initial_password_hash))
                print("[DB Init] 创建了默认 admin 用户 (密码: 123456)")
            except sqlite3.IntegrityError:
                pass # 用户已存在
            
        # 检查并插入默认配置选项
        default_configs = {
            'LOCATION': ["基地仓库", "大仓库", "别墅", "办公楼", "公寓", "其他"],
            'CATEGORY': ["电子元件", "机械零件", "工具", "耗材", "其他"],
            'DOMAIN': ["强电", "弱电", "给排水", "暖通", "土建", "精装", "其他"],
            'PROJECT': ["项目A", "项目B", "维护保养", "行政采购"]
        }
        for cat, values in default_configs.items():
            for val in values:
                 try:
                    cursor.execute("INSERT INTO config (category, value) VALUES (?, ?)", (cat, val,))
                 except sqlite3.IntegrityError:
                     pass # 已存在
                     
        conn.commit()
        print(f"✅ 数据库初始化完成：{db_path}")
        
    except sqlite3.Error as e:
        print(f"❌ 数据库初始化错误：{e}")
        if conn:
            conn.rollback()
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
def insert_Inventory_item(db_path: str, name: str, reference: str, category: str, 
                          domain: str, unit: str, current_stock: int, min_stock: int, 
                          location: str, cabinet: str) -> Optional[int]:
    """
    【更新版】插入新的库存物品。
    
    唯一性约束变更：
    不再强制 'reference' 全局唯一。
    现在的唯一性约束为组合键：(name, reference, location, cabinet)。
    即：同一型号可以在不同地点或不同柜子存在，但不能在同一地点的同一柜子下重复添加同名同型号物品。
    
    :return: 成功返回新行的 rowid，如果违反唯一性约束返回 None。
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 检查组合唯一性 (Name + Ref + Location + Cabinet)
        check_sql = """
            SELECT id FROM Inventory 
            WHERE name=? AND reference=? AND location=? AND cabinet=?
        """
        # 注意：这里假设输入的空字符串 "" 和数据库中的 "" 匹配。
        # 如果业务逻辑中 "空柜子" 和 "未填写柜子" 需要特殊处理，需在此处标准化数据。
        
        cursor.execute(check_sql, (name.strip(), reference.strip(), location.strip(), cabinet.strip()))
        if cursor.fetchone():
            # 发现重复
            print(f"⚠️ 插入失败：检测到重复记录 -> 名称:{name}, 型号:{reference}, 地点:{location}, 柜号:{cabinet}")
            return None
        
        # 2. 执行插入
        insert_sql = """
            INSERT INTO Inventory (name, reference, category, domain, unit, current_stock, min_stock, location, cabinet)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(insert_sql, (
            name.strip(), 
            reference.strip(), 
            category.strip(), 
            domain.strip(), 
            unit.strip(), 
            current_stock, 
            min_stock, 
            location.strip(), 
            cabinet.strip()
        ))
        
        conn.commit()
        new_id = cursor.lastrowid
        print(f"✅ 成功插入新物品 (ID: {new_id}): {name} @ {location}-{cabinet}")
        return new_id
        
    except sqlite3.Error as e:
        print(f"💥 数据库插入错误: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()
# def insert_Inventory_item(
#     db_path: str, 
#     name: str, 
#     reference: str, 
#     category: str,
#     domain: str,
#     unit: str, 
#     current_stock: int, 
#     min_stock: int, 
#     location: str,
#     cabinet: str = ""  # 【新增】添加 cabinet 参数
# ) -> Optional[int]:
#     """插入新的库存物品。"""
#     conn = None
#     try:
#         conn = sqlite3.connect(db_path)
#         cursor = conn.cursor()
#         cursor.execute("""
#             INSERT INTO Inventory (name, reference, category, domain, unit, current_stock, min_stock, location, cabinet) 
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """, (name, reference, category, domain, unit, current_stock, min_stock, location, cabinet))
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.IntegrityError:
#         # print("错误：名称或参考编号已存在。")
#         return None 
#     except sqlite3.Error as e:
#         print(f"数据库错误：插入物品失败：{e}")
#         return None
#     finally:
#         if conn:
#             conn.close()
#             time.sleep(0.4)

def update_Inventory_item(
    db_path: str, 
    item_id: int, 
    name: str, 
    reference: str, 
    category: str,
    domain: str,
    unit: str, 
    min_stock: int, 
    location: str,
    cabinet: str = ""  # 【新增】添加 cabinet 参数
) -> bool:
    """更新库存物品的非库存字段。"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Inventory SET name=?, reference=?, category=?, domain=?, unit=?, min_stock=?, location=?, cabinet = ?
            WHERE id=?
        """, (name, reference, category, domain, unit, min_stock, location, cabinet, item_id))
        conn.commit()
        
        # 如果没有行被更新，可能是因为 ID 不存在或数据未变化
        return cursor.rowcount > 0
    
    except sqlite3.Error as e:
        print(f"数据库错误：更新物品失败：{e}")
        return False
    finally:
        if conn:
            conn.close()
            time.sleep(0.4) 

def delete_Inventory_item(db_path: str, item_id: int) -> bool:
    """删除库存物品及所有相关交易记录。"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 删除关联的交易记录
        cursor.execute("DELETE FROM transactions WHERE item_id=?", (item_id,))
        # 2. 删除库存项
        cursor.execute("DELETE FROM Inventory WHERE id=?", (item_id,))
        
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"数据库错误：删除物品失败：{e}")
        return False
    finally:
        if conn:
            conn.close()
            time.sleep(0.4)
def get_all_Inventory(db_path: str) -> List[Dict[str, Union[int, str]]]:
    """获取所有库存物品数据"""
    conn = None
    try:
        conn = _connect_db(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Inventory ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"数据库错误：获取库存失败：{e}")
        return []
    finally:
        if conn:
            conn.close()
            
def get_Inventory_item_by_id(db_path: str, item_id: int) -> Optional[Dict]:
    """根据 ID 获取单个库存物品详情"""
    conn = None
    try:
        conn = _connect_db(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Inventory WHERE id=?", (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"数据库错误：获取单个库存项失败：{e}")
        return None
    finally:
        if conn:
            conn.close()

def get_Inventory_names(db_path: str) -> List[Dict[str, Union[int, str]]]:
    """获取所有物品的 ID, Name, Reference, Unit, Current_Stock，用于对话框下拉列表"""
    conn = None
    try:
        conn = _connect_db(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, reference, unit, current_stock FROM Inventory ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"数据库错误：获取物品名称失败：{e}")
        return []
    finally:
        if conn:
            conn.close()

def get_Inventory_for_export(db_path: str) -> List[Dict[str, Union[int, str]]]:
    """获取所有库存物品数据，用于导出 CSV。"""
    conn = None
    try:
        conn = _connect_db(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, reference, category, domain, unit, current_stock, min_stock, location, cabinet
            FROM Inventory 
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
                i.name AS item_name, i.reference AS item_reference, i.domain AS item_domain, i.cabinet AS cabinet
            FROM transactions t
            JOIN Inventory i ON t.item_id = i.id
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
def batch_import_Inventory(db_path: str, items: List[Dict]) -> Dict[str, int]:
    """
    【修复版】批量导入或更新库存物品。
    
    核心逻辑修复：
    1. 判重键变更：从 (ref, loc, cab) 改为 (name, ref, loc, cab)。
       - 确保“同名同型号同位置同柜号”才会触发更新。
       - “同型号但不同名”会被视为新物品进行插入。
    2. 预处理：自动合并 CSV 中完全重复的行。
    
    :return: 包含操作统计的字典 {'inserted': int, 'updated': int, 'failed': int, 'merged_rows': int}
    """
    if not items:
        return {'inserted': 0, 'updated': 0, 'failed': 0, 'merged_rows': 0}

    conn = None
    stats = {'inserted': 0, 'updated': 0, 'failed': 0, 'merged_rows': 0}
    
    try:
        # --- 第一步：数据预处理 (合并重复项) ---
        # 【修复】Key 必须包含 name
        merged_data = {}
        
        for item in items:
            try:
                name = str(item.get('name', '')).strip()
                ref = str(item.get('reference', '')).strip()
                loc = str(item.get('location', '其他')).strip()
                cab = str(item.get('cabinet', '')).strip()
                
                if not ref or not name:
                    stats['failed'] += 1
                    continue
                
                # 【关键修复】Key 包含 name
                key = (name, ref, loc, cab)
                
                try:
                    stock_val = int(item.get('current_stock', 0))
                except ValueError:
                    stock_val = 0
                
                min_stock_val = 0
                try:
                    min_stock_val = int(item.get('min_stock', 0))
                except ValueError:
                    pass

                current_row = {
                    'name': name,
                    'category': item.get('category', '其他'),
                    'domain': item.get('domain', '其他'),
                    'unit': item.get('unit', ''),
                    'min_stock': min_stock_val,
                    'stock': stock_val
                }

                if key in merged_data:
                    existing = merged_data[key]
                    existing['stock'] += stock_val
                    existing['category'] = current_row['category']
                    existing['domain'] = current_row['domain']
                    existing['unit'] = current_row['unit']
                    existing['min_stock'] = current_row['min_stock']
                    stats['merged_rows'] += 1
                else:
                    merged_data[key] = current_row
                    
            except Exception as e:
                print(f"⚠️ 预处理行失败：{e}")
                stats['failed'] += 1

        if not merged_data:
            return stats

        # --- 第二步：数据库操作 ---
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        insert_sql = """
            INSERT INTO Inventory (name, reference, category, domain, unit, current_stock, min_stock, location, cabinet)  
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # 【修复】UPDATE 的 WHERE 条件必须包含 name
        update_sql = """
            UPDATE Inventory 
            SET category=?, domain=?, unit=?, min_stock=?, current_stock=?
            WHERE name=? AND reference=? AND location=? AND cabinet=?
        """
        
        # 【修复】CHECK 的 WHERE 条件必须包含 name
        check_sql = """
            SELECT id, current_stock FROM Inventory 
            WHERE name=? AND reference=? AND location=? AND cabinet=?
        """

        for (name, ref, loc, cab), data in merged_data.items():
            try:
                # 检查数据库中是否存在完全匹配的记录 (Name + Ref + Loc + Cab)
                cursor.execute(check_sql, (name, ref, loc, cab))
                row = cursor.fetchone()

                if row:
                    # 【存在】-> 更新
                    final_stock = data['stock']
                    
                    cursor.execute(
                        update_sql, 
                        (data['category'], data['domain'], data['unit'], 
                         data['min_stock'], final_stock, 
                         name, ref, loc, cab) # 注意参数顺序对应 WHERE 子句
                    )
                    stats['updated'] += 1
                else:
                    # 【不存在】-> 插入 (即使 Ref/Loc/Cab 相同，只要 Name 不同，就是新记录)
                    cursor.execute(
                        insert_sql, 
                        (name, ref, data['category'], data['domain'], data['unit'], 
                         data['stock'], data['min_stock'], loc, cab)
                    )
                    stats['inserted'] += 1

            except Exception as e:
                print(f"❌ 数据库操作失败 (Name: {name}, Ref: {ref}): {e}")
                stats['failed'] += 1
        
        conn.commit()
        
        msg = f"📊 导入完成 | 新增: {stats['inserted']}, 更新: {stats['updated']}"
        if stats['merged_rows'] > 0:
            msg += f", CSV中自动合并重复行: {stats['merged_rows']} 条"
        if stats['failed'] > 0:
            msg += f", 失败: {stats['failed']} 条"
        print(msg)
        
    except sqlite3.Error as e:
        if conn: conn.rollback()
        print(f"💥 批量导入致命错误：{e}")
        stats['failed'] += len(items)
    finally:
        if conn: conn.close()
            
    return stats

# def batch_import_Inventory(db_path: str, items: List[Dict]) -> Dict[str, int]:
#     """
#     【方案一优化版】批量导入或更新库存物品。
    
#     判重逻辑变更：
#     - 旧逻辑：仅根据 'reference' 判重。
#     - 新逻辑：根据 'reference' + 'location' + 'cabinet' 组合判重。
#       即：同型号在不同地点/柜子，会创建为新行，而不是覆盖旧行。
    
#     :return: 包含操作统计的字典 {'inserted': int, 'updated': int, 'failed': int}
#     """
#     conn = None
#     stats = {'inserted': 0, 'updated': 0, 'failed': 0}
    
#     try:
#         conn = sqlite3.connect(db_path)
#         cursor = conn.cursor()

#         # SQL for INSERT (保持不变)
#         insert_sql = """
#             INSERT INTO Inventory (name, reference, category, domain, unit, current_stock, min_stock, location, cabinet)  
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
        
#         # SQL for UPDATE (逻辑核心变化)
#         # 只有当 reference, location, cabinet 三者都匹配时，才执行更新
#         update_sql = """
#             UPDATE Inventory 
#             SET name=?, category=?, domain=?, unit=?, min_stock=?, current_stock=?
#             WHERE reference=? AND location=? AND cabinet=?
#         """
        
#         # 预编译查询，用于快速检查是否存在
#         check_sql = """
#             SELECT id FROM Inventory 
#             WHERE reference=? AND location=? AND cabinet=?
#         """

#         for item in items:
#             try:
#                 # 提取并清洗数据
#                 item_ref = str(item.get('reference', '')).strip()
#                 item_loc = str(item.get('location', '其他')).strip()
#                 item_cab = str(item.get('cabinet', '')).strip()
                
#                 # 必需字段检查
#                 if not item_ref or not item.get('name'):
#                     stats['failed'] += 1
#                     continue

#                 item_name = item['name']
#                 item_cat = str(item.get('category', '其他')).strip() or '其他'
#                 item_dom = str(item.get('domain', '其他')).strip() or '其他'
#                 item_unit = str(item.get('unit', '')).strip()
#                 item_min = int(item.get('min_stock', 0))
#                 item_stock = int(item.get('current_stock', 0))

#                 # 1. 检查是否存在完全匹配的记录 (Reference + Location + Cabinet)
#                 cursor.execute(check_sql, (item_ref, item_loc, item_cab))
#                 exists = cursor.fetchone()

#                 if exists:
#                     # 2. 如果存在 -> 更新 (覆盖该地点该柜子的数量和属性)
#                     cursor.execute(
#                         update_sql, 
#                         (item_name, item_cat, item_dom, item_unit, item_min, item_stock, 
#                          item_ref, item_loc, item_cab)
#                     )
#                     stats['updated'] += 1
#                 else:
#                     # 3. 如果不存在 -> 插入 (即使 Reference 相同，只要地点/柜子不同，就是新记录)
#                     cursor.execute(
#                         insert_sql, 
#                         (item_name, item_ref, item_cat, item_dom, item_unit, item_stock, item_min, item_loc, item_cab)
#                     )
#                     stats['inserted'] += 1

#             except Exception as e:
#                 print(f"❌ 导入失败 (参考号: {item.get('reference')}): {e}")
#                 stats['failed'] += 1
        
#         conn.commit()
#         print(f"📊 导入统计 -> 新增: {stats['inserted']}, 更新: {stats['updated']}, 失败: {stats['failed']}")
        
#     except sqlite3.Error as e:
#         if conn: conn.rollback()
#         print(f"💥 批量导入致命错误: {e}")
#         stats['failed'] += len(items)
#     finally:
#         if conn: conn.close()
            
#     return stats

# def batch_import_Inventory(db_path: str, items: List[Dict]) -> Dict[str, int]:
#     """
#     批量导入或更新库存物品。使用 'reference' 作为唯一键。
#     如果 'reference' 存在，则更新名称、类别、专业、单位、最小库存、位置。
#     如果 'reference' 不存在，则插入新记录 (current_stock 设为 0)。
#     返回包含操作统计的字典。
#     """
#     conn = None
#     stats = {'inserted': 0, 'updated': 0, 'failed': 0}
    
#     try:
#         conn = sqlite3.connect(db_path)
#         cursor = conn.cursor()

#         # SQL for UPDATE
#         update_sql = """
#             UPDATE Inventory 
#             SET name=?, category=?, domain=?, unit=?, min_stock=?, location=?, cabinet=?
#             WHERE reference=?
#         """
#         # SQL for INSERT
#         insert_sql = """
#             INSERT INTO Inventory (name, reference, category, domain, unit, current_stock, min_stock, location, cabinet)  
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
        
#         for item in items:
#             try:
#                 item_category = item.get('category', '其他')
#                 item_domain = item.get('domain', '其他')
                
#                 # 1. 尝试更新
#                 cursor.execute(
#                     update_sql, 
#                     (item['name'], item_category, item_domain, item['unit'], item['min_stock'], item['location'], item.get('cabinet', ''),item['reference'])
#                 )
                
#                 if cursor.rowcount > 0:
#                     stats['updated'] += 1
#                 else:
#                     # 2. 如果没有更新任何行，则插入新行 
#                     initial_stock = item.get('current_stock', 0) 
                    
#                     cursor.execute(
#                         insert_sql, 
#                         (item['name'], item['reference'], item_category, item_domain, item['unit'], initial_stock, item['min_stock'], item['location'],
#                             item.get('cabinet', ''))
#                     )
#                     stats['inserted'] += 1

#             except sqlite3.IntegrityError as e:
#                 print(f"完整性错误 (跳过): {item.get('reference')} - {e}")
#                 stats['failed'] += 1
#             except Exception as e:
#                 print(f"未知错误 (跳过): {item.get('reference')} - {e}") # 🔴 打印具体错误方便调试
#                 stats['failed'] += 1
        
#         conn.commit()
#     except sqlite3.Error as e:
#         if conn: conn.rollback()
#         stats['failed'] = len(items) - stats['inserted'] - stats['updated']
#         print(f"数据库批量导入致命错误: {e}")
#     finally:
#         if conn: conn.close()
            
#     return stats


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
            cursor.execute("SELECT current_stock FROM Inventory WHERE id = ?", (item_id,))
            current_stock = cursor.fetchone()
            if current_stock is None or current_stock[0] < quantity:
                return False # 库存不足
        
        # 2. 更新库存
        stock_change = quantity if type == 'IN' else -quantity
        cursor.execute("""
            UPDATE Inventory SET current_stock = current_stock + ? WHERE id = ?
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
        cursor.execute("SELECT id, current_stock FROM Inventory")
        Inventory_stocks = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 检查是否可以执行所有交易
        for tx in transactions:
            item_id = tx['item_id']
            quantity = tx['quantity']
            
            if item_id not in Inventory_stocks:
                # 物品不存在，标记失败
                results['failed_transactions'].append(tx)
                continue
                
            if type_upper == 'OUT':
                current_stock = Inventory_stocks[item_id]
                if current_stock < quantity:
                    # 库存不足，标记失败，并中断整个批次提交
                    tx['error'] = '库存不足'
                    results['failed_transactions'].append(tx)
                    raise ValueError("库存不足，批量交易中断") 
                
                # 预先扣除库存（内存中）
                Inventory_stocks[item_id] -= quantity
            elif type_upper == 'IN':
                 # 预先增加库存（内存中）
                 Inventory_stocks[item_id] += quantity


        # 1. 批量更新 Inventory 表
        update_Inventory_batch = []
        for item_id, new_stock in Inventory_stocks.items():
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
                UPDATE Inventory SET current_stock = current_stock + ? WHERE id = ?
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
                i.domain AS domain,
                i.cabinet AS cabinet
            FROM transactions t
            JOIN Inventory i ON t.item_id = i.id
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
            # query += " AND (UPPER(i.name) LIKE UPPER(?) OR UPPER(i.reference) LIKE UPPER(?))"
            # params.extend([search_pattern, search_pattern])
            # 扩展搜索范围：增加 i.cabinet (柜号) 和 t.recipient_source (接收人/来源)
            query += """
                AND (
                    UPPER(i.name) LIKE UPPER(?) 
                    OR UPPER(i.reference) LIKE UPPER(?) 
                    OR UPPER(i.cabinet) LIKE UPPER(?) 
                    OR UPPER(t.recipient_source) LIKE UPPER(?)
                )
            """
            # 需要传入 4 次相同的搜索参数
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern])



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


def get_item_cabinet_map(db_path: str) -> Dict[str, List[str]]:
    """
    【新增功能】扫描 transactions 表，建立 { reference: [cabinet_list] } 的映射。
    用于在批量操作对话框中通过柜号 (recipient_source) 反查物品。
    
    返回格式: { "REF-001": ["Cabinet-A", "Box-B"], "REF-002": ["Cabinet-C"], ... }
    """
    conn = None
    cabinet_map = {}
    try:
        conn = _connect_db(db_path)
        cursor = conn.cursor()
        
        # SQL: 连接 Inventory 和 transactions，提取 reference 和 recipient_source
        # 过滤掉空的 recipient_source
        query = """
            SELECT i.reference, t.recipient_source
            FROM transactions t
            JOIN Inventory i ON t.item_id = i.id
            WHERE t.recipient_source IS NOT NULL 
              AND t.recipient_source != ''
              AND i.reference IS NOT NULL
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        for ref, source in rows:
            source = source.strip()
            if not source:
                continue
                
            if ref not in cabinet_map:
                cabinet_map[ref] = set() # 使用 set 自动去重
            cabinet_map[ref].add(source)
            
        # 将 set 转换为 list 以便后续处理
        return {k: list(v) for k, v in cabinet_map.items()}
        
    except sqlite3.Error as e:
        print(f"数据库错误：构建柜号映射失败：{e}")
        return {}
    finally:
        if conn:
            conn.close()      

def update_item_cabinet(db_path: str, item_id: int, cabinet: str) -> bool:
    """更新物品的当前柜号"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE Inventory SET cabinet = ? WHERE id = ?", (cabinet.strip(), item_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"数据库错误：更新柜号失败：{e}")
        return False
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
            cursor.execute("SELECT current_stock FROM Inventory WHERE id = ?", (item_id,))
            current_stock = cursor.fetchone()
            if current_stock is None or current_stock[0] < original_qty:
                return False # 库存不足以冲销
                
        # 4. 更新库存
        cursor.execute("""
            UPDATE Inventory SET current_stock = current_stock + ? WHERE id = ?
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
            cursor.execute("SELECT current_stock FROM Inventory WHERE id = ?", (item_id,))
            current_stock_result = cursor.fetchone()
            if not current_stock_result or current_stock_result[0] + stock_change < 0:
                # print(f"错误：删除此交易会导致库存为负")
                return False
        
        # 4. 更新库存
        cursor.execute("""
            UPDATE Inventory 
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
                i.domain AS domain,
                i.cabinet AS cabinet
            FROM transactions t
            JOIN Inventory i ON t.item_id = i.id
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

def enable_wal_mode(db_path: str):
    """
    开启 SQLite 的 WAL (Write-Ahead Logging) 模式。
    这允许读写并发，解决界面卡顿问题。
    只需在程序生命周期内执行一次即可。
    """
    if not os.path.exists(db_path):
        print(f"⚠️ 数据库文件不存在，无法开启 WAL: {db_path}")
        return

    conn = None
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 开启 WAL 模式
        cursor.execute("PRAGMA journal_mode=WAL;")
        result = cursor.fetchone()
        print(f"✅ 数据库日志模式已设置为: {result[0]}")
        
        # 2. 设置繁忙超时为 5 秒 (防止锁竞争时无限等待)
        cursor.execute("PRAGMA busy_timeout=5000;")
        print("✅ 数据库繁忙超时已设置为 5000ms")
        
        conn.commit()
        
    except Exception as e:
        print(f"❌ 开启 WAL 模式失败: {e}")
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
            cursor.execute("SELECT current_stock FROM Inventory WHERE id = ?", (item_id,))
            current_stock_result = cursor.fetchone()
            if not current_stock_result or current_stock_result[0] + total_stock_change < 0:
                # print(f"错误：修改此交易会导致库存不足")
                return False
        
        # 4. 更新库存
        cursor.execute("""
            UPDATE Inventory 
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
get_all_inventory = get_all_Inventory
update_inventory_item = update_Inventory_item # 确保其他调用也安全
get_inventory_for_export = get_Inventory_for_export
update_inventory_item = update_Inventory_item
batch_import_inventory = batch_import_Inventory
get_inventory_item_by_id = get_Inventory_item_by_id
get_inventory_names = get_Inventory_names
delete_inventory_item  = delete_Inventory_item
insert_inventory_item = insert_Inventory_item

