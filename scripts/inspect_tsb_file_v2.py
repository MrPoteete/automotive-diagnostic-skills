

def inspect_file(filepath, outpath):
    print(f"Inspecting: {filepath}")
    with open(filepath, 'r', encoding='latin-1') as f:
        with open(outpath, 'w', encoding='utf-8') as out:
            for i, line in enumerate(f):
                if i >= 20: break
                parts = line.strip().split('\t')
                out.write(f"Line {i} ({len(parts)} cols):\n")
                for idx, part in enumerate(parts):
                    out.write(f"  Col {idx}: {part}\n")
                out.write("-" * 20 + "\n")

if __name__ == "__main__":
    path = r"C:\Users\potee\Documents\GitHub\automotive-diagnostic-skills\TSB DATA\TSBS_RECEIVED_2015-2019\TSBS_RECEIVED_2015-2019.txt"
    out = r"C:\Users\potee\.gemini\antigravity\scratch\tsb_inspection_2015.txt"
    inspect_file(path, out)
