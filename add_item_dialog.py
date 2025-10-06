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
        # 如果数据库中无任何记录，确保有一个默认的 '其他' 选项
        if not locations:
            return ["其他"]
        return locations

    def _get_category_options(self):
        """从数据库获取动态的材料类别列表 (CATEGORY)"""
        categories = db_manager.get_config_options(self.db_path, 'CATEGORY')
        # 如果数据库中无任何记录，确保有一个默认的 '其他' 选项
        if not categories:
            return ["其他"]
        return categories

    def _get_unit_options(self):
        """从数据库获取动态的计量单位列表 (UNIT)"""
        units = db_manager.get_config_options(self.db_path, 'UNIT')
        # 如果数据库中无任何记录，确保有一个默认的 '个' 选项
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
            # **** 新增材料类别 (CATEGORY) 下拉框 ****
            ("材料类别 (Category):", 'category', 'combo', self._get_category_options()), 
            # 计量单位改为动态获取
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
                entry.addItems(default_val) # default_val 现在是动态获取的选项列表
            
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
        
        # 从控件中收集数据 
        data = {}
        for key, entry in self.entries.items():
            if isinstance(entry, QLineEdit):
                data[key] = entry.text()
            elif isinstance(entry, QComboBox):
                # QComboBox 使用 currentText()
                data[key] = entry.currentText()
            elif isinstance(entry, QSpinBox):
                # QSpinBox 使用 value()
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
                # **** 新增 category 字段传递 ****
                category=data['category'].strip(), 
                unit=data['unit'].strip(),
                current_stock=data['current_stock'], 
                min_stock=data['min_stock'], 
                location=data['location'].strip()
                # 警告：此函数调用假设 db_manager.py 和 Inventory 表已更新以包含 'category' 字段。
            )
            
            if new_id is not None:
                QMessageBox.information(self, "成功", f"物品 '{data['name']}' (ID: {new_id}) 添加成功！")
                super().accept() # 关闭对话框并返回 QDialog.Accepted 结果
            else:
                # 失败通常是由于 reference 编号或 name 名称重复 (db_manager 内部处理)
                QMessageBox.critical(self, "操作失败", f"添加物品失败！物品名称或型号 '{data['reference']}' 可能已存在。")
                # 不关闭对话框，让用户修正输入
                return
        
        except TypeError as e:
            # 捕获因 db_manager.py 中 insert_inventory_item 缺少 'category' 参数导致的错误
            QMessageBox.critical(self, "数据库管理器错误", 
                                 f"添加物品失败！错误：{e}\n请确保 db_manager.py 中的 insert_inventory_item 函数已更新以接受 'category' 参数。")
        except Exception as e:
            QMessageBox.critical(self, "操作失败", f"添加物品失败！发生未知错误：{e}")
            return
            
# --- 暂时不需要运行 ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 假设数据库文件已存在并初始化
    # 注意：运行此 demo 需要 db_manager.py 及其中的函数
    # db_manager.initialize_database('honsen_storage.db')
    # dialog = AddItemDialog('honsen_storage.db')
    # dialog.exec()
    # sys.exit(0)
    # 由于缺少 db_manager.py，为避免运行时错误，暂时注释 demo 代码。
    print("请确保 db_manager.py 存在且已更新以支持 category 字段后再运行。")
    sys.exit(0)
