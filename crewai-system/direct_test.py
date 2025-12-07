import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_agent import KnowledgeAgent
from utils import format_external_evidence

# Create a mock PineconeClient for testing
class MockPineconeClient:
    def query_vectors(self, vector, top_k=5, include_metadata=True):
        # Return empty results to simulate no document matches
        return {"matches": []}

def test_directly():
    print("Testing DocuGuard formatting directly")
    print("=" * 50)
    
    # Create KnowledgeAgent with mock client
    mock_client = MockPineconeClient()
    agent = KnowledgeAgent(mock_client)
    
    # Test document query (should not show external evidence)
    print("TEST 1: Document Query")
    print("-" * 20)
    doc_query = "summarize the document"
    doc_response = agent.run(doc_query)
    print(f"Query: {doc_query}")
    print(f"Response:\n{doc_response}")
    print()
    
    # Test medical query (should show external evidence)
    print("TEST 2: Medical Query")
    print("-" * 20)
    medical_query = "What is diabetes?"
    
    # Mock external data
    mock_external = {
        "pubmed": [
            {
                "title": "Diabetes Overview",
                "authors": "Dr. Smith, Dr. Johnson",
                "journal": "Journal of Medicine",
                "pub_date": "2023-01-01"
            },
            {
                "title": "Type 2 Diabetes Management",
                "authors": "Dr. Williams",
                "journal": "Medical Reviews",
                "pub_date": "2023-05-15"
            }
        ],
        "google": [
            {
                "title": "What Is Diabetes? - Health Organization",
                "snippet": "Diabetes is a chronic disease that occurs when your blood glucose (blood sugar) is too high.",
                "link": "https://example.com/diabetes-overview"
            },
            {
                "title": "Diabetes Symptoms and Treatment",
                "snippet": "Common symptoms include frequent urination, increased thirst, and fatigue.",
                "link": "https://example.com/diabetes-symptoms"
            }
        ],
        "fda": [
            {
                "title": "FDA Approved Diabetes Medications",
                "summary": "The FDA has approved several medications for the treatment of diabetes including metformin and insulin."
            }
        ]
    }
    
    # Test the formatting function directly
    print(f"Query: {medical_query}")
    print("Formatted External Evidence:")
    formatted = format_external_evidence(mock_external)
    print(formatted)
    print()
    
    # Test the full response
    print("Full Response Simulation:")
    response_parts = []
    response_parts.append("📄 From Your Documents")
    response_parts.append("")
    response_parts.append("No relevant information found in the uploaded documents.")
    response_parts.append("")
    response_parts.append("🔍 Additional Medical Evidence")
    response_parts.append("")
    response_parts.append(formatted)
    response_parts.append("📚 Sources")
    
    full_response = "\n".join(response_parts)
    print(full_response)

if __name__ == "__main__":
    test_directly()