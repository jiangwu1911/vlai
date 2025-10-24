from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QRadioButton, QLabel, QLineEdit
from multi_lang import LANGUAGES

class ConfigDialog(QDialog):
    def __init__(self, parent=None, language='zh', rag_enabled=False, url=''):
        super().__init__(parent)
        self.language = language
        self.rag_enabled = rag_enabled
        self.url = url
        self.initUI()

    def initUI(self):
        lang_text = LANGUAGES[self.language]
        self.setWindowTitle(lang_text['config'])
        self.setFixedSize(400, 150)
        
        layout = QVBoxLayout()

        url_layout = QHBoxLayout()
        self.url_label = QLabel("URL: ")  # 添加URL标签
        self.url_label.setStyleSheet("color: #1de9b6;")
        self.url_edit = QLineEdit()  # 添加文本框
        self.url_edit.setStyleSheet("color: #1de9b6;")
        self.url_edit.setText(self.url)  # 设置初始值
        url_layout.addWidget(self.url_label)
        url_layout.addWidget(self.url_edit)

        rag_layout = QHBoxLayout()
        self.rag_switch = QCheckBox(lang_text['rag_mode'])
        self.rag_switch.setChecked(self.rag_enabled)
        rag_layout.addWidget(self.rag_switch)
        rag_layout.addStretch()

        language_layout = QHBoxLayout()
        self.chinese_rb = QRadioButton(lang_text['chinese_rb'])
        self.english_rb = QRadioButton(lang_text['english_rb'])
        if self.language == 'zh':
            self.chinese_rb.setChecked(True)
        else:
            self.english_rb.setChecked(True)
        language_layout.addWidget(self.chinese_rb)
        language_layout.addWidget(self.english_rb)

        # 确认按钮
        btn_layout = QHBoxLayout()
        self.confirm_btn = QPushButton(lang_text['confirm'])
        self.confirm_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(self.confirm_btn)

        layout.addLayout(url_layout)
        layout.addLayout(rag_layout)
        layout.addLayout(language_layout)
        layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def get_url(self):
        return self.url_edit.text()

    def get_rag_state(self):
        return self.rag_switch.isChecked()

    def get_language(self):
        if self.chinese_rb.isChecked():
            return 'zh'
        else:
            return 'en'