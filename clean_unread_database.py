import sqlite3

db_path = 'db/honsen_storage.db' # 确认你的数据库路径
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. 查看有多少乱码数据
cursor.execute("SELECT id, name, reference FROM Inventory WHERE name LIKE '%?%' OR name LIKE '%%' OR name LIKE '%Ã%'")
bad_data = cursor.fetchall()
print(f"发现 {len(bad_data)} 条疑似乱码数据:")
for row in bad_data:
    print(row)

# 2. 如果确认是乱码，取消下面注释进行删除
# ⚠️ 警告：这会永久删除这些数据！
if len(bad_data) > 0:
    confirm = input("\n是否删除这些乱码数据？(输入 yes 确认): ")
    if confirm == 'yes':
        cursor.execute("DELETE FROM Inventory WHERE name LIKE '%?%' OR name LIKE '%%' OR name LIKE '%Ã%'")
        conn.commit()
        print("✅ 乱码数据已删除。请重新导入正确的 CSV 文件。")
    else:
        print("❌ 操作取消。")

conn.close()