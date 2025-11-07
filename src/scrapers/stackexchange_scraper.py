#!/usr/bin/env python3
"""
Stack Exchange API scraper for automotive diagnostic discussions.

Scrapes mechanics.stackexchange.com for real-world diagnostic conversations,
repair approaches, and solutions. Uses official Stack Exchange API with
respectful rate limiting.

Stack Exchange API Documentation:
https://api.stackexchange.com/docs

Rate Limits:
- Anonymous: 300 requests/day
- Authenticated: 10,000 requests/day
- Backoff: Respect 'backoff' field in responses
"""

import json
import time
import requests
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Question:
    """Represents a Stack Exchange question."""
    question_id: int
    title: str
    body: str
    tags: List[str]
    score: int
    view_count: int
    answer_count: int
    creation_date: str
    last_activity_date: str
    owner_reputation: int
    owner_display_name: str
    is_answered: bool
    accepted_answer_id: Optional[int]
    link: str
    answers: List[Dict[str, Any]]
    comments: List[Dict[str, Any]]


class StackExchangeScraper:
    """
    Scrapes automotive diagnostic discussions from Stack Exchange.

    Uses the official Stack Exchange API with built-in rate limiting
    and respectful request handling.
    """

    BASE_URL = "https://api.stackexchange.com/2.3"
    SITE = "mechanics"  # mechanics.stackexchange.com

    # Automotive-related tags to focus on
    AUTOMOTIVE_TAGS = [
        'diagnostics',
        'troubleshooting',
        'obd-ii',
        'check-engine-light',
        'engine',
        'transmission',
        'electrical',
        'brakes',
        'abs',
        'airbag',
        'fuel-system',
        'ignition',
        'sensors',
        'ford',
        'gm',
        'chevrolet',
        'ram',
        'dodge',
    ]

    def __init__(self, output_dir: str = "data/raw_imports/forum_data"):
        """
        Initialize scraper.

        Args:
            output_dir: Directory to save scraped data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiting
        self.requests_made = 0
        self.quota_remaining = None
        self.quota_max = None
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests (respectful)

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Automotive-Diagnostic-AI/1.0 (Educational/Research)'
        })

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """
        Make API request with rate limiting and error handling.

        Args:
            endpoint: API endpoint (e.g., '/questions')
            params: Query parameters

        Returns:
            Response JSON or None on error
        """
        # Enforce minimum request interval
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

        # Add required parameters
        params.update({
            'site': self.SITE,
            # Use default filter (withbody) for questions
            'filter': 'withbody' if endpoint == '/questions' else 'default',
        })

        url = f"{self.BASE_URL}{endpoint}"

        try:
            logger.info(f"Making request to {endpoint} with params: {params}")
            response = self.session.get(url, params=params, timeout=30)
            self.last_request_time = time.time()
            self.requests_made += 1

            # Check for rate limit issues
            if response.status_code == 429:
                logger.warning("Rate limit exceeded, waiting 60 seconds...")
                time.sleep(60)
                return self._make_request(endpoint, params)

            # Check for other errors
            if response.status_code == 403:
                logger.error(f"403 Forbidden - API access denied. Response: {response.text[:200]}")
                return None

            response.raise_for_status()

            # Try to decompress gzip response, fallback to plain JSON
            try:
                content = gzip.decompress(response.content)
                data = json.loads(content)
            except (OSError, gzip.BadGzipFile):
                # Not gzipped, try plain JSON
                data = response.json()

            # Update quota information
            self.quota_remaining = data.get('quota_remaining')
            self.quota_max = data.get('quota_max')

            logger.info(f"Quota: {self.quota_remaining}/{self.quota_max} remaining")

            # Handle backoff (API asking us to slow down)
            if 'backoff' in data:
                backoff = data['backoff']
                logger.warning(f"API requested backoff: {backoff} seconds")
                time.sleep(backoff)

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    def get_questions(
        self,
        tags: Optional[List[str]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        max_questions: int = 10000
    ) -> List[Dict]:
        """
        Fetch questions from Stack Exchange.

        Args:
            tags: Filter by tags (defaults to AUTOMOTIVE_TAGS)
            from_date: Start date for questions
            to_date: End date for questions
            max_questions: Maximum number of questions to fetch

        Returns:
            List of question dictionaries
        """
        # Don't use default tags - they're too restrictive
        # If user wants tags, they can specify them explicitly
        if tags is None:
            tags = []  # Changed: Don't default to AUTOMOTIVE_TAGS

        if from_date is None:
            from_date = datetime.now() - timedelta(days=365 * 10)  # 10 years

        all_questions = []
        page = 1
        has_more = True

        params = {
            'pagesize': 100,  # Max allowed by API
            'sort': 'activity',
            'order': 'desc',
            'fromdate': int(from_date.timestamp()),
        }

        # Only add tagged parameter if tags are specified
        if tags:
            params['tagged'] = ';'.join(tags)

        # Only add todate if explicitly specified (don't default to "now")
        if to_date is not None:
            params['todate'] = int(to_date.timestamp())

        while has_more and len(all_questions) < max_questions:
            params['page'] = page

            response = self._make_request('/questions', params)
            if not response:
                logger.error("Failed to fetch questions, stopping")
                break

            items = response.get('items', [])
            if not items:
                break

            all_questions.extend(items)
            has_more = response.get('has_more', False)
            page += 1

            logger.info(f"Fetched {len(all_questions)} questions so far...")

            # Check quota
            if self.quota_remaining and self.quota_remaining < 10:
                logger.warning(f"Low quota ({self.quota_remaining}), stopping to be safe")
                break

        logger.info(f"Total questions fetched: {len(all_questions)}")
        return all_questions

    def get_answers(self, question_ids: List[int]) -> Dict[int, List[Dict]]:
        """
        Fetch answers for given question IDs.

        Args:
            question_ids: List of question IDs

        Returns:
            Dictionary mapping question_id to list of answers
        """
        # API allows up to 100 IDs per request
        batch_size = 100
        all_answers = {}

        for i in range(0, len(question_ids), batch_size):
            batch = question_ids[i:i + batch_size]
            ids_str = ';'.join(map(str, batch))

            params = {
                'order': 'desc',
                'sort': 'votes',
            }

            response = self._make_request(f'/questions/{ids_str}/answers', params)
            if not response:
                continue

            for answer in response.get('items', []):
                qid = answer.get('question_id')
                if qid not in all_answers:
                    all_answers[qid] = []
                all_answers[qid].append(answer)

            logger.info(f"Fetched answers for {len(batch)} questions")

        return all_answers

    def get_comments(self, question_ids: List[int]) -> Dict[int, List[Dict]]:
        """
        Fetch comments for given question IDs.

        Args:
            question_ids: List of question IDs

        Returns:
            Dictionary mapping question_id to list of comments
        """
        batch_size = 100
        all_comments = {}

        for i in range(0, len(question_ids), batch_size):
            batch = question_ids[i:i + batch_size]
            ids_str = ';'.join(map(str, batch))

            params = {
                'order': 'desc',
                'sort': 'creation',
            }

            response = self._make_request(f'/questions/{ids_str}/comments', params)
            if not response:
                continue

            for comment in response.get('items', []):
                qid = comment.get('post_id')
                if qid not in all_comments:
                    all_comments[qid] = []
                all_comments[qid].append(comment)

            logger.info(f"Fetched comments for {len(batch)} questions")

        return all_comments

    def scrape_full_threads(
        self,
        tags: Optional[List[str]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        max_questions: int = 10000
    ) -> List[Question]:
        """
        Scrape complete question threads including answers and comments.

        Args:
            tags: Filter by tags
            from_date: Start date
            to_date: End date
            max_questions: Maximum questions to fetch

        Returns:
            List of Question objects with full thread data
        """
        logger.info("Starting Stack Exchange scrape...")
        logger.info(f"Target: {self.SITE}.stackexchange.com")
        logger.info(f"Date range: {from_date} to {to_date}")
        logger.info(f"Tags: {tags or self.AUTOMOTIVE_TAGS}")

        # Step 1: Get questions
        questions_data = self.get_questions(tags, from_date, to_date, max_questions)
        if not questions_data:
            logger.error("No questions fetched")
            return []

        question_ids = [q['question_id'] for q in questions_data]

        # Step 2: Get answers
        logger.info("Fetching answers...")
        answers_by_question = self.get_answers(question_ids)

        # Step 3: Get comments
        logger.info("Fetching comments...")
        comments_by_question = self.get_comments(question_ids)

        # Step 4: Combine into Question objects
        questions = []
        for q_data in questions_data:
            qid = q_data['question_id']

            question = Question(
                question_id=qid,
                title=q_data.get('title', ''),
                body=q_data.get('body', ''),
                tags=q_data.get('tags', []),
                score=q_data.get('score', 0),
                view_count=q_data.get('view_count', 0),
                answer_count=q_data.get('answer_count', 0),
                creation_date=datetime.fromtimestamp(
                    q_data.get('creation_date', 0)
                ).isoformat(),
                last_activity_date=datetime.fromtimestamp(
                    q_data.get('last_activity_date', 0)
                ).isoformat(),
                owner_reputation=q_data.get('owner', {}).get('reputation', 0),
                owner_display_name=q_data.get('owner', {}).get('display_name', 'Anonymous'),
                is_answered=q_data.get('is_answered', False),
                accepted_answer_id=q_data.get('accepted_answer_id'),
                link=q_data.get('link', ''),
                answers=answers_by_question.get(qid, []),
                comments=comments_by_question.get(qid, []),
            )

            questions.append(question)

        logger.info(f"Compiled {len(questions)} complete question threads")
        return questions

    def save_data(self, questions: List[Question], filename: str = None):
        """
        Save scraped data to JSON file.

        Args:
            questions: List of Question objects
            filename: Output filename (auto-generated if not provided)
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"stackexchange_mechanics_{timestamp}.json"

        output_path = self.output_dir / filename

        # Convert to JSON-serializable format
        data = {
            'metadata': {
                'source': 'mechanics.stackexchange.com',
                'scrape_date': datetime.now().isoformat(),
                'total_questions': len(questions),
                'api_requests_made': self.requests_made,
                'note': 'Natural language diagnostic discussions for AI training',
            },
            'questions': [asdict(q) for q in questions]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Data saved to {output_path}")
        logger.info(f"File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")

        return output_path


def main():
    """
    Main entry point for scraping.

    Example usage:
        python src/scrapers/stackexchange_scraper.py
    """
    scraper = StackExchangeScraper()

    # Scrape last 10 years of ALL automotive discussions
    # Note: Tag filtering returns 0 results, so we scrape everything
    # and filter by content afterwards
    from_date = datetime.now() - timedelta(days=365 * 10)

    questions = scraper.scrape_full_threads(
        tags=None,  # No tags = get all mechanics questions
        from_date=from_date,
        to_date=None,  # Up to now
        max_questions=5000,  # Start with 5000 to be safe on quota
    )

    if questions:
        output_path = scraper.save_data(questions)

        # Print summary statistics
        print("\n" + "="*60)
        print("SCRAPE COMPLETE")
        print("="*60)
        print(f"Questions scraped: {len(questions)}")
        print(f"Total answers: {sum(len(q.answers) for q in questions)}")
        print(f"Total comments: {sum(len(q.comments) for q in questions)}")
        print(f"API requests made: {scraper.requests_made}")
        print(f"Output file: {output_path}")
        print("="*60)
    else:
        print("No data scraped!")


if __name__ == '__main__':
    main()
