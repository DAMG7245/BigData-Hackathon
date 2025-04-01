import streamlit as st
import requests
import json
import time
from datetime import datetime
import os
from typing import Dict, Any, List, Optional

# Import components
from components.header import render_header
from components.sidebar import render_sidebar
from components.results import render_results

# Page configuration
st.set_page_config(
    page_title="Mass Legal Research Assistant",
    page_icon="⚖️",
    layout="wide"
)

# Initialize session state
if 'selected_report_type' not in st.session_state:
    st.session_state.selected_report_type = "Deep Research Report"
if 'selected_source' not in st.session_state:
    st.session_state.selected_source = "Hybrid"
if 'selected_tone' not in st.session_state:
    st.session_state.selected_tone = "Objective"
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'research_history' not in st.session_state:
    st.session_state.research_history = []
if 'current_research_id' not in st.session_state:
    st.session_state.current_research_id = None
if 'api_url' not in st.session_state:
    st.session_state.api_url = os.getenv("API_URL", "http://backend:8000")

# Function to start research
def start_research(query, format, length, agents, year_start, year_end):
    """Start a new research request and return the research ID"""
    try:
        response = requests.post(
            f"{st.session_state.api_url}/research",
            json={
                "query": query,
                "format": format,
                "length": length,
                "agents": agents,
                "year_start": year_start,
                "year_end": year_end
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            st.session_state.current_research_id = result["research_id"]
            
            # Add to research history
            st.session_state.research_history.append({
                "id": result["research_id"],
                "query": query,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "pending"
            })
            
            return result["research_id"]
        else:
            st.error(f"Error starting research: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)}")
        return None

# Function to check research status
def get_research_results(research_id):
    """Get results for a specific research request"""
    try:
        response = requests.get(f"{st.session_state.api_url}/research/{research_id}")
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error retrieving research: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)}")
        return None

# Render the header
render_header()

# Render the sidebar
selected_options = render_sidebar()

# Main content
main_tab, history_tab = st.tabs(["Research", "History"])

with main_tab:
    # Search input
    query = st.text_area("What legal topic would you like to research?", height=100)

    # Advanced options
    with st.expander("Advanced Options"):
        col1, col2 = st.columns(2)
        with col1:
            format_option = st.selectbox(
                "Output Format",
                options=["markdown", "html"],
                index=0
            )
            
            length_option = st.selectbox(
                "Research Depth",
                options=["brief", "standard", "comprehensive"],
                index=2,
                help="Brief: 5-7 pages, Standard: 10-15 pages, Comprehensive: 20-30 pages"
            )
        
        with col2:
            year_start = st.number_input("Start Year (Optional)", min_value=1700, max_value=2025, step=1, value=None)
            year_end = st.number_input("End Year (Optional)", min_value=1700, max_value=2025, step=1, value=None)

    # Agent selection
    st.write("Select Research Components:")
    col1, col2 = st.columns(2)
    with col1:
        use_historical = st.checkbox("Massachusetts Case Law", value=True)
    with col2:
        use_web = st.checkbox("Current Legal Commentary", value=True)

    # Generate button
    if st.button("Generate Research Report"):
        if not query:
            st.error("Please enter a research question")
        else:
            agents = []
            if use_historical:
                agents.append("legal_rag")
            if use_web:
                agents.append("websearch")
            
            if not agents:
                st.error("Please select at least one research component")
            else:
                with st.spinner("Starting research..."):
                    research_id = start_research(
                        query=query,
                        format=format_option,
                        length=length_option,
                        agents=agents,
                        year_start=year_start if year_start is not None and year_start > 0 else None,
                        year_end=year_end if year_end is not None and year_end > 0 else None
                    )
                    
                    if research_id:
                        st.success(f"Research started! ID: {research_id}")
                        st.session_state.current_research_id = research_id

    # Display current research if available
    if st.session_state.current_research_id:
        research_id = st.session_state.current_research_id
        
        # Poll for results
        placeholder = st.empty()
        with placeholder.container():
            with st.spinner("Researching..."):
                complete = False
                while not complete:
                    results = get_research_results(research_id)
                    
                    if results:
                        status = results.get("status", "")
                        
                        if status == "completed":
                            complete = True
                            # Update history
                            for i, item in enumerate(st.session_state.research_history):
                                if item["id"] == research_id:
                                    st.session_state.research_history[i]["status"] = "completed"
                        
                        elif status == "failed":
                            complete = True
                            st.error(f"Research failed: {results.get('error', 'Unknown error')}")
                            # Update history
                            for i, item in enumerate(st.session_state.research_history):
                                if item["id"] == research_id:
                                    st.session_state.research_history[i]["status"] = "failed"
                        
                        # If still in progress, wait and try again
                        if not complete:
                            progress_message = "Research in progress"
                            started = results.get("started_at", 0)
                            elapsed = time.time() - started
                            st.write(f"{progress_message} ({elapsed:.1f} seconds elapsed)")
                            time.sleep(2)
                    else:
                        st.error("Could not retrieve research results")
                        break
        
        # Clear the placeholder and display results
        placeholder.empty()
        
        if complete:
            results = get_research_results(research_id)
            if results and results.get("status") == "completed":
                render_results(results)

with history_tab:
    st.subheader("Research History")
    
    if not st.session_state.research_history:
        st.info("No research history yet")
    else:
        # Display history as a table
        history_data = []
        for item in st.session_state.research_history:
            history_data.append({
                "ID": item["id"],
                "Query": item["query"],
                "Time": item["timestamp"],
                "Status": item["status"].capitalize()
            })
        
        st.table(history_data)
        
        # Option to load a previous research
        selected_history = st.selectbox("Select research to load:", 
                                     options=[f"{h['query']} ({h['id']})" for h in st.session_state.research_history],
                                     index=0)
        
        if st.button("Load Selected Research"):
            # Extract research ID from selection
            selected_id = selected_history.split("(")[-1].replace(")", "")
            st.session_state.current_research_id = selected_id
            st.experimental_rerun()

# Footer
st.markdown("---")
st.markdown(f"© {datetime.now().year} Mass Legal Research Assistant. All rights reserved.")