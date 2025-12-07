import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.knowledge_agent import KnowledgeAgent

# Create a mock PineconeClient for testing
class MockPineconeClient:
    def query_vectors(self, vector, top_k=5, include_metadata=True):
        # Return empty results to simulate no document matches
        return {"matches": []}

def test_document_queries():
    print("DocuGuard Document-Only Query Testing")
    print("=" * 50)
    
    # Create KnowledgeAgent with mock client
    mock_client = MockPineconeClient()
    agent = KnowledgeAgent(mock_client)
    
    # Test various document-only queries
    document_queries = [
        "summarize the document",
        "brief about document",
        "what is inside this file",
        "explain document",
        "document summary"
    ]
    
    for query in document_queries:
        print(f"Query: {query}")
        response = agent.run(query)
        print(f"Response:\n{response}")
        print("-" * 30)

if __name__ == "__main__":
    test_document_queries()