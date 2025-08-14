from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from langchain.schema import BaseMessage
from langchain_core.language_models import BaseLanguageModel


class BaseAgent(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def process(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def can_handle(self, message: str, context: Optional[Dict[str, Any]] = None) -> float:
        pass
    
    def get_info(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "description": self.description
        } 