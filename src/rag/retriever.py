from typing import List, Dict, Any, Optional, Tuple
from .vector_store import VectorStore
from .document_processor import DocumentProcessor, DocumentChunk


class RAGRetriever:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.document_processor = DocumentProcessor()
    
    def add_document(self, 
                    file_content: bytes,
                    filename: str,
                    file_type: str,
                    tenant_id: str = "default") -> Dict[str, Any]:
        try:
            chunks = self.document_processor.process_file(
                file_content, filename, file_type, tenant_id
            )
            
            if not chunks:
                return {
                    "success": False,
                    "error": "No content could be extracted from the document",
                    "chunks_created": 0
                }
            
            success = self.vector_store.add_documents(chunks, tenant_id)
            
            if success:
                return {
                    "success": True,
                    "chunks_created": len(chunks),
                    "filename": filename,
                    "tenant_id": tenant_id,
                    "file_type": file_type
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to add document to vector store",
                    "chunks_created": len(chunks)
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "chunks_created": 0
            }
    
    def retrieve_context(self,
                        query: str,
                        tenant_id: str = "default",
                        k: int = 5,
                        use_hybrid: bool = True,
                        metadata_filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            if use_hybrid:
                results = self.vector_store.hybrid_search(
                    query, tenant_id, k, metadata_filter
                )
            else:
                results = self.vector_store.search(
                    query, tenant_id, k, metadata_filter
                )
            
            if not results:
                return {
                    "context": "",
                    "sources": [],
                    "chunks_found": 0,
                    "tenant_id": tenant_id
                }
            
            context_parts = []
            sources = []
            
            for i, result in enumerate(results):
                source_info = {
                    "filename": result["source"],
                    "page": result["metadata"].get("page_number", 1),
                    "chunk_index": result["metadata"].get("chunk_index", 0),
                    "score": result["score"]
                }
                
                if use_hybrid and "hybrid_score" in result:
                    source_info["hybrid_score"] = result["hybrid_score"]
                
                sources.append(source_info)
                
                chunk_header = f"[Source {i+1}: {result['source']}]"
                if result["metadata"].get("page_number"):
                    chunk_header += f" (Page {result['metadata']['page_number']})"
                
                context_parts.append(f"{chunk_header}\n{result['content']}")
            
            full_context = "\n\n---\n\n".join(context_parts)
            
            return {
                "context": full_context,
                "sources": sources,
                "chunks_found": len(results),
                "tenant_id": tenant_id,
                "query": query
            }
            
        except Exception as e:
            return {
                "context": "",
                "sources": [],
                "chunks_found": 0,
                "error": str(e),
                "tenant_id": tenant_id
            }
    
    def get_tenant_summary(self, tenant_id: str = "default") -> Dict[str, Any]:
        return self.vector_store.get_tenant_stats(tenant_id)
    
    def delete_tenant_documents(self, tenant_id: str) -> bool:
        return self.vector_store.delete_tenant_data(tenant_id)
    
    def search_documents(self,
                        query: str,
                        tenant_id: str = "default",
                        file_filter: Optional[str] = None,
                        k: int = 10) -> List[Dict[str, Any]]:
        metadata_filter = {}
        if file_filter:
            metadata_filter["filename"] = file_filter
        
        results = self.vector_store.hybrid_search(
            query, tenant_id, k, metadata_filter
        )
        
        document_results = {}
        for result in results:
            filename = result["source"]
            if filename not in document_results:
                document_results[filename] = {
                    "filename": filename,
                    "best_score": result.get("hybrid_score", result["score"]),
                    "chunks": [],
                    "metadata": result["metadata"]
                }
            
            document_results[filename]["chunks"].append({
                "content": result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"],
                "score": result.get("hybrid_score", result["score"]),
                "page": result["metadata"].get("page_number", 1)
            })
        
        return sorted(
            document_results.values(),
            key=lambda x: x["best_score"],
            reverse=True
        ) 