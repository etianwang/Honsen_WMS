import sqlite3
import os

DB_PATH = r'E:\Project\Py\wms\Honsen_WMS\db\honsen_storage.db'

def clean_schema():
    if not os.path.exists(DB_PATH):
        print("数据库不存在")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 先合并数据
        print("正在合并数据...")
        cursor.execute("""
            UPDATE Inventory 
            SET cabinet = initial_cabinet 
            WHERE (cabinet = '' OR cabinet IS NULL) 
              AND (initial_cabinet != '' AND initial_cabinet IS NOT NULL)
        """)
        print(f"更新了 {cursor.rowcount} 条记录。")
        
        # 2. SQLite 删除列的标准做法：重建表
        # 获取所有列名
        cursor.execute("PRAGMA table_info(Inventory)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'initial_cabinet' not in columns:
            print("initial_cabinet 列已不存在，无需清理。")
            conn.close()
            return

        # 构建新表的列列表 (排除 initial_cabinet)
        new_columns = [col for col in columns if col != 'initial_cabinet']
        cols_str = ', '.join(f'"{c}"' for c in new_columns)
        
        # 创建临时表
        print("正在重建表结构...")
        cursor.execute(f"CREATE TABLE Inventory_new AS SELECT {cols_str} FROM Inventory")
        
        # 删除旧表
        cursor.execute("DROP TABLE Inventory")
        
        # 重命名新表
        cursor.execute("ALTER TABLE Inventory_new RENAME TO Inventory")
        
        conn.commit()
        print("✅ 数据库清理完成！initial_cabinet 列已移除，数据已合并。")
        
    except Exception as e:
        print(f"❌ 错误：{e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    clean_schema()