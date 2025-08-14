import re
from typing import Dict, Any, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain.prompts import ChatPromptTemplate
from .base_agent import BaseAgent


class FormGenerationAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel):
        super().__init__(
            name="Form Generation Agent",
            description="Creates dynamic forms and handles form-related requests"
        )
        self.llm = llm
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a specialized form generation assistant. Your role is to:
            1. Create dynamic forms based on user requirements
            2. Generate form schemas and validation rules
            3. Suggest appropriate field types and layouts
            4. Handle form validation and error handling
            5. Provide form templates and examples
            
            Always create user-friendly forms with proper validation and clear labels.
            Consider accessibility and responsive design principles."""),
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
                    "type": "form_generation",
                    "generates_ui_components": True
                }
            }
        except Exception as e:
            return {
                "response": f"I encountered an error generating your form: {str(e)}",
                "agent": self.name,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def can_handle(self, message: str, context: Optional[Dict[str, Any]] = None) -> float:
        message_lower = message.lower()
        
        high_confidence_keywords = [
            "form", "create form", "generate form", "form builder", "input field",
            "form validation", "form schema", "contact form", "registration form",
            "survey form", "feedback form"
        ]
        
        medium_confidence_keywords = [
            "field", "input", "validation", "schema", "template", "layout",
            "checkbox", "radio button", "dropdown", "text field", "submit"
        ]
        
        for keyword in high_confidence_keywords:
            if keyword in message_lower:
                return 0.9
        
        for keyword in medium_confidence_keywords:
            if keyword in message_lower:
                return 0.6
        
        if re.search(r'\b(html|css|javascript|react|vue|angular)\b', message_lower):
            return 0.7
        
        return 0.1 