# backend/agents/synthesis_agent.py
import os
import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SynthesisAgent:
    def __init__(self):
        # Initialize with OpenAI
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.llm = ChatOpenAI(
            temperature=0, 
            model="gpt-4",
            api_key=openai_api_key
        )
    
    def synthesize(self, query: str, agent_results: Dict[str, Any], format: str = "markdown", length: str = "comprehensive") -> Dict[str, Any]:
        """
        Synthesize results from multiple agents into a coherent legal research report.
        
        Args:
            query: The original query
            agent_results: Results from each agent
            format: Output format (markdown, json, html)
            length: Desired length/detail level of report
            
        Returns:
            Synthesized report with content and sources
        """
        try:
            logger.info(f"Synthesizing results for query: {query}")
            
            # Extract content from each agent
            historical_content = ""
            web_content = ""
            all_sources = []
            
            # Process legal RAG agent results
            if "legal_rag" in agent_results:
                rag_results = agent_results["legal_rag"]
                historical_content = rag_results.get("response", "")
                if "sources" in rag_results:
                    all_sources.extend(rag_results["sources"])
            
            # Process web search agent results
            if "websearch" in agent_results:
                web_results = agent_results["websearch"]
                web_content = web_results.get("response", "")
                if "sources" in web_results:
                    all_sources.extend(web_results["sources"])
            
            # Determine length parameters
            if length == "brief":
                max_pages = "5-7"
                detail_level = "concise overview of key points"
            elif length == "standard":
                max_pages = "10-15"
                detail_level = "balanced analysis with moderate detail"
            else:  # comprehensive
                max_pages = "20-30"
                detail_level = "in-depth analysis with thorough examination of legal principles"
            
            # Create appropriate template based on format
            system_template = f"""
            You are a specialized legal research assistant creating formal legal research reports.
            
            Your task is to synthesize historical Massachusetts case law with recent legal commentary and web information
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
            """
            
            human_template = """
            LEGAL QUERY:
            {query}
            
            HISTORICAL CASE LAW INFORMATION:
            {historical_content}
            
            RECENT LEGAL COMMENTARY AND WEB INFORMATION:
            {web_content}
            """
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_template),
                ("human", human_template)
            ])
            
            # Generate synthesis
            logger.info("Generating synthesis using LLM")
            chain = prompt | self.llm
            response = chain.invoke({
                "query": query,
                "historical_content": historical_content,
                "web_content": web_content
            })
            
            logger.info("Synthesis generated successfully")
            
            # Return synthesized report
            return {
                "content": response.content,
                "sources": all_sources
            }
            
        except Exception as e:
            logger.error(f"Error in synthesis: {str(e)}", exc_info=True)
            return {
                "content": f"Error synthesizing research report: {str(e)}",
                "sources": []
            }