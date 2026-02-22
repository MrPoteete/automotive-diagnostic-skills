#!/usr/bin/env python3
"""
Process Stack Exchange forum data into structured diagnostic documents.

This script:
1. Reads raw JSON forum data
2. Filters for high-quality Q&A pairs
3. Extracts DTC codes, vehicle info, symptoms
4. Cleans HTML formatting
5. Creates structured documents ready for embedding

Usage:
    python src/rag/process_forum_data.py
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from bs4 import BeautifulSoup
from collections import Counter

# Import config
import sys
sys.path.append(str(Path(__file__).parent.parent))
from rag import config


@dataclass
class DiagnosticDocument:
    """Structured document for RAG retrieval."""
    id: str                          # Unique ID (e.g., "SE-100671")
    source: str                      # "stackexchange"
    title: str                       # Question title
    question_text: str               # Cleaned question body
    answer_text: str                 # Cleaned answer body
    full_text: str                   # Combined for embedding
    dtc_codes: List[str]            # Extracted DTC codes
    make: Optional[str]             # Vehicle make
    model: Optional[str]            # Vehicle model
    year: Optional[int]             # Vehicle year
    system: Optional[str]           # Automotive system (engine, brakes, etc.)
    tags: List[str]                 # Original tags
    score: int                      # Question score
    answer_score: int               # Answer score
    is_accepted: bool               # Has accepted answer
    view_count: int                 # Number of views
    url: str                        # Original URL
    created_date: str               # ISO format date


class ForumDataProcessor:
    """
    Processes raw Stack Exchange forum data into structured documents.
    """

    def __init__(self, forum_data_dir: Path = None):
        """
        Initialize processor.

        Args:
            forum_data_dir: Directory containing JSON forum data files
        """
        self.forum_data_dir = forum_data_dir or config.FORUM_DATA_DIR
        self.documents: List[DiagnosticDocument] = []
        self.stats = {
            'total_questions': 0,
            'high_quality_questions': 0,
            'dtc_codes_found': set(),
            'makes_found': Counter(),
            'years_found': Counter(),
        }

    def load_forum_data(self) -> List[Dict]:
        """
        Load all JSON forum data files.

        Returns:
            List of question dictionaries
        """
        all_questions = []
        json_files = list(self.forum_data_dir.glob("stackexchange_*.json"))

        if not json_files:
            print(f"⚠️  No forum data files found in {self.forum_data_dir}")
            print("   Make sure you've run the scraper first!")
            return []

        print(f"📁 Found {len(json_files)} forum data files")

        for json_file in json_files:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                questions = data.get('questions', [])
                all_questions.extend(questions)
                print(f"   {json_file.name}: {len(questions)} questions")

        self.stats['total_questions'] = len(all_questions)
        return all_questions

    def clean_html(self, html_text: str) -> str:
        """
        Clean HTML formatting from text.

        Args:
            html_text: HTML string

        Returns:
            Plain text
        """
        if not html_text:
            return ""

        # Parse HTML
        soup = BeautifulSoup(html_text, 'lxml')

        # Remove code blocks (keep them but format nicely)
        for code in soup.find_all('code'):
            code.string = f" `{code.get_text()}` "

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    def extract_dtc_codes(self, text: str) -> List[str]:
        """
        Extract all DTC codes from text.

        Args:
            text: Text to search

        Returns:
            List of unique DTC codes (e.g., ['P0300', 'P0420'])
        """
        codes = set()

        for pattern in config.DTC_PATTERNS.values():
            matches = re.findall(pattern, text, re.IGNORECASE)
            codes.update([m.upper() for m in matches])

        return sorted(list(codes))

    def extract_vehicle_info(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract vehicle information from text.

        Args:
            text: Text to search

        Returns:
            Dict with 'make', 'model', 'year'
        """
        info = {
            'make': None,
            'model': None,
            'year': None,
        }

        # Extract make
        for make, pattern in config.MANUFACTURER_PATTERNS.items():
            if re.search(pattern, text):
                info['make'] = make
                break  # Take first match

        # Extract year
        year_matches = re.findall(config.YEAR_PATTERN, text)
        if year_matches:
            # Take first year mentioned
            info['year'] = int(year_matches[0])

        # TODO: Extract model (more complex, needs make context)
        # For now, we'll rely on tags

        return info

    def infer_system(self, tags: List[str], text: str) -> Optional[str]:
        """
        Infer automotive system from tags and text.

        Args:
            tags: Question tags
            text: Question + answer text

        Returns:
            System name or None
        """
        system_keywords = {
            'engine': ['engine', 'motor', 'cylinder', 'piston', 'cam', 'valve', 'ignition', 'fuel-system'],
            'transmission': ['transmission', 'gearbox', 'shifting', 'clutch', 'torque-converter'],
            'brakes': ['brake', 'brakes', 'abs', 'pad', 'rotor', 'caliper'],
            'electrical': ['electrical', 'battery', 'alternator', 'starter', 'wiring'],
            'suspension': ['suspension', 'shock', 'strut', 'spring', 'control-arm'],
            'steering': ['steering', 'power-steering', 'rack', 'pinion'],
        }

        # Check tags first
        tags_lower = [t.lower() for t in tags]
        for system, keywords in system_keywords.items():
            if any(kw in tags_lower for kw in keywords):
                return system

        # Check text
        text_lower = text.lower()
        for system, keywords in system_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return system

        return None

    def is_high_quality(self, question: Dict) -> bool:
        """
        Check if question meets quality criteria.

        Args:
            question: Question dictionary

        Returns:
            True if high quality
        """
        # Check basic requirements
        if config.REQUIRE_ACCEPTED_ANSWER and not question.get('accepted_answer_id'):
            return False

        if question.get('score', 0) < config.MIN_QUESTION_SCORE:
            return False

        if question.get('view_count', 0) < config.MIN_VIEW_COUNT:
            return False

        # Check has answers
        answers = question.get('answers', [])
        if not answers:
            return False

        # Check content length
        body = question.get('body', '')
        if len(self.clean_html(body)) < config.MIN_QUESTION_LENGTH:
            return False

        return True

    def get_best_answer(self, question: Dict) -> Optional[Dict]:
        """
        Get the best answer for a question.

        Prefers accepted answer, then highest scored.

        Args:
            question: Question dictionary

        Returns:
            Answer dictionary or None
        """
        answers = question.get('answers', [])
        if not answers:
            return None

        # Try accepted answer first
        accepted_id = question.get('accepted_answer_id')
        if accepted_id:
            for answer in answers:
                if answer.get('answer_id') == accepted_id:
                    return answer

        # Fall back to highest scored
        answers_sorted = sorted(answers, key=lambda a: a.get('score', 0), reverse=True)
        return answers_sorted[0] if answers_sorted else None

    def create_document(self, question: Dict) -> Optional[DiagnosticDocument]:
        """
        Create a structured document from question data.

        Args:
            question: Question dictionary

        Returns:
            DiagnosticDocument or None if can't create
        """
        # Get best answer
        answer = self.get_best_answer(question)
        if not answer:
            return None

        # Check answer quality
        if answer.get('score', 0) < config.MIN_ANSWER_SCORE:
            return None

        # Clean text
        question_text = self.clean_html(question.get('body', ''))
        answer_text = self.clean_html(answer.get('body', ''))

        if len(answer_text) < config.MIN_ANSWER_LENGTH:
            return None

        # Create combined text for embedding
        title = question.get('title', '')
        full_text = f"[QUESTION] {title}\n{question_text}\n\n[SOLUTION] {answer_text}"

        # Extract metadata
        dtc_codes = self.extract_dtc_codes(full_text)
        vehicle_info = self.extract_vehicle_info(title + ' ' + question_text)
        tags = question.get('tags', [])
        system = self.infer_system(tags, full_text)

        # Create document
        doc = DiagnosticDocument(
            id=f"SE-{question['question_id']}",
            source="stackexchange",
            title=title,
            question_text=question_text,
            answer_text=answer_text,
            full_text=full_text[:config.MAX_CHUNK_LENGTH],  # Limit length
            dtc_codes=dtc_codes,
            make=vehicle_info.get('make'),
            model=None,  # TODO: Extract from tags if possible
            year=vehicle_info.get('year'),
            system=system,
            tags=tags,
            score=question.get('score', 0),
            answer_score=answer.get('score', 0),
            is_accepted=answer.get('answer_id') == question.get('accepted_answer_id'),
            view_count=question.get('view_count', 0),
            url=question.get('link', ''),
            created_date=question.get('creation_date', ''),
        )

        # Update stats
        if dtc_codes:
            self.stats['dtc_codes_found'].update(dtc_codes)
        if vehicle_info.get('make'):
            self.stats['makes_found'][vehicle_info['make']] += 1
        if vehicle_info.get('year'):
            self.stats['years_found'][vehicle_info['year']] += 1

        return doc

    def process_all(self) -> List[DiagnosticDocument]:
        """
        Process all forum data.

        Returns:
            List of DiagnosticDocument objects
        """
        print("\n" + "="*70)
        print("PROCESSING FORUM DATA")
        print("="*70)

        # Load data
        questions = self.load_forum_data()
        if not questions:
            return []

        print(f"\n✅ Loaded {len(questions)} total questions")

        # Filter for quality
        high_quality = [q for q in questions if self.is_high_quality(q)]
        self.stats['high_quality_questions'] = len(high_quality)

        print(f"✅ Filtered to {len(high_quality)} high-quality questions")
        print(f"   ({len(high_quality)/len(questions)*100:.1f}% pass quality filters)")

        # Create documents
        documents = []
        for question in high_quality:
            doc = self.create_document(question)
            if doc:
                documents.append(doc)

        self.documents = documents

        # Print stats
        print("\n📊 EXTRACTION RESULTS:")
        print(f"   Documents created: {len(documents)}")
        print(f"   Unique DTC codes: {len(self.stats['dtc_codes_found'])}")

        if self.stats['makes_found']:
            print("\n   Vehicle makes found:")
            for make, count in self.stats['makes_found'].most_common(10):
                print(f"      {make}: {count} discussions")

        if self.stats['dtc_codes_found']:
            print("\n   Top 10 DTC codes:")
            code_counts = Counter()
            for doc in documents:
                code_counts.update(doc.dtc_codes)
            for code, count in code_counts.most_common(10):
                print(f"      {code}: {count} mentions")

        return documents

    def save_documents(self, output_file: Path = None):
        """
        Save processed documents to JSON.

        Args:
            output_file: Output path (default: config.DIAGNOSTIC_DOCUMENTS)
        """
        if output_file is None:
            output_file = config.DIAGNOSTIC_DOCUMENTS

        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to JSON-serializable format
        data = {
            'metadata': {
                'created': datetime.now().isoformat(),
                'total_documents': len(self.documents),
                'total_questions_processed': self.stats['total_questions'],
                'quality_pass_rate': self.stats['high_quality_questions'] / max(self.stats['total_questions'], 1),
                'unique_dtc_codes': len(self.stats['dtc_codes_found']),
            },
            'documents': [asdict(doc) for doc in self.documents]
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Saved {len(self.documents)} documents to:")
        print(f"   {output_file}")
        print(f"   File size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")


def main():
    """Main entry point."""
    processor = ForumDataProcessor()

    # Process all data
    documents = processor.process_all()

    if documents:
        # Save processed documents
        processor.save_documents()

        print("\n" + "="*70)
        print("✅ PROCESSING COMPLETE")
        print("="*70)
        print("\nNext step: Generate embeddings")
        print("   python src/rag/generate_embeddings.py")
    else:
        print("\n❌ No documents created!")
        print("   Check that you have scraped forum data in:")
        print(f"   {config.FORUM_DATA_DIR}")


if __name__ == '__main__':
    main()
