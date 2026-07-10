import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QStackedWidget, QLabel,
    QFrame, QMessageBox, QToolButton, QGraphicsOpacityEffect,
    QDialog
)
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QPixmap, QIcon, QDesktopServices

from inventory_page import InventoryPage
from transaction_page import TransactionPage
from settings_widget import SettingsWidget

LOGO_FILENAME = 'logo.png'


def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class QRCodeTooltip(QDialog):
    def __init__(self, parent=None, image_path=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel()
        self.label.setObjectName("qrLabel")
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path).scaled(
                200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.label.setPixmap(pixmap)
        else:
            self.label.setText("二维码图片未找到\n请放置 wechat_qr.png\n在项目根目录")
            self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.label)

        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.95)
        self.setGraphicsEffect(effect)

    def show_at(self, pos):
        self.move(pos.x() - 260, pos.y() - 50)
        self.show()


class MainWindow(QMainWindow):

    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.setWindowTitle("仓库管理系统 (Honsen Africa CI) - 主程序")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon(get_resource_path(LOGO_FILENAME)))
        self.init_ui()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_h_layout = QHBoxLayout(self.central_widget)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)
        self.main_h_layout.setSpacing(0)

        self.create_sidebar()

        self.stacked_widget = QStackedWidget()
        self.main_h_layout.addWidget(self.stacked_widget)

        self.create_pages()

        self.statusBar().showMessage(
            f"数据库连接路径: {self.db_path} | 仅限弘盛非洲机电仓管人员使用 | 有需求或bug找王一健。"
        )

        self.show_page(0)

    def create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)

        v_layout = QVBoxLayout(sidebar)
        v_layout.setContentsMargins(12, 20, 12, 12)
        v_layout.setSpacing(8)

        logo_label = QLabel()
        logo_label.setObjectName("logoLabel")
        logo_path = get_resource_path(LOGO_FILENAME)

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo_label.setPixmap(pixmap.scaled(
                160, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logo_label.setText("HONSEN")
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        v_layout.addWidget(logo_label)
        v_layout.addSpacing(16)

        self.nav_buttons = []
        pages = ["库存管理", "交易记录", "系统设置"]

        for i, name in enumerate(pages):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, index=i: self.show_page(index))
            v_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        v_layout.addStretch(1)

        contact_frame = QFrame()
        contact_layout = QHBoxLayout(contact_frame)
        contact_layout.setContentsMargins(0, 0, 0, 10)
        contact_layout.setSpacing(10)
        contact_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_github = QToolButton()
        github_path = get_resource_path("github.svg")
        if os.path.exists(github_path):
            self.btn_github.setIcon(QIcon(github_path))
            self.btn_github.setIconSize(QSize(14, 14))
        else:
            self.btn_github.setText("GH")
        self.btn_github.setToolTip("访问 GitHub 主页")
        self.btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/etianwang")))
        contact_layout.addWidget(self.btn_github)

        self.btn_telegram = QToolButton()
        tg_path = get_resource_path("telegram.svg")
        if os.path.exists(tg_path):
            self.btn_telegram.setIcon(QIcon(tg_path))
            self.btn_telegram.setIconSize(QSize(14, 14))
        else:
            self.btn_telegram.setText("TG")
        self.btn_telegram.setToolTip("通过 Telegram 联系")
        self.btn_telegram.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://t.me/etienne_wang")))
        contact_layout.addWidget(self.btn_telegram)

        self.btn_wechat = QToolButton()
        wx_path = get_resource_path("wechat.svg")
        if os.path.exists(wx_path):
            self.btn_wechat.setIcon(QIcon(wx_path))
            self.btn_wechat.setIconSize(QSize(14, 14))
        else:
            self.btn_wechat.setText("WX")
        self.btn_wechat.setToolTip("悬停查看微信二维码")

        qr_image_path = get_resource_path('wechat_qr.png')
        self.wechat_tooltip = QRCodeTooltip(self, qr_image_path)
        self.wechat_tooltip.hide()

        self.btn_wechat.enterEvent = lambda e: self._show_wechat_qr(e)
        self.btn_wechat.leaveEvent = lambda e: self._hide_wechat_qr(e)
        contact_layout.addWidget(self.btn_wechat)

        v_layout.addWidget(contact_frame)

        line = QFrame()
        line.setObjectName("sidebarDivider")
        line.setFrameShape(QFrame.Shape.HLine)
        v_layout.addWidget(line)

        copyright_label = QLabel("Ver 2026.03\nAuthor: Etienne")
        copyright_label.setObjectName("copyrightLabel")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(copyright_label)

        self.main_h_layout.addWidget(sidebar)

    def create_pages(self):
        self.inventory_page = InventoryPage(self.db_path)
        self.stacked_widget.addWidget(self.inventory_page)

        self.transaction_page = TransactionPage(
            db_path=self.db_path,
            inventory_page_ref=self.inventory_page
        )
        self.stacked_widget.addWidget(self.transaction_page)

        self.settings_page = SettingsWidget(self.db_path)
        self.stacked_widget.addWidget(self.settings_page)

    def show_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def _show_wechat_qr(self, event):
        global_pos = self.btn_wechat.mapToGlobal(self.btn_wechat.rect().topRight())
        self.wechat_tooltip.show_at(global_pos)
        try:
            super(QToolButton, self.btn_wechat).enterEvent(event)
        except Exception:
            pass

    def _hide_wechat_qr(self, event):
        self.wechat_tooltip.hide()
        try:
            super(QToolButton, self.btn_wechat).leaveEvent(event)
        except Exception:
            pass

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            '确认退出',
            "您确定要退出仓库管理系统吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
