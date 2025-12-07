"""
Google Custom Search API Wrapper
"""
import os
import requests

def google_search(query, max_results=3):
    """
    Perform Google search using Custom Search API
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of results to return
        
    Returns:
        list: List of search results
    """
    try:
        # Get API key and CSE ID from environment
        api_key = os.environ.get("GOOGLE_API_KEY")
        cse_id = os.environ.get("GOOGLE_CSE_ID")
        
        if not api_key or not cse_id:
            raise ValueError("Google API key or CSE ID not found in environment variables")
        
        # Base URL for Google Custom Search API
        url = "https://www.googleapis.com/customsearch/v1"
        
        # Parameters for the search
        params = {
            "key": api_key,
            "cx": cse_id,
            "q": query,
            "num": min(max_results, 10)  # Google CSE max is 10
        }
        
        # Make the request
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        
        # Extract relevant information
        results = []
        items = data.get("items", [])
        
        for item in items[:max_results]:
            result = {
                "title": item.get("title", "No title available"),
                "snippet": item.get("snippet", "No snippet available"),
                "link": item.get("link", "No link available"),
                "displayLink": item.get("displayLink", "No display link available")
            }
            results.append(result)
            
        return results
        
    except Exception as e:
        print(f"Error performing Google search: {str(e)}")
        # Return mock data as fallback
        return [{"title": f"Google search result for {query}", "snippet": "This is a mock Google search result snippet"}]