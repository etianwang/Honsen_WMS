# inventory_page.py
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QMessageBox, QApplication, QLabel, QDialog, QFileDialog,
    QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import os
# 导入数据库管理器
import db_manager 
from add_item_dialog import AddItemDialog 
from edit_item_dialog import EditItemDialog 
from batch_edit_dialog import BatchEditDialog

class InventoryPage(QWidget):
    """
    库存管理界面：展示和操作 Inventory 表数据。
    实现：根据库存状态（缺货/预警）设置行背景色。
    新增：支持多选和批量编辑功能，以及刷新按钮。
    扩展：增加类别、专业、储存位置筛选功能。
    """
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.all_data = []  # 存储所有数据用于筛选
        self.init_ui()
        self.load_inventory_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- 1. 顶部操作栏 (工具栏) ---
        toolbar_layout = QHBoxLayout()
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入物品名称或型号进行搜索...")
        self.search_input.textChanged.connect(self.filter_data)
        toolbar_layout.addWidget(self.search_input)
        
        # 类别筛选
        toolbar_layout.addWidget(QLabel("类别:"))
        self.category_filter_combo = QComboBox()
        self.category_filter_combo.setFixedWidth(120)
        self.category_filter_combo.addItem("ALL")
        self.category_filter_combo.currentTextChanged.connect(self.filter_data)
        toolbar_layout.addWidget(self.category_filter_combo)
        
        # 专业筛选
        toolbar_layout.addWidget(QLabel("专业:"))
        self.domain_filter_combo = QComboBox()
        self.domain_filter_combo.setFixedWidth(120)
        self.domain_filter_combo.addItem("ALL")
        self.domain_filter_combo.currentTextChanged.connect(self.filter_data)
        toolbar_layout.addWidget(self.domain_filter_combo)
        
        # 储存位置筛选
        toolbar_layout.addWidget(QLabel("储存位置:"))
        self.location_filter_combo = QComboBox()
        self.location_filter_combo.setFixedWidth(120)
        self.location_filter_combo.addItem("ALL")
        self.location_filter_combo.currentTextChanged.connect(self.filter_data)
        toolbar_layout.addWidget(self.location_filter_combo)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 8px;")
        self.refresh_btn.setToolTip("从数据库重新加载最新数据")
        self.refresh_btn.clicked.connect(self.refresh_data)
        toolbar_layout.addWidget(self.refresh_btn)
        
        toolbar_layout.addStretch(1)
        
        # 按钮
        self.add_btn = QPushButton("新增物品")
        self.edit_btn = QPushButton("编辑物品")
        self.batch_edit_btn = QPushButton("批量编辑")
        self.del_btn = QPushButton("删除物品")
        
        # 设置按钮样式
        self.add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.edit_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px;")
        self.batch_edit_btn.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold; padding: 8px;")
        self.del_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px;")
        
        # 连接信号
        self.add_btn.clicked.connect(self.add_item_dialog)
        self.edit_btn.clicked.connect(self.edit_item_dialog) 
        self.batch_edit_btn.clicked.connect(self.batch_edit_action)
        self.del_btn.clicked.connect(self.delete_item_action) 

        toolbar_layout.addWidget(self.add_btn)
        toolbar_layout.addWidget(self.edit_btn)
        toolbar_layout.addWidget(self.batch_edit_btn)
        toolbar_layout.addWidget(self.del_btn)
        
        main_layout.addLayout(toolbar_layout)

        # --- 2. 主数据表格 ---
        self.inventory_table = QTableWidget()
        self.inventory_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.inventory_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.inventory_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)

        # 定义表头（新增 domain 列）
        self.headers = [
            "ID", "名称 (Name)", "物品型号 (Ref)", "材料类别", "专业类别", "单位 (Unit)", 
            "当前库存", "最小库存", "储存位置", "库存状态"
        ]
        self.inventory_table.setColumnCount(len(self.headers))
        self.inventory_table.setHorizontalHeaderLabels(self.headers)
        
        # 调整列宽
        self.inventory_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.inventory_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        main_layout.addWidget(self.inventory_table)
        
        # 底部状态栏
        self.status_label = QLabel("总计 0 条记录。")
        self.status_label.setStyleSheet("padding: 5px; font-weight: bold;")
        main_layout.addWidget(self.status_label)
        
        # 连接选择变化信号
        self.inventory_table.itemSelectionChanged.connect(self.update_status_label)


    def load_inventory_data(self):
        """从数据库加载数据并填充表格"""
        data = db_manager.get_all_inventory(self.db_path)
        
        # 保存所有数据用于筛选
        self.all_data = data
        
        # 刷新筛选下拉框选项
        self._refresh_filter_dropdowns()
        
        # 填充表格
        self._populate_table(data)
        
        # 应用当前筛选
        self.filter_data()


    def _refresh_filter_dropdowns(self):
        """刷新筛选下拉框的选项"""
        if not self.all_data:
            return
        
        # 保存当前选择
        current_category = self.category_filter_combo.currentText()
        current_domain = self.domain_filter_combo.currentText()
        current_location = self.location_filter_combo.currentText()
        
        # 提取所有唯一的类别
        categories = set()
        for item in self.all_data:
            category = item.get('category', '').strip()
            if category:
                categories.add(category)
        
        # 提取所有唯一的专业
        domains = set()
        for item in self.all_data:
            domain = item.get('domain', '').strip()
            if domain:
                domains.add(domain)
        
        # 提取所有唯一的储存位置
        locations = set()
        for item in self.all_data:
            location = item.get('location', '').strip()
            if location:
                locations.add(location)
        
        # 更新类别下拉框
        self.category_filter_combo.blockSignals(True)
        self.category_filter_combo.clear()
        self.category_filter_combo.addItem("ALL")
        self.category_filter_combo.addItems(sorted(list(categories)))
        cat_index = self.category_filter_combo.findText(current_category)
        if cat_index >= 0:
            self.category_filter_combo.setCurrentIndex(cat_index)
        self.category_filter_combo.blockSignals(False)
        
        # 更新专业下拉框
        self.domain_filter_combo.blockSignals(True)
        self.domain_filter_combo.clear()
        self.domain_filter_combo.addItem("ALL")
        self.domain_filter_combo.addItems(sorted(list(domains)))
        dom_index = self.domain_filter_combo.findText(current_domain)
        if dom_index >= 0:
            self.domain_filter_combo.setCurrentIndex(dom_index)
        self.domain_filter_combo.blockSignals(False)
        
        # 更新储存位置下拉框
        self.location_filter_combo.blockSignals(True)
        self.location_filter_combo.clear()
        self.location_filter_combo.addItem("ALL")
        self.location_filter_combo.addItems(sorted(list(locations)))
        loc_index = self.location_filter_combo.findText(current_location)
        if loc_index >= 0:
            self.location_filter_combo.setCurrentIndex(loc_index)
        self.location_filter_combo.blockSignals(False)


    def _populate_table(self, data):
        """填充表格数据"""
        self.inventory_table.setRowCount(len(data))
        
        # 定义颜色常量
        critical_color = QColor(255, 179, 179)
        warning_color = QColor(255, 240, 192)
        default_color = QColor(255, 255, 255)
        
        for row_index, item in enumerate(data):
            
            # 检查库存预警状态
            current = item['current_stock']
            minimum = item['min_stock']
            status_text = "正常"
            
            color = default_color
            if current <= 0:
                status_text = "缺货"
                color = critical_color
            elif current <= minimum:
                status_text = "预警"
                color = warning_color
            
            # 填充表格行（新增 domain 列）
            self.inventory_table.setItem(row_index, 0, QTableWidgetItem(str(item['id'])))
            self.inventory_table.setItem(row_index, 1, QTableWidgetItem(item['name']))
            self.inventory_table.setItem(row_index, 2, QTableWidgetItem(item['reference']))
            self.inventory_table.setItem(row_index, 3, QTableWidgetItem(item.get('category', '其他')))
            self.inventory_table.setItem(row_index, 4, QTableWidgetItem(item.get('domain', '其他')))  # 新增
            self.inventory_table.setItem(row_index, 5, QTableWidgetItem(item['unit']))
            self.inventory_table.setItem(row_index, 6, QTableWidgetItem(str(current)))
            self.inventory_table.setItem(row_index, 7, QTableWidgetItem(str(minimum)))
            self.inventory_table.setItem(row_index, 8, QTableWidgetItem(item['location']))
            self.inventory_table.setItem(row_index, 9, QTableWidgetItem(status_text))
            
            # 应用行颜色
            for col in range(self.inventory_table.columnCount()):
                self.inventory_table.item(row_index, col).setBackground(color)
            
            # 隐藏 ID 列
            self.inventory_table.setColumnHidden(0, True)

        self.update_status_label()


    def refresh_data(self):
        """刷新按钮的处理函数：重新从数据库加载数据"""
        self.load_inventory_data()
        self.status_label.setText(f"数据已刷新 | 总计 {self.inventory_table.rowCount()} 条记录。")


    def update_status_label(self):
        """更新状态栏，显示总记录数和选中数量"""
        total_count = self.inventory_table.rowCount()
        selected_count = len(self.inventory_table.selectionModel().selectedRows())
        
        if selected_count > 0:
            self.status_label.setText(f"总计 {total_count} 条记录，已选中 {selected_count} 条。")
        else:
            self.status_label.setText(f"总计 {total_count} 条记录。")


    def filter_data(self):
        """根据搜索框和筛选下拉框内容过滤表格行"""
        search_text = self.search_input.text().lower().strip()
        category_filter = self.category_filter_combo.currentText()
        domain_filter = self.domain_filter_combo.currentText()
        location_filter = self.location_filter_combo.currentText()
        
        visible_count = 0
        
        for i in range(self.inventory_table.rowCount()):
            name_item = self.inventory_table.item(i, 1)
            ref_item = self.inventory_table.item(i, 2)
            category_item = self.inventory_table.item(i, 3)
            domain_item = self.inventory_table.item(i, 4)
            location_item = self.inventory_table.item(i, 8)
            
            hide = False
            
            # 搜索框筛选
            if search_text:
                name_match = name_item and search_text in name_item.text().lower()
                ref_match = ref_item and search_text in ref_item.text().lower()
                if not (name_match or ref_match):
                    hide = True
            
            # 类别筛选
            if not hide and category_filter != "ALL":
                if not category_item or category_item.text() != category_filter:
                    hide = True
            
            # 专业筛选
            if not hide and domain_filter != "ALL":
                if not domain_item or domain_item.text() != domain_filter:
                    hide = True
            
            # 储存位置筛选
            if not hide and location_filter != "ALL":
                if not location_item or location_item.text() != location_filter:
                    hide = True
            
            self.inventory_table.setRowHidden(i, hide)
            
            if not hide:
                visible_count += 1
        
        # 更新状态栏显示筛选结果
        total_count = self.inventory_table.rowCount()
        if visible_count < total_count:
            self.status_label.setText(f"筛选结果：显示 {visible_count} / {total_count} 条记录。")
        else:
            self.status_label.setText(f"总计 {total_count} 条记录。")
            
        
    def add_item_dialog(self):
        """显示新增物品对话框"""
        dialog = AddItemDialog(self.db_path, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted: 
            self.load_inventory_data()
            
            
    def edit_item_dialog(self):
        """编辑选中物品"""
        selected_rows = self.inventory_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要编辑的物品行。")
            return
        
        if len(selected_rows) > 1:
            reply = QMessageBox.question(
                self,
                "多选提示",
                f"您选中了 {len(selected_rows)} 个物品。\n\n是否使用批量编辑功能？ \n选择'否'将只编辑第一个选中的物品。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.batch_edit_action()
                return
            
        row_index = selected_rows[0].row()
        
        # 提取选中行的数据（新增 domain 字段）
        item_data = {
            'id': int(self.inventory_table.item(row_index, 0).text()),
            'name': self.inventory_table.item(row_index, 1).text(),
            'reference': self.inventory_table.item(row_index, 2).text(),
            'category': self.inventory_table.item(row_index, 3).text(),
            'domain': self.inventory_table.item(row_index, 4).text(),  # 新增
            'unit': self.inventory_table.item(row_index, 5).text(),
            'current_stock': int(self.inventory_table.item(row_index, 6).text()),
            'min_stock': int(self.inventory_table.item(row_index, 7).text()),
            'location': self.inventory_table.item(row_index, 8).text()
        }
        
        # 弹出编辑对话框
        dialog = EditItemDialog(self.db_path, item_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted: 
            self.load_inventory_data()


    def batch_edit_action(self):
        """批量编辑选中的物品"""
        selected_rows = self.inventory_table.selectionModel().selectedRows()
        
        if len(selected_rows) == 0:
            QMessageBox.warning(self, "警告", "请先选择要批量编辑的物品。提示：按住Ctrl键点击可以多选。")
            return
        
        if len(selected_rows) == 1:
            reply = QMessageBox.question(self, "单选提示", "您只选中了一个物品。是否使用普通编辑功能？", 
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                        QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.Yes:
                self.edit_item_dialog()
            return
        
        # 收集选中物品的完整信息（新增 domain 字段）
        selected_items = []
        for row_model_index in selected_rows:
            row = row_model_index.row()
            item_data = {
                'id': int(self.inventory_table.item(row, 0).text()),
                'name': self.inventory_table.item(row, 1).text(),
                'reference': self.inventory_table.item(row, 2).text(),
                'category': self.inventory_table.item(row, 3).text(),
                'domain': self.inventory_table.item(row, 4).text(),  # 新增
                'unit': self.inventory_table.item(row, 5).text(),
                'current_stock': int(self.inventory_table.item(row, 6).text()),
                'min_stock': int(self.inventory_table.item(row, 7).text()),
                'location': self.inventory_table.item(row, 8).text()
            }
            selected_items.append(item_data)
        
        # 打开批量编辑对话框
        dialog = BatchEditDialog(self.db_path, selected_items, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_inventory_data()


    def delete_item_action(self):
        """删除选中物品"""
        selected_rows = self.inventory_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的物品行。")
            return
        
        # 支持多选删除
        if len(selected_rows) > 1:
            reply = QMessageBox.question(
                self,
                "确认批量删除",
                f"您确定要删除选中的 {len(selected_rows)} 个物品吗？\n\n⚠️ 注意：此操作将同时删除这些物品及其所有相关的交易记录！\n数据不可恢复！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success_count = 0
                failed_count = 0
                
                for row_model_index in selected_rows:
                    row = row_model_index.row()
                    item_id = int(self.inventory_table.item(row, 0).text())
                    
                    if db_manager.delete_inventory_item(self.db_path, item_id):
                        success_count += 1
                    else:
                        failed_count += 1
                
                if failed_count == 0:
                    QMessageBox.information(self, "成功", f"成功删除了 {success_count} 个物品及其关联交易记录。")
                else:
                    QMessageBox.warning(self, "部分失败", f"成功删除：{success_count} 个\n失败：{failed_count} 个")
                
                self.load_inventory_data()
            return
            
        # 单个删除
        row_index = selected_rows[0].row()
        item_id = int(self.inventory_table.item(row_index, 0).text())
        item_name = self.inventory_table.item(row_index, 1).text()
        
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"您确定要删除物品 **{item_name}** (ID: {item_id}) 吗？\n\n注意：此操作将同时删除该物品及其所有相关的交易记录，数据不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if db_manager.delete_inventory_item(self.db_path, item_id):
                QMessageBox.information(self, "成功", "物品及关联交易记录已成功删除。")
                self.load_inventory_data()
            else:
                QMessageBox.critical(self, "删除失败", "删除失败！请检查数据库连接或确认该物品ID是否存在。")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    TEST_DB_PATH = 'honsen_storage.db' 
    
    if not os.path.exists(TEST_DB_PATH):
        print("警告: 数据库文件不存在，请先通过 login.py 初始化。")