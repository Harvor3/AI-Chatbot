import re
from typing import Dict, Any, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain.prompts import ChatPromptTemplate
from .base_agent import BaseAgent


class APIExecutionAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel):
        super().__init__(
            name="API Execution Agent",
            description="Handles API calls, integrations, and external service requests"
        )
        self.llm = llm
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a specialized API execution assistant. Your role is to:
            1. Help users make API calls to external services
            2. Explain API endpoints and their usage
            3. Format API requests and responses
            4. Handle authentication and error scenarios
            5. Suggest appropriate APIs for specific tasks
            
            Always provide clear instructions and handle errors gracefully. 
            If you need API keys or credentials, guide the user on how to obtain them securely."""),
            ("human", "{message}")
        ])
    
    async def process(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            chain = self.prompt | self.llm
            
            response = await chain.ainvoke({"message": message})
            
            return {
                "response": response.content if hasattr(response, 'content') else str(response),
                "agent": self.name,
                "confidence": self.can_handle(message, context),
                "metadata": {
                    "type": "api_execution",
                    "requires_external_calls": True
                }
            }
        except Exception as e:
            return {
                "response": f"I encountered an error processing your API request: {str(e)}",
                "agent": self.name,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def can_handle(self, message: str, context: Optional[Dict[str, Any]] = None) -> float:
        message_lower = message.lower()
        
        high_confidence_keywords = [
            "api", "endpoint", "rest", "graphql", "webhook", "http request",
            "post request", "get request", "put request", "delete request",
            "api call", "integration", "third party", "external service"
        ]
        
        medium_confidence_keywords = [
            "service", "request", "response", "authentication", "auth",
            "token", "key", "connect", "fetch data", "send data"
        ]
        
        for keyword in high_confidence_keywords:
            if keyword in message_lower:
                return 0.9
        
        for keyword in medium_confidence_keywords:
            if keyword in message_lower:
                return 0.6
        
        if re.search(r'https?://', message_lower):
            return 0.8
        
        if re.search(r'\b(json|xml|curl|postman)\b', message_lower):
            return 0.7
        
        return 0.1 