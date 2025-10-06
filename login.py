import sys
import os
import sqlite3
import bcrypt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QMessageBox, 
    QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QPixmap, QIcon 
from main import MainWindow # 导入 MainWindow 类

# --- 配置和常量 ---
# 数据库文件名称
DB_NAME = 'honsen_storage' 
DB_FILE = f'{DB_NAME}.db' 
# 默认管理员凭证
DEFAULT_LOGIN_USER = 'Honsen_Admin'
DEFAULT_LOGIN_PASS_PLAINTEXT = '66778899HONSEN' 

# --- 资源文件名 ---
LOGO_FILENAME = 'logo.png' 
BANNER_FILENAME = 'banner.png' 

# --- 数据库路径固定 ---
DB_FOLDER = 'db'

# --- 1. 外部文件路径处理函数 (用于 DB 文件) ---
def get_base_dir():
    """
    获取程序运行时的基准目录，用于创建外部文件（如数据库）。
    - 打包环境 (sys.frozen)：返回 EXE 所在的永久目录。
    """
    if getattr(sys, 'frozen', False):
        # 打包环境：sys.executable 是 EXE 文件的完整路径
        return os.path.dirname(sys.executable)
    else:
        # 开发环境：__file__ 是当前脚本的路径
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()

# 固定的完整数据库路径：[EXE 所在目录]/db/honsen_storage.db
FIXED_DB_PATH = os.path.join(BASE_DIR, DB_FOLDER, DB_FILE)
# --- END 数据库路径固定 ---


# --- 2. 内部资源路径处理函数 (用于图片文件) ---
def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径，适配开发环境和 PyInstaller 打包环境。
    【关键修复】使用 sys._MEIPASS 来获取 --onefile 模式下的临时资源路径。
    目的：用于加载通过 --add-data 打包进 EXE 内部的资源。
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # 打包环境：使用 PyInstaller 临时目录 (sys._MEIPASS)
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)
# --- END 资源路径处理函数 ---


# --- 数据库操作：基础连接和工具函数 (以下保持不变) ---

def get_db_connection(db_path, create_if_missing=False):
    """根据提供的路径建立 SQLite 连接。"""
    try:
        if not db_path:
            db_path = DB_FILE
        
        file_exists = os.path.exists(db_path)
        
        if not file_exists and not create_if_missing:
            QMessageBox.critical(None, "数据库连接错误", 
                                 f"数据库文件 '{db_path}' 不存在。请点击 '初始化数据库' 按钮创建。")
            return None

        # 尝试连接。
        conn = sqlite3.connect(db_path)
        return conn
        
    except Exception as e:
        QMessageBox.critical(None, "数据库连接错误", f"无法连接数据库文件 '{db_path}'。\n错误: {e}")
        return None

