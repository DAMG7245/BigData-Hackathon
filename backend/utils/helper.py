# backend/utils/helpers.py
import logging
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format sources for consistent citation in research reports.
    
    Args:
        sources: Raw sources from various agents
        
    Returns:
        Formatted list of sources
    """
    formatted_sources = []
    
    for source in sources:
        # Handle case law sources from RAG agent
        if "case_name" in source:
            formatted_sources.append({
                "type": "case_law",
                "case_name": source.get("case_name", "Unknown case"),
                "citation": source.get("citation", ""),
                "year": source.get("year", ""),
                "url": "",  # Usually not available for historical cases
                "source": source.get("source", "Massachusetts Reports")
            })
        # Handle web sources from WebSearch agent
        elif "url" in source:
            formatted_sources.append({
                "type": "web",
                "title": source.get("title", "Untitled"),
                "url": source.get("url", ""),
                "published_date": source.get("published_date", ""),
                "source": "Web Search"
            })
    
    return formatted_sources

def create_research_prompt() -> str:
    """
    Create the MCP prompt template for legal research.
    
    Returns:
        Prompt template string
    """
    return """
    # Legal Research Assistant
    
    I'll help you conduct comprehensive legal research on Massachusetts law topics, combining historical case law with current legal information.
    
    ## Available Tools
    
    - `conduct_research`: Conduct legal research on a specific topic
      - Parameters:
        - `query`: The legal question or research topic
        - `format`: Output format (markdown, json, html)
        - `length`: Research depth (brief, standard, comprehensive)
        - `agents`: Research sources to use (legal_rag, websearch)
        - `year_start`: Optional starting year for case filtering
        - `year_end`: Optional ending year for case filtering
    
    - `check_research_status`: Check the status of an ongoing research
      - Parameters:
        - `research_id`: ID of the research request
    
    - `get_research_sources`: Get sources used in the research
      - Parameters:
        - `research_id`: ID of the research request
    
    ## Examples
    
    To conduct research on a legal topic:
    ```
    I need research on adverse possession requirements in Massachusetts
    ```
    
    To specify research parameters:
    ```
    Can you conduct comprehensive research on eminent domain case law in Massachusetts between 1990 and 2010?
    ```
    
    To check research status:
    ```
    Can you check the status of my research with ID research_12345?
    ```
    """

def extract_legal_principles(content: str) -> List[str]:
    """
    Extract key legal principles from content.
    
    Args:
        content: Legal research content
        
    Returns:
        List of identified legal principles
    """
    # In a real implementation, this might use more sophisticated NLP
    # For now, just look for common patterns in legal writing
    principles = []
    
    # Look for sentences that likely state a principle
    lines = content.split('\n')
    for line in lines:
        if "principle" in line.lower() or "rule" in line.lower() or "doctrine" in line.lower():
            principles.append(line.strip())
        elif "court held" in line.lower() or "court ruled" in line.lower():
            principles.append(line.strip())
        elif "standard" in line.lower() and "established" in line.lower():
            principles.append(line.strip())
    
    return principles

def format_legal_citation(case_name: str, citation: str, year: str) -> str:
    """
    Format a legal citation properly.
    
    Args:
        case_name: Name of the case
        citation: Raw citation string
        year: Year of the decision
        
    Returns:
        Properly formatted citation
    """
    # Basic citation formatting
    if case_name and citation and year:
        return f"{case_name}, {citation} ({year})"
    elif case_name and year:
        return f"{case_name} ({year})"
    elif case_name:
        return case_name
    else:
        return "Unknown case"

def validate_research_query(query: str) -> Dict[str, Any]:
    """
    Validate and enhance a research query.
    
    Args:
        query: Original query string
        
    Returns:
        Dictionary with validation results and enhancement suggestions
    """
    results = {
        "valid": True,
        "enhancements": [],
        "warnings": []
    }
    
    # Check query length
    if len(query) < 10:
        results["valid"] = False
        results["warnings"].append("Query is too short")
    
    # Check if query contains legal terminology
    legal_terms = ["law", "case", "statute", "regulation", "court", "decision", 
                  "plaintiff", "defendant", "appeal", "tort", "contract", 
                  "property", "liability", "rights", "judge", "jury", "verdict"]
    
    has_legal_term = any(term in query.lower() for term in legal_terms)
    if not has_legal_term:
        results["enhancements"].append(
            "Consider adding specific legal terminology to focus your search"
        )
    
    # Check if Massachusetts is explicitly mentioned
    if "massachusetts" not in query.lower() and "mass" not in query.lower():
        results["enhancements"].append(
            "Consider explicitly mentioning Massachusetts to focus on relevant jurisdiction"
        )
    
    return results