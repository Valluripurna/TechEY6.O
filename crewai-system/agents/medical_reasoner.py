# Note: These imports would need to be implemented based on actual external API wrappers
# For now, we'll use mock implementations

def fetch_pubmed(query):
    return [{"title": f"Mock PubMed result for {query}", "abstract": "This is a mock result"}]

def google_search(query):
    return [{"title": f"Mock Google result for {query}", "snippet": "This is a mock result"}]

def search_trials(query):
    return [{"title": f"Mock Clinical trial for {query}", "status": "Recruiting"}]

def search_patents(query):
    return [{"title": f"Mock Patent for {query}", "assignee": "PharmaCorp"}]

class MedicalReasoner:
    """Fallback Medical Reasoner Agent for external queries"""

    def run(self, query):
        """Run the medical reasoning pipeline with external sources"""
        pubmed = fetch_pubmed(query)
        google = google_search(query)
        trials = search_trials(query)
        patents = search_patents(query)

        external_context = {
            "pubmed": pubmed,
            "google": google,
            "trials": trials,
            "patents": patents
        }

        return external_context