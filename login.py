# login.py，config表只有id，category和value三个键
# 仓库管理系统的登录界面和数据库初始化逻辑。
#打包指令：pyinstaller --noconfirm --onefile --windowed --icon "logo.ico" --add-data "logo.png;." --add-data "wechat_qr.png;." --add-data "github.svg;." --add-data "telegram.svg;." --add-data "wechat.svg;." --name "Honsen_WMS" login.py

import sys
import os
import sqlite3
import hashlib
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QMessageBox, 
    QGridLayout, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QPixmap, QIcon 
from main import MainWindow # 导入 MainWindow 类
from qt_material import apply_stylesheet
import db_manager  # <--- 确保有这一行，用于调用 enable_wal_mode

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
    """
    if getattr(sys, 'frozen', False):
        # 打包环境
        return os.path.dirname(sys.executable)
    else:
        # 开发环境
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()

# 固定的完整数据库路径：[EXE 所在目录]/db/honsen_storage.db
FIXED_DB_PATH = os.path.join(BASE_DIR, DB_FOLDER, DB_FILE)
# --- END 数据库路径固定 ---


# --- 2. 内部资源路径处理函数 (用于图片文件) ---
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
# --- END 资源路径处理函数 ---


# --- 数据库操作：基础连接和工具函数 ---

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

# def hash_password(password_plaintext):
#     """使用 bcrypt 对明文密码进行哈希"""
#     return bcrypt.hashpw(password_plaintext.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# --- 业务表初始化逻辑 (已修复插入语句) ---

def initialize_all_schema(conn):
    """
    检查并创建所有表 (admin_user, Inventory, Transactions, config)，并插入默认管理员账号和配置。
    【已更新】Inventory 表增加了 cabinet 和 initial_cabinet 字段。
    【已更新】密码加密逻辑与 db_manager.py 保持一致 (SHA256)，防止冲突。
    """
    cursor = conn.cursor()
    
    try:
        # 1. 检查 admin_user 表是否存在 (作为是否为新表的判断依据)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_user'")
        if cursor.fetchone() is not None:
            cursor.close()
            QMessageBox.information(None, "初始化提示", "数据库已存在，并非新数据库。跳过创建。\n(如需重置，请手动删除 db 文件夹下的 .db 文件)")
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
        # 【重要修改】为了与 db_manager.py 兼容，这里改用 SHA256 哈希 (原代码使用 bcrypt)
        # 如果您希望全程使用 bcrypt，请确保 db_manager.py 也改为 bcrypt
        import hashlib
        default_pass = DEFAULT_LOGIN_PASS_PLAINTEXT
        hashed_pass = hashlib.sha256(default_pass.encode('utf-8')).hexdigest()
        
        cursor.execute("INSERT INTO admin_user (username, password) VALUES (?, ?)", 
                             (DEFAULT_LOGIN_USER, hashed_pass))
        
        # C. Inventory 表 (库存物品) - 【核心修改点】
        cursor.execute("""
            CREATE TABLE Inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                reference TEXT NOT NULL,
                category TEXT,
                domain TEXT,
                unit TEXT,
                current_stock REAL DEFAULT 0,
                min_stock REAL DEFAULT 0,
                location TEXT,
                cabinet TEXT DEFAULT ''          -- 【新增】当前柜号
            )
        """)
        
        # D. Transactions 表 (交易记录) 
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('IN', 'OUT', 'REVERSAL-IN', 'REVERSAL-OUT')), 
                quantity REAL NOT NULL,
                recipient_source TEXT,
                project_ref TEXT,
                FOREIGN KEY (item_id) REFERENCES Inventory(id)
            )
        """)
        
        # E. Config 表 (存放自定义配置)
        cursor.execute("""
            CREATE TABLE config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                UNIQUE(category, value)
            );
        """)

        # F. 插入默认存放位置选项
        default_locations = ["基地仓库", "大仓库", "别墅", "办公楼", "公寓", "其他"]
        for loc in default_locations:
            cursor.execute("INSERT OR IGNORE INTO config (category, value) VALUES (?, ?)", ('LOCATION', loc))
            
        # G. 插入默认项目选项
        default_projects = ["日常维护", "别墅", "办公楼", "公寓", "基地", "通用"]
        for proj in default_projects:
            cursor.execute("INSERT OR IGNORE INTO config (category, value) VALUES (?, ?)", ('PROJECT', proj))

        # H. 插入默认单位选项
        default_units = ["个", "件", "套", "米", "卷", "箱", "KG", "升", "桶", "其他"]
        for unit in default_units:
            cursor.execute("INSERT OR IGNORE INTO config (category, value) VALUES (?, ?)", ('UNIT', unit))

        # I. 插入默认材料类别选项
        default_categories = ["办公用品", "工具耗材", "安防劳保", "电器设备", "建筑材料", "油漆涂料", "五金件", "管件", "电缆线材", "其他"]
        for cat in default_categories:
            cursor.execute("INSERT OR IGNORE INTO config (category, value) VALUES (?, ?)", ('CATEGORY', cat))
            
        # J. 插入默认专业类别选项 
        default_domains = ["强电", "弱电", "给排水", "暖通", "土建", "精装", "其他"]
        for dom in default_domains:
            cursor.execute("INSERT OR IGNORE INTO config (category, value) VALUES (?, ?)", ('DOMAIN', dom))
            
        
        conn.commit()
        cursor.close()
        
        msg = (f"所有表格已创建成功！\n\n"
               f"✅ Inventory 表已包含：cabinet, initial_cabinet 字段\n"
               f"✅ 默认管理员账号：{DEFAULT_LOGIN_USER}\n"
               f"✅ 默认密码：{DEFAULT_LOGIN_PASS_PLAINTEXT}")
               
        QMessageBox.information(None, "初始化成功", msg)
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        QMessageBox.critical(None, "初始化失败", f"创建表格时发生错误。\n错误内容：{e}")
        import traceback
        traceback.print_exc()
