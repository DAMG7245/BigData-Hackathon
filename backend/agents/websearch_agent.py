# backend/agents/websearch_agent.py
import os
import logging
from typing import Dict, Any, List, Optional
from tavily import TavilyClient
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSearchAgent:
    def __init__(self):
        # Initialize with Tavily API
        self.api_key = os.getenv("TAVILY_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = TavilyClient(api_key=self.api_key)
        self.llm = ChatOpenAI(
            temperature=0, 
            model="gpt-4",
            api_key=openai_api_key
        )
        
    def query(self, query_text: str) -> Dict[str, Any]:
        """
        Query Tavily API for latest legal information related to the query.
        
        Args:
            query_text: The legal query text
            
        Returns:
            Dictionary with search results and synthesized information
        """
        try:
            # Augment query to focus on legal information and recent commentary
            augmented_query = f"Massachusetts legal cases {query_text} recent interpretation court decisions"
            
            logger.info(f"Web searching for: {augmented_query}")
            
            # Execute search with Tavily
            response = self.client.search(
                query=augmented_query,
                search_depth="advanced",
                max_results=7,
                include_domains=[
                    "law.cornell.edu", 
                    "justia.com", 
                    "findlaw.com", 
                    "caselaw.findlaw.com",
                    "mass.gov",
                    "masslegalservices.org",
                    "masslawyersweekly.com",
                    "scholar.google.com",
                    "courtlistener.com"
                ]
            )
            
            # Extract results
            search_results = response.get("results", [])
            
            # Format results
            formatted_results = []
            for result in search_results:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0),
                    "published_date": result.get("published_date", "")
                })
            
            # Generate insights from the search results
            insights = self._generate_insights(formatted_results, query_text)
            
            # Extract sources for citation
            sources = []
            for result in formatted_results:
                sources.append({
                    "title": result["title"],
                    "url": result["url"],
                    "published_date": result["published_date"]
                })
            
            # Return results
            return {
                "results": formatted_results,
                "response": insights,
                "sources": sources
            }
        except Exception as e:
            logger.error(f"Error in web search agent: {str(e)}", exc_info=True)
            return {
                "results": [],
                "response": f"Error retrieving web information: {str(e)}",
                "sources": []
            }
        
    def _generate_insights(self, results: List[Dict[str, Any]], query_text: str) -> str:
        """Generate insights from search results"""
        try:
            # Format results for the prompt
            context = ""
            for i, result in enumerate(results, 1):
                context += f"{i}. Title: {result['title']}\n"
                context += f"   URL: {result['url']}\n"
                context += f"   Published Date: {result['published_date']}\n"
                # Include only a brief snippet of content to avoid copyright issues
                content_snippet = result['content'][:300] + "..." if len(result['content']) > 300 else result['content']
                context += f"   Content Snippet: {content_snippet}\n\n"
            
            # Create prompt for insights
            prompt = ChatPromptTemplate.from_messages([
                ("system", """
                You are a legal research analyst specializing in Massachusetts law.
                Analyze the following recent legal information to answer the query.
                Focus on extracting the most relevant and recent legal insights.
                Provide a balanced perspective considering multiple sources.
                Use formal legal writing style.
                
                IMPORTANT: Reference legal sources properly with standard legal citations.
                Organize your analysis by legal principles and trends.
                Include relevant statutes, regulations, and case law if mentioned in the sources.
                """),
                ("human", "Recent legal information:\n{context}\n\nLegal Query: {query}")
            ])
            
            # Generate insights
            chain = prompt | self.llm
            response = chain.invoke({
                "context": context,
                "query": query_text
            })
            
            return response.content
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}", exc_info=True)
            return f"Error generating insights from web search: {str(e)}"