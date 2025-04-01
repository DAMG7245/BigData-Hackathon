import streamlit as st
import pandas as pd
from datetime import datetime

def render_results(results):
    """Render research results"""
    st.subheader("Legal Research Report")
    
    # Display metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Query:** {results.get('query', 'N/A')}")
    with col2:
        started = datetime.fromtimestamp(results.get('started_at', 0))
        st.write(f"**Started:** {started.strftime('%Y-%m-%d %H:%M:%S')}")
    with col3:
        if results.get('completed_at'):
            completed = datetime.fromtimestamp(results.get('completed_at', 0))
            duration = completed - started
            st.write(f"**Duration:** {duration.total_seconds():.1f} seconds")
    
    # Display content
    st.markdown("---")
    content = results.get('content', 'No content available')
    st.markdown(content)
    
    # Display sources
    st.markdown("---")
    st.subheader("Sources")
    
    sources = results.get('sources', [])
    if not sources:
        st.info("No sources available")
    else:
        # Group sources by type
        case_law_sources = [s for s in sources if s.get('type') == 'case_law']
        web_sources = [s for s in sources if s.get('type') == 'web']
        
        # Display case law sources
        if case_law_sources:
            st.write("**Case Law:**")
            case_data = []
            for source in case_law_sources:
                case_data.append({
                    "Case Name": source.get('case_name', 'Unknown'),
                    "Citation": source.get('citation', ''),
                    "Year": source.get('year', ''),
                })
            st.table(pd.DataFrame(case_data))
        
        # Display web sources
        if web_sources:
            st.write("**Web Sources:**")
            web_data = []
            for source in web_sources:
                web_data.append({
                    "Title": source.get('title', 'Unknown'),
                    "Published": source.get('published_date', ''),
                    "URL": source.get('url', '')
                })
            st.table(pd.DataFrame(web_data))
    
    # Download options
    st.markdown("---")
    st.subheader("Download Options")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Download as PDF"):
            st.info("Preparing PDF download...")
            # This would be implemented with a PDF generation library
    
    with col2:
        if st.button("Download as Word Document"):
            st.info("Preparing Word document download...")
            # This would be implemented with a docx generation library