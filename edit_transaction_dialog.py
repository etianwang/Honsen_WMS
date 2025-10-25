# edit_transaction_dialog.py
import sys
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QGridLayout, 
    QLabel, QLineEdit, QSpinBox, QMessageBox, 
    QComboBox, QApplication, QDateTimeEdit
)
from PyQt6.QtCore import Qt, QDateTime
from typing import Dict
import db_manager 
from datetime import datetime

class EditTransactionDialog(QDialog):
    """
    修改交易记录的对话框
    用于修改已存在的交易记录（不包括冲销记录）
    """
    def __init__(self, db_path: str, tx_id: int, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.tx_id = tx_id
        self.setWindowTitle(f"修改交易记录 (ID: {tx_id})")
        
        # 获取原始交易记录
        self.original_transaction = db_manager.get_transaction_by_id(self.db_path, tx_id)
        
        if not self.original_transaction:
            QMessageBox.critical(self, "错误", f"无法找到 ID 为 {tx_id} 的交易记录。")
            self.reject()
            return
        
        # 存储原始数量用于计算库存变化
        self.original_quantity = self.original_transaction['quantity']
        self.original_type = self.original_transaction['type']
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # 显示物品信息（只读）
        info_layout = QGridLayout()
        
        # 显示物品名称（不可修改）
        info_layout.addWidget(QLabel("物品名称:"), 0, 0, Qt.AlignmentFlag.AlignLeft)
        self.item_name_label = QLabel(self.original_transaction['item_name'])
        self.item_name_label.setStyleSheet("font-weight: bold; color: #333;")
        info_layout.addWidget(self.item_name_label, 0, 1)
        
        # 显示物品型号（不可修改）
        info_layout.addWidget(QLabel("物品型号:"), 1, 0, Qt.AlignmentFlag.AlignLeft)
        self.item_ref_label = QLabel(self.original_transaction['item_ref'])
        self.item_ref_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.item_ref_label, 1, 1)
        
        # 显示交易类型（不可修改）
        info_layout.addWidget(QLabel("交易类型:"), 2, 0, Qt.AlignmentFlag.AlignLeft)
        tx_type_text = "入库 (IN)" if self.original_type == 'IN' else "出库 (OUT)"
        self.type_label = QLabel(tx_type_text)
        self.type_label.setStyleSheet("font-weight: bold; color: " + 
                                      ("#4CAF50" if self.original_type == 'IN' else "#f44336") + ";")
        info_layout.addWidget(self.type_label, 2, 1)
        
        main_layout.addLayout(info_layout)
        
        # 分隔线
        separator = QLabel()
        separator.setStyleSheet("border-bottom: 2px solid #ccc; margin: 10px 0;")
        main_layout.addWidget(separator)
        
        # 可修改字段
        form_layout = QGridLayout()
        
        # A. 日期时间（可修改）
        form_layout.addWidget(QLabel("日期时间:"), 0, 0, Qt.AlignmentFlag.AlignLeft)
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        
        # 解析原始日期时间
        try:
            original_dt = QDateTime.fromString(self.original_transaction['date'], 'yyyy-MM-dd HH:mm:ss')
            if original_dt.isValid():
                self.datetime_edit.setDateTime(original_dt)
            else:
                self.datetime_edit.setDateTime(QDateTime.currentDateTime())
        except:
            self.datetime_edit.setDateTime(QDateTime.currentDateTime())
        
        form_layout.addWidget(self.datetime_edit, 0, 1)
        
        # B. 数量（可修改）
        form_layout.addWidget(QLabel("数量:"), 1, 0, Qt.AlignmentFlag.AlignLeft)
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 999999)
        self.quantity_spin.setValue(self.original_quantity)
        form_layout.addWidget(self.quantity_spin, 1, 1)
        
        # C. 接收人/来源（可修改）
        label_text = "来源/柜号:" if self.original_type == 'IN' else "接收人:"
        form_layout.addWidget(QLabel(label_text), 2, 0, Qt.AlignmentFlag.AlignLeft)
        self.recipient_entry = QLineEdit()
        self.recipient_entry.setText(self.original_transaction['recipient_source'])
        self.recipient_entry.setPlaceholderText("请输入采购地/柜号/员工姓名...")
        form_layout.addWidget(self.recipient_entry, 2, 1)
        
        # D. 项目参考（仅出库时显示，可修改）
        self.project_label = QLabel("项目:")
        self.project_combo = QComboBox()
        
        # 动态从数据库加载项目选项
        project_options = db_manager.get_config_options(self.db_path, 'PROJECT')
        
        if not project_options:
            project_options = ["", "别墅", "办公楼", "基地", "其他"]
        
        self.project_combo.addItems(project_options)
        
        # 设置当前项目值
        current_project = self.original_transaction.get('project_ref', '')
        idx = self.project_combo.findText(current_project)
        if idx >= 0:
            self.project_combo.setCurrentIndex(idx)
        
        form_layout.addWidget(self.project_label, 3, 0, Qt.AlignmentFlag.AlignLeft)
        form_layout.addWidget(self.project_combo, 3, 1)
        
        # 根据交易类型控制"项目"输入框的可见性
        if self.original_type == 'IN':
            self.project_label.setVisible(False)
            self.project_combo.setVisible(False)
        
        main_layout.addLayout(form_layout)
        
        # 警告提示
        warning_label = QLabel("⚠️ 注意：修改记录将自动调整库存！")
        warning_label.setStyleSheet("color: #ff9800; font-weight: bold; padding: 10px; border: 1px solid #ff9800; border-radius: 5px; background-color: #fff3e0;")
        main_layout.addWidget(warning_label)
        
        # 按钮栏
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("确认修改")
        
        cancel_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setText("取消")
        
        self.buttonBox.accepted.connect(self.accept_action)
        self.buttonBox.rejected.connect(self.reject)
        
        main_layout.addWidget(self.buttonBox)

    def accept_action(self):
        """当用户点击确认按钮时执行的操作：更新交易记录"""
        
        # 1. 验证输入
        recipient_source = self.recipient_entry.text().strip()
        if not recipient_source:
            QMessageBox.warning(self, "输入错误", 
                              f"{'来源' if self.original_type == 'IN' else '接收人'} 不能为空。")
            return
        
        new_quantity = self.quantity_spin.value()
        new_date = self.datetime_edit.dateTime().toString('yyyy-MM-dd HH:mm:ss')
        
        # 2. 确定 project_ref 的值
        project_ref = ""
        if self.original_type == 'OUT':
            project_ref = self.project_combo.currentText()
        
        # 3. 检查是否有任何修改
        if (new_quantity == self.original_quantity and
            new_date == self.original_transaction['date'] and
            recipient_source == self.original_transaction['recipient_source'] and
            project_ref == self.original_transaction.get('project_ref', '')):
            QMessageBox.information(self, "提示", "没有任何修改。")
            return
        
        # 4. 确认修改
        if new_quantity != self.original_quantity:
            quantity_diff = new_quantity - self.original_quantity
            if self.original_type == 'IN':
                stock_change_msg = f"库存将{'增加' if quantity_diff > 0 else '减少'} {abs(quantity_diff)} 单位"
            else:  # OUT
                stock_change_msg = f"库存将{'减少' if quantity_diff > 0 else '增加'} {abs(quantity_diff)} 单位"
            
            reply = QMessageBox.question(
                self, 
                "确认修改", 
                f"您将要修改此交易记录：\n\n"
                f"数量: {self.original_quantity} → {new_quantity}\n"
                f"{stock_change_msg}\n\n"
                f"确定要继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # 5. 调用数据库管理器更新交易
        success = db_manager.update_transaction(
            db_path=self.db_path,
            tx_id=self.tx_id,
            quantity=new_quantity,
            date=new_date,
            recipient_source=recipient_source,
            project_ref=project_ref
        )
        
        if success:
            super().accept()
        else:
            QMessageBox.critical(self, "修改失败", 
                               "修改交易失败！可能是库存不足，或数据库发生错误。")


# --- 测试代码 ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 假设数据库文件已存在，并且有交易记录
    # db_manager.initialize_database('honsen_storage.db')
    # 测试修改 ID 为 1 的交易记录
    dialog = EditTransactionDialog('honsen_storage.db', 1)
    dialog.exec()
    sys.exit(0)