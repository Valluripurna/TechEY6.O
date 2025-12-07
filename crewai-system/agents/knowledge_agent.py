import pinecone
from vector.embeddings import embed_text
from external.medical_sources import fetch_pubmed, fetch_google, fetch_fda
from utils import generate_response, format_external_evidence
from knowledge_base.processor import DocumentProcessor
import json

class KnowledgeAgent:
    """DocuGuard - Ultra-Strict Document-First Knowledge Agent"""
    
    # Document-only query patterns
    DOCUMENT_ONLY_QUERIES = [
        "brief about document",
        "summary of document", 
        "explain document",
        "what is inside this file",
        "what drugs are used in the document",
        "explain methodology used in the document",
        "results from document",
        "what is discussed in the document",
        "this document",
        "the uploaded file",
        "my file",
        "content here",
        "summary",
        "summarize",
        "what is in the document",
        "give document overview",
        "document summary",
        "file summary",
        "tell me about this file",
        "what's in this document",
        "findings of the uploaded file",
        "this pdf",
        "this doc"
    ]

    def __init__(self, pinecone_client):
        """Initialize the KnowledgeAgent with Pinecone client"""
        self.db = pinecone_client
        self.doc_processor = DocumentProcessor()

    def is_document_query(self, query):
        """Detect if user wants document-only response"""
        q = query.lower().strip()
        # Check for exact matches first
        if q in ["hi", "hello", "hey"]:
            return False
        return any(key in q for key in self.DOCUMENT_ONLY_QUERIES)

    # STEP 1: ALWAYS search documents first
    def search_documents(self, query):
        """Search documents in Pinecone vector database with enhanced diagnostics"""
        query_vector = embed_text(query)
        results = self.db.query_vectors(
            vector=query_vector,
            top_k=10,  # Increased from 5 to 10 for better coverage
            include_metadata=True
        )
        
        # Create a new dictionary with diagnostics instead of modifying the original
        enhanced_results = {
            "matches": results.get("matches", []),
            "diagnostics": {
                "query": query,
                "total_matches": len(results.get("matches", [])),
                "top_scores": [match.get("score", 0) for match in results.get("matches", [])[:3]]
            }
        }
        
        return enhanced_results

    # STEP 2: ONLY if no documents answer the question → fetch external data
    def fetch_external(self, query):
        """Fetch external medical data when document search is insufficient"""
        # Skip external fetch for document-only queries
        if self.is_document_query(query):
            return {}
            
        return {
            "pubmed": fetch_pubmed(query),
            "google": fetch_google(query),
            "fda": fetch_fda(query)
        }

    # STEP 3: Core pipeline following DocuGuard rules
    def run(self, query):
        """Run the complete knowledge retrieval pipeline following ultra-strict document-first rules"""
        # Handle greetings and simple messages
        if query.lower().strip() in ["hi", "hello", "hey"]:
            return "Hello! I'm DocuGuard. I can help you analyze your uploaded documents. Please ask me specific questions about your documents or medical questions."
        
        # 1. Detect if user wants document-only response
        if self.is_document_query(query):
            doc_results = self.search_documents(query)

            # Document query - NEVER use external sources
            if len(doc_results["matches"]) == 0:
                # Follow exact format for no document findings
                return "📄 From Your Documents\n\nNo relevant information found in the uploaded documents."

            # Extract document content
            document_context = "\n".join([m["metadata"]["text"] for m in doc_results["matches"]])
            
            # Use BERT analysis for better document understanding
            try:
                insights = self.doc_processor.analyzer.get_document_insights(document_context, query)
                if insights.get("relevant_sections"):
                    relevant_text = "\n".join([section for section, score in insights["relevant_sections"][:2]])
                    document_context = relevant_text
                elif insights.get("summary"):
                    document_context = insights["summary"]
            except Exception as e:
                # If BERT analysis fails, use original text
                pass
            
            # Follow exact format for document findings
            return f"📄 From Your Documents\n\n{document_context}"

        # 2. For medical/scientific questions --> follow full pipeline
        doc_results = self.search_documents(query)

        # Check if we found relevant document content
        if len(doc_results["matches"]) > 0:
            # Found relevant document content - use only documents
            document_context = "\n".join([m["metadata"]["text"] for m in doc_results["matches"]])
            
            # Use BERT analysis for better document understanding
            try:
                insights = self.doc_processor.analyzer.get_document_insights(document_context, query)
                if insights.get("relevant_sections"):
                    relevant_text = "\n".join([section for section, score in insights["relevant_sections"][:2]])
                    document_context = relevant_text
            except Exception as e:
                # If BERT analysis fails, use original text
                pass
            
            # Check if we should also include external evidence
            external = self.fetch_external(query)
            has_external_data = any([
                external.get("pubmed"),
                external.get("google"),
                external.get("fda")
            ])
            
            if has_external_data:
                # Follow format for both document findings and external evidence
                response_parts = []
                response_parts.append("📄 From Your Documents")
                response_parts.append("")
                response_parts.append(document_context)
                response_parts.append("")
                response_parts.append("🔍 Additional Medical Evidence")
                response_parts.append("")
                response_parts.append(format_external_evidence(external))
                response_parts.append("📚 Sources")
                return "\n".join(response_parts)
            else:
                # Follow exact format for document findings only
                response_parts = []
                response_parts.append("📄 From Your Documents")
                response_parts.append("")
                response_parts.append(document_context)
                return "\n".join(response_parts)

        # 3. If no document info exists --> fallback to medical reasoner ONLY for medical questions
        external = self.fetch_external(query)
        
        # Check if we have any external data
        has_external_data = any([
            external.get("pubmed"),
            external.get("google"),
            external.get("fda")
        ])
        
        if not has_external_data:
            # No document content and no external data
            response_parts = []
            response_parts.append("📄 From Your Documents")
            response_parts.append("")
            response_parts.append("No relevant information found in the uploaded documents.")
            return "\n".join(response_parts)
        
        # Follow exact format for external medical evidence
        response_parts = []
        response_parts.append("📄 From Your Documents")
        response_parts.append("")
        response_parts.append("No relevant information found in the uploaded documents.")
        response_parts.append("")
        response_parts.append("🔍 Additional Medical Evidence")
        response_parts.append("")
        response_parts.append(format_external_evidence(external))
        response_parts.append("📚 Sources")
        
        return "\n".join(response_parts)