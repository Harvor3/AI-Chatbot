from typing import List, Dict, Any, Optional, Tuple
from .vector_store import VectorStore
from .document_processor import DocumentProcessor, DocumentChunk
from ..storage.tenant_manager import TenantManager


class RAGRetriever:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.document_processor = DocumentProcessor()
        self.tenant_manager = TenantManager()
        self._load_existing_documents()
    
    def add_documents(self, 
                     documents: List[Dict[str, Any]],
                     tenant_id: str = "default") -> Dict[str, Any]:
        results = []
        total_chunks = 0
        successful_docs = 0
        
        for doc in documents:
            result = self.add_document(
                doc["content"], 
                doc["filename"], 
                doc["file_type"], 
                tenant_id
            )
            results.append(result)
            if result["success"]:
                successful_docs += 1
                total_chunks += result["chunks_created"]
        
        return {
            "success": successful_docs > 0,
            "total_documents": len(documents),
            "successful_documents": successful_docs,
            "failed_documents": len(documents) - successful_docs,
            "total_chunks": total_chunks,
            "results": results,
            "tenant_id": tenant_id
        }
    
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
            
            success = self.vector_store.add_documents(chunks, tenant_id, replace_existing=True, clear_all=False)
            
            if success:
                storage_success = self.tenant_manager.add_document(
                    tenant_id, filename, file_type, len(file_content), len(chunks), file_content
                )
                
                return {
                    "success": True,
                    "chunks_created": len(chunks),
                    "filename": filename,
                    "tenant_id": tenant_id,
                    "file_type": file_type,
                    "stored": storage_success
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
    
    def retrieve_context_from_documents(self,
                                       query: str,
                                       document_names: Optional[List[str]] = None,
                                       tenant_id: str = "default",
                                       k: int = 5,
                                       use_hybrid: bool = True) -> Dict[str, Any]:
        metadata_filter = {}
        if document_names:
            metadata_filter["source"] = document_names
        
        return self.retrieve_context(query, tenant_id, k, use_hybrid, metadata_filter)
    
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
        return self.tenant_manager.get_tenant_stats(tenant_id)
    
    def get_available_documents(self, tenant_id: str = "default") -> List[str]:
        storage_docs = self.tenant_manager.get_tenant_documents(tenant_id)
        return [doc.filename for doc in storage_docs]
    
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
    
    def _load_existing_documents(self):
        try:
            tenants = self.tenant_manager.list_tenants()
            if not tenants:
                return
                
            for tenant_info in tenants:
                tenant_id = tenant_info.tenant_id
                docs = self.tenant_manager.get_tenant_documents(tenant_id)
                
                if not docs:
                    continue
                    
                for doc in docs:
                    try:
                        file_content = self.tenant_manager.get_document_content(tenant_id, doc.filename)
                        if file_content:
                            chunks = self.document_processor.process_file(
                                file_content, doc.filename, doc.file_type, tenant_id
                            )
                            if chunks:
                                self.vector_store.add_documents(chunks, tenant_id, replace_existing=True, clear_all=False)
                    except Exception as doc_error:
                        print(f"Error loading document {doc.filename} for tenant {tenant_id}: {doc_error}")
                        continue
        except Exception as e:
            print(f"Error loading existing documents: {e}")
            pass
    
    def create_tenant(self, name: str, email: str = None, tenant_id: str = None) -> str:
        return self.tenant_manager.create_tenant(name, email, tenant_id)
    
    def get_tenant_info(self, tenant_id: str):
        return self.tenant_manager.get_tenant(tenant_id)
    
    def delete_document(self, tenant_id: str, filename: str) -> bool:
        vector_success = self.vector_store._remove_documents_by_filename(filename, tenant_id)
        storage_success = self.tenant_manager.delete_document(tenant_id, filename)
        return vector_success and storage_success 