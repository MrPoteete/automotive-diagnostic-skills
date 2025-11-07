#!/usr/bin/env python3
"""
Analyze large text file structure and identify separators.

This script examines the first portion of a large file to identify:
- File encoding
- Line/record separators (including unusual Unicode separators)
- Field delimiters
- Data structure patterns

Safe for very large files (streams data, doesn't load into memory).
"""

import sys
import chardet
from pathlib import Path
from collections import Counter


def detect_encoding(file_path: Path, sample_size: int = 100000) -> str:
    """
    Detect file encoding by reading a sample.

    Args:
        file_path: Path to the file
        sample_size: Bytes to read for detection

    Returns:
        Detected encoding name (e.g., 'utf-8', 'latin-1')
    """
    with open(file_path, 'rb') as f:
        raw_sample = f.read(sample_size)

    result = chardet.detect(raw_sample)
    return result['encoding']


def analyze_separators(file_path: Path, encoding: str, lines_to_check: int = 1000) -> dict:
    """
    Analyze file for unusual separator characters.

    Args:
        file_path: Path to the file
        encoding: File encoding
        lines_to_check: Number of lines to analyze

    Returns:
        Dict with separator analysis results
    """
    unusual_chars = Counter()
    total_bytes_read = 0

    # Characters to look for
    CONTROL_CHARS = {
        '\x1e': 'RS (Record Separator)',
        '\x1f': 'US (Unit Separator)',
        '\u2028': 'LS (Line Separator)',
        '\u2029': 'PS (Paragraph Separator)',
        '\t': 'TAB',
        '|': 'PIPE',
        '\x00': 'NULL',
    }

    with open(file_path, 'r', encoding=encoding, errors='replace') as f:
        for i, line in enumerate(f):
            if i >= lines_to_check:
                break

            total_bytes_read += len(line.encode(encoding))

            # Count control characters
            for char, name in CONTROL_CHARS.items():
                count = line.count(char)
                if count > 0:
                    unusual_chars[name] += count

    return {
        'unusual_separators': dict(unusual_chars),
        'bytes_analyzed': total_bytes_read,
        'lines_analyzed': min(lines_to_check, i + 1)
    }


def show_sample_records(file_path: Path, encoding: str, num_records: int = 5) -> None:
    """
    Display first few records with separator visualization.

    Args:
        file_path: Path to the file
        encoding: File encoding
        num_records: Number of records to display
    """
    print(f"\n{'='*80}")
    print(f"FIRST {num_records} RECORDS (with separator visualization):")
    print(f"{'='*80}\n")

    with open(file_path, 'r', encoding=encoding, errors='replace') as f:
        content = f.read(10000)  # Read first 10KB

    # Replace control characters for visibility
    visible = content
    visible = visible.replace('\u2029', '⏎[PS]⏎')  # Paragraph Separator
    visible = visible.replace('\u2028', '↵[LS]↵')  # Line Separator
    visible = visible.replace('\x1e', '␞[RS]␞')    # Record Separator
    visible = visible.replace('\x1f', '␟[US]␟')    # Unit Separator
    visible = visible.replace('\t', '→[TAB]→')     # Tab

    print(visible[:2000])  # Show first 2000 chars
    print(f"\n{'='*80}\n")


def analyze_file_size(file_path: Path) -> dict:
    """Get file size information."""
    size_bytes = file_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    size_gb = size_bytes / (1024 * 1024 * 1024)

    return {
        'bytes': size_bytes,
        'megabytes': round(size_mb, 2),
        'gigabytes': round(size_gb, 2),
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_file_structure.py <path_to_large_file>")
        print("\nExample:")
        print("  python analyze_file_structure.py /path/to/nhtsa_complaints.txt")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"ANALYZING FILE: {file_path.name}")
    print(f"{'='*80}\n")

    # File size
    size_info = analyze_file_size(file_path)
    print(f"📊 FILE SIZE:")
    print(f"   {size_info['gigabytes']} GB ({size_info['megabytes']} MB)")
    print(f"   {size_info['bytes']:,} bytes\n")

    # Encoding detection
    print("🔍 Detecting encoding...")
    encoding = detect_encoding(file_path)
    print(f"   Detected: {encoding}\n")

    # Separator analysis
    print("🔎 Analyzing separators (first 1000 lines)...")
    sep_analysis = analyze_separators(file_path, encoding, lines_to_check=1000)
    print(f"   Lines analyzed: {sep_analysis['lines_analyzed']}")
    print(f"   Bytes analyzed: {sep_analysis['bytes_analyzed']:,}\n")

    if sep_analysis['unusual_separators']:
        print("   ⚠️  UNUSUAL SEPARATORS FOUND:")
        for sep_name, count in sep_analysis['unusual_separators'].items():
            print(f"      {sep_name}: {count} occurrences")
    else:
        print("   ✅ No unusual separators detected (standard newlines)")

    # Show sample records
    show_sample_records(file_path, encoding, num_records=5)

    # Recommendations
    print(f"{'='*80}")
    print("💡 RECOMMENDATIONS:")
    print(f"{'='*80}\n")

    if 'PS (Paragraph Separator)' in sep_analysis['unusual_separators']:
        print("✓ File uses Paragraph Separator (U+2029) - likely NHTSA format")
        print("  → Use split on '\\u2029' for record boundaries\n")

    if 'LS (Line Separator)' in sep_analysis['unusual_separators']:
        print("✓ File uses Line Separator (U+2028) - multi-line fields")
        print("  → Use split on '\\u2028' for field boundaries within records\n")

    if 'TAB' in sep_analysis['unusual_separators']:
        print("✓ File uses tabs as delimiters")
        print("  → Consider tab-separated parsing\n")

    print("📝 Next steps:")
    print("   1. Review the sample records above")
    print("   2. Identify the field structure (what each field represents)")
    print("   3. Run the streaming parser to process the full file")
    print()


if __name__ == '__main__':
    main()
