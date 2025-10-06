import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QFrame, QApplication,
    QFileDialog
)
from PyQt6.QtCore import Qt
import os
# 导入数据库管理器，我们需要其中的 check_admin_credentials, update_admin_password 以及数据导入导出方法
import db_manager 

# 假设项目中存在 data_utility.py 用于处理文件IO
# 您需要创建此文件并实现 export_to_csv 和 import_from_csv 函数
try:
    import data_utility 
except ImportError:
    # 临时定义一个存根，确保代码可运行，但需要用户实现 data_utility 
    class MockDataUtility:
        @staticmethod
        def export_to_csv(data: list, filepath: str, headers: list):
            print(f"Mock: Exporting {len(data)} rows to {filepath}")
            # 真实实现应将数据写入CSV
            return True

        @staticmethod
        def import_from_csv(filepath: str) -> list:
            print(f"Mock: Importing data from {filepath}")
            # 真实实现应从CSV读取并返回字典列表
            # 模拟返回一些数据，以测试db_manager的调用
            return []

    data_utility = MockDataUtility()


class SettingsPage(QWidget):
    """
    系统设置界面：只包含数据导入/导出功能。
    """
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel("<h2>系统设置与数据管理</h2>")
        main_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addSpacing(20)

        # ----------------------------------------
        # I. 数据管理区域
        # 移除了密码修改区域，数据管理区域现在是第一个功能块
        # ----------------------------------------
        data_frame = QFrame()
        data_frame.setFixedWidth(450)
        data_frame.setFrameShape(QFrame.Shape.StyledPanel)
        data_frame.setStyleSheet("QFrame { border: 1px solid #ccc; border-radius: 8px; padding: 15px; }")
        
        data_layout = QVBoxLayout(data_frame)
        data_layout.setSpacing(10)
        
        data_layout.addWidget(QLabel("<h3>数据导入/导出 (CSV)</h3>"))
        data_layout.addWidget(QLabel("警告：导入操作会覆盖或新增现有库存数据。"))

        # --- 导出按钮 ---
        export_title = QLabel("<b>数据导出:</b>")
        data_layout.addWidget(export_title)
        
        export_grid = QGridLayout()
        self.export_inv_btn = QPushButton("导出库存清单 (.csv)")
        self.export_inv_btn.clicked.connect(self.export_inventory_action)
        self.export_inv_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px; border-radius: 4px;")
        
        self.export_tx_btn = QPushButton("导出交易记录 (.csv)")
        self.export_tx_btn.clicked.connect(self.export_transactions_action)
        self.export_tx_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px; border-radius: 4px;")
        
        export_grid.addWidget(self.export_inv_btn, 0, 0)
        export_grid.addWidget(self.export_tx_btn, 0, 1)
        data_layout.addLayout(export_grid)
        data_layout.addSpacing(15)
        
        # --- 导入按钮 ---
        import_title = QLabel("<b>数据导入:</b>")
        data_layout.addWidget(import_title)

        self.import_inv_btn = QPushButton("导入/更新库存清单 (.csv)")
        self.import_inv_btn.clicked.connect(self.import_inventory_action)
        self.import_inv_btn.setStyleSheet("background-color: #FF9800; color: black; padding: 8px; border-radius: 4px;")
        data_layout.addWidget(self.import_inv_btn)

        main_layout.addWidget(data_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch(1)


    # ----------------------------------------
    # I. 删除了 change_password_action 方法
    # ----------------------------------------

    # ----------------------------------------
    # II. 数据管理方法 
    # ----------------------------------------
    
    def export_inventory_action(self):
        """导出库存清单到 CSV 文件"""
        filepath, _ = QFileDialog.getSaveFileName(self, "导出库存清单", "inventory_export.csv", "CSV Files (*.csv)")
        
        if filepath:
            data = db_manager.get_inventory_for_export(self.db_path)
            headers = ["name", "reference", "unit", "current_stock", "min_stock", "location"]
            
            if data_utility.export_to_csv(data, filepath, headers):
                QMessageBox.information(self, "导出成功", f"库存清单已成功导出到:\n{filepath}")
            else:
                QMessageBox.critical(self, "导出失败", "写入文件时发生错误。")


    def export_transactions_action(self):
        """导出交易记录到 CSV 文件"""
        filepath, _ = QFileDialog.getSaveFileName(self, "导出交易记录", "transactions_export.csv", "CSV Files (*.csv)")
        
        if filepath:
            data = db_manager.get_transactions_for_export(self.db_path)
            headers = ["date", "type", "quantity", "recipient_source", "project_ref", "item_name", "item_reference"]
            
            if data_utility.export_to_csv(data, filepath, headers):
                QMessageBox.information(self, "导出成功", f"交易记录已成功导出到:\n{filepath}")
            else:
                QMessageBox.critical(self, "导出失败", "写入文件时发生错误。")


    def import_inventory_action(self):
        """从 CSV 文件导入或更新库存清单"""
        filepath, _ = QFileDialog.getOpenFileName(self, "选择要导入的库存文件", "", "CSV Files (*.csv)")
        
        if not filepath:
            return

        # 1. 读取 CSV 文件 (假设 data_utility 处理了格式验证)
        try:
            items_to_import = data_utility.import_from_csv(filepath)
        except Exception as e:
            QMessageBox.critical(self, "导入错误", f"读取或解析文件失败: {e}")
            return
        
        if not items_to_import:
            QMessageBox.warning(self, "导入警告", "文件内容为空或格式不正确，没有可导入的数据。")
            return
        
        # 2. 执行批量导入/更新
        stats = db_manager.batch_import_inventory(self.db_path, items_to_import)
        
        # 3. 显示结果
        message = (
            f"库存批量导入操作完成:\n\n"
            f"新增记录: {stats['inserted']} 条\n"
            f"更新记录: {stats['updated']} 条\n"
            f"失败记录: {stats['failed']} 条 (可能由于 'reference' 字段缺失或数据库完整性错误)"
        )
        if stats['failed'] > 0:
             QMessageBox.warning(self, "导入完成 (有错误)", message)
        else:
             QMessageBox.information(self, "导入成功", message)
             
# --- 暂时不需要运行 ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 假设数据库文件存在
    TEST_DB_PATH = 'honsen_storage.db' 
    if not os.path.exists(TEST_DB_PATH):
        print("警告: 数据库文件不存在，请先运行 login.py 或 main.py 进行初始化。")
        # 为了测试，我们可以尝试初始化它
        db_manager.initialize_database(TEST_DB_PATH) 
    
    window = SettingsPage(TEST_DB_PATH)
    window.show()
    sys.exit(app.exec())
