import streamlit as st

def render_header():
    """Render the application header"""
    st.title("⚖️ Mass Legal Research Assistant")
    st.subheader("Powered by Massachusetts Reports (1768-2017)")
    st.write(
        "Your AI assistant for rapid legal insights, case analysis, and comprehensive research"
    )
    st.markdown("---")