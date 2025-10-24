# -*- coding: utf-8 -*-
from decouple import config
from langchain_openai import ChatOpenAI
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
import os, base64
import re

OPENAI_KEY = "OPENAI_KEY"

st.set_page_config(layout="wide") 
st.session_state.theme = "dark"  

# 如果想通过mitmproxy调试程序, 打开这个注释
#os.environ["HTTP_PROXY"] = "http://127.0.0.1:8080"
#os.environ["HTTPS_PROXY"] = "http://127.0.0.1:8080"

# v1.6 72B
# llm = ChatOpenAI(openai_api_base="http://180.76.114.40/auth/s-r4bd4d7991d7/8000/v1",
#        model="DolphinUltrasoundV16R1",
#        api_key=os.getenv("DELPHIN_V16_72B_API_KEY"),
#        max_tokens=2048)

# v1.9 7B
#llm = ChatOpenAI(openai_api_base="http://180.76.114.40/auth/s-r67c16319ee6/8000/v1",
#                      model="DolphinUltrasoundV19",
#                      api_key=os.getenv("DELPHIN_V19_7B_API_KEY"),
#                      max_tokens=2048)

# v1.9 72B
llm = ChatOpenAI(openai_api_base="http://180.76.114.40/auth/s-rd21ade7a13b/8000/v1",
                      model="DolphinUltrasoundV19",
                      api_key=os.getenv("DELPHIN_V19_72B_API_KEY"),
                      max_tokens=2048)

default_system_prompt = (
    "你是‘海豚超声智能诊断助手’，一个专注于医学超声图像分析与诊断的人工智能系统。"
    "你通过文本与用户交流，致力于为临床医生、科研人员和相关用户提供清晰、精准、全面且可靠的医学建议。"
    "你的核心任务是基于深厚的医学知识、影像学原理及最新研究成果，辅助用户对超声图像进行分析判断、病灶识别、初步诊断和临床解释，"
    "同时全面地回答用户提出的各类问题，包括但不限于科学知识、历史文化、技术原理、生活常识等。"
    "回答时请遵循以下原则："
    "- 若问题为观点类探讨，需从多角度分析，并结合客观依据给出合理观点，"
    "- 对疑难病灶或不确定的影像特征，应列出可能性，并说明诊断依据及其不确定性。"
    "- 结合图像特征、解剖部位、常见病变、临床表现等多个角度分析问题，帮助用户做出更全面的判断。"
    "- 对于复杂问题，可拆解为多个步骤逐步解答，确保逻辑连贯。"
    "- 当用户有特定风格（如幽默、正式）或格式（如表格、代码）要求时，严格遵循；"
    "- 用户导向输出："
    "- 若用户要求具体格式（如表格、术语解释、分级描述），需严格遵循；"
    "- 若用户为非专业人员，避免术语堆砌，提供简洁解释；"
    "- 若用户为专业医生，可适当引入规范术语与操作建议。"
    "- 回复为用户提问所用的语言，回复内容不能过于简洁 ")
deep_thinking_prompt = (
    "你是“海豚超声智能诊断助手”，一个专注于医学超声图像分析与诊断的人工智能系统。"
    "To answer the user's question, you first think about the reasoning process and then provide the user with the answer."
    "The reasoning process is enclosed within <think> </think> tags, respectively, i.e., <think> reasoning process here </think> ."
)

def get_session_id():
    ctx = get_script_run_ctx()
    return ctx.session_id if ctx else None

# 初始化会话状态
if 'user_states' not in st.session_state:
    st.session_state.user_states = {}

# 添加深度思考开关，加大字体
deep_thinking = st.checkbox("深度思考(Deep Thinking)", value=True)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def process_image(file, session_id):
    try:
        with st.spinner("Processing image..."):
            data = file.read()
            file_name = os.path.join("./", file.name)

            with open(file_name, "wb") as f:
                f.write(data)
            image = encode_image(file_name)
            st.session_state.user_states[session_id]['encoded_image'] = image
            st.image(file, caption='Uploaded Image')

            if "uploaded_file_name" in st.session_state.user_states[session_id]:
                if st.session_state.user_states[session_id]["uploaded_file_name"] != file_name:
                    clear_history(session_id)

            st.session_state.user_states[session_id]["uploaded_file_name"] = file_name
    except Exception as e:
        st.error(f"文件处理出错: {e}")

def clear_history(session_id):
    #print(f"call clear_history()")
    st.session_state.user_states[session_id]['history'].messages = []
    system_prompt = deep_thinking_prompt if deep_thinking else default_system_prompt
    st.session_state.user_states[session_id]['text_chain'] = build_text_chain(system_prompt, session_id)
    st.session_state.user_states[session_id]['multimodal_chain'] = build_multimodal_chain(system_prompt, session_id)

