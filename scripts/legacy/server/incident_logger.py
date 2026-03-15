import json
import traceback
import uuid
from datetime import datetime
import os

LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "incident_history.jsonl")

def log_incident(agent_id, error, context=None):
    """
    Logs an error incident to the central history file.
    
    Args:
        agent_id (str): Name of the agent/script (e.g., 'data_miner').
        error (Exception): The exception object.
        context (dict): Additional metadata (e.g., url, args).
    """
    # Ensure log directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    incident = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "agent_id": agent_id,
        "error": {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc()
        },
        "context": context or {},
        "resolution": None,
        "status": "OPEN"
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(incident) + "\n")
    
    print(f"[IncidentLogger] Logged error {incident['id']} for {agent_id}")
    return incident['id']