# --- 登录验证 (应用层验证) (保持不变) ---

def validate_user_login(conn, login_user, login_pass_plaintext):
    """在 admin_user 表中验证登录账号和明文密码 (使用 SHA-256)。"""
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
        
        # ✅ 【修改点】使用 SHA-256 进行验证
        # 逻辑：将用户输入的密码直接进行 SHA-256 哈希，然后与数据库中的哈希值比对
        # 注意：你的初始化代码里没有加盐，所以这里也不加盐，保持绝对一致
        computed_hash = hashlib.sha256(login_pass_plaintext.encode('utf-8')).hexdigest()
        
        # 比对哈希值 (去除可能的首尾空格)
        if computed_hash == stored_hashed_password.strip():
            return True
        else:
            return False

    except Exception as e:
        QMessageBox.critical(None, "登录验证错误", f"登录验证时发生错误。\n错误: {e}")
        import traceback
        traceback.print_exc()
        return False


# --- PyQt6 应用程序类 (保持不变) ---

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # 1. 设置固定路径 (使用 get_base_dir 确定的外部路径)
        self.db_path = FIXED_DB_PATH
        
        self.setWindowTitle(f"弘盛非洲仓库管理系统 - {DB_NAME} 登录")
        self.setFixedSize(480, 450) 
        
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

    def change_theme(self, theme_name):
        """动态切换主题"""
        # 注意：这里需要能访问到全局的 app 实例
        # 我们可以通过 QApplication.instance() 获取
        app = QApplication.instance()
        if app:
            apply_stylesheet(app, theme=theme_name)
    def change_theme(self):
        """动态切换主题，通过 currentData() 获取文件名"""
        theme_file = self.theme_combo.currentData()
        if theme_file:
            print(f"正在切换主题: {theme_file}")
            app = QApplication.instance()
            if app:
                apply_stylesheet(app, theme=theme_file)
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
            banner_label.setStyleSheet("")
            
        main_layout.addWidget(banner_label)
        # ----------------------------

        # --- 登录表单内容区域 ---
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 10, 20, 20) 

        grid = QGridLayout()
        grid.setSpacing(10)
        
        row = 0
        
        # --- 数据库文件配置标题 ---
        db_title = QLabel("--- 数据库文件配置 (固定路径) ---")
        db_title.setStyleSheet("font-weight: bold; margin-top: 10px;")
        grid.addWidget(db_title, row, 0, 1, 3)
        row += 1

        # --- 固定的数据库文件名称 ---
        grid.addWidget(QLabel("数据库文件:"), row, 0, Qt.AlignmentFlag.AlignLeft)
        self.entries['db_name'] = QLineEdit(DB_FILE)
        self.entries['db_name'].setReadOnly(True)
        self.entries['db_name'].setStyleSheet("")
        grid.addWidget(self.entries['db_name'], row, 1)
        grid.addWidget(QLabel("（位于/db/）"), row, 2)
        row += 1

        # --- 固定的完整路径显示 ---
        grid.addWidget(QLabel("完整路径:"), row, 0, Qt.AlignmentFlag.AlignLeft)
        self.entries['db_path'] = QLineEdit(self.db_path) 
        self.entries['db_path'].setReadOnly(True)
        self.entries['db_path'].setStyleSheet("")
        grid.addWidget(self.entries['db_path'], row, 1, 1, 2)
        row += 1
        
        # --- 分隔符和用户登录标题 ---
        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.Shape.NoFrame) # 强制无边框
        separator_line.setStyleSheet("border: none;")      # 强制 CSS 移除边框
        separator_line.setFrameShape(QFrame.Shape.HLine)
        separator_line.setFrameShadow(QFrame.Shadow.Sunken)
        grid.addWidget(separator_line, row, 0, 1, 3)
        row += 1
        
        user_title = QLabel("--- 系统登录验证 ---")
        user_title.setStyleSheet("font-weight: bold; margin-top: 10px;")
        grid.addWidget(user_title, row, 0, 1, 3)
        row += 1

        # --- 新增：主题选择区域 ---
        theme_layout = QHBoxLayout()
        theme_label = QLabel("选择主题:")

        # 1. 定义显示名称到文件名的映射字典
        self.theme_map = {
            '深色-琥珀': 'dark_amber.xml',
            '深色-蓝': 'dark_blue.xml',
            '深色-青': 'dark_cyan.xml',
            '深色-浅绿': 'dark_lightgreen.xml',
            '深色-粉': 'dark_pink.xml',
            '深色-紫': 'dark_purple.xml',
            '深色-红': 'dark_red.xml',
            '深色-蓝绿': 'dark_teal.xml',
            '深色-黄': 'dark_yellow.xml',
            '浅色-琥珀': 'light_amber.xml',
            '浅色-蓝': 'light_blue.xml',
            '浅色-青': 'light_cyan.xml',
            '浅色-青(500)': 'light_cyan_500.xml',
            '浅色-浅绿': 'light_lightgreen.xml',
            '浅色-粉': 'light_pink.xml',
            '浅色-紫': 'light_purple.xml',
            '浅色-红': 'light_red.xml',
            '浅色-蓝绿': 'light_teal.xml',
            '浅色-黄': 'light_yellow.xml'
        }

        self.theme_combo = QComboBox()

        # 2. 将数据添加到下拉框
        for display_name, file_name in self.theme_map.items():
            self.theme_combo.addItem(display_name, file_name)

        # 3. 设置默认值
        self.theme_combo.setCurrentText("浅色-蓝")

        # 4. 连接信号
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        content_layout.addLayout(theme_layout)

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
                # 🔴 新增：按下回车键时触发登录
                entry.returnPressed.connect(self.login_action)
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
        self.init_btn.setStyleSheet("") 
        
        db_action_layout.addWidget(self.test_btn)
        db_action_layout.addWidget(self.init_btn)
        content_layout.addLayout(db_action_layout)
        content_layout.addSpacing(10)
        
        self.login_btn = QPushButton("登录系统")
        self.login_btn.clicked.connect(self.login_action)
        self.login_btn.setMinimumHeight(45)
        self.login_btn.setStyleSheet("") 
        content_layout.addWidget(self.login_btn)
        
        content_layout.addStretch(1)
        
        main_layout.addWidget(content_widget) 


    # --- 配置读取/保存 (保持不变) ---
    
    def load_settings(self):
        """加载配置 (仅加载用户登录信息)"""
        self.entries['login_user'].setText(
            self.settings.value("user/username", DEFAULT_LOGIN_USER, type=str)
        )

    def save_settings(self):
        """保存配置 (仅保存用户登录信息)"""
        self.settings.setValue("user/username", self.entries['login_user'].text())
        self.settings.sync()
    
    
    # --- 动作 (保持不变) ---
    
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

            # ✅【关键修改】调用 db_manager 中的函数开启 WAL 模式
            # 这能解决编辑保存后界面卡死的问题
            print("🔧 正在配置数据库并发模式 (WAL)...")
            db_manager.enable_wal_mode(db_path) 

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
    # 确保应用程序在运行之前设置了正确的环境
    if not os.environ.get('QT_SCALE_FACTOR'):
        os.environ['QT_SCALE_FACTOR'] = '1.0' # 确保默认缩放为 100%
        
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='light_blue.xml')
    # 2. 追加清理样式的 QSS，移除所有控件的硬边框
    clean_style = """
        /* 提升选择器权重：使用类名或更具体的容器来匹配按钮 */
        QPushButton {
            background-color: palette(button) !important; /* 强制指向系统调色板 */
            color: palette(button-text) !important;
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
        }
        QHeaderView::section {
            padding: 0px !important;    /* 把内边距设为0 */
            margin: 0px !important;     /* 把外边距设为0 */
            border: 1px solid #d3d3d3;  /* 如果需要边框，可以自己定义 */
            background-color: palette(button); /* 跟随你的主题背景 */
            text-align: center;         /* 文字居中 */
        }
        /* 如果按钮在悬停时颜色变了，也要重置 */
        QPushButton:hover {
            background-color: palette(midlight) !important;
        /* 强制缩小序号列的宽度 */
        QTableWidget QTableCornerButton::section, QTableWidget::verticalHeader {
            width: 30px !important;
            min-width: 30px !important;
            max-width: 30px !important;
        }
        
        /* 针对你代码中特别的颜色按钮（如添加/删除按钮），需要清空它们的硬编码样式 */
    """
    app.setStyleSheet(app.styleSheet() + clean_style + """
    QPushButton {
        padding: 6px 12px;
        border-radius: 4px;
    }
    QListWidget {
        background-color: palette(base);
        border: 1px solid palette(mid);
    }
    QLabel {
        color: palette(text);
    }
    """)
    window = LoginWindow()
    window.show()
    window.change_theme()
    sys.exit(app.exec())