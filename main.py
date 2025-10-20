# main.py
import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QStackedWidget, QLabel, 
    QFrame, QMessageBox # <--- [新增] 导入 QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QIcon # 导入用于图标和图片的类

# 导入功能页面
from inventory_page import InventoryPage 
from transaction_page import TransactionPage 
# [修改] 导入新的设置工具 Widget
from settings_widget import SettingsWidget 

# --- 资源路径处理函数 ---
# 定义 Logo 文件名（假设您的 Logo 文件名为 logo.png）
LOGO_FILENAME = 'logo.png' 

def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径，适配开发环境和 PyInstaller 打包环境。
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # 打包环境：使用 PyInstaller 临时目录 (sys._MEIPASS)
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# --- 1. 定义主窗口类 ---
class MainWindow(QMainWindow):

    def __init__(self, db_path):
        super().__init__()
        # 接收从 login.py 传递来的数据库路径
        self.db_path = db_path 
        self.setWindowTitle("仓库管理系统 (Honsen Africa CI) - 主程序")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置窗口图标 (显示在任务栏和标题栏左上角)
        self.setWindowIcon(QIcon(get_resource_path(LOGO_FILENAME)))
        
        self.init_ui()
        
    def init_ui(self):
        # 1. 创建中心部件和主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_h_layout = QHBoxLayout(self.central_widget)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)

        # 2. 创建侧边导航栏
        self.create_sidebar()
        
        # 3. 创建主内容区 (堆栈式布局)
        self.stacked_widget = QStackedWidget()
        self.main_h_layout.addWidget(self.stacked_widget)
        
        # 4. 初始化所有页面
        self.create_pages()
        
        # 5. 设置状态栏
        self.statusBar().showMessage(f"数据库连接路径: {self.db_path} | 仅限弘盛非洲机电仓管人员使用 | 有需求或bug找王一健。")
        
        # 默认显示第一个页面
        self.show_page(0) 

    def create_sidebar(self):
        """创建左侧导航栏和按钮"""
        sidebar = QFrame()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet("""
            background-color: #3f51b5; 
            color: white;
            border-right: 1px solid #283593;
        """)
        
        v_layout = QVBoxLayout(sidebar)
        v_layout.setContentsMargins(10, 20, 10, 10)
        v_layout.setSpacing(15)
        
        # --- [新增] 左上角 Logo 区域 ---
        logo_label = QLabel()
        logo_path = get_resource_path(LOGO_FILENAME)
        
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # 缩放 Logo 以适应侧边栏宽度 (160 像素宽，50 像素高)
            logo_label.setPixmap(pixmap.scaled(
                160, 50, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            ))
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            # 如果图片不存在，显示文字占位符
            logo_label.setText("HONSEN WMS")
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setStyleSheet("font-size: 16pt; font-weight: bold; padding: 10px; color: #ff9800;")
            
        v_layout.addWidget(logo_label)
        v_layout.addSpacing(20) # 增加 Logo 和导航按钮之间的间距
        # ----------------------------
        
        btn_style = """
            QPushButton {
                background-color: #5c6bc0; 
                color: white;
                padding: 10px;
                border: none;
                border-radius: 5px;
                text-align: left;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #7986cb; 
            }
            QPushButton:checked {
                background-color: #ff9800; 
                font-weight: bold;
            }
        """

        self.nav_buttons = []
        pages = ["库存管理", "交易记录", "系统设置"]
        
        for i, name in enumerate(pages):
            btn = QPushButton(name)
            btn.setStyleSheet(btn_style)
            btn.setCheckable(True) 
            # 使用 lambda 传参切换页面
            btn.clicked.connect(lambda checked, index=i: self.show_page(index))
            v_layout.addWidget(btn)
            self.nav_buttons.append(btn)
            
        v_layout.addStretch(1) 
        
        self.main_h_layout.addWidget(sidebar)


    def create_pages(self):
        """创建并向 QStackedWidget 添加所有功能页面"""
        
        # 1. 库存管理页面 (必须先创建，以便传递其引用)
        self.inventory_page = InventoryPage(self.db_path)
        self.stacked_widget.addWidget(self.inventory_page)

        # 2. 交易记录页面
        # 传递 inventory_page 的引用
        self.transaction_page = TransactionPage(
            db_path=self.db_path,
            inventory_page_ref=self.inventory_page
        ) 
        self.stacked_widget.addWidget(self.transaction_page)

        # 3. 系统设置页面 
        # [修改] 现在使用 settings_widget.py 中的 SettingsWidget
        self.settings_page = SettingsWidget(self.db_path) 
        self.stacked_widget.addWidget(self.settings_page)


    def show_page(self, index):
        """切换显示的页面并更新导航按钮状态"""
        self.stacked_widget.setCurrentIndex(index)
        
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
            
            
    # --- [新增] 关闭事件确认 ---
    def closeEvent(self, event):
        """
        当用户尝试关闭窗口时，弹出确认对话框。
        """
        reply = QMessageBox.question(
            self, 
            '确认退出',
            "您确定要退出仓库管理系统吗？", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No # 默认选中“否”
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 如果用户选择“是”，则接受关闭事件
            event.accept()
        else:
            # 如果用户选择“否”或关闭对话框，则忽略关闭事件
            event.ignore()
    # --- [新增] 关闭事件确认结束 ---


# --- 2. 应用程序入口 (供 login.py 导入，此部分保持注释) ---
# if __name__ == '__main__':
#     # 确保应用程序只有一个实例
#     app = QApplication(sys.argv)
    
#     # 尝试从命令行参数获取数据库路径（通常由 login.py 传入）
#     if len(sys.argv) > 1:
#         db_path = sys.argv[1] 
#     else:
#         # 如果是独立启动，使用默认路径
#         print("警告：main.py 独立启动。请通过 login.py 启动以获取正确的数据库路径。")
#         db_path = os.path.join(os.getcwd(), 'honsen_storage.db')

#     window = MainWindow(db_path)
#     window.show()
#     sys.exit(app.exec())
