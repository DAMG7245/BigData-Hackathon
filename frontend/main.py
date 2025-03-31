import streamlit as st
import requests
import json
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="GPT Researcher",
    page_icon="🔍",
    layout="wide"
)

# Initialize session state
if 'selected_report_type' not in st.session_state:
    st.session_state.selected_report_type = "Deep Research Report"
if 'selected_source' not in st.session_state:
    st.session_state.selected_source = "My Documents"
if 'selected_tone' not in st.session_state:
    st.session_state.selected_tone = "Objective"
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []

# Sidebar for settings
with st.sidebar:
    st.title("Settings")
    
    # Report Type
    st.subheader("Report Type")
    report_type = st.selectbox(
        "Select report type",
        options=[
            "Summary - Short and fast (~2 min)",
            "Deep Research Report",
            "Multi Agents Report",
            "Detailed - In depth and longer (~5 min)"
        ],
        index=1
    )
    
    # Report Source
    st.subheader("Report Source")
    report_source = st.selectbox(
        "Select source",
        options=[
            "The Internet",
            "My Documents",
            "Hybrid"
        ],
        index=1
    )
    
    # File upload
    st.subheader("Upload Files")
    uploaded_files = st.file_uploader("Choose files", accept_multiple_files=True)
    if uploaded_files:
        st.session_state.uploaded_files = uploaded_files
        for file in uploaded_files:
            st.write(f"File uploaded: {file.name}")
    
    # Tone selection
    st.subheader("Tone")
    tone = st.selectbox(
        "Select tone",
        options=[
            "Objective",
            "Formal",
            "Analytical",
            "Persuasive",
            "Informative",
            "Explanatory",
            "Descriptive",
            "Critical",
            "Comparative",
            "Speculative",
            "Reflective",
            "Narrative",
            "Humorous",
            "Optimistic",
            "Pessimistic"
        ],
        index=0
    )
    
    # Preferences section
    st.subheader("Preferences")
    st.checkbox("Dark mode", value=True)
    st.checkbox("Save history", value=True)
    
    # Update session state
    st.session_state.selected_report_type = report_type
    st.session_state.selected_source = report_source
    st.session_state.selected_tone = tone

# Main content
st.title("DataNexus Pro - Mass Legal Research Assistant")
st.subheader("Say Goodbye to Hours of Legal Research")
st.write("Your AI assistant for rapid legal insights, case analysis, and comprehensive research")

# Search input
query = st.text_input("What would you like to research next?")

# Agent selection
st.write("Select Legal Research Components:")
col1, col2, col3 = st.columns(3)
with col1:
    use_historical = st.checkbox("Case Law & Precedents", value=True)
with col2:
    use_financial = st.checkbox("Statutes & Regulations", value=True)
with col3:
    use_news = st.checkbox("Legal Commentary & News", value=True)

# Quick research suggestions
st.subheader("Quick Legal Research Ideas")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("⚖️ Recent Supreme Court decisions"):
        st.session_state.query = "Recent Supreme Court decisions on privacy law"
with col2:
    if st.button("📝 Contract clause analysis"):
        st.session_state.query = "Standard force majeure clause analysis"
with col3:
    if st.button("🔍 Case law precedents"):
        st.session_state.query = "Landmark precedents in intellectual property law"

# Generate button
if st.button("Generate Research Report"):
    agents = []
    if use_historical:
        agents.append("historical")
    if use_financial:
        agents.append("financial")
    if use_news:
        agents.append("news")
    
    # Display mock progress
    with st.spinner("Generating research report..."):
        st.success("Research data collected!")
        
        # Display example report
        st.subheader("Legal Research Report")
        
        if use_historical:
            st.markdown("### Case Law Analysis")
            st.write("This section examines relevant precedents and case history related to your legal query.")
            
        if use_financial:
            st.markdown("### Statutory Framework")
            st.write("This section analyzes applicable statutes, regulations, and legal frameworks.")
            
        if use_news:
            st.markdown("### Legal Commentary & Recent Developments")
            st.write("This section summarizes scholarly opinions, law journal articles, and recent legal developments.")

# Footer
st.markdown("---")
st.markdown(f"© {datetime.now().year} DataNexus Pro AI Researcher. All rights reserved.")