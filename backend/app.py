# backend/app.py
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import logging
import uuid
import time
from dotenv import load_dotenv

# Local imports
from agents.legal_rag_agent import LegalRagAgent
from agents.websearch_agent import WebSearchAgent
from agents.synthesis_agent import SynthesisAgent
from utils.helper import format_sources, validate_research_query

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Mass Legal Research Assistant API")

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

# In-memory store for research results
research_results = {}

# Pydantic models
class ResearchQuery(BaseModel):
    query: str
    format: str = "markdown"
    length: str = "comprehensive"  # brief, standard, comprehensive
    agents: List[str] = ["legal_rag", "websearch"]
    year_start: Optional[int] = None
    year_end: Optional[int] = None

class ResearchResponse(BaseModel):
    research_id: str
    status: str
    message: str

class ResearchResult(BaseModel):
    research_id: str
    query: str
    status: str
    content: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = {}
    started_at: float
    completed_at: Optional[float] = None
    error: Optional[str] = None

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/research", response_model=ResearchResponse)
async def start_research(request: ResearchQuery, background_tasks: BackgroundTasks):
    """
    Start a new research request.
    
    The research will run asynchronously in the background.
    """
    try:
        # Validate query
        validation = validate_research_query(request.query)
        if not validation["valid"]:
            warnings = ", ".join(validation["warnings"])
            raise HTTPException(status_code=400, detail=f"Invalid query: {warnings}")
        
        # Generate a unique research ID
        research_id = f"research_{uuid.uuid4().hex}"
        
        # Store initial research state
        research_results[research_id] = {
            "research_id": research_id,
            "query": request.query,
            "status": "pending",
            "content": None,
            "sources": [],
            "metadata": {
                "format": request.format,
                "length": request.length,
                "agents": request.agents,
                "year_range": {
                    "start": request.year_start,
                    "end": request.year_end
                },
                "validation": validation
            },
            "started_at": time.time(),
            "completed_at": None,
            "error": None
        }
        
        # Start background task for research
        background_tasks.add_task(
            conduct_research,
            research_id,
            request.query,
            request.format,
            request.length,
            request.agents,
            request.year_start,
            request.year_end
        )
        
        # Return immediate response with research ID
        return {
            "research_id": research_id,
            "status": "pending",
            "message": "Research started. Use /research/{research_id} to check status."
        }
        
    except Exception as e:
        logger.error(f"Error starting research: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/research/{research_id}", response_model=ResearchResult)
async def get_research_results(research_id: str):
    """
    Get results for a specific research request.
    """
    if research_id not in research_results:
        raise HTTPException(status_code=404, detail=f"Research ID {research_id} not found")
    
    return research_results[research_id]

@app.get("/research")
async def list_research():
    """
    List all research requests.
    """
    result = []
    for research_id, research in research_results.items():
        result.append({
            "research_id": research_id,
            "query": research["query"],
            "status": research["status"],
            "started_at": research["started_at"],
            "completed_at": research["completed_at"]
        })
    
    return result

@app.delete("/research/{research_id}")
async def delete_research(research_id: str):
    """
    Delete a research request.
    """
    if research_id not in research_results:
        raise HTTPException(status_code=404, detail=f"Research ID {research_id} not found")
    
    del research_results[research_id]
    return {"status": "deleted", "research_id": research_id}

# Background function for conducting research
async def conduct_research(
    research_id: str,
    query: str,
    format: str,
    length: str,
    agents: List[str],
    year_start: Optional[int],
    year_end: Optional[int]
):
    """
    Conduct research as a background task.
    """
    try:
        # Update status to in progress
        research_results[research_id]["status"] = "in_progress"
        
        # Track results from each agent
        agent_results = {}
        
        # Run Legal RAG agent if requested
        if "legal_rag" in agents:
            logger.info(f"Running legal RAG agent for query: {query}")
            try:
                rag_results = legal_rag_agent.query(
                    query, 
                    year_start=year_start, 
                    year_end=year_end
                )
                agent_results["legal_rag"] = rag_results
            except Exception as e:
                logger.error(f"Error in legal RAG agent: {str(e)}")
                agent_results["legal_rag"] = {
                    "error": str(e),
                    "response": "Error retrieving from legal database",
                    "sources": []
                }
        
        # Run WebSearch agent if requested
        if "websearch" in agents:
            logger.info(f"Running websearch agent for query: {query}")
            try:
                websearch_results = websearch_agent.query(query)
                agent_results["websearch"] = websearch_results
            except Exception as e:
                logger.error(f"Error in websearch agent: {str(e)}")
                agent_results["websearch"] = {
                    "error": str(e),
                    "response": "Error retrieving from web sources",
                    "sources": []
                }
        
        # Synthesize results
        try:
            logger.info(f"Synthesizing research results for query: {query}")
            synthesis_result = synthesis_agent.synthesize(
                query=query,
                agent_results=agent_results,
                format=format,
                length=length
            )
            
            # Format sources for consistency
            sources = format_sources(synthesis_result.get("sources", []))
            
            # Update research results
            research_results[research_id].update({
                "status": "completed",
                "content": synthesis_result.get("content", "No content generated"),
                "sources": sources,
                "completed_at": time.time(),
            })
            
        except Exception as e:
            logger.error(f"Error in synthesis: {str(e)}")
            research_results[research_id].update({
                "status": "failed",
                "error": f"Error in synthesis: {str(e)}",
                "completed_at": time.time(),
            })
            
    except Exception as e:
        logger.error(f"Error in research process: {str(e)}")
        research_results[research_id].update({
            "status": "failed",
            "error": f"Error in research process: {str(e)}",
            "completed_at": time.time(),
        })

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)