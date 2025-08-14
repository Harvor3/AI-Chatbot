import re
from typing import Dict, Any, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain.prompts import ChatPromptTemplate
from .base_agent import BaseAgent


class AnalyticsAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel):
        super().__init__(
            name="Analytics Agent",
            description="Handles data analysis, reporting, and analytics queries"
        )
        self.llm = llm
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a specialized analytics assistant. Your role is to:
            1. Analyze data and provide insights
            2. Create reports and dashboards
            3. Perform statistical analysis
            4. Generate charts and visualizations
            5. Explain trends and patterns in data
            
            Always provide clear, actionable insights and suggest appropriate visualization methods.
            Consider statistical significance and data quality when making recommendations."""),
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
                    "type": "analytics",
                    "involves_data_analysis": True
                }
            }
        except Exception as e:
            return {
                "response": f"I encountered an error processing your analytics request: {str(e)}",
                "agent": self.name,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def can_handle(self, message: str, context: Optional[Dict[str, Any]] = None) -> float:
        message_lower = message.lower()
        
        high_confidence_keywords = [
            "analytics", "analysis", "analyze", "data analysis", "statistics",
            "report", "dashboard", "chart", "graph", "visualization", "metrics",
            "kpi", "performance", "trend", "pattern"
        ]
        
        medium_confidence_keywords = [
            "data", "numbers", "calculate", "measure", "compare", "insight",
            "summary", "overview", "breakdown", "distribution", "correlation"
        ]
        
        for keyword in high_confidence_keywords:
            if keyword in message_lower:
                return 0.9
        
        for keyword in medium_confidence_keywords:
            if keyword in message_lower:
                return 0.6
        
        if re.search(r'\b(sql|python|r|excel|tableau|powerbi)\b', message_lower):
            return 0.7
        
        if re.search(r'\b(average|mean|median|sum|count|percentage)\b', message_lower):
            return 0.8
        
        return 0.1 