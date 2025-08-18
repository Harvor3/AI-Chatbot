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
    st.markdown("*Powered by OpenAI, LangChain, LangGraph, and RAG*")
    
    st.info("🧠 **4 Specialized AI Agents** ready to help with documents, APIs, forms, and analytics!")
    
    initialize_session_state()
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("👤 Tenant Management")
        
        try:
            from src.rag.vector_store import VectorStore
            from src.rag.retriever import RAGRetriever
            from src.storage.tenant_manager import TenantManager
            
            # Use cached instances to avoid multiple instances and race conditions
            if 'tenant_manager' not in st.session_state:
                st.session_state.tenant_manager = TenantManager()
                # Clean up any orphaned references on startup
                st.session_state.tenant_manager.cleanup_orphaned_references()
            if 'vector_store' not in st.session_state:
                st.session_state.vector_store = VectorStore()
            if 'rag_retriever' not in st.session_state:
                st.session_state.rag_retriever = RAGRetriever(st.session_state.vector_store)
            
            tenant_manager = st.session_state.tenant_manager
            vector_store = st.session_state.vector_store
            rag_retriever = st.session_state.rag_retriever
            existing_tenants = tenant_manager.list_tenants()
            
            # Only use custom tenants (no default)
            if len(existing_tenants) > 0:
                tenant_options = [t.tenant_id for t in existing_tenants]
                tenant_names = [f"{t.name} ({t.tenant_id})" for t in existing_tenants]
                
                # Find current selection index, default to 0 (first tenant)
                current_tenant = st.session_state.get("current_tenant_id")
                try:
                    current_idx = tenant_options.index(current_tenant) if current_tenant in tenant_options else 0
                except (ValueError, TypeError):
                    current_idx = 0
                
                selected_idx = st.selectbox(
                    "Select Tenant",
                    range(len(tenant_options)),
                    index=current_idx,
                    format_func=lambda x: tenant_names[x],
                    help="Choose your tenant profile",
                    key="tenant_selector"
                )
                tenant_id = tenant_options[selected_idx]
                st.session_state.current_tenant_id = tenant_id
            else:
                tenant_id = None
                st.warning("⚠️ **No tenants available**")
                st.info("💡 Create a tenant below to get started")
            
            with st.expander("➕ Create New Tenant"):
                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("Name")
                    new_email = st.text_input("Email (optional)")
                    if st.button("Create Tenant"):
                        if new_name:
                            new_tenant_id = tenant_manager.create_tenant(new_name, new_email)
                            st.success(f"Created tenant: {new_tenant_id}")
                            st.session_state.current_tenant_id = new_tenant_id
                            st.rerun()
                        else:
                            st.error("Name is required")
                
                with col2:
                    st.write("**Quick Create:**")
                    if st.button("👤 Create 'Boss'"):
                        new_tenant_id = tenant_manager.create_tenant("Boss", "boss@company.com")
                        st.success(f"Created Boss tenant: {new_tenant_id}")
                        st.session_state.current_tenant_id = new_tenant_id
                        st.rerun()
                    if st.button("👨‍💼 Create 'Manager'"):
                        new_tenant_id = tenant_manager.create_tenant("Manager", "manager@company.com")
                        st.success(f"Created Manager tenant: {new_tenant_id}")
                        st.session_state.current_tenant_id = new_tenant_id
                        st.rerun()
                    if st.button("👩‍💻 Create 'Developer'"):
                        new_tenant_id = tenant_manager.create_tenant("Developer", "dev@company.com")
                        st.success(f"Created Developer tenant: {new_tenant_id}")
                        st.session_state.current_tenant_id = new_tenant_id
                        st.rerun()
            
            # Show current tenant info
            st.divider()
            if tenant_id:
                tenant_info = tenant_manager.get_tenant(tenant_id)
                if tenant_info:
                    st.success(f"🎯 **Active Tenant: {tenant_info.name}**")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.caption(f"📋 ID: {tenant_id}")
                        if tenant_info.email:
                            st.caption(f"📧 {tenant_info.email}")
                    with col_b:
                        st.caption(f"📁 Documents: {tenant_info.document_count}")
                        st.caption(f"🧩 Chunks: {tenant_info.total_chunks}")
                else:
                    st.warning(f"⚠️ Tenant {tenant_id} not found")
            else:
                st.error("❌ **No Tenant Selected**")
                st.info("Create a tenant above to continue")
        
        except Exception as e:
            st.error("Error loading tenant system")
            tenant_id = st.text_input(
                "Tenant ID", 
                value="fallback",
                help="Fallback tenant ID due to system error."
            )
            st.warning(f"Using fallback tenant: {tenant_id}")
        
        st.subheader("🤖 OpenAI Status")
        
        if config.OPENAI_API_KEY:
            st.success("✅ OpenAI API Key configured")
            st.info("🚀 Using GPT-3.5-Turbo model")
            st.caption("Rate limits apply based on your plan")
        else:
            st.error("❌ OpenAI not configured!")
            st.warning("⚠️ This system requires OpenAI to function")
            st.info("Get your OpenAI API key:")
            st.code("""
Add to your .env file:
OPENAI_API_KEY=your_openai_api_key_here

Get your API key at: https://platform.openai.com/api-keys
            """)
        
        st.subheader("LangSmith Tracing")
        if config.LANGCHAIN_TRACING_V2:
            st.success("✅ LangSmith tracing enabled")
            st.write(f"Project: {config.LANGCHAIN_PROJECT}")
        else:
            st.info("ℹ️ LangSmith tracing disabled")
        
        try:
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
                    "Analyze this dataset",
                    "Create visualizations",
                    "Generate insights"
                ]
            }
        ]
        
        for agent in agents_info:
            with st.expander(f"{agent['name']}"):
                st.write(agent['description'])
                st.write("**Example queries:**")
                for example in agent['examples']:
                    st.write(f"• {example}")
    
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
    
    # Show existing documents only if tenant is selected
    if tenant_id:
        try:
            # Use the cached instances (already loaded above)
            existing_docs = tenant_manager.get_tenant_documents(tenant_id)
            
            if existing_docs:
                st.markdown("**📚 Existing Documents**")
                st.info(f"💾 **{len(existing_docs)} documents** stored for this tenant")
                
                with st.expander("📋 View Document Details"):
                    for doc in existing_docs:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            file_icon = '📕' if doc.file_type.endswith('pdf') else '📄' if doc.file_type.endswith('txt') else '📘'
                            st.write(f"{file_icon} **{doc.filename}**")
                            st.caption(f"Uploaded: {doc.upload_date[:10]} • {doc.chunks_created} chunks")
                        
                        with col2:
                            st.caption(f"{doc.file_size:,} bytes")
                        
                        with col3:
                            if st.button("🗑️", key=f"delete_{doc.filename}", help="Delete document"):
                                try:
                                    # Use the cached retriever instance to ensure consistency
                                    if rag_retriever.delete_document(tenant_id, doc.filename):
                                        st.success(f"✅ Deleted {doc.filename}")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to delete document")
                                except Exception as e:
                                    st.error(f"❌ Error deleting document: {e}")
        except Exception:
            pass
    else:
        st.warning("⚠️ **No tenant selected** - Create a tenant to upload and manage documents")

    st.divider()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("💬 Chat")
    with col2:
        if st.button("🗑️ Clear Chat", help="Clear all chat messages"):
            st.session_state.messages = []
            st.rerun()
    
    # Display chat messages
    for message in st.session_state.messages:
        display_message(message["role"], message["content"])
    
    # Chat input - only allow if tenant is selected
    if tenant_id:
        if prompt := st.chat_input("Ask me anything about your documents, APIs, forms, or analytics!"):
            display_message("user", prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Processing your request..."):
                    # Build context with conversation history
                    context = {
                        "tenant_id": tenant_id,
                        "conversation_history": st.session_state.messages[-10:] if st.session_state.messages else []  # Last 10 messages for context
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
                metadata = response.get('metadata', {})
                
                # Special handling for form generation
                if metadata.get('type') == 'form_generation' and metadata.get('can_build_form'):
                    form_schema = metadata.get('form_schema')
                    if form_schema:
                        # Store form schema in session state for persistence
                        st.session_state.current_form_schema = form_schema
                        
                        st.divider()
                        st.success("✅ **Form generated successfully!** Scroll down to see the interactive form.")
                        st.info("📋 **The form is now available in the Form Builder section below**")
                
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
    else:
        st.info("💡 **Select a tenant** from the sidebar to start chatting")
    
    # Persistent form display section
    if 'current_form_schema' in st.session_state and st.session_state.current_form_schema:
        st.divider()
        st.markdown("### 🎯 **Current Form Builder**")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("📝 **Form ready for use and export**")
        with col2:
            if st.button("🗑️ Clear Form", help="Remove current form"):
                del st.session_state.current_form_schema
                st.rerun()
        
        # Get the form generation agent and build the form
        if st.session_state.controller:
            for agent in st.session_state.controller.agents:
                if agent.name == "Form Generation Agent":
                    agent.build_streamlit_form(st.session_state.current_form_schema)
                    break

if __name__ == "__main__":
    main() 