def hash_password(password_plaintext):
    """使用 bcrypt 对明文密码进行哈希"""
    return bcrypt.hashpw(password_plaintext.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# --- 业务表初始化逻辑 ---

def initialize_all_schema(conn):
    """检查并创建所有三张表 (admin_user, Inventory, Transactions)，并插入默认管理员账号。"""
    cursor = conn.cursor()
    
    try:
        # 1. 检查 admin_user 表是否存在 (作为是否为新表的判断依据)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_user'")
        if cursor.fetchone() is not None:
            cursor.close()
            QMessageBox.information(None, "初始化提示", "数据库已存在，并非新数据库。跳过创建。")
            return

        # 2. 如果不存在，则创建所有表
        
        # A. admin_user 表 (用户管理)
        cursor.execute("""
            CREATE TABLE admin_user (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL 
            );
        """)
        
        # B. 插入默认管理员账号
        hashed_pass = hash_password(DEFAULT_LOGIN_PASS_PLAINTEXT)
        cursor.execute("INSERT INTO admin_user (username, password) VALUES (?, ?)", 
                         (DEFAULT_LOGIN_USER, hashed_pass))
        
        # C. Inventory 表 (库存物品)
        cursor.execute("""
            CREATE TABLE Inventory (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                reference TEXT UNIQUE,
                unit TEXT,
                current_stock INTEGER,
                min_stock INTEGER,
                location TEXT
            )
        """)
        
        # D. Transactions 表 (交易记录)
        cursor.execute("""
            CREATE TABLE Transactions (
                id INTEGER PRIMARY KEY,
                item_id INTEGER,
                type TEXT NOT NULL, -- 'IN' 或 'OUT'
                quantity INTEGER NOT NULL,
                date TEXT,
                recipient_source TEXT,
                project_ref TEXT,
                FOREIGN KEY (item_id) REFERENCES Inventory (id)
            )
        """)
        
        conn.commit()
        cursor.close()
        QMessageBox.information(None, "初始化成功", 
                                 f"所有表格已创建，默认管理员 ({DEFAULT_LOGIN_USER}/{DEFAULT_LOGIN_PASS_PLAINTEXT}) 已设置！")
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        QMessageBox.critical(None, "初始化失败", f"创建表格时发生错误。\n错误内容: {e}")

# --- 登录验证 (应用层验证) ---

def validate_user_login(conn, login_user, login_pass_plaintext):
    """在 admin_user 表中验证登录账号和明文密码。"""
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # 确保 admin_user 表存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_user'")
        if cursor.fetchone() is None:
            QMessageBox.critical(None, "登录失败", "数据库未初始化，请先点击 '初始化数据库' 按钮。")
            return False

        query = "SELECT password FROM admin_user WHERE username = ?"
        cursor.execute(query, (login_user,))
        result = cursor.fetchone()
        cursor.close()
        
        if not result:
            return False 
            
        stored_hashed_password = result[0]
        
        # 使用 bcrypt 校验密码
        return bcrypt.checkpw(login_pass_plaintext.encode('utf-8'), 
                              stored_hashed_password.encode('utf-8'))

    except Exception as e:
        QMessageBox.critical(None, "登录验证错误", f"登录验证时发生错误。\n错误: {e}")
        return False


# --- PyQt6 应用程序类 ---

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # 1. 设置固定路径 (使用 get_base_dir 确定的外部路径)
        self.db_path = FIXED_DB_PATH
        
        self.setWindowTitle(f"弘盛非洲仓库管理系统 - {DB_NAME} 登录")
        self.setFixedSize(480, 410) 
        
        # [使用 get_resource_path 加载内部资源]
        self.setWindowIcon(QIcon(get_resource_path(LOGO_FILENAME)))

        self.main_window = None 

        # 2. 确保 db 文件夹存在 (使用 get_base_dir 确定的外部路径)
        self.ensure_db_folder_exists()
        
        self.settings = QSettings("WarehouseSystem", "Login") 
        
        self.entries = {}
        self.init_ui()
        self.load_settings()

    def ensure_db_folder_exists(self):
        """检查并创建 db 文件夹 (使用 FIXED_DB_PATH 的目录)"""
        db_folder = os.path.dirname(self.db_path)
        if not os.path.exists(db_folder):
            try:
                os.makedirs(db_folder)
                print(f"数据库目录创建成功: {db_folder}") 
            except OSError as e:
                QMessageBox.critical(self, "严重错误", f"无法创建数据库目录: {db_folder}\n错误: {e}")
                sys.exit(1)


    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0) 

        # --- 顶部横幅图片区域 ---
        banner_label = QLabel()
        # [使用 get_resource_path 加载内部资源]
        banner_path = get_resource_path(BANNER_FILENAME) 
        
        if os.path.exists(banner_path):
            pixmap = QPixmap(banner_path)
            # 缩放横幅以适应窗口宽度 (480 像素宽，固定高度如 60 像素)
            banner_label.setPixmap(pixmap.scaled(
                480, 60, 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            ))
            banner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            banner_label.setFixedHeight(60) 
        else:
            banner_label.setText("Honsen Africa WMS | 弘盛非洲仓库管理系统")
            banner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            banner_label.setFixedHeight(60)
            banner_label.setStyleSheet("background-color: #3f51b5; color: white; font-size: 14pt; font-weight: bold;")
            
        main_layout.addWidget(banner_label)
        # ----------------------------

        # --- 登录表单内容区域 ---
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 10, 20, 20) 

        grid = QGridLayout()
        grid.setSpacing(10)
        
        row = 0
        
        # ... (以下代码与之前版本保持一致)
        
        # --- 数据库文件配置标题 ---
        db_title = QLabel("--- 数据库文件配置 (固定路径) ---")
        db_title.setStyleSheet("font-weight: bold; margin-top: 10px;")
        grid.addWidget(db_title, row, 0, 1, 3)
        row += 1

        # --- 固定的数据库文件名称 ---
        grid.addWidget(QLabel("数据库文件:"), row, 0, Qt.AlignmentFlag.AlignLeft)
        self.entries['db_name'] = QLineEdit(DB_FILE)
        self.entries['db_name'].setReadOnly(True)
        self.entries['db_name'].setStyleSheet("background-color: #f0f0f0; font-weight: bold; color: #3F51B5;")
        grid.addWidget(self.entries['db_name'], row, 1)
        grid.addWidget(QLabel("（位于/db/）"), row, 2)
        row += 1

        # --- 固定的完整路径显示 ---
        grid.addWidget(QLabel("完整路径:"), row, 0, Qt.AlignmentFlag.AlignLeft)
        self.entries['db_path'] = QLineEdit(self.db_path) 
        self.entries['db_path'].setReadOnly(True)
        self.entries['db_path'].setStyleSheet("background-color: #f0f0f0; font-size: 8pt; color: #555;")
        grid.addWidget(self.entries['db_path'], row, 1, 1, 2)
        row += 1
        
        # --- 分隔符和用户登录标题 ---
        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.Shape.HLine)
        separator_line.setFrameShadow(QFrame.Shadow.Sunken)
        grid.addWidget(separator_line, row, 0, 1, 3)
        row += 1
        
        user_title = QLabel("--- 系统登录验证 ---")
        user_title.setStyleSheet("font-weight: bold; margin-top: 10px;")
        grid.addWidget(user_title, row, 0, 1, 3)
        row += 1

        # --- 用户名和密码字段 ---
        login_fields = [
            ("登录账号 (Username):", 'login_user', False),
            ("登录密码 (Password):", 'login_pass', True)
        ]
        
        for label_text, key, is_password in login_fields:
            label = QLabel(label_text)
            entry = QLineEdit()
            
            if is_password:
                entry.setEchoMode(QLineEdit.EchoMode.Password)
            
            self.entries[key] = entry
            
            grid.addWidget(label, row, 0, Qt.AlignmentFlag.AlignLeft)
            grid.addWidget(entry, row, 1)
            grid.addWidget(QLabel(""), row, 2) 
            row += 1
            
        content_layout.addLayout(grid)

        # --- 底部按钮区域 ---
        db_action_layout = QHBoxLayout()
        db_action_layout.setSpacing(15)
        
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.test_connection_action)
        self.test_btn.setMinimumHeight(35)
        
        self.init_btn = QPushButton("初始化数据库")
        self.init_btn.clicked.connect(self.initialize_action)
        self.init_btn.setMinimumHeight(35)
        self.init_btn.setStyleSheet("background-color: #f7d358; color: black; font-weight: bold;") 
        
        db_action_layout.addWidget(self.test_btn)
        db_action_layout.addWidget(self.init_btn)
        content_layout.addLayout(db_action_layout)
        content_layout.addSpacing(10)
        
        self.login_btn = QPushButton("登录系统")
        self.login_btn.clicked.connect(self.login_action)
        self.login_btn.setMinimumHeight(45)
        self.login_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; font-size: 14pt;") 
        content_layout.addWidget(self.login_btn)
        
        content_layout.addStretch(1)
        
        main_layout.addWidget(content_widget) 


    # --- 配置读取/保存 ---
    
    def load_settings(self):
        """加载配置 (仅加载用户登录信息)"""
        self.entries['login_user'].setText(
            self.settings.value("user/username", DEFAULT_LOGIN_USER, type=str)
        )

    def save_settings(self):
        """保存配置 (仅保存用户登录信息)"""
        self.settings.setValue("user/username", self.entries['login_user'].text())
        self.settings.sync()
    
    
    # --- 动作 ---
    
    def test_connection_action(self):
        """测试数据库连接：仅验证文件路径是否正确且可连接。"""
        db_path = self.db_path 
        conn = get_db_connection(db_path, create_if_missing=False) 
        
        if conn:
            conn.close()
            QMessageBox.information(
                self, 
                "数据库连接测试成功", 
                f"文件路径 **{db_path}** 连接成功！"
            )

    def initialize_action(self):
        """初始化动作：允许创建文件，然后创建表和用户。"""
        db_path = self.db_path
        conn = get_db_connection(db_path, create_if_missing=True) 
        if conn:
            try:
                initialize_all_schema(conn)
            finally:
                conn.close()


    def login_action(self):
        """登录操作"""
        db_path = self.db_path
        login_user = self.entries['login_user'].text()
        login_pass = self.entries['login_pass'].text()
        
        if not login_user or not login_pass:
            QMessageBox.warning(self, "登录警告", "登录账号和密码不能为空！")
            return

        conn = get_db_connection(db_path, create_if_missing=False) 
        if not conn:
            return

        if validate_user_login(conn, login_user, login_pass):
            conn.close()
            
            self.save_settings()
            QMessageBox.information(self, "登录成功", f"欢迎回来, {login_user}！正在启动系统...")
            
            try:
                self.main_window = MainWindow(db_path=db_path) 
                self.main_window.show()
                self.close()
                
            except NameError:
                QMessageBox.critical(self, "启动错误", "无法找到主类 'MainWindow'。请确保 main.py 中定义了该类，且已正确导入。")
            except Exception as e:
                QMessageBox.critical(self, "启动错误", f"无法启动主程序: {e}")
                
        else:
            conn.close()
            QMessageBox.critical(self, "登录失败", "登录账号或密码错误。")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())
