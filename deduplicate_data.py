#!/usr/bin/env python3
"""
Deduplicate scraped forum data.

Merges multiple scrape files and removes duplicate questions based on question_id.
"""

import json
from pathlib import Path
from datetime import datetime


def deduplicate_scraped_data(data_dir: Path = None, output_file: str = None):
    """
    Merge all scraped data files and remove duplicates.

    Args:
        data_dir: Directory containing scraped JSON files
        output_file: Output filename for deduplicated data
    """
    if data_dir is None:
        data_dir = Path("data/raw_imports/forum_data")

    json_files = list(data_dir.glob("stackexchange_*.json"))

    if not json_files:
        print("❌ No scraped data files found")
        return

    print("="*70)
    print("DEDUPLICATION UTILITY")
    print("="*70)
    print(f"Found {len(json_files)} scrape files\n")

    # Track unique questions by ID
    unique_questions = {}
    total_questions = 0
    duplicates_found = 0

    # Process each file
    for json_file in json_files:
        print(f"Processing: {json_file.name}")

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            questions = data.get('questions', [])
            total_questions += len(questions)

            for q in questions:
                q_id = q.get('question_id')

                if q_id in unique_questions:
                    duplicates_found += 1
                    # Keep the version with more data (more answers/comments)
                    existing = unique_questions[q_id]
                    existing_data = len(existing.get('answers', [])) + len(existing.get('comments', []))
                    new_data = len(q.get('answers', [])) + len(q.get('comments', []))

                    if new_data > existing_data:
                        unique_questions[q_id] = q
                else:
                    unique_questions[q_id] = q

    # Create output
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"stackexchange_mechanics_deduplicated_{timestamp}.json"

    output_path = data_dir / output_file

    deduplicated_data = {
        'metadata': {
            'source': 'mechanics.stackexchange.com',
            'deduplication_date': datetime.now().isoformat(),
            'total_files_merged': len(json_files),
            'total_questions_processed': total_questions,
            'duplicates_removed': duplicates_found,
            'unique_questions': len(unique_questions),
            'note': 'Deduplicated from multiple scrape runs',
        },
        'questions': list(unique_questions.values())
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(deduplicated_data, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "="*70)
    print("DEDUPLICATION COMPLETE")
    print("="*70)
    print(f"Total questions processed: {total_questions}")
    print(f"Duplicates removed: {duplicates_found}")
    print(f"Unique questions: {len(unique_questions)}")
    print(f"Deduplication rate: {(duplicates_found/total_questions*100):.1f}%")
    print(f"\nOutput: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
    print("="*70)


if __name__ == '__main__':
    deduplicate_scraped_data()
