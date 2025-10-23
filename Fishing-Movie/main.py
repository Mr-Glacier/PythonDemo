import os
import sys
import vlc
from PyQt5 import QtWidgets, QtCore, QtGui

# VLC 动态库路径（64位 VLC）
vlc_path = r"D:\Software\VLC"
if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(vlc_path)


class MiniVideoPlayer(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # === 窗口设置 ===
        self.setWindowTitle("🎬 Mini Video Player")
        self.resize(300, 180)
        self.setMinimumSize(100, 60)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        # === 视频显示区 ===
        self.video_frame = QtWidgets.QFrame(self)
        self.video_frame.setStyleSheet(
            "background-color: black; border: 2px solid #000; border-radius: 6px;"
        )

        # === 进度条 ===
        self.progress_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderMoved.connect(self.set_position)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #444;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
        """)

        # === 控制栏 ===
        self.control_bar = QtWidgets.QWidget(self)
        self.control_bar.setFixedHeight(28)
        self.control_bar.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 160);
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QPushButton {
                color: white;
                background: none;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                color: #00BFFF;
            }
        """)

        # 控制栏布局
        control_layout = QtWidgets.QHBoxLayout()
        control_layout.setContentsMargins(5, 2, 5, 2)
        control_layout.setSpacing(5)

        # 左侧按钮
        self.play_button = QtWidgets.QPushButton("▶")
        self.play_button.clicked.connect(self.toggle_play)
        self.open_button = QtWidgets.QPushButton("📂")
        self.open_button.clicked.connect(self.open_file)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.open_button)

        control_layout.addStretch()  # 中间空白

        # 右侧按钮（关闭）
        self.close_button = QtWidgets.QPushButton("✖")
        self.close_button.clicked.connect(self.close)
        control_layout.addWidget(self.close_button)

        # 右下角拖拉控件
        self.resize_grip = QtWidgets.QSizeGrip(self.control_bar)
        self.resize_grip.setStyleSheet("background: transparent;")
        self.resize_grip.setFixedSize(12, 12)

        # 使用垂直布局把 QSizeGrip 放到右下角
        grip_layout = QtWidgets.QVBoxLayout()
        grip_layout.addStretch()
        grip_layout.addWidget(self.resize_grip, 0, QtCore.Qt.AlignRight)
        grip_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.addLayout(grip_layout)

        self.control_bar.setLayout(control_layout)

        # === 主布局 ===
        self.container = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.video_frame)
        self.main_layout.addWidget(self.progress_slider)
        self.main_layout.addWidget(self.control_bar)
        self.setCentralWidget(self.container)

        # === VLC 播放器 ===
        self.instance = vlc.Instance()
        self.media_player = self.instance.media_player_new()
        if sys.platform == "win32":
            self.media_player.set_hwnd(self.video_frame.winId())

        # 状态变量
        self.media = None
        self.is_playing = False
        self.drag_pos = None

        # 定时器更新进度条
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start()

    # 打开视频
    def open_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mkv *.mov)"
        )
        if file_path:
            self.media = self.instance.media_new(file_path)
            self.media_player.set_media(self.media)
            self.media_player.play()
            self.play_button.setText("⏸")
            self.is_playing = True

    # 播放/暂停
    def toggle_play(self):
        if not self.media:
            return
        if self.is_playing:
            self.media_player.pause()
            self.play_button.setText("▶")
        else:
            self.media_player.play()
            self.play_button.setText("⏸")
        self.is_playing = not self.is_playing

    # 拖动窗口
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_pos and event.buttons() == QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    # 更新进度条
    def update_ui(self):
        if self.media_player.is_playing():
            pos = self.media_player.get_position()
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(int(pos * 1000))
            self.progress_slider.blockSignals(False)
        elif self.media_player.get_state() == vlc.State.Ended:
            self.play_button.setText("▶")
            self.is_playing = False

    # 拖动进度条改变播放位置
    def set_position(self, value):
        if self.media_player.get_media():
            self.media_player.set_position(value / 1000.0)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    player = MiniVideoPlayer()

    # 居中显示
    screen = app.primaryScreen().availableGeometry()
    player.move(
        screen.center().x() - player.width() // 2,
        screen.center().y() - player.height() // 2
    )

    player.show()
    sys.exit(app.exec_())
