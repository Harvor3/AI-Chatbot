import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import uuid

@dataclass
class TenantInfo:
    tenant_id: str
    name: str
    email: Optional[str] = None
    created_at: str = ""
    last_accessed: str = ""
    document_count: int = 0
    total_chunks: int = 0
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.last_accessed = datetime.now().isoformat()

@dataclass
class DocumentInfo:
    filename: str
    tenant_id: str
    file_type: str
    file_size: int
    upload_date: str
    chunks_created: int
    file_path: str
    
    def __post_init__(self):
        if not hasattr(self, 'upload_date') or not self.upload_date:
            self.upload_date = datetime.now().isoformat()

class TenantManager:
    def __init__(self, storage_path: str = "tenant_storage"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        self.tenants_file = self.storage_path / "tenants.json"
        self.documents_file = self.storage_path / "documents.json"
        
        self.tenants: Dict[str, TenantInfo] = {}
        self.documents: Dict[str, List[DocumentInfo]] = {}
        
        self._load_data()
    
    def _load_data(self):
        if self.tenants_file.exists():
            try:
                with open(self.tenants_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tenants = {
                        tid: TenantInfo(**info) for tid, info in data.items()
                    }
            except Exception as e:
                print(f"Error loading tenants: {e}")
        
        if self.documents_file.exists():
            try:
                with open(self.documents_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.documents = {
                        tid: [DocumentInfo(**doc) for doc in docs] 
                        for tid, docs in data.items()
                    }
            except Exception as e:
                print(f"Error loading documents: {e}")
    
    def _save_data(self):
        try:
            with open(self.tenants_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {tid: asdict(info) for tid, info in self.tenants.items()}, 
                    f, indent=2, ensure_ascii=False
                )
            
            with open(self.documents_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {tid: [asdict(doc) for doc in docs] for tid, docs in self.documents.items()}, 
                    f, indent=2, ensure_ascii=False
                )
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def create_tenant(self, name: str, email: Optional[str] = None, tenant_id: Optional[str] = None) -> str:
        if not tenant_id:
            tenant_id = str(uuid.uuid4())[:8]
        
        tenant_info = TenantInfo(
            tenant_id=tenant_id,
            name=name,
            email=email
        )
        
        self.tenants[tenant_id] = tenant_info
        self.documents[tenant_id] = []
        self._save_data()
        
        return tenant_id
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantInfo]:
        if tenant_id in self.tenants:
            self.tenants[tenant_id].last_accessed = datetime.now().isoformat()
            self._save_data()
            return self.tenants[tenant_id]
        return None
    
    def list_tenants(self) -> List[TenantInfo]:
        return list(self.tenants.values())
    
    def add_document(self, tenant_id: str, filename: str, file_type: str, 
                    file_size: int, chunks_created: int, file_content: bytes) -> bool:
        try:
            tenant_dir = self.storage_path / tenant_id
            tenant_dir.mkdir(exist_ok=True)
            
            file_path = tenant_dir / filename
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            doc_info = DocumentInfo(
                filename=filename,
                tenant_id=tenant_id,
                file_type=file_type,
                file_size=file_size,
                upload_date=datetime.now().isoformat(),
                chunks_created=chunks_created,
                file_path=str(file_path)
            )
            
            if tenant_id not in self.documents:
                self.documents[tenant_id] = []
            
            existing_doc_index = None
            for i, doc in enumerate(self.documents[tenant_id]):
                if doc.filename == filename:
                    existing_doc_index = i
                    break
            
            if existing_doc_index is not None:
                self.documents[tenant_id][existing_doc_index] = doc_info
            else:
                self.documents[tenant_id].append(doc_info)
            
            if tenant_id in self.tenants:
                self.tenants[tenant_id].document_count = len(self.documents[tenant_id])
                self.tenants[tenant_id].total_chunks = sum(doc.chunks_created for doc in self.documents[tenant_id])
                self.tenants[tenant_id].last_accessed = datetime.now().isoformat()
            
            self._save_data()
            return True
            
        except Exception as e:
            print(f"Error adding document: {e}")
            return False
    
    def get_tenant_documents(self, tenant_id: str) -> List[DocumentInfo]:
        return self.documents.get(tenant_id, [])
    
    def get_document_content(self, tenant_id: str, filename: str) -> Optional[bytes]:
        try:
            docs = self.documents.get(tenant_id, [])
            for doc in docs:
                if doc.filename == filename:
                    with open(doc.file_path, 'rb') as f:
                        return f.read()
            return None
        except Exception as e:
            print(f"Error reading document: {e}")
            return None
    
    def delete_document(self, tenant_id: str, filename: str) -> bool:
        try:
            docs = self.documents.get(tenant_id, [])
            for i, doc in enumerate(docs):
                if doc.filename == filename:
                    # Try to delete the physical file, but don't fail if it doesn't exist
                    if os.path.exists(doc.file_path):
                        try:
                            os.remove(doc.file_path)
                            print(f"✅ Deleted physical file: {doc.file_path}")
                        except Exception as e:
                            print(f"⚠️ Warning: Could not delete physical file {doc.file_path}: {e}")
                    else:
                        print(f"⚠️ Physical file not found (orphaned reference): {doc.file_path}")
                    
                    # Always remove from metadata even if physical file deletion failed
                    del self.documents[tenant_id][i]
                    
                    # Update tenant statistics
                    if tenant_id in self.tenants:
                        self.tenants[tenant_id].document_count = len(self.documents[tenant_id])
                        self.tenants[tenant_id].total_chunks = sum(d.chunks_created for d in self.documents[tenant_id])
                    
                    self._save_data()
                    print(f"✅ Removed document reference: {filename}")
                    return True
            
            print(f"❌ Document not found in metadata: {filename}")
            return False
        except Exception as e:
            print(f"❌ Error deleting document: {e}")
            return False
    
    def cleanup_orphaned_references(self) -> int:
        """Clean up orphaned document references that point to non-existent files"""
        total_removed = 0
        
        for tenant_id, docs in self.documents.items():
            if not docs:
                continue
                
            valid_docs = []
            for doc in docs:
                if os.path.exists(doc.file_path):
                    valid_docs.append(doc)
                else:
                    print(f"🧹 Removing orphaned reference: {doc.filename} (tenant: {tenant_id})")
                    total_removed += 1
            
            self.documents[tenant_id] = valid_docs
            
            # Update tenant statistics
            if tenant_id in self.tenants:
                self.tenants[tenant_id].document_count = len(valid_docs)
                self.tenants[tenant_id].total_chunks = sum(d.chunks_created for d in valid_docs)
        
        if total_removed > 0:
            self._save_data()
            print(f"✅ Cleaned up {total_removed} orphaned document references")
        
        return total_removed

    def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        tenant = self.get_tenant(tenant_id)
        docs = self.get_tenant_documents(tenant_id)
        
        if not tenant:
            return {
                "tenant_id": tenant_id,
                "exists": False,
                "document_count": 0,
                "total_size": 0,
                "files": []
            }
        
        total_size = sum(doc.file_size for doc in docs)
        filenames = [doc.filename for doc in docs]
        
        return {
            "tenant_id": tenant_id,
            "name": tenant.name,
            "email": tenant.email,
            "exists": True,
            "document_count": len(docs),
            "total_chunks": tenant.total_chunks,
            "total_size": total_size,
            "files": filenames,
            "created_at": tenant.created_at,
            "last_accessed": tenant.last_accessed
        } 