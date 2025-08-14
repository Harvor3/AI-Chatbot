import re
from typing import Dict, Any, Optional, List
from langchain_core.language_models import BaseLanguageModel
from langchain.prompts import ChatPromptTemplate
from .base_agent import BaseAgent

try:
    from ..rag.retriever import RAGRetriever
    from ..rag.vector_store import VectorStore
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


class DocumentQAAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel):
        super().__init__(
            name="Document Q&A Agent",
            description="Handles questions about documents, PDFs, and text-based content using RAG"
        )
        self.llm = llm
        
        if RAG_AVAILABLE:
            try:
                self.vector_store = VectorStore()
                self.rag_retriever = RAGRetriever(self.vector_store)
                self.rag_enabled = True
            except Exception as e:
                print(f"Failed to initialize RAG system: {e}")
                self.rag_enabled = False
        else:
            self.rag_enabled = False
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a specialized document Q&A assistant with RAG capabilities. Your role is to:
            1. Answer questions about documents using retrieved context
            2. Help users find information within documents
            3. Summarize document content when requested
            4. Extract specific information from documents
            5. Provide accurate answers based on the retrieved document context
            
            When provided with context from documents, use that information to answer questions accurately.
            Always cite the sources when possible. If the context doesn't contain enough information,
            clearly state what additional information would be needed."""),
            ("human", "{message}")
        ])
        
        self.rag_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a specialized document Q&A assistant. You MUST ONLY use the provided context from documents to answer questions.

            STRICT INSTRUCTIONS:
            1. ONLY use information from the provided context below - DO NOT use any external knowledge
            2. If the context doesn't contain the answer, say "The provided documents don't contain information about this topic"
            3. Always cite the specific source document and page when referencing information
            4. Provide direct quotes from the context when possible
            5. Be accurate and concise in your response
            
            Context from documents:
            {context}
            
            Available sources: {sources}
            
            REMEMBER: Answer ONLY based on the context provided above. Do not use general knowledge."""),
            ("human", "Question: {question}")
        ])
    
    def process(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            tenant_id = context.get("tenant_id", "default") if context else "default"
            uploaded_files = context.get("uploaded_files", []) if context else []
            
            if self.rag_enabled and hasattr(self, 'rag_retriever'):
                return self._process_with_rag(message, context, tenant_id, uploaded_files)
            else:
                return self._process_without_rag(message, context, uploaded_files)
                
        except Exception as e:
            return {
                "response": f"I encountered an error processing your document query: {str(e)}",
                "agent": self.name,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _process_with_rag(self, message: str, context: Dict[str, Any], 
                               tenant_id: str, uploaded_files: List[Dict]) -> Dict[str, Any]:
        try:
            newly_added = []
            if uploaded_files:
                for file_info in uploaded_files:
                    if 'raw_content' in file_info and file_info['raw_content']:
                        result = self.rag_retriever.add_document(
                            file_info['raw_content'], 
                            file_info['name'], 
                            file_info.get('type', 'text/plain'),
                            tenant_id
                        )
                        if result['success']:
                            newly_added.append(file_info['name'])
                    elif 'content' in file_info and not file_info.get('raw_content'):
                        file_content = file_info['content'].encode('utf-8')
                        result = self.rag_retriever.add_document(
                            file_content, 
                            file_info['name'], 
                            file_info.get('type', 'text/plain'),
                            tenant_id
                        )
                        if result['success']:
                            newly_added.append(file_info['name'])
            
            rag_context = self.rag_retriever.retrieve_context(
                message, tenant_id, k=5, use_hybrid=True
            )
            
            if rag_context['chunks_found'] > 0:
                sources_info = []
                for source in rag_context['sources']:
                    sources_info.append(f"- {source['filename']} (Page {source['page']}, Score: {source['score']:.2f})")
                
                sources_text = "\n".join(sources_info)
                
                chain = self.rag_prompt | self.llm
                
                response = chain.invoke({
                    "context": rag_context['context'],
                    "sources": sources_text,
                    "question": message
                })
                
                return {
                    "response": response.content if hasattr(response, 'content') else str(response),
                    "agent": self.name,
                    "confidence": self.can_handle(message, context),
                    "metadata": {
                        "type": "document_qa_rag",
                        "chunks_retrieved": rag_context['chunks_found'],
                        "sources": rag_context['sources'],
                        "tenant_id": tenant_id,
                        "newly_added_files": newly_added,
                        "rag_enabled": True
                    }
                }
            else:
                tenant_stats = self.rag_retriever.get_tenant_summary(tenant_id)
                
                if tenant_stats['documents'] == 0:
                    response_text = """I can help with document analysis using advanced RAG (Retrieval-Augmented Generation). 
                    
To get started:
1. Upload your documents (PDF, DOCX, TXT, CSV, Excel)
2. I'll automatically index them for intelligent search
3. Ask questions and I'll find the most relevant information

Supported formats: PDF, Word documents, text files, CSV, Excel spreadsheets

Upload your documents and try asking questions like:
- "What are the main findings in the research?"
- "Summarize the key points from the report"
- "Find information about [specific topic]"
- "Compare data across different sections"
"""
                else:
                    response_text = f"""I found {tenant_stats['documents']} documents in your collection, but none seem relevant to your question: "{message}"

Available documents: {', '.join(tenant_stats['files'])}

Try rephrasing your question or ask about topics covered in these documents."""
                
                return {
                    "response": response_text,
                    "agent": self.name,
                    "confidence": self.can_handle(message, context),
                    "metadata": {
                        "type": "document_qa_rag",
                        "chunks_retrieved": 0,
                        "tenant_stats": tenant_stats,
                        "rag_enabled": True
                    }
                }
                
        except Exception as e:
            return self._process_without_rag(message, context, uploaded_files)
    
    def _process_without_rag(self, message: str, context: Dict[str, Any], 
                                  uploaded_files: List[Dict]) -> Dict[str, Any]:
        if uploaded_files:
            files_info = []
            document_content = []
            
            for file_info in uploaded_files:
                files_info.append(f"📎 {file_info['name']} ({file_info['size']} bytes)")
                if 'content' in file_info:
                    document_content.append(f"=== {file_info['name']} ===\n{file_info['content']}")
            
            enhanced_message = f"""
User Query: {message}

Available Documents:
{chr(10).join(files_info)}

Document Content:
{chr(10).join(document_content)}

Please analyze the provided documents and answer the user's query based on the content.
"""
            
            chain = self.prompt | self.llm
            
            response = chain.invoke({"message": enhanced_message})
            
            return {
                "response": response.content if hasattr(response, 'content') else str(response),
                "agent": self.name,
                "confidence": self.can_handle(message, context),
                "metadata": {
                    "type": "document_qa_basic",
                    "files_processed": len(uploaded_files),
                    "files": [f['name'] for f in uploaded_files],
                    "rag_enabled": False
                }
            }
        else:
            response_text = f"""I can help with document analysis. Upload documents to get started!
            
To analyze documents:
1. Use the file upload section above the chat
2. Upload PDF, TXT, DOCX, CSV, or Excel files
3. Then ask your question about the documents

For example:
- "Summarize the key points"
- "What are the main findings?"
- "Extract important information"
- "Analyze the document structure"

Please upload your documents and try again!"""
            
            return {
                "response": response_text,
                "agent": self.name,
                "confidence": self.can_handle(message, context),
                "metadata": {
                    "type": "document_qa_basic",
                    "requires_documents": True,
                    "files_processed": 0,
                    "rag_enabled": False
                }
            }
    
    def can_handle(self, message: str, context: Optional[Dict[str, Any]] = None) -> float:
        message_lower = message.lower()
        
        document_keywords = [
            "document", "pdf", "file", "text", "analyze", "summary", "summarize",
            "read", "content", "extract", "information", "doc", "paper", "report",
            "article", "research", "study", "findings", "data", "table", "chart"
        ]
        
        uploaded_files = context.get("uploaded_files", []) if context else []
        
        if uploaded_files:
            return 0.9
        
        keyword_matches = sum(1 for keyword in document_keywords if keyword in message_lower)
        confidence = min(keyword_matches * 0.2, 0.8)
        
        if any(phrase in message_lower for phrase in ["what does", "tell me about", "explain"]):
            confidence += 0.1
        
        if re.search(r'\b(this|the)\s+(document|file|pdf|paper)\b', message_lower):
            confidence += 0.2
        
        return min(confidence, 1.0) if confidence > 0.3 else 0.1 