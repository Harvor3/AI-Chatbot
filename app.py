import streamlit as st
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
import PyPDF2
import io

from src.config import config
from src.controller.agent_controller import AgentController

st.set_page_config(
    page_title="Multi-Agent RAG Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def load_controller():
    try:
        return AgentController()
    except Exception as e:
        st.error(f"Failed to initialize controller: {str(e)}")
        return None

def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "controller" not in st.session_state:
        st.session_state.controller = load_controller()
    if "processing" not in st.session_state:
        st.session_state.processing = False

def display_message(role: str, content: str):
    with st.chat_message(role):
        st.write(content)

def process_user_message_with_context(message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    if st.session_state.controller is None:
        return {
            "response": "System not initialized. Please check your API keys.",
            "agent": "System",
            "confidence": 0.0
        }
    
    if st.session_state.processing:
        return {
            "response": "Please wait for the current request to complete before sending another.",
            "agent": "System",
            "confidence": 0.0
        }
    
    try:
        st.session_state.processing = True
        
        result = st.session_state.controller.process_message(message, context)
        return result
        
    except Exception as e:
        return {
            "response": f"I encountered an error processing your request: {str(e)}",
            "agent": "Error Handler",
            "confidence": 0.0,
            "error": str(e)
        }
    finally:
        st.session_state.processing = False

def main():
    st.title("🤖 Multi-Agent RAG Chatbot")
    st.markdown("*Powered by Google AI, LangChain, LangGraph, and RAG*")
    
    st.info("🧠 **4 Specialized AI Agents** ready to help with documents, APIs, forms, and analytics!")
    
    initialize_session_state()
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("🏢 Tenant Settings")
        tenant_id = st.text_input(
            "Tenant ID", 
            value="default",
            help="Unique identifier for document isolation. Each tenant has separate document storage."
        )
        if tenant_id != "default":
            st.info(f"📊 Active Tenant: {tenant_id}")
        
        st.subheader("🤖 Google AI Status")
        
        if config.GOOGLE_API_KEY:
            st.success("✅ Google AI API Key configured")
            st.info("🚀 Using Gemini 1.5 Flash model")
            st.caption("Free tier: 15 requests/minute")
        elif config.GOOGLE_PROJECT_ID:
            st.success("✅ Google Cloud Vertex AI configured")
            st.info("🏢 Using Vertex AI Gemini model")
            st.caption(f"Project: {config.GOOGLE_PROJECT_ID}")
        else:
            st.error("❌ Google AI not configured!")
            st.warning("⚠️ This system requires Google AI to function")
            st.info("Get your FREE API key from Google AI Studio:")
            st.code("""
Add to your .env file:
GOOGLE_API_KEY=your_google_api_key_here

Get your free key at: https://aistudio.google.com/
            """)
        
        st.subheader("LangSmith Tracing")
        if config.LANGCHAIN_TRACING_V2:
            st.success("✅ LangSmith tracing enabled")
            st.write(f"Project: {config.LANGCHAIN_PROJECT}")
        else:
            st.info("ℹ️ LangSmith tracing disabled")
        
        st.divider()
        
        st.subheader("🧠 RAG System")
        try:
            from src.rag.vector_store import VectorStore
            st.success("✅ RAG system available")
            st.info("🔍 Advanced document search enabled")
        except ImportError:
            st.warning("⚠️ RAG system not available")
            st.info("📄 Using basic document processing")
        
        st.divider()
        
        st.subheader("🤖 Available Agents")
        
        agents_info = [
            {
                "name": "📄 Document Q&A Agent",
                "description": "RAG-powered document analysis",
                "examples": [
                    "Summarize this document",
                    "What are the key findings?",
                    "Extract information about..."
                ]
            },
            {
                "name": "🌐 API Execution Agent", 
                "description": "REST API calls and integrations",
                "examples": [
                    "Help me call a REST API",
                    "Create API authentication",
                    "Format JSON requests"
                ]
            },
            {
                "name": "📊 Form Generation Agent",
                "description": "Dynamic form creation",
                "examples": [
                    "Create a contact form",
                    "Generate survey questions",
                    "Build registration form"
                ]
            },
            {
                "name": "📈 Analytics Agent",
                "description": "Data analysis and reporting", 
                "examples": [
                    "Analyze trends in data",
                    "Create data visualizations",
                    "Generate reports"
                ]
            }
        ]
        
        for agent in agents_info:
            with st.expander(f"**{agent['name']}**", expanded=False):
                st.write(agent['description'])
                st.write("**Example queries:**")
                for example in agent['examples']:
                    st.write(f"• {example}")
        
        st.divider()
        
        if st.session_state.controller:
            st.subheader("🤖 Available Agents")
            agents = st.session_state.controller.get_available_agents()
            for agent in agents:
                st.write(f"**{agent['name']}**")
                st.caption(agent['description'])
    
    st.header("🚀 How It Works")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### 📄 Document Q&A")
        st.markdown("Upload documents and ask questions. Powered by RAG for accurate, contextual answers.")
        
    with col2:
        st.markdown("### 🌐 API Execution") 
        st.markdown("Get help with REST APIs, authentication, and integrations.")
        
    with col3:
        st.markdown("### 📊 Form Generation")
        st.markdown("Create dynamic forms with validation and modern UI components.")
        
    with col4:
        st.markdown("### 📈 Analytics")
        st.markdown("Analyze data, create reports, and generate insights from your information.")
    
    st.divider()
    
    st.subheader("📁 Document Upload")
    st.markdown("*Upload documents to enable the Document Q&A Agent with RAG capabilities*")
    
    uploaded_files = st.file_uploader(
        "Upload documents for analysis",
        type=['pdf', 'txt', 'docx', 'md', 'csv', 'xlsx'],
        accept_multiple_files=True,
        help="Upload documents to enable RAG-powered Q&A"
    )
    
    if uploaded_files:
        st.markdown("**📋 Uploaded Files**")
        cols = st.columns(min(len(uploaded_files), 4))
        
        for i, file in enumerate(uploaded_files):
            with cols[i % 4]:
                file_icon = {
                    'application/pdf': '📕',
                    'text/plain': '📄',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📘',
                    'text/csv': '📊',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '📊'
                }.get(file.type, '📎')
                
                st.write(f"{file_icon} **{file.name}**")
                st.caption(f"{file.type} • {file.size:,} bytes")
    
    st.divider()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("💬 Chat")
    with col2:
        if st.button("🗑️ Clear Chat", help="Clear all chat messages"):
            st.session_state.messages = []
            st.rerun()
    
    for message in st.session_state.messages:
        display_message(message["role"], message["content"])
    
    
    
    if prompt := st.chat_input("Ask about documents, APIs, forms, analytics, or anything else..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        display_message("user", prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Processing your request..."):
                context = {
                    "tenant_id": tenant_id
                }
                if uploaded_files:
                    context["uploaded_files"] = []
                    for file in uploaded_files:
                        file_info = {
                            "name": file.name,
                            "type": file.type,
                            "size": file.size
                        }
                        try:
                            file.seek(0)
                            file_info["raw_content"] = file.read()
                            
                            file.seek(0)
                            if file.type == "text/plain":
                                content = str(file.read(), "utf-8")
                                file_info["content"] = content[:1000] + "..." if len(content) > 1000 else content
                            elif file.type == "application/pdf":
                                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
                                pdf_text = ""
                                for page in pdf_reader.pages[:3]:
                                    pdf_text += page.extract_text() + "\n"
                                file_info["content"] = pdf_text[:1000] + "..." if len(pdf_text) > 1000 else pdf_text
                                file_info["pages"] = len(pdf_reader.pages)
                            else:
                                file_info["content"] = f"File type {file.type} - content will be processed by RAG system"
                        except Exception as e:
                            file_info["content"] = f"Could not read file content: {str(e)}"
                            file_info["raw_content"] = b""
                        context["uploaded_files"].append(file_info)
                
                response = process_user_message_with_context(prompt, context)
            
            st.write(response["response"])
            
            agent_name = response.get('agent', 'Unknown')
            confidence = response.get('confidence', 0)
            
            if confidence >= 0.8:
                st.success(f"🎯 **Handled by**: {agent_name} (Confidence: {confidence:.2f})")
            elif confidence >= 0.5:
                st.info(f"🤖 **Handled by**: {agent_name} (Confidence: {confidence:.2f})")
            else:
                st.warning(f"🔄 **Handled by**: {agent_name} (Confidence: {confidence:.2f})")
            
            with st.expander("📊 Response Details", expanded=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Agent**: {agent_name}")
                    st.write(f"**Confidence**: {confidence:.2f}")
                    if "metadata" in response and "type" in response["metadata"]:
                        st.write(f"**Type**: {response['metadata']['type']}")
                with col_b:
                    if "metadata" in response:
                        st.write("**Metadata**:")
                        st.json(response["metadata"])
        
        st.session_state.messages.append({"role": "assistant", "content": response["response"]})

if __name__ == "__main__":
    main() 