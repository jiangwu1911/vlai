# -*- coding: utf-8 -*-
import sys
import datetime
import argparse
import markdown  
import shutil
import re
import json
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, \
    QTextEdit, QLineEdit, QLabel
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal, QTimer
from voice_recognizer import VoskRecognizer
from voice_recognizer import SherpaRecognizer
from restful_server import RESTfulServer
from qt_material import apply_stylesheet
from chat_model import ChatSession, ChatContent, ChatDatabase
from chat_view import ChatViewer
from llmagent import LLMAgent
from imagegallery import ImageGallery
from chat_utils import *
from multi_lang import LANGUAGES
from configdialog import ConfigDialog
from save_note_thread import SaveNoteThread

# 如果想通过mitmproxy调试程序, 打开这个注释
#os.environ["HTTP_PROXY"] = "http://127.0.0.1:8080"
#os.environ["HTTPS_PROXY"] = "http://127.0.0.1:8080"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

db = ChatDatabase()

class RequestThread(QThread):
    response_signal = Signal(object)
    _stop_flag = False

    def __init__(self, llmagent, question, images):
        super().__init__()
        self.llmagent = llmagent
        self.question = question
        self.images = images

    def run(self):
        response = self.llmagent.ask_question(self.question, self.images)
        if isinstance(response, str):
            self.response_signal.emit(response)
        else:
            for chunk in response:
                if self._stop_flag:
                    break
                #logger.info(f"emit chunk: {chunk}")
                self.response_signal.emit(chunk)

    def stop(self):
        self._stop_flag = True


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.current_thread = None
        self.assistant = None
        self.chat_session = None
        self.currentAnswer = None
        self.llmagent = None
        self.encoded_images = []
        self.currentUploadedImages = ""

        self.load_config()

        self.saveNoteThread = SaveNoteThread()
        self.initVoiceAssistant()
        self.initUI()
        self.llmagent = self.create_llmagent("default")
        self.initRestfulServer()

        self.move_to_left()
        self.accept_voice_input = True
        self.isActive = False

        self._response_changed = False  # 标记是否有新内容需要保存
        self._save_timer = QTimer(self)
        self._save_timer.timeout.connect(self.save_answer_if_changed)
        self._save_timer.start(1000)  # 每秒检查一次

    def create_llmagent(self, config_name):
        self.stop_chat_session()

        model_name = self.default_model
        if config_name == "RAG":
            model_name = self.rag_model

        agent = LLMAgent(config_name,
                         self.url,
                         model_name,
                         self.key)
        return agent

    def on_voice_command_received(self, command1):
        if self.isActive == False:
            if command1.find("你好") >=0  or command1.find("您好") >= 0 or command1.find("帕斯卡") >= 0 \
	            or command1.find("东风") >= 0 or command1.find("海豚") >= 0 or command1.find("hello") >= 0:
                self.imageGallery.clear()
                self.llmagent.clear_history()
                self.txt_chat_history.clear()
                self.question_input.clear()

                self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
                lang_text = LANGUAGES[self.language]
                assistant_html = f"{lang_text['welcome_message']}<br>"
                self.txt_chat_history.append(assistant_html)
                self.show()
                self.activateWindow()
                self.accept_voice_input = True
                self.isActive = True
            else:
                return

        elif command1.find("退出") >= 0 or command1.find("quit") >= 0:
            self.stop_chat_session()
            self.accept_voice_input = False
            self.hide()
            self.isActive = False

        elif command1.find("截屏") >= 0 or command1.find("capture screen") >= 0:
            self.take_screenshot()

        elif command1.find("停止") >= 0 or command1.find("停下") >= 0 or command1.find("暂停") >= 0 \
                or command1.find("stop") >= 0:
            self.stop_current_thread()

        elif len(command1) < 2:
            return

        else:
            #logger.info(f"Receive command: {command}")
            if self.accept_voice_input == True:
                self.question_input.setText(command1)
                self.ask_button.click()

    def on_partial_result(self, partial):
        if partial != "":
            self.question_input.setText(partial)

    def got_voice_command(self, command):
        if command != "":
            self.saveNoteThread.receive_data(command)

    def initVoiceAssistant(self, language='zh'):
        self.assistant = None
        #self.assistant = VoskRecognizer(language)
        self.assistant = SherpaRecognizer()
        self.assistant.callbacks.append(self.on_voice_command_received)
        self.assistant.partial_result.connect(self.on_partial_result)
        self.assistant.command_sent.connect(self.got_voice_command)
        self.assistant.start_listening()

    def receivedShowCommand(self):
        if self.isActive == True:
            self.accept_voice_input = True
            self.show()
            self.activateWindow()

    def receivedHideCommand(self):
        if self.current_thread is not None:
            self.stop_current_thread()
        self.accept_voice_input = False
        self.hide()

    def startSaving(self, filename):
        self.saveNoteThread.start_saving(filename)

    def stopSaving(self):
        self.saveNoteThread.stop_saving()
        
    def initRestfulServer(self):
        self.restfulServer = RESTfulServer()
        self.restfulServer.showWindow.connect(self.receivedShowCommand)
        self.restfulServer.hideWindow.connect(self.receivedHideCommand)
        self.restfulServer.clearHistory.connect(self.llmagent.clear_history)
        self.restfulServer.uploadImage.connect(self.handleImageUpload)
        self.restfulServer.startSaveNote.connect(self.startSaving)
        self.restfulServer.stopSaveNote.connect(self.stopSaving)

    css = """
            QWidget {
                font-size: 13px;
                font-weight: 300;
                border-radius: 10px;
                border: 1px;
            }
            QPushButton {
                font-size: 13px;
                font-weight: 300;
                border-radius: 8px;
                padding: 5px;
            }
            QLabel {
                font-size: 13px;
                font-weight: 300;
                border-radius: 8px;
            }
            QLineEdit, QTextEdit {
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 300;
                border-radius: 8px;
                padding: 5px;
                border: 1px;
            }
            QRadioButton, QCheckBox {
                color: #1de9b6;
               font-size: 13px;
                font-weight: 300;
            }
            QRadioButton::indicator, QCheckBox::indicator {
                color: #1de9b6;
                width: 13px;
                height: 13px;
            }
        """

    def initUI(self):
        # 使用默认语言设置界面文本
        lang_text = LANGUAGES[self.language]
        self.setWindowTitle(lang_text['title'])

        self.setGeometry(100, 350, 460, 720)
        self.setFixedSize(460, 720)

        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.main_frame = QWidget()
        self.setStyleSheet(self.css)
        main_layout.addWidget(self.main_frame)
        content_layout = QVBoxLayout(self.main_frame)

        self.imageGallery = ImageGallery(rows=2, cols=2, language=self.language)
        self.imageGallery.setFixedSize(440, 300)
        content_layout.addWidget(self.imageGallery)

        self.txt_chat_history = QTextEdit()
        self.txt_chat_history.setReadOnly(True)
        self.txt_chat_history.setAcceptRichText(True)  # 显式设置为富文本模式
        content_layout.addWidget(self.txt_chat_history)

        self.question_input = QLineEdit()
        self.question_input.returnPressed.connect(self.send_question)
        self.ask_button = QPushButton(lang_text['ask_button'])
        self.ask_button.clicked.connect(self.send_question)
        ask_layout = QHBoxLayout()
        ask_layout.addWidget(self.question_input)
        ask_layout.addWidget(self.ask_button)
        content_layout.addLayout(ask_layout)

        # 添加语言选择的RadioButton
        control_layout = QHBoxLayout()
        control_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # 清除历史对话按钮
        self.clear_conversion_button = QPushButton(lang_text['clear_conversion_button'])
        self.clear_conversion_button.clicked.connect(self.stop_chat_session)
        control_layout.addWidget(self.clear_conversion_button)

        # 截屏按钮
        self.capture_screen_button = QPushButton(lang_text['capture_screen_button'])
        self.capture_screen_button.clicked.connect(self.take_screenshot)
        control_layout.addWidget(self.capture_screen_button)

        control_layout.addStretch()

        self.config_button = QPushButton(lang_text['config'])
        self.config_button.clicked.connect(self.show_config_dialog)
        control_layout.addWidget(self.config_button)

        # 历史对话按钮
        self.history_button = QPushButton(lang_text['history_button'])
        self.history_button.clicked.connect(self.show_chat_history)
        control_layout.addWidget(self.history_button)
 
        # 创建底部布局
        bottom_layout = QHBoxLayout()
        bottom_layout.addLayout(control_layout)
        content_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)

    def start_chat_session(self):
        self.chat_session = ChatSession(
                start_time = datetime.datetime.now(),
                end_time = datetime.datetime.now(),
                )
        self.chat_session.session_id = db.save_chat_session(self.chat_session)
        self.currentAnswer = None
        self.currentUploadedImages = ""
        self.start_position = 0

    def stop_chat_session(self):
        if self.current_thread:
            self.stop_current_thread()

        if self.chat_session is not None:
            self.chat_session.end_time = datetime.datetime.now()
            db.save_chat_session(self.chat_session)

        self.chat_session = None
        self.imageGallery.clear()
        if self.llmagent is not None:
            self.llmagent.clear_history()
        self.txt_chat_history.clear()

    def handleImageUpload(self, image_path):
        if not self.rag_enabled:
            self.imageGallery.addImage(image_path)
            self.encoded_images = [self.llmagent.encode_image(img_path) for img_path in self.imageGallery.image_paths]

    def escape_response(self, str):
        str = str.replace("中国的深度求索（DeepSeek）公司开发", "海豚智能开发")
        str = str.replace("DeepSeek-R1", "")
        #str = str.replace("<think>", "&lt;think&gt;")
        #str = str.replace("</think>", "&lt;/think&gt;")
        str = str.replace("<think>", "&lt;think&gt;<span style=\"color:gray\">")
        str = str.replace("</think>", "</span>&lt;/think&gt;")
        str = re.sub("&lt;think&gt;.*&lt;/think&gt;", "", str, flags=re.M | re.S)
        return str
    
    def send_question(self):
        self.stop_current_thread()

        question = self.question_input.text()
        if question:
            if self.chat_session is None:
                self.start_chat_session()
            self.currentAnswer = None

            if self.currentUploadedImages != json.dumps(self.imageGallery.image_paths):
                self.save_upload_image()
                self.currentUploadedImages = json.dumps(self.imageGallery.image_paths)
            self.save_question(question)

            user_html = f'<img src="{get_app_dir()}/assets/user.png" style="vertical-align: middle; ">&nbsp;&nbsp; {question}'
            self.txt_chat_history.append(user_html)
    
            # 使用线程处理请求
            if self.language == 'en':
                question = f"Please answer in English. {question}"  # 添加英文提示
            self.encoded_images = [self.llmagent.encode_image(img_path) for img_path in self.imageGallery.image_paths]    
            self.current_thread = RequestThread(self.llmagent, question, self.encoded_images)
            self.current_thread.response_signal.connect(self.handle_response)
            self.current_thread.start()
    
            self.question_input.clear()
            if hasattr(self, 'full_response'):
                del self.full_response

    def handle_response(self, response):
        if isinstance(response, str):
            assistant_html = f'<br><img src="{get_app_dir()}/assets/robot.png" style="vertical-align: middle;"> &nbsp;&nbsp;&nbsp;'
            self.txt_chat_history.append(assistant_html)
            # 滚动到文本末尾
            scrollbar = self.txt_chat_history.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        else:
            if not hasattr(self, 'full_response'):
                assistant_html = f'<br><img src="{get_app_dir()}/assets/robot.png" style="vertical-align: middle;"> &nbsp;&nbsp;&nbsp;'
                self.txt_chat_history.insertHtml(assistant_html)
                self.full_response = ""
                # 记录助手回复起始位置
                self.start_cursor = self.txt_chat_history.textCursor()
                self.start_position = self.start_cursor.position()

            self.full_response += response.content
            self._response_changed = True  # 标记内容已更新

            try:
                response_html = markdown.markdown(self.escape_response(self.full_response))
                if response_html.startswith('<p>') and response_html.endswith('</p>'):
                    response_html = response_html[3:-4]
                # 移动光标到助手回复起始位置
                cursor = self.txt_chat_history.textCursor()
                cursor.setPosition(self.start_position)
                # 修改此处，使用 QTextCursor.End
                cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
                # 插入新的解析结果
                self.txt_chat_history.insertHtml(response_html+"<br>")
                # 滚动到文本末尾
                scrollbar = self.txt_chat_history.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
            except Exception as e:
                logger.info(f"Display response error: {e}")

    def move_to_left(self):
        # 获取可用屏幕区域
        available_geometry = QApplication.primaryScreen().availableGeometry()
        window_width = self.width()
        window_height = self.height()
        # 设置窗口的 x 坐标为可用区域的左侧边缘
        x = available_geometry.x()
        # 设置窗口的 y 坐标，这里假设窗口顶部与可用区域顶部对齐
        y = available_geometry.height() - window_height - 130
        self.move(0, y)

    def set_chinese(self):
        if self.language != 'zh':
            self.language = 'zh'
            self.imageGallery.language = self.language
            self.imageGallery.updateUI()
            self.update_ui_text()
            logger.info("Init Chinese voice assistant")
            self.stop_current_thread()

            if self.assistant:
                self.assistant.stop_listening()

            self.initVoiceAssistant('zh')

    def set_english(self):
        if self.language != 'en':
            self.language = 'en'
            self.imageGallery.language = self.language
            self.imageGallery.updateUI()
            self.update_ui_text()
            logger.info("Init English voice assistant")
            self.stop_current_thread()

            if self.assistant:
                self.assistant.stop_listening()

            self.initVoiceAssistant('en')

    def stop_current_thread(self) :
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.stop()
            self.current_thread.wait()

    def save_question(self, question):
        question = ChatContent(session_id=self.chat_session.session_id,
                                 type="Question", content=question)
        return db.save_chat_content(question)

    def save_answer(self, answer):
        if self.currentAnswer is None:
            self.currentAnswer = ChatContent(session_id=self.chat_session.session_id,
                                 type="Answer", content=answer)

        self.currentAnswer.content = answer
        return db.save_chat_content(self.currentAnswer)

    def save_upload_image(self):
        history_image_path = f"history/images/{self.chat_session.session_id}"
        if not os.path.exists(history_image_path):
            os.makedirs(history_image_path, exist_ok=True)
        
        image_paths = []
        for original_path in self.imageGallery.image_paths:    
            image_name = os.path.basename(original_path)
            shutil.copy2(original_path, f"{history_image_path}")
            image_paths.append(f"{history_image_path}/{image_name}")
            
        upload_images = ChatContent(session_id=self.chat_session.session_id,
                                 type="Upload_image", content=json.dumps(image_paths))
        return db.save_chat_content(upload_images)

    def show_config_dialog(self):
        dialog = ConfigDialog(self, self.language, self.rag_enabled, self.url)
        dialog.setStyleSheet(self.css)

        if dialog.exec():
            if dialog.get_rag_state() != self.rag_enabled:
                self.rag_enabled = dialog.get_rag_state()
                if self.rag_enabled:
                    self.llmagent = self.create_llmagent("RAG")
                else:
                    self.llmagent = self.create_llmagent("default")

            if dialog.get_language() != self.language:
                if dialog.get_language() == 'zh':
                    self.set_chinese()
                else:
                    self.set_english()
                self.language = dialog.get_language()

            self.save_config()

    def show_chat_history(self):
        self.stop_current_thread()

        logger.info("Set accept_voice_input to False")
        self.accept_voice_input = False
        chat_viewer = ChatViewer(db_path='history/chat_sessions.db', parent=self, language=self.language)
        chat_viewer.setFixedSize(1024, 768)
        chat_viewer.setWindowFlags(chat_viewer.windowFlags() | Qt.WindowType.FramelessWindowHint)
        chat_viewer.setWindowModality(Qt.WindowModality.ApplicationModal)
        chat_viewer.finished.connect(lambda: self.on_history_dialog_closed())
        chat_viewer.show()

    def on_history_dialog_closed(self):
        logger.info("Set accept_voice_input to True")
        self.accept_voice_input = True
        
    def on_deep_thinking_changed(self, state):
        self.llmagent.change_deep_thinking(state)
        self.llmagent.clear_history()

    def take_screenshot(self):
        if self.rag_enabled:
            return

        self.hide()
        QTimer.singleShot(200, self.capture_screen)

    def capture_screen(self):
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(0, 220, 0, 1300, 975)

        screenshot_path = f"screenshot/"
        if not os.path.exists(screenshot_path):
            os.makedirs(screenshot_path, exist_ok=True)

        now = datetime.datetime.now()
        timestamp = now.strftime("screen_shot_%Y_%m_%dT%H_%M_%S")
        path = f"{screenshot_path}/screenshot_{timestamp}.png"
        screenshot.save(path)
        self.imageGallery.addImage(path)
        self.show()
        self.activateWindow()

    def update_ui_text(self):
        lang_text = LANGUAGES[self.language]
        self.setWindowTitle(lang_text['title'])
        self.ask_button.setText(lang_text['ask_button'])
        self.clear_conversion_button.setText(lang_text['clear_conversion_button'])
        self.capture_screen_button.setText(lang_text['capture_screen_button'])
        self.history_button.setText(lang_text['history_button'])
        self.config_button.setText(lang_text['config'])

    def save_answer_if_changed(self):
        if hasattr(self, 'full_response') and self._response_changed:
            self.save_answer(self.full_response)
            self._response_changed = False  # 重置标志

    def load_config(self):
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            self.language = config["language"]
            self.rag_enabled = config["rag_enabled"]
            self.key = config["key"]
            self.url = config["url"]
            self.default_model = config["default_model"]
            self.rag_model = config["rag_model"]

    def save_config(self):
        with open("config.json", "w", encoding="utf-8") as f:
            config = {}
            config["language"] = self.language
            config["rag_enabled"] = self.rag_enabled
            config["key"] = self.key
            config["url"] = self.url
            config["default_model"] = self.default_model
            config["rag_model"] = self.rag_model
            json.dump(config, f, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--without_voice_input', action='store_true', help='没有语音输入')
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = MainWindow()
    apply_stylesheet(app, theme='dark_teal.xml')

    upload_dir = get_app_dir() + "/upload"
    delete_all_files_in_directory(upload_dir)

    window.setWindowFlags(window.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint 
        & ~Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
    if args.without_voice_input == True:
        window.show()
        window.isActive = True
        window.activateWindow()

    app.aboutToQuit.connect(window.stop_chat_session)

    sys.exit(app.exec())
