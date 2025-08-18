import os
import pickle
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np

try:
    import faiss
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"Missing vector store dependencies: {e}")

from .document_processor import DocumentChunk


class VectorStore:
    def __init__(self, 
                 model_name: str = "all-MiniLM-L6-v2",
                 vector_dim: int = 384,
                 storage_path: str = "vector_store"):
        self.model_name = model_name
        self.vector_dim = vector_dim
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        try:
            self.embedding_model = SentenceTransformer(model_name)
            test_embedding = self.embedding_model.encode(["test"])
            self.vector_dim = test_embedding.shape[1]
        except Exception as e:
            print(f"Error loading embedding model: {e}")
            self.embedding_model = None
        
        self.tenant_indices: Dict[str, faiss.Index] = {}
        self.tenant_metadata: Dict[str, List[Dict[str, Any]]] = {}
        
        self._load_indices()
    
    def add_documents(self, chunks: List[DocumentChunk], tenant_id: str = "default", replace_existing: bool = True, clear_all: bool = False) -> bool:
        if not self.embedding_model or not chunks:
            return False
        
        try:
            if tenant_id not in self.tenant_indices:
                self.tenant_indices[tenant_id] = faiss.IndexFlatIP(self.vector_dim)
                self.tenant_metadata[tenant_id] = []
            
            if clear_all:
                self.tenant_indices[tenant_id] = faiss.IndexFlatIP(self.vector_dim)
                self.tenant_metadata[tenant_id] = []
            elif replace_existing and chunks:
                filename = chunks[0].source
                self._remove_documents_by_filename(filename, tenant_id)
            
            texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            
            self.tenant_indices[tenant_id].add(embeddings.astype('float32'))
            
            for chunk in chunks:
                metadata = {
                    "chunk_id": chunk.chunk_id,
                    "content": chunk.content,
                    "source": chunk.source,
                    "metadata": chunk.metadata
                }
                self.tenant_metadata[tenant_id].append(metadata)
            
            self._save_tenant_index(tenant_id)
            
            return True
            
        except Exception as e:
            return False
    
    def search(self, 
               query: str, 
               tenant_id: str = "default",
               k: int = 5,
               metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self.embedding_model or tenant_id not in self.tenant_indices:
            return []
        
        try:
            query_embedding = self.embedding_model.encode([query])
            
            scores, indices = self.tenant_indices[tenant_id].search(
                query_embedding.astype('float32'), k * 2
            )
            
            results = []
            tenant_metadata = self.tenant_metadata[tenant_id]
            
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(tenant_metadata):
                    result = {
                        **tenant_metadata[idx],
                        "score": float(score)
                    }
                    
                    if metadata_filter:
                        if self._matches_filter(result, metadata_filter):
                            results.append(result)
                    else:
                        results.append(result)
                    
                    if len(results) >= k:
                        break
            
            return results
            
        except Exception as e:
            return []
    
    def hybrid_search(self,
                     query: str,
                     tenant_id: str = "default",
                     k: int = 5,
                     metadata_filter: Optional[Dict[str, Any]] = None,
                     keyword_weight: float = 0.3) -> List[Dict[str, Any]]:
        semantic_results = self.search(query, tenant_id, k * 2, metadata_filter)
        
        query_words = set(query.lower().split())
        
        for result in semantic_results:
            content_words = set(result["content"].lower().split())
            keyword_score = len(query_words.intersection(content_words)) / len(query_words)
            
            semantic_score = result["score"]
            combined_score = (1 - keyword_weight) * semantic_score + keyword_weight * keyword_score
            result["hybrid_score"] = combined_score
            result["keyword_score"] = keyword_score
        
        semantic_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return semantic_results[:k]
    
    def get_tenant_stats(self, tenant_id: str = "default") -> Dict[str, Any]:
        if tenant_id not in self.tenant_indices:
            return {"documents": 0, "chunks": 0, "files": []}
        
        metadata = self.tenant_metadata[tenant_id]
        files = set(item["source"] for item in metadata)
        
        return {
            "documents": len(files),
            "chunks": len(metadata),
            "files": list(files),
            "tenant_id": tenant_id
        }
    
    def delete_tenant_data(self, tenant_id: str) -> bool:
        try:
            if tenant_id in self.tenant_indices:
                del self.tenant_indices[tenant_id]
            
            if tenant_id in self.tenant_metadata:
                del self.tenant_metadata[tenant_id]
            
            index_file = self.storage_path / f"{tenant_id}_index.faiss"
            metadata_file = self.storage_path / f"{tenant_id}_metadata.json"
            
            if index_file.exists():
                index_file.unlink()
            if metadata_file.exists():
                metadata_file.unlink()
            
            return True
            
        except Exception as e:
            print(f"Error deleting tenant data: {e}")
            return False
    
    def _matches_filter(self, metadata: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        for key, value in filter_dict.items():
            if key not in metadata:
                return False
            
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            else:
                if metadata[key] != value:
                    return False
        return True
    
    def _load_indices(self):
        for index_file in self.storage_path.glob("*_index.faiss"):
            tenant_id = index_file.stem.replace("_index", "")
            
            try:
                index = faiss.read_index(str(index_file))
                self.tenant_indices[tenant_id] = index
                
                metadata_file = self.storage_path / f"{tenant_id}_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        self.tenant_metadata[tenant_id] = json.load(f)
                else:
                    self.tenant_metadata[tenant_id] = []
                
            except Exception as e:
                pass
    
    def _save_tenant_index(self, tenant_id: str):
        try:
            index_file = self.storage_path / f"{tenant_id}_index.faiss"
            faiss.write_index(self.tenant_indices[tenant_id], str(index_file))
            
            metadata_file = self.storage_path / f"{tenant_id}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.tenant_metadata[tenant_id], f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            pass
    
    def list_tenants(self) -> List[str]:
        return list(self.tenant_indices.keys())
    
    def clear_all_documents(self, tenant_id: str = "default") -> bool:
        try:
            self.tenant_indices[tenant_id] = faiss.IndexFlatIP(self.vector_dim)
            self.tenant_metadata[tenant_id] = []
            self._save_tenant_index(tenant_id)
            return True
        except Exception as e:
            return False
    
    def _remove_documents_by_filename(self, filename: str, tenant_id: str) -> bool:
        try:
            if tenant_id not in self.tenant_metadata:
                return True
            
            original_count = len(self.tenant_metadata[tenant_id])
            metadata_to_keep = []
            indices_to_keep = []
            
            for idx, metadata in enumerate(self.tenant_metadata[tenant_id]):
                if metadata.get("source") != filename:
                    metadata_to_keep.append(metadata)
                    indices_to_keep.append(idx)
            
            removed_count = original_count - len(metadata_to_keep)
            
            if removed_count == 0:
                return True
            
            if len(indices_to_keep) == 0:
                self.tenant_indices[tenant_id] = faiss.IndexFlatIP(self.vector_dim)
                self.tenant_metadata[tenant_id] = []
            else:
                old_index = self.tenant_indices[tenant_id]
                embeddings_to_keep = []
                
                for idx in indices_to_keep:
                    try:
                        vector = old_index.reconstruct(idx)
                        embeddings_to_keep.append(vector)
                    except Exception as e:
                        continue
                
                new_index = faiss.IndexFlatIP(self.vector_dim)
                if embeddings_to_keep:
                    embeddings_array = np.array(embeddings_to_keep, dtype='float32')
                    new_index.add(embeddings_array)
                
                self.tenant_indices[tenant_id] = new_index
                self.tenant_metadata[tenant_id] = metadata_to_keep
            
            self._save_tenant_index(tenant_id)
            return True
            
        except Exception as e:
            return False 