def clear_conversation(session_id):
    """清除对话历史"""
    st.session_state.user_states[session_id]['history'].clear()
    
    # 清除图像相关状态
    if "encoded_image" in st.session_state.user_states[session_id]:
        del st.session_state.user_states[session_id]["encoded_image"]
    if "uploaded_file_name" in st.session_state.user_states[session_id]:
        del st.session_state.user_states[session_id]["uploaded_file_name"]
    
    # 重新初始化chains
    system_prompt = deep_thinking_prompt if deep_thinking else default_system_prompt
    st.session_state.user_states[session_id]['text_chain'] = build_text_chain(system_prompt, session_id)
    st.session_state.user_states[session_id]['multimodal_chain'] = build_multimodal_chain(system_prompt, session_id)
    st.success("对话历史已清除！")
    st.rerun()

def filter_think_tags(text):
    text = text.replace("[指令]请先生成 <think> 推理过程，再回答：", '')
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return text

# 构建纯文本chain的函数
def build_text_chain(system_prompt, session_id):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ]
    )
    chain = prompt | llm
    chain_with_history = RunnableWithMessageHistory(
        chain,
        lambda _: st.session_state.user_states[session_id]['history'],
        input_messages_key="input",
        history_messages_key="chat_history",
        Temperature=0.9
    )
    return chain_with_history

# 构建多模态chain的函数
def build_multimodal_chain(system_prompt, session_id):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            (
                "human",
                [
                    {"type": "text", "text": "{input}"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64," "{image}",
                            "detail": "low",
                        },
                    },
                ],
            ),
        ]
    )
    chain = prompt | llm
    chain_with_history = RunnableWithMessageHistory(
        chain,
        lambda _: st.session_state.user_states[session_id]['history'],
        input_messages_key="input",
        history_messages_key="chat_history",
    )
    return chain_with_history

def ask_question(question, session_id):
    #if deep_thinking:
    #    question = f"[指令]请先生成 <think> 推理过程，再回答：{question}"

    with st.chat_message("user"):
        st.markdown(question)
    
    # 检查开关状态是否改变
    if deep_thinking != st.session_state.user_states[session_id]['current_deep_thinking_state']:
        st.session_state.user_states[session_id]['current_deep_thinking_state'] = deep_thinking
        clear_history(session_id)
    
    # 如果chain还没有初始化，初始化它们
    system_prompt = deep_thinking_prompt if deep_thinking else default_system_prompt
    if st.session_state.user_states[session_id]['text_chain'] is None:
        st.session_state.user_states[session_id]['text_chain'] = build_text_chain(system_prompt, session_id)
    if st.session_state.user_states[session_id]['multimodal_chain'] is None:
        st.session_state.user_states[session_id]['multimodal_chain'] = build_multimodal_chain(system_prompt, session_id)

    for message in st.session_state.user_states[session_id]['history'].messages:
        message.content = filter_think_tags(message.content)

    try:
        # 根据是否有图像选择不同的chain
        if "encoded_image" in st.session_state.user_states[session_id]:
            # 有图像时使用多模态chain
            image = st.session_state.user_states[session_id]["encoded_image"]
            response = st.session_state.user_states[session_id]['multimodal_chain'].stream(
                {"input": question, "image": image},
                config={"configurable": {"session_id": "any"}},
            )
        else:
            # 没有图像时使用纯文本chain
            response = st.session_state.user_states[session_id]['text_chain'].stream(
                {"input": question},
                config={"configurable": {"session_id": "any"}},
            )
        
        with st.chat_message("assistant"):
            st.write_stream(response)
    except Exception as e:
        st.error(f"后台错误，请稍后再试. {e}")

st.title("海豚超声大模型")

# 创建左右两列
left_column, spacer, right_column = st.columns([20, 1, 15])

session_id = get_session_id()
if session_id not in st.session_state.user_states:
    st.session_state.user_states[session_id] = {
        'current_deep_thinking_state': deep_thinking,
        'text_chain': None,
        'multimodal_chain': None,
        'history': StreamlitChatMessageHistory(),
        'encoded_image': None,
        'uploaded_file_name': None
    }

# 左边列用于图片上传
with left_column:
    # 修改这里，添加 'bmp' 到文件类型列表
    uploaded_file = st.file_uploader("上传超声图片 (可选): ", type=["jpg", "png", "bmp"])
    if uploaded_file:
        process_image(uploaded_file, session_id)

# 右边列用于对话
with right_column:
    # 添加清除对话按钮
    if st.button("🗑️ 清除对话", type="secondary"):
        clear_conversation(session_id)
    
    question = st.chat_input("提问")

    for message in st.session_state.user_states[session_id]['history'].messages:
        role = "user" if message.type == "human" else "assistant"
        with st.chat_message(role):
            st.markdown(message.content)

    if question:
        ask_question(question, session_id)

