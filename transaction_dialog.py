# transaction_dialog.py
import sys
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QGridLayout, 
    QLabel, QLineEdit, QSpinBox, QMessageBox, 
    QComboBox, QApplication, QHBoxLayout, QPushButton
)
from PyQt6.QtCore import Qt
from typing import Dict, List, Union, Optional
from datetime import datetime

import db_manager 
from batch_transaction_dialog import BatchTransactionDialog 

class TransactionDialog(QDialog):
    
    def __init__(self, db_path: str, transaction_type: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.type = transaction_type # 'IN' 或 'OUT'
        self.setWindowTitle(f"{'入库 (IN)' if self.type == 'IN' else '出库 (OUT)'} 操作")
        
        # 初始加载数据
        self.all_inventory_items: List[Dict] = db_manager.get_all_inventory(self.db_path)
        self.filtered_items: List[Dict] = [] # 初始化为空，等待 _apply_filters 填充
        
        # 【新增】构建物品与柜号的关联映射 (用于搜索历史入库柜号)
        self.item_cabinet_map: Dict[str, List[str]] = db_manager.get_item_cabinet_map(self.db_path)
        
        self.init_ui()
        # 初始化时立即应用一次筛选，填充 filtered_items 和下拉框
        self._apply_filters() 

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- 批量操作按钮 ---
        batch_button_layout = QHBoxLayout()
        self.batch_button = QPushButton(f"批量{'入库' if self.type == 'IN' else '出库'}...")
        self.batch_button.clicked.connect(self._open_batch_dialog)
        batch_button_layout.addStretch(1)
        batch_button_layout.addWidget(self.batch_button)
        main_layout.addLayout(batch_button_layout)
        
        # --- 筛选区域 --- 
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("类别:"))
        self.category_filter = QComboBox()
        filter_layout.addWidget(self.category_filter)
        
        filter_layout.addWidget(QLabel("专业:"))
        self.domain_filter = QComboBox()
        filter_layout.addWidget(self.domain_filter)
        
        filter_layout.addWidget(QLabel("地点:"))
        self.location_filter = QComboBox()
        filter_layout.addWidget(self.location_filter)
        
        filter_layout.addWidget(QLabel("搜索:"))
        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("名称/型号/柜号/入库来源")
        filter_layout.addWidget(self.search_filter)
        filter_layout.addStretch(1)
        main_layout.addLayout(filter_layout)
        
        self._populate_filter_options()
        
        # 连接筛选信号
        self.category_filter.currentTextChanged.connect(self._apply_filters)
        self.domain_filter.currentTextChanged.connect(self._apply_filters)
        self.location_filter.currentTextChanged.connect(self._apply_filters)
        self.search_filter.textChanged.connect(self._apply_filters)
        
        # --- 物品选择区域 (单次交易) --- 
        form_layout = QGridLayout()
        
        # 第 0 行：选择物品
        form_layout.addWidget(QLabel("选择物品:"), 0, 0, Qt.AlignmentFlag.AlignLeft)
        self.item_combo = QComboBox()
        self.item_combo.setMinimumWidth(300)
        form_layout.addWidget(self.item_combo, 0, 1)

        # 第 1 行：数量
        form_layout.addWidget(QLabel("数量 (Quantity):"), 1, 0, Qt.AlignmentFlag.AlignLeft)
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 999999)
        self.quantity_spin.setValue(1)
        form_layout.addWidget(self.quantity_spin, 1, 1)

        # 第 2 行：来源/接收人
        label_text = "来源柜号:" if self.type == 'IN' else "接收人:"
        self.recipient_label = QLabel(label_text)
        self.recipient_entry = QLineEdit()
        self.recipient_entry.setPlaceholderText("请输入来源柜号" if self.type == 'IN' else "请输入接收人姓名")
        form_layout.addWidget(self.recipient_label, 2, 0, Qt.AlignmentFlag.AlignLeft)
        form_layout.addWidget(self.recipient_entry, 2, 1)
        
        # 第 3 行：项目 (仅出库显示)
        self.project_label = QLabel("项目 (Project Ref):")
        self.project_combo = QComboBox() 
        project_options = db_manager.get_config_options(self.db_path, 'PROJECT')
        if not project_options: project_options = ["", "项目A", "项目B"]
        self.project_combo.addItems(project_options)
        
        form_layout.addWidget(self.project_label, 3, 0, Qt.AlignmentFlag.AlignLeft)
        form_layout.addWidget(self.project_combo, 3, 1)
        
        if self.type == 'IN':
            self.project_label.setVisible(False)
            self.project_combo.setVisible(False)

        main_layout.addLayout(form_layout)
        
        # --- 按钮栏 --- 
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText(f"确认{'入库' if self.type == 'IN' else '出库'}")
        
        self.buttonBox.accepted.connect(self.accept_action)
        self.buttonBox.rejected.connect(self.reject)
        
        main_layout.addWidget(self.buttonBox)
        
        # _populate_item_combo 会在 _apply_filters 中调用，这里不需要再调

    def _open_batch_dialog(self):
        batch_dialog = BatchTransactionDialog(self.db_path, self.type, self)
        batch_dialog.inventory_changed.connect(self._refresh_inventory_data) 
        batch_dialog.exec()
        
    def _refresh_inventory_data(self):
        """刷新数据并关闭"""
        print("DEBUG: 刷新库存数据...")
        
        # 1. 重新拉取最新的库存数据
        self.all_inventory_items = db_manager.get_all_inventory(self.db_path)
        
        # 2. 重新构建柜号映射
        self.item_cabinet_map = db_manager.get_item_cabinet_map(self.db_path)
        
        # 3. 刷新筛选器选项
        self._populate_filter_options() 
        
        # 4. 重新应用筛选
        self._apply_filters() 
        
        QMessageBox.information(self, "库存刷新", "操作完成，主界面库存信息已刷新。", QMessageBox.StandardButton.Ok)
        super().accept()

    def _populate_filter_options(self):
        current_category = self.category_filter.currentText()
        current_domain = self.domain_filter.currentText() 
        current_location = self.location_filter.currentText()

        self.category_filter.clear()
        self.location_filter.clear()
        self.domain_filter.clear() 

        if not self.all_inventory_items:
            self.category_filter.addItem("无可用物品")
            self.location_filter.addItem("无可用物品")
            self.domain_filter.addItem("无可用专业") 
            return
        
        categories = set(item.get('category', '').strip() for item in self.all_inventory_items if item.get('category'))
        domains = set(item.get('domain', '').strip() for item in self.all_inventory_items if item.get('domain'))
        locations = set(item.get('location', '').strip() for item in self.all_inventory_items if item.get('location'))

        self.category_filter.addItem("全部类别")
        self.category_filter.addItems(sorted(list(categories)))
        if current_category and self.category_filter.findText(current_category) >= 0:
            self.category_filter.setCurrentText(current_category)
        
        self.domain_filter.addItem("全部专业")
        self.domain_filter.addItems(sorted(list(domains)))
        if current_domain and self.domain_filter.findText(current_domain) >= 0:
            self.domain_filter.setCurrentText(current_domain)
        
        self.location_filter.addItem("全部地点")
        self.location_filter.addItems(sorted(list(locations)))
        if current_location and self.location_filter.findText(current_location) >= 0:
            self.location_filter.setCurrentText(current_location)

    def _apply_filters(self):
        selected_category = self.category_filter.currentText()
        selected_location = self.location_filter.currentText()
        selected_domain = self.domain_filter.currentText()
        search_text = self.search_filter.text().strip().lower()
        
        self.filtered_items = []
        
        for item in self.all_inventory_items:
            # 基础筛选
            if selected_category not in ["全部类别", "无可用物品"] and item.get('category', '') != selected_category: continue
            if selected_domain not in ["全部专业", "无可用专业"] and item.get('domain', '') != selected_domain: continue
            if selected_location not in ["全部地点", "无可用物品"] and item.get('location', '') != selected_location: continue
            
            if search_text:
                item_name = item.get('name', '').lower()
                item_ref = item.get('reference', '').lower()
                
                # 1. 检查库存柜号 (inventory.cabinet)
                curr_cab = (item.get('cabinet', '') or '').lower()
                match_curr_cab = search_text in curr_cab
                
                # 2. 检查历史入库来源柜号 (transactions.recipient_source)
                associated_cabinets = self.item_cabinet_map.get(item_ref, [])
                match_hist_cab = False
                for cab in associated_cabinets:
                    if search_text in cab.lower():
                        match_hist_cab = True
                        break
                
                # 如果所有搜索条件都不匹配，则跳过
                if not (search_text in item_name or search_text in item_ref or match_curr_cab or match_hist_cab):
                    continue
            
            self.filtered_items.append(item)
        
        self._populate_item_combo()

    def _populate_item_combo(self):
        current_data = self.item_combo.currentData()
        self.item_combo.clear()
        
        if not self.filtered_items:
            self.item_combo.addItem("--- 无符合条件的物品 ---")
            self.item_combo.setEnabled(False)
            self.ok_button.setEnabled(False)
        else:
            self.item_combo.setEnabled(True)
            self.ok_button.setEnabled(True)
            
            new_index = -1
            for index, item in enumerate(self.filtered_items):
                display_text = (
                    f"[{item.get('reference', 'N/A')}] {item.get('name', 'N/A')} "
                    f"(库存: {item.get('current_stock', 0)}) - {item.get('location', 'N/A')}"
                )
                self.item_combo.addItem(display_text, userData=item['id'])
                if item['id'] == current_data:
                    new_index = index
                    
            if new_index >= 0:
                self.item_combo.setCurrentIndex(new_index)
            elif self.item_combo.count() > 0:
                self.item_combo.setCurrentIndex(0)

    def accept_action(self):
        # 1. 基础验证
        if not self.filtered_items or self.item_combo.currentIndex() < 0 or self.item_combo.currentData() is None:
            QMessageBox.critical(self, "错误", "请先在库存中添加物品或调整筛选条件。")
            return
        
        item_id = self.item_combo.currentData()
        
        # 2. 验证其他字段
        recipient_source = self.recipient_entry.text().strip()
        if not recipient_source:
            QMessageBox.warning(self, "输入错误", f"{'来源柜号' if self.type == 'IN' else '接收人'} 不能为空。")
            return
            
        quantity = self.quantity_spin.value()
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        project_ref = ""
        if self.type == 'OUT': 
            project_ref = self.project_combo.currentText()

        # 4. 记录交易
        success = db_manager.record_transaction(
            db_path=self.db_path, 
            item_id=item_id, 
            type=self.type, 
            quantity=quantity, 
            date=current_datetime,
            recipient_source=recipient_source, 
            project_ref=project_ref
        )
        
        if success:
            QMessageBox.information(self, "成功", f"成功记录 {self.type} 交易，库存已更新。")
            # 成功后，刷新数据并关闭
            self._refresh_inventory_data()
        else:
            QMessageBox.critical(self, "操作失败", "记录交易失败！可能是出库数量超过当前库存，或数据库发生其他错误。")
            return