import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QMessageBox, QApplication, QLabel, QDialog, QFileDialog 
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor # 确保导入 QColor
import os
# 导入数据库管理器
import db_manager 
from add_item_dialog import AddItemDialog 
from edit_item_dialog import EditItemDialog 

# 注意：为了让代码能独立运行，请确保 db_manager.py, add_item_dialog.py, edit_item_dialog.py 都在同一目录下。

class InventoryPage(QWidget):
    """
    库存管理界面：展示和操作 Inventory 表数据。
    实现：根据库存状态（缺货/预警）设置行背景色。
    """
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.init_ui()
        # 首次加载时填充数据
        self.load_inventory_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- 1. 顶部操作栏 (工具栏) ---
        toolbar_layout = QHBoxLayout()
        
        # 搜索框 (已连接筛选功能)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入物品名称或型号进行搜索...")
        self.search_input.textChanged.connect(self.filter_data) # 关键：连接到 filter_data 方法
        toolbar_layout.addWidget(self.search_input)
        
        toolbar_layout.addStretch(1) # 填充空间
        
        # 按钮
        self.add_btn = QPushButton("新增物品")
        self.edit_btn = QPushButton("编辑物品")
        self.del_btn = QPushButton("删除物品")
        
        # 连接按钮到相应的槽函数
        self.add_btn.clicked.connect(self.add_item_dialog)
        self.edit_btn.clicked.connect(self.edit_item_dialog) 
        self.del_btn.clicked.connect(self.delete_item_action) 

        toolbar_layout.addWidget(self.add_btn)
        toolbar_layout.addWidget(self.edit_btn)
        toolbar_layout.addWidget(self.del_btn)
        
        main_layout.addLayout(toolbar_layout)

        # --- 2. 主数据表格 ---
        self.inventory_table = QTableWidget()
        self.inventory_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # 禁止直接编辑
        self.inventory_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows) # 整行选中
        self.inventory_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection) 

        # 定义表头 (注意：ID列是隐藏的)
        self.headers = [
            "ID", "名称 (Name)", "物品型号 (Ref)", "材料类别","单位 (Unit)", 
            "当前库存", "最小库存", "储存位置", "库存状态"
        ]
        self.inventory_table.setColumnCount(len(self.headers))
        self.inventory_table.setHorizontalHeaderLabels(self.headers)
        
        # 调整列宽以适应内容
        self.inventory_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.inventory_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # '名称'列自动拉伸
        
        main_layout.addWidget(self.inventory_table)
        
        # 底部状态栏
        self.status_label = QLabel("总计 0 条记录。")
        main_layout.addWidget(self.status_label)


    def load_inventory_data(self):
        """从数据库加载数据并填充表格"""
        data = db_manager.get_all_inventory(self.db_path)
        
        self.inventory_table.setRowCount(len(data))
        
        # 定义颜色常量
        critical_color = QColor(255, 179, 179) # 缺货：浅红色
        warning_color = QColor(255, 240, 192)  # 预警：浅黄色/橙色
        default_color = QColor(255, 255, 255)  # 正常：白色
        
        for row_index, item in enumerate(data):
            
            # 检查库存预警状态
            current = item['current_stock']
            minimum = item['min_stock']
            status_text = "正常"
            
            # --- 颜色选择逻辑 ---
            color = default_color
            if current <= 0:
                status_text = "缺货"
                color = critical_color
            elif current <= minimum:
                status_text = "预警"
                color = warning_color
            # ---------------------
            
            # 填充表格行 (顺序与 self.headers 对应)
            self.inventory_table.setItem(row_index, 0, QTableWidgetItem(str(item['id'])))
            self.inventory_table.setItem(row_index, 1, QTableWidgetItem(item['name']))
            self.inventory_table.setItem(row_index, 2, QTableWidgetItem(item['reference']))
            self.inventory_table.setItem(row_index, 3, QTableWidgetItem(item['category']))
            self.inventory_table.setItem(row_index, 4, QTableWidgetItem(item['unit']))
            self.inventory_table.setItem(row_index, 5, QTableWidgetItem(str(current)))
            self.inventory_table.setItem(row_index, 6, QTableWidgetItem(str(minimum)))
            self.inventory_table.setItem(row_index, 7, QTableWidgetItem(item['location']))
            self.inventory_table.setItem(row_index, 8, QTableWidgetItem(status_text))
            
            # 应用行颜色：遍历当前行的所有单元格并设置背景色
            for col in range(self.inventory_table.columnCount()):
                # 确保在设置背景色之前，QTableWidgetItem 已经被创建 (上面已经完成)
                self.inventory_table.item(row_index, col).setBackground(color)
            
            # 隐藏 ID 列
            self.inventory_table.setColumnHidden(0, True)

        self.status_label.setText(f"总计 {len(data)} 条记录。")


    def filter_data(self):
        """根据搜索框内容过滤表格行"""
        search_text = self.search_input.text().lower().strip()
        
        for i in range(self.inventory_table.rowCount()):
            name_item = self.inventory_table.item(i, 1) # 名称
            ref_item = self.inventory_table.item(i, 2)  # 编号
            
            hide = True
            if not search_text:
                # 搜索框为空，显示所有行
                hide = False 
            elif name_item and search_text in name_item.text().lower():
                # 名称匹配
                hide = False
            elif ref_item and search_text in ref_item.text().lower():
                # 编号匹配
                hide = False

            self.inventory_table.setRowHidden(i, hide)
            
        
    def add_item_dialog(self):
        """显示新增物品对话框，并处理结果。"""
        dialog = AddItemDialog(self.db_path, self)
        
        # 修正：使用 QDialog.DialogCode.Accepted
        if dialog.exec() == QDialog.DialogCode.Accepted: 
            self.load_inventory_data() # 刷新表格数据
            
            
    def edit_item_dialog(self):
        """编辑选中物品的槽函数"""
        selected_rows = self.inventory_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要编辑的物品行。")
            return
            
        row_index = selected_rows[0].row()
        
        # 提取选中行的数据到字典中
        item_data = {
            'id': int(self.inventory_table.item(row_index, 0).text()),
            'name': self.inventory_table.item(row_index, 1).text(),
            'reference': self.inventory_table.item(row_index, 2).text(),
            'category': self.inventory_table.item(row_index, 3).text(),
            'unit': self.inventory_table.item(row_index, 4).text(),
            'current_stock': int(self.inventory_table.item(row_index, 5).text()),
            'min_stock': int(self.inventory_table.item(row_index, 6).text()),
            'location': self.inventory_table.item(row_index, 7).text()
        }
        
        # 弹出编辑对话框
        dialog = EditItemDialog(self.db_path, item_data, self)
        # 修正：使用 QDialog.DialogCode.Accepted
        if dialog.exec() == QDialog.DialogCode.Accepted: 
            self.load_inventory_data() # 刷新表格数据


    def delete_item_action(self):
        """删除选中物品的槽函数"""
        selected_rows = self.inventory_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的物品行。")
            return
            
        # 获取选中行 ID (第 0 列) 的值
        row_index = selected_rows[0].row()
        item_id_item = self.inventory_table.item(row_index, 0)
        item_id = int(item_id_item.text())
        item_name = self.inventory_table.item(row_index, 1).text()
        
        # 提示信息已更新，匹配 db_manager 中的级联删除行为
        reply = QMessageBox.question(self, 
            "确认删除", 
            f"您确定要删除物品 **{item_name}** (ID: {item_id}) 吗？\n\n注意：此操作将同时删除该物品及其所有相关的交易记录，数据不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if db_manager.delete_inventory_item(self.db_path, item_id):
                QMessageBox.information(self, "成功", "物品及关联交易记录已成功删除。")
                self.load_inventory_data() # 刷新数据
            else:
                # 失败通常是数据库连接问题或 ID 不存在。
                QMessageBox.critical(self, "删除失败", "删除失败！请检查数据库连接或确认该物品ID是否存在。")


# --- 暂时不需要运行，但用于测试 ---
if __name__ == '__main__':
    # 仅用于快速测试页面布局
    app = QApplication(sys.argv)
    TEST_DB_PATH = 'honsen_storage.db' 
    
    # 确保 db_manager.py 可用
    if not os.path.exists(TEST_DB_PATH):
        print("警告: 数据库文件不存在，请先通过 login.py 初始化。")
    # 为了运行，需要导入 Mock 或实际的 db_manager, AddItemDialog, EditItemDialog
    # window = InventoryPage(TEST_DB_PATH)
    # window.show()
    # sys.exit(app.exec())
