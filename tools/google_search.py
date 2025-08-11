import os, requests, time
from typing import Dict, Any
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv(".env")

class GoogleSearchTool:
    """Розширений Google Search з аналізом контенту"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.enabled = bool(self.api_key and self.search_engine_id)

    def search_with_analysis(self, query: str, num_results: int = 3) -> Dict[str, Any]:
        """Пошук з Google та аналіз контенту сторінок"""
        try:
            if not self.enabled:
                return {
                    'success': False,
                    'error': 'Google Search не налаштований'
                }
            
            # 1. Отримуємо результати пошуку
            search_results = self._get_search_results(query, num_results)
            
            if not search_results['success']:
                return search_results
            
            # 2. Аналізуємо контент кожної сторінки
            analyzed_sources = []
            
            for result in search_results['results'][:num_results]:
                
                content_analysis = self._analyze_page_content(
                    result['link'], 
                    result['title'],
                    result['snippet']
                )
                
                analyzed_sources.append({
                    'title': result['title'],
                    'url': result['link'],
                    'snippet': result['snippet'],
                    'content': content_analysis['content'],
                    'success': content_analysis['success'],
                    'word_count': content_analysis.get('word_count', 0)
                })
                
                # Пауза між запитами
                time.sleep(0.5)
            
            return {
                'success': True,
                'query': query,
                'sources': analyzed_sources,
                'total_found': len(analyzed_sources)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_search_results(self, query: str, num_results: int = 3) -> Dict[str, Any]:
        """Отримання результатів пошуку з Google API"""
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': query,
                'num': num_results,
                'hl': 'uk'  # Українська мова
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'items' not in data:
                return {
                    'success': False,
                    'error': 'Нічого не знайдено'
                }
            
            results = []
            for item in data['items']:
                results.append({
                    'title': item.get('title', ''),
                    'link': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'displayLink': item.get('displayLink', '')
                })
            
            return {
                'success': True,
                'results': results,
                'total_results': data.get('searchInformation', {}).get('totalResults', 0)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Google API помилка: {str(e)}'
            }
    
    def _analyze_page_content(self, url: str, title: str, snippet: str) -> Dict[str, Any]:
        """Аналіз контенту веб-сторінки"""
        try:
            # Налаштування headers для уникнення блокування
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Парсинг HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Видаляємо скрипти та стилі
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Отримуємо текст
            text = soup.get_text()
            
            # Очищуємо текст
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Обмежуємо розмір тексту
            max_chars = 3000
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            
            return {
                'success': True,
                'content': text,
                'word_count': len(text.split()),
                'char_count': len(text)
            }
            
        except Exception as e:
            # Повертаємо snippet як fallback
            return {
                'success': False,
                'content': snippet,
                'word_count': len(snippet.split()),
                'error': str(e)
            }
    
    def search(self, query: str) -> str:
        """Звичайний пошук (для зворотної сумісності)"""
        result = self.search_with_analysis(query, 3)
        
        if not result['success']:
            return f"❌ Помилка Google пошуку: {result.get('error', 'Невідома помилка')}"
        
        response = f"🔍 **Результати Google пошуку для:** '{query}'\n\n"
        
        for i, source in enumerate(result['sources'], 1):
            response += f"**{i}. {source['title']}**\n"
            response += f"🔗 {source['url']}\n"
            response += f"📄 {source['snippet']}\n\n"
        
        return response