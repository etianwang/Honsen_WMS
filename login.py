# login.py，config表只有id，category和value三个键
# 仓库管理系统的登录界面和数据库初始化逻辑。

import sys
import os
import sqlite3
import hashlib
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox,
    QFrame
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QPixmap, QIcon
from main import MainWindow

import db_manager
from theme.loader import setup_app_theme, apply_widget_role

# --- 配置和常量 ---
DB_NAME = 'honsen_storage'
DB_FILE = f'{DB_NAME}.db'
DEFAULT_LOGIN_USER = 'Honsen_Admin'
DEFAULT_LOGIN_PASS_PLAINTEXT = '66778899HONSEN'

LOGO_FILENAME = 'logo.png'
BANNER_FILENAME = 'banner.png'
DB_FOLDER = 'db'


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
FIXED_DB_PATH = os.path.join(BASE_DIR, DB_FOLDER, DB_FILE)


def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def get_db_connection(db_path, create_if_missing=False):
    try:
        if not db_path:
            db_path = DB_FILE

        file_exists = os.path.exists(db_path)

        if not file_exists and not create_if_missing:
            QMessageBox.critical(
                None, "数据库连接错误",
                f"数据库文件 '{db_path}' 不存在。请点击 '初始化数据库' 按钮创建。"
            )
            return None

        return sqlite3.connect(db_path)

    except Exception as e:
        QMessageBox.critical(None, "数据库连接错误", f"无法连接数据库文件 '{db_path}'。\n错误: {e}")
        return None


def initialize_all_schema(conn):
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_user'")
        if cursor.fetchone() is not None:
            cursor.close()
            QMessageBox.information(
                None, "初始化提示",
                "数据库已存在，并非新数据库。跳过创建。\n(如需重置，请手动删除 db 文件夹下的 .db 文件)"
            )
            return

        cursor.execute("""
            CREATE TABLE admin_user (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
        """)

        hashed_pass = hashlib.sha256(DEFAULT_LOGIN_PASS_PLAINTEXT.encode('utf-8')).hexdigest()
        cursor.execute(
            "INSERT INTO admin_user (username, password) VALUES (?, ?)",
            (DEFAULT_LOGIN_USER, hashed_pass)
        )

        cursor.execute("""
            CREATE TABLE Inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                reference TEXT NOT NULL,
                category TEXT,
                domain TEXT,
                unit TEXT,
                current_stock INTEGER DEFAULT 0,
                min_stock INTEGER DEFAULT 0,
                location TEXT,
                cabinet TEXT DEFAULT ''
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('IN', 'OUT', 'REVERSAL-IN', 'REVERSAL-OUT')),
                quantity INTEGER NOT NULL,
                recipient_source TEXT,
                project_ref TEXT,
                FOREIGN KEY (item_id) REFERENCES Inventory(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                UNIQUE(category, value)
            );
        """)

        default_locations = ["基地仓库", "大仓库", "别墅", "办公楼", "公寓", "其他"]
        for loc in default_locations:
            cursor.execute("INSERT OR IGNORE INTO config (category, value) VALUES (?, ?)", ('LOCATION', loc))

        default_projects = ["日常维护", "别墅", "办公楼", "公寓", "基地", "通用"]
        for proj in default_projects:
            cursor.execute("INSERT OR IGNORE INTO config (category, value) VALUES (?, ?)", ('PROJECT', proj))

        default_units = ["个", "件", "套", "米", "卷", "箱", "KG", "升", "桶", "其他"]
        for unit in default_units:
            cursor.execute("INSERT OR IGNORE INTO config (category, value) VALUES (?, ?)", ('UNIT', unit))

        default_categories = [
            "办公用品", "工具耗材", "安防劳保", "电器设备", "建筑材料",
            "油漆涂料", "五金件", "管件", "电缆线材", "其他"
        ]
        for cat in default_categories:
            cursor.execute("INSERT OR IGNORE INTO config (category, value) VALUES (?, ?)", ('CATEGORY', cat))

        default_domains = ["强电", "弱电", "给排水", "暖通", "土建", "精装", "其他"]
        for dom in default_domains:
            cursor.execute("INSERT OR IGNORE INTO config (category, value) VALUES (?, ?)", ('DOMAIN', dom))

        conn.commit()
        cursor.close()

        msg = (
            f"所有表格已创建成功！\n\n"
            f"✅ 默认管理员账号：{DEFAULT_LOGIN_USER}\n"
            f"✅ 默认密码：{DEFAULT_LOGIN_PASS_PLAINTEXT}"
        )
        QMessageBox.information(None, "初始化成功", msg)

    except Exception as e:
        conn.rollback()
        cursor.close()
        QMessageBox.critical(None, "初始化失败", f"创建表格时发生错误。\n错误内容：{e}")
        import traceback
        traceback.print_exc()


