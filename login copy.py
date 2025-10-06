import sys
import os
import subprocess
import sqlite3
import bcrypt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QMessageBox, 
    QGridLayout, QFrame, QFileDialog
)
from PyQt6.QtCore import Qt, QSettings

# --- 配置和常量 ---
# 数据库文件名称
DB_NAME = 'honsen_storage' 
DB_FILE = f'{DB_NAME}.db' 
# 默认管理员凭证
DEFAULT_LOGIN_USER = 'Honsen_Admin'
DEFAULT_LOGIN_PASS_PLAINTEXT = '66778899HONSEN' 

# 数据库地址输入框的默认值 (程序所在目录下的 db 文件)
DEFAULT_DB_PATH = os.path.join(os.getcwd(), DB_FILE)

# --- 数据库操作：基础连接和工具函数 ---

def get_db_connection(db_path, create_if_missing=False):
    """
    根据提供的路径建立 SQLite 连接。
    - create_if_missing=False (默认): 如果文件不存在，则返回 None 并报错（用于登录/测试）。
    - create_if_missing=True: 允许连接，如果文件不存在则创建（仅用于初始化）。
    """
    try:
        if not db_path:
             db_path = DB_FILE
        
        file_exists = os.path.exists(db_path)
        
        if not file_exists and not create_if_missing:
            QMessageBox.critical(None, "数据库连接错误", 
                                 f"数据库文件 '{db_path}' 不存在。请检查路径或点击 '初始化数据库' 按钮创建。")
            return None

        # 尝试连接。
        conn = sqlite3.connect(db_path)
        return conn
        
    except Exception as e:
        QMessageBox.critical(None, "数据库连接错误", f"无法连接数据库文件 '{db_path}'。\n错误: {e}")
        return None

