"""
LLM Processor for synthesizing natural language reports from JSON data
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def synthesize_report_with_llm(query, data):
    """
    Synthesize a natural language report from JSON data using an LLM
    
    Args:
        query (str): Original query
        data (dict): Collected data from agents
        
    Returns:
        str: Natural language report
    """
    try:
        # Try to use Google Gemini API first
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if gemini_api_key and gemini_api_key != "your_gemini_api_key_here":
            return _synthesize_with_gemini(query, data, gemini_api_key)
        
        # Fallback to existing implementation if Gemini API key is not available
        # Create a prompt that would be sent to an LLM
        prompt = f"""
        Create a comprehensive pharmaceutical research report based on the following data.
        
        Query: {query}
        
        Data:
        {json.dumps(data, indent=2)}
        
        Please provide:
        1. An executive summary
        2. Key findings for each data category
        3. Insights and recommendations
        4. Future research directions
        
        Format the response as a professional pharmaceutical research report.
        """
        
        # Mock LLM response - in reality this would call an actual LLM API
        report = _generate_mock_llm_response(query, data)
        return report
        
    except Exception as e:
        print(f"Error in LLM processing: {str(e)}")
        # Fallback to basic text summary if LLM fails
        return _generate_basic_summary(query, data)

def _generate_mock_llm_response(query, data):
    """
    Generate a mock LLM response that simulates what a real LLM would produce
    
    Args:
        query (str): Original query
        data (dict): Collected data
        
    Returns:
        str: Mock LLM-generated report
    """
    # Extract key information from data
    key_findings = []
    data_summary = []
    
    for section, content in data.items():
        if not content:
            continue
            
        data_summary.append(f"\n{section.upper()}:")
        
        if isinstance(content, list) and len(content) > 0:
            # Handle list data (like patents, trials)
            data_summary.append(f"  - Found {len(content)} items")
            if isinstance(content[0], dict):
                # Show first item as example
                example = content[0]
                example_str = ", ".join([f"{k}: {v}" for k, v in example.items() if v])
                data_summary.append(f"  - Example: {example_str}")
                
                # Add key findings based on content type
                if "patent" in section.lower():
                    key_findings.append(f"Recent patent activity indicates innovation in {query} treatments")
                elif "trial" in section.lower():
                    key_findings.append(f"Clinical trials show active research in {query} therapies")
                    
        elif isinstance(content, dict):
            # Handle dictionary data (like market stats)
            for key, value in content.items():
                data_summary.append(f"  - {key.replace('_', ' ').title()}: {value}")
                
                # Add key findings based on content
                if "market" in key.lower():
                    key_findings.append(f"Market analysis shows strong growth potential for {query}")
                    
    # Create mock report sections
    report_sections = [
        f"PHARMACEUTICAL RESEARCH SYNTHESIS REPORT: {query.upper()}",
        "=" * 60,
        f"Generated on: {datetime.now().strftime('%B %d, %Y')}",
        "",
        "EXECUTIVE SUMMARY",
        "-" * 20,
        f"This comprehensive analysis of {query} covers multiple aspects of pharmaceutical research "
        f"including market dynamics, intellectual property landscape, clinical development, and "
        f"regulatory considerations. Key findings suggest significant ongoing innovation and "
        f"commercial interest in this therapeutic area.",
        "",
        "KEY FINDINGS",
        "-" * 15
    ]
    
    # Add key findings
    for i, finding in enumerate(key_findings, 1):
        report_sections.append(f"{i}. {finding}")
    
    # Add data summary
    report_sections.append("")
    report_sections.append("DATA ANALYSIS")
    report_sections.append("-" * 15)
    report_sections.extend(data_summary)
    
    # Add insights and recommendations
    report_sections.append("")
    report_sections.append("INSIGHTS AND RECOMMENDATIONS")
    report_sections.append("-" * 30)
    report_sections.append(
        "Based on the analyzed data, we recommend prioritizing research investments in "
        "this therapeutic area. The strong patent portfolio and active clinical trial "
        "landscape indicate both opportunity and competition. Companies should consider "
        "strategic partnerships to accelerate development timelines."
    )
    
    # Add future research directions
    report_sections.append("")
    report_sections.append("FUTURE RESEARCH DIRECTIONS")
    report_sections.append("-" * 25)
    report_sections.append(
        "Future research should focus on comparative effectiveness studies, "
        "real-world evidence generation, and exploration of combination therapies. "
        "Additionally, monitoring regulatory pathways and payer coverage decisions "
        "will be crucial for commercial success."
    )
    
    return "\n".join(report_sections)

def _generate_basic_summary(query, data):
    """
    Generate a basic text summary when LLM processing fails
    
    Args:
        query (str): Original query
        data (dict): Collected data
        
    Returns:
        str: Basic text summary
    """
    summary = f"PHARMA RESEARCH SUMMARY FOR: {query}\n"
    summary += "=" * 50 + "\n\n"
    summary += f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    for section, content in data.items():
        if not content:
            continue
            
        summary += f"{section.upper()}:\n"
        summary += "-" * len(section) + "\n"
        
        if isinstance(content, list):
            summary += f"  Found {len(content)} items\n"
            if len(content) > 0 and isinstance(content[0], dict):
                example = content[0]
                example_str = ", ".join([f"{k}: {v}" for k, v in example.items() if v])
                summary += f"  Example: {example_str}\n"
        elif isinstance(content, dict):
            for key, value in content.items():
                summary += f"  {key.replace('_', ' ').title()}: {value}\n"
        else:
            summary += f"  {content}\n"
        
        summary += "\n"
    
    return summary

def generate_visualization_data(data):
    """
    Generate data structures suitable for visualization from collected data
    
    Args:
        data (dict): Collected data from agents
        
    Returns:
        dict: Visualization-ready data structures
    """
    viz_data = {}
    
    for section, content in data.items():
        if not content:
            continue
            
        if "market" in section.lower() and isinstance(content, dict):
            # Market data visualization
            if "competitors" in content:
                viz_data["market_competitors"] = {
                    "labels": [c["name"] for c in content["competitors"]],
                    "values": [float(c["market_share"].replace('%', '')) for c in content["competitors"]]
                }
            
        elif "trial" in section.lower() and isinstance(content, list):
            # Trial data visualization
            phases = {}
            for trial in content:
                if isinstance(trial, dict) and "phase" in trial:
                    phase = trial["phase"]
                    phases[phase] = phases.get(phase, 0) + 1
                    
            if phases:
                viz_data["trial_phases"] = {
                    "labels": list(phases.keys()),
                    "values": list(phases.values())
                }
                
        elif "patent" in section.lower() and isinstance(content, list):
            # Patent data visualization
            assignees = {}
            for patent in content:
                if isinstance(patent, dict) and "assignee" in patent:
                    assignee = patent["assignee"]
                    assignees[assignee] = assignees.get(assignee, 0) + 1
                    
            if assignees:
                # Top 5 assignees
                sorted_assignees = sorted(assignees.items(), key=lambda x: x[1], reverse=True)[:5]
                viz_data["patent_assignees"] = {
                    "labels": [a[0] for a in sorted_assignees],
                    "values": [a[1] for a in sorted_assignees]
                }
    
    return viz_data

def _synthesize_with_gemini(query, data, api_key):
    """
    Synthesize a report using Google Gemini API
    
    Args:
        query (str): Original query
        data (dict): Collected data
        api_key (str): Gemini API key
        
    Returns:
        str: Gemini-generated report
    """
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Create the model
        model = genai.GenerativeModel('gemini-pro')
        
        # Create a prompt for Gemini
        prompt = f"""
        Act as a pharmaceutical research analyst. Create a comprehensive pharmaceutical research report 
        based on the following data.
        
        Query: {query}
        
        Data:
        {json.dumps(data, indent=2)}
        
        Please provide a detailed report with:
        1. An executive summary (2-3 paragraphs)
        2. Key findings for each data category with specific insights
        3. Strategic insights and actionable recommendations
        4. Future research directions and opportunities
        5. Risk factors and mitigation strategies
        
        Format the response as a professional pharmaceutical research report with clear headings and 
        structured content. Use technical language appropriate for pharmaceutical researchers and 
        industry professionals. Include specific numbers and data points from the provided data where 
        relevant.
        """
        
        # Generate content
        response = model.generate_content(prompt)
        
        # Return the generated text
        if response and response.text:
            return response.text
        else:
            # Fallback if Gemini didn't return content
            return _generate_mock_llm_response(query, data)
            
    except Exception as e:
        print(f"Error using Gemini API: {str(e)}")
        # Fallback to mock response if Gemini fails
        return _generate_mock_llm_response(query, data)

# Example usage:
# report = synthesize_report_with_llm("diabetes treatment", sample_data)
# viz_data = generate_visualization_data(sample_data)