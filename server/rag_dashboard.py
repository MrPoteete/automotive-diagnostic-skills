
import streamlit as st
import requests
import json
import time

# --- CONFIGURATION ---
API_URL = "http://localhost:8000"
API_KEY = "mechanic-secret-key-123"

st.set_page_config(
    page_title="Automotive RAG Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLING ---
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .main {
        background: #0e1117;
    }
    h1 {
        color: #ff4b4b;
    }
    .stTextInput > div > div > input {
        color: #000000;
        background-color: #ffffff;
        font-size: 1.2em;
    }
    .complaint-card {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 5px solid #ff4b4b;
    }
    .complaint-header {
        font-weight: bold;
        font-size: 1.1em;
        color: #ffa421;
        margin-bottom: 5px;
    }
    .complaint-summary {
        color: #e0e0e0;
        font-family: monospace;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/engine-warning.png", width=80)
    st.title("Mechanic's Assistant")
    st.markdown("---")
    
    # Server Status Check
    try:
        response = requests.get(f"{API_URL}/", timeout=1)
        if response.status_code == 200:
            st.success("✅ RAG Server Online")
        else:
            st.error("❌ Server Error")
    except:
        st.error("❌ Server Offline")
        st.info("Run 'start_server.bat' to fix.")

    st.markdown("### Settings")
    limit = st.slider("Max Results", 1, 20, 5)
    
    st.markdown("---")
    st.caption("v1.0.0 | Powered by NHTSA Data")

# --- MAIN APP ---
st.title("🔍 Automotive Complaint Search")
st.markdown("Identify common failures by searching the **National Highway Traffic Safety Administration (NHTSA)** database.")

# Search Input
query = st.text_input("Describe the problem (e.g., '2015 Ford Focus transmission shudder')", placeholder="Enter vehicle and symptoms...")

if st.button("Search Database", type="primary") or query:
    if not query:
        st.warning("Please enter a search term.")
    else:
        with st.spinner(f"Searching for '{query}'..."):
            try:
                # Call the API
                headers = {"X-API-KEY": API_KEY}
                params = {"query": query, "limit": limit}
                start_time = time.time()
                response = requests.get(f"{API_URL}/search", headers=headers, params=params)
                end_time = time.time()
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    # Metrics
                    col1, col2 = st.columns(2)
                    col1.metric("Results Found", len(results))
                    col2.metric("Search Time", f"{(end_time - start_time):.3f}s")
                    
                    if "sanitized_query" in data and data["sanitized_query"] != query:
                         st.caption(f"Sanitized Query: `{data['sanitized_query']}`")

                    
                    st.markdown("### 📋 Findings")
                    
                    if not results:
                        st.info("No specific complaints found. Try broadening your search terms.")
                    
                    for i, result in enumerate(results):
                        # Construct a nice card
                        make = result.get('make', 'UNKNOWN')
                        model = result.get('model', 'UNKNOWN')
                        year = result.get('year', '????')
                        comp = result.get('component', 'GENERAL')
                        summary = result.get('summary', 'No details provided.')
                        
                        st.markdown(f"""
                        <div class="complaint-card">
                            <div class="complaint-header">
                                🚗 {year} {make} {model} | {comp}
                            </div>
                            <div class="complaint-summary">
                                "{summary}"
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    with st.expander("View Raw JSON Response"):
                        st.json(data)
                        
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.write(response.text)
                    
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the RAG Server. Is it running?")
