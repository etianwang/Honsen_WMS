# edit_item_dialog.py
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
            elif category == 'CATEGORY': 
                return ["电子元件", "机械零件", "工具", "耗材", "其他"]
            elif category == 'DOMAIN': # 新增 DOMAIN 的默认值
                return ["电气", "暖通", "水务", "通用"]
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
            ("材料类别 (Category):", 'category', 'combo_category'), 
            # **** 新增专业 (Domain) 下拉框 ****
            ("专业 (Domain):", 'domain', 'combo_domain'), 
            ("计量单位 (Unit):", 'unit', 'combo_unit'), 
            ("当前柜号 (Cabinet):", 'cabinet', 'text'), # 【新增】当前柜号输入框
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
                entry.setEditable(True)  # 【新增】允许手动输入
                category_options = self.load_config_options('CATEGORY')
                entry.addItems(category_options)
            elif input_type == 'combo_domain':
                entry = QComboBox()
                # 动态加载专业选项 (新增逻辑)
                entry.setEditable(True)  # 【新增】允许手动输入
                domain_options = self.load_config_options('DOMAIN')
                entry.addItems(domain_options)
            elif input_type == 'combo_unit':
                entry = QComboBox()
                # 动态加载计量单位选项
                entry.setEditable(True)  # 【新增】允许手动输入
                unit_options = self.load_config_options('UNIT')
                entry.addItems(unit_options)
            elif input_type == 'combo_location':
                entry = QComboBox()
                # 动态加载存放位置选项
                entry.setEditable(True)  # 【新增】允许手动输入
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
                    
                    # entry.setCurrentText(str(value))

                    # 如果原值不在列表中，尝试设置为该文本（可能在后面添加）
                    # 注意：QComboBox 没有 setCurrentText 方法在所有版本都可用，
                    # 但 addItem 可以动态添加。这里为了简单，如果找不到就设为空或第一个。
                    # 更稳健的做法是确保 config 表里有这个值，或者允许用户手动输入后自动加入 config。
                    # 这里暂时保持原逻辑，如果找不到就不选中，用户需手动选择或输入（如果是可编辑的 ComboBox）。
                    # 对于标准 QComboBox，如果值不在列表里，它不会显示该值。
                    # 如果需要显示不在列表里的值，可以考虑使用 QComboBox.setEditable(True)
                    pass 
                    # 如果希望允许输入不在列表中的值，可以在 init_ui 中设置 entry.setEditable(True)


    def validate_inputs(self):
        """检查必填字段是否已填写，并启用/禁用 OK 按钮"""
        # 只有 name 和 reference 字段是 QLineEdit 且必填
        name_ok = bool(self.entries['name'].text().strip())
        ref_ok = bool(self.entries['reference'].text().strip())
        
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(name_ok and ref_ok)
        
        
    def accept_action(self):
        """当用户点击 OK 按钮时执行的操作：更新数据库。"""
        print("💾 [EditDialog] 开始保存操作...")
        
        # 1. 收集数据
        data: Dict[str, Any] = {}
        for key, entry in self.entries.items():
            if isinstance(entry, QLineEdit):
                data[key] = entry.text().strip()
            elif isinstance(entry, QSpinBox):
                data[key] = entry.value()
            elif isinstance(entry, QComboBox):
                data[key] = entry.currentText().strip()
        
        # 简单校验
        if not data.get('name') or not data.get('reference'):
            QMessageBox.warning(self, "输入错误", "名称和型号不能为空！")
            return

        # 2. 【新增】自动将新选项写入 Config 表 (防止因配置表缺失导致后续问题)
        config_mapping = {
            'category': 'CATEGORY',
            'domain': 'DOMAIN',
            'unit': 'UNIT',
            'location': 'LOCATION'
        }
        try:
            for field_key, config_cat in config_mapping.items():
                val = data.get(field_key, '')
                if val:
                    # 忽略插入失败的错误 (如已存在)
                    db_manager.insert_config_option(self.db_path, config_cat, val)
        except Exception as e:
            print(f"⚠️ [EditDialog] 更新配置表警告 (可忽略): {e}")

        # 3. 调用数据库管理器进行更新
        try:
            print(f"🔄 [EditDialog] 正在调用 update_Inventory_item (ID: {self.item_id})...")
            
            success = db_manager.update_Inventory_item(
                db_path=self.db_path,
                item_id=self.item_id,
                name=data['name'],
                reference=data['reference'],
                category=data['category'],
                domain=data['domain'],
                unit=data['unit'],
                min_stock=data['min_stock'],
                location=data['location'],
                cabinet=data['cabinet']
            )
            
            print(f"✅ [EditDialog] 数据库返回结果: {success}")

            if success:
                QMessageBox.information(self, "成功", f"物品 '{data['name']}' 更新成功！")
                
                # 【关键修复】强制关闭对话框
                # 使用 self.done() 比 super().accept() 更可靠，确保模态窗口彻底销毁
                print("🚪 [EditDialog] 正在强制关闭对话框...")
                self.done(QDialog.DialogCode.Accepted) 
                return
            else:
                # 更新失败 (通常是 Reference 重复)
                QMessageBox.critical(self, "操作失败", f"更新物品失败！\n可能原因：物品编号 '{data['reference']}' 已被其他物品使用。")
                # 不要关闭对话框，让用户修改
                
        except TypeError as te:
            print(f"❌ [EditDialog] 参数类型错误: {te}")
            QMessageBox.critical(self, "代码错误", f"数据库函数参数不匹配！\n请检查 db_manager.py 的 update_Inventory_item 定义。\n详情：{te}")
            # 不关闭对话框
        except Exception as e:
            print(f"❌ [EditDialog] 发生未知异常: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "系统错误", f"保存时发生未知错误：\n{e}")
            # 不关闭对话框            
# --- 测试代码 ---
# if __name__ == '__main__':
#     # 为了运行测试，这里提供一个简化的 db_manager 存根，包含 get_config_options
#     class MockDBManager:
#         _options: Dict[str, List[str]] = {
#             "UNIT": ["个", "套", "对", "箱", "卷", "米"],
#             "LOCATION": ["基地仓库", "大仓库", "别墅", "办公楼", "公寓", "其他"],
#             "CATEGORY": ["电子元件", "机械零件", "工具", "耗材", "其他"], 
#             "DOMAIN": ["电气", "暖通", "水务", "通用"] # 增加 DOMAIN 模拟数据
#         }
        
#         @staticmethod
#         def get_config_options(db_path, category):
#             print(f"--- Mock DB: Getting options for {category} from {db_path} ---")
#             return MockDBManager._options.get(category, [])
            
#         @staticmethod
#         def update_Inventory_item(*args, **kwargs):
#             print("--- Mock DB Update Called ---")
#             # 打印所有更新的参数 (已包含 domain)
#             print(f"ID: {kwargs.get('item_id')}, Name: {kwargs.get('name')}, Category: {kwargs.get('category')}, Domain: {kwargs.get('domain')}, Unit: {kwargs.get('unit')}, Location: {kwargs.get('location')}, Cabinet: {kwargs.get('cabinet')}")
#             return True
            
#     db_manager = MockDBManager()

#     app = QApplication(sys.argv)
#     test_data = {
#         'id': 101,
#         'name': 'LED灯管',
#         'reference': 'TL-LED-18W',
#         'category': '电子元件', 
#         'domain': '电气', # 增加 domain 字段，以便加载时能选中
#         'unit': '套', 
#         'cabinet': 'A-01', # 测试数据包含柜号
#         'current_stock': 55,
#         'min_stock': 10,
#         'location': '别墅'
#     }

#     dialog = EditItemDialog('test_storage.db', test_data)
#     dialog.exec()
#     sys.exit(0)