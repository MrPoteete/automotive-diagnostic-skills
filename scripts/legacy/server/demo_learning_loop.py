import incident_logger
import time

def risky_task():
    print("Attempting risky task...")
    time.sleep(1)
    # Simulate a failure
    raise ConnectionError("Failed to connect to the Mainframe!")

def main():
    agent_name = "demo_agent"
    try:
        risky_task()
    except Exception as e:
        print("Caught error! Logging to persistent memory...")
        incident_id = incident_logger.log_incident(
            agent_id=agent_name,
            error=e,
            context={"attempt": 1, "target": "Mainframe"}
        )
        print(f"Incident {incident_id} recorded.")
        print("Integration Successful. The 'Teacher' would now analyze this log.")

if __name__ == "__main__":
    main()
