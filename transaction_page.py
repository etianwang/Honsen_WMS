import sys
import csv # 导入 csv 模块用于更规范的 CSV 写入
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QMessageBox, QDialog, QApplication, QLabel,
    QDateEdit, QComboBox, QFileDialog # 导入 QFileDialog 用于导出
)
from PyQt6.QtCore import Qt, QDateTime, QDate 
from PyQt6.QtGui import QColor
from typing import Optional, List, Dict, Union 

# 导入数据库管理器和交易对话框
import db_manager 
from transaction_dialog import TransactionDialog 

class TransactionPage(QWidget):
    """
    交易记录界面：展示 Transactions 表数据，并提供筛选、入库/出库和冲销操作。
    增加了类别、地点和项目筛选和底部统计功能，以及导出功能。
    """
    def __init__(self, db_path: str, inventory_page_ref): 
        super().__init__()
        self.db_path = db_path
        self.inventory_page_ref = inventory_page_ref # 存储对库存页面的直接引用
        self.current_data: List[Dict[str, Union[int, str]]] = [] # 存储当前筛选后的数据
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
        
        # --- 2. 筛选区域 (调整为两行布局) ---
        filter_container = QVBoxLayout()
        
        # --- 筛选行 1: 日期范围 ---
        filter_row1 = QHBoxLayout()
        
        filter_row1.addWidget(QLabel("从日期:"))
        self.start_date_edit = QDateEdit(calendarPopup=True)
        self.start_date_edit.setDate(QDate.currentDate().addYears(-1))
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        filter_row1.addWidget(self.start_date_edit)
        
        filter_row1.addWidget(QLabel("到日期:"))
        self.end_date_edit = QDateEdit(calendarPopup=True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        filter_row1.addWidget(self.end_date_edit)
        
        filter_row1.addStretch(1) # 增加弹性空间
        
        filter_container.addLayout(filter_row1)

        # --- 筛选行 2: 类别、地点、项目、类型、搜索 & 按钮 ---
        filter_row2 = QHBoxLayout()

        # A. 类别筛选
        filter_row2.addWidget(QLabel("类别:"))
        self.category_filter_combo = QComboBox()
        category_options = ["ALL"] + db_manager.get_config_options(self.db_path, 'CATEGORY')
        self.category_filter_combo.addItems(category_options)
        filter_row2.addWidget(self.category_filter_combo)

        # B. 地点筛选
        filter_row2.addWidget(QLabel("地点:"))
        self.location_filter_combo = QComboBox()
        location_options = ["ALL"] + db_manager.get_config_options(self.db_path, 'LOCATION')
        self.location_filter_combo.addItems(location_options)
        filter_row2.addWidget(self.location_filter_combo)

        # C. 项目筛选
        filter_row2.addWidget(QLabel("项目:"))
        self.project_filter_combo = QComboBox()
        project_options = ["ALL"] + db_manager.get_config_options(self.db_path, 'PROJECT')
        self.project_filter_combo.addItems(project_options)
        filter_row2.addWidget(self.project_filter_combo)

        # D. 类型筛选
        filter_row2.addWidget(QLabel("类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["ALL", "IN", "OUT", "REVERSAL"])
        filter_row2.addWidget(self.type_combo)

        # E. 物品搜索
        filter_row2.addWidget(QLabel("物品搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("物品名称或型号")
        filter_row2.addWidget(self.search_input)
        
        # F. 筛选/刷新按钮
        self.filter_btn = QPushButton("筛选/刷新")
        self.filter_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        self.filter_btn.clicked.connect(self.apply_filters)
        filter_row2.addWidget(self.filter_btn)

        # G. 导出筛选结果按钮 
        self.export_btn = QPushButton("导出筛选结果 (CSV)")
        self.export_btn.setStyleSheet("background-color: #00BCD4; color: white; font-weight: bold; padding: 8px;")
        self.export_btn.clicked.connect(self.export_filtered_transactions_action)
        filter_row2.addWidget(self.export_btn)
        
        filter_container.addLayout(filter_row2)
        
        main_layout.addLayout(filter_container)

        # --- 3. 主数据表格 ---
        self.transaction_table = QTableWidget()
        self.transaction_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.transaction_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.transaction_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection) 

        # 定义表头
        self.headers = [
            "ID", "日期/时间", "物品名称", "物品型号", 
            "储存位置", "类型", "数量", "接收人/来源", "项目"
        ]
        self.transaction_table.setColumnCount(len(self.headers))
        self.transaction_table.setHorizontalHeaderLabels(self.headers)
        
        # 调整列宽
        self.transaction_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.transaction_table.horizontalHeader().resizeSection(1, 160)
        self.transaction_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.transaction_table.horizontalHeader().resizeSection(4, 120) 
        
        main_layout.addWidget(self.transaction_table)
        
        # 底部状态栏
        self.status_label = QLabel("总计 0 条交易记录。")
        self.status_label.setStyleSheet("padding: 5px; font-weight: bold; border-top: 1px solid #ccc;")
        main_layout.addWidget(self.status_label)

    # ----------------------------------------
    # --- 筛选和数据加载逻辑 ---
    # ----------------------------------------

    def apply_filters(self):
        """读取筛选控件的值并加载数据"""
        start_date = self.start_date_edit.date().toString('yyyy-MM-dd')
        end_date = self.end_date_edit.date().toString('yyyy-MM-dd')
        
        category = self.category_filter_combo.currentText()
        location = self.location_filter_combo.currentText()
        project = self.project_filter_combo.currentText()
        tx_type = self.type_combo.currentText()
        item_search = self.search_input.text().strip()
        
        # 转换 'ALL' 和空字符串/None 为 None
        category = category if category and category != 'ALL' else None
        location = location if location and location != 'ALL' else None
        project = project if project and project != 'ALL' else None
        tx_type = tx_type if tx_type and tx_type != 'ALL' else None
        item_search = item_search if item_search else None
        
        self._load_data_with_filters(
            start_date=start_date,
            end_date=end_date,
            tx_type=tx_type,
            item_search=item_search,
            category=category, 
            location=location, 
            project=project 	
        )
        
    def load_transaction_data(self):
        """初始加载数据"""
        self.apply_filters()


    def _load_data_with_filters(self, start_date: Optional[str] = None, end_date: Optional[str] = None, 
                                 tx_type: Optional[str] = None, item_search: Optional[str] = None,
                                 category: Optional[str] = None, location: Optional[str] = None,
                                 project: Optional[str] = None): 
        """
        根据筛选参数从数据库加载数据并填充表格
        """
        
        data = db_manager.get_transactions_history(
            self.db_path, 
            start_date=start_date, 
            end_date=end_date, 
            tx_type=tx_type, 
            item_search=item_search,
            category=category, 
            location=location, 
            project=project 	
        )
        
        # 关键步骤：存储当前筛选结果供导出使用
        self.current_data = data 
        
        # --- 状态栏统计计算 ---
        total_transactions = len(data)
        total_in_qty = 0
        total_out_qty = 0
        unique_locations = set()
        unique_projects = set()
        
        for tx in data:
            quantity = tx['quantity']
            tx_type_upper = tx['type'].upper()
            
            if tx_type_upper == 'IN':
                total_in_qty += quantity
            elif tx_type_upper == 'OUT':
                total_out_qty += quantity
                
            if tx.get('location'):
                unique_locations.add(tx['location'])
                
            project_ref = tx.get('project_ref')
            if project_ref and project_ref.strip() and not project_ref.startswith("Reversed TX:"):
                unique_projects.add(project_ref)

        # 格式化状态栏信息
        stats_msg = (
            f"筛选结果: **共 {total_transactions} 条记录**。"
            f" 入库总数量: {total_in_qty}，出库总数量: {total_out_qty}。"
            f" 涉及 **{len(unique_locations)} 个地点**，用于 **{len(unique_projects)} 个项目**。"
        )
        # ----------------------

        self.transaction_table.setRowCount(len(data))
        
        for row_index, tx in enumerate(data):
            
            tx_type_upper = tx['type'].upper()
            is_out = tx_type_upper == 'OUT'
            is_reversal = tx_type_upper == 'REVERSAL'
            
            # 填充表格行
            self.transaction_table.setItem(row_index, 0, QTableWidgetItem(str(tx['id'])))
            self.transaction_table.setItem(row_index, 1, QTableWidgetItem(tx['date']))
            self.transaction_table.setItem(row_index, 2, QTableWidgetItem(tx['item_name']))
            self.transaction_table.setItem(row_index, 3, QTableWidgetItem(tx['item_ref']))
            self.transaction_table.setItem(row_index, 4, QTableWidgetItem(tx['location']))
            self.transaction_table.setItem(row_index, 5, QTableWidgetItem(tx['type']))
            self.transaction_table.setItem(row_index, 6, QTableWidgetItem(str(tx['quantity'])))
            self.transaction_table.setItem(row_index, 7, QTableWidgetItem(tx['recipient_source']))
            self.transaction_table.setItem(row_index, 8, QTableWidgetItem(tx['project_ref']))
            
            # 设置行颜色
            if is_out:
                color = QColor(255, 230, 230) 
            elif is_reversal:
                color = QColor(255, 240, 210) 
            else:
                color = QColor(230, 255, 230) 

            for col in range(self.transaction_table.columnCount()):
                self.transaction_table.item(row_index, col).setBackground(color)

            self.transaction_table.setColumnHidden(0, True)

        # 更新状态栏
        self.status_label.setText(stats_msg) 
        
    # ----------------------------------------
    # --- 交易操作逻辑 ---
    # ----------------------------------------
            
    def open_transaction_dialog(self, type: str):
        """打开入库或出库对话框"""
        dialog = TransactionDialog(self.db_path, type, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted: 
            self.apply_filters()
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
        tx_type = self.transaction_table.item(row_index, 5).text() 
        
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
                self.apply_filters()
                if self.inventory_page_ref:
                    self.inventory_page_ref.load_inventory_data()
            else:
                QMessageBox.critical(self, "冲销失败", "冲销失败！可能是库存不足以进行反向操作。")


    # ----------------------------------------
    # --- 导出功能 (更新) ---
    # ----------------------------------------
    def export_filtered_transactions_action(self):
        """将当前筛选结果导出为 CSV 文件，并弹出保存路径选择框。"""
        if not self.current_data:
            QMessageBox.warning(self, "警告", "没有筛选结果可供导出。请先执行筛选。")
            return
        
        # 弹出文件保存对话框
        default_filename = f"transactions_export_{QDate.currentDate().toString('yyyyMMdd')}.csv"
        # 使用 QFileDialog 获取保存路径
        filepath, _ = QFileDialog.getSaveFileName(
            self, 
            "导出筛选结果为 CSV", 
            default_filename,      
            "CSV Files (*.csv);;All Files (*)"
        )

        if not filepath:
            # 用户取消了保存操作
            return
        
        # 定义 CSV 头部和对应的字典键
        csv_headers = [
            "日期/时间", "物品名称", "物品型号", 
            "储存位置", "类型", "数量", "接收人/来源", "项目"
        ]
        data_keys = [
            'date', 'item_name', 'item_ref', 
            'location', 'type', 'quantity', 'recipient_source', 'project_ref'
        ]
        
        # 写入文件
        try:
            # 使用 'w' 模式和 'utf-8' 编码来确保中文正确显示
            with open(filepath, 'w', encoding='utf-8', newline='') as csvfile:
                # 使用 csv 模块进行写入，处理引号和逗号等特殊字符
                writer = csv.writer(csvfile)
                
                # 写入头部
                writer.writerow(csv_headers)
                
                # 写入数据行
                for tx in self.current_data:
                    row = [tx.get(key, '') for key in data_keys]
                    writer.writerow(row)
            
            # 成功反馈
            QMessageBox.information(self, "导出成功", f"筛选结果已成功导出到：\n**{filepath}**")
            
        except Exception as e:
            # 失败反馈
            QMessageBox.critical(self, "导出失败", f"文件写入失败：\n{str(e)}")


# --- 暂时不需要运行 ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    sys.exit(0)
