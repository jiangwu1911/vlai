import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                               QVBoxLayout, QGridLayout,
                               QScrollArea, QPushButton, QSizePolicy, QDialog, QStatusBar)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, pyqtSignal as Signal, QSize, QTimer
from qt_material import apply_stylesheet
from multi_lang import LANGUAGES

class ClickableLabel(QLabel):
    clicked = Signal()
    deleteRequested = Signal(int)  # 新增删除信号，携带图片索引

    def __init__(self, index, image_path, readOnly, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index = index
        self.image_path = image_path
        self.readOnly = readOnly
        self.big_image_window = None  # 用于存储大图窗口
        self.is_mouse_in_big_window = False  # 标志位，判断鼠标是否在大图窗口内

    def mousePressEvent(self, event):
        self.clicked.emit()
        
    def enterEvent(self, event):
        pixmap = self.pixmap()
        if pixmap and not self.big_image_window:
            # 创建新窗口
            self.big_image_window = QDialog(self.window())
            self.big_image_window.setWindowTitle("放大图片")
            self.big_image_window.setFixedSize(600, 600)
            self.big_image_window.setWindowFlags(self.window().windowFlags() | Qt.WindowType.FramelessWindowHint)

            big_image_label = QLabel(self.big_image_window)
            big_pixmap = QPixmap(self.image_path)
            scaled_pixmap = big_pixmap.scaled(600, 600, Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation)
            big_image_label.setPixmap(scaled_pixmap)
            big_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            layout = QVBoxLayout(self.big_image_window)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter) 

            # 创建大图窗口的删除按钮
            if not self.readOnly:
                big_delete_btn = QPushButton(self.big_image_window)
                big_delete_btn.setIcon(QIcon.fromTheme("window-close"))
                big_delete_btn.setIconSize(QSize(20, 20))
                big_delete_btn.setText("")
                big_delete_btn.setStyleSheet("""
                QPushButton {
                    padding: 0px !important;
                    margin: 0px !important;
                    border: 0px !important;
                }
                """)
                big_delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                big_delete_btn.clicked.connect(lambda: self.deleteRequested.emit(self.index))
                big_delete_btn.clicked.connect(self.big_image_window.close)

                if not self.readOnly:
                    layout.addWidget(big_delete_btn, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

            layout.addWidget(big_image_label, alignment=Qt.AlignmentFlag.AlignCenter)
            self.big_image_window.enterEvent = lambda e: self.on_big_window_enter()
            self.big_image_window.leaveEvent = lambda e: self.on_big_window_leave()
            self.big_image_window.show(),
            self.big_image_window.activateWindow()

        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.big_image_window and not self.is_mouse_in_big_window:
            self.big_image_window.close()
            self.big_image_window = None
        super().leaveEvent(event)

    def on_big_window_enter(self):
        self.is_mouse_in_big_window = True

    def on_big_window_leave(self):
        self.is_mouse_in_big_window = False
        if self.big_image_window:
            self.big_image_window.close()
            self.big_image_window = None

    def resizeEvent(self, event):
        # 调整删除按钮位置到右上角
        super().resizeEvent(event)
        

class ImageGallery(QWidget):
    def __init__(self, readOnly=False, rows=2, cols=3, language='zh'):
        super().__init__()
        self.readOnly = readOnly
        self.maxImageNumber = 3
        self.language = language
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 20, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        scroll_content = QWidget()
        scroll_area.setWidget(scroll_content)
        self.grid_layout = QGridLayout(scroll_content)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(0)

        self.image_paths = []
        self.rows = rows
        self.cols = cols

        # 启用拖放功能
        if not self.readOnly:
            self.setAcceptDrops(True)

        self.updateUI()

    def addImage(self, path):
        for p in self.image_paths:
            if p == path:
                self.upload_label.setText(LANGUAGES[self.language]['image_gallery_image_already_exist'])
                return

        if len(self.image_paths) >= self.maxImageNumber:
            self.upload_label.setText(
                f"{LANGUAGES[self.language]['image_gallery_max_image_number_1']}"
                f"{self.maxImageNumber}"
                f"{LANGUAGES[self.language]['image_gallery_max_image_number_2']}")
            return
          
        pixmap = QPixmap(path)    
        if pixmap.isNull():
            self.upload_label.setText(f"{LANGUAGES[self.language]['image_gallery_unable_to_load_image']}{path}")
            return

        self.image_paths.append(path)

        self.updateUI()

    def clear(self):
        self.image_paths.clear()
        self.updateUI()

    def updateUI(self):
        # 清空之前的布局
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()  # 安全删除控件

        for i, image_path in enumerate(self.image_paths):
            row = i // self.cols
            col = i % self.cols

            image_label = ClickableLabel(i, image_path, self.readOnly)  # 使用自定义的可点击标签
            pixmap = QPixmap(image_path)
            width = min(self.width() // self.cols, 300)
            if not pixmap.isNull():
                # 修改这里，使用 // 进行整除运算得到整数高度
                height = width * 2 // 3
                pixmap = pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                image_label.setPixmap(pixmap)
            else:
                image_label.setText(f"图片 {i + 1} 不存在")

            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setStyleSheet("""
                QLabel {
                    border: 0px solid #ccc;
                    padding: 5px;
                    background-color: #31363b;
                }
            """)
            image_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            image_label.setFixedSize(width, width * 2 // 3)  # 固定大小以便布局

            # 连接删除信号
            image_label.deleteRequested.connect(self.deleteImage)

            self.grid_layout.addWidget(image_label, row, col)

        if not self.readOnly:
            if len(self.image_paths) < self.maxImageNumber + 1:
                self.upload_label = QLabel(f" + {LANGUAGES[self.language]['image_gallery_add_image']}")
                self.upload_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.grid_layout.addWidget(self.upload_label, len(self.image_paths) // self.cols,
                                           len(self.image_paths) % self.cols)

    def deleteImage(self, index):
        if 0 <= index < len(self.image_paths):
            del self.image_paths[index]
            self.updateUI()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            self.addImage(file_path)
        event.acceptProposedAction()
        
    def setRowsAndCols(self, rows, cols):
        self.rows = rows
        self.cols = cols   


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_teal.xml')

    window = QMainWindow()
    window.setWindowTitle("多张图片展示(带删除功能)")
    window.setGeometry(100, 100, 800, 800)

    # 设置主窗口背景颜色为 dark_teal 主题的灰色
    window.setStyleSheet("background-color: #31363b;")

    gallery = ImageGallery()
    window.setCentralWidget(gallery)
    window.show()

    # 测试图片
    # gallery.addImage("2024_08_01_143715_509.jpg")
    # gallery.addImage("2025_05_13_155826_007.jpg")
    # gallery.addImage("2025_05_13_155826_067.jpg")
    # gallery.addImage("2025_05_13_155826_087.jpg")
    # gallery.addImage("2025_05_13_155826_267.jpg")
    # gallery.addImage("2025_05_13_155826_467.jpg")

    sys.exit(app.exec())
