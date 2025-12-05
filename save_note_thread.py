import os.path
import threading
import time
from datetime import datetime
from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal, pyqtSlot

class ChinesePunctuator:
    def __init__(self):
        # 使用简单的规则方法，避免模型下载问题
        pass

    def punctuate(self, text):
        """智能添加中文标点符号"""
        if not text or len(text.strip()) == 0:
            return text

        text = text.strip()

        # 1. 处理疑问句
        question_words = ['吗', '呢', '什么', '为什么', '怎么', '哪', '谁', '多少', '几时', '何时', '会不会', '能不能']
        if any(word in text for word in question_words):
            if not text.endswith('？'):
                text += '？'
            return text

        # 2. 处理感叹句
        exclamation_words = ['真', '太', '非常', '特别', '超级', '极其', '十分', '确实', '实在']
        exclamation_endings = ['啊', '呀', '哇', '啦', '哦']
        if any(word in text for word in exclamation_words) or text[-1] in exclamation_endings:
            if not text.endswith('！'):
                text += '！'
            return text

        # 3. 添加逗号（基于常见连接词）
        connectors = ['然后', '接着', '但是', '不过', '所以', '因为', '如果', '而且', '另外', '同时']
        for connector in connectors:
            if connector in text and f'，{connector}' not in text:
                text = text.replace(connector, f'，{connector}', 1)

        # 4. 基于长度添加逗号
        if len(text) > 15:
            # 在文本中间位置添加逗号，但避免在数字、英文中间断开
            mid_pos = len(text) // 2
            for i in range(mid_pos, len(text) - 2):
                if not text[i].isalnum() or text[i].isascii():
                    text = text[:i + 1] + '，' + text[i + 1:]
                    break

        # 5. 确保有句末标点
        if not text[-1] in ['。', '？', '！', '，']:
            text += '。'

        return text


class SaveNoteThread(QObject):
    started = pyqtSignal() 
    stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)
    MAX_RECORD_LENGTH = 60 # Seconds

    def __init__(self):
        super().__init__()
        self._running = False
        self._thread = None
        self._start_time = None
        self._data_buffer = []
        self._lock = threading.Lock()
        self._filename = ""
        
    @pyqtSlot()
    def start_saving(self, filename):
        if self._running:
            return
            
        self._filename = filename
        self._running = True
        self._start_time = time.time()
        self._data_buffer.clear()
        
        self._thread = threading.Thread(target=self._save_worker)
        self._thread.daemon = True
        self._thread.start()
        
        self.started.emit()
        print("Begin to save note")
    
    @pyqtSlot()
    def stop_saving(self):
        if not self._running:
            return
            
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        
        self._flush_buffer()
        self.stopped.emit()
        print("Stop saving")
    
    @pyqtSlot(object)
    def receive_data(self, data):
        if not self._running:
            return
            
        with self._lock:
            self._data_buffer.append({
                'timestamp': datetime.now(),
                'data': data
            })
    
    def _save_worker(self):
        try:
            while self._running:
                if time.time() - self._start_time > self.MAX_RECORD_LENGTH:
                    print("Exceed ${MAX_RECORD_LENGTO} seconds, stop saving")
                    self.stop_saving()
                    break
                
                #self._flush_buffer()
                time.sleep(0.1) 
                
        except Exception as e:
            self.error_occurred.emit(f"Save error: {str(e)}")
    
    def _flush_buffer(self):
        with self._lock:
            if not self._data_buffer:
                return

            punctuator = ChinesePunctuator()
            for message in self._data_buffer:
                message['data'] = punctuator.punctuate(message['data'])

            try:
                with open(self._filename, 'a', encoding='utf-8') as f:
                    for item in self._data_buffer:
                        data_str = str(item['data'])
                        f.write(f"{data_str}")
                
                self._data_buffer.clear()
                
            except Exception as e:
                self.error_occurred.emit(f"Save file error: {str(e)}")
