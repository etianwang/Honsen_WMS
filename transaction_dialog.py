# transaction_dialog.py
import sys
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QGridLayout, 
    QLabel, QLineEdit, QSpinBox, QMessageBox, 
    QComboBox, QApplication, QHBoxLayout
)
from PyQt6.QtCore import Qt
from typing import Dict, List
import db_manager 
from datetime import datetime

class TransactionDialog(QDialog):
    """
    处理物品入库 (IN) 或出库 (OUT) 的通用对话框。
    增加了类别和地点筛选功能，方便快速找到物品。
    """
    def __init__(self, db_path: str, transaction_type: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.type = transaction_type # 'IN' 或 'OUT'
        self.setWindowTitle(f"{'入库 (IN)' if self.type == 'IN' else '出库 (OUT)'} 操作")
        
        # 存储所有库存物品数据
        self.all_inventory_items: List[Dict] = db_manager.get_all_inventory(self.db_path)
        # 存储当前筛选后的物品数据
        self.filtered_items: List[Dict] = self.all_inventory_items.copy()
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- 新增：筛选区域 ---
        filter_layout = QHBoxLayout()
        
        # 类别筛选
        filter_layout.addWidget(QLabel("类别筛选:"))
        self.category_filter = QComboBox()
        self.category_filter.setMinimumWidth(120)
        filter_layout.addWidget(self.category_filter)
        
        # 地点筛选
        filter_layout.addWidget(QLabel("地点筛选:"))
        self.location_filter = QComboBox()
        self.location_filter.setMinimumWidth(120)
        filter_layout.addWidget(self.location_filter)
        
        # 搜索框
        filter_layout.addWidget(QLabel("搜索:"))
        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("物品名称或型号")
        self.search_filter.setMinimumWidth(150)
        filter_layout.addWidget(self.search_filter)
        
        filter_layout.addStretch(1)
        
        main_layout.addLayout(filter_layout)
        
        # 初始化筛选选项
        self._populate_filter_options()
        
        # 连接筛选信号
        self.category_filter.currentTextChanged.connect(self._apply_filters)
        self.location_filter.currentTextChanged.connect(self._apply_filters)
        self.search_filter.textChanged.connect(self._apply_filters)
        
        # --- 物品选择区域 ---
        form_layout = QGridLayout()
        
        # A. 物品选择 (ComboBox)
        form_layout.addWidget(QLabel("选择物品:"), 0, 0, Qt.AlignmentFlag.AlignLeft)
        self.item_combo = QComboBox()
        self.item_combo.setMinimumWidth(300)
        
        form_layout.addWidget(self.item_combo, 0, 1)

        # B. 数量输入 (SpinBox)
        form_layout.addWidget(QLabel("数量 (Quantity):"), 1, 0, Qt.AlignmentFlag.AlignLeft)
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 999999)
        self.quantity_spin.setValue(1)
        form_layout.addWidget(self.quantity_spin, 1, 1)

        # C. 接收人/来源 (LineEdit)
        label_text = "来源/柜号 (Source):" if self.type == 'IN' else "接收人 (Recipient):"
        self.recipient_label = QLabel(label_text)
        self.recipient_entry = QLineEdit()
        self.recipient_entry.setPlaceholderText("请输入采购地/柜号/员工姓名...")
        form_layout.addWidget(self.recipient_label, 2, 0, Qt.AlignmentFlag.AlignLeft)
        form_layout.addWidget(self.recipient_entry, 2, 1)
        
        # D. 项目参考 (QComboBox) - 仅出库时显示 (OUT)
        self.project_label = QLabel("项目 (Project Ref):")
        self.project_combo = QComboBox() 
        
        # 动态从数据库加载项目选项
        project_options = db_manager.get_config_options(self.db_path, 'PROJECT')
        
        if not project_options:
            project_options = ["", "别墅", "办公楼", "基地", "其他"]
            
        self.project_combo.addItems(project_options)
        
        form_layout.addWidget(self.project_label, 3, 0, Qt.AlignmentFlag.AlignLeft)
        form_layout.addWidget(self.project_combo, 3, 1)
        
        # 根据交易类型控制"项目"输入框的可见性
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
        
        # 初始加载物品列表
        self._populate_item_combo()

    def _populate_filter_options(self):
        """填充筛选下拉框的选项"""
        if not self.all_inventory_items:
            self.category_filter.addItem("无可用物品")
            self.location_filter.addItem("无可用物品")
            self.category_filter.setEnabled(False)
            self.location_filter.setEnabled(False)
            return
        
        # 提取唯一的类别
        categories = set()
        for item in self.all_inventory_items:
            category = item.get('category', '').strip()
            if category:
                categories.add(category)
        
        # 提取唯一的地点
        locations = set()
        for item in self.all_inventory_items:
            location = item.get('location', '').strip()
            if location:
                locations.add(location)
        
        # 填充类别筛选
        self.category_filter.addItem("全部类别")
        self.category_filter.addItems(sorted(list(categories)))
        
        # 填充地点筛选
        self.location_filter.addItem("全部地点")
        self.location_filter.addItems(sorted(list(locations)))

    def _apply_filters(self):
        """应用筛选条件并更新物品下拉框"""
        selected_category = self.category_filter.currentText()
        selected_location = self.location_filter.currentText()
        search_text = self.search_filter.text().strip().lower()
        
        # 筛选物品
        self.filtered_items = []
        for item in self.all_inventory_items:
            # 类别筛选
            if selected_category != "全部类别" and selected_category != "无可用物品":
                if item.get('category', '') != selected_category:
                    continue
            
            # 地点筛选
            if selected_location != "全部地点" and selected_location != "无可用物品":
                if item.get('location', '') != selected_location:
                    continue
            
            # 搜索筛选
            if search_text:
                item_name = item.get('name', '').lower()
                item_ref = item.get('reference', '').lower()
                if search_text not in item_name and search_text not in item_ref:
                    continue
            
            self.filtered_items.append(item)
        
        # 更新物品下拉框
        self._populate_item_combo()

    def _populate_item_combo(self):
        """填充物品下拉框（基于筛选结果）"""
        self.item_combo.clear()
        
        if not self.filtered_items:
            self.item_combo.addItem("--- 无符合条件的物品 ---")
            self.item_combo.setEnabled(False)
            self.ok_button.setEnabled(False)
        else:
            self.item_combo.setEnabled(True)
            self.ok_button.setEnabled(True)
            
            for item in self.filtered_items:
                # 显示格式: [编号] 名称 (当前库存: X) - 地点
                display_text = (
                    f"[{item['reference']}] {item['name']} "
                    f"(库存: {item['current_stock']}) - {item['location']}"
                )
                self.item_combo.addItem(display_text, userData=item['id'])

    def accept_action(self):
        """当用户点击 OK 按钮时执行的操作：记录交易。"""
        
        # 1. 验证基础输入
        if not self.filtered_items or self.item_combo.currentIndex() < 0:
            QMessageBox.critical(self, "错误", "请先在库存中添加物品或调整筛选条件。")
            return
            
        recipient_source = self.recipient_entry.text().strip()
        if not recipient_source:
            QMessageBox.warning(self, "输入错误", f"{'来源' if self.type == 'IN' else '接收人'} 不能为空。")
            return
            
        quantity = self.quantity_spin.value()
        item_id = self.item_combo.currentData()
        
        # 2. 获取当前日期时间
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 3. 确定 project_ref 的值
        project_ref = ""
        if self.type == 'OUT':
             project_ref = self.project_combo.currentText()

        # 4. 调用数据库管理器进行事务记录
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
            super().accept() 
        else:
            QMessageBox.critical(self, "操作失败", "记录交易失败！可能是出库数量超过当前库存，或数据库发生其他错误。")
            return

# --- 测试代码 ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 假设数据库文件已存在
    # db_manager.initialize_database('honsen_storage.db')
    dialog = TransactionDialog('honsen_storage.db', 'OUT')
    dialog.exec()
    sys.exit(0)