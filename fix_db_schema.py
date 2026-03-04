import sqlite3
import os

# 必须与您的主程序使用的文件名完全一致
DB_FILE = 'db/honsen_storage.db'

def force_fix():
    if not os.path.exists(DB_FILE):
        print(f"❌ 错误：找不到数据库文件 '{DB_FILE}'")
        print(f"   当前路径：{os.getcwd()}")
        return

    print(f"🔧 正在强制修复数据库：{os.path.abspath(DB_FILE)}")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. 检查表结构
        cursor.execute("PRAGMA table_info(Inventory);") # 尝试大写
        cols = [col[1] for col in cursor.fetchall()]
        
        # 如果大写表不存在，尝试小写 (兼容不同系统)
        if not cols:
            cursor.execute("PRAGMA table_info(inventory);")
            cols = [col[1] for col in cursor.fetchall()]
            target_table = "inventory"
        else:
            target_table = "Inventory"
            
        print(f"📋 检测到表名：{target_table}")
        print(f"📋 当前列：{cols}")
        
        fixes = []
        
        # 2. 强制添加 cabinet
        if 'cabinet' not in cols:
            sql = f"ALTER TABLE {target_table} ADD COLUMN cabinet TEXT DEFAULT ''"
            cursor.execute(sql)
            fixes.append('cabinet')
            print(f"✅ 已添加列：cabinet")
        else:
            print("ℹ️  列 'cabinet' 已存在")
            
        # 3. 强制添加 initial_cabinet
        if 'initial_cabinet' not in cols:
            sql = f"ALTER TABLE {target_table} ADD COLUMN initial_cabinet TEXT DEFAULT ''"
            cursor.execute(sql)
            fixes.append('initial_cabinet')
            print(f"✅ 已添加列：initial_cabinet")
        else:
            print("ℹ️  列 'initial_cabinet' 已存在")
            
        conn.commit()
        
        if fixes:
            print(f"\n🎉 修复成功！已添加列：{', '.join(fixes)}")
            print("👉 现在请重新启动您的主程序 (main.py)，问题应该解决了。")
        else:
            print("\n✨ 数据库结构看起来是完整的。如果还报错，请检查是否连接了错误的数据库文件。")
            
        # 最终验证
        cursor.execute(f"PRAGMA table_info({target_table});")
        final_cols = [col[1] for col in cursor.fetchall()]
        print(f"🔍 最终验证列列表：{final_cols}")
        
    except Exception as e:
        print(f"❌ 发生严重错误：{e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    force_fix()