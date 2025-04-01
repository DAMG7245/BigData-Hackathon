# backend/agents/legal_rag_agent.py
import os
import logging
from typing import Dict, Any, List, Optional
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LegalRagAgent:
    def __init__(self):
        # Initialize Pinecone client
        api_key = os.getenv("PINECONE_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Create Pinecone instance (new API)
        self.pc = Pinecone(api_key=api_key)
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "mass-reports")
        
        # Use OpenAI embeddings
        self.embedding_model = OpenAIEmbeddings(
            model="text-embedding-3-large",
            openai_api_key=openai_api_key
        )
        self.llm = ChatOpenAI(
            temperature=0, 
            model="gpt-4",
            api_key=openai_api_key
        )
        
        # Log available indexes for debugging
        logger.info(f"Available Pinecone indexes: {self.pc.list_indexes().names()}")
        
    def query(self, query_text: str, year_start: Optional[int] = None, year_end: Optional[int] = None) -> Dict[str, Any]:
        """
        Query the RAG system with optional metadata filtering by year range.
        
        Args:
            query_text: The query text
            year_start: Optional starting year filter
            year_end: Optional ending year filter
            
        Returns:
            Dictionary with retrieved context and generated response
        """
        try:
            # Log query parameters
            logger.info(f"Legal RAG Query: '{query_text}', Year range: {year_start} - {year_end}")
            
            # Generate embedding for the query using OpenAI
            query_embedding = self.embedding_model.embed_query(query_text)
            
            # Prepare metadata filter for year range
            filter_dict = {}
            if year_start is not None:
                filter_dict["year"] = {"$gte": str(year_start)}
            if year_end is not None:
                if "year" in filter_dict:
                    filter_dict["year"]["$lte"] = str(year_end)
                else:
                    filter_dict["year"] = {"$lte": str(year_end)}
            
            logger.info(f"Using filter: {filter_dict}")
            
            # Connect to index - using new Pinecone API
            index = self.pc.Index(self.index_name)
            
            # Perform hybrid search with metadata filtering
            search_results = index.query(
                vector=query_embedding,
                filter=filter_dict if filter_dict else None,
                top_k=15,
                include_metadata=True
            )
            
            # Log search results for debugging
            logger.info(f"Found {len(search_results.matches)} matches")
            
            # Extract retrieved contexts
            contexts = []
            for i, match in enumerate(search_results.matches):
                # Extract text and metadata
                text = match.metadata.get("text", "")
                source = match.metadata.get("source", "Unknown source")
                doc_year = match.metadata.get("year", "Unknown year")
                case_name = match.metadata.get("case_name", "Unknown case")
                citation = match.metadata.get("citation", "")
                
                # Log match details for debugging
                logger.info(f"Match {i+1}: Score {match.score}, Source: {source}, Year: {doc_year}")
                
                # Add formatted context
                contexts.append({
                    "text": text,
                    "metadata": {
                        "source": source,
                        "year": doc_year,
                        "case_name": case_name,
                        "citation": citation,
                        "score": match.score
                    }
                })
            
            # If no contexts were retrieved, provide a fallback
            if not contexts:
                logger.warning("No relevant information found in legal database")
                return {
                    "context": "",
                    "response": "I couldn't find any relevant case law or legal information based on your query and filters. Please try a different query or adjust the year range.",
                    "sources": []
                }
            
            # Format contexts for the LLM
            formatted_contexts = []
            for ctx in contexts:
                formatted_contexts.append(
                    f"[Case: {ctx['metadata']['case_name']}, Year: {ctx['metadata']['year']}, Citation: {ctx['metadata']['citation']}]\n\n{ctx['text']}"
                )
            
            combined_context = "\n\n---\n\n".join(formatted_contexts)
            
            # Create prompt for generation
            prompt = ChatPromptTemplate.from_messages([
                ("system", """
                You are a legal research assistant specializing in Massachusetts case law.
                Use the following information from legal cases to answer the query.
                Only use the information provided in the context.
                If the information is not in the context, say so clearly.
                Be specific about case names, citations, and legal principles.
                Respond in a formal legal writing style.
                Cite cases properly using standard legal citation format.
                Organize your analysis by legal principles and precedents.
                """),
                ("human", "Legal Context Information:\n{context}\n\nLegal Query: {query}")
            ])
            
            # Generate response using LLM
            logger.info("Generating response with LLM")
            chain = prompt | self.llm
            response = chain.invoke({
                "context": combined_context,
                "query": query_text
            })
            
            logger.info("LLM response generated successfully")
            
            # Extract sources for citation
            sources = []
            for ctx in contexts:
                sources.append({
                    "case_name": ctx["metadata"]["case_name"],
                    "citation": ctx["metadata"]["citation"],
                    "year": ctx["metadata"]["year"],
                    "source": ctx["metadata"]["source"],
                })
            
            # Return results
            return {
                "context": combined_context,
                "response": response.content,
                "sources": sources
            }
        except Exception as e:
            # Add better error handling
            logger.error(f"Error in legal RAG agent: {str(e)}", exc_info=True)
            return {
                "context": "",
                "response": f"Error retrieving legal information: {str(e)}",
                "sources": []
            }
    
    def test_connection(self) -> bool:
        """Test connection to Pinecone and verify index exists"""
        try:
            indexes = self.pc.list_indexes().names()
            logger.info(f"Available indexes: {indexes}")
            
            # Check if our index exists in the available indexes
            if self.index_name not in indexes:
                logger.error(f"Index '{self.index_name}' not found in available indexes: {indexes}")
                return False
                
            # Test a simple query to make sure we can connect
            index = self.pc.Index(self.index_name)
            stats = index.describe_index_stats()
            logger.info(f"Index stats: {stats}")
            
            return True
        except Exception as e:
            logger.error(f"Error testing Pinecone connection: {str(e)}", exc_info=True)
            return False