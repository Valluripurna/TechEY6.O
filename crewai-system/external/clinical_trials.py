"""
Clinical Trials API Wrapper
"""
def search_trials(query):
    """Search for clinical trials"""
    # Implementation would go here
    # For now, returning mock data
    return [{"title": f"Clinical trial for {query}", "status": "Recruiting", "phase": "Phase 2"}]