import json
import gradio as gr
import os
from typing import Dict
from dotenv import load_dotenv
from ai_system import AISystem
from history_manager import AdvancedHistoryManager
from interfaces.dialogue_state import DialogueState

load_dotenv(".env")
history_manager = AdvancedHistoryManager()
def load_file_map() -> Dict[str, str]:
    file_map = {}
    try:
        # Try UTF-8 first, then fallback to other encodings
        encodings_to_try = ['utf-8', 'utf-8-sig', 'cp1251', 'latin1']
        
        for encoding in encodings_to_try:
            try:
                with open("./data/gdrive_file_map.json", "r", encoding=encoding) as f:
                    file_map = json.load(f)
                print(f"✅ File map loaded successfully with {encoding} encoding")
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            print("❌ Could not decode file with any encoding, using empty map")
            
    except FileNotFoundError:
        print("⚠️ Файл gdrive_file_map.json не знайдено, створюю порожню мапу")
        # Create the data directory and empty file if it doesn't exist
        os.makedirs("./data", exist_ok=True)
        with open("./data/gdrive_file_map.json", "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print("⚠️ Using empty file map")
    except Exception as e:
        print(f"❌ Unexpected error loading file map: {e}")
        print("⚠️ Using empty file map")
    
    return file_map
file_map = load_file_map()

ai_system = AISystem(state=DialogueState())
def load_previous_session(session_list: str, session_state: dict) -> tuple:
    if session_list:
        # Створюємо новий dict якщо session_state є tuple або None
        if not isinstance(session_state, dict):
            session_state = {}
            
        session_state["session_id"] = session_list
        
        # Переконайтеся, що history_manager повертає правильний формат
        history = history_manager.get_session_history(session_list, format_type="messages")
        
        # Перевіряємо і конвертуємо формат якщо потрібно
        formatted_history = []
        for msg in history:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                formatted_history.append(msg)
            elif isinstance(msg, (list, tuple)) and len(msg) >= 2:
                # Конвертуємо старий формат [user_msg, bot_msg] в новий
                formatted_history.append({"role": "user", "content": str(msg[0])})
                formatted_history.append({"role": "assistant", "content": str(msg[1])})
        
        return formatted_history, session_state
    return [], session_state if isinstance(session_state, dict) else {}

def clear_chat(session_state: dict) -> tuple:
    """Створює нову сесію та очищає чат"""
    if not isinstance(session_state, dict):
        session_state = {}
        
    new_session_id = history_manager.create_session()
    session_state["session_id"] = new_session_id
    # Повертаємо порожній список для chatbot та оновлений session_state
    return [], session_state

def chat_interface(message: str, history: list, mode: str, session_state: dict) -> tuple:
    # Створюємо новий dict якщо session_state є tuple або None
    if not isinstance(session_state, dict):
        session_state = {}
   
    if "session_id" not in session_state:
        session_state["session_id"] = history_manager.create_session({
            "mode": mode,
            "created_by": "gradio_interface"
        })
    
    session_id = session_state["session_id"]
    ai_system.state.update(
        user_input=message,
        session_state=session_state,
    )
    user_message = {"role": "user", "content": message}
    history.append(user_message)
    history_manager.save_message(session_id, "user", message)
    # Додаємо прелоадер у чат
    loader_message = {"role": "assistant", "content": "⏳ Асистент друкує..."}
    history.append(loader_message)
    yield "", history, session_state

    try:
        result = ai_system.process_query()
        response = result.response_messages[-1]["content"] if result.response_messages else "Вибачте, не вдалося обробити ваш запит."
        # Видаляємо прелоадер
        history = [msg for msg in history if msg != loader_message]
        assistant_message = {"role": "assistant", "content": response}
        history.append(assistant_message)
        history_manager.save_message(session_id, "assistant", response)
        yield "", history, session_state
    except Exception as e:
        history = [msg for msg in history if msg != loader_message]
        error_message = f"❌ Помилка: {str(e)}"
        error_response = {"role": "assistant", "content": error_message}
        history.append(error_response)
        yield "", history, session_state

def create_interface():
    """Створення Gradio інтерфейсу"""
    
    # Кастомний CSS
    css = """
    .gradio-container {
        max-width: 1200px !important;
        margin: 0 auto;
        width: 100% !important;
        height: 100% !important;
    }
    .chat-message {
        padding: 10px;
        margin: 5px 0;
        border-radius: 10px;
    }
    """

    # Функція для отримання списку сесій
    def get_session_choices():
        try:
            sessions = history_manager.get_sessions()
            return [
                (f"Сесія {s['session_id'][:8]}... ({s['message_count']} повідомлень)", s['session_id'])
                for s in sessions
            ]
        except Exception as e:
            print(f"Error getting sessions: {e}")
            return []

    with gr.Blocks(title="🤖 AI Assistant", css=css, theme=gr.themes.Soft(), fill_height=True, fill_width=True) as app:
        # Ініціалізуємо State з початковим значенням dict
        session_state = gr.State(value={})
        
        gr.Markdown(
            """
            # 🤖 AI Assistant RAG + Function Calling + Google Search
            Система поєднує: 📚 **RAG**, 🔧 **Function Calling**, 🔍 **Google Search** 
            """
        )
        
        with gr.Row(scale=2):
            with gr.Column():
                chatbot = gr.Chatbot(
                    height=500,
                    placeholder="Напишіть запит і я допоможу знайти інформацію...",
                    avatar_images=(
                        "https://cdn-icons-png.flaticon.com/512/3135/3135715.png",  # користувач
                        "https://cdn-icons-png.flaticon.com/512/4712/4712027.png"   # бот
                    ),
                    type="messages"
                )

                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="Введіть ваш запит тут...",
                        container=False,
                        scale=4
                    )
                    send_btn = gr.Button("Відправити", variant="primary", scale=1)

                # Кнопка очищення
                clear_btn = gr.ClearButton([msg, chatbot], value="🗑️ Очистити")
                
        with gr.Sidebar(position="left"):
            with gr.Column(scale=1):
                gr.Markdown("## 💡 Приклади запитів:")
                
                examples = [
                    "🎯 завдання #12345",
                    "📅 завдання на сьогодні", 
                    "⏰ заповнити 4 години для #12345",
                    "📊 статус завдання Bug 123",
                    "👤 мої завдання",
                    "🔍 пошук у Redmine API",
                    "📚 wiki інформація про проект",
                    "❓ що таке штучний інтелект?"
                ]
                
                for example in examples:
                    gr.Markdown(example)
                    
                # with gr.Group():
                #     gr.Markdown("## 🚀 Швидкі режими:")
                    
                #     mode_buttons = gr.Radio(
                #         choices=[
                #             ("📚 Тільки Redmine", "redmine"),
                #             ("🔍 База + веб-пошук", "hybrid"),
                #             ("🌐 Тільки веб-пошук", "web_only")
                #         ],
                #         value="hybrid",
                #         label="Режим роботи:",
                #         info="Оберіть стратегію пошуку"
                #     )
                    
                # gr.Markdown("## ℹ️ Статус системи:")
                
                # Перевірка статусу компонентів
                status_info = []
                
                # # Pinecone
                # pinecone_status = "✅" if os.getenv("PINECONE_API_KEY") else "❌"
                # status_info.append(f"{pinecone_status} Pinecone RAG")
                
                # # OpenAI
                # openai_status = "✅" if os.getenv("OPENAI_API_KEY") else "❌"
                # status_info.append(f"{openai_status} OpenAI")
                
                # # Redmine
                # redmine_status = "✅" if os.getenv("REDMINE_API_KEY") else "❌"
                # status_info.append(f"{redmine_status} Redmine API")
                
                # # Google
                # google_status = "✅" if os.getenv("GOOGLE_API_KEY") else "❌"
                # status_info.append(f"{google_status} Google Search")
                
                # gr.Markdown("\n\n".join(status_info))
                
        # with gr.Sidebar(position="right"):
        #     gr.Markdown("## 📚 Історія сесій")
            
        #     # Dropdown для вибору сесії з початковими choices
        #     session_dropdown = gr.Dropdown(
        #         choices=get_session_choices(),  # Ініціалізуємо з поточними сесіями
        #         label="Попередні сесії",
        #         info="Виберіть сесію для продовження",
        #         allow_custom_value=False
        #     )

        #     load_session_btn = gr.Button("📂 Завантажити сесію", size="sm")
        #     refresh_sessions_btn = gr.Button("🔄 Оновити список", size="sm")
        #     remove_sessions_btn = gr.Button("🗑️ Видалити сесію", size="sm")

        # Event handlers - after all components are defined
        # def refresh_sessions():
        #     """Оновлює список сесій в dropdown"""
        #     new_choices = get_session_choices()
        #     return gr.Dropdown(choices=new_choices, value=None)
        # def remove_session(input_session: str):
        #     history_manager.delete_session(input_session)
        # load_session_btn.click(
        #     load_previous_session,
        #     inputs=[session_dropdown, session_state],
        #     outputs=[chatbot, session_state]
        # )
        
        # refresh_sessions_btn.click(
        #     refresh_sessions, 
        #     outputs=[session_dropdown]
        # )
        # remove_sessions_btn.click(
        #     remove_session,
        #     inputs=[session_dropdown]
        # )
        # Chat events
        msg.submit(
            chat_interface, 
            inputs=[msg, chatbot, session_state], 
            outputs=[msg, chatbot, session_state], 
            queue=True
        )
        
        send_btn.click(
            chat_interface, 
            inputs=[msg, chatbot, session_state], 
            outputs=[msg, chatbot, session_state], 
            queue=True
        )
        
        # Clear button event - потрібно оновити outputs
        clear_btn.click(
            clear_chat,
            inputs=[session_state],
            outputs=[chatbot, session_state]  # Додано chatbot для очищення чату
        )
    
    return app

if __name__ == "__main__":
    required_vars = [
        "OPENAI_API_KEY",
        "PINECONE_API_KEY", 
        "PINECONE_ENV",
        "PINECONE_INDEX_NAME"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    # Запускаємо інтерфейс
    app = create_interface()
    app.queue(max_size=20)
    app.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        show_error=True
    )