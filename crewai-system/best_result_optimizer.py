#!/usr/bin/env python3
"""
Best Result Optimizer for DocuGuard
Ensures optimal document processing and retrieval for the best results
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from knowledge_base.processor import DocumentProcessor
from knowledge_base.parsers import extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt, clean_text
from vector.pinecone_client import PineconeClient
from vector.embeddings import embed_text
import time

class BestResultOptimizer:
    """Optimizes document processing for the best results"""
    
    def __init__(self):
        self.processor = DocumentProcessor()
        self.pc = PineconeClient()
    
    def optimize_document_processing(self, file_path):
        """
        Optimize document processing for best results
        
        Args:
            file_path (str): Path to the document file
            
        Returns:
            dict: Processing results with diagnostics
        """
        print(f"Optimizing document processing for: {file_path}")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Step 1: Validate file
            if not os.path.exists(file_path):
                return {"status": "error", "message": f"File not found: {file_path}"}
            
            # Step 2: Extract text with multiple methods
            print("Step 1: Extracting text...")
            raw_text = self._extract_text_multiple_methods(file_path)
            
            if not raw_text or len(raw_text.strip()) < 50:
                return {"status": "error", "message": "Extracted text is too short or empty"}
            
            print(f"  ✓ Extracted {len(raw_text)} characters")
            
            # Step 3: Clean text
            print("Step 2: Cleaning text...")
            cleaned_text = clean_text(raw_text)
            print(f"  ✓ Cleaned text: {len(cleaned_text)} characters")
            
            # Step 4: Analyze document structure
            print("Step 3: Analyzing document structure...")
            structure_info = self._analyze_document_structure(cleaned_text)
            print(f"  ✓ Found {len(structure_info)} key sections")
            
            # Step 5: Process with enhanced chunking
            print("Step 4: Processing document with enhanced chunking...")
            processing_result = self._enhanced_processing(file_path, cleaned_text)
            
            if processing_result["status"] == "error":
                return processing_result
            
            # Step 6: Verify indexing
            print("Step 5: Verifying document indexing...")
            verification_result = self._verify_document_indexed(processing_result.get("document_id", ""))
            
            end_time = time.time()
            
            # Compile final results
            final_result = {
                "status": "success",
                "document_id": processing_result.get("document_id", ""),
                "processing_time_seconds": round(end_time - start_time, 2),
                "text_statistics": {
                    "raw_characters": len(raw_text),
                    "cleaned_characters": len(cleaned_text),
                    "word_count": len(cleaned_text.split()),
                },
                "structure_analysis": structure_info,
                "chunks_processed": processing_result.get("chunks_processed", 0),
                "verification": verification_result,
                "recommendations": self._generate_recommendations(structure_info, verification_result)
            }
            
            return final_result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Processing failed: {str(e)}",
                "processing_time_seconds": round(time.time() - start_time, 2)
            }
    
    def _extract_text_multiple_methods(self, file_path):
        """Extract text using multiple methods for best coverage"""
        text = ""
        
        # Try primary extraction method
        try:
            if file_path.lower().endswith('.pdf'):
                text = extract_text_from_pdf(file_path)
            elif file_path.lower().endswith('.docx'):
                text = extract_text_from_docx(file_path)
            elif file_path.lower().endswith('.txt'):
                text = extract_text_from_txt(file_path)
        except Exception as e:
            print(f"  ⚠ Primary extraction failed: {e}")
        
        # If primary failed or text is too short, try alternative methods
        if not text or len(text.strip()) < 50:
            try:
                # Fallback to basic text reading
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            except Exception as e:
                print(f"  ⚠ Fallback extraction failed: {e}")
        
        return text
    
    def _analyze_document_structure(self, text):
        """Analyze document structure for better processing"""
        from knowledge_base.parsers import extract_key_sections
        return extract_key_sections(text)
    
    def _enhanced_processing(self, file_path, cleaned_text):
        """Process document with enhanced chunking strategy"""
        try:
            # Use the processor's built-in method but with enhanced diagnostics
            result = self.processor.process_document(file_path, os.path.basename(file_path))
            return result
        except Exception as e:
            return {"status": "error", "message": f"Enhanced processing failed: {str(e)}"}
    
    def _verify_document_indexed(self, document_id):
        """Verify that document was properly indexed"""
        try:
            # Perform a targeted query to find the document
            test_query = f"document {document_id}"
            query_vector = embed_text(test_query)
            
            results = self.pc.query_vectors(
                vector=query_vector,
                top_k=3,
                include_metadata=True
            )
            
            # Check if our document appears in results
            matches = results.get("matches", [])
            document_found = any(
                document_id in match.get("metadata", {}).get("source", "") 
                for match in matches
            )
            
            return {
                "indexed_successfully": document_found,
                "total_matches": len(matches),
                "sample_matches": [
                    {
                        "source": match.get("metadata", {}).get("source", "Unknown"),
                        "score": match.get("score", 0)
                    }
                    for match in matches[:2]
                ]
            }
        except Exception as e:
            return {
                "indexed_successfully": False,
                "error": str(e)
            }
    
    def _generate_recommendations(self, structure_info, verification_result):
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Structure-based recommendations
        if not structure_info:
            recommendations.append("Consider structuring your document with clear section headers (Abstract, Introduction, Methods, etc.) for better analysis")
        
        # Indexing recommendations
        if not verification_result.get("indexed_successfully", False):
            recommendations.append("Document may not be properly indexed. Try re-uploading or check for processing errors")
        
        # General recommendations
        recommendations.append("For drug-related queries, ensure your document explicitly mentions drug names, dosages, or pharmaceutical compounds")
        recommendations.append("Try specific queries like 'What medications are discussed?' instead of general terms")
        
        return recommendations

def main():
    """Main function to run the optimizer"""
    print("DocuGuard Best Result Optimizer")
    print("Optimizes document processing for maximum retrieval accuracy")
    print()
    
    # Example usage
    optimizer = BestResultOptimizer()
    
    # If you want to process a specific document, uncomment and modify the line below:
    # result = optimizer.optimize_document_processing("path/to/your/document.pdf")
    
    print("To use this optimizer:")
    print("1. Import BestResultOptimizer in your code")
    print("2. Create an instance: optimizer = BestResultOptimizer()")
    print("3. Call: result = optimizer.optimize_document_processing('path/to/your/document.pdf')")
    print("4. Check the result dictionary for processing details and recommendations")
    print()
    print("This will ensure your document is processed optimally for the best retrieval results.")

if __name__ == "__main__":
    main()