# backend/server.py
#mcp
import os
import logging
import uuid
import time
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import MCP library
from mcp.server.fastmcp import FastMCP, Image

# Import our agents
from agents.legal_rag_agent import LegalRagAgent
from agents.websearch_agent import WebSearchAgent
from agents.synthesis_agent import SynthesisAgent
from utils.helper import format_sources, create_research_prompt, validate_research_query

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a FastAPI app that will be exposed to uvicorn
app = FastAPI(title="Mass Legal Research API")

# Initialize the FastMCP server
mcp_server = FastMCP("Mass Legal Research Assistant")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the MCP SSE server to the FastAPI app
app.mount("/mcp", mcp_server.sse_app())

# Initialize agents
legal_rag_agent = LegalRagAgent()
websearch_agent = WebSearchAgent()
synthesis_agent = SynthesisAgent()

# In-memory research store (unified for both REST API and MCP)
research_store = {}

# Pydantic models for REST API
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

# REST API ENDPOINTS
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
        research_store[research_id] = {
            "research_id": research_id,
            "id": research_id,  # Add this for MCP compatibility
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
            conduct_research_task,
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
    if research_id not in research_store:
        raise HTTPException(status_code=404, detail=f"Research ID {research_id} not found")
    
    research = research_store[research_id]
    return {
        "research_id": research_id,
        "query": research.get("query", ""),
        "status": research.get("status", ""),
        "content": research.get("content"),
        "sources": research.get("sources", []),
        "metadata": research.get("metadata", {}),
        "started_at": research.get("started_at", 0),
        "completed_at": research.get("completed_at"),
        "error": research.get("error")
    }

@app.get("/research")
async def list_research():
    """
    List all research requests.
    """
    result = []
    for research_id, research in research_store.items():
        result.append({
            "research_id": research_id,
            "query": research.get("query", ""),
            "status": research.get("status", ""),
            "started_at": research.get("started_at", 0),
            "completed_at": research.get("completed_at")
        })
    
    return result

@app.delete("/research/{research_id}")
async def delete_research(research_id: str):
    """
    Delete a research request.
    """
    if research_id not in research_store:
        raise HTTPException(status_code=404, detail=f"Research ID {research_id} not found")
    
    del research_store[research_id]
    return {"status": "deleted", "research_id": research_id}

# MCP TOOLS AND RESOURCES
@mcp_server.tool()
async def conduct_research(
    query: str,
    format: str = "markdown",
    length: str = "comprehensive",
    agents: List[str] = ["legal_rag", "websearch"],
    year_start: Optional[int] = None,
    year_end: Optional[int] = None
) -> Dict[str, Any]:
    """
    Conduct legal research on a specific topic.
    
    Args:
        query: The legal question or research topic
        format: Output format (markdown, json, html)
        length: Research depth (brief, standard, comprehensive)
        agents: Research sources to use (legal_rag, websearch)
        year_start: Optional starting year for case filtering
        year_end: Optional ending year for case filtering
        
    Returns:
        Research results with content and sources
    """
    research_id = f"research_{uuid.uuid4().hex}"
    
    # Report start of process
    logger.info(f"Starting research on: {query}")
    
    # Store initial research state
    research_store[research_id] = {
        "id": research_id,
        "research_id": research_id,  # Add this for REST API compatibility
        "query": query,
        "status": "in_progress",
        "format": format,
        "length": length,
        "agents": agents,
        "year_range": {"start": year_start, "end": year_end},
        "started_at": time.time(),
        "content": None,
        "sources": [],
        "error": None,
    }
    
    try:
        # Perform research using common implementation
        agent_results = await perform_research(
            query, 
            agents, 
            year_start, 
            year_end
        )
        
        # Synthesize results
        logger.info("Synthesizing research results")
        synthesis_result = synthesis_agent.synthesize(
            query=query,
            agent_results=agent_results,
            format=format,
            length=length
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
            "research_id": research_id,
            "status": "completed",
            "content": synthesis_result.get("content", "No content generated"),
            "sources": synthesis_result.get("sources", []),
        }
            
    except Exception as e:
        logger.error(f"Error in research process: {str(e)}")
        research_store[research_id].update({
            "status": "failed",
            "error": f"Error in research process: {str(e)}",
            "completed_at": time.time(),
        })
        
        return {
            "research_id": research_id,
            "status": "failed",
            "error": str(e)
        }

@mcp_server.tool()
def check_research_status(research_id: str) -> Dict[str, Any]:
    """
    Check the status of an ongoing research.
    
    Args:
        research_id: ID of the research request
        
    Returns:
        Current status and metadata of the research
    """
    if research_id not in research_store:
        raise ValueError(f"Research ID {research_id} not found")
    
    research = research_store[research_id]
    return {
        "research_id": research_id,
        "status": research.get("status", "unknown"),
        "query": research.get("query", ""),
        "started_at": research.get("started_at", 0),
        "completed_at": research.get("completed_at", None)
    }

@mcp_server.tool()
def get_research_sources(research_id: str) -> Dict[str, Any]:
    """
    Get sources used in the research.
    
    Args:
        research_id: ID of the research request
        
    Returns:
        Sources used in the research
    """
    if research_id not in research_store:
        raise ValueError(f"Research ID {research_id} not found")
    
    research = research_store[research_id]
    return {
        "research_id": research_id,
        "sources": research.get("sources", [])
    }

@mcp_server.resource("research://{topic}")
async def research_resource(topic: str) -> str:
    """
    Access research on a specific legal topic.
    
    Args:
        topic: The legal topic to research
        
    Returns:
        Research report on the topic
    """
    # Call the conduct_research tool
    result = await conduct_research(
        query=topic,
        format="markdown",
        length="comprehensive",
        agents=["legal_rag", "websearch"]
    )
    
    # Return the content
    return result.get("content", "No research content available")

@mcp_server.resource("report://{research_id}")
def research_report_resource(research_id: str) -> str:
    """
    Access a completed research report by ID.
    
    Args:
        research_id: ID of the research request
        
    Returns:
        Completed research report
    """
    if research_id not in research_store:
        return f"Research ID {research_id} not found"
    
    research = research_store[research_id]
    
    if research.get("status") != "completed":
        return f"Research is not completed. Current status: {research.get('status')}"
    
    return research.get("content", "No content available")

@mcp_server.prompt()
def legal_research_prompt() -> str:
    """
    Prompt template for legal research.
    """
    return create_research_prompt()

# SHARED FUNCTIONS
async def perform_research(
    query: str,
    agents: List[str],
    year_start: Optional[int] = None,
    year_end: Optional[int] = None
) -> Dict[str, Any]:
    """
    Perform research across specified agents.
    
    Args:
        query: The research query
        agents: List of agents to use
        year_start: Optional start year filter
        year_end: Optional end year filter
        
    Returns:
        Dictionary mapping agent names to their results
    """
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
                "content": "Error retrieving from legal database",
                "response": "Error retrieving from legal database",  # For backward compatibility
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
                "content": "Error retrieving from web sources",
                "response": "Error retrieving from web sources",  # For backward compatibility
                "sources": []
            }
    
    return agent_results

# Background task for REST API
async def conduct_research_task(
    research_id: str,
    query: str,
    format: str,
    length: str,
    agents: List[str],
    year_start: Optional[int],
    year_end: Optional[int]
):
    """
    Conduct research as a background task for the REST API.
    """
    try:
        # Update status to in progress
        research_store[research_id]["status"] = "in_progress"
        
        # Perform research using common implementation
        agent_results = await perform_research(
            query, 
            agents, 
            year_start, 
            year_end
        )
        
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
            research_store[research_id].update({
                "status": "completed",
                "content": synthesis_result.get("content", "No content generated"),
                "sources": sources,
                "completed_at": time.time(),
            })
            
        except Exception as e:
            logger.error(f"Error in synthesis: {str(e)}")
            research_store[research_id].update({
                "status": "failed",
                "error": f"Error in synthesis: {str(e)}",
                "completed_at": time.time(),
            })
            
    except Exception as e:
        logger.error(f"Error in research process: {str(e)}")
        research_store[research_id].update({
            "status": "failed",
            "error": f"Error in research process: {str(e)}",
            "completed_at": time.time(),
        })

# Run the server if called directly
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)