import sys
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QGridLayout, 
    QLabel, QLineEdit, QSpinBox, QMessageBox, QApplication, QComboBox # 导入 QComboBox
)
from PyQt6.QtCore import Qt
from typing import Dict

# 导入数据库管理器
import db_manager 

class EditItemDialog(QDialog):
    """
    编辑现有库存物品的对话框。
    """
    def __init__(self, db_path: str, item_data: Dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"编辑物品：{item_data.get('name', 'N/A')}")
        self.db_path = db_path
        self.item_id = item_data['id']
        self.original_data = item_data
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QGridLayout()
        
        # --- 1. 定义输入字段 ---
        
        # 字段配置: (标签文本, 键名, 输入类型)
        # 'combo_unit' 和 'combo_location' 表示使用 QComboBox
        fields = [
            ("物品名称 (Name):", 'name', 'text'),
            ("物品型号 (Ref):", 'reference', 'text'),
            # 更改为下拉选择框
            ("计量单位 (Unit):", 'unit', 'combo_unit'), 
            ("最小库存 (Min Stock):", 'min_stock', 'spin'),
            # 更改为下拉选择框
            ("存放位置 (Location):", 'location', 'combo_location') 
        ]
        # 注意：current_stock 不在此处修改，它通过交易记录来更新

        self.entries = {}
        row = 0
        
        # 显示 ID 和当前库存作为参考，但不允许编辑
        form_layout.addWidget(QLabel("ID:"), row, 0, Qt.AlignmentFlag.AlignLeft)
        form_layout.addWidget(QLabel(str(self.item_id)), row, 1)
        row += 1
        
        form_layout.addWidget(QLabel("当前库存:"), row, 0, Qt.AlignmentFlag.AlignLeft)
        form_layout.addWidget(QLabel(str(self.original_data.get('current_stock', 0))), row, 1)
        row += 1
        
        
        for label_text, key, input_type in fields:
            label = QLabel(label_text)
            
            if input_type == 'text':
                entry = QLineEdit()
                # 名称和编号必填，连接校验函数
                if key in ['name', 'reference']:
                    entry.textChanged.connect(self.validate_inputs) 
            elif input_type == 'spin':
                entry = QSpinBox()
                entry.setRange(0, 999999) 
            elif input_type == 'combo_unit':
                # 计量单位下拉框
                entry = QComboBox()
                entry.addItems(["个", "套", "对"])
            elif input_type == 'combo_location':
                # 存放位置下拉框
                entry = QComboBox()
                entry.addItems(["基地仓库", "大仓库", "别墅", "办公楼", "公寓", "其他"])

            
            self.entries[key] = entry
            
            form_layout.addWidget(label, row, 0, Qt.AlignmentFlag.AlignLeft)
            form_layout.addWidget(entry, row, 1)
            row += 1

        main_layout.addLayout(form_layout)
        
        # --- 2. 按钮栏 ---
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox.accepted.connect(self.accept_action)
        self.buttonBox.rejected.connect(self.reject)
        
        main_layout.addWidget(self.buttonBox)
        
        self.validate_inputs()

    def load_data(self):
        """将原始数据填充到输入框"""
        for key, entry in self.entries.items():
            value = self.original_data.get(key, '')
            if isinstance(entry, QLineEdit):
                entry.setText(str(value))
            elif isinstance(entry, QSpinBox):
                entry.setValue(int(value))
            elif isinstance(entry, QComboBox):
                # 对于 QComboBox，找到匹配的文本并设置当前选中项
                index = entry.findText(str(value))
                if index != -1:
                    entry.setCurrentIndex(index)

    def validate_inputs(self):
        """检查必填字段是否已填写，并启用/禁用 OK 按钮"""
        # 只有 name 和 reference 字段是 QLineEdit 且必填
        name_ok = bool(self.entries['name'].text().strip())
        ref_ok = bool(self.entries['reference'].text().strip())
        
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(name_ok and ref_ok)
        
    
    def accept_action(self):
        """当用户点击 OK 按钮时执行的操作：更新数据库。"""
        
        # 收集数据
        data = {}
        for key, entry in self.entries.items():
            if isinstance(entry, QLineEdit):
                data[key] = entry.text().strip()
            elif isinstance(entry, QSpinBox):
                data[key] = entry.value()
            elif isinstance(entry, QComboBox):
                # 从 QComboBox 获取当前选中的文本
                data[key] = entry.currentText()
        
        # 调用数据库管理器进行更新操作
        success = db_manager.update_inventory_item(
            db_path=self.db_path,
            item_id=self.item_id,
            name=data['name'],
            reference=data['reference'],
            unit=data['unit'], # 使用 QComboBox 的值
            min_stock=data['min_stock'],
            location=data['location'] # 使用 QComboBox 的值
        )
        
        if success:
            QMessageBox.information(self, "成功", f"物品 '{data['name']}' (ID: {self.item_id}) 更新成功！")
            super().accept() # 关闭对话框
        else:
            # 失败通常是由于 reference 编号重复或 ID 不存在
            QMessageBox.critical(self, "操作失败", f"更新物品失败！物品编号 '{data['reference']}' 可能已存在或未修改任何数据。")
            return
            
# --- 测试代码 ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    test_data = {
        'id': 101,
        'name': 'LED灯管',
        'reference': 'TL-LED-18W',
        # 示例数据现在应该能被正确匹配到下拉框选项中
        'unit': '个', 
        'current_stock': 55,
        'min_stock': 10,
        'location': '大仓库'
    }
    # 假设 db_manager 存在，否则测试代码会失败
    # 为了运行测试，这里提供一个简化的 db_manager 存根
    class MockDBManager:
        @staticmethod
        def update_inventory_item(*args, **kwargs):
            print("--- Mock DB Update Called ---")
            print(f"ID: {kwargs['item_id']}, Name: {kwargs['name']}, Unit: {kwargs['unit']}, Location: {kwargs['location']}")
            return True
            
    db_manager = MockDBManager()

    dialog = EditItemDialog('honsen_storage.db', test_data)
    dialog.exec()
    sys.exit(0)
