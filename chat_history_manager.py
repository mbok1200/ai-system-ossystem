from langchain.memory import ConversationBufferWindowMemory, ConversationSummaryBufferMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from typing import List, Dict
import json
import os
class ChatHistoryManager:
    def __init__(self, max_token_limit: int = 2000, k: int = 10):
        self.window_memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            k=k,
            return_messages=True,
        )
        self.summary_memory = ConversationSummaryBufferMemory(
            memory_key="chat_summary",
            max_token_limit=max_token_limit,
            return_messages=True,
        )

    def add_message(self, user_message: str, ai_response: str):
        self.window_memory.chat_memory.add_user_message(user_message)
        self.window_memory.chat_memory.add_ai_message(ai_response)

        self.summary_memory.chat_memory.add_user_message(user_message)
        self.summary_memory.chat_memory.add_ai_message(ai_response)

    def get_history(self, format_type: str = "gradio") -> List:
        messages = self.window_memory.chat_memory.messages
        if format_type == "gradio":
            history = []
            for i in range(0, len(messages), 2):
                if i + 1 < len(messages):
                    user_msg = messages[i].content
                    ai_msg = messages[i + 1].content
                    history.append([user_msg, ai_msg])
            return history
        elif format_type == "openai":
            return  [
                {"role": "user" if isinstance(msg, HumanMessage) else "assistant", 
                 "content": msg.content}
                for msg in messages
            ]
    def clear_history(self):
        self.window_memory.clear()
        self.summary_memory.clear()
    def save_to_file(self, file_path: str):
        history = self.get_history("openai")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    def load_from_file(self, filepath: str):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            self.clear_history()
            for msg in history:
                if msg["role"] == "user":
                    self.window_memory.chat_memory.add_user_message(msg["content"])
                    self.summary_memory.chat_memory.add_user_message(msg["content"])
                elif msg["role"] == "assistant":
                    self.window_memory.chat_memory.add_ai_message(msg["content"])
                    self.summary_memory.chat_memory.add_ai_message(msg["content"])
        except FileNotFoundError:
            pass
