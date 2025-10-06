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

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QGridLayout()
        
        # --- 1. 定义输入字段 ---
        
        # 字段配置: (标签文本, 键名, 输入类型, 选项/默认值)
        # 'combo' 类型现在使用第四个元素作为选项列表
        fields = [
            ("物品名称 (Name):", 'name', 'text', ""),
            ("物品型号 (Ref):", 'reference', 'text', ""),
            # 修改为下拉选择框，选项为 "个" / "套" / "对"
            ("计量单位 (Unit):", 'unit', 'combo', ["个", "套", "对", "包", "箱", "其他"]),
            ("初始库存 (Stock):", 'current_stock', 'spin', 0),
            ("最小库存 (Min Stock):", 'min_stock', 'spin', 5),
            # 修改为下拉选择框，选项为 "基地仓库" / "大仓库"
            ("存放位置 (Location):", 'location', 'combo', ["基地仓库", "大仓库", "别墅", "办公楼", "公寓", "其他"])
        ]

        self.entries = {}
        row = 0
        
        for label_text, key, input_type, default_val in fields:
            label = QLabel(label_text)
            
            if input_type == 'text':
                entry = QLineEdit()
                entry.setText(default_val)
                # 名称和编号不能为空，进行简单校验
                if key in ['name', 'reference']:
                    entry.textChanged.connect(self.validate_inputs)
                    
            elif input_type == 'spin':
                entry = QSpinBox()
                entry.setRange(0, 999999) # 设定范围
                entry.setValue(default_val)
                
            elif input_type == 'combo':
                # 新增 QComboBox 逻辑
                entry = QComboBox()
                entry.addItems(default_val) # default_val 现在是选项列表
            
            else:
                # 默认处理
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
        # 连接信号
        self.buttonBox.accepted.connect(self.accept_action)
        self.buttonBox.rejected.connect(self.reject)
        
        main_layout.addWidget(self.buttonBox)
        
        # 初始时检查一次输入状态
        self.validate_inputs()


    def validate_inputs(self):
        """检查必填字段是否已填写，并启用/禁用 OK 按钮"""
        name_ok = bool(self.entries['name'].text().strip())
        ref_ok = bool(self.entries['reference'].text().strip())
        
        # 只有当名称和编号都非空时，才启用 OK 按钮
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(name_ok and ref_ok)
        
    
    def accept_action(self):
        """当用户点击 OK 按钮时执行的操作：插入数据到数据库。"""
        
        # 从控件中收集数据 (FIXED: 使用 if/elif 结构区分 QComboBox, QLineEdit 和 QSpinBox)
        data = {}
        for key, entry in self.entries.items():
            if isinstance(entry, QLineEdit):
                data[key] = entry.text()
            elif isinstance(entry, QComboBox):
                # 修复点：QComboBox 使用 currentText()
                data[key] = entry.currentText()
            elif isinstance(entry, QSpinBox):
                # QSpinBox 使用 value()
                data[key] = entry.value()
            # 注意：此处没有 else 分支来处理其他可能的控件类型，如果未来增加，需要在这里扩展。
        
        # 必填字段检查（虽然在 validate_inputs 中做了，这里再次确认）
        if not data.get('name', '').strip() or not data.get('reference', '').strip():
            QMessageBox.warning(self, "输入错误", "物品名称和物品编号是必填项！")
            return
            
        # 调用数据库管理器进行插入操作
        # 确保所有字符串数据都被 strip()
        new_id = db_manager.insert_inventory_item(
            db_path=self.db_path,
            name=data['name'].strip(),
            reference=data['reference'].strip(),
            unit=data['unit'].strip(),
            current_stock=data['current_stock'], # QSpinBox 的 value 是 int
            min_stock=data['min_stock'], # QSpinBox 的 value 是 int
            location=data['location'].strip()
        )
        
        if new_id is not None:
            QMessageBox.information(self, "成功", f"物品 '{data['name']}' (ID: {new_id}) 添加成功！")
            super().accept() # 关闭对话框并返回 QDialog.Accepted 结果
        else:
            # 失败通常是由于 reference 编号重复
            QMessageBox.critical(self, "操作失败", f"添加物品失败！物品型号 '{data['reference']}' 可能已存在。")
            # 不关闭对话框，让用户修正输入
            return
            
# --- 暂时不需要运行 ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 假设数据库文件已存在并初始化
    db_manager.initialize_database('honsen_storage.db')
    dialog = AddItemDialog('honsen_storage.db')
    dialog.exec()
    sys.exit(0)
