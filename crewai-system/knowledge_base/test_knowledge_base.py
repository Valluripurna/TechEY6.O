"""
Test script for the knowledge base module
"""
import os
from knowledge_base import DocumentProcessor, extract_text_from_file

def test_document_processing():
    """Test document processing functionality"""
    # Initialize document processor
    processor = DocumentProcessor()
    
    # Create a sample text file for testing
    sample_text = """
    This is a sample medical document about diabetes treatment.
    Diabetes is a chronic disease that affects blood sugar levels.
    Treatment options include insulin therapy and lifestyle changes.
    Patients should monitor their blood glucose regularly.
    Exercise and diet play important roles in diabetes management.
    """
    
    # Write sample text to file
    sample_file = "sample_medical_doc.txt"
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write(sample_text)
    
    try:
        # Test document processing
        print("Testing document processing...")
        doc_data = processor.process_document(sample_file)
        
        print(f"Document ID: {doc_data['id']}")
        print(f"Filename: {doc_data['filename']}")
        print(f"Word count: {doc_data['word_count']}")
        print(f"Character count: {doc_data['character_count']}")
        print("\nDocument insights:")
        print(f"Summary: {doc_data['insights'].get('summary', 'N/A')}")
        print(f"Topics: {doc_data['insights'].get('topics', 'N/A')}")
        
        # Test query functionality
        print("\n\nTesting query functionality...")
        query = "diabetes treatment options"
        relevant_docs = processor.find_relevant_documents(query, [doc_data])
        
        if relevant_docs:
            doc, score = relevant_docs[0]
            print(f"Most relevant document: {doc['filename']} (Score: {score:.2f})")
        else:
            print("No relevant documents found.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Clean up sample file
        if os.path.exists(sample_file):
            os.remove(sample_file)

def test_text_extraction():
    """Test text extraction from different file formats"""
    print("\n\nTesting text extraction...")
    
    # Test with the sample text file we created
    sample_text = """
    Sample document for testing text extraction.
    This document contains multiple paragraphs.
    
    Second paragraph with more content.
    
    Third paragraph to test extraction.
    """
    
    sample_file = "extraction_test.txt"
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write(sample_text)
    
    try:
        extracted_text = extract_text_from_file(sample_file)
        print(f"Extracted text:\n{extracted_text}")
        print(f"Length: {len(extracted_text)} characters")
    except Exception as e:
        print(f"Error extracting text: {str(e)}")
    finally:
        if os.path.exists(sample_file):
            os.remove(sample_file)

if __name__ == "__main__":
    test_document_processing()
    test_text_extraction()