# backend/server.py
import os
import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import our agents
from agents.legal_rag_agent import LegalRagAgent
from agents.websearch_agent import WebSearchAgent
from agents.synthesis_agent import SynthesisAgent
from utils.helper import format_sources, create_research_prompt

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Mass Legal Research Assistant API for MCP")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents
legal_rag_agent = LegalRagAgent()
websearch_agent = WebSearchAgent()
synthesis_agent = SynthesisAgent()

# In-memory research store
research_store = {}

# Pydantic models for validation
class ResearchRequest(BaseModel):
    query: str
    format: str = "markdown"
    length: str = "comprehensive"
    agents: List[str] = ["legal_rag", "websearch"]
    year_start: Optional[int] = None
    year_end: Optional[int] = None

class ResearchResponse(BaseModel):
    id: str
    status: str
    content: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

# Endpoint for starting a new research request
@app.post("/research")
async def start_research(request: ResearchRequest):
    """
    Start a new legal research request.
    """
    try:
        logger.info(f"Starting research on: {request.query}")
        research_id = f"research_{uuid.uuid4().hex}"
        
        # Store initial research state
        research_store[research_id] = {
            "id": research_id,
            "query": request.query,
            "status": "in_progress",
            "format": request.format,
            "length": request.length,
            "agents": request.agents,
            "year_range": {"start": request.year_start, "end": request.year_end},
            "started_at": time.time(),
            "content": None,
            "sources": [],
            "error": None,
        }
        
        # Track results from each agent
        agent_results = {}
        
        # Run Legal RAG agent if requested
        if "legal_rag" in request.agents:
            logger.info("Running legal RAG agent")
            try:
                rag_results = legal_rag_agent.query(
                    request.query, 
                    year_start=request.year_start, 
                    year_end=request.year_end
                )
                agent_results["legal_rag"] = rag_results
            except Exception as e:
                logger.error(f"Error in legal RAG agent: {str(e)}")
                agent_results["legal_rag"] = {
                    "error": str(e),
                    "content": "Error retrieving from legal database",
                    "sources": []
                }
        
        # Run WebSearch agent if requested
        if "websearch" in request.agents:
            logger.info("Running websearch agent")
            try:
                websearch_results = websearch_agent.query(request.query)
                agent_results["websearch"] = websearch_results
            except Exception as e:
                logger.error(f"Error in websearch agent: {str(e)}")
                agent_results["websearch"] = {
                    "error": str(e),
                    "content": "Error retrieving from web sources",
                    "sources": []
                }
        
        # Synthesize results
        try:
            logger.info("Synthesizing research results")
            synthesis_result = synthesis_agent.synthesize(
                query=request.query,
                agent_results=agent_results,
                format=request.format,
                length=request.length
            )
            
            # Update research store
            research_store[research_id].update({
                "status": "completed",
                "content": synthesis_result.get("content", "No content generated"),
                "sources": synthesis_result.get("sources", []),
                "completed_at": time.time(),
            })
            
            # Return research output
            return {
                "id": research_id,
                "status": "completed",
                "content": synthesis_result.get("content", "No content generated"),
                "sources": synthesis_result.get("sources", []),
            }
            
        except Exception as e:
            logger.error(f"Error in synthesis: {str(e)}")
            research_store[research_id].update({
                "status": "failed",
                "error": f"Error in synthesis: {str(e)}",
                "completed_at": time.time(),
            })
            return {
                "id": research_id,
                "status": "failed",
                "error": f"Error in synthesis: {str(e)}",
            }
            
    except Exception as e:
        logger.error(f"Error in research process: {str(e)}")
        return {
            "id": research_id if 'research_id' in locals() else f"research_{uuid.uuid4().hex}",
            "status": "failed",
            "error": f"Error in research process: {str(e)}",
        }

# Endpoint for checking research status
@app.get("/research/{research_id}")
async def check_research_status(research_id: str):
    """
    Check the status of a research request.
    """
    if research_id not in research_store:
        raise HTTPException(status_code=404, detail=f"Research ID {research_id} not found")
    
    return research_store[research_id]

# Endpoint for listing all research
@app.get("/research")
async def list_research():
    """
    List all research requests.
    """
    result = []
    for research_id, research in research_store.items():
        result.append({
            "id": research_id,
            "query": research.get("query", ""),
            "status": research.get("status", ""),
            "started_at": research.get("started_at", 0),
            "completed_at": research.get("completed_at", None)
        })
    
    return result

# Endpoint for retrieving research sources
@app.get("/research/{research_id}/sources")
async def get_research_sources(research_id: str):
    """
    Get the sources used in a research.
    """
    if research_id not in research_store:
        raise HTTPException(status_code=404, detail=f"Research ID {research_id} not found")
    
    research = research_store[research_id]
    return {
        "id": research_id,
        "status": research.get("status", ""),
        "sources": research.get("sources", []),
    }

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Main app entrypoint
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)