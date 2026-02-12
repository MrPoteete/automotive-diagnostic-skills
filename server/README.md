# Automotive Diagnostic RAG Server

This directory contains the core server infrastructure for the AI mechanic system.

## 🚀 Quick Launch
**Double-click** `start_full_system.bat` to launch everything.

---

## 📂 Key Files

### 1. Launchers (Batch Scripts)
-   **`start_full_system.bat`** (Recommended): Launches Server + Dashboard in the correct order.
-   **`start_server.bat`**: Starts ONLY the backend API server (`server.log` will capture output).
-   **`start_dashboard.bat`**: Starts ONLY the frontend UI (Streamlit) in your browser.
-   **`setup_environment.bat`**: Run this ONCE to install Python libraries and mine initial data.

### 2. Core Applications
-   **`home_server.py`**: The "brain". A FastAPI server that connects to the database (`automotive_complaints.db`) and provides search APIs.
-   **`rag_dashboard.py`**: The "face". A Streamlit web app that lets you search for complaints.
-   **`data_miner.py`**: The "worker". Downloads data from NHTSA.
    -   Usage: `python data_miner.py --fleet` (Mines 20 years of data for 60+ models).

### 3. Configuration
-   **`mining_targets.json`**: List of vehicles (Make/Model) to download when running the miner.
-   **`server.log`**: Standard log file. Rotates automatically (Max 5MB, keeps 3 backups).

## 📱 Remote Access
You can access this dashboard from any tablet/phone on your Tailscale network.
1.  Ensure Tailscale is connected.
2.  Go to `http://[YOUR-TAILSCALE-IP]:8501`.

## 🛠 Troubleshooting
-   **Server closes immediately?** Run `start_server.bat` and read the error message (it will pause).
-   **Dashboard says "Offline"?** Make sure the black "Server" window is open.
-   **No data?** Run `setup_environment.bat` to re-trigger the data miner.
