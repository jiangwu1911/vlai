import os
import json
import threading
import time
import sys
import re
import numpy as np
import pyttsx3
from PyQt6.QtCore import QObject, pyqtSignal as Signal
from PyQt6.QtWidgets import QApplication
from pathlib import Path

class SpeechRecognizer(QObject):
    command_sent = Signal(str)  # 用于输出完整命令
    partial_result = Signal(str)  # 用于实时部分结果

    def __init__(self):
        super().__init__()
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)
        self.engine.setProperty('volume', 1.0)
        self.is_listening = False
        self.stop_event = threading.Event()
        self.callbacks = []
        self.lock = threading.Lock()
        self.last_command_time = 0
        self.error_mapping = {
            "一线": "胰腺",
            "类见": "肋间"
        }

    def start_listening(self):
        if self.is_listening:
            return

        self.is_listening = True
        self.stop_event.clear()

        # 连接回调函数
        for callback in self.callbacks:
            self.command_sent.connect(callback)

        # 启动监听线程
        self.listening_thread = threading.Thread(target=self._listen_thread)
        self.listening_thread.daemon = True
        self.listening_thread.start()

        print("语音识别已启动，开始监听...")

    def stop_listening(self):
        if not self.is_listening:
            return

        self.is_listening = False
        self.stop_event.set()

        if hasattr(self, 'listening_thread') and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=1.0)

        self._cleanup_resources()
        print("语音识别已停止监听")

    def __del__(self):
        self.stop_listening()
        if self.engine:
            self.engine.stop()

    def handle_command(self, text):
        self.command_sent.emit(text)

    def _listen_thread(self):
        raise NotImplementedError("子类必须实现监听线程方法")

    def _cleanup_resources(self):
        raise NotImplementedError("子类必须实现资源清理方法")

    def smart_to_lower(self, text):
        text = text.lower()
        text = re.sub(r'(^|[.!?])\s*(\w)', lambda m: m.group(1) + ' ' + m.group(2).upper(), text)

        proper_nouns = ['nasa', 'usa', 'uk', 'ai', 'ibm', 'http', 'https', 'dr.', 'mr.', 'mrs.', 'ms.']
        for word in proper_nouns:
            text = re.sub(r'\b' + word + r'\b', word.upper(), text, flags=re.IGNORECASE)

        important_words = ['The', 'A', 'An', 'And', 'But', 'Or', 'For', 'Nor', 'With', 'In', 'On', 'At', 'To', 'By']
        words = text.split()
        if len(words) > 1:  # 如果是标题（多个单词）
            capitalized_words = [words[0].capitalize()]  # 第一个单词总是大写
            for word in words[1:]:
                if word.lower() not in [w.lower() for w in important_words]:
                    capitalized_words.append(word.capitalize())
                else:
                    capitalized_words.append(word.lower())
            text = ' '.join(capitalized_words)

        return text

class VoskRecognizer(SpeechRecognizer):
    def __init__(self, language='zh'):
        super().__init__()
        import pyaudio
        from vosk import Model, KaldiRecognizer

        self.pyaudio = pyaudio
        self.KaldiRecognizer = KaldiRecognizer

        # Vosk模型初始化
        if language == 'zh':
            model_path = "vosk-model-cn-0.22"
        else:
            model_path = "vosk-model-small-en-us-0.15"

        if not os.path.exists(model_path):
            print(f"请先下载模型并放在{model_path}目录下")
            print("下载地址: https://alphacephei.com/vosk/models")
            exit(1)

        self.model = Model(model_path)
        self.sample_rate = 16000
        self.audio_interface = None
        self.stream = None
        self.recognizer = None

    def enhance_audio(self, audio_data):
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        audio_np = np.clip(audio_np * 1.5, -32768, 32767).astype(np.int16)
        return audio_np.tobytes()

    def recognize_audio(self, audio_data):
        with self.lock:
            processed_data = self.enhance_audio(audio_data)
            # 获取部分结果（实时识别）
            partial_result = self.recognizer.PartialResult()
            partial_text = ""
            if partial_result:
                partial_json = json.loads(partial_result)
                partial_text = partial_json.get("partial", "").strip().replace(' ', '')
                # 应用错误映射
                for wrong_word, correct_word in self.error_mapping.items():
                    if wrong_word in partial_text:
                        partial_text = partial_text.replace(wrong_word, correct_word)
                # 发送实时部分结果信号
                self.partial_result.emit(partial_text)

            # 检查是否完成一句话识别
            if self.recognizer.AcceptWaveform(processed_data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").strip().replace(' ', '')
                for wrong_word, correct_word in self.error_mapping.items():
                    if wrong_word in text:
                        text = text.replace(wrong_word, correct_word)
                return text
        return ""

    def _listen_thread(self):
        try:
            self.audio_interface = self.pyaudio.PyAudio()
            self.stream = self.audio_interface.open(
                format=self.pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=4096
            )
            self.recognizer = self.KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)
            self.last_voice_time = time.time()

            while not self.stop_event.is_set():
                data = self.stream.read(4096, exception_on_overflow=False)
                if len(data) == 0:
                    break

                text = self.recognize_audio(data)
                self.handle_command(text)
        except Exception as e:
            print(f"监听线程出错: {e}")
        finally:
            self._cleanup_resources()

    def _cleanup_resources(self):
        with self.lock:
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass
                self.stream = None

            if self.audio_interface:
                try:
                    self.audio_interface.terminate()
                except:
                    pass
                self.audio_interface = None

            self.recognizer = None


