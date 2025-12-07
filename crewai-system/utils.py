"""
Utility functions for DocuGuard
"""

# Document-first system prompt
DOCUMENT_FIRST_SYSTEM_PROMPT = """You are DocuGuard, an AI assistant that answers questions using the user's uploaded documents as the primary source."""

def format_external_evidence(external_data):
    """
    Format external medical evidence in a clean, readable way
    
    Args:
        external_data (dict): External data from PubMed, Google, FDA
        
    Returns:
        str: Formatted external evidence
    """
    if not external_data:
        return ""
        
    formatted_parts = []
    
    # Add formatted PubMed data if available
    if external_data.get("pubmed"):
        formatted_parts.append("🔬 PubMed Research:")
        for i, article in enumerate(external_data["pubmed"][:3], 1):
            title = article.get("title", "No title")
            authors = article.get("authors", "Unknown authors")
            journal = article.get("journal", "Unknown journal")
            pub_date = article.get("pub_date", "Unknown date")
            formatted_parts.append(f"  {i}. {title}")
            formatted_parts.append(f"     Authors: {authors}")
            formatted_parts.append(f"     Journal: {journal}, {pub_date}")
            formatted_parts.append("")
        
    # Add formatted Google data if available
    if external_data.get("google"):
        formatted_parts.append("🌐 Web Search Results:")
        for i, result in enumerate(external_data["google"][:3], 1):
            title = result.get("title", "No title")
            snippet = result.get("snippet", "No description available")
            link = result.get("link", "#")
            formatted_parts.append(f"  {i}. {title}")
            formatted_parts.append(f"     {snippet}")
            formatted_parts.append(f"     Source: {link}")
            formatted_parts.append("")
        
    # Add formatted FDA data if available
    if external_data.get("fda"):
        formatted_parts.append("💊 FDA Information:")
        for i, result in enumerate(external_data["fda"][:2], 1):
            title = result.get("title", "No title")
            summary = result.get("summary", "No summary available")
            formatted_parts.append(f"  {i}. {title}")
            formatted_parts.append(f"     {summary}")
            formatted_parts.append("")
            
    return "\n".join(formatted_parts)

def generate_response(user_query, document_context, external_context=None):
    """
    Generate a response following DocuGuard format
    
    Args:
        user_query (str): The user's question
        document_context (str): Content extracted from relevant documents
        external_context (dict): External medical data if needed
        
    Returns:
        str: Generated response in DocuGuard format
    """
    # Follow exact format for document findings
    if document_context and document_context.strip():
        return f"📄 From Your Documents\n\n{document_context}"
    
    # If no document context but external context is provided
    if external_context:
        response_parts = []
        response_parts.append("📄 From Your Documents")
        response_parts.append("")
        response_parts.append("No relevant information found in the uploaded documents.")
        response_parts.append("")
        response_parts.append("🔍 Additional Medical Evidence")
        response_parts.append("")
        response_parts.append(format_external_evidence(external_context))
        response_parts.append("📚 Sources")
        
        return "\n".join(response_parts)
    
    # No information available
    return "📄 From Your Documents\n\nNo relevant information found in the uploaded documents."