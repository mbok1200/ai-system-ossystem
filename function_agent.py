import json
import re
from typing import Dict, List, Optional, Any
import logging

class FunctionAgent:
    """Агент для обробки function calling з LoRA адаптером на Gemma2-2B"""
    
    def __init__(self, base_model_path: str = None, lora_path: str = None):        
        self.function_examples = self._load_dataset()
        # Мапінг функцій залишається той же
        self.function_registry = {
            'check_have_access': self.access_to_redmine,
            'get_issue_by_date': self._get_issue_by_date,
            'get_issue_by_id': self._get_issue_by_id,
            'get_issue_by_name': self._get_issue_by_name,
            'get_issue_status': self._get_issue_status,
            'get_issue_hours': self._get_issue_hours,
            'fill_issue_hours': self._fill_issue_hours,
            'get_user_status': self._get_user_status,
            'set_user_status': self._set_user_status,
            'create_issue': self._create_issue,
            'assign_issue': self._assign_issue,
            'get_wiki_info': self._get_wiki_info
        }
    def _simple_response_analysis(self, response: str, query: str) -> Dict[str, Any]:
        """Простий аналіз відповіді якщо JSON не знайдено"""
        
        query_lower = query.lower()
        
        # Розширені ключові слова для функцій
        function_keywords = {
            'create_issue': ['створити', 'create', 'додати', 'add', 'нове завдання', 'new task'],
            'assign_issue': ['призначити', 'assign', 'назначити', 'на мене', 'to me'],
            'get_issue_by_id': ['завдання #', 'задача #', 'issue #', 'task #', '#', 'user story'],
            'get_issue_by_date': ['сьогодні', 'вчора', 'завтра', 'дата', 'today', 'yesterday', 'tomorrow'],
            'fill_issue_hours': ['заповнити', 'години', 'hour', 'time', 'годин'],
            'get_issue_status': ['статус', 'status'],
            'get_user_status': ['мої завдання', 'my tasks', 'мої', 'користувач']
        }
        
        detected_functions = []
        
        # Перевіряємо всі функції
        for func_name, keywords in function_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                
                # Витягуємо аргументи
                arguments = {}
                
                if func_name == 'create_issue':
                    # Витягуємо назву завдання
                    title_match = re.search(r'User story (\d+)', query, re.IGNORECASE)
                    if title_match:
                        arguments['value_1'] = f"User story {title_match.group(1)}"
                    
                    # Витягуємо опис
                    desc_match = re.search(r'- (.+?)(?:,|$)', query)
                    if desc_match:
                        arguments['value_2'] = desc_match.group(1).strip()
                    
                elif func_name == 'assign_issue':
                    # Витягуємо ID завдання
                    task_match = re.search(r'User story (\d+)', query, re.IGNORECASE)
                    if task_match:
                        arguments['value_1'] = f"User story {task_match.group(1)}"
                    
                    # Витягуємо користувача
                    if 'на мене' in query_lower or 'to me' in query_lower:
                        arguments['value_2'] = 'current_user'
                    else:
                        user_match = re.search(r'призначити на (.+?)(?:,|$)', query_lower)
                        if user_match:
                            arguments['value_2'] = user_match.group(1).strip()
                
                elif func_name == 'get_issue_by_id':
                    # Шукаємо номер завдання
                    task_match = re.search(r'#?(\d+)', query)
                    if task_match:
                        arguments['value_1'] = task_match.group(1)
                    
                    # User Story
                    user_story_match = re.search(r'User story (\d+)', query, re.IGNORECASE)
                    if user_story_match:
                        arguments['value_1'] = f"User story {user_story_match.group(1)}"
                
                elif func_name == 'fill_issue_hours':
                    # Шукаємо номер завдання та години
                    task_match = re.search(r'#?(\d+)', query)
                    hours_match = re.search(r'(\d+)\s*годин?', query)
                    if task_match:
                        arguments['value_1'] = task_match.group(1)
                    if hours_match:
                        arguments['value_2'] = int(hours_match.group(1))
                
                detected_functions.append({
                    'name': func_name, 
                    'arguments': arguments,
                    'confidence': 0.8
                })
        
        if detected_functions:
            # Якщо знайдено кілька функцій, повертаємо всі
            return {
                'is_function_call': True,
                'confidence': max(f['confidence'] for f in detected_functions),
                'function_calls': [{'name': f['name'], 'arguments': f['arguments']} for f in detected_functions],
                'explanation': f'Визначено функції: {", ".join(f["name"] for f in detected_functions)}',
                'model_response': response,
                'model_type': 'simple_analysis_multi'
            }
        return {
            'is_function_call': False,
            'confidence': 0.1,
            'message': 'Не вдалося чітко визначити потрібну функцію',
            'model_response': response,
            'model_type': 'simple_analysis'
        }
    
    
    def _load_dataset(self) -> List[Dict]:
        """Завантаження датасету інструкцій"""
        try:
            with open('data/dataset.jsonl', 'r', encoding='utf-8') as f:
                return [json.loads(line) for line in f]
        except FileNotFoundError:
            logging.warning("dataset.jsonl не знайдено")
            return []
    
    def _find_best_match(self, query: str) -> Optional[Dict]:
        """Пошук найбільш схожого прикладу в датасеті"""
        query_lower = query.lower()
        best_score = 0
        best_match = None
        
        for example in self.function_examples:
            example_input = example['input'].lower()
            
            # Простий алгоритм схожості
            score = self._calculate_similarity(query_lower, example_input)
            
            if score > best_score and score > 0.3:  # Поріг схожості
                best_score = score
                best_match = example
        
        return best_match
    
    def _calculate_similarity(self, query: str, example: str) -> float:
        """Розрахунок схожості між запитом і прикладом"""
        # Ключові слова для різних типів запитів
        query_words = set(query.split())
        example_words = set(example.split())
        
        # Jaccard similarity
        intersection = len(query_words.intersection(example_words))
        union = len(query_words.union(example_words))
        
        if union == 0:
            return 0.0
        
        jaccard = intersection / union
        
        # Додаткові бонуси за ключові слова
        bonus = 0
        
        # Номери завдань
        query_numbers = re.findall(r'#?\d+', query)
        example_numbers = re.findall(r'#?\d+', example)
        if query_numbers and example_numbers:
            bonus += 0.2
        
        # Дати
        if re.search(r'\d{1,2}\.\d{1,2}', query) and re.search(r'\d{1,2}\.\d{1,2}', example):
            bonus += 0.2
        
        # Ключові слова завдань
        task_keywords = ['завдання', 'задача', 'таска', 'user story', 'bug']
        if any(word in query for word in task_keywords) and any(word in example for word in task_keywords):
            bonus += 0.3
        
        return min(jaccard + bonus, 1.0)
    
    # Заглушки для функцій (тут підключаються реальні API)
    def access_to_redmine(self, args: Dict, query: str) -> str:
        return "✅ Доступ підтверджено"
    
    def _get_issue_by_date(self, args: Dict, query: str) -> str:
        date = args.get('value_1', 'невідомо')
        return f"📅 Завдання на {date}: Завдання #12345, #12346"
    
    def _get_issue_by_id(self, args: Dict, query: str) -> str:
        issue_id = args.get('value_1', 'невідомо')
        return f"🎯 Завдання {issue_id}: Розробка нової функції"
    
    def _get_issue_by_name(self, args: Dict, query: str) -> str:
        issue_name = args.get('value_1', 'невідомо')
        return f"📋 {issue_name}: Статус - В роботі"
    
    def _get_issue_status(self, args: Dict, query: str) -> str:
        issue = args.get('value_1', 'невідомо')
        return f"📊 Статус {issue}: В роботі"
    
    def _get_issue_hours(self, args: Dict, query: str) -> str:
        issue = args.get('value_1', 'невідомо')
        return f"⏰ {issue}: Витрачено 8 годин"
    
    def _fill_issue_hours(self, args: Dict, query: str) -> str:
        issue = args.get('value_1', 'невідомо')
        hours = args.get('value_2', 0)
        desc = args.get('value_4', '')
        return f"✅ Заповнено {hours} год. для {issue}" + (f" ({desc})" if desc else "")
    
    def _get_user_status(self, args: Dict, query: str) -> str:
        return "👤 Ваш статус: На роботі"
    
    def _set_user_status(self, args: Dict, query: str) -> str:
        status = args.get('value_1', 'невідомо')
        return f"✅ Статус змінено на: {status}"
    
    def _create_issue(self, args: Dict, query: str) -> str:
        title = args.get('value_1', 'Нове завдання')
        description = args.get('value_2', '')
        
        # Симуляція створення завдання
        issue_id = "12345"  # В реальності буде ID з API
        
        result = f"✅ Створено завдання: {title}"
        if description:
            result += f"\n📝 Опис: {description}"
        result += f"\n🆔 ID: #{issue_id}"
        
        return result
    
    def _assign_issue(self, args: Dict, query: str) -> str:
        issue = args.get('value_1', 'невідомо')
        user = args.get('value_2', 'невідомо')
        
        if user == 'current_user':
            user = 'Вас'
        
        result = f"✅ Завдання {issue} призначено на {user}"
        
        return result
    
    def _get_wiki_info(self, args: Dict, query: str) -> str:
        topic = args.get('value_1', 'невідомо')
        return f"📖 Wiki інформація про {topic}: Детальна інформація знайдена"
