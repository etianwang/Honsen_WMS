import sqlite3
import sys
import os
import csv 
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QLabel, QLineEdit, QPushButton, 
    QMessageBox, QListWidget, QListWidgetItem,
    QFrame, QFileDialog, QTabWidget, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon 

# 假设导入 db_manager 和 data_utility
try:
    import db_manager 
    import data_utility 
except ImportError:
    # --- 临时存根/模拟类 ---
    class MockDBManager:
        @staticmethod
        def get_inventory_for_export(db_path):
            # 模拟导出数据
            return [{'name': 'Mock Item 1', 'reference': 'REF001', 'current_stock': 10, 'location': 'A1', 'category': 'Cat', 'notes': '', 'unit': '个', 'min_stock': 1}]
        
        @staticmethod
        def get_transactions_for_export(db_path):
            # 模拟交易记录导出
            return [{'date': '2024-01-01', 'type': 'IN', 'quantity': 5, 'recipient_source': 'Sup', 'project_ref': 'P1', 'item_name': 'Mock Item 1', 'item_reference': 'REF001'}]

        @staticmethod
        def batch_import_inventory(db_path, items):
            # 模拟批量导入
            return {'inserted': 0, 'updated': len(items), 'failed': 0}
            
    class MockDataUtility:
        @staticmethod
        def export_to_csv(data: list, filepath: str, headers: list):
            # 模拟 CSV 导出
            if not data: return True
            try:
                # 实际环境中会写入文件
                print(f"Mock Export to: {filepath}")
                return True
            except Exception as e:
                return False

        @staticmethod
        def import_from_csv(filepath: str) -> list:
            # 模拟 CSV 导入
            return [{'reference': 'TEST-A', 'name': 'Imported A', 'current_stock': 1, 'unit': '个', 'location': 'L1'}]

    db_manager = MockDBManager()
    data_utility = MockDataUtility()
# --- 模拟类结束 ---


# --- 数据库操作辅助函数 ---

