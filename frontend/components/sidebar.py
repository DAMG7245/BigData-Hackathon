import streamlit as st

def render_sidebar():
    """Render the sidebar with options and return selected values"""
    with st.sidebar:
        st.title("Settings")
        
        # Report Type
        st.subheader("Report Type")
        report_type = st.selectbox(
            "Select report type",
            options=[
                "Summary - Short and fast (~2 min)",
                "Deep Research Report",
                "Detailed - In depth and longer (~5 min)"
            ],
            index=1
        )
        
        # Report Source
        st.subheader("Report Source")
        report_source = st.selectbox(
            "Select source",
            options=[
                "Massachusetts Case Law",
                "Web Legal Sources",
                "Hybrid"
            ],
            index=2
        )
        
        # File upload (for future use)
        st.subheader("Upload Files")
        uploaded_files = st.file_uploader("Choose files for additional context", accept_multiple_files=True)
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
                "Explanatory"
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
        
        # Quick research suggestions
        st.subheader("Quick Legal Research Ideas")
        if st.button("⚖️ Recent Supreme Court decisions"):
            st.session_state.query = "Recent Massachusetts Supreme Judicial Court decisions on privacy law"
        if st.button("📝 Contract clause analysis"):
            st.session_state.query = "Massachusetts standard force majeure clause analysis"
        if st.button("🔍 Property law precedents"):
            st.session_state.query = "Landmark Massachusetts precedents in property law"
        
        # Return selected options
        return {
            "report_type": report_type,
            "report_source": report_source,
            "tone": tone
        }