class SherpaRecognizer(SpeechRecognizer):
    def __init__(self):
        super().__init__()
        try:
            import sounddevice as sd
            import sherpa_onnx
        except ImportError as e:
            print(f"缺少依赖: {e}")
            print("请安装所需依赖: pip install sounddevice sherpa-onnx")
            exit(1)

        self.sd = sd
        self.sherpa_onnx = sherpa_onnx
        self.recognizer = self.create_recognizer()
        self.stream = None
        self.display = sherpa_onnx.Display()
        self.gain_level = 0.3

    def assert_file_exists(self, filename: str):
        assert Path(filename).is_file(), (
            f"{filename} does not exist!\n"
            "Please refer to "
            "https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-paraformer/paraformer-models.html to download it"
        )

    def create_recognizer(self):
        model_dir = "./sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"
        encoder = f"{model_dir}/encoder-epoch-99-avg-1.onnx"
        decoder = f"{model_dir}/decoder-epoch-99-avg-1.onnx"
        joiner = f"{model_dir}/joiner-epoch-99-avg-1.onnx"
        tokens = f"{model_dir}/tokens.txt"

        # 检查文件是否存在
        self.assert_file_exists(encoder)
        self.assert_file_exists(decoder)
        self.assert_file_exists(joiner)
        self.assert_file_exists(tokens)

        return self.sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=tokens,
            encoder=encoder,
            decoder=decoder,
            joiner=joiner,
            num_threads=4,
            sample_rate=16000,
            feature_dim=80,
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=2.4,
            rule2_min_trailing_silence=1.2,
            rule3_min_utterance_length=300,
        )

    def _listen_thread(self):
        try:
            devices = self.sd.query_devices()
            if len(devices) == 0:
                print("未找到麦克风设备")
                return

            default_input_device_idx = self.sd.default.device[0]
            print(f'使用默认设备: {devices[default_input_device_idx]["name"]}')

            self.stream = self.recognizer.create_stream()
            sample_rate = 48000  # Sherpa会自动重采样
            samples_per_read = int(0.1 * sample_rate)  # 100ms 一次读取

            with self.sd.InputStream(channels=1, dtype="float32",
                                     samplerate=sample_rate) as s:
                while not self.stop_event.is_set():
                    samples, _ = s.read(samples_per_read)  # 阻塞读取
                    samples = samples.reshape(-1)
                    samples = samples * self.gain_level
                    self.stream.accept_waveform(sample_rate, samples)

                    while self.recognizer.is_ready(self.stream):
                        self.recognizer.decode_stream(self.stream)

                    # 检查是否到达端点
                    is_endpoint = self.recognizer.is_endpoint(self.stream)
                    result = self.recognizer.get_result(self.stream)

                    # 处理部分结果
                    partial_text = result
                    for wrong_word, correct_word in self.error_mapping.items():
                        if wrong_word in partial_text:
                            partial_text = partial_text.replace(wrong_word, correct_word)
                    partial_text = self.smart_to_lower(partial_text)
                    self.partial_result.emit(partial_text)

                    # 处理完整句子
                    if is_endpoint and result:
                        final_text = result.strip()
                        for wrong_word, correct_word in self.error_mapping.items():
                            if wrong_word in final_text:
                                final_text = final_text.replace(wrong_word, correct_word)
                        final_text = self.smart_to_lower(final_text)
                        self.handle_command(final_text)
                        self.display.finalize_current_sentence()
                        self.recognizer.reset(self.stream)

        except Exception as e:
            print(f"监听线程出错: {e}")
        finally:
            self._cleanup_resources()

    def _cleanup_resources(self):
        with self.lock:
            self.stream = None


# 回调函数和测试代码
def on_partial_result(partial):
    if len(partial) > 0:
        sys.stdout.write(f"\r正在识别: {partial}")
        sys.stdout.flush()


def on_command_received(command):
    if len(command) > 0:
        print(f"\n收到完整命令: {command}")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 选择使用的识别引擎
    #recognizer = VoskRecognizer()
    recognizer = SherpaRecognizer()

    recognizer.callbacks.append(on_command_received)
    recognizer.partial_result.connect(on_partial_result)
    recognizer.start_listening()

    sys.exit(app.exec())