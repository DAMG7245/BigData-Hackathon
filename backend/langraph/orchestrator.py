# backend/langraph/orchestrator.py
from typing import Dict, Any, List, Optional
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import os
import logging
import time

# Import our specialized agents
from agents.legal_rag_agent import LegalRagAgent
from agents.websearch_agent import WebSearchAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LegalResearchOrchestrator:
    def __init__(self, use_legal_rag: bool = True, use_websearch: bool = True):
        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
            
        # Initialize LLM for synthesis
        self.llm = ChatOpenAI(
            temperature=0, 
            model="gpt-4",
            api_key=api_key
        )
        
        # Initialize specialized legal agents
        self.legal_rag_agent = LegalRagAgent() if use_legal_rag else None
        self.websearch_agent = WebSearchAgent() if use_websearch else None
        
        # Track which agents are active
        self.active_agents = []
        if use_legal_rag:
            self.active_agents.append("legal_rag")
        if use_websearch:
            self.active_agents.append("websearch")
        
        logger.info(f"Initialized legal research orchestrator with agents: {self.active_agents}")
        
    def run(self, 
            query: str, 
            year_start: Optional[int] = None, 
            year_end: Optional[int] = None,
            format: str = "markdown",
            length: str = "comprehensive") -> Dict[str, Any]:
        """
        Run the legal research orchestrator to generate a comprehensive report.
        
        Args:
            query: The legal research question
            year_start: Optional starting year filter for case law
            year_end: Optional ending year filter for case law
            format: Output format (markdown, html)
            length: Desired length/detail level of report
            
        Returns:
            Dictionary with the final research report
        """
        logger.info(f"Running legal research orchestrator with query: {query}, year range: {year_start}-{year_end}")
        
        research_id = f"research_{int(time.time())}"
        results = {}
        content = {}
        all_sources = []
        
        # Process with Legal RAG agent if enabled
        if "legal_rag" in self.active_agents:
            logger.info("Processing with Legal RAG agent")
            try:
                rag_results = self.legal_rag_agent.query(query, year_start, year_end)
                results["case_law"] = {
                    "content": rag_results.get("response", "No relevant case law available"),
                    "sources": rag_results.get("sources", [])
                }
                content["case_law"] = rag_results.get("response", "No relevant case law available")
                all_sources.extend(rag_results.get("sources", []))
            except Exception as e:
                logger.error(f"Error in Legal RAG agent: {str(e)}", exc_info=True)
                results["case_law"] = {
                    "content": f"Error retrieving case law: {str(e)}",
                    "sources": []
                }
                content["case_law"] = f"Error retrieving case law: {str(e)}"
        
        # Process with WebSearch agent if enabled
        if "websearch" in self.active_agents:
            logger.info("Processing with WebSearch agent")
            try:
                websearch_results = self.websearch_agent.query(query)
                results["legal_commentary"] = {
                    "content": websearch_results.get("response", "No recent legal commentary available"),
                    "sources": websearch_results.get("sources", [])
                }
                content["legal_commentary"] = websearch_results.get("response", "No recent legal commentary available")
                all_sources.extend(websearch_results.get("sources", []))
            except Exception as e:
                logger.error(f"Error in WebSearch agent: {str(e)}", exc_info=True)
                results["legal_commentary"] = {
                    "content": f"Error retrieving legal commentary: {str(e)}",
                    "sources": []
                }
                content["legal_commentary"] = f"Error retrieving legal commentary: {str(e)}"
        
        # Determine length parameters for synthesis
        if length == "brief":
            max_pages = "5-7"
            detail_level = "concise overview of key points"
        elif length == "standard":
            max_pages = "10-15"
            detail_level = "balanced analysis with moderate detail"
        else:  # comprehensive
            max_pages = "20-30"
            detail_level = "in-depth analysis with thorough examination of legal principles"
            
        # Synthesize the final report if we have multiple sections
        final_response = ""
        if len(self.active_agents) > 1:
            try:
                # Create prompt for synthesis
                prompt = ChatPromptTemplate.from_messages([
                    ("system", f"""
                    You are a specialized legal research assistant creating formal legal research reports.
                    
                    Your task is to synthesize historical Massachusetts case law with recent legal commentary
                    to produce a comprehensive {max_pages} page legal research report.
                    
                    Follow these guidelines:
                    1. Write in formal legal style with proper citations
                    2. Create a {detail_level}
                    3. Organize by legal principles and precedents
                    4. Include both historical context and current interpretations
                    5. Format as a professional legal research memorandum
                    6. Include executive summary, table of contents, methodology, analysis, and conclusion sections
                    7. Use proper legal citation format
                    8. Add footnotes for important references
                    
                    Output format: {format}
                    Output length: {max_pages} pages
                    """),
                    ("human", """
                    LEGAL QUERY:
                    {query}
                    
                    HISTORICAL CASE LAW:
                    {case_law}
                    
                    RECENT LEGAL COMMENTARY:
                    {legal_commentary}
                    """)
                ])
                
                # Generate synthesis
                logger.info("Generating legal research synthesis")
                chain = prompt | self.llm
                response = chain.invoke({
                    "query": query,
                    "case_law": content.get("case_law", "Not available"),
                    "legal_commentary": content.get("legal_commentary", "Not available")
                })
                
                final_response = response.content
                
            except Exception as e:
                logger.error(f"Error in synthesis: {str(e)}", exc_info=True)
                final_response = f"Error generating legal research synthesis: {str(e)}"
        else:
            # If only one agent is active, use its response as the final report
            if "legal_rag" in self.active_agents:
                final_response = content.get("case_law", "")
            elif "websearch" in self.active_agents:
                final_response = content.get("legal_commentary", "")
        
        # Create final report
        final_report = {
            "id": research_id,
            "query": query,
            "content": final_response,
            "sources": all_sources,
            "components": results,
            "metadata": {
                "year_range": {
                    "start": year_start,
                    "end": year_end
                },
                "format": format,
                "length": length,
                "agents_used": self.active_agents
            }
        }
        
        return final_report