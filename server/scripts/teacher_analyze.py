import json
import os
from collections import defaultdict
from datetime import datetime

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "logs", "incident_history.jsonl")
OUTPUT_FILE = os.path.join(BASE_DIR, "logs", "suggested_fixes.md")

def load_incidents():
    if not os.path.exists(LOG_FILE):
        return []
    
    incidents = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    incidents.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return incidents

def analyze_incidents(incidents):
    # Filter for OPEN incidents
    open_incidents = [i for i in incidents if i.get("status") == "OPEN"]
    
    # Group by (Agent, Error Type)
    grouped = defaultdict(list)
    for inc in open_incidents:
        key = (inc['agent_id'], inc['error']['type'])
        grouped[key].append(inc)
    
    return grouped

def generate_report(grouped_incidents):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = [
        f"# Teacher Analysis Report - {timestamp}",
        "",
        "## Summary",
        f"Found {sum(len(v) for v in grouped_incidents.values())} open incidents across {len(grouped_incidents)} unique error patterns.",
        "",
        "## Analysis & Suggestions",
        ""
    ]
    
    for (agent, error_type), items in grouped_incidents.items():
        count = len(items)
        latest = items[-1]
        error_msg = latest['error']['message']
        trace = latest['error'].get('traceback', 'No traceback')
        
        # Simple heuristic analysis (The "Teacher" Logic)
        suggestion = "Requires manual investigation."
        action_type = "MANUAL"
        
        if "Timeout" in error_type:
            suggestion = f"Consider increasing timeout or implementing retry logic in {agent}."
            action_type = "PROMPT_PATCH"
        elif "FileNotFound" in error_type:
            suggestion = f"Ensure paths are absolute or check file existence before access in {agent}."
            action_type = "CODE_PATCH"
        elif "Connection" in error_type:
            suggestion = "Check network connectivity or external service status."
            action_type = "CONFIG_CHANGE"

        report.append(f"### [{count}x] {agent}: {error_type}")
        report.append(f"- **Latest Message:** `{error_msg}`")
        report.append(f"- **Suggested Action ({action_type}):** {suggestion}")
        report.append(f"- **Sample Context:** `{json.dumps(latest.get('context', {}))}`")
        report.append("")
        report.append("#### Proposed Fix (Draft)")
        report.append("```markdown")
        if action_type == "PROMPT_PATCH":
            report.append(f"## Lessons Learned ({datetime.now().strftime('%Y-%m-%d')})")
            report.append(f"- **{error_type}**: {suggestion}")
        else:
            report.append(f"# TODO: Implement fix for {error_type} in {agent}")
        report.append("```")
        report.append("---")
    
    return "\n".join(report)

def generate_patches(grouped_incidents):
    patches = []
    
    for (agent, error_type), items in grouped_incidents.items():
        latest = items[-1]
        
        # Determine target file based on agent_id
        # Simple mapping for now
        target_file = None
        if agent == "demo_agent":
            # Just a demo target
            target_file = os.path.join(BASE_DIR, "demo_learning_loop.py")
        elif agent.endswith("_skill"):
            # Assume it's a SKILL.md file
            skill_name = agent
            target_file = os.path.join(os.path.dirname(BASE_DIR), "skills", skill_name, "SKILL.md")
        
        if not target_file or not os.path.exists(target_file):
            continue

        # Logic for patch content
        patch_content = ""
        if "Timeout" in error_type:
            patch_content = f"\n## Lessons Learned\n- **{error_type}**: Encountered timeout. Recommend implementing retry logic.\n"
        elif "Connection" in error_type:
             patch_content = "\n# [Teacher Patch] Connection issues detected. Review external service status.\n"
        
        if patch_content:
            patches.append({
                "target": target_file,
                "type": "append",
                "content": patch_content,
                "incident_id": latest['id']
            })
            
    return patches

def main():
    print(f"Analyzing incidents from {LOG_FILE}...")
    incidents = load_incidents()
    grouped = analyze_incidents(incidents)
    
    if not grouped:
        print("No open incidents found.")
        return

    report_content = generate_report(grouped)
    patches = generate_patches(grouped)
    
    # Ensure raw output dir
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    patch_file = os.path.join(BASE_DIR, "logs", "patches.json")
    with open(patch_file, "w", encoding="utf-8") as f:
        json.dump(patches, f, indent=2)
    
    print(f"Analysis complete. Report generated at: {OUTPUT_FILE}")
    print(f"Generated {len(patches)} automated patches in: {patch_file}")
    print("Review the report and use 'apply_fixes.py' to apply approved fixes.")

if __name__ == "__main__":
    main()