def get_db_connection(db_path):
    """建立 SQLite 连接。"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        QMessageBox.critical(None, "数据库错误", f"无法连接数据库: {db_path}\n错误: {e}")
        return None

# =========================================================================
# I. 基础配置标签页 (Location & Project Management) - 使用 2x2 网格布局
# =========================================================================

class ConfigurationPage(QWidget):
    """
    负责基础配置项 (存放位置 LOCATION, 项目名称 PROJECT, 计量单位 UNIT, 材料类别 CATEGORY) 的增删改查 UI 和逻辑。
    使用 2x2 网格布局，优化空间利用和视觉效果。
    """
    def __init__(self, db_path, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.init_ui()
        self.load_all_configs()

    # --- 数据库 CRUD 操作 (通用配置) ---
    
    def fetch_configs(self, category):
        """从 config 表中获取特定类别的配置值。"""
        conn = get_db_connection(self.db_path)
        if conn is None: return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE category = ? ORDER BY value COLLATE NOCASE ASC", (category,))
            return [row['value'] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"数据库查询错误 (fetch_configs for {category}): {e}")
            QMessageBox.critical(self, "数据库错误", f"读取 {category} 时出错: {e}")
            return []
        finally:
            conn.close()

    def insert_config(self, category, value):
        """向 config 表中插入一个新的配置值。"""
        if not value: return False
        conn = get_db_connection(self.db_path)
        if conn is None: return False
            
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO config (category, value) VALUES (?, ?)", 
                             (category, value))
            conn.commit()
            return cursor.rowcount > 0 
        except sqlite3.Error as e:
            print(f"数据库插入错误 (insert_config for {category}): {e}")
            QMessageBox.critical(self, "数据库错误", f"插入配置时出错: {e}")
            return False
        finally:
            conn.close()

    def remove_config(self, category, value):
        """从 config 表中删除一个配置值。"""
        conn = get_db_connection(self.db_path)
        if conn is None: return False
            
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM config WHERE category = ? AND value = ?", (category, value))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"数据库删除错误 (remove_config for {category}): {e}")
            QMessageBox.critical(self, "数据库错误", f"删除配置时出错: {e}")
            return False
        finally:
            conn.close()

    # --- UI 初始化和逻辑 (Refactored) ---
    
    def init_ui(self):
        """初始化基础配置页面的布局和组件，使用 2x2 网格布局。"""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(30, 30, 30, 30)

        main_layout.addWidget(QLabel("<h2>基础配置管理</h2>"))
        main_layout.addWidget(QLabel("管理系统使用的通用配置项，如存放位置、项目名称、计量单位和材料类别。"))
        main_layout.addSpacing(15)
        
        # 使用 QScrollArea 确保在内容过多时可以滚动
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)

        # -----------------------------------------------
        # 配置项 2x2 网格布局 (平铺展示四个配置面板)
        # -----------------------------------------------
        config_grid = QGridLayout()
        config_grid.setSpacing(20) # 间距
        config_grid.setContentsMargins(0, 10, 0, 10)

        # 1. 存放位置 (LOCATION) - Row 0, Col 0
        location_container = self._create_config_panel('LOCATION', 'location_input', 'location_list', 'location_delete_btn', "存放位置")
        config_grid.addWidget(location_container, 0, 0)

        # 2. 项目名称 (PROJECT) - Row 0, Col 1
        project_container = self._create_config_panel('PROJECT', 'project_input', 'project_list', 'project_delete_btn', "项目名称")
        config_grid.addWidget(project_container, 0, 1)

        # 3. 计量单位 (UNIT) - Row 1, Col 0
        unit_container = self._create_config_panel('UNIT', 'unit_input', 'unit_list', 'unit_delete_btn', "计量单位")
        config_grid.addWidget(unit_container, 1, 0)

        # 4. 材料类别 (CATEGORY) - Row 1, Col 1
        category_container = self._create_config_panel('CATEGORY', 'category_input', 'category_list', 'category_delete_btn', "材料类别")
        config_grid.addWidget(category_container, 1, 1)

        content_layout.addLayout(config_grid)
        content_layout.addStretch(1) # 撑开底部空间

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
    def _create_config_panel(self, category: str, input_attr: str, list_attr: str, btn_attr: str, display_name: str) -> QFrame:
        """
        创建单个配置项的面板 (QFrame)，并调用 _setup_config_section 来填充内容。
        """
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        # 增加背景色和边框，美化面板
        frame.setStyleSheet("QFrame { border: 1px solid #d0d0d0; border-radius: 8px; padding: 15px; background-color: #ffffff; }")
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel(f"<b>{display_name} ({category})</b>")
        title_label.setStyleSheet("font-size: 12pt; color: #3f51b5; margin-bottom: 5px;")
        layout.addWidget(title_label)
        
        # Separator within the panel
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("QFrame { border: 1px solid #eee; margin-bottom: 10px;}")
        layout.addWidget(line)
        
        # Fill content
        self._setup_config_section(layout, category, input_attr, list_attr, btn_attr, display_name)
        
        layout.addStretch(1) # 确保垂直空间利用
        return frame


    def _setup_config_section(self, section_layout: QVBoxLayout, category: str, input_attr: str, list_attr: str, btn_attr: str, display_name: str):
        """通用配置区段的创建函数（用于填充面板）。"""
        
        # 输入和添加布局
        add_layout = QHBoxLayout()
        input_field = QLineEdit()
        input_field.setPlaceholderText(f"输入新的{display_name}...")
        input_field.setMinimumHeight(35)
        setattr(self, input_attr, input_field) # 动态设置属性
        
        add_btn = QPushButton("添加") # 简化按钮文本
        add_btn.setFixedWidth(80)
        add_btn.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 5px; font-weight: bold;")
        add_btn.clicked.connect(lambda: self.add_config_action(category, input_attr, list_attr, display_name))
        
        add_layout.addWidget(input_field)
        add_layout.addWidget(add_btn)
        section_layout.addLayout(add_layout)

        # 列表显示区域
        list_widget = QListWidget()
        list_widget.setMinimumHeight(150) # 增加高度以适应 2x2 布局
        list_widget.setStyleSheet("QListWidget {border: 1px solid #ddd; padding: 5px; border-radius: 5px; background-color: #fafafa;}")
        setattr(self, list_attr, list_widget) # 动态设置属性
        section_layout.addWidget(list_widget)

        # 删除按钮区域
        delete_layout = QHBoxLayout()
        delete_btn = QPushButton(f"删除选中")
        delete_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; border-radius: 5px;")
        delete_btn.setMinimumHeight(35)
        delete_btn.clicked.connect(lambda: self.delete_config_action(category, list_attr, display_name))
        delete_btn.setEnabled(False)
        setattr(self, btn_attr, delete_btn) # 动态设置属性
        
        # 启用/禁用删除按钮的连接
        list_widget.itemSelectionChanged.connect(
            lambda: delete_btn.setEnabled(len(list_widget.selectedItems()) > 0)
        )
        
        delete_layout.addStretch(1)
        delete_layout.addWidget(delete_btn)
        delete_layout.addStretch(1)
        section_layout.addLayout(delete_layout)
        
    
    def load_all_configs(self):
        """加载所有配置项并填充列表。"""
        # 1. 加载 LOCATION
        self.location_list.clear()
        locations = self.fetch_configs('LOCATION')
        for loc in locations:
            QListWidgetItem(loc, self.location_list)

        # 2. 加载 PROJECT
        self.project_list.clear()
        projects = self.fetch_configs('PROJECT')
        for proj in projects:
            QListWidgetItem(proj, self.project_list)

        # 3. 加载 UNIT (新增)
        self.unit_list.clear()
        units = self.fetch_configs('UNIT')
        for unit in units:
            QListWidgetItem(unit, self.unit_list)

        # 4. 加载 CATEGORY (新增)
        self.category_list.clear()
        categories = self.fetch_configs('CATEGORY')
        for cat in categories:
            QListWidgetItem(cat, self.category_list)


    def add_config_action(self, category: str, input_attr: str, list_attr: str, display_name: str):
        """处理添加新配置项的点击事件。"""
        input_field: QLineEdit = getattr(self, input_attr)
        new_value = input_field.text().strip()
        
        if not new_value:
            QMessageBox.warning(self, "输入警告", f"{display_name} 名称不能为空。")
            return
            
        if self.insert_config(category, new_value):
            input_field.clear()
            self.load_all_configs()
            QMessageBox.information(self, "操作成功", f"{display_name} '{new_value}' 添加成功。")
        else:
             QMessageBox.warning(self, "操作失败", f"{display_name} '{new_value}' 可能已存在或数据库操作失败。")


    def delete_config_action(self, category: str, list_attr: str, display_name: str):
        """处理删除选中配置项的点击事件。"""
        list_widget: QListWidget = getattr(self, list_attr)
        selected_items = list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "选择警告", f"请选择要删除的 {display_name}。")
            return
            
        value_to_delete = selected_items[0].text()
        
        reply = QMessageBox.question(self, '确认删除',
            f"确定要删除 {display_name} '{value_to_delete}' 吗？\n\n注意：此操作不会更改现有库存/交易记录中的该字段。", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.remove_config(category, value_to_delete):
                self.load_all_configs()
                QMessageBox.information(self, "操作成功", f"{display_name} '{value_to_delete}' 已删除。")
            else:
                QMessageBox.critical(self, "操作失败", f"删除 {display_name} '{value_to_delete}' 失败。")


# =========================================================================
# II. 数据导入/导出标签页 (Data Management)
# =========================================================================

class DataManagementPage(QWidget):
    """
    负责 CSV 导入和导出 UI 和逻辑。
    """
    def __init__(self, db_path, refresh_inventory_callback=None, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.refresh_inventory_callback = refresh_inventory_callback
        self.init_ui()

    def init_ui(self):
        """初始化数据管理页面的布局和组件。"""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(30, 30, 30, 30)

        main_layout.addWidget(QLabel("<h2>数据导入/导出 (CSV)</h2>"))
        main_layout.addWidget(QLabel("使用 CSV 文件进行数据的备份和批量更新。"))
        main_layout.addWidget(QLabel("警告：导入操作会覆盖或新增现有库存数据，请谨慎操作。", styleSheet="color: #f44336; font-weight: bold;"))
        main_layout.addSpacing(20)

        # --- 导出部分 ---
        export_frame = self._create_section_frame("数据导出：备份库存与交易记录")
        export_layout = export_frame.layout() 
        
        export_grid = QGridLayout()

        self.export_inv_btn = QPushButton("导出库存清单 (.csv)")
        self.export_inv_btn.clicked.connect(self.export_inventory_action)
        self.export_inv_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px; border-radius: 4px; font-weight: bold;")
        
        self.export_tx_btn = QPushButton("导出交易记录 (.csv)")
        self.export_tx_btn.clicked.connect(self.export_transactions_action)
        self.export_tx_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px; border-radius: 4px; font-weight: bold;")
        
        export_grid.addWidget(self.export_inv_btn, 0, 0)
        export_grid.addWidget(self.export_tx_btn, 0, 1)
        
        export_layout.addLayout(export_grid) 
        main_layout.addWidget(export_frame)
        main_layout.addSpacing(20)
        
        # --- 导入部分 ---
        import_frame = self._create_section_frame("数据导入：批量更新/新增库存")
        import_layout = import_frame.layout() 

        self.import_inv_btn = QPushButton("导入/更新库存清单 (.csv)")
        self.import_inv_btn.clicked.connect(self.import_inventory_action)
        self.import_inv_btn.setStyleSheet("background-color: #FF9800; color: black; padding: 10px; border-radius: 4px; font-weight: bold;")
        
        import_layout.addWidget(self.import_inv_btn) 
        main_layout.addWidget(import_frame)

        main_layout.addStretch(1)


    def _create_section_frame(self, title):
        """创建带标题和边框的区域框架，并在内部设置布局和标题。"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("QFrame { border: 1px solid #ccc; border-radius: 8px; padding: 15px; }")
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 10) 

        title_label = QLabel(f"<b>{title}</b>")
        title_label.setStyleSheet("font-size: 12pt; color: #333; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        return frame


    def export_inventory_action(self):
        """导出库存清单到 CSV 文件"""
        filepath, _ = QFileDialog.getSaveFileName(self, "导出库存清单", "inventory_export.csv", "CSV Files (*.csv)")
        
        if filepath:
            data = db_manager.get_inventory_for_export(self.db_path)
            # 确保导出字段与导入字段一致
            headers = ["name", "reference", "unit", "current_stock", "min_stock", "location", "project", "notes"] 
            
            if data_utility.export_to_csv(data, filepath, headers):
                QMessageBox.information(self, "导出成功", f"库存清单已成功导出到:\n{filepath}")
            else:
                QMessageBox.critical(self, "导出失败", "写入文件时发生错误。")


    def export_transactions_action(self):
        """导出交易记录到 CSV 文件"""
        filepath, _ = QFileDialog.getSaveFileName(self, "导出交易记录", "transactions_export.csv", "CSV Files (*.csv)")
        
        if filepath:
            data = db_manager.get_transactions_for_export(self.db_path)
            # 注意: 这里使用 'project_ref' 对应数据库字段，而不是 'category'
            headers = ["date", "type", "quantity", "recipient_source", "project_ref", "item_name", "item_reference"]
            
            if data_utility.export_to_csv(data, filepath, headers):
                QMessageBox.information(self, "导出成功", f"交易记录已成功导出到:\n{filepath}")
            else:
                QMessageBox.critical(self, "导出失败", "写入文件时发生错误。")


    def import_inventory_action(self):
        """从 CSV 文件导入或更新库存清单"""
        filepath, _ = QFileDialog.getOpenFileName(self, "选择要导入的库存文件", os.path.expanduser("~"), "CSV Files (*.csv)")
        
        if not filepath:
            return

        # 1. 确认导入
        reply = QMessageBox.question(self, '确认导入',
            f"您确定要使用文件 '{os.path.basename(filepath)}' 导入数据吗？\n\n警告：此操作将批量更新或新增库存数据！", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return

        # 2. 读取 CSV 文件
        try:
            items_to_import = data_utility.import_from_csv(filepath)
        except Exception as e:
            QMessageBox.critical(self, "导入错误", f"读取或解析文件失败: {e}")
            return
        
        if not items_to_import:
            QMessageBox.warning(self, "导入警告", "文件内容为空或格式不正确，没有可导入的数据。")
            return
        
        # 3. 执行批量导入/更新
        stats = db_manager.batch_import_inventory(self.db_path, items_to_import)
        
        # 4. 显示结果
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
            
        # 5. 刷新库存页面
        if self.refresh_inventory_callback:
            self.refresh_inventory_callback()
            print("InventoryPage 刷新回调已执行。")


# =========================================================================
# III. 主设置窗口 (Tab Widget)
# =========================================================================

class SettingsWidget(QWidget):
    """
    主设置窗口，包含两个 QTabWidget 标签页。
    """
    def __init__(self, db_path, refresh_inventory_callback=None, parent=None): 
        super().__init__(parent)
        self.db_path = db_path
        self.refresh_inventory_callback = refresh_inventory_callback 
        self.setWindowTitle("系统配置与管理")
        self.init_ui()
    
    def init_ui(self):
        """初始化主界面的布局，使用 QTabWidget。"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)

        # 标题
        title = QLabel("<h2>系统配置与管理</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #3f51b5;")
        main_layout.addWidget(title)
        main_layout.addSpacing(10)

        # 创建 Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setFixedWidth(850) # 增大宽度以适应 2x2 布局
        self.tab_widget.setStyleSheet(
            """
            QTabWidget::pane { border: 1px solid #ccc; border-radius: 8px; }
            QTabBar::tab { padding: 10px 20px; font-weight: bold; }
            QTabBar::tab:selected { background: #e0e0e0; }
            """
        )

        # 1. 基础配置页 (包含位置和项目)
        self.config_page = ConfigurationPage(self.db_path)
        self.tab_widget.addTab(self.config_page, "基础配置")

        # 2. 数据导入/导出页
        self.data_page = DataManagementPage(self.db_path, self.refresh_inventory_callback)
        self.tab_widget.addTab(self.data_page, "数据导入/导出")

        main_layout.addWidget(self.tab_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch(1)

# --- 测试运行 (可选) ---
if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    
    # 模拟初始化数据库
    TEST_DB_PATH = 'test_storage.db' 
    if not os.path.exists(TEST_DB_PATH):
        try:
            conn = sqlite3.connect(TEST_DB_PATH)
            cursor = conn.cursor()
            # 确保 config 表存在
            cursor.execute("CREATE TABLE IF NOT EXISTS config (category TEXT, value TEXT UNIQUE, PRIMARY KEY (category, value))")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error initializing test database: {e}")
            
    # 模拟刷新回调函数
    def mock_refresh():
        print("Mock: Inventory List Refreshed!")

    main_window = QMainWindow()
    settings_widget = SettingsWidget(TEST_DB_PATH, refresh_inventory_callback=mock_refresh)
    main_window.setCentralWidget(settings_widget)
    main_window.setWindowTitle("Settings Demo")
    main_window.setMinimumSize(900, 750) 

    main_window.show()
    sys.exit(app.exec())
