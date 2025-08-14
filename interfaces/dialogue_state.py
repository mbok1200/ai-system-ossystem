import os
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class DialogueState(BaseModel):
    user_input: str = ""
    user_id: int = int(os.getenv("REDMINE_USER_ID", 1))
    current_node: str = ""
    intent: str = ""
    function_calls: List[Dict] = Field(default_factory=list)
    messages: List[Dict] = Field(default_factory=list)
    response_messages: List[Dict] = Field(default_factory=list)
    context: Any = Field(default_factory=dict)  # Дозволяємо будь-який тип
    collected_data: Dict[str, Any] = Field(default_factory=dict)
    required_fields: List[str] = Field(default_factory=list)
    options: Dict[str, Any] = Field(default_factory=dict)
    session_state: Dict[str, Any] = Field(default_factory=dict)
    mode: str = "hybrid"
    RAG_context: str = ""
    sources: List[Any] = Field(default_factory=list)
    delta: str = ""
    def update(self, **kwargs):
        """Простий update - перевіряє поля і встановлює значення"""
        for field_name, value in kwargs.items():
            if hasattr(self, field_name):
                setattr(self, field_name, value)
        return self