@echo off
TITLE Automotive RAG Dashboard
CD /D "%~dp0"

echo Starting Dashboard UI...
streamlit run rag_dashboard.py --server.address 0.0.0.0
pause
