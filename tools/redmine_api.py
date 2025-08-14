import requests, os
from typing import Dict
from datetime import datetime, timedelta
from interfaces.dialogue_state import DialogueState
from interfaces.redmine_state import RedmineState
from tools.google_search import GoogleSearchTool
class RedmineAPI:
    """Клас для роботи з Redmine API"""
    
    def __init__(self):
        self.state = RedmineState()
        self.google_search = GoogleSearchTool()
        

    def _make_request(self, patch: str, method: str = "GET", params: Dict = None) -> Dict:
        """Базовий метод для HTTP запитів до Redmine"""
        if not self.state.redmine_url or not self.state.redmine_api_key:
            raise Exception("Redmine API не налаштований")
        
        url = f"{self.state.redmine_url}/{patch}.json"
        headers = {
            'X-Redmine-API-Key': self.state.redmine_api_key,
            'Content-Type': 'application/json'
        }
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=params)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=params)
            else:
                raise ValueError(f"Непідтримуваний HTTP метод: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Помилка Redmine API: {str(e)}")

    def access_to_redmine(self, state: DialogueState) -> DialogueState:
        """Перевірка доступу до Redmine API"""
        try:
            url = f"{self.base_url}/issues.json"
            headers = {'X-Redmine-API-Key': self.api_key}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            state.context = "✅ Доступ до Redmine API підтверджено"
            return state
        except Exception as e:
            state.context = f"❌ Помилка доступу до Redmine API: {str(e)}"
            return state
    def get_my_issues(self, state: DialogueState) -> DialogueState:
        """Отримання завдань, призначених користувачу"""
        try:
            params = {
                'assigned_to_id': self.state.user_id,
                'status_id': '*',
                'limit': 5
            }
            data = self._make_request('issues', params=params)
            if not data.get('issues'):
                state.context = "📋 Завдань не знайдено"
                return state
            
            issues_text = [self._format_issue_short(issue) for issue in data['issues']]
            state.context = "📋 Ваші завдання:\n\n" + "\n".join(issues_text)
            return state
            
        except Exception as e:
            state.context = f"❌ Помилка отримання завдань: {str(e)}"
            return state
    def get_issue_by_id(self, state: DialogueState) -> DialogueState:
        issue_id = state.function_calls[0].get("arguments", {}).get("issue_id", "")
        try:
            # Очищуємо ID від # якщо є
            clean_id = issue_id.replace('#', '').strip()
            
            url = f"{self.base_url}/issues/{clean_id}.json"
            headers = {'X-Redmine-API-Key': self.api_key}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            issue = response.json()['issue']
            state.context = self._format_issue(issue)
            return state

        except Exception as e:
            state.context = f"❌ Не вдалося знайти завдання {issue_id}: {str(e)}"
            return state

    def get_issue_by_date(self, state: DialogueState) -> DialogueState:
        """Отримання завдань за датою"""
        date = state.function_calls[0].get("arguments", {}).get("date", "")
        try:
            # Парсимо дату
            parsed_date = self._parse_date(date)
            print(f"Пошук завдань за датою: {parsed_date}")

            params = {
                'assigned_to_id': self.state.user_id,
                'updated_on': f">={parsed_date}",
                'limit': 10
            }
            
            data = self._make_request('issues', params=params)
            
            if not data.get('issues'):
                state.context = f"📅 На {date} завдань не знайдено"                
                return state

            issues_text = [self._format_issue_short(issue) for issue in data['issues']]
            state.context = f"📅 Завдання на {date}:\n\n" + "\n".join(issues_text)
            return state

        except Exception as e:
            state.context = f"❌ Помилка пошуку завдань за датою {date}: {str(e)}"
            return state
    
    def search_issues(self, state: DialogueState) -> DialogueState:
        """Пошук завдань за текстом"""
        search_term = state.function_calls[0].get("arguments", {}).get("search_term", "")
        try:
            params = {
                'assigned_to_id': self.user_id,
                'subject': f"~{search_term}",
                'limit': 5
            }

            data = self._make_request('issues', params=params)

            if not data.get('issues'):
                state.context = f"🔍 За запитом '{search_term}' нічого не знайдено"
                return state

            issues_text = [self._format_issue_short(issue) for issue in data['issues']]
            state.context = f"🔍 Результати пошуку '{search_term}':\n\n" + "\n".join(issues_text)
            return state

        except Exception as e:
            state.context = f"❌ Помилка пошуку: {str(e)}"
            return state

    def get_issue_by_name(self, state: DialogueState) -> DialogueState:
        """Отримання завдання за назвою"""
        issue_name = state.function_calls[0].get("arguments", {}).get("issue_name", "")
        try:
            params = {
                'assigned_to_id': self.user_id,
                'status_id': 'open',
                'subject': f"~{issue_name}",
                'limit': 5
            }

            data = self._make_request('issues', params=params)

            if not data.get('issues'):
                state.context = f"🔍 За запитом '{issue_name}' нічого не знайдено"
                return state

            issues_text = [self._format_issue_short(issue) for issue in data['issues']]
            state.context = f"🔍 Результати пошуку '{issue_name}':\n\n" + "\n".join(issues_text)
            return state

        except Exception as e:
            state.context = f"❌ Помилка пошуку: {str(e)}"
            return state
    def get_issue_hours(self, state: DialogueState) -> DialogueState:
        """Отримання годин по завданню"""
        issue_name = state.function_calls[0].get("arguments", {}).get("issue_name", "")
        try:
            params = {
                'assigned_to_id': self.user_id,
                'subject': f"~{issue_name}",
                'limit': 1
            }

            data = self._make_request('issues', params=params)

            if not data.get('issues'):
                state.context = f"🔍 За запитом '{issue_name}' нічого не знайдено"
                return state

            issue = data['issues'][0]
            hours = issue.get('estimated_hours', 0)
            state.context = f"⏱️ Години по завданню '{issue_name}': {hours} год."
            return state

        except Exception as e:
            state.context = f"❌ Помилка отримання годин по завданню '{issue_name}': {str(e)}"
            return state
    def fill_issue_hours(self, state: DialogueState ) -> DialogueState:
        """Заповнення годин по завданню"""
        issue_id = state.function_calls[0].get("arguments", {}).get("issue_id", "")
        hours = state.function_calls[0].get("arguments", {}).get("hours", 0)
        description = state.function_calls[0].get("arguments", {}).get("description", "")
        try:
            clean_id = issue_id.replace('#', '').strip()
            
            url = f"{self.base_url}/issues/{clean_id}.json"
            headers = {
                'X-Redmine-API-Key': self.api_key,
                'Content-Type': 'application/json'
            }
            
            data = {
                'issue': {
                    'estimated_hours': hours,
                    'notes': description
                }
            }
            
            response = requests.put(url, headers=headers, json=data)
            response.raise_for_status()
            state.context = f"✅ Заповнено {hours} год. для завдання #{clean_id}"
            return state

        except Exception as e:
            state.context = f"❌ Помилка заповнення годин: {str(e)}"
            return state
    def get_user_status(self, state: DialogueState) -> DialogueState:
        """Отримання статусу користувача"""
        try:
            url = f"{self.base_url}/users/{self.user_id}.json"
            headers = {'X-Redmine-API-Key': self.api_key}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            user = response.json()['user']
            status = user.get('status', 'Невідомо')
            state.context = f"👤 Статус користувача: {status}"
            return state

        except Exception as e:
            return f"❌ Помилка отримання статусу користувача: {str(e)}"
    def set_user_status(self, state: DialogueState) -> DialogueState:
        """Встановлення статусу користувача"""
        status = state.function_calls[0].get("arguments", {}).get("status", "")
        try:
            url = f"{self.base_url}/users/{self.user_id}.json"
            headers = {
                'X-Redmine-API-Key': self.api_key,
                'Content-Type': 'application/json'
            }
            
            data = {
                'user': {
                    'status': status
                }
            }
            
            response = requests.put(url, headers=headers, json=data)
            response.raise_for_status()
            state.context = f"✅ Статус користувача змінено на: {status}"
            return state
            
        except Exception as e:
            state.context = f"❌ Помилка встановлення статусу: {str(e)}"
            return state
    def create_issue(self, state: DialogueState) -> DialogueState:
        """Створення нового завдання"""
        subject = state.function_calls[0].get("arguments", {}).get("subject", "")
        description = state.function_calls[0].get("arguments", {}).get("description", "")
        priority = state.function_calls[0].get("arguments", {}).get("priority", "Normal")
        try:
            url = f"{self.base_url}/issues.json"
            headers = {
                'X-Redmine-API-Key': self.api_key,
                'Content-Type': 'application/json'
            }
            
            data = {
                'issue': {
                    'subject': subject,
                    'description': description,
                    'priority_id': self._get_priority_id(priority)
                }
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            issue = response.json()['issue']
            state.context = f"✅ Завдання створено: {self._format_issue(issue)}"
            return state
            
        except Exception as e:
            state.context = f"❌ Помилка створення завдання: {str(e)}"
            return state
    def assign_issue(self, state: DialogueState) -> DialogueState: 
        """Призначення завдання користувачу"""
        issue_id = state.function_calls[0].get("arguments", {}).get("issue_id", "")
        user_id = state.function_calls[0].get("arguments", {}).get("user_id", "")
        try:
            clean_id = issue_id.replace('#', '').strip()
            
            url = f"{self.base_url}/issues/{clean_id}.json"
            headers = {
                'X-Redmine-API-Key': self.api_key,
                'Content-Type': 'application/json'
            }
            
            data = {
                'issue': {
                    'assigned_to_id': user_id
                }
            }
            
            response = requests.put(url, headers=headers, json=data)
            response.raise_for_status()
            state.context = f"✅ Завдання #{clean_id} призначено користувачу {user_id}"
            return state            
        except Exception as e:
            state.context = f"❌ Помилка призначення завдання #{issue_id} користувачу {user_id}: {str(e)}"
            return state
    def get_wiki_info(self, state: DialogueState) -> DialogueState:
        """Отримання інформації з Wiki"""
        topic = state.function_calls[0].get("arguments", {}).get("topic", "")
        try:
            url = f"{self.base_url}/wiki/{topic}.json"
            headers = {'X-Redmine-API-Key': self.api_key}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            wiki_info = response.json()['wiki']
            state.context = f"📖 Wiki інформація про {topic}:\n\n{wiki_info['content'][:200]}..."
            return state

        except Exception as e:
            state.context = f"❌ Помилка отримання Wiki інформації: {str(e)}"
            return state

    def _format_issue(self, issue: Dict) -> str:
        """Форматування повної інформації про завдання"""
        issue_id = issue['id']
        title = issue.get('subject', 'Без назви')
        status = issue.get('status', {}).get('name', 'Невідомо')
        priority = issue.get('priority', {}).get('name', 'Невідомо')
        assignee = issue.get('assigned_to', {}).get('name', 'Не призначено')
        description = issue.get('description', '')[:200] + '...' if issue.get('description') else ''

        # Генеруємо посилання на завдання
        issue_link = f"{self.state.redmine_url}/issues/{issue_id}"

        return f"""🎯 **Завдання #{issue_id}**
🔗 **Посилання:** {issue_link}
📝 **Назва:** {title}
📊 **Статус:** {status}
⚡ **Пріоритет:** {priority}
👤 **Відповідальний:** {assignee}
📄 **Опис:** {description}"""

    def _format_issue_short(self, issue: Dict) -> str:
        """Короткий формат завдання з посиланням"""
        issue_id = issue['id']
        title = issue.get('subject', 'Без назви')
        status = issue.get('status', {}).get('name', 'Невідомо')

        # Генеруємо посилання
        issue_link = f"{self.state.redmine_url}/issues/{issue_id}"

        return f"**[#{issue_id}]({issue_link}) - {title} ({status})**"
    def _parse_date(self, date_str: str) -> str:
        """Парсинг дати в формат Redmine"""
        date_str = date_str.lower().strip()
        
        today = datetime.now()
        
        if date_str in ['сьогодні', 'today']:
            return today.strftime('%Y-%m-%d')
        elif date_str in ['вчора', 'yesterday']:
            return (today - timedelta(days=1)).strftime('%Y-%m-%d')
        elif date_str in ['завтра', 'tomorrow']:
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            # Спробуємо парсити як дату
            try:
                # Формат дд.мм.рррр або дд.мм
                if '.' in date_str:
                    parts = date_str.split('.')
                    if len(parts) == 2:
                        day, month = int(parts[0]), int(parts[1])
                        year = today.year
                        return f"{year:04d}-{month:02d}-{day:02d}"
                    elif len(parts) == 3:
                        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                        if year < 100:
                            year += 2000
                        return f"{year:04d}-{month:02d}-{day:02d}"
            except ValueError:
                pass
        
        # Якщо не вдалося парсити, повертаємо сьогодні
        return today.strftime('%Y-%m-%d')
    def get_google_search(self, state: DialogueState) -> DialogueState:
        """Викликає Google Search Tool"""
        try:
            query = state.function_calls[0]["arguments"]["query"]
            result = self.google_search.search(query)
            state.context = result
            state.current_node = "generate_response"
            state.intent = "get_google_search"
        except Exception as e:
            print(f"Google Search error: {e}")
            state.context = "Помилка пошуку в Google."
            state.current_node = "generate_response"
        return state