def validate_user_login(conn, login_user, login_pass_plaintext):
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_user'")
        if cursor.fetchone() is None:
            QMessageBox.critical(None, "登录失败", "数据库未初始化，请先点击 '初始化数据库' 按钮。")
            return False

        cursor.execute("SELECT password FROM admin_user WHERE username = ?", (login_user,))
        result = cursor.fetchone()
        cursor.close()

        if not result:
            return False

        computed_hash = hashlib.sha256(login_pass_plaintext.encode('utf-8')).hexdigest()
        return computed_hash == result[0].strip()

    except Exception as e:
        QMessageBox.critical(None, "登录验证错误", f"登录验证时发生错误。\n错误: {e}")
        import traceback
        traceback.print_exc()
        return False


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.db_path = FIXED_DB_PATH
        self.setObjectName("loginWindow")
        self.setWindowTitle(f"弘盛非洲仓库管理系统 - {DB_NAME} 登录")
        self.setFixedSize(440, 480)
        self.setWindowIcon(QIcon(get_resource_path(LOGO_FILENAME)))

        self.main_window = None
        self.ensure_db_folder_exists()
        self.settings = QSettings("WarehouseSystem", "Login")
        self.entries = {}
        self.init_ui()
        self.load_settings()

    def ensure_db_folder_exists(self):
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
        main_layout.setSpacing(0)

        # --- 顶部品牌横幅 ---
        banner = QLabel()
        banner.setObjectName("loginBanner")
        banner_path = get_resource_path(BANNER_FILENAME)

        if os.path.exists(banner_path):
            pixmap = QPixmap(banner_path)
            banner.setPixmap(pixmap.scaled(
                440, 56,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            banner.setText("Honsen Africa WMS | 弘盛非洲仓库管理系统")

        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner.setFixedHeight(56)
        main_layout.addWidget(banner)

        # --- 居中登录卡片 ---
        outer = QVBoxLayout()
        outer.setContentsMargins(24, 20, 24, 20)

        card = QFrame()
        card.setObjectName("loginCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(12)

        title = QLabel("系统登录")
        title.setObjectName("loginTitle")
        subtitle = QLabel("弘盛非洲机电仓库管理系统")
        subtitle.setObjectName("loginSubtitle")
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(8)

        user_label = QLabel("登录账号")
        user_label.setObjectName("fieldLabel")
        self.entries['login_user'] = QLineEdit()
        self.entries['login_user'].setPlaceholderText("请输入登录账号")
        card_layout.addWidget(user_label)
        card_layout.addWidget(self.entries['login_user'])

        pass_label = QLabel("登录密码")
        pass_label.setObjectName("fieldLabel")
        self.entries['login_pass'] = QLineEdit()
        self.entries['login_pass'].setEchoMode(QLineEdit.EchoMode.Password)
        self.entries['login_pass'].setPlaceholderText("请输入登录密码")
        card_layout.addWidget(pass_label)
        card_layout.addWidget(self.entries['login_pass'])

        card_layout.addSpacing(4)

        db_action_layout = QHBoxLayout()
        db_action_layout.setSpacing(10)

        self.test_btn = QPushButton("测试连接")
        apply_widget_role(self.test_btn, "outline")
        self.test_btn.clicked.connect(self.test_connection_action)

        self.init_btn = QPushButton("初始化数据库")
        apply_widget_role(self.init_btn, "warning")
        self.init_btn.clicked.connect(self.initialize_action)

        db_action_layout.addWidget(self.test_btn)
        db_action_layout.addWidget(self.init_btn)
        card_layout.addLayout(db_action_layout)

        self.login_btn = QPushButton("登录系统")
        apply_widget_role(self.login_btn, "loginPrimary")
        self.login_btn.clicked.connect(self.login_action)
        card_layout.addWidget(self.login_btn)

        db_hint = QLabel(f"数据库: {self.db_path}")
        db_hint.setObjectName("loginDbHint")
        db_hint.setWordWrap(True)
        card_layout.addWidget(db_hint)

        outer.addWidget(card)
        main_layout.addLayout(outer)

    def load_settings(self):
        self.entries['login_user'].setText(
            self.settings.value("user/username", DEFAULT_LOGIN_USER, type=str)
        )

    def save_settings(self):
        self.settings.setValue("user/username", self.entries['login_user'].text())
        self.settings.sync()

    def test_connection_action(self):
        conn = get_db_connection(self.db_path, create_if_missing=False)
        if conn:
            conn.close()
            QMessageBox.information(
                self, "数据库连接测试成功",
                f"文件路径连接成功！\n{self.db_path}"
            )

    def initialize_action(self):
        conn = get_db_connection(self.db_path, create_if_missing=True)
        if conn:
            try:
                initialize_all_schema(conn)
            finally:
                conn.close()

    def login_action(self):
        login_user = self.entries['login_user'].text()
        login_pass = self.entries['login_pass'].text()

        if not login_user or not login_pass:
            QMessageBox.warning(self, "登录警告", "登录账号和密码不能为空！")
            return

        conn = get_db_connection(self.db_path, create_if_missing=False)
        if not conn:
            return

        if validate_user_login(conn, login_user, login_pass):
            conn.close()
            print("🔧 正在配置数据库并发模式 (WAL)...")
            db_manager.enable_wal_mode(self.db_path)

            self.save_settings()
            QMessageBox.information(self, "登录成功", f"欢迎回来, {login_user}！正在启动系统...")

            try:
                self.main_window = MainWindow(db_path=self.db_path)
                self.main_window.show()
                self.close()
            except NameError:
                QMessageBox.critical(
                    self, "启动错误",
                    "无法找到主类 'MainWindow'。请确保 main.py 中定义了该类，且已正确导入。"
                )
            except Exception as e:
                QMessageBox.critical(self, "启动错误", f"无法启动主程序: {e}")
        else:
            conn.close()
            QMessageBox.critical(self, "登录失败", "登录账号或密码错误。")


if __name__ == '__main__':
    if not os.environ.get('QT_SCALE_FACTOR'):
        os.environ['QT_SCALE_FACTOR'] = '1.0'

    app = QApplication(sys.argv)
    setup_app_theme(app)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())
