

def inspect_file(filepath):
    print(f"Inspecting: {filepath}")
    with open(filepath, 'r', encoding='latin-1') as f:
        for i, line in enumerate(f):
            if i >= 50: break
            parts = line.strip().split('\t')
            print(f"Line {i}: {len(parts)} columns")
            for idx, part in enumerate(parts):
                print(f"  Col {idx}: {part}")
            print("-" * 20)

if __name__ == "__main__":
    # Hardcoded path for now based on user's env
    path = r"C:\Users\potee\Documents\GitHub\automotive-diagnostic-skills\TSB DATA\TSBS_RECEIVED_2005-2009\TSBS_RECEIVED_2005-2009.txt"
    inspect_file(path)
