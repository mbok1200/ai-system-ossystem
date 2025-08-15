import os
from dotenv import load_dotenv
from rag_engine import RAGEngine
from tools.google_search import GoogleSearchTool
from workflow import Workflow
from openai import OpenAI
from interfaces.dialogue_state import DialogueState
load_dotenv(".env")

class AISystem:
    def __init__(self, state: DialogueState = None):
        openai_api_key = os.getenv("OPENAI_API_KEY")
        pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")
        self.rag_engine = RAGEngine(
            pinecone_index_name=pinecone_index_name
        )
        self.google_search = GoogleSearchTool()
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.workflow = Workflow(self.openai_client)
        self.state = state if state else DialogueState(
            user_input="",
            current_node="analyze_intent"
        )
    def process_query(self) -> DialogueState:
        """Основна логіка обробки запиту з режимами роботи"""
        if not self.state.user_input.strip():
            self.state.response_messages.append({
                "role": "assistant",
                "content": "❓ Будь ласка, введіть запит"
            })
            return self.state
        self.state = self._process_redmine()
        return self.state

    def _process_redmine(self) -> DialogueState:
        try:
            rag_result = self.rag_engine.search(self.state.user_input)
            self.state.RAG_context = ""
            if rag_result['success'] and rag_result['score'] > 0.75:
                self.state.RAG_context = rag_result['context']
                self.state.sources = rag_result['sources']
        except Exception as e:
            print(f"RAG пошук помилка: {e}")
        try:
            response = self.workflow.process_user_input(self.state)
            return response
        except Exception as e:
            print(f"Function calling помилка: {e}")