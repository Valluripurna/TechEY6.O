import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import format_external_evidence

def demo_formatting():
    print("DocuGuard External Evidence Formatting Demo")
    print("=" * 50)
    
    # Sample external data
    sample_data = {
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
    
    print("BEFORE - Raw data format:")
    print(sample_data)
    print()
    
    print("AFTER - Clean, formatted output:")
    print("-" * 30)
    formatted = format_external_evidence(sample_data)
    print(formatted)

if __name__ == "__main__":
    demo_formatting()