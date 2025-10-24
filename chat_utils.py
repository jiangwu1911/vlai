from PyQt6.QtGui import QFontDatabase
import logging
import os

def delete_all_files_in_directory(directory):
    if not os.path.isdir(directory):
        return

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # 删除文件或符号链接
            elif os.path.isdir(file_path):
                pass
        except Exception as e:
            print(f"删除 {file_path} 失败: {e}")

def get_app_dir():
    return os.path.dirname(os.path.abspath(__file__))