def hash_password(password_plaintext):
    """使用 bcrypt 对明文密码进行哈希"""
    # 调整gensalt参数以控制强度（可选）
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
        self.setWindowTitle(f"仓库管理系统 - {DB_NAME} 登录")
        self.setGeometry(300, 300, 480, 350)
        self.setFixedSize(480, 350)

        # QSettings 用于保存用户上次的配置 (如数据库路径)
        self.settings = QSettings("WarehouseSystem", "Login") 
        
        self.entries = {}
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        grid = QGridLayout()
        grid.setSpacing(10)
        
        # 简化后的字段定义 (移除了数据库账号和密码)
        fields = [
            ("数据库名称:", 'db_name', False), 
            ("文件路径:", 'db_path', False),
            (None, None, None), # 分隔符占位
            ("登录账号 (Username):", 'login_user', False),
            ("登录密码 (Password):", 'login_pass', True)
        ]
        
        row = 0
        
        # --- 数据库文件配置标题 ---
        db_title = QLabel("--- 数据库文件配置 ---")
        db_title.setStyleSheet("font-weight: bold; margin-top: 10px;")
        grid.addWidget(db_title, row, 0, 1, 3)
        row += 1

        # --- 输入框布局 ---
        for label_text, key, is_password in fields:
            if key is None:
                # 添加分隔线和标题
                row += 1
                separator_line = QFrame()
                separator_line.setFrameShape(QFrame.Shape.HLine)
                separator_line.setFrameShadow(QFrame.Shadow.Sunken)
                grid.addWidget(separator_line, row, 0, 1, 3)
                
                row += 1
                user_title = QLabel("--- 系统登录验证 ---")
                user_title.setStyleSheet("font-weight: bold; margin-top: 10px;")
                grid.addWidget(user_title, row, 0, 1, 3)
                row += 1
                continue
            
            label = QLabel(label_text)
            entry = QLineEdit()
            
            if is_password:
                entry.setEchoMode(QLineEdit.EchoMode.Password)
            
            self.entries[key] = entry
            
            grid.addWidget(label, row, 0, Qt.AlignmentFlag.AlignLeft)
            grid.addWidget(entry, row, 1)

            if key == 'db_path':
                browse_btn = QPushButton("选择文件")
                browse_btn.setFixedWidth(100)
                browse_btn.clicked.connect(self.browse_file_action)
                grid.addWidget(browse_btn, row, 2)
            elif key == 'db_name':
                entry.setReadOnly(True)
                entry.setStyleSheet("background-color: #f0f0f0; font-weight: bold;")
                entry.setText(DB_FILE)
                grid.addWidget(QLabel("（固定）"), row, 2)
            else:
                 grid.addWidget(QLabel(""), row, 2)

            row += 1

        main_layout.addLayout(grid)

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
        main_layout.addLayout(db_action_layout)
        main_layout.addSpacing(10)
        
        self.login_btn = QPushButton("登录系统")
        self.login_btn.clicked.connect(self.login_action)
        self.login_btn.setMinimumHeight(45)
        self.login_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; font-size: 14pt;") 
        main_layout.addWidget(self.login_btn)
        
        main_layout.addStretch(1)


    # --- 配置读取/保存 ---
    
    def load_settings(self):
        """加载配置"""
        self.entries['db_path'].setText(
            self.settings.value("db/path", DEFAULT_DB_PATH, type=str)
        )
        self.entries['login_user'].setText(
            self.settings.value("user/username", DEFAULT_LOGIN_USER, type=str)
        )

    def save_settings(self):
        """保存配置"""
        self.settings.setValue("db/path", self.entries['db_path'].text())
        self.settings.setValue("user/username", self.entries['login_user'].text())
        self.settings.sync()
    
    
    # --- 动作 ---
    
    def browse_file_action(self):
        """打开文件选择对话框，用于选择或创建数据库文件路径"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "选择或创建数据库文件", 
            self.entries['db_path'].text(), 
            f"{DB_NAME} 数据库 (*.{DB_NAME}.db)"
        )
        
        if file_path:
            # 确保文件以 DB_FILE 结尾
            if not file_path.endswith(DB_FILE):
                if os.path.isdir(file_path):
                    final_path = os.path.join(file_path, DB_FILE)
                else:
                    final_path = os.path.join(os.path.dirname(file_path), DB_FILE)
            else:
                final_path = file_path
                
            self.entries['db_path'].setText(final_path)


    def test_connection_action(self):
        """测试数据库连接：仅验证文件路径是否正确且可连接。"""
        db_path = self.entries['db_path'].text()
        
        # 严格要求文件必须存在
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
        db_path = self.entries['db_path'].text()
        # 允许创建新文件
        conn = get_db_connection(db_path, create_if_missing=True) 
        if conn:
            try:
                initialize_all_schema(conn)
            finally:
                conn.close()


    def login_action(self):
        """登录操作"""
        db_path = self.entries['db_path'].text()
        login_user = self.entries['login_user'].text()
        login_pass = self.entries['login_pass'].text()
        
        if not login_user or not login_pass:
            QMessageBox.warning(self, "登录警告", "登录账号和密码不能为空！")
            return

        # 登录时，不允许文件不存在
        conn = get_db_connection(db_path, create_if_missing=False) 
        if not conn:
            return

        if validate_user_login(conn, login_user, login_pass):
            conn.close()
            
            self.save_settings()
            QMessageBox.information(self, "登录成功", f"欢迎回来, {login_user}！正在启动系统...")
            
            self.close() 
            
            try:
                # --- 关键修正：确保 main.py 启动路径正确 ---
                current_dir = os.path.dirname(os.path.abspath(__file__)) 
                main_py_path = os.path.join(current_dir, 'main.py')
                
                # 使用 main.py 的绝对路径，并将子进程的工作目录设置为当前目录
                subprocess.Popen([sys.executable, main_py_path, db_path], cwd=current_dir)
                sys.exit(0)
            except Exception as e:
                # 错误处理：检查文件路径
                if not os.path.exists(main_py_path):
                     QMessageBox.critical(self, "启动错误", f"无法启动 main.py: 目标路径 '{main_py_path}' 不存在。请检查文件是否与 login.py 在同一目录。\n原始错误: {e}")
                else:
                    QMessageBox.critical(self, "启动错误", f"无法启动 main.py: {e}")
                
        else:
            conn.close()
            QMessageBox.critical(self, "登录失败", "登录账号或密码错误。")


if __name__ == '__main__':
    # 检查 main.py 是否存在于预期路径
    main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py')
    if not os.path.exists(main_py_path):
        print(f"警告: main.py 文件不存在于预期目录: {os.path.dirname(os.path.abspath(__file__))}. 请确保它与 login.py 在同一路径下。")

    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())