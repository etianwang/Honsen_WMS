import sys
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QGridLayout, 
    QLabel, QLineEdit, QSpinBox, QMessageBox, 
    QComboBox, QApplication
)
from PyQt6.QtCore import Qt
from typing import Dict, List
import db_manager 
from datetime import datetime

class TransactionDialog(QDialog):
    """
    处理物品入库 (IN) 或出库 (OUT) 的通用对话框。
    """
    def __init__(self, db_path: str, transaction_type: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.type = transaction_type # 'IN' 或 'OUT'
        self.setWindowTitle(f"{'入库 (IN)' if self.type == 'IN' else '出库 (OUT)'} 操作")
        
        # 存储所有库存物品数据，用于下拉框映射
        self.inventory_items: List[Dict] = db_manager.get_all_inventory(self.db_path)
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QGridLayout()
        
        # --- 1. 定义输入字段 ---
        
        # A. 物品选择 (ComboBox)
        form_layout.addWidget(QLabel("选择物品:"), 0, 0, Qt.AlignmentFlag.AlignLeft)
        self.item_combo = QComboBox()
        self.item_combo.setMinimumWidth(200)
        
        if not self.inventory_items:
            self.item_combo.addItem("--- 无可用库存物品，请先添加 ---")
            self.item_combo.setEnabled(False)
        else:
            for item in self.inventory_items:
                # 显示格式: [编号] 名称 (当前库存: X)
                display_text = f"[{item['reference']}] {item['name']} (库存: {item['current_stock']})"
                self.item_combo.addItem(display_text, userData=item['id'])
        
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
        
        # D. 项目参考 (QComboBox) - 更改为下拉选择框
        self.project_label = QLabel("项目 (Project Ref):")
        # 更改: 使用 QComboBox 
        self.project_combo = QComboBox() 
        project_options = ["别墅", "办公楼", "基地", "其他"]
        self.project_combo.addItems(project_options)
        
        form_layout.addWidget(self.project_label, 3, 0, Qt.AlignmentFlag.AlignLeft)
        # 更改: 使用 self.project_combo
        form_layout.addWidget(self.project_combo, 3, 1)

        main_layout.addLayout(form_layout)
        
        # --- 2. 按钮栏 ---
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText(f"确认{'入库' if self.type == 'IN' else '出库'}")
        # 连接信号
        self.buttonBox.accepted.connect(self.accept_action)
        self.buttonBox.rejected.connect(self.reject)
        
        main_layout.addWidget(self.buttonBox)
        
        # 初始检查：如果库存为空，则禁用 OK 按钮
        if not self.inventory_items:
            self.ok_button.setEnabled(False)


    def accept_action(self):
        """当用户点击 OK 按钮时执行的操作：记录交易。"""
        
        # 1. 验证基础输入
        if not self.inventory_items or self.item_combo.currentIndex() < 0:
            QMessageBox.critical(self, "错误", "请先在库存中添加物品。")
            return
            
        recipient_source = self.recipient_entry.text().strip()
        if not recipient_source:
            QMessageBox.warning(self, "输入错误", f"{'来源' if self.type == 'IN' else '接收人'} 不能为空。")
            return
            
        quantity = self.quantity_spin.value()
        item_id = self.item_combo.currentData()
        
        # 2. 获取当前日期时间
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 3. 调用数据库管理器进行事务记录 (包含原子性更新库存)
        success = db_manager.record_transaction(
            db_path=self.db_path,
            item_id=item_id,
            type=self.type,
            quantity=quantity,
            date=current_datetime,
            recipient_source=recipient_source,
            # 更改: 从 QComboBox 中使用 currentText() 获取选定的项目值
            project_ref=self.project_combo.currentText()
        )
        
        if success:
            QMessageBox.information(self, "成功", f"成功记录 {self.type} 交易，库存已更新。")
            super().accept() 
        else:
            # 失败通常是由于出库时库存不足
            QMessageBox.critical(self, "操作失败", "记录交易失败！可能是出库数量超过当前库存，或数据库发生其他错误。")
            return

# --- 暂时不需要运行 ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 假设数据库文件已存在
    # db_manager.initialize_database('honsen_storage.db') # 需要 db_manager.py
    dialog = TransactionDialog('honsen_storage.db', 'OUT')
    dialog.exec()
    sys.exit(0)
