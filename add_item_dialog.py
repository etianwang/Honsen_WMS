# add_item_dialog.py
import sys
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QGridLayout, 
    QLabel, QLineEdit, QSpinBox, QMessageBox, QApplication, QComboBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt

# 导入数据库管理器
import db_manager 

class AddItemDialog(QDialog):
    """
    新增库存物品的对话框。
    """
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增库存物品")
        self.db_path = db_path
        
        self.init_ui()

    def _get_location_options(self):
        """从数据库获取动态的存放位置列表 (LOCATION)"""
        locations = db_manager.get_config_options(self.db_path, 'LOCATION')
        if not locations:
            return ["其他"]
        return locations

    def _get_category_options(self):
        """从数据库获取动态的材料类别列表 (CATEGORY)"""
        categories = db_manager.get_config_options(self.db_path, 'CATEGORY')
        if not categories:
            return ["其他"]
        return categories

    def _get_domain_options(self):
        """从数据库获取动态的专业类别列表 (DOMAIN)"""
        domains = db_manager.get_config_options(self.db_path, 'DOMAIN')
        if not domains:
            return ["其他"]
        return domains

    def _get_unit_options(self):
        """从数据库获取动态的计量单位列表 (UNIT)"""
        units = db_manager.get_config_options(self.db_path, 'UNIT')
        if not units:
            return ["个"]
        return units

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QGridLayout()
        
        # --- 1. 定义输入字段 ---
        
        # 字段配置: (标签文本, 键名, 输入类型, 选项/默认值)
        fields = [
            ("物品名称 (Name):", 'name', 'text', ""),
            ("物品型号 (Ref):", 'reference', 'text', ""),
            ("材料类别 (Category):", 'category', 'combo', self._get_category_options()),
            ("专业类别 (Domain):", 'domain', 'combo', self._get_domain_options()),  # 新增
            ("计量单位 (Unit):", 'unit', 'combo', self._get_unit_options()),
            ("初始库存 (Stock):", 'current_stock', 'spin', 0),
            ("最小库存 (Min Stock):", 'min_stock', 'spin', 5),
            ("存放位置 (Location):", 'location', 'combo', self._get_location_options())
        ]

        self.entries = {}
        row = 0
        
        for label_text, key, input_type, default_val in fields:
            label = QLabel(label_text)
            
            if input_type == 'text':
                entry = QLineEdit()
                entry.setText(default_val)
                if key in ['name', 'reference']:
                    entry.textChanged.connect(self.validate_inputs)
                    
            elif input_type == 'spin':
                entry = QSpinBox()
                entry.setRange(0, 999999)
                entry.setValue(default_val)
                
            elif input_type == 'combo':
                entry = QComboBox()
                entry.addItems(default_val)
            
            else:
                entry = QLineEdit()
            
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


    def validate_inputs(self):
        """检查必填字段是否已填写，并启用/禁用 OK 按钮"""
        name_ok = bool(self.entries['name'].text().strip())
        ref_ok = bool(self.entries['reference'].text().strip())
        
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(name_ok and ref_ok)
    
    
    def accept_action(self):
        """当用户点击 OK 按钮时执行的操作：插入数据到数据库。"""
        
        # 从控件中收集数据 
        data = {}
        for key, entry in self.entries.items():
            if isinstance(entry, QLineEdit):
                data[key] = entry.text()
            elif isinstance(entry, QComboBox):
                data[key] = entry.currentText()
            elif isinstance(entry, QSpinBox):
                data[key] = entry.value()
        
        # 必填字段检查
        if not data.get('name', '').strip() or not data.get('reference', '').strip():
            QMessageBox.warning(self, "输入错误", "物品名称和物品编号是必填项！")
            return
            
        # 调用数据库管理器进行插入操作
        try:
            new_id = db_manager.insert_inventory_item(
                db_path=self.db_path,
                name=data['name'].strip(),
                reference=data['reference'].strip(),
                category=data['category'].strip(),
                domain=data['domain'].strip(),  # 新增
                unit=data['unit'].strip(),
                current_stock=data['current_stock'], 
                min_stock=data['min_stock'], 
                location=data['location'].strip()
            )
            
            if new_id is not None:
                QMessageBox.information(self, "成功", f"物品 '{data['name']}' (ID: {new_id}) 添加成功！")
                super().accept()
            else:
                QMessageBox.critical(self, "操作失败", f"添加物品失败！物品名称或型号 '{data['reference']}' 可能已存在。")
                return
        
        except TypeError as e:
            QMessageBox.critical(self, "数据库管理器错误", 
                                 f"添加物品失败！错误：{e}\n请确保 db_manager.py 中的 insert_inventory_item 函数已更新以接受 'domain' 参数。")
        except Exception as e:
            QMessageBox.critical(self, "操作失败", f"添加物品失败！发生未知错误：{e}")
            return
            
if __name__ == '__main__':
    app = QApplication(sys.argv)
    print("请确保 db_manager.py 存在且已更新以支持 domain 字段后再运行。")
    sys.exit(0)