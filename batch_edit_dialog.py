"""
batch_edit_dialog.py
批量编辑库存物品对话框
支持同时修改多个物品的类别、单位、最小库存和存放位置
"""

import sys
from typing import List, Dict
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QGridLayout, 
    QLabel, QSpinBox, QMessageBox, QApplication, 
    QComboBox, QCheckBox, QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt

import db_manager


class BatchEditDialog(QDialog):
    """
    批量编辑多个库存物品的对话框。
    只编辑选中要修改的字段，未选中的字段保持原值不变。
    """
    def __init__(self, db_path: str, selected_items: List[Dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"批量编辑 - 已选中 {len(selected_items)} 个物品")
        self.setMinimumWidth(500)
        self.db_path = db_path
        self.selected_items = selected_items  # 包含所有选中物品的完整信息
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # 显示选中的物品列表
        items_group = QGroupBox("选中的物品")
        items_layout = QVBoxLayout()
        
        # 使用滚动区域以防物品过多
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(150)
        
        scroll_content = QLabel()
        items_text = "\n".join([
            f"• [{item['reference']}] {item['name']}" 
            for item in self.selected_items
        ])
        scroll_content.setText(items_text)
        scroll_content.setWordWrap(True)
        scroll_content.setStyleSheet("padding: 5px;")
        
        scroll_area.setWidget(scroll_content)
        items_layout.addWidget(scroll_area)
        items_group.setLayout(items_layout)
        main_layout.addWidget(items_group)
        
        # 说明标签
        info_label = QLabel(
            "提示：只勾选并修改需要批量更新的字段，未勾选的字段将保持原值不变。"
        )
        info_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 10px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)
        
        # 编辑字段区域
        form_layout = QGridLayout()
        form_layout.setSpacing(10)
        
        row = 0
        
        # --- 1. 材料类别 ---
        self.category_checkbox = QCheckBox("修改材料类别")
        self.category_combo = QComboBox()
        category_options = db_manager.get_config_options(self.db_path, 'CATEGORY')
        if not category_options:
            category_options = ["其他"]
        self.category_combo.addItems(category_options)
        self.category_combo.setEnabled(False)
        self.category_checkbox.stateChanged.connect(
            lambda state: self.category_combo.setEnabled(state == Qt.CheckState.Checked.value)
        )
        
        form_layout.addWidget(self.category_checkbox, row, 0)
        form_layout.addWidget(self.category_combo, row, 1)
        row += 1
        
        # --- 2. 计量单位 ---
        self.unit_checkbox = QCheckBox("修改计量单位")
        self.unit_combo = QComboBox()
        unit_options = db_manager.get_config_options(self.db_path, 'UNIT')
        if not unit_options:
            unit_options = ["个"]
        self.unit_combo.addItems(unit_options)
        self.unit_combo.setEnabled(False)
        self.unit_checkbox.stateChanged.connect(
            lambda state: self.unit_combo.setEnabled(state == Qt.CheckState.Checked.value)
        )
        
        form_layout.addWidget(self.unit_checkbox, row, 0)
        form_layout.addWidget(self.unit_combo, row, 1)
        row += 1
        
        # --- 3. 最小库存 ---
        self.min_stock_checkbox = QCheckBox("修改最小库存")
        self.min_stock_spin = QSpinBox()
        self.min_stock_spin.setRange(0, 999999)
        self.min_stock_spin.setValue(5)
        self.min_stock_spin.setEnabled(False)
        self.min_stock_checkbox.stateChanged.connect(
            lambda state: self.min_stock_spin.setEnabled(state == Qt.CheckState.Checked.value)
        )
        
        form_layout.addWidget(self.min_stock_checkbox, row, 0)
        form_layout.addWidget(self.min_stock_spin, row, 1)
        row += 1
        
        # --- 4. 存放位置 ---
        self.location_checkbox = QCheckBox("修改存放位置")
        self.location_combo = QComboBox()
        location_options = db_manager.get_config_options(self.db_path, 'LOCATION')
        if not location_options:
            location_options = ["其他"]
        self.location_combo.addItems(location_options)
        self.location_combo.setEnabled(False)
        self.location_checkbox.stateChanged.connect(
            lambda state: self.location_combo.setEnabled(state == Qt.CheckState.Checked.value)
        )
        
        form_layout.addWidget(self.location_checkbox, row, 0)
        form_layout.addWidget(self.location_combo, row, 1)
        row += 1
        
        main_layout.addLayout(form_layout)
        
        # 按钮栏
        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("批量更新")
        self.buttonBox.accepted.connect(self.accept_action)
        self.buttonBox.rejected.connect(self.reject)
        
        main_layout.addWidget(self.buttonBox)
        
    def accept_action(self):
        """执行批量更新操作"""
        
        # 检查是否至少选择了一个字段进行修改
        if not any([
            self.category_checkbox.isChecked(),
            self.unit_checkbox.isChecked(),
            self.min_stock_checkbox.isChecked(),
            self.location_checkbox.isChecked()
        ]):
            QMessageBox.warning(
                self, 
                "未选择修改字段", 
                "请至少勾选一个要修改的字段。"
            )
            return
        
        # 确认对话框
        checked_fields = []
        if self.category_checkbox.isChecked():
            checked_fields.append(f"材料类别 → {self.category_combo.currentText()}")
        if self.unit_checkbox.isChecked():
            checked_fields.append(f"计量单位 → {self.unit_combo.currentText()}")
        if self.min_stock_checkbox.isChecked():
            checked_fields.append(f"最小库存 → {self.min_stock_spin.value()}")
        if self.location_checkbox.isChecked():
            checked_fields.append(f"存放位置 → {self.location_combo.currentText()}")
        
        fields_text = "\n".join([f"  • {field}" for field in checked_fields])
        
        reply = QMessageBox.question(
            self,
            "确认批量修改",
            f"您确定要对 {len(self.selected_items)} 个物品进行以下修改吗？\n\n"
            f"{fields_text}\n\n"
            f"此操作将更新所有选中物品的这些字段。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 执行批量更新
        success_count = 0
        failed_count = 0
        
        for item in self.selected_items:
            try:
                # 获取原始数据
                item_id = item['id']
                name = item['name']
                reference = item['reference']
                
                # 确定要更新的值（选中的字段使用新值，未选中的保持原值）
                category = self.category_combo.currentText() if self.category_checkbox.isChecked() else item.get('category', '其他')
                unit = self.unit_combo.currentText() if self.unit_checkbox.isChecked() else item['unit']
                min_stock = self.min_stock_spin.value() if self.min_stock_checkbox.isChecked() else item['min_stock']
                location = self.location_combo.currentText() if self.location_checkbox.isChecked() else item['location']
                
                # 调用数据库更新
                if db_manager.update_inventory_item(
                    db_path=self.db_path,
                    item_id=item_id,
                    name=name,
                    reference=reference,
                    category=category,
                    unit=unit,
                    min_stock=min_stock,
                    location=location
                ):
                    success_count += 1
                else:
                    failed_count += 1
                    print(f"更新失败：{name} (ID: {item_id})")
                    
            except Exception as e:
                failed_count += 1
                print(f"更新物品时发生错误：{e}")
        
        # 显示结果
        if failed_count == 0:
            QMessageBox.information(
                self,
                "批量更新成功",
                f"成功更新了 {success_count} 个物品！"
            )
            super().accept()  # 关闭对话框
        else:
            QMessageBox.warning(
                self,
                "批量更新完成（有错误）",
                f"成功更新：{success_count} 个\n失败：{failed_count} 个\n\n请检查失败的物品。"
            )
            super().accept()  # 仍然关闭对话框


# --- 测试代码 ---
if __name__ == '__main__':
    # 模拟 db_manager
    class MockDBManager:
        @staticmethod
        def get_config_options(db_path, category):
            options = {
                "UNIT": ["个", "套", "对", "箱", "卷", "米"],
                "LOCATION": ["基地仓库", "大仓库", "别墅", "办公楼", "公寓", "其他"],
                "CATEGORY": ["电子元件", "机械零件", "工具", "耗材", "其他"]
            }
            return options.get(category, [])
        
        @staticmethod
        def update_inventory_item(*args, **kwargs):
            print(f"Mock Update: {kwargs}")
            return True
    
    db_manager = MockDBManager()
    
    app = QApplication(sys.argv)
    
    # 模拟选中的物品
    test_items = [
        {'id': 1, 'name': 'LED灯管', 'reference': 'LED-001', 'category': '电子元件', 
         'unit': '个', 'min_stock': 10, 'location': '大仓库'},
        {'id': 2, 'name': '螺丝刀', 'reference': 'TOOL-001', 'category': '工具', 
         'unit': '套', 'min_stock': 5, 'location': '基地仓库'},
        {'id': 3, 'name': '电线', 'reference': 'WIRE-001', 'category': '电子元件', 
         'unit': '米', 'min_stock': 100, 'location': '别墅'}
    ]
    
    dialog = BatchEditDialog('test.db', test_items)
    dialog.exec()
    
    sys.exit(0)