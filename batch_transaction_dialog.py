# batch_transaction_dialog.py
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, 
    QPushButton, QSpinBox, QDialogButtonBox, QMessageBox, QApplication,
    QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal 
from typing import Optional, List, Dict, Union
from datetime import datetime
# 确保导入 db_manager 并正确引用 DB_NAME
import db_manager 

# =================================================================
# 辅助类：ItemReferenceCombo 和 ProjectCombo (保持不变)
# =================================================================
class ItemReferenceCombo(QComboBox):
    def __init__(self, item_map: Dict[str, Dict], parent=None):
        super().__init__(parent)
        self.item_map = item_map
        self.addItems(["--- 选择物品型号 ---"] + sorted(item_map.keys()))
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setCompleter(None) 
        
class ProjectCombo(QComboBox):
    def __init__(self, project_options: List[str], parent=None):
        super().__init__(parent)
        self.addItems(project_options)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setCompleter(None)


# 批量交易对话框类
class BatchTransactionDialog(QDialog):
    inventory_changed = pyqtSignal() 
    
    def __init__(self, db_path: str, transaction_type: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.type = transaction_type # 'IN' 或 'OUT'
        self.setWindowTitle(f"批量{'入库 (IN)' if self.type == 'IN' else '出库 (OUT)'} 操作")
        
        self.setMinimumWidth(1100) # 增大宽度以容纳更多字段
        self.locked_rows: Dict[int, str] = {} 
        
        # 使用 db_manager.get_all_inventory 获取数据
        self.all_inventory_items: List[Dict] = db_manager.get_all_inventory(self.db_path)
        self.inventory_map: Dict[str, Dict] = {item.get('reference', ''): dict(item) for item in self.all_inventory_items}
        
        # 2. 【新增】构建物品与柜号的关联映射 (调用 db_manager 新函数)
        # 数据结构: { "REF-001": ["柜号A", "柜号B"], ... }
        self.item_cabinet_map: Dict[str, List[str]] = db_manager.get_item_cabinet_map(self.db_path)

        # 从 db_manager 获取配置项
        self.project_options = db_manager.get_config_options(self.db_path, 'PROJECT')
        self.domain_options = db_manager.get_config_options(self.db_path, 'DOMAIN')

        if not self.project_options: self.project_options = ["", "项目A", "项目B"]
        if "" not in self.project_options and self.type == 'OUT': self.project_options.insert(0, "")
        if not self.domain_options: self.domain_options = ["电气", "水暖", "通用"]
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 1. 筛选/操作栏
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("专业筛选:"))
        self.domain_filter = QComboBox()
        filter_layout.addWidget(self.domain_filter)
        filter_layout.addWidget(QLabel("类别筛选:"))
        self.category_filter = QComboBox()
        filter_layout.addWidget(self.category_filter)
        filter_layout.addWidget(QLabel("地点筛选:"))
        self.location_filter = QComboBox()
        filter_layout.addWidget(self.location_filter)
        filter_layout.addWidget(QLabel("搜索:"))
        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("型号/名称/柜号")
        filter_layout.addWidget(self.search_filter)
        filter_layout.addStretch(1)

        main_layout.addLayout(filter_layout)

        # 2. 交易表格
        self.transaction_table = QTableWidget()
        headers = ["锁定", "物品型号 (Reference)", "数量 (Qty)", "物品名称/库存", "项目 (Project Ref)", "操作状态/错误"]
        self.transaction_table.setColumnCount(len(headers))
        self.transaction_table.setHorizontalHeaderLabels(headers)
        self.transaction_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.transaction_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.transaction_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.transaction_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        main_layout.addWidget(self.transaction_table)

        # 3. 底部控制栏
        control_layout = QHBoxLayout()
        self.add_row_button = QPushButton("✚ 添加行")
        self.remove_row_button = QPushButton("━ 删除行")
        self.recipient_label = QLabel("接收人/来源:")
        self.recipient_entry = QLineEdit()
        self.recipient_entry.setPlaceholderText("柜号/采购方/员工姓名...")
        self.recipient_entry.textChanged.connect(self._check_overall_validity)

        control_layout.addWidget(self.add_row_button)
        control_layout.addWidget(self.remove_row_button)
        control_layout.addSpacing(20)
        control_layout.addWidget(self.recipient_label)
        control_layout.addWidget(self.recipient_entry)

        main_layout.addLayout(control_layout)

        # 4. 确认/取消按钮
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText(f"确认批量{'入库' if self.type == 'IN' else '出库'}")
        self.ok_button.setEnabled(False) 
        
        # 【连接执行函数】
        self.buttonBox.accepted.connect(self.accept_action)
        self.buttonBox.rejected.connect(self.reject)
        
        main_layout.addWidget(self.buttonBox)

        # 连接筛选信号
        self.domain_filter.currentTextChanged.connect(self._apply_filters)
        self.category_filter.currentTextChanged.connect(self._apply_filters)
        self.location_filter.currentTextChanged.connect(self._apply_filters)
        self.search_filter.textChanged.connect(self._apply_filters)
        self.add_row_button.clicked.connect(self._add_row)
        self.remove_row_button.clicked.connect(self._remove_selected_row)
        
        self._populate_filter_options()
        self._add_row() # 默认添加一行

    def _populate_filter_options(self):
        # ... (筛选器填充逻辑，使用 self.all_inventory_items)
        self.category_filter.clear()
        self.location_filter.clear()
        self.domain_filter.clear() 
        if not self.all_inventory_items:
             self.category_filter.addItem("无可用物品")
             self.location_filter.addItem("无可用物品")
             self.domain_filter.addItem("无可用物品")
             return
        categories = sorted(list(set(item.get('category', '').strip() for item in self.all_inventory_items if item.get('category'))))
        locations = sorted(list(set(item.get('location', '').strip() for item in self.all_inventory_items if item.get('location'))))
        domains = sorted(list(set(item.get('domain', '').strip() for item in self.all_inventory_items if item.get('domain'))))

        self.category_filter.addItem("全部类别")
        self.category_filter.addItems(categories)
        self.location_filter.addItem("全部地点")
        self.location_filter.addItems(locations)
        self.domain_filter.addItem("全部专业")
        self.domain_filter.addItems(domains) 

    def _apply_filters(self):
        # ... (筛选逻辑，更新 self.filtered_inventory_items)
        selected_category = self.category_filter.currentText()
        selected_location = self.location_filter.currentText()
        selected_domain = self.domain_filter.currentText() 
        search_text = self.search_filter.text().strip().lower()
        self.filtered_inventory_items = []
        for item in self.all_inventory_items:
            if selected_category not in ["全部类别", "无可用物品"] and item.get('category', '') != selected_category: continue
            if selected_location not in ["全部地点", "无可用物品"] and item.get('location', '') != selected_location: continue
            if selected_domain not in ["全部专业", "无可用物品"] and item.get('domain', '') != selected_domain: continue
            if search_text:
                item_name = item.get('name', '').lower()
                item_ref = item.get('reference', '').lower()


                # 【新增】检查柜号匹配
                # 从映射表中获取该物品关联的所有柜号列表
                associated_cabinets = self.item_cabinet_map.get(item_ref, [])
                cabinet_match = False
                for cab in associated_cabinets:
                    if search_text in cab.lower():
                        cabinet_match = True
                        break
                # 如果 名称不匹配 AND 型号不匹配 AND 柜号也不匹配 -> 跳过
                if (search_text not in item_name) and \
                   (search_text not in item_ref) and \
                   (not cabinet_match):
                    continue
            
            self.filtered_inventory_items.append(item)
            
        self._refresh_table_combos()

    def _refresh_table_combos(self):
        """【修复点 2：修复锁定逻辑】刷新表格中的 ItemReferenceCombo 逻辑"""
        
        # 1. 准备筛选后的型号列表
        filtered_references = ["--- 选择物品型号 ---"] + sorted(
            item.get('reference', '') for item in self.filtered_inventory_items if item.get('reference')
        )
        filtered_map = {item.get('reference', ''): dict(item) for item in self.filtered_inventory_items if item.get('reference')}
        
        for r in range(self.transaction_table.rowCount()):
            item_combo: ItemReferenceCombo = self.transaction_table.cellWidget(r, 1) 
            if not item_combo: continue
            
            # 记录当前选定的型号
            current_ref = item_combo.currentText()
            
            # **对于未锁定的行，使用筛选结果**
            if r not in self.locked_rows:
                # 重新填充 Combo，使用筛选后的结果
                item_combo.clear()
                item_combo.item_map = filtered_map # 未锁定行只关心筛选后的数据
                item_combo.addItems(filtered_references)
                
                # 尝试恢复之前的选择，如果不在筛选结果中，则自动选择第一个项
                if current_ref in filtered_references:
                    item_combo.setCurrentText(current_ref)
                else:
                    item_combo.setCurrentIndex(0) 
            
            # **对于锁定的行，确保它保留锁定的值**
            else:
                # 锁定的型号
                locked_ref = self.locked_rows[r]
                
                # 必须确保 item_combo 的列表包含所有型号（否则锁定型号可能无法被显示）
                # 为了保持简单，我们仅在锁定时确保显示的型号是正确的。
                if item_combo.findText(locked_ref) == -1:
                    # 如果锁定型号不在列表中（例如，因为 Combo 只包含筛选后的结果），则需要临时添加它
                    item_combo.addItem(locked_ref)
                
                item_combo.setCurrentText(locked_ref)
                
                # 重要的：锁定时应使用全部库存数据进行校验
                item_combo.item_map = self.inventory_map 

            self._validate_row(r)
        self._check_overall_validity()
        
    def _toggle_lock(self, row: int, button: QPushButton):
        # ... (锁定逻辑，确保行号正确调整)
        item_combo: ItemReferenceCombo = self.transaction_table.cellWidget(row, 1) 
        if not item_combo: return
        
        # 锁定状态
        if row not in self.locked_rows:
            ref = item_combo.currentText()
            if ref == "--- 选择物品型号 ---" or ref not in self.inventory_map:
                QMessageBox.warning(self, "锁定失败", "请先选择一个有效的型号才能锁定此行。")
                return
            self.locked_rows[row] = ref
            item_combo.setEnabled(False)
            button.setText("🔓") 
            button.setToolTip("点击解锁，允许筛选影响")
            # 锁定后，确保 combo box 列表回到全部列表，这样解锁后可以立即看到
            self._refresh_table_combos()
        # 解锁状态
        else:
            del self.locked_rows[row]
            item_combo.setEnabled(True)
            button.setText("🔒") 
            button.setToolTip("点击锁定，禁止筛选影响")
            # 解锁后立即刷新，以应用当前的筛选结果
            self._refresh_table_combos() 
        self._validate_row(row)

    def _add_row(self):
        # ... (添加行逻辑，确保索引正确)
        row_count = self.transaction_table.rowCount()
        self.transaction_table.insertRow(row_count)
        
        lock_button = QPushButton("🔒")
        lock_button.setFixedSize(24, 24)
        lock_button.setToolTip("点击锁定，禁止筛选影响")
        # 使用 lambda 函数连接，确保 r=row_count 捕获正确的行号
        lock_button.clicked.connect(lambda checked, r=row_count, btn=lock_button: self._toggle_lock(r, btn)) 
        self.transaction_table.setCellWidget(row_count, 0, lock_button)
        
        # 物品型号 - 初始添加时使用筛选后的列表
        current_filtered_map = {item.get('reference', ''): dict(item) for item in self.filtered_inventory_items if item.get('reference')}
        item_combo = ItemReferenceCombo(current_filtered_map) 
        item_combo.currentIndexChanged.connect(lambda index, r=row_count: self._validate_row(r))
        self.transaction_table.setCellWidget(row_count, 1, item_combo)

        # 数量
        quantity_spin = QSpinBox()
        quantity_spin.setRange(1, 999999)
        quantity_spin.setValue(1)
        quantity_spin.valueChanged.connect(lambda value, r=row_count: self._validate_row(r))
        self.transaction_table.setCellWidget(row_count, 2, quantity_spin)

        # 物品名称/库存 (用于显示)
        name_item = QTableWidgetItem("---")
        name_item.setFlags(Qt.ItemFlag.ItemIsEnabled) 
        self.transaction_table.setItem(row_count, 3, name_item)

        # 项目 (仅出库需要)
        if self.type == 'OUT':
            project_widget = ProjectCombo(self.project_options)
            project_widget.currentIndexChanged.connect(lambda index, r=row_count: self._validate_row(r))
        else:
            project_widget = QLineEdit()
            project_widget.setDisabled(True)
            project_widget.setText("N/A")
            
        self.transaction_table.setCellWidget(row_count, 4, project_widget)

        # 状态 (隐藏列，用于存储校验结果)
        status_item = QTableWidgetItem()
        status_item.setFlags(Qt.ItemFlag.NoItemFlags) 
        self.transaction_table.setItem(row_count, 5, status_item) 
        
        self._validate_row(row_count)

    def _remove_selected_row(self):
        # ... (删除行逻辑，确保锁定字典更新)
        current_row = self.transaction_table.currentRow()
        if current_row >= 0:
            if current_row in self.locked_rows: del self.locked_rows[current_row] 
            self.transaction_table.removeRow(current_row)
            self._check_overall_validity() 
            # 重新映射锁定的行号
            new_locked_rows = {}
            for r, ref in self.locked_rows.items():
                if r > current_row: new_locked_rows[r - 1] = ref
                elif r < current_row: new_locked_rows[r] = ref
            self.locked_rows = new_locked_rows

    def _validate_row(self, row: int):
        # ... (校验逻辑)
        item_combo: ItemReferenceCombo = self.transaction_table.cellWidget(row, 1) 
        quantity_spin: QSpinBox = self.transaction_table.cellWidget(row, 2) 
        project_widget: QWidget = self.transaction_table.cellWidget(row, 4) 
        name_item: QTableWidgetItem = self.transaction_table.item(row, 3) 
        status_item: QTableWidgetItem = self.transaction_table.item(row, 5) 

        if not item_combo or not quantity_spin or not name_item or not project_widget or not status_item: return

        ref = item_combo.currentText().strip()
        qty = quantity_spin.value()
        is_valid = True
        error_msg = ""
        
        if ref == "--- 选择物品型号 ---" or not ref:
            error_msg = "请选择型号"
            is_valid = False
            # 对于空选择，显示名称应重置
            name_item.setText("---")
            name_item.setForeground(Qt.GlobalColor.red)
        else:
            # 校验时始终使用完整的 inventory_map
            item_data = self.inventory_map.get(ref) 
            if not item_data:
                error_msg = "型号不存在" 
                is_valid = False
            else:
                current_stock = item_data.get('current_stock', 0)
                display_text = f"{item_data['name']} (库存: {current_stock})"
                name_item.setText(display_text)
                
                if qty <= 0:
                    error_msg = "数量须大于0"
                    is_valid = False
                    
                if self.type == 'OUT' and is_valid:
                    if qty > current_stock:
                        error_msg = f"库存不足 ({current_stock})"
                        is_valid = False
                    
                    project_combo: ProjectCombo = project_widget
                    project_ref = project_combo.currentText().strip()
                    if not project_ref: 
                        error_msg = "请选择或填写项目"
                        is_valid = False
        
        if is_valid:
            name_item.setForeground(Qt.GlobalColor.black)
            status_item.setData(Qt.ItemDataRole.UserRole, True) 
            status_item.setText("✅")
        else:
            if ref != "--- 选择物品型号 ---" and ref: # 只有当用户选择了型号，但是型号无效时，才显示具体错误
                 name_item.setText(f"错误: {error_msg}")
            # 如果是空选择，上方的 '---' 已经设置了，这里跳过
            name_item.setForeground(Qt.GlobalColor.red)
            status_item.setData(Qt.ItemDataRole.UserRole, False) 
            status_item.setText("❌")
        
        self._check_overall_validity()

    def _check_overall_validity(self):
        # ... (检查整体有效性，确保所有行都校验通过)
        row_count = self.transaction_table.rowCount()
        recipient_source = self.recipient_entry.text().strip()
        if not recipient_source or row_count == 0:
            self.ok_button.setEnabled(False)
            return
            
        all_rows_valid = True
        for r in range(row_count):
            # 获取状态项，检查用户数据是否为 True
            status_item = self.transaction_table.item(r, 5) 
            # 确保 status_item 存在且数据为 True
            if status_item is None or status_item.data(Qt.ItemDataRole.UserRole) is None or not status_item.data(Qt.ItemDataRole.UserRole):
                all_rows_valid = False
                break
                
        self.ok_button.setEnabled(all_rows_valid)


    def accept_action(self):
        # ... (批量交易执行逻辑，保持不变)
        if not self.ok_button.isEnabled():
            QMessageBox.critical(self, "错误", "数据校验未通过，请检查列表中的红色错误项并填写来源/接收人。")
            return
            
        recipient_source = self.recipient_entry.text().strip()
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        row_count = self.transaction_table.rowCount()

        successful_count = 0
        failed_transactions = []
        
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor) 
        
        try:
            # 在事务开始前，重新拉取最新的库存信息，以防两个批量对话框同时操作
            current_inventory = db_manager.get_all_inventory(self.db_path)
            self.inventory_map = {item.get('reference', ''): dict(item) for item in current_inventory}

            for r in range(row_count):
                status_item_check = self.transaction_table.item(r, 5) 
                if status_item_check is None or not status_item_check.data(Qt.ItemDataRole.UserRole):
                    failed_transactions.append(f"行 {r+1}: 预校验失败，跳过。")
                    continue 

                try:
                    item_combo: ItemReferenceCombo = self.transaction_table.cellWidget(r, 1) 
                    quantity_spin: QSpinBox = self.transaction_table.cellWidget(r, 2) 
                    project_widget: QWidget = self.transaction_table.cellWidget(r, 4) 
                    
                    ref = item_combo.currentText()
                    qty = quantity_spin.value()
                    
                    project_ref = ""
                    if self.type == 'OUT':
                        project_combo: ProjectCombo = project_widget
                        project_ref = project_combo.currentText().strip()
                    
                    item = self.inventory_map.get(ref)
                    if not item: 
                        failed_transactions.append(f"行 {r+1} ({ref}): 型号不存在或查询失败。")
                        continue
                        
                    item_id = item['id']
                    
                    success = db_manager.record_transaction(
                        db_path=self.db_path, item_id=item_id, type=self.type, quantity=qty, date=current_datetime,
                        recipient_source=recipient_source, project_ref=project_ref
                    )
                    
                    status_item: QTableWidgetItem = self.transaction_table.item(r, 5)
                    
                    if success:
                        successful_count += 1
                        status_item.setText("✅ 成功")
                        status_item.setBackground(Qt.GlobalColor.green)
                        
                        # 仅更新 UI 内存中的库存，不影响 DB
                        item['current_stock'] = item.get('current_stock', 0) + (qty if self.type=='IN' else -qty)
                        
                    else:
                        failed_transactions.append(f"行 {r+1} ({ref}): 数据库更新失败 (可能库存不足)。")
                        status_item.setText("❌ 失败: 库存或DB错误")
                        status_item.setBackground(Qt.GlobalColor.yellow)

                except Exception as e:
                    failed_transactions.append(f"行 {r+1} ({ref}): 发生未知错误 - {e}")
                    status_item: QTableWidgetItem = self.transaction_table.item(r, 5)
                    status_item.setText("❌ 失败: 未知错误")
                    status_item.setBackground(Qt.GlobalColor.red)
        finally:
            QApplication.restoreOverrideCursor() 

        total_transactions = row_count
        
        if successful_count > 0:
            self.inventory_changed.emit() # 成功后发出信号
            
        if successful_count == total_transactions and total_transactions > 0:
            QMessageBox.information(self, "成功", f"成功记录 {successful_count} 笔批量交易。")
            super().accept()
        elif successful_count > 0:
            error_msg = (f"完成，但有部分错误！\n\n"
                         f"成功: {successful_count} 笔，失败: {len(failed_transactions)} 笔。\n\n"
                         f"详细错误:\n" + '\n'.join(failed_transactions))
            QMessageBox.warning(self, "部分成功", error_msg)
            super().accept() 
        else:
             error_msg = ("操作失败！所有交易均未成功记录。\n\n"
                          f"详细错误:\n" + '\n'.join(failed_transactions))
             QMessageBox.critical(self, "批量操作失败", error_msg)
             super().reject()