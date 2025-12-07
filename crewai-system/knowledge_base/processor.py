"""
Document processor that combines parsing and analysis functionality
"""
import os
import uuid
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from .parsers import extract_text_from_file, clean_text
from .analyzer import DocumentAnalyzer
# Use absolute import like other files
from vector.embeddings import embed_text

class DocumentProcessor:
    """Processor for handling document parsing, analysis, and storage"""
    
    def __init__(self):
        """Initialize the document processor"""
        self.analyzer = DocumentAnalyzer()
        # Import here to avoid circular imports
        from vector.pinecone_client import PineconeClient
        self.pinecone_client = PineconeClient()
        
    def process_document(self, file_path, file_name=None):
        """
        Process document with enhanced error handling and validation
        
        Args:
            file_path (str): Path to the document file
            file_name (str): Original file name
            
        Returns:
            dict: Processing results with status and document info
        """
        try:
            # Extract text using the unified function
            text_content = extract_text_from_file(file_path)
            
            # Validate content quality
            if not text_content or len(text_content.strip()) < 50:
                raise ValueError("Extracted text is too short or empty")
            
            # Get document insights using BERT analysis
            try:
                insights = self.analyzer.get_document_insights(text_content)
            except Exception as e:
                print(f"Warning: Error analyzing document {file_path}: {str(e)}")
                insights = {}
            
            # Chunk document for better processing
            chunks = self._chunk_text(text_content)
            
            # Generate embeddings for each chunk
            doc_id = file_name or os.path.basename(file_path)
            processed_chunks = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                embedding = embed_text(chunk)
                
                # Store in Pinecone with metadata
                self.pinecone_client.upsert(
                    vectors=[(chunk_id, embedding, {
                        "text": chunk,
                        "source": doc_id,
                        "chunk_index": i,
                        "processed_at": datetime.now().isoformat()
                    })]
                )
                
                processed_chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk[:100] + "..." if len(chunk) > 100 else chunk
                })
            
            # Prepare document data
            doc_data = {
                "id": doc_id,
                "filename": os.path.basename(file_path),
                "file_path": file_path,
                "text_content": text_content,
                "word_count": len(text_content.split()),
                "character_count": len(text_content),
                "insights": insights,
                "processed_at": datetime.now().isoformat()
            }
            
            return {
                "status": "success",
                "document": doc_data,
                "document_id": doc_id,
                "chunks_processed": len(processed_chunks),
                "sample_chunks": processed_chunks[:3]  # Show first 3 chunks as samples
            }
            
        except Exception as e:
            # Enhanced error logging
            error_details = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "file_path": file_path,
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"Document processing error: {error_details}")
            
            return {
                "status": "error",
                "error": error_details
            }
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into chunks for better processing
        
        Args:
            text (str): Text to chunk
            chunk_size (int): Size of each chunk in characters
            overlap (int): Overlap between chunks in characters
            
        Returns:
            List[str]: List of text chunks
        """
        chunks = []
        
        # Simple chunking by sentences
        import re
        sentences = re.split(r'[.!?]+', text)
        
        current_chunk = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # If adding this sentence would exceed chunk size, save current chunk
            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Start new chunk with overlap
                words = current_chunk.split()
                overlap_words = words[-(overlap//5):] if len(words) > overlap//5 else []
                current_chunk = " ".join(overlap_words) + " " + sentence + " "
            else:
                current_chunk += sentence + ". "
        
        # Add the final chunk if it has content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def process_documents_batch(self, file_paths: List[str]) -> List[Dict]:
        """
        Process multiple documents
        
        Args:
            file_paths (List[str]): List of paths to document files
            
        Returns:
            List[Dict]: List of processed document data
        """
        processed_docs = []
        
        for file_path in file_paths:
            try:
                doc_data = self.process_document(file_path)
                processed_docs.append(doc_data)
                print(f"Processed document: {file_path}")
            except Exception as e:
                print(f"Error processing document {file_path}: {str(e)}")
                continue
                
        return processed_docs
    
    def find_relevant_documents(self, query: str, documents: List[Dict], top_k: int = 3) -> List[Tuple[Dict, float]]:
        """
        Find documents most relevant to a query
        
        Args:
            query (str): Query string
            documents (List[Dict]): List of document data dictionaries
            top_k (int): Number of top relevant documents to return
            
        Returns:
            List[Tuple[Dict, float]]: List of (document, similarity_score) tuples
        """
        if not documents:
            return []
            
        # Extract document texts
        doc_texts = [doc["text_content"] for doc in documents if doc.get("text_content")]
        doc_objects = [doc for doc in documents if doc.get("text_content")]
        
        if not doc_texts:
            return []
            
        # Get embeddings
        try:
            query_embedding = self.analyzer.get_embeddings([query])
            doc_embeddings = self.analyzer.get_embeddings(doc_texts)
            
            # Calculate similarities
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
            
            # Get top-k most similar documents
            import numpy as np
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Only return documents with some similarity
                    results.append((doc_objects[idx], float(similarities[idx])))
                    
            return results
        except Exception as e:
            print(f"Error finding relevant documents: {str(e)}")
            return []
    
    def generate_document_summary(self, document: Dict) -> str:
        """
        Generate a summary for a document
        
        Args:
            document (Dict): Document data dictionary
            
        Returns:
            str: Document summary
        """
        text_content = document.get("text_content", "")
        if not text_content:
            return "No content available."
            
        return self.analyzer.summarize_document(text_content)
    
    def get_document_topics(self, document: Dict) -> Dict[str, float]:
        """
        Get topics for a document
        
        Args:
            document (Dict): Document data dictionary
            
        Returns:
            Dict[str, float]: Dictionary of topics and their relevance scores
        """
        text_content = document.get("text_content", "")
        if not text_content:
            return {}
            
        return self.analyzer.analyze_document_topics(text_content)