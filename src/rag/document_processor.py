import os
import io
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
from pathlib import Path

try:
    import PyPDF2
    from docx import Document
    import tiktoken
except ImportError as e:
    print(f"Missing document processing dependencies: {e}")


@dataclass
class DocumentChunk:
    content: str
    metadata: Dict[str, Any]
    chunk_id: str
    source: str
    page_number: Optional[int] = None
    chunk_index: int = 0


class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except:
            self.tokenizer = None
    
    def process_file(self, file_content: bytes, filename: str, file_type: str, 
                    tenant_id: str = "default") -> List[DocumentChunk]:
        if file_type == "application/pdf":
            text_content = self._extract_pdf_text(file_content, filename)
        elif file_type == "text/plain":
            text_content = self._extract_text_content(file_content, filename)
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text_content = self._extract_docx_content(file_content, filename)
        elif file_type in ["text/csv", "application/vnd.ms-excel", 
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            text_content = self._extract_csv_content(file_content, filename, file_type)
        else:
            text_content = [{"content": f"Unsupported file type: {file_type}", "page": 1}]
        
        chunks = []
        for page_data in text_content:
            page_chunks = self._create_chunks(
                page_data["content"], 
                filename, 
                tenant_id,
                page_data.get("page", 1)
            )
            chunks.extend(page_chunks)
        
        return chunks
    
    def _extract_pdf_text(self, file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            pages_content = []
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    pages_content.append({
                        "content": text,
                        "page": page_num
                    })
            
            if pages_content:
                return pages_content
            else:
                return [{"content": "PDF processed but no text content could be extracted. This may be an image-based PDF or contain non-text elements.", "page": 1}]
                
        except Exception as e:
            try:
                content_str = file_content.decode('utf-8', errors='ignore')
                if len(content_str.strip()) > 10:
                    return [{"content": f"PDF extraction failed, but found text content: {content_str}", "page": 1}]
            except:
                pass
            
            return [{"content": f"Unable to process PDF file '{filename}'. Please ensure it's a valid PDF with extractable text content.", "page": 1}]
    
    def _extract_text_content(self, file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        try:
            text = file_content.decode('utf-8')
            return [{"content": text, "page": 1}]
        except Exception as e:
            return [{"content": f"Error reading text file: {str(e)}", "page": 1}]
    
    def _extract_docx_content(self, file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        try:
            doc = Document(io.BytesIO(file_content))
            text_content = []
            
            for paragraph in doc.paragraphs:
                text_content.append(paragraph.text)
            
            full_text = "\n".join(text_content)
            return [{"content": full_text, "page": 1}]
        except Exception as e:
            return [{"content": f"Error extracting DOCX content: {str(e)}", "page": 1}]
    
    def _extract_csv_content(self, file_content: bytes, filename: str, file_type: str) -> List[Dict[str, Any]]:
        try:
            if file_type == "text/csv":
                df = pd.read_csv(io.BytesIO(file_content))
            else:
                df = pd.read_excel(io.BytesIO(file_content))
            
            text_content = f"File: {filename}\n\n"
            text_content += f"Shape: {df.shape[0]} rows, {df.shape[1]} columns\n\n"
            text_content += f"Columns: {', '.join(df.columns.tolist())}\n\n"
            text_content += "Data:\n"
            text_content += df.to_string(max_rows=100)
            
            if df.shape[0] > 100:
                text_content += f"\n\n... and {df.shape[0] - 100} more rows"
            
            return [{"content": text_content, "page": 1}]
        except Exception as e:
            return [{"content": f"Error processing spreadsheet: {str(e)}", "page": 1}]
    
    def _create_chunks(self, text: str, filename: str, tenant_id: str, page_number: int) -> List[DocumentChunk]:
        if not text.strip():
            return []
        
        chunks = []
        
        if self.tokenizer:
            chunks_text = self._token_based_chunking(text)
        else:
            chunks_text = self._character_based_chunking(text)
        
        for i, chunk_text in enumerate(chunks_text):
            chunk = DocumentChunk(
                content=chunk_text,
                metadata={
                    "filename": filename,
                    "tenant_id": tenant_id,
                    "page_number": page_number,
                    "chunk_index": i,
                    "total_chunks": len(chunks_text),
                    "file_type": Path(filename).suffix.lower()
                },
                chunk_id=f"{tenant_id}_{filename}_{page_number}_{i}",
                source=filename,
                page_number=page_number,
                chunk_index=i
            )
            chunks.append(chunk)
        
        return chunks
    
    def _token_based_chunking(self, text: str) -> List[str]:
        try:
            tokens = self.tokenizer.encode(text)
            chunks = []
            
            for i in range(0, len(tokens), self.chunk_size - self.chunk_overlap):
                chunk_tokens = tokens[i:i + self.chunk_size]
                chunk_text = self.tokenizer.decode(chunk_tokens)
                chunks.append(chunk_text)
            
            return chunks
        except Exception:
            return self._character_based_chunking(text)
    
    def _character_based_chunking(self, text: str) -> List[str]:
        chunks = []
        
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk = text[i:i + self.chunk_size]
            chunks.append(chunk)
        
        return chunks 