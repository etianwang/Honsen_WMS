import sys
import os
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QStackedWidget, QLabel,
    QFrame, QMessageBox, QToolButton, QGraphicsOpacityEffect,
    QDialog
)
from PyQt6.QtCore import Qt, QSize, QUrl, QRect
from PyQt6.QtGui import QPixmap, QIcon, QDesktopServices, QPainter, QImage
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink, QVideoFrame

# 导入功能页面
from inventory_page import InventoryPage
from transaction_page import TransactionPage
from settings_widget import SettingsWidget

# --- 资源路径处理函数 ---
LOGO_FILENAME = 'logo.png'

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# --- 自定义悬浮二维码窗口类 ---
class QRCodeTooltip(QDialog):
    def __init__(self, parent=None, image_path=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel()
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path).scaled(
                200, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
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


# --- 视频背景侧边栏：用 QVideoSink 抓帧，在 paintEvent 里绘制 ---
# 这样视频完全是"画"在 widget 上的，不是原生子窗口，不会遮挡任何控件
class VideoSidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(140)
        self._current_image = None  # 当前视频帧（QImage）

        # 播放器 + 音频（静音）
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setMuted(True)
        self.media_player.setAudioOutput(self.audio_output)

        # QVideoSink：不渲染到任何窗口，只通过信号拿到每一帧
        self.video_sink = QVideoSink(self)
        self.media_player.setVideoOutput(self.video_sink)
        self.video_sink.videoFrameChanged.connect(self._on_frame)

    def load_and_play(self, video_path):
        self.media_player.setSource(QUrl.fromLocalFile(video_path))
        self.media_player.setLoops(-1)
        self.media_player.play()

    def _on_frame(self, frame: QVideoFrame):
        """每帧回调：转成 QImage 缓存，然后触发重绘"""
        if frame.isValid():
            img = frame.toImage()
            if not img.isNull():
                self._current_image = img
                self.update()   # 触发 paintEvent

    def paintEvent(self, event):
        """把当前帧拉伸绘制到整个 widget 区域"""
        painter = QPainter(self)
        if self._current_image:
            painter.drawImage(QRect(0, 0, self.width(), self.height()), self._current_image)
        else:
            # 视频未加载时画纯黑背景
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
        painter.end()


# --- 主窗口类 ---
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
        """侧边栏：VideoSidebar 画视频背景，内容控件直接放在上面"""

        # VideoSidebar 本身就是侧边栏容器，视频画在它的背景里
        self.sidebar = VideoSidebar()

        # 多个视频文件名，启动时随机选一个循环播放
        # 如需添加更多，继续往列表里加文件名即可
        video_files = [
            "sidebar_bg1.mp4",
            "sidebar_bg2.mp4",
        ]
        chosen = random.choice(video_files)
        video_path = get_resource_path(chosen)
        self.sidebar.load_and_play(video_path)

        # 内容布局直接设置在 VideoSidebar 上
        v_layout = QVBoxLayout(self.sidebar)
        v_layout.setContentsMargins(10, 20, 10, 10)
        v_layout.setSpacing(15)

        # Logo 区域
        logo_label = QLabel()
        logo_path = get_resource_path(LOGO_FILENAME)
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            logo_label.setPixmap(pixmap.scaled(
                120, 40,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logo_label.setText("HONSEN")
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setStyleSheet("color: white; font-weight: bold;")

        logo_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        v_layout.addWidget(logo_label)
        v_layout.addSpacing(10)

        # 导航按钮样式（半透明，让视频透出）
        btn_style = """
            QPushButton {
                background-color: rgba(92, 107, 192, 0.70);
                color: white;
                padding: 8px 5px;
                border: none;
                border-radius: 4px;
                text-align: left;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: rgba(121, 134, 203, 0.90);
            }
            QPushButton:checked {
                background-color: rgba(255, 152, 0, 0.90);
                font-weight: bold;
            }
        """

        self.nav_buttons = []
        pages = ["库存管理", "交易记录", "系统设置"]

        for i, name in enumerate(pages):
            btn = QPushButton(name)
            btn.setStyleSheet(btn_style)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, index=i: self.show_page(index))
            v_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        v_layout.addStretch(1)

        # ── 底部联系作者区域 ─────────────────────────────────────
        contact_frame = QFrame()
        contact_frame.setFrameShape(QFrame.Shape.NoFrame)
        contact_frame.setStyleSheet("background-color: transparent; border: none;")
        contact_frame.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        contact_layout = QHBoxLayout(contact_frame)
        contact_layout.setContentsMargins(0, 0, 0, 10)
        contact_layout.setSpacing(10)
        contact_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_btn_style = """
            QToolButton {
                background-color: rgba(121, 134, 203, 0.75);
                color: white;
                border: none;
                border-radius: 10px;
                width: 26px;
                height: 26px;
                padding: 0px;
            }
            QToolButton:hover {
                background-color: rgba(255, 152, 0, 0.90);
            }
        """

        # 1. GitHub 按钮
        self.btn_github = QToolButton()
        github_path = get_resource_path("github.svg")
        if os.path.exists(github_path):
            self.btn_github.setIcon(QIcon(github_path))
            self.btn_github.setIconSize(QSize(14, 14))
        else:
            self.btn_github.setText("GH")
        self.btn_github.setStyleSheet(icon_btn_style)
        self.btn_github.setToolTip("访问 GitHub 主页")
        self.btn_github.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/etianwang"))
        )
        contact_layout.addWidget(self.btn_github)

        # 2. Telegram 按钮
        self.btn_telegram = QToolButton()
        tg_path = get_resource_path("telegram.svg")
        if os.path.exists(tg_path):
            self.btn_telegram.setIcon(QIcon(tg_path))
            self.btn_telegram.setIconSize(QSize(14, 14))
        else:
            self.btn_telegram.setText("TG")
        self.btn_telegram.setStyleSheet(icon_btn_style)
        self.btn_telegram.setToolTip("通过 Telegram 联系")
        self.btn_telegram.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://t.me/etienne_wang"))
        )
        contact_layout.addWidget(self.btn_telegram)

        # 3. 微信按钮
        self.btn_wechat = QToolButton()
        wx_path = get_resource_path("wechat.svg")
        if os.path.exists(wx_path):
            self.btn_wechat.setIcon(QIcon(wx_path))
            self.btn_wechat.setIconSize(QSize(14, 14))
        else:
            self.btn_wechat.setText("WX")
        self.btn_wechat.setStyleSheet(icon_btn_style)
        self.btn_wechat.setToolTip("悬停查看微信二维码")

        # 初始化二维码悬浮窗
        qr_image_path = get_resource_path('wechat_qr.png')
        self.wechat_tooltip = QRCodeTooltip(self, qr_image_path)
        self.wechat_tooltip.hide()

        # 绑定悬停事件
        self.btn_wechat.enterEvent = lambda e: self._show_wechat_qr(e)
        self.btn_wechat.leaveEvent = lambda e: self._hide_wechat_qr(e)

        contact_layout.addWidget(self.btn_wechat)
        v_layout.addWidget(contact_frame)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: rgba(255,255,255,0.2); background-color: transparent;")
        v_layout.addWidget(line)

        # 版权信息
        copyright_label = QLabel("Ver 2026.05\nAuthor: Etienne")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_label.setStyleSheet(
            "color: rgba(255,255,255,0.6); font-size: 8pt; background: transparent;"
        )
        copyright_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        v_layout.addWidget(copyright_label)

        self.main_h_layout.addWidget(self.sidebar)

    def create_pages(self):
        """创建并向 QStackedWidget 添加所有功能页面"""
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
        """切换显示的页面并更新导航按钮状态"""
        self.stacked_widget.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    # --- 微信二维码显示/隐藏逻辑 ---
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

    # --- 关闭事件确认 ---
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


# --- 应用程序入口 (注释掉，由 login.py 调用) ---
# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     if len(sys.argv) > 1:
#         db_path = sys.argv[1]
#     else:
#         db_path = os.path.join(os.getcwd(), 'honsen_storage.db')
#     window = MainWindow(db_path)
#     window.show()
#     sys.exit(app.exec())