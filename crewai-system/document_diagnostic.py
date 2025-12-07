#!/usr/bin/env python3
"""
Document Diagnostic Tool for DocuGuard
Helps diagnose issues with document processing and retrieval
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vector.pinecone_client import PineconeClient
from vector.embeddings import embed_text
import json

def diagnose_documents():
    """Diagnose document processing issues"""
    print("DocuGuard Document Diagnostic Tool")
    print("=" * 50)
    
    try:
        # Initialize Pinecone client
        pc = PineconeClient()
        print("✓ Pinecone client initialized successfully")
        
        # Check if there are any documents indexed
        try:
            # Try to get index stats
            index_name = os.getenv('PINECONE_INDEX_NAME', 'pharma-mind-nexus')
            print(f"✓ Using index: {index_name}")
            
            # Perform a simple query to check if there's data
            test_query = "test document query"
            query_vector = embed_text(test_query)
            
            results = pc.query_vectors(
                vector=query_vector,
                top_k=5,
                include_metadata=True
            )
            
            total_matches = len(results.get("matches", []))
            print(f"✓ Index query successful - Found {total_matches} matches")
            
            if total_matches > 0:
                print("\nDocument Analysis:")
                print("-" * 30)
                for i, match in enumerate(results["matches"][:3], 1):
                    metadata = match.get("metadata", {})
                    source = metadata.get("source", "Unknown")
                    text_preview = metadata.get("text", "")[:100] + "..." if len(metadata.get("text", "")) > 100 else metadata.get("text", "")
                    score = match.get("score", 0)
                    
                    print(f"{i}. Source: {source}")
                    print(f"   Score: {score:.4f}")
                    print(f"   Preview: {text_preview}")
                    print()
            else:
                print("⚠ No documents found in the index")
                print("  This could mean:")
                print("  - No documents have been uploaded yet")
                print("  - Documents were uploaded but failed processing")
                print("  - Index connection issues")
                
        except Exception as e:
            print(f"✗ Error querying index: {e}")
            return
            
        # Provide troubleshooting suggestions
        print("\nTroubleshooting Suggestions:")
        print("-" * 30)
        print("1. Verify document was uploaded successfully")
        print("2. Check if document processing completed without errors")
        print("3. Try uploading a simpler test document (plain text)")
        print("4. Ensure document contains sufficient text content (>50 characters)")
        print("5. Check file format is supported (.pdf, .docx, .txt)")
        
        # Test queries you can try
        print("\nSample Queries to Test:")
        print("-" * 30)
        print("• 'What is this document about?'")
        print("• 'Summarize the document'")
        print("• 'Give me an overview'")
        print("• 'What drugs are mentioned?' (if applicable)")
        
    except Exception as e:
        print(f"✗ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_documents()