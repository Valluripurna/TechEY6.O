"""
FDA API Wrapper
"""
import os
import requests

def fetch_fda(query, max_results=3):
    """
    Fetch data from FDA API
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of results to return
        
    Returns:
        list: List of FDA drug information
    """
    try:
        # Get API key from environment (optional for openFDA)
        api_key = os.environ.get("OPENFDA_API_KEY")
        
        # Base URL for openFDA Drug API
        base_url = "https://api.fda.gov/drug/label.json"
        
        # Parameters for the search
        params = {
            "search": query,
            "limit": max_results
        }
        
        # Add API key if available
        if api_key:
            params["api_key"] = api_key
            
        # Make the request
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        
        # Parse the response
        data = response.json()
        
        # Extract relevant information
        results = []
        drugs = data.get("results", [])
        
        for drug in drugs[:max_results]:
            # Extract drug information
            drug_info = {
                "brand_name": drug.get("openfda", {}).get("brand_name", ["Not specified"])[0],
                "generic_name": drug.get("openfda", {}).get("generic_name", ["Not specified"])[0],
                "manufacturer": drug.get("openfda", {}).get("manufacturer_name", ["Not specified"])[0],
                "purpose": drug.get("purpose", ["Not specified"])[0] if drug.get("purpose") else "Not specified",
                "warnings": drug.get("warnings", ["No warnings specified"])[0] if drug.get("warnings") else "No warnings specified",
                "indications": drug.get("indications_and_usage", ["Not specified"])[0] if drug.get("indications_and_usage") else "Not specified"
            }
            
            # Create a summary
            summary = f"Brand: {drug_info['brand_name']}\nGeneric: {drug_info['generic_name']}\nPurpose: {drug_info['purpose']}\nManufacturer: {drug_info['manufacturer']}"
            
            result = {
                "title": f"{drug_info['brand_name']} ({drug_info['generic_name']})",
                "summary": summary,
                "details": drug_info
            }
            
            results.append(result)
            
        return results
        
    except Exception as e:
        print(f"Error fetching from FDA: {str(e)}")
        # Return mock data as fallback
        return [{"title": f"FDA drug information for {query}", "summary": "This is a mock FDA drug information summary"}]