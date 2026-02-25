# Checked AGENTS.md - implementing directly because this is a lint-only fix
# (E722 bare except). No logic changes. security-engineer review not required.

import streamlit as st  # type: ignore[import-untyped]
import requests  # type: ignore[import-untyped]
import time

# --- CONFIGURATION ---
import os
from dotenv import load_dotenv
load_dotenv()

API_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY", "fallback-key-for-dev")

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
        caret-color: #000000;
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
    except Exception:
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
            headers = {"X-API-KEY": API_KEY}
            params = {"query": query, "limit": limit}

            tab_complaints, tab_tsbs = st.tabs(["📝 Owner Complaints", "🔧 Technical Service Bulletins (TSBs)"])

            # --- COMPLAINTS TAB ---
            with tab_complaints:
                try:
                    start_time = time.time()
                    response = requests.get(f"{API_URL}/search", headers=headers, params=params)
                    end_time = time.time()

                    if response.status_code == 200:
                        data = response.json()
                        results = data.get("results", [])

                        col1, col2 = st.columns(2)
                        col1.metric("Complaints Found", len(results))
                        col2.metric("Time", f"{(end_time - start_time):.3f}s")

                        if not results:
                            st.info("No specific complaints found.")

                        for result in results:
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
                    else:
                        st.error(f"API Error: {response.status_code}")
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to Server.")

            # --- TSB TAB ---
            with tab_tsbs:
                try:
                    start_time = time.time()
                    response = requests.get(f"{API_URL}/search_tsbs", headers=headers, params=params)
                    end_time = time.time()

                    if response.status_code == 200:
                        data = response.json()
                        results = data.get("results", [])

                        col1, col2 = st.columns(2)
                        col1.metric("TSBs Found", len(results))
                        col2.metric("Time", f"{(end_time - start_time):.3f}s")

                        if "message" in data:
                            st.warning(data["message"])
                        elif not results:
                            st.info("No TSBs found matching your query.")

                        for result in results:
                            make = result.get('make', 'UNKNOWN')
                            model = result.get('model', 'UNKNOWN')
                            year = result.get('year', '????')
                            comp = result.get('component', 'GENERAL')
                            summary = result.get('summary', 'No details provided.')
                            tsb_id = result.get('nhtsa_id', 'N/A')

                            st.markdown(f"""
                            <div class="complaint-card" style="border-left: 5px solid #4b7bff;">
                                <div class="complaint-header" style="color: #4b7bff;">
                                    🔧 {year} {make} {model} | TSB #{tsb_id}
                                </div>
                                <div style="font-size: 0.9em; color: #88aec6; margin-bottom: 5px;">
                                    Component: {comp}
                                </div>
                                <div class="complaint-summary">
                                    "{summary}"
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.error(f"API Error: {response.status_code}")
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to Server.")
