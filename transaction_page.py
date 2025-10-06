import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QMessageBox, QDialog, QApplication, QLabel,
    QDateEdit, QComboBox # 新增导入用于筛选
)
from PyQt6.QtCore import Qt, QDateTime, QDate # 新增导入 QDate
from PyQt6.QtGui import QColor
from typing import Optional # 新增导入 Optional

# 导入数据库管理器和交易对话框
import db_manager 
from transaction_dialog import TransactionDialog 
# 导入 InventoryPage 类型提示 (虽然不是必须，但有利于代码阅读)
from inventory_page import InventoryPage

class TransactionPage(QWidget):
    """
    交易记录界面：展示 Transactions 表数据，并提供筛选、入库/出库和冲销操作。
    """
    def __init__(self, db_path: str, inventory_page_ref: InventoryPage): 
        super().__init__()
        self.db_path = db_path
        self.inventory_page_ref = inventory_page_ref # 存储对库存页面的直接引用
        self.init_ui()
        self.load_transaction_data() # 初始加载数据

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- 1. 顶部操作栏 (入库/出库/冲销) ---
        toolbar_layout = QHBoxLayout()
        
        self.in_btn = QPushButton("入库 (IN)")
        self.out_btn = QPushButton("出库 (OUT)")
        self.reverse_btn = QPushButton("冲销交易")
        
        self.in_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.out_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        self.reverse_btn.setStyleSheet("background-color: #ff9800; color: white; padding: 8px;")
        
        self.in_btn.clicked.connect(lambda: self.open_transaction_dialog('IN'))
        self.out_btn.clicked.connect(lambda: self.open_transaction_dialog('OUT'))
        self.reverse_btn.clicked.connect(self.reverse_transaction_action)

        toolbar_layout.addWidget(self.in_btn)
        toolbar_layout.addWidget(self.out_btn)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.reverse_btn)
        
        main_layout.addLayout(toolbar_layout)
        
        # --- 2. 筛选区域 ---
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("从日期:"))
        self.start_date_edit = QDateEdit(calendarPopup=True)
        # 默认设置为一年前
        self.start_date_edit.setDate(QDate.currentDate().addYears(-1))
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.start_date_edit)
        
        filter_layout.addWidget(QLabel("到日期:"))
        self.end_date_edit = QDateEdit(calendarPopup=True)
        # 默认设置为今天
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.end_date_edit)
        
        filter_layout.addWidget(QLabel("类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["ALL", "IN", "OUT", "REVERSAL"])
        filter_layout.addWidget(self.type_combo)
        
        filter_layout.addWidget(QLabel("物品搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("物品名称或型号")
        filter_layout.addWidget(self.search_input)
        
        self.filter_btn = QPushButton("筛选/刷新")
        self.filter_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        # 将按钮连接到新的筛选方法
        self.filter_btn.clicked.connect(self.apply_filters)
        filter_layout.addWidget(self.filter_btn)

        main_layout.addLayout(filter_layout)

        # --- 3. 主数据表格 ---
        self.transaction_table = QTableWidget()
        self.transaction_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.transaction_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.transaction_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection) 

        # 定义表头
        self.headers = [
            "ID", "日期/时间", "物品名称", "物品型号", 
            "储存位置", "类型", "数量", "接收人/来源", "项目" # <-- 包含 '位置'
        ]
        self.transaction_table.setColumnCount(len(self.headers))
        self.transaction_table.setHorizontalHeaderLabels(self.headers)
        
        # 调整列宽
        self.transaction_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # 调整：将索引 1 的“日期/时间”设置为固定宽度 160px
        self.transaction_table.horizontalHeader().resizeSection(1, 160)
        
        # 调整：将索引 2 的“物品名称”设置为拉伸，以便适应窗口大小
        self.transaction_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        # 新增：将索引 4 的“位置”设置为固定宽度，例如 120px
        self.transaction_table.horizontalHeader().resizeSection(4, 120) 
        
        main_layout.addWidget(self.transaction_table)
        
        # 底部状态栏
        self.status_label = QLabel("总计 0 条交易记录。")
        main_layout.addWidget(self.status_label)

    def apply_filters(self):
        """读取筛选控件的值并加载数据"""
        # 1. 读取日期（格式化为 YYYY-MM-DD）
        start_date = self.start_date_edit.date().toString('yyyy-MM-dd')
        end_date = self.end_date_edit.date().toString('yyyy-MM-dd')
        
        # 2. 读取类型
        tx_type = self.type_combo.currentText()
        
        # 3. 读取搜索关键词
        item_search = self.search_input.text().strip()
        
        self._load_data_with_filters(
            start_date=start_date,
            end_date=end_date,
            tx_type=tx_type,
            item_search=item_search if item_search else None
        )
        
    def load_transaction_data(self):
        """初始加载数据 (无筛选，使用默认范围)"""
        # 默认使用 UI 中设置的初始日期范围进行加载
        self.apply_filters()


    def _load_data_with_filters(self, start_date: Optional[str] = None, end_date: Optional[str] = None, 
                                 tx_type: Optional[str] = None, item_search: Optional[str] = None):
        """
        根据筛选参数从数据库加载数据并填充表格
        
        注意：此处假设 db_manager.get_transactions_history 已通过 JOIN Inventory 表
        获取了 'location' 字段。
        """
        
        # 调用 db_manager 中支持筛选的新函数
        data = db_manager.get_transactions_history(
            self.db_path, 
            start_date=start_date, 
            end_date=end_date, 
            tx_type=tx_type, 
            item_search=item_search
        )
        
        self.transaction_table.setRowCount(len(data))
        
        for row_index, tx in enumerate(data):
            
            tx_type_upper = tx['type'].upper()
            is_out = tx_type_upper == 'OUT'
            is_reversal = tx_type_upper == 'REVERSAL'
            
            # 填充表格行 (索引已调整，新索引 4 用于位置)
            self.transaction_table.setItem(row_index, 0, QTableWidgetItem(str(tx['id'])))
            self.transaction_table.setItem(row_index, 1, QTableWidgetItem(tx['date']))
            self.transaction_table.setItem(row_index, 2, QTableWidgetItem(tx['item_name']))
            self.transaction_table.setItem(row_index, 3, QTableWidgetItem(tx['item_ref']))
            self.transaction_table.setItem(row_index, 4, QTableWidgetItem(tx['location'])) # <--- 使用 tx['location'] 字段
            self.transaction_table.setItem(row_index, 5, QTableWidgetItem(tx['type']))
            self.transaction_table.setItem(row_index, 6, QTableWidgetItem(str(tx['quantity'])))
            self.transaction_table.setItem(row_index, 7, QTableWidgetItem(tx['recipient_source']))
            self.transaction_table.setItem(row_index, 8, QTableWidgetItem(tx['project_ref']))
            
            # 根据类型设置行颜色：OUT = 红色，IN = 绿色，REVERSAL = 橙色
            if is_out:
                color = QColor(255, 230, 230) # 浅红
            elif is_reversal:
                color = QColor(255, 240, 210) # 浅橙 (用于冲销)
            else:
                color = QColor(230, 255, 230) # 浅绿 (用于入库 IN)

            for col in range(self.transaction_table.columnCount()):
                self.transaction_table.item(row_index, col).setBackground(color)

            # 隐藏 ID 列
            self.transaction_table.setColumnHidden(0, True)

        self.status_label.setText(f"总计 {len(data)} 条交易记录。")
        
        
    def open_transaction_dialog(self, type: str):
        """打开入库或出库对话框"""
        dialog = TransactionDialog(self.db_path, type, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted: 
            # 成功记录交易后，刷新交易记录 (应用当前筛选器)
            self.apply_filters()
            
            # 关键刷新逻辑：直接调用库存页面的刷新方法
            if self.inventory_page_ref:
                self.inventory_page_ref.load_inventory_data()
            
            
    def reverse_transaction_action(self):
        """冲销选中交易的槽函数"""
        selected_rows = self.transaction_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要冲销的交易记录。")
            return
            
        row_index = selected_rows[0].row()
        tx_id = int(self.transaction_table.item(row_index, 0).text())
        tx_type = self.transaction_table.item(row_index, 5).text() # 索引为 5
        
        # 避免冲销冲销记录
        if tx_type == 'REVERSAL':
             QMessageBox.warning(self, "警告", "不能冲销已冲销的交易记录。")
             return

        reply = QMessageBox.question(self, 
            "确认冲销", 
            f"您确定要冲销 ID 为 {tx_id} 的 **{tx_type}** 交易记录吗？\n\n冲销将生成一笔反向交易。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if db_manager.reverse_transaction(self.db_path, tx_id):
                QMessageBox.information(self, "成功", "交易冲销成功，已生成反向交易记录。")
                self.apply_filters() # 刷新交易记录 (应用当前筛选器)
                
                # 关键刷新逻辑：直接调用库存页面的刷新方法
                if self.inventory_page_ref:
                    self.inventory_page_ref.load_inventory_data()
            else:
                QMessageBox.critical(self, "冲销失败", "冲销失败！可能是库存不足以进行反向操作。")


# --- 暂时不需要运行 ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 此处省略了 InventoryPage 的创建，因为在主程序中才能运行
    # window = TransactionPage('honsen_storage.db', None) # 独立运行时需要手动传入 None 或 InventoryPage 实例
    # window.show()
    sys.exit(0)
