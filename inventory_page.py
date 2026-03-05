# Inventory_page.py
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QMessageBox, QApplication, QLabel, QDialog, QFileDialog,
    QComboBox
)
from PyQt6.QtCore import Qt, QTimer
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
    【更新】表格仅保留“柜号”列 (已合并初始柜号)。
    """
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.all_data = []  # 存储所有数据用于筛选
        self.init_ui()
        self.load_Inventory_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- 1. 顶部操作栏 (工具栏) ---
        toolbar_layout = QHBoxLayout()
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索：名称、型号 或 柜号...")
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
        self.Inventory_table = QTableWidget()
        self.Inventory_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.Inventory_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.Inventory_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)

        # 定义表头：【修改】移除"初始柜号"，只保留"柜号"
        # 索引: 0:ID, 1:Name, 2:Ref, 3:Category, 4:Domain, 5:Unit, 
        #      6:Current, 7:Min, 8:Location, 9:Cabinet, 10:Status
        self.headers = [
            "ID", "名称 (Name)", "物品型号 (Ref)", "材料类别", "专业类别", "单位 (Unit)", 
            "当前库存", "最小库存", "储存位置", "柜号", "库存状态"
        ]
        self.Inventory_table.setColumnCount(len(self.headers))
        self.Inventory_table.setHorizontalHeaderLabels(self.headers)
        
        # 调整列宽
        self.Inventory_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.Inventory_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        main_layout.addWidget(self.Inventory_table)
        
        # 底部状态栏
        self.status_label = QLabel("总计 0 条记录。")
        self.status_label.setStyleSheet("padding: 5px; font-weight: bold;")
        main_layout.addWidget(self.status_label)
        
        # 连接选择变化信号
        self.Inventory_table.itemSelectionChanged.connect(self.update_status_label)


    def load_Inventory_data(self):
        """从数据库加载数据并填充表格"""
        print("⏳ [Load] 开始从数据库读取...")
        data = db_manager.get_all_Inventory(self.db_path)
        print(f"✅ [Load] 读取完成，共 {len(data)} 条数据。开始填充表格...")
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


    # def _populate_table(self, data):
    #     """填充表格数据 - 【性能优化版】"""
    #     print(f"⚙️ [Render] 准备渲染 {len(data)} 行数据...")
        
    #     # 🔥【关键优化 1】暂停界面重绘，防止每填一个格子就刷新一次
    #     self.Inventory_table.setUpdatesEnabled(False)
    #     self.Inventory_table.setSortingEnabled(False) # 暂时关闭排序
        
    #     try:
    #         self.Inventory_table.setRowCount(len(data))
            
    #         # 定义颜色常量
    #         critical_color = QColor(255, 179, 179)
    #         warning_color = QColor(255, 240, 192)
    #         default_color = QColor(255, 255, 255)
            
    #         for row_index, item in enumerate(data):
    #             # 检查库存预警状态
    #             current = item['current_stock']
    #             minimum = item['min_stock']
    #             status_text = "正常"
    #             color = default_color
                
    #             if current <= 0:
    #                 status_text = "缺货"
    #                 color = critical_color
    #             elif current <= minimum:
    #                 status_text = "预警"
    #                 color = warning_color
                
    #             # 填充数据 (此时界面不会重绘，速度极快)
    #             # 为了代码简洁，可以使用循环或逐个设置，这里保持逐个设置以便调试
    #             self.Inventory_table.setItem(row_index, 0, QTableWidgetItem(str(item['id'])))
    #             self.Inventory_table.setItem(row_index, 1, QTableWidgetItem(item['name']))
    #             self.Inventory_table.setItem(row_index, 2, QTableWidgetItem(item['reference']))
    #             self.Inventory_table.setItem(row_index, 3, QTableWidgetItem(item.get('category', '其他')))
    #             self.Inventory_table.setItem(row_index, 4, QTableWidgetItem(item.get('domain', '其他')))
    #             self.Inventory_table.setItem(row_index, 5, QTableWidgetItem(item['unit']))
    #             self.Inventory_table.setItem(row_index, 6, QTableWidgetItem(str(current)))
    #             self.Inventory_table.setItem(row_index, 7, QTableWidgetItem(str(minimum)))
    #             self.Inventory_table.setItem(row_index, 8, QTableWidgetItem(item['location']))
                
    #             cabinet = item.get('cabinet', '')
    #             self.Inventory_table.setItem(row_index, 9, QTableWidgetItem(cabinet))
    #             self.Inventory_table.setItem(row_index, 10, QTableWidgetItem(status_text))
                
    #             # 🔥【关键优化 2】批量设置背景色
    #             # 注意：setBackground 依然需要逐个调用，但在 setUpdatesEnabled(False) 下非常快
    #             for col in range(self.Inventory_table.columnCount()):
    #                 cell_item = self.Inventory_table.item(row_index, col)
    #                 if cell_item:
    #                     cell_item.setBackground(color)
                
    #             # 隐藏 ID 列 (只需设置一次，放在循环外更好，但放在里面也没事，因为被暂停了)
    #             if row_index == 0:
    #                 self.Inventory_table.setColumnHidden(0, True)

    #         # 更新状态栏
    #         self.update_status_label()
            
    #         print("🎉 [Render] 数据填充完成，正在恢复重绘...")
            
    #     finally:
    #         # 🔥【关键优化 3】恢复界面重绘，此时界面会瞬间“刷”出来
    #         self.Inventory_table.setUpdatesEnabled(True)
    #         self.Inventory_table.setSortingEnabled(True)
    #         # 强制刷新一次视图，确保显示最新状态
    #         self.Inventory_table.viewport().update()

    def _populate_table(self, data):
        """填充表格数据 - 【视觉优化版：突出显示地点和柜号】"""
        print(f"⚙️ [Render] 准备渲染 {len(data)} 行数据...")
        
        # 🔥【关键优化 1】暂停界面重绘
        self.Inventory_table.setUpdatesEnabled(False)
        self.Inventory_table.setSortingEnabled(False)
        
        try:
            self.Inventory_table.setRowCount(len(data))
            
            # 定义颜色常量
            critical_color = QColor(255, 179, 179) # 缺货红
            warning_color = QColor(255, 240, 192)  # 预警黄
            default_color = QColor(255, 255, 255)  # 正常白
            
            for row_index, item in enumerate(data):
                # 1. 计算库存状态和颜色
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
                
                # 2. 【核心修改】构建智能显示名称
                # 格式：名称 + [地点] + (柜号)
                name = item['name']
                location = item.get('location', '')
                cabinet = item.get('cabinet', '')
                
                display_name = name
                if location:
                    display_name += f" 📍[{location}]"
                if cabinet:
                    display_name += f" 🗄️({cabinet})"
                
                # 3. 填充数据
                # 第 1 列：名称 (使用智能显示名称)
                name_item = QTableWidgetItem(display_name)
                name_item.setToolTip(f"原始名称: {name}\n地点: {location}\n柜号: {cabinet}\n型号: {item.get('reference', '')}")
                self.Inventory_table.setItem(row_index, 1, name_item)
                
                # 其他列保持原样
                self.Inventory_table.setItem(row_index, 0, QTableWidgetItem(str(item['id'])))
                self.Inventory_table.setItem(row_index, 2, QTableWidgetItem(item['reference']))
                self.Inventory_table.setItem(row_index, 3, QTableWidgetItem(item.get('category', '其他')))
                self.Inventory_table.setItem(row_index, 4, QTableWidgetItem(item.get('domain', '其他')))
                self.Inventory_table.setItem(row_index, 5, QTableWidgetItem(item['unit']))
                self.Inventory_table.setItem(row_index, 6, QTableWidgetItem(str(current)))
                self.Inventory_table.setItem(row_index, 7, QTableWidgetItem(str(minimum)))
                
                # 第 8 列：地点 (单独保留一列，方便筛选)
                loc_item = QTableWidgetItem(location)
                loc_item.setToolTip(f"完整位置: {location} - {cabinet}")
                self.Inventory_table.setItem(row_index, 8, loc_item)
                
                # 第 9 列：柜号
                self.Inventory_table.setItem(row_index, 9, QTableWidgetItem(cabinet))
                
                # 第 10 列：状态
                self.Inventory_table.setItem(row_index, 10, QTableWidgetItem(status_text))
                
                # 4. 批量设置背景色
                for col in range(self.Inventory_table.columnCount()):
                    cell_item = self.Inventory_table.item(row_index, col)
                    if cell_item:
                        cell_item.setBackground(color)
                
                # 隐藏 ID 列 (只在第一行执行一次判断即可，但在循环内也无妨，因为被暂停了)
                if row_index == 0:
                    self.Inventory_table.setColumnHidden(0, True)

            self.update_status_label()
            print("🎉 [Render] 数据填充完成。")
            
        finally:
            # 🔥【关键优化 3】恢复界面重绘
            self.Inventory_table.setUpdatesEnabled(True)
            self.Inventory_table.setSortingEnabled(True)
            self.Inventory_table.viewport().update()

    def refresh_data(self):
        """刷新按钮的处理函数：重新从数据库加载数据"""
        self.load_Inventory_data()
        self.status_label.setText(f"数据已刷新 | 总计 {self.Inventory_table.rowCount()} 条记录。")


    def update_status_label(self):
        """更新状态栏，显示总记录数和选中数量"""
        total_count = self.Inventory_table.rowCount()
        selected_count = len(self.Inventory_table.selectionModel().selectedRows())
        
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
        
        for i in range(self.Inventory_table.rowCount()):
            # 获取表格中的数据项
            name_item = self.Inventory_table.item(i, 1)
            ref_item = self.Inventory_table.item(i, 2)
            category_item = self.Inventory_table.item(i, 3)
            domain_item = self.Inventory_table.item(i, 4)
            location_item = self.Inventory_table.item(i, 8) # 地点列
            
            # 获取原始数据 (用于获取准确的 cabinet)
            item_data = self.all_data[i] if i < len(self.all_data) else {}
            cabinet = item_data.get('cabinet', '').lower()
            location_raw = item_data.get('location', '').lower() # 获取原始地点用于搜索

            hide = False
            
            # --- 搜索框筛选逻辑 ---
            if search_text:
                name_match = name_item and search_text in name_item.text().lower()
                ref_match = ref_item and search_text in ref_item.text().lower()
                cabinet_match = search_text in cabinet
                location_match = search_text in location_raw # 【新增】支持搜地点

                # 只要有一个匹配就不隐藏
                if not (name_match or ref_match or cabinet_match or location_match):
                    hide = True
            
            # --- 下拉框筛选逻辑 (保持不变) ---
            if not hide and category_filter != "ALL":
                if not category_item or category_item.text() != category_filter:
                    hide = True
            
            if not hide and domain_filter != "ALL":
                if not domain_item or domain_item.text() != domain_filter:
                    hide = True
            
            if not hide and location_filter != "ALL":
                if not location_item or location_item.text() != location_filter:
                    hide = True
            
            self.Inventory_table.setRowHidden(i, hide)
            
            if not hide:
                visible_count += 1
        
        # 更新状态栏
        total_count = self.Inventory_table.rowCount()
        if visible_count < total_count:
            self.status_label.setText(f"筛选结果：显示 {visible_count} / {total_count} 条记录。")
        else:
            self.status_label.setText(f"总计 {total_count} 条记录。")
            
    # def filter_data(self):
    #     """根据搜索框和筛选下拉框内容过滤表格行"""
    #     search_text = self.search_input.text().lower().strip()
    #     category_filter = self.category_filter_combo.currentText()
    #     domain_filter = self.domain_filter_combo.currentText()
    #     location_filter = self.location_filter_combo.currentText()
        
    #     visible_count = 0
        
    #     for i in range(self.Inventory_table.rowCount()):
    #         name_item = self.Inventory_table.item(i, 1)
    #         ref_item = self.Inventory_table.item(i, 2)
    #         category_item = self.Inventory_table.item(i, 3)
    #         domain_item = self.Inventory_table.item(i, 4)
    #         location_item = self.Inventory_table.item(i, 8)
            
    #         item_data = self.all_data[i] if i < len(self.all_data) else {}
            
    #         # 【修改】只获取合并后的柜号
    #         cabinet = item_data.get('cabinet', '').lower()

    #         hide = False
            
    #         # 搜索框筛选
    #         if search_text:
    #             name_match = name_item and search_text in name_item.text().lower()
    #             ref_match = ref_item and search_text in ref_item.text().lower()
                 
    #             # 【修改】只匹配当前柜号
    #             cabinet_match = search_text in cabinet

    #             if not (name_match or ref_match or cabinet_match):
    #                 hide = True
            
    #         # 类别筛选
    #         if not hide and category_filter != "ALL":
    #             if not category_item or category_item.text() != category_filter:
    #                 hide = True
            
    #         # 专业筛选
    #         if not hide and domain_filter != "ALL":
    #             if not domain_item or domain_item.text() != domain_filter:
    #                 hide = True
            
    #         # 储存位置筛选
    #         if not hide and location_filter != "ALL":
    #             if not location_item or location_item.text() != location_filter:
    #                 hide = True
            
    #         self.Inventory_table.setRowHidden(i, hide)
            
    #         if not hide:
    #             visible_count += 1
        
    #     # 更新状态栏显示筛选结果
    #     total_count = self.Inventory_table.rowCount()
    #     if visible_count < total_count:
    #         self.status_label.setText(f"筛选结果：显示 {visible_count} / {total_count} 条记录。")
    #     else:
    #         self.status_label.setText(f"总计 {total_count} 条记录。")
            
        
    def add_item_dialog(self):
        """显示新增物品对话框"""
        dialog = AddItemDialog(self.db_path, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted: 
            # ❌ 旧代码 (容易卡):
            # self.load_Inventory_data()
            
            # ✅ 新代码 (延迟 300ms 刷新，确保锁释放):
            QTimer.singleShot(300, self.load_Inventory_data)
            
            
    def edit_item_dialog(self):
        """编辑选中物品"""
        selected_rows = self.Inventory_table.selectionModel().selectedRows()
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
        
        item_id = int(self.Inventory_table.item(row_index, 0).text())
        # 为了获取准确的 cabinet，从 all_data 取
        item_data = next((item for item in self.all_data if item['id'] == item_id), None)
        
        if not item_data:
             QMessageBox.critical(self, "错误", "无法找到该物品的详细数据。")
             return

        # 构建编辑所需数据字典
        edit_data = {
            'id': item_data['id'],
            'name': item_data['name'],
            'reference': item_data['reference'],
            'category': item_data.get('category', '其他'),
            'domain': item_data.get('domain', '其他'),
            'unit': item_data['unit'],
            'current_stock': item_data['current_stock'],
            'min_stock': item_data['min_stock'],
            'location': item_data['location'],
            'cabinet': item_data.get('cabinet', '')
            # 【修改】移除了 initial_cabinet
        }
        
        # 弹出编辑对话框
        dialog = EditItemDialog(self.db_path, edit_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted: 
            # ❌ 旧代码:
            # self.load_Inventory_data()
            
            # ✅ 新代码:
            QTimer.singleShot(300, self.load_Inventory_data)


    def batch_edit_action(self):
        """批量编辑选中的物品"""
        selected_rows = self.Inventory_table.selectionModel().selectedRows()
        
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
        
        # 收集选中物品的完整信息
        selected_items = []
        for row_model_index in selected_rows:
            row = row_model_index.row()
            item_id = int(self.Inventory_table.item(row, 0).text())
            
            # 从 all_data 中查找完整信息
            item_data = next((item for item in self.all_data if item['id'] == item_id), None)
            
            if item_data:
                selected_items.append({
                    'id': item_data['id'],
                    'name': item_data['name'],
                    'reference': item_data['reference'],
                    'category': item_data.get('category', '其他'),
                    'domain': item_data.get('domain', '其他'),
                    'unit': item_data['unit'],
                    'current_stock': item_data['current_stock'],
                    'min_stock': item_data['min_stock'],
                    'location': item_data['location'],
                    'cabinet': item_data.get('cabinet', '')
                    # 【修改】移除了 initial_cabinet
                })
        
        # 打开批量编辑对话框
        if selected_items:
            dialog = BatchEditDialog(self.db_path, selected_items, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # ❌ 旧代码:
                # self.load_Inventory_data()
                
                # ✅ 新代码:
                QTimer.singleShot(300, self.load_Inventory_data)


    def delete_item_action(self):
        """删除选中物品"""
        selected_rows = self.Inventory_table.selectionModel().selectedRows()
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
                    item_id = int(self.Inventory_table.item(row, 0).text())
                    
                    if db_manager.delete_Inventory_item(self.db_path, item_id):
                        success_count += 1
                    else:
                        failed_count += 1
                
                if failed_count == 0:
                    QMessageBox.information(self, "成功", f"成功删除了 {success_count} 个物品及其关联交易记录。")
                else:
                    QMessageBox.warning(self, "部分失败", f"成功删除：{success_count} 个\n失败：{failed_count} 个")
                
                # self.load_Inventory_data()
                QTimer.singleShot(300, self.load_Inventory_data)
            return
            
        # 单个删除
        row_index = selected_rows[0].row()
        item_id = int(self.Inventory_table.item(row_index, 0).text())
        item_name = self.Inventory_table.item(row_index, 1).text()
        
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"您确定要删除物品 **{item_name}** (ID: {item_id}) 吗？\n\n注意：此操作将同时删除该物品及其所有相关的交易记录，数据不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if db_manager.delete_Inventory_item(self.db_path, item_id):
                QMessageBox.information(self, "成功", "物品及关联交易记录已成功删除。")
                # self.load_Inventory_data()
                QTimer.singleShot(300, self.load_Inventory_data)
            else:
                QMessageBox.critical(self, "删除失败", "删除失败！请检查数据库连接或确认该物品ID是否存在。")
    load_inventory_data = load_Inventory_data

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 使用绝对路径测试 (根据您的实际路径调整)
    TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db', 'honsen_storage.db')
    
    if not os.path.exists(TEST_DB_PATH):
        # 如果 db 文件夹下没有，尝试根目录 (兼容旧版)
        TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'honsen_storage.db')
        if not os.path.exists(TEST_DB_PATH):
            print("警告：数据库文件不存在，请先通过 login.py 初始化。")
            # 创建一个空窗口防止崩溃
            window = InventoryPage("") 
            window.show()
            sys.exit(app.exec())

    window = InventoryPage(TEST_DB_PATH)
    window.show()
    sys.exit(app.exec())
    
