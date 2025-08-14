import asyncio
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from ..config import config
from ..agents.base_agent import BaseAgent
from ..agents.document_qa_agent import DocumentQAAgent
from ..agents.api_execution_agent import APIExecutionAgent
from ..agents.form_generation_agent import FormGenerationAgent
from ..agents.analytics_agent import AnalyticsAgent


class AgentState(TypedDict):
    message: str
    context: Dict[str, Any]
    selected_agent: Optional[str]
    confidence: float
    result: Dict[str, Any]


class AgentController:
    def __init__(self):
        self.llm = self._initialize_llm()
        self.agents = self._initialize_agents()
        self.agent_map = {agent.name: agent for agent in self.agents}
        self.graph = self._build_graph()
    
    def _initialize_llm(self) -> BaseLanguageModel:
        try:
            return ChatOpenAI(
                model="gpt-3.5-turbo",
                openai_api_key=config.OPENAI_API_KEY,
                temperature=0.7
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize OpenAI LLM: {str(e)}")
    
    def _initialize_agents(self) -> List[BaseAgent]:
        return [
            DocumentQAAgent(self.llm),
            APIExecutionAgent(self.llm),
            FormGenerationAgent(self.llm),
            AnalyticsAgent(self.llm)
        ]
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        
        workflow.add_node("route_to_agent", self._route_to_agent)
        workflow.add_node("execute_selected_agent", self._execute_selected_agent)
        workflow.add_node("fallback_response", self._fallback_response)
        
        workflow.add_edge(START, "route_to_agent")
        
        workflow.add_conditional_edges(
            "route_to_agent",
            self._should_use_fallback,
            {
                True: "fallback_response",
                False: "execute_selected_agent"
            }
        )
        
        workflow.add_edge("execute_selected_agent", END)
        workflow.add_edge("fallback_response", END)
        
        return workflow.compile()
    
    def _route_to_agent(self, state: AgentState) -> AgentState:
        message = state["message"]
        context = state["context"]
        
        best_agent = None
        highest_confidence = 0.0
        
        for agent in self.agents:
            confidence = agent.can_handle(message, context)
            if confidence > highest_confidence:
                highest_confidence = confidence
                best_agent = agent
        
        return {
            **state,
            "selected_agent": best_agent.name if best_agent else None,
            "confidence": highest_confidence
        }
    
    def _should_use_fallback(self, state: AgentState) -> bool:
        return state["confidence"] < 0.5 or state["selected_agent"] is None
    
    def _execute_selected_agent(self, state: AgentState) -> AgentState:
        selected_agent_name = state["selected_agent"]
        if selected_agent_name and selected_agent_name in self.agent_map:
            agent = self.agent_map[selected_agent_name]
            try:
                result = agent.process(state["message"], state["context"])
            except Exception as e:
                result = {
                    "response": f"Agent processing error: {str(e)}",
                    "agent": selected_agent_name,
                    "confidence": 0.0,
                    "error": str(e)
                }
        else:
            result = {
                "response": "No suitable agent found to handle this request.",
                "agent": "Unknown",
                "confidence": 0.0
            }
        
        return {
            **state,
            "result": result
        }
    
    def _fallback_response(self, state: AgentState) -> AgentState:
        try:
            from langchain.prompts import ChatPromptTemplate
            
            fallback_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful AI assistant. The user's query couldn't be handled by any specialized agent, 
                so provide a general response. Be helpful and suggest how they might rephrase their question or 
                what specific information they might need to provide."""),
                ("human", "{message}")
            ])
            
            chain = fallback_prompt | self.llm
            response = chain.invoke({"message": state["message"]})
            
            result = {
                "response": response.content if hasattr(response, 'content') else str(response),
                "agent": "General Assistant",
                "confidence": 0.3,
                "metadata": {
                    "type": "fallback",
                    "reason": "No specialized agent had sufficient confidence"
                }
            }
        except Exception as e:
            result = {
                "response": f"I apologize, but I encountered an error processing your request: {str(e)}",
                "agent": "Error Handler",
                "confidence": 0.0,
                "error": str(e)
            }
        
        return {
            **state,
            "result": result
        }
    
    def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if context is None:
            context = {}
        
        initial_state: AgentState = {
            "message": message,
            "context": context,
            "selected_agent": None,
            "confidence": 0.0,
            "result": {}
        }
        
        try:
            final_state = self.graph.invoke(initial_state)
            return final_state["result"]
        except Exception as e:
            return {
                "response": f"System error occurred: {str(e)}",
                "agent": "System",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def get_available_agents(self) -> List[Dict[str, str]]:
        return [agent.get_info() for agent in self.agents] 