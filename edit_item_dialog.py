import sys
from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QGridLayout, 
    QLabel, QLineEdit, QSpinBox, QMessageBox, QApplication, 
    QComboBox, QWidget
)
from PyQt6.QtCore import Qt

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
        self.load_data() # 加载数据到所有控件

    def load_config_options(self, category: str) -> List[str]:
        """从数据库获取指定类别的配置选项列表"""
        try:
            # 假设 db_manager 中存在 get_config_options(db_path, category) 方法
            options = db_manager.get_config_options(self.db_path, category)
            # 确保返回的是列表，即使数据库返回空
            return options if isinstance(options, list) else []
        except AttributeError:
            # 如果 db_manager 缺少此方法，则使用默认值并提示
            QMessageBox.critical(self, "数据库配置错误", f"db_manager 缺少 'get_config_options' 方法。请检查 db_manager.py。", QMessageBox.StandardButton.Ok)
            # 返回一个基本的默认列表
            if category == 'UNIT':
                return ["个", "套", "对", "箱"]
            elif category == 'LOCATION':
                return ["基地仓库", "大仓库", "其他"]
            elif category == 'CATEGORY': # 新增 CATEGORY 的默认值
                return ["电子元件", "机械零件", "工具", "耗材", "其他"]
            return []
        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"无法加载 {category} 选项: {e}", QMessageBox.StandardButton.Ok)
            return []

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QGridLayout()
        
        # --- 1. 定义输入字段 ---
        
        # 字段配置: (标签文本, 键名, 输入类型)
        fields = [
            ("物品名称 (Name):", 'name', 'text'),
            ("物品型号 (Ref):", 'reference', 'text'),
            # **** 新增材料类别 (Category) 下拉框 ****
            ("材料类别 (Category):", 'category', 'combo_category'), 
            ("计量单位 (Unit):", 'unit', 'combo_unit'), 
            ("最小库存 (Min Stock):", 'min_stock', 'spin'),
            ("存放位置 (Location):", 'location', 'combo_location') 
        ]

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
            
            # --- QComboBox 逻辑 ---
            elif input_type == 'combo_category':
                entry = QComboBox()
                # 动态加载材料类别选项
                category_options = self.load_config_options('CATEGORY')
                entry.addItems(category_options)
            elif input_type == 'combo_unit':
                entry = QComboBox()
                # 动态加载计量单位选项
                unit_options = self.load_config_options('UNIT')
                entry.addItems(unit_options)
            elif input_type == 'combo_location':
                entry = QComboBox()
                # 动态加载存放位置选项
                location_options = self.load_config_options('LOCATION')
                entry.addItems(location_options)
            
            
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
                # QSpinBox 期望 int 或可以转换为 int 的值
                try:
                    entry.setValue(int(value))
                except (ValueError, TypeError):
                    entry.setValue(0)
            elif isinstance(entry, QComboBox):
                # 对于 QComboBox，找到匹配的文本并设置当前选中项
                index = entry.findText(str(value))
                if index != -1:
                    entry.setCurrentIndex(index)
                else:
                    entry.setCurrentText(str(value))


    def validate_inputs(self):
        """检查必填字段是否已填写，并启用/禁用 OK 按钮"""
        # 只有 name 和 reference 字段是 QLineEdit 且必填
        name_ok = bool(self.entries['name'].text().strip())
        ref_ok = bool(self.entries['reference'].text().strip())
        
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(name_ok and ref_ok)
        
        
    def accept_action(self):
        """当用户点击 OK 按钮时执行的操作：更新数据库。"""
        
        # 收集数据
        data: Dict[str, Any] = {}
        for key, entry in self.entries.items():
            if isinstance(entry, QLineEdit):
                data[key] = entry.text().strip()
            elif isinstance(entry, QSpinBox):
                data[key] = entry.value()
            elif isinstance(entry, QComboBox):
                # 从 QComboBox 获取当前选中的文本
                data[key] = entry.currentText()
        
        # 调用数据库管理器进行更新操作 (注意：假定 update_inventory_item 已更新以接受 category)
        try:
            success = db_manager.update_inventory_item(
                db_path=self.db_path,
                item_id=self.item_id,
                name=data['name'],
                reference=data['reference'],
                # **** 传递新增的 category 字段 ****
                category=data['category'],
                unit=data['unit'],
                min_stock=data['min_stock'],
                location=data['location']
            )
        except TypeError as e:
            QMessageBox.critical(self, "数据库管理器错误", 
                                 f"更新物品失败！错误：{e}\n请确保 db_manager.py 中的 update_inventory_item 函数已更新以接受 'category' 参数。")
            return
        
        if success:
            QMessageBox.information(self, "成功", f"物品 '{data['name']}' (ID: {self.item_id}) 更新成功！")
            super().accept() # 关闭对话框
        else:
            # 失败通常是由于 reference 编号重复或 ID 不存在
            QMessageBox.critical(self, "操作失败", f"更新物品失败！物品编号 '{data['reference']}' 可能已存在或未修改任何数据。")
            return
            
# --- 测试代码 ---
if __name__ == '__main__':
    # 为了运行测试，这里提供一个简化的 db_manager 存根，包含 get_config_options
    class MockDBManager:
        _options: Dict[str, List[str]] = {
            "UNIT": ["个", "套", "对", "箱", "卷", "米"],
            "LOCATION": ["基地仓库", "大仓库", "别墅", "办公楼", "公寓", "其他"],
            "CATEGORY": ["电子元件", "机械零件", "工具", "耗材", "其他"] # 增加 CATEGORY 模拟数据
        }
        
        @staticmethod
        def get_config_options(db_path, category):
            print(f"--- Mock DB: Getting options for {category} from {db_path} ---")
            return MockDBManager._options.get(category, [])
            
        @staticmethod
        def update_inventory_item(*args, **kwargs):
            print("--- Mock DB Update Called ---")
            # 打印所有更新的参数
            print(f"ID: {kwargs.get('item_id')}, Name: {kwargs.get('name')}, Category: {kwargs.get('category')}, Unit: {kwargs.get('unit')}, Location: {kwargs.get('location')}")
            return True
            
    db_manager = MockDBManager()

    app = QApplication(sys.argv)
    test_data = {
        'id': 101,
        'name': 'LED灯管',
        'reference': 'TL-LED-18W',
        'category': '电子元件', # 增加 category 字段，以便加载时能选中
        'unit': '套', 
        'current_stock': 55,
        'min_stock': 10,
        'location': '别墅'
    }

    dialog = EditItemDialog('test_storage.db', test_data)
    dialog.exec()
    sys.exit(0)
