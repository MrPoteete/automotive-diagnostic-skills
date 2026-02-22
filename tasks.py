
import subprocess
import sys
import os

def run_command(command, description):
    print(f"\n🚀 Running Task: {description}")
    print(f"Executing: {command}")
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}: {e}")
        sys.exit(1)

def setup():
    if not os.path.exists(".venv"):
        run_command("python -m venv .venv", "Creating Virtual Environment")
    
    if os.name == 'nt':
        pip_cmd = r".venv\Scripts\pip"
    else:
        pip_cmd = ".venv/bin/pip"

    if os.path.exists("requirements.txt"):
        run_command(f"{pip_cmd} install -r requirements.txt", "Installing Dependencies")
    else:
        print("requirements.txt not found. Skipping dependency installation.")

def db_stats():
    script_path = os.path.join("database", "init_database_simple.py")
    if os.path.exists(script_path):
        run_command(f"python {script_path} --stats", "Database Statistics")
    else:
        print(f"Database script not found at {script_path}")

def update_status():
    print("Opening PROJECT_STATUS.md for update in your default editor...")
    if os.name == 'nt':
        os.startfile("PROJECT_STATUS.md")
    elif sys.platform == 'darwin':
        subprocess.call(('open', "PROJECT_STATUS.md"))
    else:
        subprocess.call(('xdg-open', "PROJECT_STATUS.md"))

def help():
    print("Available Tasks:")
    print("  setup          - Set up virtual environment and install dependencies")
    print("  db-stats       - Show database statistics (using existing init script)")
    print("  update-status  - Open PROJECT_STATUS.md for manual update")
    print("  help           - Show this help message")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        help()
    else:
        task = sys.argv[1]
        if task == "setup":
            setup()
        elif task == "db-stats":
            db_stats()
        elif task == "update-status":
            update_status()
        elif task == "help":
            help()
        else:
            print(f"Unknown task: {task}")
            help()
