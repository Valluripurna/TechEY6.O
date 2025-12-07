"""
Medical Sources API Wrappers
"""
import os
from .pubmed import fetch_pubmed as _fetch_pubmed
from .google_cse import google_search as _fetch_google
from .fda import fetch_fda as _fetch_fda

def fetch_pubmed(query):
    """Fetch data from PubMed"""
    return _fetch_pubmed(query)

def fetch_google(query):
    """Fetch data from Google Search"""
    return _fetch_google(query)

def fetch_fda(query):
    """Fetch data from FDA"""
    return _fetch_fda(query)