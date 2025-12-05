import sys
import json
import os
import time
from PyQt6.QtCore import QObject, pyqtSignal as Signal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QTcpServer, QHostAddress
from chat_utils import *

class HTTPRequestHandler(QObject):
    def __init__(self, socket, parent=None):
        super().__init__(parent)
        self.socket = socket
        self.socket.readyRead.connect(self.onReadyRead)
        self.socket.disconnected.connect(self.onDisconnected)
        self.buffer = bytearray()
        self.headers = {}
        self.content_length = 0
        self.boundary = None
        self.receiving_body = False
        self.body_data = bytearray()

    def onReadyRead(self):
        while self.socket.bytesAvailable() > 0:
            chunk = self.socket.readAll()
            self.buffer.extend(chunk)

            # 如果还没开始接收body
            if not self.receiving_body:
                # 查找头部结束标记
                header_end = self.buffer.find(b"\r\n\r\n")
                if header_end >= 0:
                    # 解析头部
                    header_data = self.buffer[:header_end]
                    self.parse_headers(header_data)

                    # 剩余数据是body的开始
                    body_start = header_end + 4  # 跳过\r\n\r\n
                    if body_start < len(self.buffer):
                        self.body_data.extend(self.buffer[body_start:])

                    self.buffer = bytearray()  # 清空缓冲区
                    self.receiving_body = True

            # 如果正在接收body
            if self.receiving_body:
                if len(self.buffer) > 0:
                    self.body_data.extend(self.buffer)
                    self.buffer = bytearray()

                # 检查是否接收完成
                if self.content_length == 0:
                    self.handle_request()
                elif self.content_length > 0:
                    if len(self.body_data) >= self.content_length:
                        self.handle_request()
                elif self.boundary:
                    # 对于multipart，检查结束边界
                    if (b'--' + self.boundary + b'--') in self.body_data:
                        self.handle_request()

    def parse_headers(self, header_data):
        header_lines = header_data.splitlines()
        request_line = header_lines[0].decode('utf-8').split()
        self.method = request_line[0]
        self.path = request_line[1]

        for line in header_lines[1:]:
            if b':' in line:
                key, value = line.split(b': ', 1)
                key = key.decode('utf-8').lower()
                value = value.decode('utf-8')
                self.headers[key] = value

                if key == 'content-length':
                    self.content_length = int(value)
                elif key == 'content-type' and 'multipart/form-data' in value:
                    # 提取boundary
                    boundary_part = value.split('boundary=')[1]
                    self.boundary = boundary_part.strip('"').encode('utf-8')

    def handle_request(self):
        try:
            # 完整请求数据在self.body_data中
            complete_data = bytes(self.body_data)

            # 处理请求逻辑...
            if self.path == "/v1/show" and self.method == "GET":
                self.parent().showWindow.emit()
                response = self.create_response(200, {"message": "窗口已显示"})

            elif self.path == "/v1/hide" and self.method == "GET":
                self.parent().hideWindow.emit()
                response = self.create_response(200, {"message": "窗口已隐藏"})

            elif self.path == "/v1/clear" and self.method == "GET":
                self.parent().clearHistory.emit()
                response = self.create_response(200, {"message": "对话历史已清除"})

            if self.path == "/v1/upload" and self.method == "POST":
                if self.boundary:
                    parts = self.parse_multipart(complete_data, self.boundary)
                    image_data = parts.get('image_data', b'')

                    if image_data:
                        upload_dir = get_app_dir() + "/upload"
                        save_path = os.path.join(upload_dir, f"upload_{int(time.time())}.png")
                        os.makedirs(os.path.dirname(save_path), exist_ok=True)

                        with open(save_path, 'wb') as f:
                            f.write(image_data)

                        self.parent().uploadImage.emit(save_path)
                        response = self.create_response(200, {
                            "message": "图片已上传并保存",
                            "saved_path": save_path
                        })
                    else:
                        response = self.create_response(400, {
                            "message": "缺少图片数据"
                        })
                else:
                    response = self.create_response(400, {
                        "message": "无效的内容类型"
                    })

            if self.path == "/v1/start_save_note" and self.method == "POST":
                filename = self.headers["x-filename"]
                self.parent().startSaveNote.emit(filename)
                response = self.create_response(200, {"message": "开始保存文本"})

            if self.path == "/v1/stop_save_note" and self.method == "POST":
                self.parent().stopSaveNote.emit()
                response = self.create_response(200, {"message": "停止保存文本"})

            # 发送响应
            self.socket.write(response)
            self.request_data = b""
            self.headers_received = False
            self.content_length = 0
            self.boundary = None

        except Exception as e:
            print(f"处理请求时出错: {str(e)}")
            response = self.create_response(500, {
                "message": f"服务器错误: {str(e)}"
            })
            self.socket.write(response)
        finally:
            self.socket.disconnectFromHost()

    def create_response(self, status_code, content_dict):
        content = json.dumps(content_dict).encode('utf-8')
        return (
            f"HTTP/1.1 {status_code} {'OK' if status_code == 200 else 'Error'}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(content)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode('utf-8') + content

    def onDisconnected(self):
        self.socket.deleteLater()
        self.deleteLater()

    def parse_multipart(self, data, boundary):
        parts = {}
        boundary = b'--' + boundary
        end_boundary = boundary + b'--'

        # 确保数据以boundary开头
        if not data.startswith(boundary):
            data = boundary + b'\r\n' + data

        # 分割各部分
        part_list = data.split(boundary)

        for part in part_list:
            part = part.strip()
            if not part or part == b'--':
                continue

            # 分割头部和内容
            if b'\r\n\r\n' not in part:
                continue

            header_data, content = part.split(b'\r\n\r\n', 1)
            headers = {}

            # 解析头部
            for header_line in header_data.split(b'\r\n'):
                if b':' in header_line:
                    name, value = header_line.split(b': ', 1)
                    headers[name.decode('utf-8').lower()] = value.decode('utf-8')

            # 获取字段名
            if 'content-disposition' in headers:
                disp = headers['content-disposition']
                field_name = None
                if 'name="' in disp:
                    field_name = disp.split('name="')[1].split('"')[0]

                if field_name:
                    parts[field_name] = content

        return parts

class RESTfulServer(QObject):
    showWindow = Signal()
    hideWindow = Signal()
    clearHistory = Signal()
    uploadImage = Signal(str)
    startSaveNote = Signal(str)
    stopSaveNote = Signal()

    def __init__(self, parent=None, port=8133):
        super().__init__(parent)
        self.server = QTcpServer(self)
        self.server.newConnection.connect(self.onNewConnection)

        if not self.server.listen(QHostAddress.SpecialAddress.Any, port):
            print("无法启动服务器！")
        else:
            print(f"服务器已启动，监听端口{port}...")

    def onNewConnection(self):
        socket = self.server.nextPendingConnection()
        handler = HTTPRequestHandler(socket, self)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    server = RESTfulServer()
    sys.exit(app.exec_())
