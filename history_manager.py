import sqlite3
import json, os
import uuid
from datetime import datetime
from typing import List, Dict, Optional
import threading

class AdvancedHistoryManager:
    def __init__(self, db_path: str = "data/chat_history.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """)
            conn.commit()
    
    def create_session(self, metadata: dict = None) -> str:
        """Створює нову сесію"""
        session_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else "{}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, metadata) VALUES (?, ?)",
                (session_id, metadata_json)
            )
            conn.commit()
        
        return session_id
    
    def save_message(self, session_id: str, role: str, content: str):
        """Зберігає повідомлення в сесію"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content)
            )
            conn.commit()
    
    def get_session_history(self, session_id: str, format_type: str = "messages") -> List:
        """Отримує історію сесії"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            )
            messages = cursor.fetchall()
        
        if format_type == "messages":
            return [
                {"role": msg[0], "content": msg[1], "timestamp": msg[2]}
                for msg in messages
            ]
        else:
            # Старий формат для сумісності
            return messages
    
    def get_sessions(self) -> List[Dict]:
        """Отримує список всіх сесій"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT s.session_id, s.created_at, COUNT(m.id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.session_id = m.session_id
                GROUP BY s.session_id, s.created_at
                ORDER BY s.created_at DESC
            """)
            sessions = cursor.fetchall()
        
        return [
            {
                "session_id": session[0],
                "created_at": session[1],
                "message_count": session[2]
            }
            for session in sessions
        ]
    
    def delete_session(self, session_id: str):
        """Видаляє сесію та всі її повідомлення"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
    
    def search_messages(self, query: str) -> List[Dict]:
        """Пошук по повідомленнях"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT role, content, timestamp FROM messages WHERE content LIKE ? ORDER BY timestamp DESC LIMIT 50",
                (f"%{query}%",)
            )
            results = cursor.fetchall()
        
        return [
            {"role": result[0], "content": result[1], "timestamp": result[2]}
            for result in results
        ]