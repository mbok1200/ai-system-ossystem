import json
import os
import logging
from typing import List, Dict
from openai import OpenAI
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from interfaces.dialogue_state import DialogueState
from tools.config.functions import get_functions
class RAGEngine:
    """Система пошуку через Pinecone RAG"""
    
    def __init__(self, pinecone_index_name: str = "streamlit"):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Ініціалізація Pinecone (новий API)
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    
        self.index_name = pinecone_index_name
        self.index = self.pc.Index(pinecone_index_name)
        self._detect_embedding_model()
        self._log_index_stats()
    
    def _detect_embedding_model(self):
        """Автоматичне визначення моделі embedding"""
        try:
            stats = self.index.describe_index_stats()
            dimension = stats.dimension
            
            if dimension == 1536:
                self.embedding_model = "text-embedding-ada-002"
            elif dimension == 768:
                self.embedding_model = "local"  # Використовуємо локальну модель
            elif dimension == 3072:
                self.embedding_model = "text-embedding-3-large"
            else:
                self.embedding_model = "local"  # fallback
                
        except Exception as e:
            self.embedding_model = "local"
    
    def _log_index_stats(self):
        try:
            stats = self.index.describe_index_stats()
            if stats.namespaces:
                for ns, data in stats.namespaces.items():
                    ns_name = ns if ns else "''"
                    print(f"   Namespace {ns_name}: {data['vector_count']} векторів")
        except Exception as e:
            print(f"❌ Помилка отримання статистики: {e}")

    def search(self, query: str, top_k: int = 5) -> Dict:
        try:
            stats = self.index.describe_index_stats()
            total_vectors = stats.total_vector_count                   
            if total_vectors == 0:
                return {
                    'success': False,
                    'context': '',
                    'score': 0.0,
                    'sources': [],
                    'raw_results': [],
                    'message': 'База знань порожня'
                }
            
            # Генеруємо embedding для запиту
            embedding = self._get_embedding(query)
            
            # Шукаємо в default namespace (де більше векторів)
            results = self.index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True,
                namespace="default"  # ← Ключове виправлення!
            )
                    
            # Якщо в default мало результатів, спробуємо порожній namespace
            if len(results.matches) < top_k // 2:
                empty_results = self.index.query(
                    vector=embedding,
                    top_k=top_k,
                    include_metadata=True,
                    namespace=""  # Порожній namespace
                )                
                # Об'єднуємо результати
                all_matches = list(results.matches) + list(empty_results.matches)
                # Сортуємо за score
                all_matches.sort(key=lambda x: x.score, reverse=True)
                results.matches = all_matches[:top_k]
            
            if not results.matches:
                return {
                    'success': False,
                    'context': '',
                    'score': 0.0,
                    'sources': [],
                    'raw_results': [],
                    'message': 'В базі знань нічого не знайдено'
                }
            
            # Збираємо всі результати для відображення
            all_results = []
            context_parts = []
            sources = []
            total_score = 0
            
            # Відсортуємо всі результати за score (від найбільшого до найменшого)
            sorted_matches = sorted(results.matches, key=lambda x: x.score, reverse=True)

            # Фільтруємо всі з score > 0.73
            relevant_matches = [m for m in sorted_matches if m.score > 0.73]

            # Якщо релевантних менше 2, добираємо ще найближчі (найвищі за score)
            if len(relevant_matches) < 2:
                relevant_matches = sorted_matches[:2]

            for i, match in enumerate(relevant_matches, 1):
                result_info = {
                    'rank': i,
                    'score': round(match.score, 3),
                    'id': match.id,
                    'text': match.metadata.get('text', ''),
                    'source': match.metadata.get('source', 'Unknown'),
                    'title': match.metadata.get('title', 'Без назви'),
                    'is_relevant': match.score > 0.73
                }
                all_results.append(result_info)
                context_parts.append(match.metadata.get('text', ''))
                sources.append({
                    'id': match.id,
                    'score': match.score,
                    'source': match.metadata.get('source', 'Unknown'),
                    'title': match.metadata.get('title', 'Без назви')
                })
                total_score += match.score

            avg_score = total_score / len(sources) if sources else 0

            return {
                'success': len(context_parts) > 0,
                'context': '\n\n'.join(context_parts),
                'score': avg_score,
                'sources': sources,
                'raw_results': all_results,
                'total_found': len(results.matches),
                'relevant_count': len(context_parts),
                'message': f'Знайдено {len(results.matches)} документів, {len(context_parts)} релевантних'
            }
            
        except Exception as e:
            return {
                'success': False,
                'context': '',
                'score': 0.0,
                'sources': [],
                'raw_results': [],
                'error': str(e),
                'message': f'Помилка пошуку: {str(e)}'
            }
    
    def _get_embedding(self, text: str) -> List[float]:
        """Отримання embedding (той же метод що і в DocumentLoader)"""
        try:
            if self.embedding_model == "local":
                return self._get_local_embedding(text)
            else:
                response = self.openai_client.embeddings.create(
                    input=text,
                    model=self.embedding_model
                )
                return response.data[0].embedding
        except Exception as e:
            return self._get_local_embedding(text)
    
    def _get_local_embedding(self, text: str) -> List[float]:
        """Локальний embedding (точно той же що DocumentLoader)"""
        try:            
            # Ініціалізуємо модель якщо ще не ініціалізована
            if not hasattr(self, '_local_model'):
                # Використовуємо ТУ Ж САМУ модель що і DocumentLoader
                self._local_model = SentenceTransformer('intfloat/multilingual-e5-base')
            
            embedding = self._local_model.encode(text).tolist()
            
            # Перевіряємо розмірність
            stats = self.index.describe_index_stats()
            expected_dim = stats.dimension
            
            if len(embedding) != expected_dim:                
                if len(embedding) > expected_dim:
                    embedding = embedding[:expected_dim]
                elif len(embedding) < expected_dim:
                    # Розширюємо вектор
                    while len(embedding) < expected_dim:
                        remaining = expected_dim - len(embedding)
                        if remaining >= len(embedding):
                            embedding.extend(embedding)
                        else:
                            embedding.extend(embedding[:remaining])
                    embedding = embedding[:expected_dim]
            
            return embedding
            
        except ImportError:
            raise Exception("Встановіть: pip install sentence-transformers")
        except Exception as e:
            raise e
    
    def generate_answer(self, query: str, context: str, state: DialogueState) -> DialogueState:
        """Генерація відповіді на основі контексту"""
        try:
            # Отримуємо функції
            functions = get_functions()
            
            # Логування вхідних даних
            logging.info(f"🔍 Генерую відповідь для запиту: {query[:100]}...")
            logging.info(f"📝 Контекст довжина: {len(context)} символів")
            
            system_prompt = f"""Ти корисний асистент. Відповідай українською мовою на основі наданого контексту.

КОНТЕКСТ ДЛЯ АНАЛІЗУ:
{context}

ІНСТРУКЦІЇ:
1. Якщо запит стосується управління завданнями Redmine (номери завдань, статуси, години), викликай відповідну функцію
2. Якщо запит про загальну інформацію, використовуй контекст для відповіді
3. Якщо в контексті немає потрібної інформації, скажи що не знаєш
4. Відповідай детально та структуровано
5. Завжди використовуй українську мову
6. Якщо є функції, які потрібно викликати, вкажи їх у відповіді"""

            # Формуємо повідомлення
            messages = state.messages.copy() if state.messages else []
            messages.append({
                "role": "system", 
                "content": system_prompt
            })
            messages.append({
                "role": "user",
                "content": query
            })
            
            logging.info(f"🚀 Відправляю запит до OpenAI (model: gpt-4)")
            
            # Викликаємо OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4.1-nano",  # Змінено на більш стабільну модель
                messages=messages,
                temperature=0.3,
                max_tokens=1500,  # Збільшено ліміт
                functions=functions,
                function_call="auto"
            )
            
            message = response.choices[0].message
            logging.info(f"✅ Отримано відповідь від OpenAI")
            
            # Перевіряємо чи є function call
            if message.function_call:
                function_name = message.function_call.name
                try:
                    function_args = json.loads(message.function_call.arguments)
                    logging.info(f"🔧 Викликана функція: {function_name} з аргументами: {function_args}")
                    
                    # Оновлюємо стан
                    state.user_input = query
                    state.user_id = str(os.getenv("REDMINE_USER_ID", "1"))  # Гарантуємо строку
                    state.intent = function_name
                    state.function_calls = [{
                        "name": function_name,
                        "arguments": function_args
                    }]
                    state.current_node = function_name
                    
                    logging.info(f"📝 Стан оновлено для function call")
                    
                except json.JSONDecodeError as je:
                    logging.error(f"❌ Помилка парсингу function arguments: {je}")
                    state.context = f"❌ Помилка обробки функції: {function_name}. Неправильні аргументи."
                
            else:
                # Звичайна відповідь без function call
                answer = message.content
                if answer:
                    state.context = answer
                    logging.info(f"✅ Згенеровано відповідь: {answer[:100]}...")
                else:
                    state.context = "❌ OpenAI повернув порожню відповідь"
                    logging.warning("⚠️ OpenAI повернув порожню відповідь")
        
        except Exception as e:
            # Детальне логування помилки
            logging.error(f"❌ Помилка в generate_answer: {e}", exc_info=True)
            
            # Різні типи помилок
            if "rate limit" in str(e).lower():
                error_msg = "❌ Перевищено ліміт запитів до OpenAI. Спробуйте через хвилину."
            elif "api key" in str(e).lower():
                error_msg = "❌ Проблема з API ключем OpenAI. Перевірте налаштування."
            elif "timeout" in str(e).lower():
                error_msg = "❌ Тайм-аут запиту до OpenAI. Спробуйте ще раз."
            else:
                error_msg = f"❌ Помилка генерації відповіді: {str(e)}"
            
            state.context = error_msg
        return state
    
    def format_search_results(self, rag_result: Dict) -> str:
        """Форматування результатів пошуку для відображення"""
        if not rag_result.get('raw_results'):
            return "🔍 Результатів пошуку немає"
        
        output = []
        output.append(f"🔍 **Результати пошуку в базі знань:**")
        output.append(f"📊 {rag_result.get('message', '')}")
        output.append("")
        
        for result in rag_result['raw_results']:
            relevance_icon = "✅" if result['is_relevant'] else "⚠️"
            score_percent = f"{result['score']*100:.1f}%"
            
            output.append(f"{relevance_icon} **#{result['rank']} - {result['title']}** ({score_percent})")
            
            # Показуємо перші 150 символів тексту
            text_preview = result['text'][:150] + "..." if len(result['text']) > 150 else result['text']
            output.append(f"📄 {text_preview}")
            output.append(f"🏷️ Джерело: {result['source']}")
            output.append("")
        
        return "\n".join(output)