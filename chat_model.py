from sqlalchemy import create_engine, Column, Integer, String, DateTime, LargeBinary, Text
from sqlalchemy.orm import declarative_base, sessionmaker  # 从orm导入declarative_base
import datetime
import os
from chat_utils import *
import threading

# 创建基础类 - 使用ORM版本的declarative_base
Base = declarative_base()

# 对话保存类
class ChatSession(Base):
    __tablename__ = 'chat_sessions'

    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time

    def __repr__(self):
        return f"<ChatSession(start_time='{self.start_time}', end_time='{self.end_time}')>"

class ChatContent(Base):
    __tablename__ = 'chat_content'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, nullable=False)
    type = Column(String, nullable=False)  # 内容是Question, Answer, Upload_images
    content = Column(String, nullable=False)
    occurred_time = Column(DateTime, nullable=False)

    def __init__(self, session_id, type, content):
        self.session_id = session_id
        self.type = type
        self.content = content
        self.occurred_time = datetime.datetime.now()

    def __repr__(self):
        return (f"<ChatContent(session_id='{self.session_id}', type='{self.type}', "
                f"content='{self.content}', occurred_time='{self.occurred_time}')>")

# 数据库操作类
class ChatDatabase:
    def __init__(self, db_path='chat_sessions.db'):
        db_dir = get_app_dir() + "/history"
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # 创建数据库引擎
        self.engine = create_engine(f'sqlite:///{db_dir}/{db_path}')
        # 创建所有表结构
        Base.metadata.create_all(self.engine)
        # 创建会话工厂
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        # 添加锁
        self.lock = threading.Lock()

    def save_chat_session(self, chat_session):
        with self.lock:
            try:
                self.session.add(chat_session)
                self.session.commit()
                return chat_session.id
            except Exception as e:
                logging.error(f"保存聊天会话时出错: {e}")
                self.session.rollback()
            return None

    def get_chat_session(self, session_id):
        return self.session.get(ChatSession, session_id)  # 使用Session.get()

    def get_all_chat_sessions(self):
        return self.session.query(ChatSession).all()

    def save_chat_content(self, chat_content):
        with self.lock:
            try:
                self.session.add(chat_content)
                self.session.commit()
                return chat_content.id
            except Exception as e:
                self.session.rollback()
                print(f"保存聊天内容时出错: {e}")
                return None

    def close(self):
        self.session.close()

    def search_chat_content_by_session_id(self, session_id):
        return self.session.query(ChatContent).filter(ChatContent.session_id == session_id).order_by(ChatContent.occurred_time).all()


if __name__ == "__main__":
    db = ChatDatabase()

    start_time = datetime.datetime.now()
    end_time = start_time
    chat_session = ChatSession(
        start_time=start_time,
        end_time=end_time,
    )
    session_id = db.save_chat_session(chat_session)

    question1 = ChatContent(
        session_id=session_id,
        type="Question",
        content="你好，今天天气如何？"
    )
    db.save_chat_content(question1)

    answer1 = ChatContent(
        session_id=session_id,
        type="Answer",
        content="你好！我无法获取实时天气数据。你可以通过天气预报网站或应用查询当地天气。"
    )
    db.save_chat_content(answer1)

    chat_session.end_time = datetime.datetime.now()
    db.save_chat_session(chat_session)
    print(f"对话会话已保存，ID: {session_id}")

    saved_session = db.get_chat_session(session_id)
    print(f"查询结果: {saved_session}")

    # 测试搜索方法
    chat_contents = db.search_chat_content_by_session_id(session_id)
    for content in chat_contents:
        print(content)

    db.close()

