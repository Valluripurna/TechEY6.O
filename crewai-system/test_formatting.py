import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_agent import KnowledgeAgent
from vector.pinecone_client import PineconeClient
from external.medical_sources import fetch_pubmed, fetch_google, fetch_fda

# Create a mock PineconeClient for testing
class MockPineconeClient:
    def query_vectors(self, vector, top_k=5, include_metadata=True):
        # Return empty results to simulate no document matches
        return {"matches": []}

# Test the KnowledgeAgent with our formatting changes
def test_formatting():
    # Create KnowledgeAgent with mock client
    mock_client = MockPineconeClient()
    agent = KnowledgeAgent(mock_client)
    
    # Test a medical query that should trigger external sources
    query = "What is diabetes?"
    print(f"Testing query: {query}")
    print("=" * 50)
    
    # Mock external data to test formatting
    mock_pubmed = [
        {
            "title": "Diabetes Overview",
            "authors": "Dr. Smith, Dr. Johnson",
            "journal": "Journal of Medicine",
            "pub_date": "2023-01-01"
        }
    ]
    
    mock_google = [
        {
            "title": "What Is Diabetes?",
            "snippet": "Diabetes is a chronic disease that occurs when your blood glucose is too high.",
            "link": "https://example.com/diabetes"
        }
    ]
    
    mock_fda = [
        {
            "title": "Diabetes Medications",
            "summary": "Information about medications used to treat diabetes."
        }
    ]
    
    # Override the fetch_external method to return mock data
    original_fetch = agent.fetch_external
    
    def mock_fetch_external(query):
        # Skip external fetch for document-only queries
        if agent.is_document_query(query):
            return {}
        
        return {
            "pubmed": mock_pubmed,
            "google": mock_google,
            "fda": mock_fda
        }
    
    agent.fetch_external = mock_fetch_external
    
    # Run the agent
    response = agent.run(query)
    print(response)
    print("=" * 50)
    
    # Test a document query
    doc_query = "summarize the document"
    print(f"Testing document query: {doc_query}")
    print("=" * 50)
    
    doc_response = agent.run(doc_query)
    print(doc_response)
    print("=" * 50)

if __name__ == "__main__":
    test_formatting()