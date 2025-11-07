#!/usr/bin/env python3
"""
Analyze scraped Stack Exchange forum data.

Provides statistics, quality metrics, and sample previews to help
decide how to incorporate forum data into the diagnostic system.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter, defaultdict
from datetime import datetime


class ForumDataAnalyzer:
    """
    Analyzes scraped forum data for quality and content insights.
    """

    def __init__(self, data_file: str):
        """
        Initialize analyzer with scraped data file.

        Args:
            data_file: Path to JSON file with scraped forum data
        """
        self.data_file = Path(data_file)

        with open(self.data_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

        self.questions = self.data.get('questions', [])
        self.metadata = self.data.get('metadata', {})

    def print_overview(self):
        """Print high-level overview of scraped data."""
        print("\n" + "="*70)
        print("STACK EXCHANGE DATA OVERVIEW")
        print("="*70)

        print(f"\nSource: {self.metadata.get('source', 'Unknown')}")
        print(f"Scrape Date: {self.metadata.get('scrape_date', 'Unknown')}")
        print(f"Total Questions: {len(self.questions)}")
        print(f"API Requests: {self.metadata.get('api_requests_made', 'Unknown')}")

        total_answers = sum(len(q.get('answers', [])) for q in self.questions)
        total_comments = sum(len(q.get('comments', [])) for q in self.questions)

        print(f"\nTotal Answers: {total_answers}")
        print(f"Total Comments: {total_comments}")
        print(f"Total Discussion Threads: {total_answers + total_comments}")

        # Calculate averages
        if self.questions:
            avg_answers = total_answers / len(self.questions)
            avg_comments = total_comments / len(self.questions)
            print(f"\nAverage Answers per Question: {avg_answers:.2f}")
            print(f"Average Comments per Question: {avg_comments:.2f}")

    def analyze_tags(self) -> Dict[str, int]:
        """Analyze tag distribution."""
        print("\n" + "="*70)
        print("TAG DISTRIBUTION")
        print("="*70)

        tag_counter = Counter()
        for question in self.questions:
            tags = question.get('tags', [])
            tag_counter.update(tags)

        # Print top 20 tags
        print(f"\nTop 20 Most Common Tags:")
        print("-" * 50)
        for tag, count in tag_counter.most_common(20):
            percentage = (count / len(self.questions)) * 100
            print(f"  {tag:30s} {count:5d} ({percentage:5.1f}%)")

        return dict(tag_counter)

    def analyze_dtc_codes(self):
        """Find and analyze OBD-II diagnostic codes mentioned in discussions."""
        print("\n" + "="*70)
        print("OBD-II DIAGNOSTIC CODES FOUND")
        print("="*70)

        # Regex patterns for DTC codes
        dtc_pattern = r'\b([PCBU][0-3][0-9A-F]{3})\b'

        dtc_counter = Counter()
        questions_with_codes = 0

        for question in self.questions:
            # Search in question title and body
            text = question.get('title', '') + ' ' + question.get('body', '')

            # Search in answers
            for answer in question.get('answers', []):
                text += ' ' + answer.get('body', '')

            # Find all DTCs
            codes = re.findall(dtc_pattern, text, re.IGNORECASE)
            if codes:
                questions_with_codes += 1
                dtc_counter.update([c.upper() for c in codes])

        print(f"\nQuestions mentioning DTCs: {questions_with_codes} ({questions_with_codes/len(self.questions)*100:.1f}%)")
        print(f"Unique DTC codes found: {len(dtc_counter)}")

        # Print top 30 most discussed codes
        if dtc_counter:
            print(f"\nTop 30 Most Discussed Codes:")
            print("-" * 50)
            for code, count in dtc_counter.most_common(30):
                print(f"  {code}  mentioned {count} times")

        return dict(dtc_counter)

    def analyze_manufacturers(self):
        """Analyze vehicle manufacturer mentions."""
        print("\n" + "="*70)
        print("MANUFACTURER MENTIONS")
        print("="*70)

        manufacturers = {
            'Ford': r'\b(ford|f-?150|f-?250|explorer|mustang|focus|fusion|escape|expedition)\b',
            'GM/Chevrolet': r'\b(chevy|chevrolet|gm|silverado|tahoe|suburban|malibu|cruze|impala)\b',
            'RAM/Dodge': r'\b(ram|dodge|1500|2500|journey|durango|caravan)\b',
            'Toyota': r'\b(toyota|camry|corolla|tacoma|tundra|rav4|highlander)\b',
            'Honda': r'\b(honda|civic|accord|cr-v|pilot)\b',
            'Nissan': r'\b(nissan|altima|sentra|rogue|frontier)\b',
        }

        make_counter = defaultdict(int)

        for question in self.questions:
            text = (question.get('title', '') + ' ' + question.get('body', '')).lower()

            for make, pattern in manufacturers.items():
                if re.search(pattern, text, re.IGNORECASE):
                    make_counter[make] += 1

        print("\nManufacturer Discussion Frequency:")
        print("-" * 50)
        for make, count in sorted(make_counter.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(self.questions)) * 100
            print(f"  {make:20s} {count:5d} questions ({percentage:5.1f}%)")

        return dict(make_counter)

    def analyze_quality_metrics(self):
        """Analyze data quality metrics."""
        print("\n" + "="*70)
        print("DATA QUALITY METRICS")
        print("="*70)

        answered_questions = sum(1 for q in self.questions if q.get('is_answered'))
        accepted_answers = sum(1 for q in self.questions if q.get('accepted_answer_id'))

        print(f"\nQuestions with answers: {answered_questions} ({answered_questions/len(self.questions)*100:.1f}%)")
        print(f"Questions with accepted answer: {accepted_answers} ({accepted_answers/len(self.questions)*100:.1f}%)")

        # Score distribution
        scores = [q.get('score', 0) for q in self.questions]
        print(f"\nQuestion Score Statistics:")
        print(f"  Average score: {sum(scores)/len(scores):.2f}")
        print(f"  Median score: {sorted(scores)[len(scores)//2]}")
        print(f"  Max score: {max(scores)}")
        print(f"  Min score: {min(scores)}")

        # High quality questions (score >= 5 and has accepted answer)
        high_quality = [
            q for q in self.questions
            if q.get('score', 0) >= 5 and q.get('accepted_answer_id')
        ]
        print(f"\nHigh Quality Questions (score>=5 + accepted answer): {len(high_quality)} ({len(high_quality)/len(self.questions)*100:.1f}%)")

        return {
            'answered': answered_questions,
            'accepted': accepted_answers,
            'high_quality': len(high_quality)
        }

    def show_sample_questions(self, num_samples: int = 3):
        """Show sample questions for manual review."""
        print("\n" + "="*70)
        print("SAMPLE QUESTIONS (for manual review)")
        print("="*70)

        # Show high-quality samples
        high_quality = [
            q for q in self.questions
            if q.get('score', 0) >= 5 and q.get('is_answered')
        ]

        samples = high_quality[:num_samples] if high_quality else self.questions[:num_samples]

        for i, question in enumerate(samples, 1):
            print(f"\n{'='*70}")
            print(f"SAMPLE {i}")
            print(f"{'='*70}")
            print(f"Title: {question.get('title', 'N/A')}")
            print(f"Link: {question.get('link', 'N/A')}")
            print(f"Score: {question.get('score', 0)}")
            print(f"Tags: {', '.join(question.get('tags', []))}")
            print(f"Answers: {len(question.get('answers', []))}")
            print(f"Comments: {len(question.get('comments', []))}")

            # Show snippet of question
            body = question.get('body', '')
            if body:
                # Strip HTML tags for preview
                body_text = re.sub(r'<[^>]+>', '', body)
                body_text = body_text[:300] + '...' if len(body_text) > 300 else body_text
                print(f"\nQuestion Preview:")
                print(body_text)

            # Show top answer if exists
            answers = question.get('answers', [])
            if answers:
                top_answer = max(answers, key=lambda a: a.get('score', 0))
                answer_text = re.sub(r'<[^>]+>', '', top_answer.get('body', ''))
                answer_text = answer_text[:200] + '...' if len(answer_text) > 200 else answer_text
                print(f"\nTop Answer Preview (score: {top_answer.get('score', 0)}):")
                print(answer_text)

    def generate_report(self, output_file: str = None):
        """Generate comprehensive analysis report."""
        if output_file is None:
            output_file = self.data_file.parent / f"analysis_{self.data_file.stem}.txt"

        # Run all analyses
        self.print_overview()
        tag_stats = self.analyze_tags()
        dtc_stats = self.analyze_dtc_codes()
        make_stats = self.analyze_manufacturers()
        quality_stats = self.analyze_quality_metrics()
        self.show_sample_questions()

        # Save summary to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("STACK EXCHANGE FORUM DATA ANALYSIS REPORT\n")
            f.write("="*70 + "\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Data File: {self.data_file}\n")
            f.write(f"Total Questions: {len(self.questions)}\n\n")

            f.write("KEY INSIGHTS:\n")
            f.write(f"- {quality_stats['high_quality']} high-quality diagnostic threads\n")
            f.write(f"- {len(dtc_stats)} unique DTC codes discussed\n")
            f.write(f"- {len(tag_stats)} unique tags\n")
            f.write(f"- Coverage across {len(make_stats)} manufacturers\n\n")

            f.write("RECOMMENDATION:\n")
            f.write("This data is rich in natural language diagnostic discussions\n")
            f.write("suitable for training AI models on mechanic reasoning patterns.\n")
            f.write("Consider:\n")
            f.write("1. Extracting high-quality Q&A pairs (score >= 5)\n")
            f.write("2. Linking DTC codes to real-world troubleshooting approaches\n")
            f.write("3. Using as training data for RAG embeddings\n")
            f.write("4. Building symptom -> diagnostic approach mappings\n")

        print(f"\n{'='*70}")
        print(f"Analysis report saved to: {output_file}")
        print(f"{'='*70}\n")


def main():
    """
    Analyze scraped forum data.

    Usage:
        python src/scrapers/analyze_forum_data.py
    """
    import sys

    data_dir = Path("data/raw_imports/forum_data")

    if not data_dir.exists():
        print(f"Error: {data_dir} does not exist")
        sys.exit(1)

    # Find most recent data file
    json_files = list(data_dir.glob("stackexchange_*.json"))

    if not json_files:
        print(f"No scraped data files found in {data_dir}")
        print("Run the scraper first: python src/scrapers/stackexchange_scraper.py")
        sys.exit(1)

    # Use most recent file
    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)

    print(f"Analyzing: {latest_file}")

    analyzer = ForumDataAnalyzer(latest_file)
    analyzer.generate_report()


if __name__ == '__main__':
    main()
