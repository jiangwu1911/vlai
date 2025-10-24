import base64
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
import os
import re

class LLMAgent():
    def __init__(self, name, url, model, key):
        self.name = name
        self.url = url
        self.model = model
        self.key = key

        self.llm = ChatOpenAI(openai_api_base=self.url,
                      model=self.model,
                      api_key=self.key,
                      max_tokens=2048)

        # 系统提示词保持不变
        self.default_system_prompt = (
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
        self.deep_thinking_prompt = (
            "你是'海豚超声智能诊断助手'，一个专注于医学超声图像分析与诊断的人工智能系统。"
            "To answer the user's question, you first think about the reasoning process and then provide the user with the answer. "
            "The reasoning process is enclosed within <think> </think> tags, respectively, i.e., <think> reasoning process here </think>"
        )

        self.history = ChatMessageHistory()
        self.chain_with_history = None  # 初始化为 None，将在第一次提问时构建
        self.current_prompt = self.deep_thinking_prompt

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def clean_history_messages(self, messages):
        """清理历史消息，移除 <think> 标签内的内容"""
        cleaned_history = ChatMessageHistory()
        for message in messages:
            content = message.content
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            if content.strip():
                cleaned_history.add_message(message)
        self.history = cleaned_history
        return cleaned_history

    def build_text_chain(self, system_prompt, session_id):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ]
        )
        chain = prompt | self.llm
        chain_with_history = RunnableWithMessageHistory(
            chain,
            #lambda session_id: self.history,
            lambda session_id: self.clean_history_messages(self.history.messages),
            input_messages_key="input",
            history_messages_key="chat_history",
            Temperature=0.9
        )
        return chain_with_history

    def build_multimodal_chain(self, system_prompt, num_images):
        # 动态构建人类消息部分，只包含实际需要的图片变量
        human_messages = [{"type": "text", "text": "{input}"}]
        for i in range(num_images):
            human_messages.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{{image{i}}}",
                    "detail": "low",
                },
            })

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", human_messages),
            ]
        )
        chain = prompt | self.llm
        chain_with_history = RunnableWithMessageHistory(
            chain,
            #lambda session_id: self.history,
            lambda session_id: self.clean_history_messages(self.history.messages),
            input_messages_key="input",
            history_messages_key="chat_history",
            Temperature=0.9
        )
        return chain_with_history

    def clear_history(self):
        self.history.clear()

    def ask_question(self, question, images):
        try:
            # 如果是第一次提问或图片数量变化，重新构建链
            if self.chain_with_history is None or len(images) != self.current_num_images:
                self.current_num_images = len(images)
                if len(images) > 0 and self.name != "RAG":
                    self.chain_with_history = self.build_multimodal_chain(self.current_prompt, self.current_num_images)
                else:
                    self.chain_with_history = self.build_text_chain(self.current_prompt, self.current_num_images)
            
            # 构建输入字典
            question = f"[指令]请先生成 <think> 推理过程，再回答：{question}"
            input_dict = {"input": question}
            if self.name != "RAG":
                for i, image in enumerate(images):
                    input_dict[f"image{i}"] = image

            return self.chain_with_history.stream(
                input_dict,
                config={"configurable": {"session_id": "any"}},
            )
        except Exception as e:
            return f"后台错误，请稍后再试. {e}"
            
    def change_deep_thinking(self, state):
        deep_thinking = (state != 0)
        self.current_prompt = self.default_system_prompt if not deep_thinking else self.deep_thinking_prompt
        # 清空历史记录并重置链，下次提问时会重新构建
        self.clear_history()
        self.chain_with_history = None
        

if __name__ == "__main__":
    openai_api_base = "http://180.76.114.40/auth/s-rd21ade7a13b/8000/v1"
    model = "DolphinUltrasoundV19"
    api_key = os.getenv("DELPHIN_V19_72B_API_KEY")

    agent = LLMAgent(openai_api_base, model, api_key)
    agent.change_deep_thinking(1)
    
    image_files = ["pics/2024_08_01_143715_509.jpg", "pics/2025_05_13_155826_007.jpg"]
    encoded_images = [agent.encode_image(img_path) for img_path in image_files]

    question = "请分析这些图片中的内容，并说明它们之间可能的联系。"
    response = agent.ask_question(question, encoded_images)

    if isinstance(response, str):
        print(response)
    else:
        full_response = ""
        print("正在生成回答...")
        
        for chunk in response:
            content = chunk.content
            if content:
                full_response += content
                print(content, end="", flush=True)

