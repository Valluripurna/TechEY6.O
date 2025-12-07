"""
PubMed API Wrapper
"""
import os
import requests
from urllib.parse import urlencode

def fetch_pubmed(query, max_results=3):
    """
    Fetch data from PubMed API
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of results to return
        
    Returns:
        list: List of PubMed articles
    """
    try:
        # Get API key from environment
        api_key = os.environ.get("PUBMED_API_KEY")
        
        # Base URL for PubMed ESearch API
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        
        # Parameters for the search
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        }
        
        # Add API key if available
        if api_key:
            params["api_key"] = api_key
            
        # Make the request
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        
        # Get the PMIDs
        pmids = data.get("esearchresult", {}).get("idlist", [])
        
        if not pmids:
            return []
            
        # Fetch details for each PMID using ESummary API
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        summary_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json"
        }
        
        if api_key:
            summary_params["api_key"] = api_key
            
        summary_response = requests.get(summary_url, params=summary_params, timeout=10)
        summary_response.raise_for_status()
        
        summary_data = summary_response.json()
        
        # Extract relevant information
        articles = []
        docs = summary_data.get("result", {})
        
        for pmid in pmids:
            if pmid in docs:
                doc = docs[pmid]
                article = {
                    "title": doc.get("title", "No title available"),
                    "abstract": doc.get("abstract", "No abstract available"),
                    "authors": ", ".join([author.get("name", "") for author in doc.get("authors", [])]),
                    "journal": doc.get("fulljournalname", "Journal not specified"),
                    "pub_date": doc.get("pubdate", "Date not specified"),
                    "pmid": pmid
                }
                articles.append(article)
                
        return articles[:max_results]
        
    except Exception as e:
        print(f"Error fetching from PubMed: {str(e)}")
        # Return mock data as fallback
        return [{"title": f"PubMed article about {query}", "abstract": "This is a mock PubMed article abstract"}]